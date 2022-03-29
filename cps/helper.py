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

import os
import io
import sys
import mimetypes
import re
import shutil
import socket
from datetime import datetime, timedelta
from tempfile import gettempdir
import requests
import unidecode

from babel.dates import format_datetime
from babel.units import format_unit
from flask import send_from_directory, make_response, redirect, abort, url_for
from flask_babel import gettext as _
from flask_login import current_user
from sqlalchemy.sql.expression import true, false, and_, text, func
from sqlalchemy.exc import InvalidRequestError, OperationalError
from werkzeug.datastructures import Headers
from werkzeug.security import generate_password_hash
from markupsafe import escape
from urllib.parse import quote


try:
    import advocate
    from advocate.exceptions import UnacceptableAddressException
    use_advocate = True
except ImportError:
    use_advocate = False
    advocate = requests
    UnacceptableAddressException = MissingSchema = BaseException

from . import calibre_db, cli
from .tasks.convert import TaskConvert
from . import logger, config, get_locale, db, ub
from . import gdriveutils as gd
from .constants import STATIC_DIR as _STATIC_DIR
from .subproc_wrapper import process_wait
from .services.worker import WorkerThread, STAT_WAITING, STAT_FAIL, STAT_STARTED, STAT_FINISH_SUCCESS
from .tasks.mail import TaskEmail

log = logger.create()

try:
    from wand.image import Image
    from wand.exceptions import MissingDelegateError, BlobError
    use_IM = True
except (ImportError, RuntimeError) as e:
    log.debug('Cannot import Image, generating covers from non jpg files will not work: %s', e)
    use_IM = False
    MissingDelegateError = BaseException


# Convert existing book entry to new format
def convert_book_format(book_id, calibrepath, old_book_format, new_book_format, user_id, kindle_mail=None):
    book = calibre_db.get_book(book_id)
    data = calibre_db.get_book_format(book.id, old_book_format)
    file_path = os.path.join(calibrepath, book.path, data.name)
    if not data:
        error_message = _(u"%(format)s format not found for book id: %(book)d", format=old_book_format, book=book_id)
        log.error("convert_book_format: %s", error_message)
        return error_message
    if config.config_use_google_drive:
        if not gd.getFileFromEbooksFolder(book.path, data.name + "." + old_book_format.lower()):
            error_message = _(u"%(format)s not found on Google Drive: %(fn)s",
                              format=old_book_format, fn=data.name + "." + old_book_format.lower())
            return error_message
    else:
        if not os.path.exists(file_path + "." + old_book_format.lower()):
            error_message = _(u"%(format)s not found: %(fn)s",
                              format=old_book_format, fn=data.name + "." + old_book_format.lower())
            return error_message
    # read settings and append converter task to queue
    if kindle_mail:
        settings = config.get_mail_settings()
        settings['subject'] = _('Send to Kindle')  # pretranslate Subject for e-mail
        settings['body'] = _(u'This e-mail has been sent via Calibre-Web.')
    else:
        settings = dict()
    link = '<a href="{}">{}</a>'.format(url_for('web.show_book', book_id=book.id), escape(book.title))  # prevent xss
    txt = u"{} -> {}: {}".format(
           old_book_format.upper(),
           new_book_format.upper(),
           link)
    settings['old_book_format'] = old_book_format
    settings['new_book_format'] = new_book_format
    WorkerThread.add(user_id, TaskConvert(file_path, book.id, txt, settings, kindle_mail, user_id))
    return None


def send_test_mail(kindle_mail, user_name):
    WorkerThread.add(user_name, TaskEmail(_(u'Calibre-Web test e-mail'), None, None,
                     config.get_mail_settings(), kindle_mail, _(u"Test e-mail"),
                                          _(u'This e-mail has been sent via Calibre-Web.')))
    return


