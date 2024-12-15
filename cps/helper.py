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
import random
import io
import mimetypes
import re
import regex
import shutil
import socket
from datetime import datetime, timedelta, timezone
import requests
import unidecode
from uuid import uuid4

from flask import send_from_directory, make_response, abort, url_for, Response, request
from flask_babel import gettext as _
from flask_babel import lazy_gettext as N_
from flask_babel import get_locale
from .cw_login import current_user
from sqlalchemy.sql.expression import true, false, and_, or_, text, func
from sqlalchemy.exc import InvalidRequestError, OperationalError
from werkzeug.datastructures import Headers
from werkzeug.security import generate_password_hash
from markupsafe import escape
from urllib.parse import quote

try:
    from . import cw_advocate
    from .cw_advocate.exceptions import UnacceptableAddressException
    use_advocate = True
except ImportError as e:
    use_advocate = False
    advocate = requests
    UnacceptableAddressException = MissingSchema = BaseException

from . import calibre_db, cli_param
from .string_helper import strip_whitespaces
from .tasks.convert import TaskConvert
from . import logger, config, db, ub, fs
from . import gdriveutils as gd
from .constants import (STATIC_DIR as _STATIC_DIR, CACHE_TYPE_THUMBNAILS, THUMBNAIL_TYPE_COVER, THUMBNAIL_TYPE_SERIES,
                        SUPPORTED_CALIBRE_BINARIES)
from .subproc_wrapper import process_wait
from .services.worker import WorkerThread
from .tasks.mail import TaskEmail
from .tasks.thumbnail import TaskClearCoverThumbnailCache, TaskGenerateCoverThumbnails
from .tasks.metadata_backup import TaskBackupMetadata
from .file_helper import get_temp_dir
from .epub_helper import get_content_opf, create_new_metadata_backup, updateEpub, replace_metadata
from .embed_helper import do_calibre_export

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
def convert_book_format(book_id, calibre_path, old_book_format, new_book_format, user_id, ereader_mail=None):
    book = calibre_db.get_book(book_id)
    data = calibre_db.get_book_format(book.id, old_book_format)
    if not data:
        error_message = _("%(format)s format not found for book id: %(book)d", format=old_book_format, book=book_id)
        log.error("convert_book_format: %s", error_message)
        return error_message
    file_path = os.path.join(calibre_path, book.path, data.name)
    if config.config_use_google_drive:
        if not gd.getFileFromEbooksFolder(book.path, data.name + "." + old_book_format.lower()):
            error_message = _("%(format)s not found on Google Drive: %(fn)s",
                              format=old_book_format, fn=data.name + "." + old_book_format.lower())
            return error_message
    else:
        if not os.path.exists(file_path + "." + old_book_format.lower()):
            error_message = _("%(format)s not found: %(fn)s",
                              format=old_book_format, fn=data.name + "." + old_book_format.lower())
            return error_message
    # read settings and append converter task to queue
    if ereader_mail:
        settings = config.get_mail_settings()
        settings['subject'] = _('Send to eReader')  # pretranslate Subject for Email
        settings['body'] = _('This Email has been sent via Calibre-Web.')
    else:
        settings = dict()
    link = '<a href="{}">{}</a>'.format(url_for('web.show_book', book_id=book.id), escape(book.title))  # prevent xss
    txt = "{} -> {}: {}".format(
           old_book_format.upper(),
           new_book_format.upper(),
           link)
    settings['old_book_format'] = old_book_format
    settings['new_book_format'] = new_book_format
    WorkerThread.add(user_id, TaskConvert(file_path, book.id, txt, settings, ereader_mail, user_id))
    return None


# Texts are not lazy translated as they are supposed to get send out as is
def send_test_mail(ereader_mail, user_name):
    for email in ereader_mail.split(','):
        email = strip_whitespaces(email)
        WorkerThread.add(user_name, TaskEmail(_('Calibre-Web Test Email'), None, None,
                         config.get_mail_settings(), email, N_("Test Email"),
                                              _('This Email has been sent via Calibre-Web.')))
    return


# Send registration email or password reset email, depending on parameter resend (False means welcome email)
def send_registration_mail(e_mail, user_name, default_password, resend=False):
    txt = "Hi %s!\r\n" % user_name
    if not resend:
        txt += "Your account at Calibre-Web has been created.\r\n"
    txt += "Please log in using the following information:\r\n"
    txt += "Username: %s\r\n" % user_name
    txt += "Password: %s\r\n" % default_password
    txt += "Don't forget to change your password after your first login.\r\n"
    txt += "Regards,\r\n\r\n"
    txt += "Calibre-Web"
    WorkerThread.add(None, TaskEmail(
        subject=_('Get Started with Calibre-Web'),
        filepath=None,
        attachment=None,
        settings=config.get_mail_settings(),
        recipient=e_mail,
        task_message=N_("Registration Email for user: %(name)s", name=user_name),
        text=txt
    ))
    return


