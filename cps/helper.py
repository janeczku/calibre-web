# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2012-2019 cervinko, idalin, SiphonSquirrel, ouzklcn, akushsky,
#                            OzzieIsaacs, bodybybuddha, jkrehm, matthazinski, janeczku
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

from __future__ import division, print_function, unicode_literals
import sys
import os
import io
import json
import mimetypes
import re
import shutil
import time
import unicodedata
from datetime import datetime, timedelta
from tempfile import gettempdir

import requests
from babel.dates import format_datetime
from babel.units import format_unit
from flask import send_from_directory, make_response, redirect, abort
from flask_babel import gettext as _
from flask_login import current_user
from sqlalchemy.sql.expression import true, false, and_, or_, text, func
from werkzeug.datastructures import Headers
from werkzeug.security import generate_password_hash
from . import calibre_db

try:
    from urllib.parse import quote
except ImportError:
    from urllib import quote

try:
    import unidecode
    use_unidecode = True
except ImportError:
    use_unidecode = False

try:
    from PIL import Image as PILImage
    from PIL import UnidentifiedImageError
    use_PIL = True
except ImportError:
    use_PIL = False

from . import logger, config, get_locale, db, ub, isoLanguages, worker
from . import gdriveutils as gd
from .constants import STATIC_DIR as _STATIC_DIR
from .pagination import Pagination
from .subproc_wrapper import process_wait
from .worker import STAT_WAITING, STAT_FAIL, STAT_STARTED, STAT_FINISH_SUCCESS
from .worker import TASK_EMAIL, TASK_CONVERT, TASK_UPLOAD, TASK_CONVERT_ANY


log = logger.create()


# Convert existing book entry to new format
def convert_book_format(book_id, calibrepath, old_book_format, new_book_format, user_id, kindle_mail=None):
    book = calibre_db.get_book(book_id)
    data = calibre_db.get_book_format(book.id, old_book_format)
    if not data:
        error_message = _(u"%(format)s format not found for book id: %(book)d", format=old_book_format, book=book_id)
        log.error("convert_book_format: %s", error_message)
        return error_message
    if config.config_use_google_drive:
        df = gd.getFileFromEbooksFolder(book.path, data.name + "." + old_book_format.lower())
        if df:
            datafile = os.path.join(calibrepath, book.path, data.name + u"." + old_book_format.lower())
            if not os.path.exists(os.path.join(calibrepath, book.path)):
                os.makedirs(os.path.join(calibrepath, book.path))
            df.GetContentFile(datafile)
        else:
            error_message = _(u"%(format)s not found on Google Drive: %(fn)s",
                              format=old_book_format, fn=data.name + "." + old_book_format.lower())
            return error_message
    file_path = os.path.join(calibrepath, book.path, data.name)
    if os.path.exists(file_path + "." + old_book_format.lower()):
        # read settings and append converter task to queue
        if kindle_mail:
            settings = config.get_mail_settings()
            settings['subject'] = _('Send to Kindle')  # pretranslate Subject for e-mail
            settings['body'] = _(u'This e-mail has been sent via Calibre-Web.')
            # text = _(u"%(format)s: %(book)s", format=new_book_format, book=book.title)
        else:
            settings = dict()
        text = (u"%s -> %s: %s" % (old_book_format, new_book_format, book.title))
        settings['old_book_format'] = old_book_format
        settings['new_book_format'] = new_book_format
        worker.add_convert(file_path, book.id, user_id, text, settings, kindle_mail)
        return None
    else:
        error_message = _(u"%(format)s not found: %(fn)s",
                          format=old_book_format, fn=data.name + "." + old_book_format.lower())
        return error_message


def send_test_mail(kindle_mail, user_name):
    worker.add_email(_(u'Calibre-Web test e-mail'), None, None,
                     config.get_mail_settings(), kindle_mail, user_name,
                     _(u"Test e-mail"), _(u'This e-mail has been sent via Calibre-Web.'))
    return


