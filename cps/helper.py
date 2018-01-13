#!/usr/bin/env python
# -*- coding: utf-8 -*-

import db
import ub
from flask import current_app as app
import logging
import smtplib
from tempfile import gettempdir
import socket
import sys
import os
import traceback
import re
import unicodedata

try:
    from StringIO import StringIO
    from email.MIMEBase import MIMEBase
    from email.MIMEMultipart import MIMEMultipart
    from email.MIMEText import MIMEText
except ImportError as e:
    from io import StringIO
    from email.mime.base import MIMEBase
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

from email import encoders
from email.generator import Generator
from email.utils import formatdate
from email.utils import make_msgid
from flask_babel import gettext as _
import subprocess
import threading
import shutil
import requests
import zipfile
from tornado.ioloop import IOLoop
try:
    import gdriveutils as gd
except ImportError:
    pass
import web

try:
    import unidecode
    use_unidecode = True
except ImportError:
    use_unidecode = False

# Global variables
global_task = None
updater_thread = None

RET_SUCCESS = 1
RET_FAIL = 0


def update_download(book_id, user_id):
    check = ub.session.query(ub.Downloads).filter(ub.Downloads.user_id == user_id).filter(ub.Downloads.book_id ==
                                                                                          book_id).first()

    if not check:
        new_download = ub.Downloads(user_id=user_id, book_id=book_id)
        ub.session.add(new_download)
        ub.session.commit()