def check_send_to_ereader_with_converter(formats):
    book_formats = list()
    if 'MOBI' in formats and 'EPUB' not in formats:
        book_formats.append({'format': 'Epub',
                             'convert': 1,
                             'text': _('Convert %(orig)s to %(format)s and send to eReader',
                                       orig='Mobi',
                                       format='Epub')})
    if 'AZW3' in formats and 'EPUB' not in formats:
        book_formats.append({'format': 'Epub',
                             'convert': 2,
                             'text': _('Convert %(orig)s to %(format)s and send to eReader',
                                       orig='Azw3',
                                       format='Epub')})
    return book_formats


def check_send_to_ereader(entry):
    """
        returns all available book formats for sending to eReader
    """
    formats = list()
    book_formats = list()
    if len(entry.data):
        for ele in iter(entry.data):
            if ele.uncompressed_size < config.mail_size:
                formats.append(ele.format)
        if 'EPUB' in formats:
            book_formats.append({'format': 'Epub',
                                 'convert': 0,
                                 'text': _('Send %(format)s to eReader', format='Epub')})
        if 'PDF' in formats:
            book_formats.append({'format': 'Pdf',
                                 'convert': 0,
                                 'text': _('Send %(format)s to eReader', format='Pdf')})
        if 'AZW' in formats:
            book_formats.append({'format': 'Azw',
                                 'convert': 0,
                                 'text': _('Send %(format)s to eReader', format='Azw')})
        if config.config_converterpath:
            book_formats.extend(check_send_to_ereader_with_converter(formats))
        return book_formats
    else:
        log.error('Cannot find book entry %d', entry.id)
        return None


# Check if a reader is existing for any of the book formats, if not, return empty list, otherwise return
# list with supported formats
def check_read_formats(entry):
    extensions_reader = {'TXT', 'PDF', 'EPUB', 'KEPUB', 'CBZ', 'CBT', 'CBR', 'DJVU', 'DJV'}
    book_formats = list()
    if len(entry.data):
        for ele in iter(entry.data):
            if ele.format.upper() in extensions_reader:
                book_formats.append(ele.format.lower())
    return book_formats


# Files are processed in the following order/priority:
# 1: If epub file is existing, it's directly send to eReader email,
# 2: If mobi file is existing, it's converted and send to eReader email,
# 3: If Pdf file is existing, it's directly send to eReader email
def send_mail(book_id, book_format, convert, ereader_mail, calibrepath, user_id):
    """Send email with attachments"""
    book = calibre_db.get_book(book_id)

    if convert == 1:
        # returns None if success, otherwise errormessage
        return convert_book_format(book_id, calibrepath, 'mobi', book_format.lower(), user_id, ereader_mail)
    if convert == 2:
        # returns None if success, otherwise errormessage
        return convert_book_format(book_id, calibrepath, 'azw3', book_format.lower(), user_id, ereader_mail)

    for entry in iter(book.data):
        if entry.format.upper() == book_format.upper():
            converted_file_name = entry.name + '.' + book_format.lower()
            link = '<a href="{}">{}</a>'.format(url_for('web.show_book', book_id=book_id), escape(book.title))
            email_text = N_("%(book)s send to eReader", book=link)
            for email in ereader_mail.split(','):
                email = strip_whitespaces(email)
                WorkerThread.add(user_id, TaskEmail(_("Send to eReader"), book.path, converted_file_name,
                                 config.get_mail_settings(), email,
                                 email_text, _('This Email has been sent via Calibre-Web.'), book.id))
            return
    return _("The requested file could not be read. Maybe wrong permissions?")