# Send registration email or password reset email, depending on parameter resend (False means welcome email)
def send_registration_mail(e_mail, user_name, default_password, resend=False):
    text = "Hello %s!\r\n" % user_name
    if not resend:
        text += "Your new account at Calibre-Web has been created. Thanks for joining us!\r\n"
    text += "Please log in to your account using the following informations:\r\n"
    text += "User name: %s\r\n" % user_name
    text += "Password: %s\r\n" % default_password
    text += "Don't forget to change your password after first login.\r\n"
    text += "Sincerely\r\n\r\n"
    text += "Your Calibre-Web team"
    worker.add_email(_(u'Get Started with Calibre-Web'), None, None,
                     config.get_mail_settings(), e_mail, None,
                     _(u"Registration e-mail for user: %(name)s", name=user_name), text)
    return


def check_send_to_kindle(entry):
    """
        returns all available book formats for sending to Kindle
    """
    if len(entry.data):
        bookformats = list()
        if not config.config_converterpath:
            # no converter - only for mobi and pdf formats
            for ele in iter(entry.data):
                if ele.uncompressed_size < config.mail_size:
                    if 'MOBI' in ele.format:
                        bookformats.append({'format': 'Mobi',
                                            'convert': 0,
                                            'text': _('Send %(format)s to Kindle', format='Mobi')})
                    if 'PDF' in ele.format:
                        bookformats.append({'format': 'Pdf',
                                            'convert': 0,
                                            'text': _('Send %(format)s to Kindle', format='Pdf')})
                    if 'AZW' in ele.format:
                        bookformats.append({'format': 'Azw',
                                            'convert': 0,
                                            'text': _('Send %(format)s to Kindle', format='Azw')})
        else:
            formats = list()
            for ele in iter(entry.data):
                if ele.uncompressed_size < config.mail_size:
                    formats.append(ele.format)
            if 'MOBI' in formats:
                bookformats.append({'format': 'Mobi',
                                    'convert': 0,
                                    'text': _('Send %(format)s to Kindle', format='Mobi')})
            if 'AZW' in formats:
                bookformats.append({'format': 'Azw',
                                    'convert': 0,
                                    'text': _('Send %(format)s to Kindle', format='Azw')})
            if 'PDF' in formats:
                bookformats.append({'format': 'Pdf',
                                    'convert': 0,
                                    'text': _('Send %(format)s to Kindle', format='Pdf')})
            if config.config_converterpath:
                if 'EPUB' in formats and not 'MOBI' in formats:
                    bookformats.append({'format': 'Mobi',
                                        'convert':1,
                                        'text': _('Convert %(orig)s to %(format)s and send to Kindle',
                                                  orig='Epub',
                                                  format='Mobi')})
                if 'AZW3' in formats and not 'MOBI' in formats:
                    bookformats.append({'format': 'Mobi',
                                        'convert': 2,
                                        'text': _('Convert %(orig)s to %(format)s and send to Kindle',
                                                  orig='Azw3',
                                                  format='Mobi')})
        return bookformats
    else:
        log.error(u'Cannot find book entry %d', entry.id)
        return None


# Check if a reader is existing for any of the book formats, if not, return empty list, otherwise return
# list with supported formats
def check_read_formats(entry):
    EXTENSIONS_READER = {'TXT', 'PDF', 'EPUB', 'CBZ', 'CBT', 'CBR'}
    bookformats = list()
    if len(entry.data):
        for ele in iter(entry.data):
            if ele.format.upper() in EXTENSIONS_READER:
                bookformats.append(ele.format.lower())
    return bookformats


# Files are processed in the following order/priority:
# 1: If Mobi file is existing, it's directly send to kindle email,
# 2: If Epub file is existing, it's converted and send to kindle email,
# 3: If Pdf file is existing, it's directly send to kindle email
def send_mail(book_id, book_format, convert, kindle_mail, calibrepath, user_id):
    """Send email with attachments"""
    book = calibre_db.get_book(book_id)

    if convert == 1:
        # returns None if success, otherwise errormessage
        return convert_book_format(book_id, calibrepath, u'epub', book_format.lower(), user_id, kindle_mail)
    if convert == 2:
        # returns None if success, otherwise errormessage
        return convert_book_format(book_id, calibrepath, u'azw3', book_format.lower(), user_id, kindle_mail)

    for entry in iter(book.data):
        if entry.format.upper() == book_format.upper():
            converted_file_name = entry.name + '.' + book_format.lower()
            worker.add_email(_(u"Send to Kindle"), book.path, converted_file_name,
                             config.get_mail_settings(), kindle_mail, user_id,
                             _(u"E-mail: %(book)s", book=book.title), _(u'This e-mail has been sent via Calibre-Web.'))
            return
    return _(u"The requested file could not be read. Maybe wrong permissions?")


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
        re_slugify = re.compile(r'[\W\s-]', re.UNICODE)
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
    if sys.version_info.major == 3:
        return value
    else:
        return value.decode('utf-8')


