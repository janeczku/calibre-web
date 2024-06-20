# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2020 pwr
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program. If not, see <http://www.gnu.org/licenses/>.

import os
import smtplib
import ssl
import threading
import socket
import mimetypes

from io import StringIO
from email.message import EmailMessage
from email.utils import formatdate, parseaddr
from email.generator import Generator
from flask_babel import lazy_gettext as N_

from cps.services.worker import CalibreTask
from cps.services import gmail
from cps.embed_helper import do_calibre_export
from cps import logger, config
from cps import gdriveutils
import uuid

log = logger.create()

CHUNKSIZE = 8192


# Class for sending email with ability to get current progress
class EmailBase:

    transferSize = 0
    progress = 0

    def data(self, msg):
        self.transferSize = len(msg)
        (code, resp) = smtplib.SMTP.data(self, msg)
        self.progress = 0
        return (code, resp)

    def send(self, strg):
        """Send `strg' to the server."""
        log.debug_no_auth('send: {}'.format(strg[:300]))
        if hasattr(self, 'sock') and self.sock:
            try:
                if self.transferSize:
                    lock = threading.Lock()
                    lock.acquire()
                    self.transferSize = len(strg)
                    lock.release()
                    for i in range(0, self.transferSize, CHUNKSIZE):
                        if isinstance(strg, bytes):
                            self.sock.send((strg[i:i + CHUNKSIZE]))
                        else:
                            self.sock.send((strg[i:i + CHUNKSIZE]).encode('utf-8'))
                        lock.acquire()
                        self.progress = i
                        lock.release()
                else:
                    self.sock.sendall(strg.encode('utf-8'))
            except socket.error:
                self.close()
                raise smtplib.SMTPServerDisconnected('Server not connected')
        else:
            raise smtplib.SMTPServerDisconnected('please run connect() first')

    @classmethod
    def _print_debug(cls, *args):
        log.debug(args)

    def getTransferStatus(self):
        if self.transferSize:
            lock2 = threading.Lock()
            lock2.acquire()
            value = int((float(self.progress) / float(self.transferSize))*100)
            lock2.release()
            return value / 100
        else:
            return 1


# Class for sending email with ability to get current progress, derived from emailbase class
class Email(EmailBase, smtplib.SMTP):

    def __init__(self, *args, **kwargs):
        smtplib.SMTP.__init__(self, *args, **kwargs)


# Class for sending ssl encrypted email with ability to get current progress, , derived from emailbase class
class EmailSSL(EmailBase, smtplib.SMTP_SSL):

    def __init__(self, *args, **kwargs):
        smtplib.SMTP_SSL.__init__(self, *args, **kwargs)