def get_valid_filename(value, replace_whitespace=True, chars=128):
    """
    Returns the given string converted to a string that can be used for a clean
    filename. Limits num characters to 128 max.
    """
    if value[-1:] == '.':
        value = value[:-1]+'_'
    value = value.replace("/", "_").replace(":", "_").strip('\0')
    if config.config_unicode_filename:
        value = (unidecode.unidecode(value))
    if replace_whitespace:
        #  *+:\"/<>? are replaced by _
        value = re.sub(r'[*+:\\\"/<>?]+', '_', value, flags=re.U)
        # pipe has to be replaced with comma
        value = re.sub(r'[|]+', ',', value, flags=re.U)

    value = strip_whitespaces(value.encode('utf-8')[:chars].decode('utf-8', errors='ignore'))

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
                authors_list.append(strip_whitespaces(author_split[1]) + ' ' + strip_whitespaces(author_split[0]))
            elif commas > 1:
                authors_list.extend([strip_whitespaces(x) for x in author.split(',')])
            else:
                authors_list.append(strip_whitespaces(author))
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
                book.read_status = ub.ReadBook.STATUS_FINISHED if read_status == True else ub.ReadBook.STATUS_UNREAD
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
            calibre_db.create_functions(config)
            book = calibre_db.get_filtered_book(book_id)
            book_read_status = getattr(book, 'custom_column_' + str(config.config_read_column))
            if len(book_read_status):
                if read_status is None:
                    book_read_status[0].value = not book_read_status[0].value
                else:
                    book_read_status[0].value = read_status is True
                calibre_db.session.commit()
            else:
                cc_class = db.cc_classes[config.config_read_column]
                new_cc = cc_class(value=read_status or 1, book=book_id)
                calibre_db.session.add(new_cc)
                calibre_db.session.commit()
        except (KeyError, AttributeError, IndexError):
            log.error(
                "Custom Column No.{} does not exist in calibre database".format(config.config_read_column))
            return "Custom Column No.{} does not exist in calibre database".format(config.config_read_column)
        except (OperationalError, InvalidRequestError) as ex:
            calibre_db.session.rollback()
            log.error("Read status could not set: {}".format(ex))
            return _("Read status could not set: {}".format(ex.orig))
    return ""


# Deletes a book from the local filestorage, returns True if deleting is successful, otherwise false
def delete_book_file(book, calibrepath, book_format=None):
    # check that path is 2 elements deep, check that target path has no sub folders
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

def rename_all_files_on_change(one_book, new_path, old_path, all_new_name, gdrive=False):
    for file_format in one_book.data:
        if not gdrive:
            if not os.path.exists(new_path):
                os.makedirs(new_path)
            shutil.move(os.path.join(old_path, file_format.name + '.' + file_format.format.lower()),
                    os.path.join(new_path, all_new_name + '.' + file_format.format.lower()))
        else:
            g_file = gd.getFileFromEbooksFolder(old_path,
                                                file_format.name + '.' + file_format.format.lower())
            if g_file:
                gd.moveGdriveFileRemote(g_file, all_new_name + '.' + file_format.format.lower())
                gd.updateDatabaseOnEdit(g_file['id'], all_new_name + '.' + file_format.format.lower())
            else:
                log.error("File {} not found on gdrive"
                          .format(old_path, file_format.name + '.' + file_format.format.lower()))

        # change name in Database
        file_format.name = all_new_name


def rename_author_path(first_author, old_author_dir, renamed_author, calibre_path="", gdrive=False):
    # Create new_author_dir from parameter or from database
    # Create new title_dir from database and add id
    new_authordir = get_valid_filename(first_author, chars=96)
    new_author_rename_dir = get_valid_filename(renamed_author, chars=96)
    if gdrive:
        g_file = gd.getFileFromEbooksFolder(None, old_author_dir)
        if g_file:
            gd.moveGdriveFolderRemote(g_file, new_author_rename_dir)
    else:
        if os.path.isdir(os.path.join(calibre_path, old_author_dir)):
            old_author_path = os.path.join(calibre_path, old_author_dir)
            new_author_path = os.path.join(calibre_path, new_author_rename_dir)
            try:
                os.rename(old_author_path, new_author_path)
            except OSError:
                try:
                    shutil.move(old_author_path, new_author_path)
                except OSError as ex:
                    log.error("Rename author from: %s to %s: %s", old_author_path, new_author_path, ex)
                    log.error_or_exception(ex)
                    raise Exception(_("Rename author from: '%(src)s' to '%(dest)s' failed with error: %(error)s",
                             src=old_author_path, dest=new_author_path, error=str(ex)))
    return new_authordir

# Moves files in file storage during author/title rename, or from temp dir to file storage
def update_dir_structure_file(book_id, calibre_path, original_filepath, new_author, db_filename):
    # get book database entry from id, if original path overwrite source with original_filepath
    local_book = calibre_db.get_book(book_id)
    if original_filepath:
        path = original_filepath
    else:
        path = os.path.join(calibre_path, local_book.path)

    # Create (current) author_dir and title_dir from database
    author_dir = local_book.path.split('/')[0]
    title_dir = local_book.path.split('/')[1]

    new_title_dir = get_valid_filename(local_book.title, chars=96) + " (" + str(book_id) + ")"
    if new_author:
        new_author_dir = get_valid_filename(new_author, chars=96)
    else:
        new_author = new_author_dir = author_dir

    if title_dir != new_title_dir or author_dir != new_author_dir or original_filepath:
        error = move_files_on_change(calibre_path,
                                     new_author_dir,
                                     new_title_dir,
                                     local_book,
                                     db_filename,
                                     original_filepath,
                                     path)
        new_path = os.path.join(calibre_path, new_author_dir, new_title_dir).replace('\\', '/')
        all_new_name = get_valid_filename(local_book.title, chars=42) + ' - ' \
                       + get_valid_filename(new_author, chars=42)
        # Book folder already moved, only files need to be renamed
        rename_all_files_on_change(local_book, new_path, new_path, all_new_name)

        if error:
            return error
    return False