def make_mobi(book_id, calibrepath):
    error_message = None
    vendorpath = os.path.join(os.path.normpath(os.path.dirname(os.path.realpath(__file__)) +
                                               os.sep + "../vendor" + os.sep))
    if sys.platform == "win32":
        kindlegen = (os.path.join(vendorpath, u"kindlegen.exe")).encode(sys.getfilesystemencoding())
    else:
        kindlegen = (os.path.join(vendorpath, u"kindlegen")).encode(sys.getfilesystemencoding())
    if not os.path.exists(kindlegen):
        error_message = _(u"kindlegen binary %(kindlepath)s not found", kindlepath=kindlegen)
        app.logger.error("make_mobi: " + error_message)
        return error_message, RET_FAIL
    book = db.session.query(db.Books).filter(db.Books.id == book_id).first()
    data = db.session.query(db.Data).filter(db.Data.book == book.id).filter(db.Data.format == 'EPUB').first()
    if not data:
        error_message = _(u"epub format not found for book id: %(book)d", book=book_id)
        app.logger.error("make_mobi: " + error_message)
        return error_message, RET_FAIL

    file_path = os.path.join(calibrepath, book.path, data.name)
    if os.path.exists(file_path + u".epub"):
        try:
            p = subprocess.Popen((kindlegen + " \"" + file_path + u".epub\"").encode(sys.getfilesystemencoding()),
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        except Exception:
            error_message = _(u"kindlegen failed, no execution permissions")
            app.logger.error("make_mobi: " + error_message)
            return error_message, RET_FAIL
        # Poll process for new output until finished
        while True:
            nextline = p.stdout.readline()
            if nextline == '' and p.poll() is not None:
                break
            if nextline != "\r\n":
                # Format of error message (kindlegen translates its output texts):
                # Error(prcgen):E23006: Language not recognized in metadata.The dc:Language field is mandatory.Aborting.
                conv_error = re.search(".*\(.*\):(E\d+):\s(.*)", nextline)
                # If error occoures, log in every case
                if conv_error:
                    error_message = _(u"Kindlegen failed with Error %(error)s. Message: %(message)s",
                                      error=conv_error.group(1), message=conv_error.group(2).decode('utf-8'))
                    app.logger.info("make_mobi: " + error_message)
                    app.logger.info(nextline.strip('\r\n'))
                app.logger.debug(nextline.strip('\r\n'))

        check = p.returncode
        if not check or check < 2:
            book.data.append(db.Data(
                    name=book.data[0].name,
                    book_format="MOBI",
                    book=book.id,
                    uncompressed_size=os.path.getsize(file_path + ".mobi")
                ))
            db.session.commit()
            return file_path + ".mobi", RET_SUCCESS
        else:
            app.logger.info("make_mobi: kindlegen failed with error while converting book")
            if not error_message:
                error_message = 'kindlegen failed, no excecution permissions'
            return error_message, RET_FAIL
    else:
        error_message = "make_mobi: epub not found: %s.epub" % file_path
        return error_message, RET_FAIL


class StderrLogger(object):

    buffer = ''

    def __init__(self):
        self.logger = logging.getLogger('cps.web')

    def write(self, message):
        if message == '\n':
            self.logger.debug(self.buffer)
            self.buffer = ''
        else:
            self.buffer += message


def send_raw_email(kindle_mail, msg):
    settings = ub.get_mail_settings()

    msg['From'] = settings["mail_from"]
    msg['To'] = kindle_mail

    use_ssl = int(settings.get('mail_use_ssl', 0))

    # convert MIME message to string
    fp = StringIO()
    gen = Generator(fp, mangle_from_=False)
    gen.flatten(msg)
    msg = fp.getvalue()

    # send email
    try:
        timeout = 600     # set timeout to 5mins

        org_stderr = sys.stderr
        sys.stderr = StderrLogger()

        if use_ssl == 2:
            mailserver = smtplib.SMTP_SSL(settings["mail_server"], settings["mail_port"], timeout)
        else:
            mailserver = smtplib.SMTP(settings["mail_server"], settings["mail_port"], timeout)
        mailserver.set_debuglevel(1)

        if use_ssl == 1:
            mailserver.starttls()

        if settings["mail_password"]:
            mailserver.login(str(settings["mail_login"]), str(settings["mail_password"]))
        mailserver.sendmail(settings["mail_from"], kindle_mail, msg)
        mailserver.quit()

        smtplib.stderr = org_stderr

    except (socket.error, smtplib.SMTPRecipientsRefused, smtplib.SMTPException) as ex:
        app.logger.error(traceback.print_exc())
        return _("Failed to send mail: %s" % str(ex))

    return None


def send_test_mail(kindle_mail):
    msg = MIMEMultipart()
    msg['Subject'] = _(u'Calibre-web test email')
    text = _(u'This email has been sent via calibre web.')
    msg.attach(MIMEText(text.encode('UTF-8'), 'plain', 'UTF-8'))
    return send_raw_email(kindle_mail, msg)


def send_mail(book_id, kindle_mail, calibrepath):
    """Send email with attachments"""
    # create MIME message
    msg = MIMEMultipart()
    msg['Subject'] = _(u'Send to Kindle')
    msg['Message-Id'] = make_msgid('calibre-web')
    msg['Date'] = formatdate(localtime=True)
    text = _(u'This email has been sent via calibre web.')
    msg.attach(MIMEText(text.encode('UTF-8'), 'plain', 'UTF-8'))

    book = db.session.query(db.Books).filter(db.Books.id == book_id).first()
    data = db.session.query(db.Data).filter(db.Data.book == book.id)

    formats = {}

    for entry in data:
        if entry.format == "MOBI":
            formats["mobi"] = os.path.join(calibrepath, book.path, entry.name + ".mobi")
        if entry.format == "EPUB":
            formats["epub"] = os.path.join(calibrepath, book.path, entry.name + ".epub")
        if entry.format == "PDF":
            formats["pdf"] = os.path.join(calibrepath, book.path, entry.name + ".pdf")

    if len(formats) == 0:
        return _("Could not find any formats suitable for sending by email")

    if 'mobi' in formats:
        msg.attach(get_attachment(formats['mobi']))
    elif 'epub' in formats:
        data, resultCode = make_mobi(book.id, calibrepath)
        if resultCode == RET_SUCCESS:
            msg.attach(get_attachment(data))
        else:
            app.logger.error = data
            return data  # _("Could not convert epub to mobi")
    elif 'pdf' in formats:
        msg.attach(get_attachment(formats['pdf']))
    else:
        return _("Could not find any formats suitable for sending by email")

    return send_raw_email(kindle_mail, msg)


def get_attachment(file_path):
    """Get file as MIMEBase message"""

    try:
        file_ = open(file_path, 'rb')
        attachment = MIMEBase('application', 'octet-stream')
        attachment.set_payload(file_.read())
        file_.close()
        encoders.encode_base64(attachment)

        attachment.add_header('Content-Disposition', 'attachment',
                              filename=os.path.basename(file_path))
        return attachment
    except IOError:
        traceback.print_exc()
        app.logger.error = u'The requested file could not be read. Maybe wrong permissions?'
        return None


def get_valid_filename(value, replace_whitespace=True):
    """
    Returns the given string converted to a string that can be used for a clean
    filename. Limits num characters to 128 max.
    """
    if value[-1:] == u'.':
        value = value[:-1]+u'_'
    value = value.replace("/", "_").replace(":", "_").strip('\0')
    if use_unidecode:
        value = (unidecode.unidecode(value)).strip()
    else:
        value = value.replace(u'§', u'SS')
        value = value.replace(u'ß', u'ss')
        value = unicodedata.normalize('NFKD', value)
        re_slugify = re.compile('[\W\s-]', re.UNICODE)
        if isinstance(value, str):  # Python3 str, Python2 unicode
            value = re_slugify.sub('', value).strip()
        else:
            value = unicode(re_slugify.sub('', value).strip())
    if replace_whitespace:
        #  *+:\"/<>? are replaced by _
        value = re.sub(r'[\*\+:\\\"/<>\?]+', u'_', value, flags=re.U)
        # pipe has to be replaced with comma
        value = re.sub(r'[\|]+', u',', value, flags=re.U)
    value = value[:128]
    if not value:
        raise ValueError("Filename cannot be empty")

    return value


def get_sorted_author(value):
    try:
        regexes = ["^(JR|SR)\.?$", "^I{1,3}\.?$", "^IV\.?$"]
        combined = "(" + ")|(".join(regexes) + ")"
        value = value.split(" ")
        if re.match(combined, value[-1].upper()):
            value2 = value[-2] + ", " + " ".join(value[:-2]) + " " + value[-1]
        else:
            value2 = value[-1] + ", " + " ".join(value[:-1])
    except Exception:
        logging.getLogger('cps.web').error("Sorting author " + str(value) + "failed")
        value2 = value
    return value2


def delete_book(book, calibrepath):
    if "/" in book.path:
        path = os.path.join(calibrepath, book.path)
        shutil.rmtree(path, ignore_errors=True)
    else:
        logging.getLogger('cps.web').error("Deleting book " + str(book.id) + " failed, book path value: "+ book.path)

# ToDo: Implement delete book on gdrive
def delete_book_gdrive(book):
    pass


def update_dir_stucture(book_id, calibrepath):
    localbook = db.session.query(db.Books).filter(db.Books.id == book_id).first()
    path = os.path.join(calibrepath, localbook.path)

    authordir = localbook.path.split('/')[0]
    new_authordir = get_valid_filename(localbook.authors[0].name)

    titledir = localbook.path.split('/')[1]
    new_titledir = get_valid_filename(localbook.title) + " (" + str(book_id) + ")"

    if titledir != new_titledir:
        try:
            new_title_path = os.path.join(os.path.dirname(path), new_titledir)
            os.renames(path, new_title_path)
            path = new_title_path
            localbook.path = localbook.path.split('/')[0] + '/' + new_titledir
        except OSError as ex:
            logging.getLogger('cps.web').error("Rename title from: " + path + " to " + new_title_path)
            logging.getLogger('cps.web').error(ex, exc_info=True)
            return _('Rename title from: "%s" to "%s" failed with error: %s' % (path, new_title_path, str(ex)))
    if authordir != new_authordir:
        try:
            new_author_path = os.path.join(os.path.join(calibrepath, new_authordir), os.path.basename(path))
            os.renames(path, new_author_path)
            localbook.path = new_authordir + '/' + localbook.path.split('/')[1]
        except OSError as ex:
            logging.getLogger('cps.web').error("Rename author from: " + path + " to " + new_author_path)
            logging.getLogger('cps.web').error(ex, exc_info=True)
            return _('Rename author from: "%s" to "%s" failed with error: %s' % (path, new_title_path, str(ex)))
    return False


def update_dir_structure_gdrive(book_id):
    error = False
    book = db.session.query(db.Books).filter(db.Books.id == book_id).first()

    authordir = book.path.split('/')[0]
    new_authordir = get_valid_filename(book.authors[0].name)
    titledir = book.path.split('/')[1]
    new_titledir = get_valid_filename(book.title) + " (" + str(book_id) + ")"

    if titledir != new_titledir:
        print (titledir)
        gFile = gd.getFileFromEbooksFolder(web.Gdrive.Instance().drive, os.path.dirname(book.path), titledir)
        gFile['title'] = new_titledir
        gFile.Upload()
        book.path = book.path.split('/')[0] + '/' + new_titledir

    if authordir != new_authordir:
        gFile = gd.getFileFromEbooksFolder(web.Gdrive.Instance().drive, None, authordir)
        gFile['title'] = new_authordir
        gFile.Upload()
        book.path = new_authordir + '/' + book.path.split('/')[1]
    return error


class Updater(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.status = 0

    def run(self):
        global global_task
        self.status = 1
        r = requests.get('https://api.github.com/repos/janeczku/calibre-web/zipball/master', stream=True)
        fname = re.findall("filename=(.+)", r.headers['content-disposition'])[0]
        self.status = 2
        z = zipfile.ZipFile(StringIO(r.content))
        self.status = 3
        tmp_dir = gettempdir()
        z.extractall(tmp_dir)
        self.status = 4
        self.update_source(os.path.join(tmp_dir, os.path.splitext(fname)[0]), ub.config.get_main_dir)
        self.status = 5
        global_task = 0
        db.session.close()
        db.engine.dispose()
        ub.session.close()
        ub.engine.dispose()
        self.status = 6

        if web.gevent_server:
            web.gevent_server.stop()
        else:
            # stop tornado server
            server = IOLoop.instance()
            server.add_callback(server.stop)
        self.status = 7

    def get_update_status(self):
        return self.status

    @classmethod
    def file_to_list(self, filelist):
        return [x.strip() for x in open(filelist, 'r') if not x.startswith('#EXT')]

    @classmethod
    def one_minus_two(self, one, two):
        return [x for x in one if x not in set(two)]

    @classmethod
    def reduce_dirs(self, delete_files, new_list):
        new_delete = []
        for filename in delete_files:
            parts = filename.split(os.sep)
            sub = ''
            for part in parts:
                sub = os.path.join(sub, part)
                if sub == '':
                    sub = os.sep
                count = 0
                for song in new_list:
                    if song.startswith(sub):
                        count += 1
                        break
                if count == 0:
                    if sub != '\\':
                        new_delete.append(sub)
                    break
        return list(set(new_delete))

    @classmethod
    def reduce_files(self, remove_items, exclude_items):
        rf = []
        for item in remove_items:
            if not item.startswith(exclude_items):
                rf.append(item)
        return rf

    @classmethod
    def moveallfiles(self, root_src_dir, root_dst_dir):
        change_permissions = True
        if sys.platform == "win32" or sys.platform == "darwin":
            change_permissions = False
        else:
            logging.getLogger('cps.web').debug('Update on OS-System : ' + sys.platform)
            new_permissions = os.stat(root_dst_dir)
            # print new_permissions
        for src_dir, __, files in os.walk(root_src_dir):
            dst_dir = src_dir.replace(root_src_dir, root_dst_dir, 1)
            if not os.path.exists(dst_dir):
                os.makedirs(dst_dir)
                logging.getLogger('cps.web').debug('Create-Dir: '+dst_dir)
                if change_permissions:
                    # print('Permissions: User '+str(new_permissions.st_uid)+' Group '+str(new_permissions.st_uid))
                    os.chown(dst_dir, new_permissions.st_uid, new_permissions.st_gid)
            for file_ in files:
                src_file = os.path.join(src_dir, file_)
                dst_file = os.path.join(dst_dir, file_)
                if os.path.exists(dst_file):
                    if change_permissions:
                        permission = os.stat(dst_file)
                    logging.getLogger('cps.web').debug('Remove file before copy: '+dst_file)
                    os.remove(dst_file)
                else:
                    if change_permissions:
                        permission = new_permissions
                shutil.move(src_file, dst_dir)
                logging.getLogger('cps.web').debug('Move File '+src_file+' to '+dst_dir)
                if change_permissions:
                    try:
                        os.chown(dst_file, permission.st_uid, permission.st_gid)
                    except Exception:
                        # ex = sys.exc_info()
                        old_permissions = os.stat(dst_file)
                        logging.getLogger('cps.web').debug('Fail change permissions of ' + str(dst_file) + '. Before: '
                            + str(old_permissions.st_uid) + ':' + str(old_permissions.st_gid) + ' After: '
                            + str(permission.st_uid) + ':' + str(permission.st_gid) + ' error: '+str(e))
        return

    def update_source(self, source, destination):
        # destination files
        old_list = list()
        exclude = (
            'vendor' + os.sep + 'kindlegen.exe', 'vendor' + os.sep + 'kindlegen', os.sep + 'app.db',
            os.sep + 'vendor', os.sep + 'calibre-web.log')
        for root, dirs, files in os.walk(destination, topdown=True):
            for name in files:
                old_list.append(os.path.join(root, name).replace(destination, ''))
            for name in dirs:
                old_list.append(os.path.join(root, name).replace(destination, ''))
        # source files
        new_list = list()
        for root, dirs, files in os.walk(source, topdown=True):
            for name in files:
                new_list.append(os.path.join(root, name).replace(source, ''))
            for name in dirs:
                new_list.append(os.path.join(root, name).replace(source, ''))

        delete_files = self.one_minus_two(old_list, new_list)

        rf = self.reduce_files(delete_files, exclude)

        remove_items = self.reduce_dirs(rf, new_list)

        self.moveallfiles(source, destination)

        for item in remove_items:
            item_path = os.path.join(destination, item[1:])
            if os.path.isdir(item_path):
                logging.getLogger('cps.web').debug("Delete dir " + item_path)
                shutil.rmtree(item_path)
            else:
                try:
                    logging.getLogger('cps.web').debug("Delete file " + item_path)
                    # log_from_thread("Delete file " + item_path)
                    os.remove(item_path)
                except Exception:
                    logging.getLogger('cps.web').debug("Could not remove:" + item_path)
        shutil.rmtree(source, ignore_errors=True)
