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

from . import logger
from .services.background_scheduler import BackgroundScheduler
from .tasks.thumbnail import TaskThumbnail

log = logger.create()


def register_jobs():
    scheduler = BackgroundScheduler()

    # Generate 100 book cover thumbnails every 5 minutes
    scheduler.add_task(user=None, task=lambda: TaskThumbnail(limit=100), trigger='interval', minutes=5)

    # TODO: validate thumbnail scheduled task