def upload_new_file_gdrive(book_id, first_author, title, title_dir, original_filepath, filename_ext):
    book = calibre_db.get_book(book_id)
    file_name = get_valid_filename(title, chars=42) + ' - ' + \
        get_valid_filename(first_author, chars=42) + filename_ext
    gdrive_path = os.path.join(get_valid_filename(first_author, chars=96),
                               title_dir + " (" + str(book_id) + ")")
    book.path = gdrive_path.replace("\\", "/")
    gd.uploadFileToEbooksFolder(os.path.join(gdrive_path, file_name).replace("\\", "/"), original_filepath)
    return False


def update_dir_structure_gdrive(book_id, first_author):
    book = calibre_db.get_book(book_id)

    authordir = book.path.split('/')[0]
    titledir = book.path.split('/')[1]
    # new_authordir = rename_all_authors(first_author, renamed_author, gdrive=True)
    new_authordir = get_valid_filename(first_author, chars=96)
    new_titledir = get_valid_filename(book.title, chars=96) + " (" + str(book_id) + ")"

    if titledir != new_titledir:
        g_file = gd.getFileFromEbooksFolder(authordir, titledir)
        if g_file:
            gd.moveGdriveFileRemote(g_file, new_titledir)
            book.path = book.path.split('/')[0] + '/' + new_titledir
            gd.updateDatabaseOnEdit(g_file['id'], book.path)     # only child folder affected
        else:
            return _('File %(file)s not found on Google Drive', file=book.path)  # file not found

    if authordir != new_authordir:
        g_file = gd.getFileFromEbooksFolder(authordir, new_titledir)
        if g_file:
            gd.moveGdriveFolderRemote(g_file, new_authordir, single_book=True)
            book.path = new_authordir + '/' + book.path.split('/')[1]
            gd.updateDatabaseOnEdit(g_file['id'], book.path)
        else:
            return _('File %(file)s not found on Google Drive', file=authordir)  # file not found'''
    if titledir != new_titledir or authordir != new_authordir :
        all_new_name = get_valid_filename(book.title, chars=42) + ' - ' \
                       + get_valid_filename(new_authordir, chars=42)
        rename_all_files_on_change(book, book.path, book.path, all_new_name, gdrive=True)  # todo: Move filenames on gdrive
    return False


def move_files_on_change(calibre_path, new_author_dir, new_titledir, localbook, db_filename, original_filepath, path):
    new_path = os.path.join(calibre_path, new_author_dir, new_titledir)
    try:
        if original_filepath:
            if not os.path.isdir(new_path):
                os.makedirs(new_path)
            try:
                shutil.move(original_filepath, os.path.join(new_path, db_filename))
            except OSError:
                log.error("Rename title from {} to {} failed with error, trying to "
                          "move without metadata".format(path, new_path))
                shutil.move(original_filepath, os.path.join(new_path, db_filename), copy_function=shutil.copy)
            log.debug("Moving title: %s to %s", original_filepath, new_path)
        else:
            # Check new path is not valid path
            if not os.path.exists(new_path):
                # move original path to new path
                log.debug("Moving title: %s to %s", path, new_path)
                shutil.move(path, new_path)
            else:  # path is valid copy only files to new location (merge)
                log.info("Moving title: %s into existing: %s", path, new_path)
                # Take all files and subfolder from old path (strange command)
                for dir_name, __, file_list in os.walk(path):
                    for file in file_list:
                        shutil.move(os.path.join(dir_name, file), os.path.join(new_path + dir_name[len(path):], file))
            if not os.listdir(os.path.split(path)[0]):
                try:
                    shutil.rmtree(os.path.split(path)[0])
                except (IOError, OSError) as ex:
                    log.error("Deleting authorpath for book %s failed: %s", localbook.id, ex)
        # change location in database to new author/title path
        localbook.path = os.path.join(new_author_dir, new_titledir).replace('\\', '/')
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
    #try:
        #clean_author_database(renamed_author, calibre_path, gdrive=gdrive)
        #if first_author and first_author not in renamed_author:
        #    clean_author_database([first_author], calibre_path, local_book, gdrive)
        #if not gdrive and not renamed_author and not original_filepath and len(os.listdir(os.path.dirname(path))) == 0:
        #    shutil.rmtree(os.path.dirname(path))
    #except (OSError, FileNotFoundError) as ex:
    #    log.error_or_exception("Error in rename file in path {}".format(ex))
    #    return _("Error in rename file in path: {}".format(str(ex)))
    return False


