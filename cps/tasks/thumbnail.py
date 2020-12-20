# -*- coding: utf-8 -*-

#   This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#     Copyright (C) 2020 mmonkey
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program. If not, see <http://www.gnu.org/licenses/>.

from __future__ import division, print_function, unicode_literals
import os

from cps import config, db, gdriveutils, logger, ub
from cps.constants import CACHE_DIR as _CACHE_DIR
from cps.services.worker import CalibreTask
from cps.thumbnails import THUMBNAIL_RESOLUTION_1X, THUMBNAIL_RESOLUTION_2X
from datetime import datetime, timedelta
from sqlalchemy import func
from urllib.request import urlopen

try:
    from wand.image import Image
    use_IM = True
except (ImportError, RuntimeError) as e:
    use_IM = False


class TaskThumbnail(CalibreTask):
    def __init__(self, limit=100, task_message=u'Generating cover thumbnails'):
        super(TaskThumbnail, self).__init__(task_message)
        self.limit = limit
        self.log = logger.create()
        self.app_db_session = ub.get_new_session_instance()
        self.worker_db = db.CalibreDB(expire_on_commit=False)

    def run(self, worker_thread):
        if self.worker_db.session and use_IM:
            thumbnails = self.get_thumbnail_book_ids()
            thumbnail_book_ids = list(map(lambda t: t.book_id, thumbnails))
            books_without_thumbnails = self.get_books_without_thumbnails(thumbnail_book_ids)

            count = len(books_without_thumbnails)
            for i, book in enumerate(books_without_thumbnails):
                thumbnails = self.get_thumbnails_for_book(thumbnails, book)
                if thumbnails:
                    for thumbnail in thumbnails:
                        self.update_book_thumbnail(book, thumbnail)

                else:
                    self.create_book_thumbnail(book, THUMBNAIL_RESOLUTION_1X)
                    self.create_book_thumbnail(book, THUMBNAIL_RESOLUTION_2X)

                self.progress = (1.0 / count) * i

        self._handleSuccess()
        self.app_db_session.close()

    def get_thumbnail_book_ids(self):
        return self.app_db_session\
            .query(ub.Thumbnail)\
            .group_by(ub.Thumbnail.book_id)\
            .having(func.min(ub.Thumbnail.expiration) > datetime.utcnow())\
            .all()

    def get_books_without_thumbnails(self, thumbnail_book_ids):
        return self.worker_db.session\
            .query(db.Books)\
            .filter(db.Books.has_cover == 1)\
            .filter(db.Books.id.notin_(thumbnail_book_ids))\
            .limit(self.limit)\
            .all()

    def get_thumbnails_for_book(self, thumbnails, book):
        results = list()
        for thumbnail in thumbnails:
            if thumbnail.book_id == book.id:
                results.append(thumbnail)

        return results

    def update_book_thumbnail(self, book, thumbnail):
        thumbnail.expiration = datetime.utcnow() + timedelta(days=30)

        try:
            self.app_db_session.commit()
            self.generate_book_thumbnail(book, thumbnail)
        except Exception as ex:
            self._handleError(u'Error updating book thumbnail: ' + str(ex))
            self.app_db_session.rollback()

    def create_book_thumbnail(self, book, resolution):
        thumbnail = ub.Thumbnail()
        thumbnail.book_id = book.id
        thumbnail.resolution = resolution

        self.app_db_session.add(thumbnail)
        try:
            self.app_db_session.commit()
            self.generate_book_thumbnail(book, thumbnail)
        except Exception as ex:
            self._handleError(u'Error creating book thumbnail: ' + str(ex))
            self.app_db_session.rollback()

    def generate_book_thumbnail(self, book, thumbnail):
        if book and thumbnail:
            if config.config_use_google_drive:
                if not gdriveutils.is_gdrive_ready():
                    raise Exception('Google Drive is configured but not ready')

                web_content_link = gdriveutils.get_cover_via_gdrive(book.path)
                if not web_content_link:
                    raise Exception('Google Drive cover url not found')

                stream = None
                try:
                    stream = urlopen(web_content_link)
                    with Image(file=stream) as img:
                        height = self.get_thumbnail_height(thumbnail)
                        if img.height > height:
                            width = self.get_thumbnail_width(height, img)
                            img.resize(width=width, height=height, filter='lanczos')
                            img.save(filename=self.get_thumbnail_cache_path(thumbnail))
                except Exception as ex:
                    # Bubble exception to calling function
                    raise ex
                finally:
                    stream.close()
            else:
                book_cover_filepath = os.path.join(config.config_calibre_dir, book.path, 'cover.jpg')
                if not os.path.isfile(book_cover_filepath):
                    raise Exception('Book cover file not found')

                with Image(filename=book_cover_filepath) as img:
                    height = self.get_thumbnail_height(thumbnail)
                    if img.height > height:
                        width = self.get_thumbnail_width(height, img)
                        img.resize(width=width, height=height, filter='lanczos')
                        img.save(filename=self.get_thumbnail_cache_path(thumbnail))

    def get_thumbnail_height(self, thumbnail):
        return int(225 * thumbnail.resolution)

    def get_thumbnail_width(self, height, img):
        percent = (height / float(img.height))
        return int((float(img.width) * float(percent)))

    def get_thumbnail_cache_dir(self):
        if not os.path.isdir(_CACHE_DIR):
            os.makedirs(_CACHE_DIR)

        if not os.path.isdir(os.path.join(_CACHE_DIR, 'thumbnails')):
            os.makedirs(os.path.join(_CACHE_DIR, 'thumbnails'))

        return os.path.join(_CACHE_DIR, 'thumbnails')

    def get_thumbnail_cache_path(self, thumbnail):
        if thumbnail:
            return os.path.join(self.get_thumbnail_cache_dir(), thumbnail.filename)
        return None

    @property
    def name(self):
        return "Thumbnail"