class TaskEmail(CalibreTask):
    def __init__(self, subject, filepath, attachment, settings, recipient, task_message, text, id=0, internal=False):
        super(TaskEmail, self).__init__(task_message)
        self.subject = subject
        self.attachment = attachment
        self.settings = settings
        self.filepath = filepath
        self.recipient = recipient
        self.text = text
        self.asyncSMTP = None
        self.book_id = id
        self.results = dict()

    # from calibre code:
    # https://github.com/kovidgoyal/calibre/blob/731ccd92a99868de3e2738f65949f19768d9104c/src/calibre/utils/smtp.py#L60
    def get_msgid_domain(self):
        try:
            # Parse out the address from the From line, and then the domain from that
            from_email = parseaddr(self.settings["mail_from"])[1]
            msgid_domain = from_email.partition('@')[2].strip()
            # This can sometimes sneak through parseaddr if the input is malformed
            msgid_domain = msgid_domain.rstrip('>').strip()
        except Exception:
            msgid_domain = ''
        return msgid_domain or 'calibre-web.com'

    def prepare_message(self):
        message = EmailMessage()
        # message = MIMEMultipart()
        message['From'] = self.settings["mail_from"]
        message['To'] = self.recipient
        message['Subject'] = self.subject
        message['Date'] = formatdate(localtime=True)
        message['Message-Id'] = "{}@{}".format(uuid.uuid4(), self.get_msgid_domain())
        message.set_content(self.text.encode('UTF-8'), "text", "plain")
        if self.attachment:
            data = self._get_attachment(self.filepath, self.attachment)
            if data:
                # Set mimetype
                content_type, encoding = mimetypes.guess_type(self.attachment)
                if content_type is None or encoding is not None:
                    content_type = 'application/octet-stream'
                main_type, sub_type = content_type.split('/', 1)
                message.add_attachment(data, maintype=main_type, subtype=sub_type, filename=self.attachment)
            else:
                self._handleError("Attachment not found")
                return
        return message

    def run(self, worker_thread):
        try:
            # create MIME message
            msg = self.prepare_message()
            if not msg:
                return
            if self.settings['mail_server_type'] == 0:
                self.send_standard_email(msg)
            else:
                self.send_gmail_email(msg)
        except MemoryError as e:
            log.error_or_exception(e, stacklevel=3)
            self._handleError('MemoryError sending e-mail: {}'.format(str(e)))
        except (smtplib.SMTPException, smtplib.SMTPAuthenticationError) as e:
            log.error_or_exception(e, stacklevel=3)
            if hasattr(e, "smtp_error"):
                text = e.smtp_error.decode('utf-8').replace("\n", '. ')
            elif hasattr(e, "message"):
                text = e.message
            elif hasattr(e, "args"):
                text = '\n'.join(e.args)
            else:
                text = ''
            self._handleError('Smtplib Error sending e-mail: {}'.format(text))
        except (socket.error) as e:
            log.error_or_exception(e, stacklevel=3)
            self._handleError('Socket Error sending e-mail: {}'.format(e.strerror))
        except Exception as ex:
            log.error_or_exception(ex, stacklevel=3)
            self._handleError('Error sending e-mail: {}'.format(ex))

    def send_standard_email(self, msg):
        use_ssl = int(self.settings.get('mail_use_ssl', 0))
        timeout = 600  # set timeout to 5mins

        # on python3 debugoutput is caught with overwritten _print_debug function
        log.debug("Start sending e-mail")
        if use_ssl == 2:
            context = ssl.create_default_context()
            self.asyncSMTP = EmailSSL(self.settings["mail_server"], self.settings["mail_port"],
                                       timeout=timeout, context=context)
        else:
            self.asyncSMTP = Email(self.settings["mail_server"], self.settings["mail_port"], timeout=timeout)

        # link to logginglevel
        if logger.is_debug_enabled():
            self.asyncSMTP.set_debuglevel(1)
        if use_ssl == 1:
            context = ssl.create_default_context()
            self.asyncSMTP.starttls(context=context)
        if self.settings["mail_password_e"]:
            self.asyncSMTP.login(str(self.settings["mail_login"]), str(self.settings["mail_password_e"]))

        # Convert message to something to send
        fp = StringIO()
        gen = Generator(fp, mangle_from_=False)
        gen.flatten(msg)

        self.asyncSMTP.sendmail(self.settings["mail_from"], self.recipient, fp.getvalue())
        self.asyncSMTP.quit()
        self._handleSuccess()
        log.debug("E-mail send successfully")

    def send_gmail_email(self, message):
        gmail.send_messsage(self.settings.get('mail_gmail_token', None), message)
        self._handleSuccess()

    @property
    def progress(self):
        if self.asyncSMTP is not None:
            return self.asyncSMTP.getTransferStatus()
        else:
            return self._progress

    @progress.setter
    def progress(self, x):
        """This gets explicitly set when handle(Success|Error) are called. In this case, remove the SMTP connection"""
        if x == 1:
            self.asyncSMTP = None
            self._progress = x

    def _get_attachment(self, book_path, filename):
        """Get file as MIMEBase message"""
        calibre_path = config.get_book_path()
        extension = os.path.splitext(filename)[1][1:]
        if config.config_use_google_drive:
            df = gdriveutils.getFileFromEbooksFolder(book_path, filename)
            if df:
                datafile = os.path.join(calibre_path, book_path, filename)
                if not os.path.exists(os.path.join(calibre_path, book_path)):
                    os.makedirs(os.path.join(calibre_path, book_path))
                df.GetContentFile(datafile)
            else:
                return None
            if config.config_binariesdir and config.config_embed_metadata:
                data_path, data_file = do_calibre_export(self.book_id, extension)
                datafile = os.path.join(data_path, data_file + "." + extension)
            with open(datafile, 'rb') as file_:
                data = file_.read()
            os.remove(datafile)
        else:
            datafile = os.path.join(calibre_path, book_path, filename)
            try:
                if config.config_binariesdir and config.config_embed_metadata:
                    data_path, data_file = do_calibre_export(self.book_id, extension)
                    datafile = os.path.join(data_path, data_file + "." + extension)
                with open(datafile, 'rb') as file_:
                    data = file_.read()
                if config.config_binariesdir and config.config_embed_metadata:
                    os.remove(datafile)
            except IOError as e:
                log.error_or_exception(e, stacklevel=3)
                log.error('The requested file could not be read. Maybe wrong permissions?')
                return None
        return data

    @property
    def name(self):
        return N_("E-mail")

    @property
    def is_cancellable(self):
        return False

    def __str__(self):
        return "E-mail {}, {}".format(self.name, self.subject)