# Send registration email or password reset email, depending on parameter resend (False means welcome email)
def send_registration_mail(e_mail, user_name, default_password, resend=False):
    txt = "Hello %s!\r\n" % user_name
    if not resend:
        txt += "Your new account at Calibre-Web has been created. Thanks for joining us!\r\n"
    txt += "Please log in to your account using the following informations:\r\n"
    txt += "User name: %s\r\n" % user_name
    txt += "Password: %s\r\n" % default_password
    txt += "Don't forget to change your password after first login.\r\n"
    txt += "Sincerely\r\n\r\n"
    txt += "Your Calibre-Web team"
    WorkerThread.add(None, TaskEmail(
        subject=_(u'Get Started with Calibre-Web'),
        filepath=None,
        attachment=None,
        settings=config.get_mail_settings(),
        recipient=e_mail,
        taskMessage=_(u"Registration e-mail for user: %(name)s", name=user_name),
        text=txt
    ))
    return


def check_send_to_kindle_with_converter(formats):
    bookformats = list()
    if 'EPUB' in formats and 'MOBI' not in formats:
        bookformats.append({'format': 'Mobi',
                            'convert': 1,
                            'text': _('Convert %(orig)s to %(format)s and send to Kindle',
                                      orig='Epub',
                                      format='Mobi')})
    if 'AZW3' in formats and 'MOBI' not in formats:
        bookformats.append({'format': 'Mobi',
                            'convert': 2,
                            'text': _('Convert %(orig)s to %(format)s and send to Kindle',
                                      orig='Azw3',
                                      format='Mobi')})
    return bookformats


def check_send_to_kindle(entry):
    """
        returns all available book formats for sending to Kindle
    """
    formats = list()
    bookformats = list()
    if len(entry.data):
        for ele in iter(entry.data):
            if ele.uncompressed_size < config.mail_size:
                formats.append(ele.format)
        if 'MOBI' in formats:
            bookformats.append({'format': 'Mobi',
                                'convert': 0,
                                'text': _('Send %(format)s to Kindle', format='Mobi')})
        if 'PDF' in formats:
            bookformats.append({'format': 'Pdf',
                                'convert': 0,
                                'text': _('Send %(format)s to Kindle', format='Pdf')})
        if 'AZW' in formats:
            bookformats.append({'format': 'Azw',
                                'convert': 0,
                                'text': _('Send %(format)s to Kindle', format='Azw')})
        if config.config_converterpath:
            bookformats.extend(check_send_to_kindle_with_converter(formats))
        return bookformats
    else:
        log.error(u'Cannot find book entry %d', entry.id)
        return None


# Check if a reader is existing for any of the book formats, if not, return empty list, otherwise return
# list with supported formats
def check_read_formats(entry):
    extensions_reader = {'TXT', 'PDF', 'EPUB', 'CBZ', 'CBT', 'CBR', 'DJVU'}
    bookformats = list()
    if len(entry.data):
        for ele in iter(entry.data):
            if ele.format.upper() in extensions_reader:
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
            link = '<a href="{}">{}</a>'.format(url_for('web.show_book', book_id=book_id), escape(book.title))
            email_text = _(u"%(book)s send to Kindle", book=link)
            WorkerThread.add(user_id, TaskEmail(_(u"Send to Kindle"), book.path, converted_file_name,
                             config.get_mail_settings(), kindle_mail,
                             email_text, _(u'This e-mail has been sent via Calibre-Web.')))
            return
    return _(u"The requested file could not be read. Maybe wrong permissions?")


def shorten_component(s, by_what):
    l = len(s)
    if l < by_what:
        return s
    l = (l - by_what)//2
    if l <= 0:
        return s
    return s[:l] + s[-l:]


def get_valid_filename(value, replace_whitespace=True, chars=128):
    """
    Returns the given string converted to a string that can be used for a clean
    filename. Limits num characters to 128 max.
    """


    if value[-1:] == u'.':
        value = value[:-1]+u'_'
    value = value.replace("/", "_").replace(":", "_").strip('\0')
    if config.config_unicode_filename:
        value = (unidecode.unidecode(value))
    if replace_whitespace:
        #  *+:\"/<>? are replaced by _
        value = re.sub(r'[*+:\\\"/<>?]+', u'_', value, flags=re.U)
        # pipe has to be replaced with comma
        value = re.sub(r'[|]+', u',', value, flags=re.U)

    filename_encoding_for_length = 'utf-16' if sys.platform == "win32" or sys.platform == "darwin" else 'utf-8'
    value = value.encode(filename_encoding_for_length)[:chars].decode('utf-8', errors='ignore').strip()

    if not value:
        raise ValueError("Filename cannot be empty")
    return value