def get_sorted_author(value):
    try:
        if ',' not in value:
            regexes = [r"^(JR|SR)\.?$", r"^I{1,3}\.?$", r"^IV\.?$"]
            combined = "(" + ")|(".join(regexes) + ")"
            value = value.split(" ")
            if re.match(combined, value[-1].upper()):
                value2 = value[-2] + ", " + " ".join(value[:-2]) + " " + value[-1]
            elif len(value) == 1:
                value2 = value[0]
            else:
                value2 = value[-1] + ", " + " ".join(value[:-1])
        else:
            value2 = value
    except Exception as ex:
        log.error("Sorting author %s failed: %s", value, ex)
        value2 = value
    return value2


# Deletes a book fro the local filestorage, returns True if deleting is successfull, otherwise false
def delete_book_file(book, calibrepath, book_format=None):
    # check that path is 2 elements deep, check that target path has no subfolders
    if book.path.count('/') == 1:
        path = os.path.join(calibrepath, book.path)
        if book_format:
            for file in os.listdir(path):
                if file.upper().endswith("."+book_format):
                    os.remove(os.path.join(path, file))
            return True, None
        else:
            if os.path.isdir(path):
                if len(next(os.walk(path))[1]):
                    log.error("Deleting book %s failed, path has subfolders: %s", book.id, book.path)
                    return False , _("Deleting book %(id)s failed, path has subfolders: %(path)s",
                                     id=book.id,
                                     path=book.path)
                try:
                    for root, __, files in os.walk(path):
                        for f in files:
                            os.unlink(os.path.join(root, f))
                    shutil.rmtree(path)
                except (IOError, OSError) as e:
                    log.error("Deleting book %s failed: %s", book.id, e)
                    return False, _("Deleting book %(id)s failed: %(message)s", id=book.id, message=e)
                authorpath = os.path.join(calibrepath, os.path.split(book.path)[0])
                if not os.listdir(authorpath):
                    try:
                        shutil.rmtree(authorpath)
                    except (IOError, OSError) as e:
                        log.error("Deleting authorpath for book %s failed: %s", book.id, e)
                return True, None
            else:
                log.error("Deleting book %s failed, book path not valid: %s", book.id, book.path)
                return True, _("Deleting book %(id)s, book path not valid: %(path)s",
                                     id=book.id,
                                     path=book.path)


