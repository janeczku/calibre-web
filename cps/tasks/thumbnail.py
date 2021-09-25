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

from .. import constants
from cps import config, db, fs, gdriveutils, logger, ub
from cps.services.worker import CalibreTask
from datetime import datetime, timedelta
from sqlalchemy import func, text, or_

try:
    from urllib.request import urlopen
except ImportError as e:
    from urllib2 import urlopen

try:
    from wand.image import Image
    use_IM = True
except (ImportError, RuntimeError) as e:
    use_IM = False


def get_resize_height(resolution):
    return int(225 * resolution)


def get_resize_width(resolution, original_width, original_height):
    height = get_resize_height(resolution)
    percent = (height / float(original_height))
    width = int((float(original_width) * float(percent)))
    return width if width % 2 == 0 else width + 1


def get_best_fit(width, height, image_width, image_height):
    resize_width = int(width / 2.0)
    resize_height = int(height / 2.0)
    aspect_ratio = image_width / image_height

    # If this image's aspect ratio is different than the first image, then resize this image
    # to fill the width and height of the first image
    if aspect_ratio < width / height:
        resize_width = int(width / 2.0)
        resize_height = image_height * int(width / 2.0) / image_width

    elif aspect_ratio > width / height:
        resize_width = image_width * int(height / 2.0) / image_height
        resize_height = int(height / 2.0)

    return {'width': resize_width, 'height': resize_height}