def delete_book_gdrive(book, book_format):
    error = None
    if book_format:
        name = ''
        for entry in book.data:
            if entry.format.upper() == book_format:
                name = entry.name + '.' + book_format
        g_file = gd.getFileFromEbooksFolder(book.path, name, nocase=True)
    else:
        g_file = gd.getFileFromEbooksFolder(os.path.dirname(book.path), book.path.split('/')[1])
    if g_file:
        gd.deleteDatabaseEntry(g_file['id'])
        g_file.Trash()
    else:
        error = _('Book path %(path)s not found on Google Drive', path=book.path)  # file not found

    return error is None, error


def reset_password(user_id):
    existing_user = ub.session.query(ub.User).filter(ub.User.id == user_id).first()
    if not existing_user:
        return 0, None
    if not config.get_mail_server_configured():
        return 2, None
    try:
        password = generate_random_password(config.config_password_min_length)
        existing_user.password = generate_password_hash(password)
        ub.session.commit()
        send_registration_mail(existing_user.email, existing_user.name, password, True)
        return 1, existing_user.name
    except Exception:
        ub.session.rollback()
        return 0, None


def generate_random_password(min_length):
    min_length = max(8, min_length) - 4
    random_source = "abcdefghijklmnopqrstuvwxyz01234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ!@#$%&*()?"
    # select 1 lowercase
    s = "abcdefghijklmnopqrstuvwxyz"
    password = [s[c % len(s)] for c in os.urandom(1)]
    # select 1 uppercase
    s = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    password.extend([s[c % len(s)] for c in os.urandom(1)])
    # select 1 digit
    s = "01234567890"
    password.extend([s[c % len(s)] for c in os.urandom(1)])
    # select 1 special symbol
    s = "!@#$%&*()?"
    password.extend([s[c % len(s)] for c in os.urandom(1)])

    # generate other characters
    password.extend([random_source[c % len(random_source)] for c in os.urandom(min_length)])

    # password_list = list(password)
    # shuffle all characters
    random.SystemRandom().shuffle(password)
    return ''.join(password)


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
        log.error("Found an existing account for this Email address")
        raise Exception(_("Found an existing account for this Email address"))
    return email


def check_username(username):
    username = strip_whitespaces(username)
    if ub.session.query(ub.User).filter(func.lower(ub.User.name) == username.lower()).scalar():
        log.error("This username is already taken")
        raise Exception(_("This username is already taken"))
    return username


def valid_email(emails):
    valid_emails = []
    for email in emails.split(','):
        email = strip_whitespaces(email)
        # if email is not deleted
        if email:
            # Regex according to https://developer.mozilla.org/en-US/docs/Web/HTML/Element/input/email#validation
            if not re.search(r"^[\w.!#$%&'*+\\/=?^_`{|}~-]+@[\w](?:[\w-]{0,61}[\w])?(?:\.[\w](?:[\w-]{0,61}[\w])?)*$",
                             email):
                log.error("Invalid Email address format for {}".format(email))
                raise Exception(_("Invalid Email address format"))
            valid_emails.append(email)
    return ",".join(valid_emails)


def valid_password(check_password):
    if config.config_password_policy:
        verify = ""
        if config.config_password_min_length > 0:
            verify += r"^(?=.{" + str(config.config_password_min_length) + ",}$)"
        if config.config_password_number:
            verify += r"(?=.*?\d)"
        if config.config_password_lower:
            verify += r"(?=.*?[\p{Ll}])"
        if config.config_password_upper:
            verify += r"(?=.*?[\p{Lu}])"
        if config.config_password_character:
            verify += r"(?=.*?[\p{Letter}])"
        if config.config_password_special:
            verify += r"(?=.*?[^\p{Letter}\s0-9])"
        match = regex.match(verify, check_password)
        if not match:
            raise Exception(_("Password doesn't comply with password validation rules"))
    return check_password
# ################################# External interface #################################


def update_dir_structure(book_id,
                         calibre_path,
                         first_author=None,     # change author of book to this author
                         original_filepath=None,
                         db_filename=None):
    if config.config_use_google_drive:
        return update_dir_structure_gdrive(book_id, first_author)
    else:
        return update_dir_structure_file(book_id,
                                         calibre_path,
                                         original_filepath,
                                         first_author,
                                         db_filename)


def delete_book(book, calibrepath, book_format):
    if not book_format:
        clear_cover_thumbnail_cache(book.id)  # here it breaks
        calibre_db.delete_dirty_metadata(book.id)
    if config.config_use_google_drive:
        return delete_book_gdrive(book, book_format)
    else:
        return delete_book_file(book, calibrepath, book_format)