def update_dir_structure_file(book_id, calibrepath, first_author):
    localbook = calibre_db.get_book(book_id)
    path = os.path.join(calibrepath, localbook.path)

    authordir = localbook.path.split('/')[0]
    if first_author:
        new_authordir = get_valid_filename(first_author)
    else:
        new_authordir = get_valid_filename(localbook.authors[0].name)

    titledir = localbook.path.split('/')[1]
    new_titledir = get_valid_filename(localbook.title) + " (" + str(book_id) + ")"

    if titledir != new_titledir:
        new_title_path = os.path.join(os.path.dirname(path), new_titledir)
        try:
            if not os.path.exists(new_title_path):
                os.renames(path, new_title_path)
            else:
                log.info("Copying title: %s into existing: %s", path, new_title_path)
                for dir_name, __, file_list in os.walk(path):
                    for file in file_list:
                        os.renames(os.path.join(dir_name, file),
                                   os.path.join(new_title_path + dir_name[len(path):], file))
            path = new_title_path
            localbook.path = localbook.path.split('/')[0] + '/' + new_titledir
        except OSError as ex:
            log.error("Rename title from: %s to %s: %s", path, new_title_path, ex)
            log.debug(ex, exc_info=True)
            return _("Rename title from: '%(src)s' to '%(dest)s' failed with error: %(error)s",
                     src=path, dest=new_title_path, error=str(ex))
    if authordir != new_authordir:
        new_author_path = os.path.join(calibrepath, new_authordir, os.path.basename(path))
        try:
            os.renames(path, new_author_path)
            localbook.path = new_authordir + '/' + localbook.path.split('/')[1]
        except OSError as ex:
            log.error("Rename author from: %s to %s: %s", path, new_author_path, ex)
            log.debug(ex, exc_info=True)
            return _("Rename author from: '%(src)s' to '%(dest)s' failed with error: %(error)s",
                     src=path, dest=new_author_path, error=str(ex))
    # Rename all files from old names to new names
    if authordir != new_authordir or titledir != new_titledir:
        try:
            new_name = get_valid_filename(localbook.title) + ' - ' + get_valid_filename(new_authordir)
            path_name = os.path.join(calibrepath, new_authordir, os.path.basename(path))
            for file_format in localbook.data:
                os.renames(os.path.join(path_name, file_format.name + '.' + file_format.format.lower()),
                           os.path.join(path_name, new_name + '.' + file_format.format.lower()))
                file_format.name = new_name
        except OSError as ex:
            log.error("Rename file in path %s to %s: %s", path, new_name, ex)
            log.debug(ex, exc_info=True)
            return _("Rename file in path '%(src)s' to '%(dest)s' failed with error: %(error)s",
                     src=path, dest=new_name, error=str(ex))
    return False


def update_dir_structure_gdrive(book_id, first_author):
    error = False
    book = calibre_db.get_book(book_id)
    path = book.path

    authordir = book.path.split('/')[0]
    if first_author:
        new_authordir = get_valid_filename(first_author)
    else:
        new_authordir = get_valid_filename(book.authors[0].name)
    titledir = book.path.split('/')[1]
    new_titledir = get_valid_filename(book.title) + u" (" + str(book_id) + u")"

    if titledir != new_titledir:
        gFile = gd.getFileFromEbooksFolder(os.path.dirname(book.path), titledir)
        if gFile:
            gFile['title'] = new_titledir
            gFile.Upload()
            book.path = book.path.split('/')[0] + u'/' + new_titledir
            path = book.path
            gd.updateDatabaseOnEdit(gFile['id'], book.path)     # only child folder affected
        else:
            error = _(u'File %(file)s not found on Google Drive', file=book.path)  # file not found

    if authordir != new_authordir:
        gFile = gd.getFileFromEbooksFolder(os.path.dirname(book.path), new_titledir)
        if gFile:
            gd.moveGdriveFolderRemote(gFile, new_authordir)
            book.path = new_authordir + u'/' + book.path.split('/')[1]
            path = book.path
            gd.updateDatabaseOnEdit(gFile['id'], book.path)
        else:
            error = _(u'File %(file)s not found on Google Drive', file=authordir)  # file not found
    # Rename all files from old names to new names

    if authordir != new_authordir or titledir != new_titledir:
        new_name = get_valid_filename(book.title) + u' - ' + get_valid_filename(new_authordir)
        for file_format in book.data:
            gFile = gd.getFileFromEbooksFolder(path, file_format.name + u'.' + file_format.format.lower())
            if not gFile:
                error = _(u'File %(file)s not found on Google Drive', file=file_format.name)  # file not found
                break
            gd.moveGdriveFileRemote(gFile, new_name + u'.' + file_format.format.lower())
            file_format.name = new_name
    return error


def delete_book_gdrive(book, book_format):
    error = None
    if book_format:
        name = ''
        for entry in book.data:
            if entry.format.upper() == book_format:
                name = entry.name + '.' + book_format
        gFile = gd.getFileFromEbooksFolder(book.path, name)
    else:
        gFile = gd.getFileFromEbooksFolder(os.path.dirname(book.path), book.path.split('/')[1])
    if gFile:
        gd.deleteDatabaseEntry(gFile['id'])
        gFile.Trash()
    else:
        error = _(u'Book path %(path)s not found on Google Drive', path=book.path)  # file not found

    return error is None, error