class TaskGenerateCoverThumbnails(CalibreTask):
    def __init__(self, task_message=u'Generating cover thumbnails'):
        super(TaskGenerateCoverThumbnails, self).__init__(task_message)
        self.log = logger.create()
        self.app_db_session = ub.get_new_session_instance()
        self.calibre_db = db.CalibreDB(expire_on_commit=False)
        self.cache = fs.FileSystem()
        self.resolutions = [
            constants.COVER_THUMBNAIL_SMALL,
            constants.COVER_THUMBNAIL_MEDIUM
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

                    elif not self.cache.get_cache_file_exists(thumbnail.filename, constants.CACHE_TYPE_THUMBNAILS):
                        updated += 1
                        self.update_book_cover_thumbnail(book, thumbnail)

                self.message = u'Processing book {0} of {1}'.format(i + 1, count)
                self.progress = (1.0 / count) * i

        self._handleSuccess()
        self.app_db_session.remove()

    def get_books_with_covers(self):
        return self.calibre_db.session \
            .query(db.Books) \
            .filter(db.Books.has_cover == 1) \
            .all()

    def get_book_cover_thumbnails(self, book_id):
        return self.app_db_session \
            .query(ub.Thumbnail) \
            .filter(ub.Thumbnail.type == constants.THUMBNAIL_TYPE_COVER) \
            .filter(ub.Thumbnail.entity_id == book_id) \
            .filter(or_(ub.Thumbnail.expiration.is_(None), ub.Thumbnail.expiration > datetime.utcnow())) \
            .all()

    def create_book_cover_thumbnail(self, book, resolution):
        thumbnail = ub.Thumbnail()
        thumbnail.type = constants.THUMBNAIL_TYPE_COVER
        thumbnail.entity_id = book.id
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
            self.cache.delete_cache_file(thumbnail.filename, constants.CACHE_TYPE_THUMBNAILS)
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
                            filename = self.cache.get_cache_file_path(thumbnail.filename,
                                                                      constants.CACHE_TYPE_THUMBNAILS)
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
                    height = get_resize_height(thumbnail.resolution)
                    if img.height > height:
                        width = get_resize_width(thumbnail.resolution, img.width, img.height)
                        img.resize(width=width, height=height, filter='lanczos')
                        img.format = thumbnail.format
                        filename = self.cache.get_cache_file_path(thumbnail.filename, constants.CACHE_TYPE_THUMBNAILS)
                        img.save(filename=filename)

    @property
    def name(self):
        return "ThumbnailsGenerate"


class TaskGenerateSeriesThumbnails(CalibreTask):
    def __init__(self, task_message=u'Generating series thumbnails'):
        super(TaskGenerateSeriesThumbnails, self).__init__(task_message)
        self.log = logger.create()
        self.app_db_session = ub.get_new_session_instance()
        self.calibre_db = db.CalibreDB(expire_on_commit=False)
        self.cache = fs.FileSystem()
        self.resolutions = [
            constants.COVER_THUMBNAIL_SMALL,
            constants.COVER_THUMBNAIL_MEDIUM
        ]

    # get all series
    # get all books in series with covers and count >= 4 books
    # get the dimensions from the first book in the series & pop the first book from the series list of books
    # randomly select three other books in the series

    # resize the covers in the sequence?
    # create an image sequence from the 4 selected books of the series
    # join pairs of books in the series with wand's concat
    # join the two sets of pairs with wand's

    def run(self, worker_thread):
        if self.calibre_db.session and use_IM:
            all_series = self.get_series_with_four_plus_books()
            count = len(all_series)

            updated = 0
            generated = 0
            for i, series in enumerate(all_series):
                series_thumbnails = self.get_series_thumbnails(series.id)
                series_books = self.get_series_books(series.id)

                # Generate new thumbnails for missing covers
                resolutions = list(map(lambda t: t.resolution, series_thumbnails))
                missing_resolutions = list(set(self.resolutions).difference(resolutions))
                for resolution in missing_resolutions:
                    generated += 1
                    self.create_series_thumbnail(series, series_books, resolution)

                # Replace outdated or missing thumbnails
                for thumbnail in series_thumbnails:
                    if any(book.last_modified > thumbnail.generated_at for book in series_books):
                        updated += 1
                        self.update_series_thumbnail(series_books, thumbnail)

                    elif not self.cache.get_cache_file_exists(thumbnail.filename, constants.CACHE_TYPE_THUMBNAILS):
                        updated += 1
                        self.update_series_thumbnail(series_books, thumbnail)

                self.message = u'Processing series {0} of {1}'.format(i + 1, count)
                self.progress = (1.0 / count) * i

        self._handleSuccess()
        self.app_db_session.remove()

    def get_series_with_four_plus_books(self):
        return self.calibre_db.session \
            .query(db.Series) \
            .join(db.books_series_link) \
            .join(db.Books) \
            .filter(db.Books.has_cover == 1) \
            .group_by(text('books_series_link.series')) \
            .having(func.count('book_series_link') > 3) \
            .all()

    def get_series_books(self, series_id):
        return self.calibre_db.session \
            .query(db.Books) \
            .join(db.books_series_link) \
            .join(db.Series) \
            .filter(db.Books.has_cover == 1) \
            .filter(db.Series.id == series_id) \
            .all()

    def get_series_thumbnails(self, series_id):
        return self.app_db_session \
            .query(ub.Thumbnail) \
            .filter(ub.Thumbnail.type == constants.THUMBNAIL_TYPE_SERIES) \
            .filter(ub.Thumbnail.entity_id == series_id) \
            .filter(or_(ub.Thumbnail.expiration.is_(None), ub.Thumbnail.expiration > datetime.utcnow())) \
            .all()

    def create_series_thumbnail(self, series, series_books, resolution):
        thumbnail = ub.Thumbnail()
        thumbnail.type = constants.THUMBNAIL_TYPE_SERIES
        thumbnail.entity_id = series.id
        thumbnail.format = 'jpeg'
        thumbnail.resolution = resolution

        self.app_db_session.add(thumbnail)
        try:
            self.app_db_session.commit()
            self.generate_series_thumbnail(series_books, thumbnail)
        except Exception as ex:
            self.log.info(u'Error creating book thumbnail: ' + str(ex))
            self._handleError(u'Error creating book thumbnail: ' + str(ex))
            self.app_db_session.rollback()

    def update_series_thumbnail(self, series_books, thumbnail):
        thumbnail.generated_at = datetime.utcnow()

        try:
            self.app_db_session.commit()
            self.cache.delete_cache_file(thumbnail.filename, constants.CACHE_TYPE_THUMBNAILS)
            self.generate_series_thumbnail(series_books, thumbnail)
        except Exception as ex:
            self.log.info(u'Error updating book thumbnail: ' + str(ex))
            self._handleError(u'Error updating book thumbnail: ' + str(ex))
            self.app_db_session.rollback()

    def generate_series_thumbnail(self, series_books, thumbnail):
        books = series_books[:4]

        top = 0
        left = 0
        width = 0
        height = 0
        with Image() as canvas:
            for book in books:
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
                            # Use the first image in this set to determine the width and height to scale the
                            # other images in this set
                            if width == 0 or height == 0:
                                width = get_resize_width(thumbnail.resolution, img.width, img.height)
                                height = get_resize_height(thumbnail.resolution)
                                canvas.blank(width, height)

                            dimensions = get_best_fit(width, height, img.width, img.height)

                            # resize and crop the image
                            img.resize(width=int(dimensions['width']), height=int(dimensions['height']), filter='lanczos')
                            img.crop(width=int(width / 2.0), height=int(height / 2.0), gravity='center')

                            # add the image to the canvas
                            canvas.composite(img, left, top)

                    except Exception as ex:
                        self.log.info(u'Error generating thumbnail file: ' + str(ex))
                        raise ex
                    finally:
                        stream.close()

                book_cover_filepath = os.path.join(config.config_calibre_dir, book.path, 'cover.jpg')
                if not os.path.isfile(book_cover_filepath):
                    raise Exception('Book cover file not found')

                with Image(filename=book_cover_filepath) as img:
                    # Use the first image in this set to determine the width and height to scale the
                    # other images in this set
                    if width == 0 or height == 0:
                        width = get_resize_width(thumbnail.resolution, img.width, img.height)
                        height = get_resize_height(thumbnail.resolution)
                        canvas.blank(width, height)

                    dimensions = get_best_fit(width, height, img.width, img.height)

                    # resize and crop the image
                    img.resize(width=int(dimensions['width']), height=int(dimensions['height']), filter='lanczos')
                    img.crop(width=int(width / 2.0), height=int(height / 2.0), gravity='center')

                    # add the image to the canvas
                    canvas.composite(img, left, top)

                # set the coordinates for the next iteration
                if left == 0 and top == 0:
                    left = int(width / 2.0)
                elif left == int(width / 2.0) and top == 0:
                    left = 0
                    top = int(height / 2.0)
                else:
                    left = int(width / 2.0)

            canvas.format = thumbnail.format
            filename = self.cache.get_cache_file_path(thumbnail.filename, constants.CACHE_TYPE_THUMBNAILS)
            canvas.save(filename=filename)

    @property
    def name(self):
        return "SeriesThumbnailGenerate"


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
        return self.app_db_session \
            .query(ub.Thumbnail) \
            .filter(ub.Thumbnail.type == constants.THUMBNAIL_TYPE_COVER) \
            .filter(ub.Thumbnail.entity_id == book_id) \
            .all()

    def delete_thumbnail(self, thumbnail):
        try:
            self.cache.delete_cache_file(thumbnail.filename, constants.CACHE_TYPE_THUMBNAILS)
        except Exception as ex:
            self.log.info(u'Error deleting book thumbnail: ' + str(ex))
            self._handleError(u'Error deleting book thumbnail: ' + str(ex))

    def delete_all_thumbnails(self):
        try:
            self.cache.delete_cache_dir(constants.CACHE_TYPE_THUMBNAILS)
        except Exception as ex:
            self.log.info(u'Error deleting book thumbnails: ' + str(ex))
            self._handleError(u'Error deleting book thumbnails: ' + str(ex))

    @property
    def name(self):
        return "ThumbnailsClear"
