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

from .services.background_scheduler import BackgroundScheduler
from .tasks.database import TaskReconnectDatabase
from .tasks.thumbnail import TaskSyncCoverThumbnailCache, TaskGenerateCoverThumbnails


def register_jobs():
    scheduler = BackgroundScheduler()

    # Generate 100 book cover thumbnails every 5 minutes
    scheduler.add_task(user=None, task=lambda: TaskGenerateCoverThumbnails(limit=100), trigger='cron', minute='*/5')

    # Cleanup book cover cache every 6 hours
    scheduler.add_task(user=None, task=lambda: TaskSyncCoverThumbnailCache(), trigger='cron', minute='15', hour='*/6')

    # Reconnect metadata.db every 4 hours
    scheduler.add_task(user=None, task=lambda: TaskReconnectDatabase(), trigger='cron', minute='5', hour='*/4')