def split_authors(values):
    authors_list = []
    for value in values:
        authors = re.split('[&;]', value)
        for author in authors:
            commas = author.count(',')
            if commas == 1:
                author_split = author.split(',')
                authors_list.append(author_split[1].strip() + ' ' + author_split[0].strip())
            elif commas > 1:
                authors_list.extend([x.strip() for x in author.split(',')])
            else:
                authors_list.append(author.strip())
    return authors_list


def get_sorted_author(value):
    value2 = None
    try:
        if ',' not in value:
            regexes = [r"^(JR|SR)\.?$", r"^I{1,3}\.?$", r"^IV\.?$"]
            combined = "(" + ")|(".join(regexes) + ")"
            value = value.split(" ")
            if re.match(combined, value[-1].upper()):
                if len(value) > 1:
                    value2 = value[-2] + ", " + " ".join(value[:-2]) + " " + value[-1]
                else:
                    value2 = value[0]
            elif len(value) == 1:
                value2 = value[0]
            else:
                value2 = value[-1] + ", " + " ".join(value[:-1])
        else:
            value2 = value
    except Exception as ex:
        log.error("Sorting author %s failed: %s", value, ex)
        if isinstance(list, value2):
            value2 = value[0]
        else:
            value2 = value
    return value2


def edit_book_read_status(book_id, read_status=None):
    if not config.config_read_column:
        book = ub.session.query(ub.ReadBook).filter(and_(ub.ReadBook.user_id == int(current_user.id),
                                                         ub.ReadBook.book_id == book_id)).first()
        if book:
            if read_status is None:
                if book.read_status == ub.ReadBook.STATUS_FINISHED:
                    book.read_status = ub.ReadBook.STATUS_UNREAD
                else:
                    book.read_status = ub.ReadBook.STATUS_FINISHED
            else:
                book.read_status = ub.ReadBook.STATUS_FINISHED if read_status else ub.ReadBook.STATUS_UNREAD
        else:
            read_book = ub.ReadBook(user_id=current_user.id, book_id=book_id)
            read_book.read_status = ub.ReadBook.STATUS_FINISHED
            book = read_book
        if not book.kobo_reading_state:
            kobo_reading_state = ub.KoboReadingState(user_id=current_user.id, book_id=book_id)
            kobo_reading_state.current_bookmark = ub.KoboBookmark()
            kobo_reading_state.statistics = ub.KoboStatistics()
            book.kobo_reading_state = kobo_reading_state
        ub.session.merge(book)
        ub.session_commit("Book {} readbit toggled".format(book_id))
    else:
        try:
            calibre_db.update_title_sort(config)
            book = calibre_db.get_filtered_book(book_id)
            read_status = getattr(book, 'custom_column_' + str(config.config_read_column))
            if len(read_status):
                if read_status is None:
                    read_status[0].value = not read_status[0].value
                else:
                    read_status[0].value = read_status is True
                calibre_db.session.commit()
            else:
                cc_class = db.cc_classes[config.config_read_column]
                new_cc = cc_class(value=read_status or 1, book=book_id)
                calibre_db.session.add(new_cc)
                calibre_db.session.commit()
        except (KeyError, AttributeError, IndexError):
            log.error(
                "Custom Column No.{} is not existing in calibre database".format(config.config_read_column))
            return "Custom Column No.{} is not existing in calibre database".format(config.config_read_column)
        except (OperationalError, InvalidRequestError) as ex:
            calibre_db.session.rollback()
            log.error(u"Read status could not set: {}".format(ex))
            return _("Read status could not set: {}".format(ex.orig))
    return ""


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
                try:
                    for root, folders, files in os.walk(path):
                        for f in files:
                            os.unlink(os.path.join(root, f))
                        if len(folders):
                            log.warning("Deleting book {} failed, path {} has subfolders: {}".format(book.id,
                                        book.path, folders))
                            return True, _("Deleting bookfolder for book %(id)s failed, path has subfolders: %(path)s",
                                           id=book.id,
                                           path=book.path)
                    shutil.rmtree(path)
                except (IOError, OSError) as ex:
                    log.error("Deleting book %s failed: %s", book.id, ex)
                    return False, _("Deleting book %(id)s failed: %(message)s", id=book.id, message=ex)
                authorpath = os.path.join(calibrepath, os.path.split(book.path)[0])
                if not os.listdir(authorpath):
                    try:
                        shutil.rmtree(authorpath)
                    except (IOError, OSError) as ex:
                        log.error("Deleting authorpath for book %s failed: %s", book.id, ex)
                return True, None

    log.error("Deleting book %s from database only, book path in database not valid: %s",
              book.id, book.path)
    return True, _("Deleting book %(id)s from database only, book path in database not valid: %(path)s",
                   id=book.id,
                   path=book.path)


