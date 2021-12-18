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

import sys
import os
import re

from glob import glob
from shutil import copyfile
from markupsafe import escape

from sqlalchemy.exc import SQLAlchemyError

from cps.services.worker import CalibreTask
from cps import db
from cps import logger, config
from cps.subproc_wrapper import process_open
from flask_babel import gettext as _
from flask import url_for

from cps.tasks.mail import TaskEmail
from cps import gdriveutils
log = logger.create()


class TaskConvert(CalibreTask):
    def __init__(self, file_path, bookid, taskMessage, settings, kindle_mail, user=None):
        super(TaskConvert, self).__init__(taskMessage)
        self.file_path = file_path
        self.bookid = bookid
        self.title = ""
        self.settings = settings
        self.kindle_mail = kindle_mail
        self.user = user

        self.results = dict()

    def run(self, worker_thread):
        self.worker_thread = worker_thread
        if config.config_use_google_drive:
            worker_db = db.CalibreDB(expire_on_commit=False)
            cur_book = worker_db.get_book(self.bookid)
            self.title = cur_book.title
            data = worker_db.get_book_format(self.bookid, self.settings['old_book_format'])
            df = gdriveutils.getFileFromEbooksFolder(cur_book.path,
                                                     data.name + "." + self.settings['old_book_format'].lower())
            if df:
                datafile = os.path.join(config.config_calibre_dir,
                                        cur_book.path,
                                        data.name + u"." + self.settings['old_book_format'].lower())
                if not os.path.exists(os.path.join(config.config_calibre_dir, cur_book.path)):
                    os.makedirs(os.path.join(config.config_calibre_dir, cur_book.path))
                df.GetContentFile(datafile)
                worker_db.session.close()
            else:
                error_message = _(u"%(format)s not found on Google Drive: %(fn)s",
                                  format=self.settings['old_book_format'],
                                  fn=data.name + "." + self.settings['old_book_format'].lower())
                worker_db.session.close()
                return error_message

        filename = self._convert_ebook_format()
        if config.config_use_google_drive:
            os.remove(self.file_path + u'.' + self.settings['old_book_format'].lower())

        if filename:
            if config.config_use_google_drive:
                # Upload files to gdrive
                gdriveutils.updateGdriveCalibreFromLocal()
                self._handleSuccess()
            if self.kindle_mail:
                # if we're sending to kindle after converting, create a one-off task and run it immediately
                # todo: figure out how to incorporate this into the progress
                try:
                    EmailText = _(u"%(book)s send to Kindle", book=escape(self.title))
                    worker_thread.add(self.user, TaskEmail(self.settings['subject'],
                                                           self.results["path"],
                                                           filename,
                                                           self.settings,
                                                           self.kindle_mail,
                                                           EmailText,
                                                           self.settings['body'],
                                                           internal=True)
                                      )
                except Exception as ex:
                    return self._handleError(str(ex))

    def _convert_ebook_format(self):
        error_message = None
        local_db = db.CalibreDB(expire_on_commit=False)
        file_path = self.file_path
        book_id = self.bookid
        format_old_ext = u'.' + self.settings['old_book_format'].lower()
        format_new_ext = u'.' + self.settings['new_book_format'].lower()

        # check to see if destination format already exists - or if book is in database
        # if it does - mark the conversion task as complete and return a success
        # this will allow send to kindle workflow to continue to work
        if os.path.isfile(file_path + format_new_ext) or\
            local_db.get_book_format(self.bookid, self.settings['new_book_format']):
            log.info("Book id %d already converted to %s", book_id, format_new_ext)
            cur_book = local_db.get_book(book_id)
            self.title = cur_book.title
            self.results['path'] = file_path
            self.results['title'] = self.title
            self._handleSuccess()
            local_db.session.close()
            return os.path.basename(file_path + format_new_ext)
        else:
            log.info("Book id %d - target format of %s does not exist. Moving forward with convert.",
                     book_id,
                     format_new_ext)

        if config.config_kepubifypath and format_old_ext == '.epub' and format_new_ext == '.kepub':
            check, error_message = self._convert_kepubify(file_path,
                                                          format_old_ext,
                                                          format_new_ext)
        else:
            # check if calibre converter-executable is existing
            if not os.path.exists(config.config_converterpath):
                # ToDo Text is not translated
                self._handleError(_(u"Calibre ebook-convert %(tool)s not found", tool=config.config_converterpath))
                return
            check, error_message = self._convert_calibre(file_path, format_old_ext, format_new_ext)

        if check == 0:
            cur_book = local_db.get_book(book_id)
            if os.path.isfile(file_path + format_new_ext):
                new_format = db.Data(name=cur_book.data[0].name,
                                         book_format=self.settings['new_book_format'].upper(),
                                         book=book_id, uncompressed_size=os.path.getsize(file_path + format_new_ext))
                try:
                    local_db.session.merge(new_format)
                    local_db.session.commit()
                except SQLAlchemyError as e:
                    local_db.session.rollback()
                    log.error("Database error: %s", e)
                    local_db.session.close()
                    self._handleError(error_message)
                    return
                self.results['path'] = cur_book.path
                self.title = cur_book.title
                self.results['title'] = self.title
                if not config.config_use_google_drive:
                    self._handleSuccess()
                return os.path.basename(file_path + format_new_ext)
            else:
                error_message = _('%(format)s format not found on disk', format=format_new_ext.upper())
        local_db.session.close()
        log.info("ebook converter failed with error while converting book")
        if not error_message:
            error_message = _('Ebook converter failed with unknown error')
        self._handleError(error_message)
        return

    def _convert_kepubify(self, file_path, format_old_ext, format_new_ext):
        quotes = [1, 3]
        command = [config.config_kepubifypath, (file_path + format_old_ext), '-o', os.path.dirname(file_path)]
        try:
            p = process_open(command, quotes)
        except OSError as e:
            return 1, _(u"Kepubify-converter failed: %(error)s", error=e)
        self.progress = 0.01
        while True:
            nextline = p.stdout.readlines()
            nextline = [x.strip('\n') for x in nextline if x != '\n']
            for line in nextline:
                log.debug(line)
            if p.poll() is not None:
                break

        # ToD Handle
        # process returncode
        check = p.returncode

        # move file
        if check == 0:
            converted_file = glob(os.path.join(os.path.dirname(file_path), "*.kepub.epub"))
            if len(converted_file) == 1:
                copyfile(converted_file[0], (file_path + format_new_ext))
                os.unlink(converted_file[0])
            else:
                return 1, _(u"Converted file not found or more than one file in folder %(folder)s",
                            folder=os.path.dirname(file_path))
        return check, None

    def _convert_calibre(self, file_path, format_old_ext, format_new_ext):
        try:
            # Linux py2.7 encode as list without quotes no empty element for parameters
            # linux py3.x no encode and as list without quotes no empty element for parameters
            # windows py2.7 encode as string with quotes empty element for parameters is okay
            # windows py 3.x no encode and as string with quotes empty element for parameters is okay
            # separate handling for windows and linux
            quotes = [1, 2]
            command = [config.config_converterpath, (file_path + format_old_ext),
                       (file_path + format_new_ext)]
            quotes_index = 3
            if config.config_calibre:
                parameters = config.config_calibre.split(" ")
                for param in parameters:
                    command.append(param)
                    quotes.append(quotes_index)
                    quotes_index += 1

            p = process_open(command, quotes, newlines=False)
        except OSError as e:
            return 1, _(u"Ebook-converter failed: %(error)s", error=e)

        while p.poll() is None:
            nextline = p.stdout.readline()
            if isinstance(nextline, bytes):
                nextline = nextline.decode('utf-8', errors="ignore").strip('\r\n')
            if nextline:
                log.debug(nextline)
            # parse progress string from calibre-converter
            progress = re.search(r"(\d+)%\s.*", nextline)
            if progress:
                self.progress = int(progress.group(1)) / 100
                if config.config_use_google_drive:
                    self.progress *= 0.9

        # process returncode
        check = p.returncode
        calibre_traceback = p.stderr.readlines()
        error_message = ""
        for ele in calibre_traceback:
            ele = ele.decode('utf-8', errors="ignore").strip('\n')
            log.debug(ele)
            if not ele.startswith('Traceback') and not ele.startswith('  File'):
                error_message = _("Calibre failed with error: %(error)s", error=ele)
        return check, error_message

    @property
    def name(self):
        return "Convert"

    def __str__(self):
        return "Convert {} {}".format(self.bookid, self.kindle_mail)
