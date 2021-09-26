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
from .tasks.thumbnail import TaskGenerateCoverThumbnails, TaskGenerateSeriesThumbnails


def register_jobs():
    scheduler = BackgroundScheduler()

    if scheduler:
        # Reconnect Calibre database (metadata.db)
        scheduler.schedule_task(user=None, task=lambda: TaskReconnectDatabase(), trigger='cron', hour='4,16')

        # Generate all missing book cover thumbnails
        scheduler.schedule_task(user=None, task=lambda: TaskGenerateCoverThumbnails(), trigger='cron', hour=4)

        # Generate all missing series thumbnails
        scheduler.schedule_task(user=None, task=lambda: TaskGenerateSeriesThumbnails(), trigger='cron', hour=4)


def register_startup_jobs():
    scheduler = BackgroundScheduler()

    if scheduler:
        scheduler.schedule_task_immediately(None, task=lambda: TaskGenerateCoverThumbnails())
        scheduler.schedule_task_immediately(None, task=lambda: TaskGenerateSeriesThumbnails())