def clean_author_database(renamed_author, calibre_path="", local_book=None, gdrive=None):
    valid_filename_authors = [get_valid_filename(r, chars=96) for r in renamed_author]
    for r in renamed_author:
        if local_book:
            all_books = [local_book]
        else:
            all_books = calibre_db.session.query(db.Books) \
                .filter(db.Books.authors.any(db.Authors.name == r)).all()
        for book in all_books:
            book_author_path = book.path.split('/')[0]
            if book_author_path in valid_filename_authors or local_book:
                new_author = calibre_db.session.query(db.Authors).filter(db.Authors.name == r).first()
                all_new_authordir = get_valid_filename(new_author.name, chars=96)
                all_titledir = book.path.split('/')[1]
                all_new_path = os.path.join(calibre_path, all_new_authordir, all_titledir)
                all_new_name = get_valid_filename(book.title, chars=42) + ' - ' \
                    + get_valid_filename(new_author.name, chars=42)
                # change location in database to new author/title path
                book.path = os.path.join(all_new_authordir, all_titledir).replace('\\', '/')
                for file_format in book.data:
                    if not gdrive:
                        shutil.move(os.path.normcase(os.path.join(all_new_path,
                                                                  file_format.name + '.' + file_format.format.lower())),
                                    os.path.normcase(os.path.join(all_new_path,
                                                                  all_new_name + '.' + file_format.format.lower())))
                    else:
                        g_file = gd.getFileFromEbooksFolder(all_new_path,
                                                            file_format.name + '.' + file_format.format.lower())
                        if g_file:
                            gd.moveGdriveFileRemote(g_file, all_new_name + u'.' + file_format.format.lower())
                            gd.updateDatabaseOnEdit(g_file['id'], all_new_name + u'.' + file_format.format.lower())
                        else:
                            log.error("File {} not found on gdrive"
                                      .format(all_new_path, file_format.name + '.' + file_format.format.lower()))
                    file_format.name = all_new_name


def rename_all_authors(first_author, renamed_author, calibre_path="", localbook=None, gdrive=False):
    # Create new_author_dir from parameter or from database
    # Create new title_dir from database and add id
    if first_author:
        new_authordir = get_valid_filename(first_author, chars=96)
        for r in renamed_author:
            new_author = calibre_db.session.query(db.Authors).filter(db.Authors.name == r).first()
            old_author_dir = get_valid_filename(r, chars=96)
            new_author_rename_dir = get_valid_filename(new_author.name, chars=96)
            if gdrive:
                g_file = gd.getFileFromEbooksFolder(None, old_author_dir)
                if g_file:
                    gd.moveGdriveFolderRemote(g_file, new_author_rename_dir)
            else:
                if os.path.isdir(os.path.join(calibre_path, old_author_dir)):
                    try:
                        old_author_path = os.path.join(calibre_path, old_author_dir)
                        new_author_path = os.path.join(calibre_path, new_author_rename_dir)
                        shutil.move(os.path.normcase(old_author_path), os.path.normcase(new_author_path))
                    except OSError as ex:
                        log.error("Rename author from: %s to %s: %s", old_author_path, new_author_path, ex)
                        log.debug(ex, exc_info=True)
                        return _("Rename author from: '%(src)s' to '%(dest)s' failed with error: %(error)s",
                                 src=old_author_path, dest=new_author_path, error=str(ex))
    else:
        new_authordir = get_valid_filename(localbook.authors[0].name, chars=96)
    return new_authordir


