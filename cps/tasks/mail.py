from __future__ import division, print_function, unicode_literals
import sys
import os
import smtplib
import threading
import socket

try:
    from StringIO import StringIO
    from email.MIMEBase import MIMEBase
    from email.MIMEMultipart import MIMEMultipart
    from email.MIMEText import MIMEText
except ImportError:
    from io import StringIO
    from email.mime.base import MIMEBase
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

from email import encoders
from email.utils import formatdate, make_msgid
from email.generator import Generator

from cps.services.worker import CalibreTask
from cps import logger, config

from cps import gdriveutils

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
                    lock=threading.Lock()
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
    def __init__(self, subject, filepath, attachment, settings, recipient, taskMessage, text, internal=False):
        super(TaskEmail, self).__init__(taskMessage)
        self.subject = subject
        self.attachment = attachment
        self.settings = settings
        self.filepath = filepath
        self.recipent = recipient
        self.text = text
        self.asyncSMTP = None

        self.results = dict()

    def run(self, worker_thread):
        # create MIME message
        msg = MIMEMultipart()
        msg['Subject'] = self.subject
        msg['Message-Id'] = make_msgid('calibre-web')
        msg['Date'] = formatdate(localtime=True)
        text = self.text
        msg.attach(MIMEText(text.encode('UTF-8'), 'plain', 'UTF-8'))
        if self.attachment:
            result = self._get_attachment(self.filepath, self.attachment)
            if result:
                msg.attach(result)
            else:
                self._handleError(u"Attachment not found")
                return

        msg['From'] = self.settings["mail_from"]
        msg['To'] = self.recipent

        use_ssl = int(self.settings.get('mail_use_ssl', 0))
        try:
            # convert MIME message to string
            fp = StringIO()
            gen = Generator(fp, mangle_from_=False)
            gen.flatten(msg)
            msg = fp.getvalue()

            # send email
            timeout = 600  # set timeout to 5mins

            # redirect output to logfile on python2 pn python3 debugoutput is caught with overwritten
            # _print_debug function
            if sys.version_info < (3, 0):
                org_smtpstderr = smtplib.stderr
                smtplib.stderr = logger.StderrLogger('worker.smtp')

            if use_ssl == 2:
                self.asyncSMTP = EmailSSL(self.settings["mail_server"], self.settings["mail_port"],
                                           timeout=timeout)
            else:
                self.asyncSMTP = Email(self.settings["mail_server"], self.settings["mail_port"], timeout=timeout)

            # link to logginglevel
            if logger.is_debug_enabled():
                self.asyncSMTP.set_debuglevel(1)
            if use_ssl == 1:
                self.asyncSMTP.starttls()
            if self.settings["mail_password"]:
                self.asyncSMTP.login(str(self.settings["mail_login"]), str(self.settings["mail_password"]))
            self.asyncSMTP.sendmail(self.settings["mail_from"], self.recipent, msg)
            self.asyncSMTP.quit()
            self._handleSuccess()

            if sys.version_info < (3, 0):
                smtplib.stderr = org_smtpstderr

        except (MemoryError) as e:
            log.debug_or_exception(e)
            self._handleError(u'MemoryError sending email: ' + str(e))
            # return None
        except (smtplib.SMTPException, smtplib.SMTPAuthenticationError) as e:
            if hasattr(e, "smtp_error"):
                text = e.smtp_error.decode('utf-8').replace("\n", '. ')
            elif hasattr(e, "message"):
                text = e.message
            elif hasattr(e, "args"):
                text = '\n'.join(e.args)
            else:
                log.debug_or_exception(e)
                text = ''
            self._handleError(u'Smtplib Error sending email: ' + text)
            # return None
        except (socket.error) as e:
            self._handleError(u'Socket Error sending email: ' + e.strerror)
            # return None


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


    @classmethod
    def _get_attachment(cls, bookpath, filename):
        """Get file as MIMEBase message"""
        calibrepath = config.config_calibre_dir
        if config.config_use_google_drive:
            df = gdriveutils.getFileFromEbooksFolder(bookpath, filename)
            if df:
                datafile = os.path.join(calibrepath, bookpath, filename)
                if not os.path.exists(os.path.join(calibrepath, bookpath)):
                    os.makedirs(os.path.join(calibrepath, bookpath))
                df.GetContentFile(datafile)
            else:
                return None
            file_ = open(datafile, 'rb')
            data = file_.read()
            file_.close()
            os.remove(datafile)
        else:
            try:
                file_ = open(os.path.join(calibrepath, bookpath, filename), 'rb')
                data = file_.read()
                file_.close()
            except IOError as e:
                log.debug_or_exception(e)
                log.error(u'The requested file could not be read. Maybe wrong permissions?')
                return None

        attachment = MIMEBase('application', 'octet-stream')
        attachment.set_payload(data)
        encoders.encode_base64(attachment)
        attachment.add_header('Content-Disposition', 'attachment',
                              filename=filename)
        return attachment

    @property
    def name(self):
        return "Email"