def reset_password(user_id):
    existing_user = ub.session.query(ub.User).filter(ub.User.id == user_id).first()
    if not existing_user:
        return 0, None
    if not config.get_mail_server_configured():
        return 2, None
    try:
        password = generate_random_password()
        existing_user.password = generate_password_hash(password)
        ub.session.commit()
        send_registration_mail(existing_user.email, existing_user.nickname, password, True)
        return 1, existing_user.nickname
    except Exception:
        ub.session.rollback()
        return 0, None


def generate_random_password():
    s = "abcdefghijklmnopqrstuvwxyz01234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ!@#$%&*()?"
    passlen = 8
    return "".join(s[c % len(s)] for c in os.urandom(passlen))

################################## External interface


def update_dir_stucture(book_id, calibrepath, first_author=None):
    if config.config_use_google_drive:
        return update_dir_structure_gdrive(book_id, first_author)
    else:
        return update_dir_structure_file(book_id, calibrepath, first_author)


def delete_book(book, calibrepath, book_format):
    if config.config_use_google_drive:
        return delete_book_gdrive(book, book_format)
    else:
        return delete_book_file(book, calibrepath, book_format)


def get_cover_on_failure(use_generic_cover):
    if use_generic_cover:
        return send_from_directory(_STATIC_DIR, "generic_cover.jpg")
    else:
        return None


def get_book_cover(book_id):
    book = calibre_db.get_filtered_book(book_id, allow_show_archived=True)
    return get_book_cover_internal(book, use_generic_cover_on_failure=True)


def get_book_cover_with_uuid(book_uuid,
                             use_generic_cover_on_failure=True):
    book = calibre_db.get_book_by_uuid(book_uuid)
    return get_book_cover_internal(book, use_generic_cover_on_failure)


def get_book_cover_internal(book, use_generic_cover_on_failure):
    if book and book.has_cover:
        if config.config_use_google_drive:
            try:
                if not gd.is_gdrive_ready():
                    return get_cover_on_failure(use_generic_cover_on_failure)
                path = gd.get_cover_via_gdrive(book.path)
                if path:
                    return redirect(path)
                else:
                    log.error('%s/cover.jpg not found on Google Drive', book.path)
                    return get_cover_on_failure(use_generic_cover_on_failure)
            except Exception as e:
                log.exception(e)
                # traceback.print_exc()
                return get_cover_on_failure(use_generic_cover_on_failure)
        else:
            cover_file_path = os.path.join(config.config_calibre_dir, book.path)
            if os.path.isfile(os.path.join(cover_file_path, "cover.jpg")):
                return send_from_directory(cover_file_path, "cover.jpg")
            else:
                return get_cover_on_failure(use_generic_cover_on_failure)
    else:
        return get_cover_on_failure(use_generic_cover_on_failure)


# saves book cover from url
def save_cover_from_url(url, book_path):
    try:
        img = requests.get(url, timeout=(10, 200))      # ToDo: Error Handling
        img.raise_for_status()
        return save_cover(img, book_path)
    except (requests.exceptions.HTTPError,
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout) as ex:
        log.info(u'Cover Download Error %s', ex)
        return False, _("Error Downloading Cover")
    except UnidentifiedImageError as ex:
        log.info(u'File Format Error %s', ex)
        return False, _("Cover Format Error")



def save_cover_from_filestorage(filepath, saved_filename, img):
    if hasattr(img, '_content'):
        f = open(os.path.join(filepath, saved_filename), "wb")
        f.write(img._content)
        f.close()
    else:
        # check if file path exists, otherwise create it, copy file to calibre path and delete temp file
        if not os.path.exists(filepath):
            try:
                os.makedirs(filepath)
            except OSError:
                log.error(u"Failed to create path for cover")
                return False, _(u"Failed to create path for cover")
        try:
            img.save(os.path.join(filepath, saved_filename))
        except (IOError, OSError):
            log.error(u"Cover-file is not a valid image file, or could not be stored")
            return False, _(u"Cover-file is not a valid image file, or could not be stored")
    return True, None


