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

from cps import config, db, fs, gdriveutils, logger, ub
from cps.services.worker import CalibreTask
from datetime import datetime, timedelta
from sqlalchemy import or_

try:
    from urllib.request import urlopen
except ImportError as e:
    from urllib2 import urlopen

try:
    from wand.image import Image
    use_IM = True
except (ImportError, RuntimeError) as e:
    use_IM = False

THUMBNAIL_RESOLUTION_1X = 1
THUMBNAIL_RESOLUTION_2X = 2
THUMBNAIL_RESOLUTION_3X = 3


class TaskGenerateCoverThumbnails(CalibreTask):
    def __init__(self, task_message=u'Generating cover thumbnails'):
        super(TaskGenerateCoverThumbnails, self).__init__(task_message)
        self.log = logger.create()
        self.app_db_session = ub.get_new_session_instance()
        self.calibre_db = db.CalibreDB(expire_on_commit=False)
        self.cache = fs.FileSystem()
        self.resolutions = [
            THUMBNAIL_RESOLUTION_1X,
            THUMBNAIL_RESOLUTION_2X
        ]

    def run(self, worker_thread):
        if self.calibre_db.session and use_IM:
            books_with_covers = self.get_books_with_covers()
            count = len(books_with_covers)

            updated = 0
            generated = 0
            for i, book in enumerate(books_with_covers):
                book_cover_thumbnails = self.get_book_cover_thumbnails(book.id)

                # Generate new thumbnails for missing covers
                resolutions = list(map(lambda t: t.resolution, book_cover_thumbnails))
                missing_resolutions = list(set(self.resolutions).difference(resolutions))
                for resolution in missing_resolutions:
                    generated += 1
                    self.create_book_cover_thumbnail(book, resolution)

                # Replace outdated or missing thumbnails
                for thumbnail in book_cover_thumbnails:
                    if book.last_modified > thumbnail.generated_at:
                        updated += 1
                        self.update_book_cover_thumbnail(book, thumbnail)

                    elif not self.cache.get_cache_file_exists(thumbnail.filename, fs.CACHE_TYPE_THUMBNAILS):
                        updated += 1
                        self.update_book_cover_thumbnail(book, thumbnail)

                self.message = u'Processing book {0} of {1}'.format(i + 1, count)
                self.progress = (1.0 / count) * i

        self._handleSuccess()
        self.app_db_session.remove()

    def get_books_with_covers(self):
        return self.calibre_db.session\
            .query(db.Books)\
            .filter(db.Books.has_cover == 1)\
            .all()

    def get_book_cover_thumbnails(self, book_id):
        return self.app_db_session\
            .query(ub.Thumbnail)\
            .filter(ub.Thumbnail.book_id == book_id)\
            .filter(or_(ub.Thumbnail.expiration.is_(None), ub.Thumbnail.expiration > datetime.utcnow()))\
            .all()

    def create_book_cover_thumbnail(self, book, resolution):
        thumbnail = ub.Thumbnail()
        thumbnail.book_id = book.id
        thumbnail.format = 'jpeg'
        thumbnail.resolution = resolution

        self.app_db_session.add(thumbnail)
        try:
            self.app_db_session.commit()
            self.generate_book_thumbnail(book, thumbnail)
        except Exception as ex:
            self.log.info(u'Error creating book thumbnail: ' + str(ex))
            self._handleError(u'Error creating book thumbnail: ' + str(ex))
            self.app_db_session.rollback()

    def update_book_cover_thumbnail(self, book, thumbnail):
        thumbnail.generated_at = datetime.utcnow()

        try:
            self.app_db_session.commit()
            self.cache.delete_cache_file(thumbnail.filename, fs.CACHE_TYPE_THUMBNAILS)
            self.generate_book_thumbnail(book, thumbnail)
        except Exception as ex:
            self.log.info(u'Error updating book thumbnail: ' + str(ex))
            self._handleError(u'Error updating book thumbnail: ' + str(ex))
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
                            img.format = thumbnail.format
                            filename = self.cache.get_cache_file_path(thumbnail.filename, fs.CACHE_TYPE_THUMBNAILS)
                            img.save(filename=filename)
                except Exception as ex:
                    # Bubble exception to calling function
                    self.log.info(u'Error generating thumbnail file: ' + str(ex))
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
                        img.format = thumbnail.format
                        filename = self.cache.get_cache_file_path(thumbnail.filename, fs.CACHE_TYPE_THUMBNAILS)
                        img.save(filename=filename)

    def get_thumbnail_height(self, thumbnail):
        return int(225 * thumbnail.resolution)

    def get_thumbnail_width(self, height, img):
        percent = (height / float(img.height))
        return int((float(img.width) * float(percent)))

    @property
    def name(self):
        return "ThumbnailsGenerate"


class TaskClearCoverThumbnailCache(CalibreTask):
    def __init__(self, book_id=None, task_message=u'Clearing cover thumbnail cache'):
        super(TaskClearCoverThumbnailCache, self).__init__(task_message)
        self.log = logger.create()
        self.book_id = book_id
        self.app_db_session = ub.get_new_session_instance()
        self.cache = fs.FileSystem()

    def run(self, worker_thread):
        if self.app_db_session:
            if self.book_id:
                thumbnails = self.get_thumbnails_for_book(self.book_id)
                for thumbnail in thumbnails:
                    self.delete_thumbnail(thumbnail)
            else:
                self.delete_all_thumbnails()

        self._handleSuccess()
        self.app_db_session.remove()

    def get_thumbnails_for_book(self, book_id):
        return self.app_db_session\
            .query(ub.Thumbnail)\
            .filter(ub.Thumbnail.book_id == book_id)\
            .all()

    def delete_thumbnail(self, thumbnail):
        try:
            self.cache.delete_cache_file(thumbnail.filename, fs.CACHE_TYPE_THUMBNAILS)
        except Exception as ex:
            self.log.info(u'Error deleting book thumbnail: ' + str(ex))
            self._handleError(u'Error deleting book thumbnail: ' + str(ex))

    def delete_all_thumbnails(self):
        try:
            self.cache.delete_cache_dir(fs.CACHE_TYPE_THUMBNAILS)
        except Exception as ex:
            self.log.info(u'Error deleting book thumbnails: ' + str(ex))
            self._handleError(u'Error deleting book thumbnails: ' + str(ex))

    @property
    def name(self):
        return "ThumbnailsClear"