# Moves files in file storage during author/title rename, or from temp dir to file storage
def update_dir_structure_file(book_id, calibre_path, first_author, original_filepath, db_filename, renamed_author):
    # get book database entry from id, if original path overwrite source with original_filepath
    local_book = calibre_db.get_book(book_id)
    if original_filepath:
        path = original_filepath
    else:
        path = os.path.join(calibre_path, local_book.path)

    # Create (current) author_dir and title_dir from database
    author_dir = local_book.path.split('/')[0]
    title_dir = local_book.path.split('/')[1]

    # Create new_author_dir from parameter or from database
    # Create new title_dir from database and add id
    new_author_dir = rename_all_authors(first_author, renamed_author, calibre_path, local_book)
    if first_author:
        if first_author.lower() in [r.lower() for r in renamed_author]:
            if os.path.isdir(os.path.join(calibre_path, new_author_dir)):
                path = os.path.join(calibre_path, new_author_dir, title_dir)

    new_title_dir = get_valid_filename(local_book.title, chars=96) + " (" + str(book_id) + ")"

    if title_dir != new_title_dir or author_dir != new_author_dir or original_filepath:
        error = move_files_on_change(calibre_path,
                                     new_author_dir,
                                     new_title_dir,
                                     local_book,
                                     db_filename,
                                     original_filepath,
                                     path)
        if error:
            return error

    # Rename all files from old names to new names
    return rename_files_on_change(first_author, renamed_author, local_book, original_filepath, path, calibre_path)


def upload_new_file_gdrive(book_id, first_author, renamed_author, title, title_dir, original_filepath, filename_ext):
    book = calibre_db.get_book(book_id)
    file_name = get_valid_filename(title, chars=42) + ' - ' + \
        get_valid_filename(first_author, chars=42) + filename_ext
    rename_all_authors(first_author, renamed_author, gdrive=True)
    gdrive_path = os.path.join(get_valid_filename(first_author, chars=96),
                               title_dir + " (" + str(book_id) + ")")
    book.path = gdrive_path.replace("\\", "/")
    gd.uploadFileToEbooksFolder(os.path.join(gdrive_path, file_name).replace("\\", "/"), original_filepath)
    return rename_files_on_change(first_author, renamed_author, local_book=book, gdrive=True)


def update_dir_structure_gdrive(book_id, first_author, renamed_author):
    book = calibre_db.get_book(book_id)

    authordir = book.path.split('/')[0]
    titledir = book.path.split('/')[1]
    new_authordir = rename_all_authors(first_author, renamed_author, gdrive=True)
    new_titledir = get_valid_filename(book.title, chars=96) + u" (" + str(book_id) + u")"

    if titledir != new_titledir:
        g_file = gd.getFileFromEbooksFolder(os.path.dirname(book.path), titledir)
        if g_file:
            gd.moveGdriveFileRemote(g_file, new_titledir)
            book.path = book.path.split('/')[0] + u'/' + new_titledir
            gd.updateDatabaseOnEdit(g_file['id'], book.path)     # only child folder affected
        else:
            return _(u'File %(file)s not found on Google Drive', file=book.path)  # file not found

    if authordir != new_authordir and authordir not in renamed_author:
        g_file = gd.getFileFromEbooksFolder(os.path.dirname(book.path), new_titledir)
        if g_file:
            gd.moveGdriveFolderRemote(g_file, new_authordir)
            book.path = new_authordir + u'/' + book.path.split('/')[1]
            gd.updateDatabaseOnEdit(g_file['id'], book.path)
        else:
            return _(u'File %(file)s not found on Google Drive', file=authordir)  # file not found

    # change location in database to new author/title path
    book.path = os.path.join(new_authordir, new_titledir).replace('\\', '/')
    return rename_files_on_change(first_author, renamed_author, book, gdrive=True)


