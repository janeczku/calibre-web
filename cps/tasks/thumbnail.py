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
from sqlalchemy import func

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


class TaskGenerateCoverThumbnails(CalibreTask):
    def __init__(self, limit=100, task_message=u'Generating cover thumbnails'):
        super(TaskGenerateCoverThumbnails, self).__init__(task_message)
        self.self_cleanup = True
        self.limit = limit
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
            expired_thumbnails = self.get_expired_thumbnails()
            thumbnail_book_ids = self.get_thumbnail_book_ids()
            books_without_thumbnails = self.get_books_without_thumbnails(thumbnail_book_ids)

            count = len(books_without_thumbnails)
            for i, book in enumerate(books_without_thumbnails):
                for resolution in self.resolutions:
                    expired_thumbnail = self.get_expired_thumbnail_for_book_and_resolution(
                        book,
                        resolution,
                        expired_thumbnails
                    )
                    if expired_thumbnail:
                        self.update_book_thumbnail(book, expired_thumbnail)
                    else:
                        self.create_book_thumbnail(book, resolution)

                self.progress = (1.0 / count) * i

        self._handleSuccess()
        self.app_db_session.remove()

    def get_expired_thumbnails(self):
        return self.app_db_session\
            .query(ub.Thumbnail)\
            .filter(ub.Thumbnail.expiration < datetime.utcnow())\
            .all()

    def get_thumbnail_book_ids(self):
        return self.app_db_session\
            .query(ub.Thumbnail.book_id)\
            .group_by(ub.Thumbnail.book_id)\
            .having(func.min(ub.Thumbnail.expiration) > datetime.utcnow())\
            .distinct()

    def get_books_without_thumbnails(self, thumbnail_book_ids):
        return self.calibre_db.session\
            .query(db.Books)\
            .filter(db.Books.has_cover == 1)\
            .filter(db.Books.id.notin_(thumbnail_book_ids))\
            .limit(self.limit)\
            .all()

    def get_expired_thumbnail_for_book_and_resolution(self, book, resolution, expired_thumbnails):
        for thumbnail in expired_thumbnails:
            if thumbnail.book_id == book.id and thumbnail.resolution == resolution:
                return thumbnail

        return None

    def update_book_thumbnail(self, book, thumbnail):
        thumbnail.generated_at = datetime.utcnow()
        thumbnail.expiration = datetime.utcnow() + timedelta(days=30)

        try:
            self.app_db_session.commit()
            self.generate_book_thumbnail(book, thumbnail)
        except Exception as ex:
            self.log.info(u'Error updating book thumbnail: ' + str(ex))
            self._handleError(u'Error updating book thumbnail: ' + str(ex))
            self.app_db_session.rollback()

    def create_book_thumbnail(self, book, resolution):
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
        return "GenerateCoverThumbnails"


class TaskCleanupCoverThumbnailCache(CalibreTask):
    def __init__(self, task_message=u'Validating cover thumbnail cache'):
        super(TaskCleanupCoverThumbnailCache, self).__init__(task_message)
        self.log = logger.create()
        self.app_db_session = ub.get_new_session_instance()
        self.calibre_db = db.CalibreDB(expire_on_commit=False)
        self.cache = fs.FileSystem()

    def run(self, worker_thread):
        cached_thumbnail_files = self.cache.list_cache_files(fs.CACHE_TYPE_THUMBNAILS)

        # Expire thumbnails in the database if the cached file is missing
        # This case will happen if a user deletes the cache dir or cached files
        if self.app_db_session:
            self.expire_missing_thumbnails(cached_thumbnail_files)
            self.progress = 0.33

        # Delete thumbnails in the database if the book has been removed
        # This case will happen if a book is removed in Calibre and the metadata.db file is updated in the filesystem
        if self.app_db_session and self.calibre_db:
            book_ids = self.get_book_ids()
            self.delete_thumbnails_for_missing_books(book_ids)
            self.progress = 0.66

        # Delete extraneous cached thumbnail files
        # This case will happen if a book was deleted and the thumbnail OR the metadata.db file was changed externally
        if self.app_db_session:
            db_thumbnail_files = self.get_thumbnail_filenames()
            self.delete_extraneous_thumbnail_files(cached_thumbnail_files, db_thumbnail_files)

        self._handleSuccess()
        self.app_db_session.remove()

    def expire_missing_thumbnails(self, filenames):
        try:
            self.app_db_session\
                .query(ub.Thumbnail)\
                .filter(ub.Thumbnail.filename.notin_(filenames))\
                .update({"expiration": datetime.utcnow()}, synchronize_session=False)
            self.app_db_session.commit()
        except Exception as ex:
            self.log.info(u'Error expiring thumbnails for missing cache files: ' + str(ex))
            self._handleError(u'Error expiring thumbnails for missing cache files: ' + str(ex))
            self.app_db_session.rollback()

    def get_book_ids(self):
        results = self.calibre_db.session\
            .query(db.Books.id)\
            .filter(db.Books.has_cover == 1)\
            .distinct()

        return [value for value, in results]

    def delete_thumbnails_for_missing_books(self, book_ids):
        try:
            self.app_db_session\
                .query(ub.Thumbnail)\
                .filter(ub.Thumbnail.book_id.notin_(book_ids))\
                .delete(synchronize_session=False)
            self.app_db_session.commit()
        except Exception as ex:
            self.log.info(str(ex))
            self._handleError(u'Error deleting thumbnails for missing books: ' + str(ex))
            self.app_db_session.rollback()

    def get_thumbnail_filenames(self):
        results = self.app_db_session\
            .query(ub.Thumbnail.filename)\
            .all()

        return [thumbnail for thumbnail, in results]

    def delete_extraneous_thumbnail_files(self, cached_thumbnail_files, db_thumbnail_files):
        extraneous_files = list(set(cached_thumbnail_files).difference(db_thumbnail_files))
        for file in extraneous_files:
            self.cache.delete_cache_file(file, fs.CACHE_TYPE_THUMBNAILS)

    @property
    def name(self):
        return "CleanupCoverThumbnailCache"