# saves book cover to gdrive or locally
def save_cover(img, book_path):
    content_type = img.headers.get('content-type')

    if use_PIL:
        if content_type not in ('image/jpeg', 'image/png', 'image/webp'):
            log.error("Only jpg/jpeg/png/webp files are supported as coverfile")
            return False, _("Only jpg/jpeg/png/webp files are supported as coverfile")
        # convert to jpg because calibre only supports jpg
        if content_type in ('image/png', 'image/webp'):
            if hasattr(img, 'stream'):
                imgc = PILImage.open(img.stream)
            else:
                imgc = PILImage.open(io.BytesIO(img.content))
            im = imgc.convert('RGB')
            tmp_bytesio = io.BytesIO()
            im.save(tmp_bytesio, format='JPEG')
            img._content = tmp_bytesio.getvalue()
    else:
        if content_type not in 'image/jpeg':
            log.error("Only jpg/jpeg files are supported as coverfile")
            return False, _("Only jpg/jpeg files are supported as coverfile")

    if config.config_use_google_drive:
        tmpDir = gettempdir()
        ret, message = save_cover_from_filestorage(tmpDir, "uploaded_cover.jpg", img)
        if ret is True:
            gd.uploadFileToEbooksFolder(os.path.join(book_path, 'cover.jpg'),
                                        os.path.join(tmpDir, "uploaded_cover.jpg"))
            log.info("Cover is saved on Google Drive")
            return True, None
        else:
            return False, message
    else:
        return save_cover_from_filestorage(os.path.join(config.config_calibre_dir, book_path), "cover.jpg", img)



def do_download_file(book, book_format, client, data, headers):
    if config.config_use_google_drive:
        startTime = time.time()
        df = gd.getFileFromEbooksFolder(book.path, data.name + "." + book_format)
        log.debug('%s', time.time() - startTime)
        if df:
            return gd.do_gdrive_download(df, headers)
        else:
            abort(404)
    else:
        filename = os.path.join(config.config_calibre_dir, book.path)
        if not os.path.isfile(os.path.join(filename, data.name + "." + book_format)):
            # ToDo: improve error handling
            log.error('File not found: %s', os.path.join(filename, data.name + "." + book_format))

        if client == "kobo" and book_format == "kepub":
            headers["Content-Disposition"] = headers["Content-Disposition"].replace(".kepub", ".kepub.epub")

        response = make_response(send_from_directory(filename, data.name + "." + book_format))
        # ToDo Check headers parameter
        for element in headers:
            response.headers[element[0]] = element[1]
        return response

##################################


def check_unrar(unrarLocation):
    if not unrarLocation:
        return

    if not os.path.exists(unrarLocation):
        return _('Unrar binary file not found')

    try:
        if sys.version_info < (3, 0):
            unrarLocation = unrarLocation.encode(sys.getfilesystemencoding())
        unrarLocation = [unrarLocation]
        for lines in process_wait(unrarLocation):
            value = re.search('UNRAR (.*) freeware', lines, re.IGNORECASE)
            if value:
                version = value.group(1)
                log.debug("unrar version %s", version)
                break
    except (OSError, UnicodeDecodeError) as err:
        log.exception(err)
        return _('Error excecuting UnRar')


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, timedelta):
        return {
            '__type__': 'timedelta',
            'days': obj.days,
            'seconds': obj.seconds,
            'microseconds': obj.microseconds,
        }
        # return obj.isoformat()
    raise TypeError("Type %s not serializable" % type(obj))


# helper function for displaying the runtime of tasks
def format_runtime(runtime):
    retVal = ""
    if runtime.days:
        retVal = format_unit(runtime.days, 'duration-day', length="long", locale=get_locale()) + ', '
    mins, seconds = divmod(runtime.seconds, 60)
    hours, minutes = divmod(mins, 60)
    # ToDo: locale.number_symbols._data['timeSeparator'] -> localize time separator ?
    if hours:
        retVal += '{:d}:{:02d}:{:02d}s'.format(hours, minutes, seconds)
    elif minutes:
        retVal += '{:2d}:{:02d}s'.format(minutes, seconds)
    else:
        retVal += '{:2d}s'.format(seconds)
    return retVal