def move_files_on_change(calibre_path, new_authordir, new_titledir, localbook, db_filename, original_filepath, path):
    new_path = os.path.join(calibre_path, new_authordir, new_titledir)
    new_name = get_valid_filename(localbook.title, chars=96) + ' - ' + new_authordir
    try:
        if original_filepath:
            if not os.path.isdir(new_path):
                os.makedirs(new_path)
            shutil.move(os.path.normcase(original_filepath), os.path.normcase(os.path.join(new_path, db_filename)))
            log.debug("Moving title: %s to %s/%s", original_filepath, new_path, new_name)
        else:
            # Check new path is not valid path
            if not os.path.exists(new_path):
                # move original path to new path
                log.debug("Moving title: %s to %s", path, new_path)
                shutil.move(os.path.normcase(path), os.path.normcase(new_path))
            else:  # path is valid copy only files to new location (merge)
                log.info("Moving title: %s into existing: %s", path, new_path)
                # Take all files and subfolder from old path (strange command)
                for dir_name, __, file_list in os.walk(path):
                    for file in file_list:
                        shutil.move(os.path.normcase(os.path.join(dir_name, file)),
                                    os.path.normcase(os.path.join(new_path + dir_name[len(path):], file)))
        # change location in database to new author/title path
        localbook.path = os.path.join(new_authordir, new_titledir).replace('\\', '/')
    except OSError as ex:
        log.error_or_exception("Rename title from {} to {} failed with error: {}".format(path, new_path, ex))
        return _("Rename title from: '%(src)s' to '%(dest)s' failed with error: %(error)s",
                 src=path, dest=new_path, error=str(ex))
    return False


def rename_files_on_change(first_author,
                           renamed_author,
                           local_book,
                           original_filepath="",
                           path="",
                           calibre_path="",
                           gdrive=False):
    # Rename all files from old names to new names
    try:
        clean_author_database(renamed_author, calibre_path, gdrive=gdrive)
        if first_author and first_author not in renamed_author:
            clean_author_database([first_author], calibre_path, local_book, gdrive)
        if not gdrive and not renamed_author and not original_filepath and len(os.listdir(os.path.dirname(path))) == 0:
            shutil.rmtree(os.path.dirname(path))
    except (OSError, FileNotFoundError) as ex:
        log.error_or_exception("Error in rename file in path {}".format(ex))
        return _("Error in rename file in path: {}".format(str(ex)))
    return False


def delete_book_gdrive(book, book_format):
    error = None
    if book_format:
        name = ''
        for entry in book.data:
            if entry.format.upper() == book_format:
                name = entry.name + '.' + book_format
        g_file = gd.getFileFromEbooksFolder(book.path, name)
    else:
        g_file = gd.getFileFromEbooksFolder(os.path.dirname(book.path), book.path.split('/')[1])
    if g_file:
        gd.deleteDatabaseEntry(g_file['id'])
        g_file.Trash()
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
        send_registration_mail(existing_user.email, existing_user.name, password, True)
        return 1, existing_user.name
    except Exception:
        ub.session.rollback()
        return 0, None


def generate_random_password():
    s = "abcdefghijklmnopqrstuvwxyz01234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ!@#$%&*()?"
    passlen = 8
    return "".join(s[c % len(s)] for c in os.urandom(passlen))


def uniq(inpt):
    output = []
    inpt = [" ".join(inp.split()) for inp in inpt]
    for x in inpt:
        if x not in output:
            output.append(x)
    return output


def check_email(email):
    email = valid_email(email)
    if ub.session.query(ub.User).filter(func.lower(ub.User.email) == email.lower()).first():
        log.error(u"Found an existing account for this e-mail address")
        raise Exception(_(u"Found an existing account for this e-mail address"))
    return email


def check_username(username):
    username = username.strip()
    if ub.session.query(ub.User).filter(func.lower(ub.User.name) == username.lower()).scalar():
        log.error(u"This username is already taken")
        raise Exception(_(u"This username is already taken"))
    return username


def valid_email(email):
    email = email.strip()
    # Regex according to https://developer.mozilla.org/en-US/docs/Web/HTML/Element/input/email#validation
    if not re.search(r"^[\w.!#$%&'*+\\/=?^_`{|}~-]+@[\w](?:[\w-]{0,61}[\w])?(?:\.[\w](?:[\w-]{0,61}[\w])?)*$",
                     email):
        log.error(u"Invalid e-mail address format")
        raise Exception(_(u"Invalid e-mail address format"))
    return email

# ################################# External interface #################################