def get_cover_on_failure():
    try:
        return send_from_directory(_STATIC_DIR, "generic_cover.jpg")
    except PermissionError:
        log.error("No permission to access generic_cover.jpg file.")
        abort(403)


def get_book_cover(book_id, resolution=None):
    book = calibre_db.get_filtered_book(book_id, allow_show_archived=True)
    return get_book_cover_internal(book, resolution=resolution)


def get_book_cover_with_uuid(book_uuid, resolution=None):
    book = calibre_db.get_book_by_uuid(book_uuid)
    if not book:
        return  # allows kobo.HandleCoverImageRequest to proxy request
    return get_book_cover_internal(book, resolution=resolution)


def get_book_cover_internal(book, resolution=None):
    if book and book.has_cover:

        # Send the book cover thumbnail if it exists in cache
        if resolution:
            thumbnail = get_book_cover_thumbnail(book, resolution)
            if thumbnail:
                cache = fs.FileSystem()
                if cache.get_cache_file_exists(thumbnail.filename, CACHE_TYPE_THUMBNAILS):
                    return send_from_directory(cache.get_cache_file_dir(thumbnail.filename, CACHE_TYPE_THUMBNAILS),
                                               thumbnail.filename)

        # Send the book cover from Google Drive if configured
        if config.config_use_google_drive:
            try:
                if not gd.is_gdrive_ready():
                    return get_cover_on_failure()
                cover_file = gd.get_cover_via_gdrive(book.path)
                if cover_file:
                    return Response(cover_file, mimetype='image/jpeg')
                else:
                    log.error('{}/cover.jpg not found on Google Drive'.format(book.path))
                    return get_cover_on_failure()
            except Exception as ex:
                log.error_or_exception(ex)
                return get_cover_on_failure()

        # Send the book cover from the Calibre directory
        else:
            cover_file_path = os.path.join(config.get_book_path(), book.path)
            if os.path.isfile(os.path.join(cover_file_path, "cover.jpg")):
                return send_from_directory(cover_file_path, "cover.jpg")
            else:
                return get_cover_on_failure()
    else:
        return get_cover_on_failure()


def get_book_cover_thumbnail(book, resolution):
    if book and book.has_cover:
        return (ub.session
                .query(ub.Thumbnail)
                .filter(ub.Thumbnail.type == THUMBNAIL_TYPE_COVER)
                .filter(ub.Thumbnail.entity_id == book.id)
                .filter(ub.Thumbnail.resolution == resolution)
                .filter(or_(ub.Thumbnail.expiration.is_(None), ub.Thumbnail.expiration > datetime.now(timezone.utc)))
                .first())


def get_series_thumbnail_on_failure(series_id, resolution):
    book = (calibre_db.session
        .query(db.Books)
        .join(db.books_series_link)
        .join(db.Series)
        .filter(db.Series.id == series_id)
        .filter(db.Books.has_cover == 1)
        .first())
    return get_book_cover_internal(book, resolution=resolution)


def get_series_cover_thumbnail(series_id, resolution=None):
    return get_series_cover_internal(series_id, resolution)


def get_series_cover_internal(series_id, resolution=None):
    # Send the series thumbnail if it exists in cache
    if resolution:
        thumbnail = get_series_thumbnail(series_id, resolution)
        if thumbnail:
            cache = fs.FileSystem()
            if cache.get_cache_file_exists(thumbnail.filename, CACHE_TYPE_THUMBNAILS):
                return send_from_directory(cache.get_cache_file_dir(thumbnail.filename, CACHE_TYPE_THUMBNAILS),
                                           thumbnail.filename)

    return get_series_thumbnail_on_failure(series_id, resolution)


def get_series_thumbnail(series_id, resolution):
    return (ub.session
        .query(ub.Thumbnail)
        .filter(ub.Thumbnail.type == THUMBNAIL_TYPE_SERIES)
        .filter(ub.Thumbnail.entity_id == series_id)
        .filter(ub.Thumbnail.resolution == resolution)
        .filter(or_(ub.Thumbnail.expiration.is_(None), ub.Thumbnail.expiration > datetime.now(timezone.utc)))
        .first())


# saves book cover from url
def save_cover_from_url(url, book_path):
    try:
        if cli_param.allow_localhost:
            img = requests.get(url, timeout=(10, 200), allow_redirects=False)  # ToDo: Error Handling
        elif use_advocate:
            img = cw_advocate.get(url, timeout=(10, 200), allow_redirects=False)      # ToDo: Error Handling
        else:
            log.error("python module advocate is not installed but is needed")
            return False, _("Python module 'advocate' is not installed but is needed for cover uploads")
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
            log.error("Failed to create path for cover")
            return False, _("Failed to create path for cover")
    try:
        # upload of jpg file without wand
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
        log.error("Cover-file is not a valid image file, or could not be stored")
        return False, _("Cover-file is not a valid image file, or could not be stored")
    return True, None