# helper function to apply localize status information in tasklist entries
def render_task_status(tasklist):
    renderedtasklist = list()
    for task in tasklist:
        if task['user'] == current_user.nickname or current_user.role_admin():
            if task['formStarttime']:
                task['starttime'] = format_datetime(task['formStarttime'], format='short', locale=get_locale())
            # task2['formStarttime'] = ""
            else:
                if 'starttime' not in task:
                    task['starttime'] = ""

            if 'formRuntime' not in task:
                task['runtime'] = ""
            else:
                task['runtime'] = format_runtime(task['formRuntime'])

            # localize the task status
            if isinstance( task['stat'], int):
                if task['stat'] == STAT_WAITING:
                    task['status'] = _(u'Waiting')
                elif task['stat'] == STAT_FAIL:
                    task['status'] = _(u'Failed')
                elif task['stat'] == STAT_STARTED:
                    task['status'] = _(u'Started')
                elif task['stat'] == STAT_FINISH_SUCCESS:
                    task['status'] = _(u'Finished')
                else:
                    task['status'] = _(u'Unknown Status')

            # localize the task type
            if isinstance( task['taskType'], int):
                if task['taskType'] == TASK_EMAIL:
                    task['taskMessage'] = _(u'E-mail: ') + task['taskMess']
                elif task['taskType'] == TASK_CONVERT:
                    task['taskMessage'] = _(u'Convert: ') + task['taskMess']
                elif task['taskType'] == TASK_UPLOAD:
                    task['taskMessage'] = _(u'Upload: ') + task['taskMess']
                elif task['taskType'] == TASK_CONVERT_ANY:
                    task['taskMessage'] = _(u'Convert: ') + task['taskMess']
                else:
                    task['taskMessage'] = _(u'Unknown Task: ') + task['taskMess']

            renderedtasklist.append(task)

    return renderedtasklist


def tags_filters():
    negtags_list = current_user.list_denied_tags()
    postags_list = current_user.list_allowed_tags()
    neg_content_tags_filter = false() if negtags_list == [''] else db.Tags.name.in_(negtags_list)
    pos_content_tags_filter = true() if postags_list == [''] else db.Tags.name.in_(postags_list)
    return and_(pos_content_tags_filter, ~neg_content_tags_filter)


# checks if domain is in database (including wildcards)
# example SELECT * FROM @TABLE WHERE  'abcdefg' LIKE Name;
# from https://code.luasoftware.com/tutorials/flask/execute-raw-sql-in-flask-sqlalchemy/
def check_valid_domain(domain_text):
    # domain_text = domain_text.split('@', 1)[-1].lower()
    sql = "SELECT * FROM registration WHERE (:domain LIKE domain and allow = 1);"
    result = ub.session.query(ub.Registration).from_statement(text(sql)).params(domain=domain_text).all()
    if not len(result):
        return False
    sql = "SELECT * FROM registration WHERE (:domain LIKE domain and allow = 0);"
    result = ub.session.query(ub.Registration).from_statement(text(sql)).params(domain=domain_text).all()
    return not len(result)


def get_cc_columns(filter_config_custom_read=False):
    tmpcc = calibre_db.session.query(db.Custom_Columns)\
        .filter(db.Custom_Columns.datatype.notin_(db.cc_exceptions)).all()
    cc = []
    r = None
    if config.config_columns_to_ignore:
        r = re.compile(config.config_columns_to_ignore)

    for col in tmpcc:
        if filter_config_custom_read and config.config_read_column and config.config_read_column == col.id:
            continue
        if r and r.match(col.name):
            continue
        cc.append(col)

    return cc

def get_download_link(book_id, book_format, client):
    book_format = book_format.split(".")[0]
    book = calibre_db.get_filtered_book(book_id)
    if book:
        data1 = calibre_db.get_book_format(book.id, book_format.upper())
    else:
        abort(404)
    if data1:
        # collect downloaded books only for registered user and not for anonymous user
        if current_user.is_authenticated:
            ub.update_download(book_id, int(current_user.id))
        file_name = book.title
        if len(book.authors) > 0:
            file_name = book.authors[0].name + '_' + file_name
        file_name = get_valid_filename(file_name)
        headers = Headers()
        headers["Content-Type"] = mimetypes.types_map.get('.' + book_format, "application/octet-stream")
        headers["Content-Disposition"] = "attachment; filename=%s.%s; filename*=UTF-8''%s.%s" % (
            quote(file_name.encode('utf-8')), book_format, quote(file_name.encode('utf-8')), book_format)
        return do_download_file(book, book_format, client, data1, headers)
    else:
        abort(404)
