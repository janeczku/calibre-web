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

from datetime import datetime
from .services.background_scheduler import BackgroundScheduler
from .tasks.database import TaskReconnectDatabase
from .tasks.thumbnail import TaskSyncCoverThumbnailCache, TaskGenerateCoverThumbnails


def register_jobs():
    scheduler = BackgroundScheduler()

    if scheduler:
        # Reconnect metadata.db once every 12 hours
        scheduler.add_task(user=None, task=lambda: TaskReconnectDatabase(), trigger='interval', hours=12)

        # Cleanup book cover cache once every 24 hours
        scheduler.add_task(user=None, task=lambda: TaskSyncCoverThumbnailCache(), trigger='interval', days=1)

        # Generate all missing book cover thumbnails once every 24 hours
        scheduler.add_task(user=None, task=lambda: TaskGenerateCoverThumbnails(), trigger='interval', days=1)
