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

import datetime

from . import config, constants
from .services.background_scheduler import BackgroundScheduler
from .tasks.database import TaskReconnectDatabase
from .tasks.thumbnail import TaskGenerateCoverThumbnails, TaskGenerateSeriesThumbnails
from .services.worker import WorkerThread


def get_scheduled_tasks(reconnect=True):
    tasks = list()

    # Reconnect Calibre database (metadata.db)
    if reconnect:
        tasks.append([lambda: TaskReconnectDatabase(), 'reconnect'])

    # Generate all missing book cover thumbnails
    if config.schedule_generate_book_covers:
        tasks.append([lambda: TaskGenerateCoverThumbnails(), 'generate book covers'])

    # Generate all missing series thumbnails
    if config.schedule_generate_series_covers:
        tasks.append([lambda: TaskGenerateSeriesThumbnails(), 'generate book covers'])

    return tasks


def end_scheduled_tasks():
    worker = WorkerThread.get_instance()
    for __, __, __, task, __ in worker.tasks:
        if task.scheduled and task.is_cancellable:
            worker.end_task(task.id)


def register_scheduled_tasks():
    scheduler = BackgroundScheduler()

    if scheduler:
        # Remove all existing jobs
        scheduler.remove_all_jobs()

        start = config.schedule_start_time
        end = config.schedule_end_time

        # Register scheduled tasks
        if start != end:
            scheduler.schedule_tasks(tasks=get_scheduled_tasks(), trigger='cron', hour=start)
            scheduler.schedule(func=end_scheduled_tasks, trigger='cron', name="end scheduled task", hour=end)

        # Kick-off tasks, if they should currently be running
        if should_task_be_running(start, end):
            scheduler.schedule_tasks_immediately(tasks=get_scheduled_tasks(False))


def register_startup_tasks():
    scheduler = BackgroundScheduler()

    if scheduler:
        start = config.schedule_start_time
        end = config.schedule_end_time

        # Run scheduled tasks immediately for development and testing
        # Ignore tasks that should currently be running, as these will be added when registering scheduled tasks
        if constants.APP_MODE in ['development', 'test'] and not should_task_be_running(start, end):
            scheduler.schedule_tasks_immediately(tasks=get_scheduled_tasks(False))


def should_task_be_running(start, end):
    now = datetime.datetime.now().hour
    return (start < end and start <= now < end) or (end < start <= now or now < end)