# saves book cover to gdrive or locally
def save_cover(img, book_path):
    content_type = img.headers.get('content-type')

    if use_IM:
        if content_type not in ('image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/bmp'):
            log.error("Only jpg/jpeg/png/webp/bmp files are supported as coverfile")
            return False, _("Only jpg/jpeg/png/webp/bmp files are supported as coverfile")
        # convert to jpg because calibre only supports jpg
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
        if content_type not in ['image/jpeg', 'image/jpg']:
            log.error("Only jpg/jpeg files are supported as coverfile")
            return False, _("Only jpg/jpeg files are supported as coverfile")

    if config.config_use_google_drive:
        tmp_dir = get_temp_dir()
        ret, message = save_cover_from_filestorage(tmp_dir, "uploaded_cover.jpg", img)
        if ret is True:
            gd.uploadFileToEbooksFolder(os.path.join(book_path, 'cover.jpg').replace("\\", "/"),
                                        os.path.join(tmp_dir, "uploaded_cover.jpg"))
            log.info("Cover is saved on Google Drive")
            return True, None
        else:
            return False, message
    else:
        return save_cover_from_filestorage(os.path.join(config.get_book_path(), book_path), "cover.jpg", img)


def do_download_file(book, book_format, client, data, headers):
    book_name = data.name
    download_name = filename = None
    if config.config_use_google_drive:
        # startTime = time.time()
        df = gd.getFileFromEbooksFolder(book.path, data.name + "." + book_format)
        # log.debug('%s', time.time() - startTime)
        if df:
            if config.config_embed_metadata and (
                 (book_format == "kepub" and config.config_kepubifypath) or
                 (book_format != "kepub" and config.config_binariesdir)):
                output_path = os.path.join(config.config_calibre_dir, book.path)
                if not os.path.exists(output_path):
                    os.makedirs(output_path)
                output = os.path.join(config.config_calibre_dir, book.path, book_name + "." + book_format)
                gd.downloadFile(book.path, book_name + "." + book_format, output)
                if book_format == "kepub" and config.config_kepubifypath:
                    filename, download_name = do_kepubify_metadata_replace(book, output)
                elif book_format != "kepub" and config.config_binariesdir:
                    filename, download_name = do_calibre_export(book.id, book_format)
            else:
                return gd.do_gdrive_download(df, headers)
        else:
            abort(404)
    else:
        filename = os.path.join(config.get_book_path(), book.path)
        if not os.path.isfile(os.path.join(filename, book_name + "." + book_format)):
            # ToDo: improve error handling
            log.error('File not found: %s', os.path.join(filename, book_name + "." + book_format))

        if client == "kobo" and book_format == "kepub":
            headers["Content-Disposition"] = headers["Content-Disposition"].replace(".kepub", ".kepub.epub")

        if book_format == "kepub" and config.config_kepubifypath and config.config_embed_metadata:
            filename, download_name = do_kepubify_metadata_replace(book, os.path.join(filename,
                                                                                      book_name + "." + book_format))
        elif book_format != "kepub" and config.config_binariesdir and config.config_embed_metadata:
            filename, download_name = do_calibre_export(book.id, book_format)
        else:
            download_name = book_name

    response = make_response(send_from_directory(filename, download_name + "." + book_format))
    # ToDo Check headers parameter
    for element in headers:
        response.headers[element[0]] = element[1]
    log.info('Downloading file: \'%s\' by %s - %s', format(os.path.join(filename, book_name + "." + book_format)),
             current_user.name, request.headers.get('X-Forwarded-For', request.remote_addr))
    return response


def do_kepubify_metadata_replace(book, file_path):
    custom_columns = (calibre_db.session.query(db.CustomColumns)
                      .filter(db.CustomColumns.mark_for_delete == 0)
                      .filter(db.CustomColumns.datatype.notin_(db.cc_exceptions))
                      .order_by(db.CustomColumns.label).all())

    tree, cf_name = get_content_opf(file_path)
    package = create_new_metadata_backup(book, custom_columns, current_user.locale, _("Cover"), lang_type=2)
    content = replace_metadata(tree, package)
    tmp_dir = get_temp_dir()
    temp_file_name = str(uuid4())
    # open zipfile and replace metadata block in content.opf
    updateEpub(file_path, os.path.join(tmp_dir, temp_file_name + ".kepub"), cf_name, content)
    return tmp_dir, temp_file_name


##################################


