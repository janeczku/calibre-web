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

from . import logger, ub
from .constants import CACHE_DIR as _CACHE_DIR
from .services.worker import WorkerThread
from .tasks.thumbnail import TaskThumbnail

from datetime import datetime

THUMBNAIL_RESOLUTION_1X = 1.0
THUMBNAIL_RESOLUTION_2X = 2.0

log = logger.create()


def get_thumbnail_cache_dir():
    if not os.path.isdir(_CACHE_DIR):
        os.makedirs(_CACHE_DIR)

    if not os.path.isdir(os.path.join(_CACHE_DIR, 'thumbnails')):
        os.makedirs(os.path.join(_CACHE_DIR, 'thumbnails'))

    return os.path.join(_CACHE_DIR, 'thumbnails')


def get_thumbnail_cache_path(thumbnail):
    if thumbnail:
        return os.path.join(get_thumbnail_cache_dir(), thumbnail.filename)

    return None


def cover_thumbnail_exists_for_book(book):
    if book and book.has_cover:
        thumbnail = ub.session.query(ub.Thumbnail).filter(ub.Thumbnail.book_id == book.id).first()
        if thumbnail and thumbnail.expiration > datetime.utcnow():
            thumbnail_path = get_thumbnail_cache_path(thumbnail)
            return thumbnail_path and os.path.isfile(thumbnail_path)

    return False


def generate_thumbnails():
    WorkerThread.add(None, TaskThumbnail())