def update_dir_structure(book_id,
                         calibre_path,
                         first_author=None,     # change author of book to this author
                         original_filepath=None,
                         db_filename=None,
                         renamed_author=None):
    renamed_author = renamed_author or []
    if config.config_use_google_drive:
        return update_dir_structure_gdrive(book_id, first_author, renamed_author)
    else:
        return update_dir_structure_file(book_id,
                                         calibre_path,
                                         first_author,
                                         original_filepath,
                                         db_filename, renamed_author)


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
                    log.error('{}/cover.jpg not found on Google Drive'.format(book.path))
                    return get_cover_on_failure(use_generic_cover_on_failure)
            except Exception as ex:
                log.error_or_exception(ex)
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
        if cli.allow_localhost:
            img = requests.get(url, timeout=(10, 200), allow_redirects=False)  # ToDo: Error Handling
        elif use_advocate:
            img = advocate.get(url, timeout=(10, 200), allow_redirects=False)      # ToDo: Error Handling
        else:
            log.error("python modul advocate is not installed but is needed")
            return False, _("Python modul 'advocate' is not installed but is needed for cover downloads")
        img.raise_for_status()
        return save_cover(img, book_path)
    except (socket.gaierror,
            requests.exceptions.HTTPError,
            requests.exceptions.InvalidURL,
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout) as ex:
        # "Invalid host" can be the result of a redirect response
        log.error(u'Cover Download Error %s', ex)
        return False, _("Error Downloading Cover")
    except MissingDelegateError as ex:
        log.info(u'File Format Error %s', ex)
        return False, _("Cover Format Error")
    except UnacceptableAddressException as e:
        log.error("Localhost or local network was accessed for cover upload")
        return False, _("You are not allowed to access localhost or the local network for cover uploads")


def save_cover_from_filestorage(filepath, saved_filename, img):
    # check if file path exists, otherwise create it, copy file to calibre path and delete temp file
    if not os.path.exists(filepath):
        try:
            os.makedirs(filepath)
        except OSError:
            log.error(u"Failed to create path for cover")
            return False, _(u"Failed to create path for cover")
    try:
        # upload of jgp file without wand
        if isinstance(img, requests.Response):
            with open(os.path.join(filepath, saved_filename), 'wb') as f:
                f.write(img.content)
        else:
            if hasattr(img, "metadata"):
                # upload of jpg/png... via url
                img.save(filename=os.path.join(filepath, saved_filename))
                img.close()
            else:
                # upload of jpg/png... from hdd
                img.save(os.path.join(filepath, saved_filename))
    except (IOError, OSError):
        log.error(u"Cover-file is not a valid image file, or could not be stored")
        return False, _(u"Cover-file is not a valid image file, or could not be stored")
    return True, None


# saves book cover to gdrive or locally
def save_cover(img, book_path):
    content_type = img.headers.get('content-type')

    if use_IM:
        if content_type not in ('image/jpeg', 'image/png', 'image/webp', 'image/bmp'):
            log.error("Only jpg/jpeg/png/webp/bmp files are supported as coverfile")
            return False, _("Only jpg/jpeg/png/webp/bmp files are supported as coverfile")
        # convert to jpg because calibre only supports jpg
        if content_type != 'image/jpg':
            try:
                if hasattr(img, 'stream'):
                    imgc = Image(blob=img.stream)
                else:
                    imgc = Image(blob=io.BytesIO(img.content))
                imgc.format = 'jpeg'
                imgc.transform_colorspace("rgb")
                img = imgc
            except (BlobError, MissingDelegateError):
                log.error("Invalid cover file content")
                return False, _("Invalid cover file content")
    else:
        if content_type not in 'image/jpeg':
            log.error("Only jpg/jpeg files are supported as coverfile")
            return False, _("Only jpg/jpeg files are supported as coverfile")

    if config.config_use_google_drive:
        tmp_dir = os.path.join(gettempdir(), 'calibre_web')

        if not os.path.isdir(tmp_dir):
            os.mkdir(tmp_dir)
        ret, message = save_cover_from_filestorage(tmp_dir, "uploaded_cover.jpg", img)
        if ret is True:
            gd.uploadFileToEbooksFolder(os.path.join(book_path, 'cover.jpg').replace("\\", "/"),
                                        os.path.join(tmp_dir, "uploaded_cover.jpg"))
            log.info("Cover is saved on Google Drive")
            return True, None
        else:
            return False, message
    else:
        return save_cover_from_filestorage(os.path.join(config.config_calibre_dir, book_path), "cover.jpg", img)