def check_unrar(unrar_location):
    if not unrar_location:
        return

    if not os.path.exists(unrar_location):
        return _('UnRar binary file not found')

    try:
        unrar_location = [unrar_location]
        value = process_wait(unrar_location, pattern='UNRAR (.*) freeware')
        if value:
            version = value.group(1)
            log.debug("UnRar version %s", version)

    except (OSError, UnicodeDecodeError) as err:
        log.error_or_exception(err)
        return _('Error executing UnRar')


def check_calibre(calibre_location):
    if not calibre_location:
        return

    if not os.path.exists(calibre_location):
        return _('Could not find the specified directory')

    if not os.path.isdir(calibre_location):
        return _('Please specify a directory, not a file')

    try:
        supported_binary_paths = [os.path.join(calibre_location, binary)
                                  for binary in SUPPORTED_CALIBRE_BINARIES.values()]
        binaries_available = [os.path.isfile(binary_path) for binary_path in supported_binary_paths]
        binaries_executable = [os.access(binary_path, os.X_OK) for binary_path in supported_binary_paths]
        if all(binaries_available) and all(binaries_executable):
            values = [process_wait([binary_path, "--version"], pattern=r'\(calibre (.*)\)')
                      for binary_path in supported_binary_paths]
            if all(values):
                version = values[0].group(1)
                log.debug("calibre version %s", version)
            else:
                return _('Calibre binaries not viable')
        else:
            ret_val = []
            missing_binaries = [path for path, available in
                               zip(SUPPORTED_CALIBRE_BINARIES.values(), binaries_available) if not available]

            missing_perms = [path for path, available in
                            zip(SUPPORTED_CALIBRE_BINARIES.values(), binaries_executable) if not available]
            if missing_binaries:
                ret_val.append(_('Missing calibre binaries: %(missing)s', missing=", ".join(missing_binaries)))
            if missing_perms:
                ret_val.append(_('Missing executable permissions: %(missing)s', missing=", ".join(missing_perms)))
            return ", ".join(ret_val)

    except (OSError, UnicodeDecodeError) as err:
        log.error_or_exception(err)
        return _('Error executing Calibre')


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


def tags_filters():
    negtags_list = current_user.list_denied_tags()
    postags_list = current_user.list_allowed_tags()
    neg_content_tags_filter = false() if negtags_list == [''] else db.Tags.name.in_(negtags_list)
    pos_content_tags_filter = true() if postags_list == [''] else db.Tags.name.in_(postags_list)
    return and_(pos_content_tags_filter, ~neg_content_tags_filter)


# checks if domain is in database (including wildcards)
# example SELECT * FROM @TABLE WHERE 'abcdefg' LIKE Name;
# from https://code.luasoftware.com/tutorials/flask/execute-raw-sql-in-flask-sqlalchemy/
# in all calls the email address is checked for validity
def check_valid_domain(domain_text):
    sql = "SELECT * FROM registration WHERE (:domain LIKE domain and allow = 1);"
    if not len(ub.session.query(ub.Registration).from_statement(text(sql)).params(domain=domain_text).all()):
        return False
    sql = "SELECT * FROM registration WHERE (:domain LIKE domain and allow = 0);"
    return not len(ub.session.query(ub.Registration).from_statement(text(sql)).params(domain=domain_text).all())


def get_download_link(book_id, book_format, client):
    book_format = book_format.split(".")[0]
    book = calibre_db.get_filtered_book(book_id, allow_show_archived=True)
    if book:
        data1 = calibre_db.get_book_format(book.id, book_format.upper())
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
                quote(file_name), book_format, quote(file_name), book_format)
            return do_download_file(book, book_format, client, data1, headers)
    else:
        log.error("Book id {} not found for downloading".format(book_id))
    abort(404)


def clear_cover_thumbnail_cache(book_id):
    if config.schedule_generate_book_covers:
        WorkerThread.add(None, TaskClearCoverThumbnailCache(book_id), hidden=True)


def replace_cover_thumbnail_cache(book_id):
    if config.schedule_generate_book_covers:
        WorkerThread.add(None, TaskClearCoverThumbnailCache(book_id), hidden=True)
        WorkerThread.add(None, TaskGenerateCoverThumbnails(book_id), hidden=True)


def delete_thumbnail_cache():
    WorkerThread.add(None, TaskClearCoverThumbnailCache(-1))


def add_book_to_thumbnail_cache(book_id):
    if config.schedule_generate_book_covers:
        WorkerThread.add(None, TaskGenerateCoverThumbnails(book_id), hidden=True)


def update_thumbnail_cache():
    if config.schedule_generate_book_covers:
        WorkerThread.add(None, TaskGenerateCoverThumbnails())


def set_all_metadata_dirty():
    WorkerThread.add(None, TaskBackupMetadata(export_language=get_locale(),
                                              translated_title=_("Cover"),
                                              set_dirty=True,
                                              task_message=N_("Queue all books for metadata backup")),
                     hidden=False)