def do_download_file(book, book_format, client, data, headers):
    if config.config_use_google_drive:
        # startTime = time.time()
        df = gd.getFileFromEbooksFolder(book.path, data.name + "." + book_format)
        # log.debug('%s', time.time() - startTime)
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
        log.info('Downloading file: {}'.format(os.path.join(filename, data.name + "." + book_format)))
        return response

##################################


def check_unrar(unrar_location):
    if not unrar_location:
        return

    if not os.path.exists(unrar_location):
        return _('Unrar binary file not found')

    try:
        unrar_location = [unrar_location]
        value = process_wait(unrar_location, pattern='UNRAR (.*) freeware')
        if value:
            version = value.group(1)
            log.debug("unrar version %s", version)

    except (OSError, UnicodeDecodeError) as err:
        log.error_or_exception(err)
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
    raise TypeError("Type %s not serializable" % type(obj))


# helper function for displaying the runtime of tasks
def format_runtime(runtime):
    ret_val = ""
    if runtime.days:
        ret_val = format_unit(runtime.days, 'duration-day', length="long", locale=get_locale()) + ', '
    mins, seconds = divmod(runtime.seconds, 60)
    hours, minutes = divmod(mins, 60)
    # ToDo: locale.number_symbols._data['timeSeparator'] -> localize time separator ?
    if hours:
        ret_val += '{:d}:{:02d}:{:02d}s'.format(hours, minutes, seconds)
    elif minutes:
        ret_val += '{:2d}:{:02d}s'.format(minutes, seconds)
    else:
        ret_val += '{:2d}s'.format(seconds)
    return ret_val


# helper function to apply localize status information in tasklist entries
def render_task_status(tasklist):
    renderedtasklist = list()
    for __, user, __, task in tasklist:
        if user == current_user.name or current_user.role_admin():
            ret = {}
            if task.start_time:
                ret['starttime'] = format_datetime(task.start_time, format='short', locale=get_locale())
                ret['runtime'] = format_runtime(task.runtime)

            # localize the task status
            if isinstance(task.stat, int):
                if task.stat == STAT_WAITING:
                    ret['status'] = _(u'Waiting')
                elif task.stat == STAT_FAIL:
                    ret['status'] = _(u'Failed')
                elif task.stat == STAT_STARTED:
                    ret['status'] = _(u'Started')
                elif task.stat == STAT_FINISH_SUCCESS:
                    ret['status'] = _(u'Finished')
                else:
                    ret['status'] = _(u'Unknown Status')

            ret['taskMessage'] = "{}: {}".format(_(task.name), task.message)
            ret['progress'] = "{} %".format(int(task.progress * 100))
            ret['user'] = escape(user)  # prevent xss
            renderedtasklist.append(ret)

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
# in all calls the email address is checked for validity
def check_valid_domain(domain_text):
    sql = "SELECT * FROM registration WHERE (:domain LIKE domain and allow = 1);"
    result = ub.session.query(ub.Registration).from_statement(text(sql)).params(domain=domain_text).all()
    if not len(result):
        return False
    sql = "SELECT * FROM registration WHERE (:domain LIKE domain and allow = 0);"
    result = ub.session.query(ub.Registration).from_statement(text(sql)).params(domain=domain_text).all()
    return not len(result)


def get_download_link(book_id, book_format, client):
    book_format = book_format.split(".")[0]
    book = calibre_db.get_filtered_book(book_id, allow_show_archived=True)
    data1= ""
    if book:
        data1 = calibre_db.get_book_format(book.id, book_format.upper())
    else:
        log.error("Book id {} not found for downloading".format(book_id))
        abort(404)
    if data1:
        # collect downloaded books only for registered user and not for anonymous user
        if current_user.is_authenticated:
            ub.update_download(book_id, int(current_user.id))
        file_name = book.title
        if len(book.authors) > 0:
            file_name = file_name + ' - ' + book.authors[0].name
        file_name = get_valid_filename(file_name, replace_whitespace=False)
        headers = Headers()
        headers["Content-Type"] = mimetypes.types_map.get('.' + book_format, "application/octet-stream")
        headers["Content-Disposition"] = "attachment; filename=%s.%s; filename*=UTF-8''%s.%s" % (
            quote(file_name.encode('utf-8')), book_format, quote(file_name.encode('utf-8')), book_format)
        return do_download_file(book, book_format, client, data1, headers)
    else:
        abort(404)
