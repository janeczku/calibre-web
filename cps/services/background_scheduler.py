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
import atexit

from .. import logger
from .worker import WorkerThread

try:
    from apscheduler.schedulers.background import BackgroundScheduler as BScheduler
    use_APScheduler = True
except (ImportError, RuntimeError) as e:
    use_APScheduler = False
    log = logger.create()
    log.info('APScheduler not found. Unable to schedule tasks.')


class BackgroundScheduler:
    _instance = None

    def __new__(cls):
        if not use_APScheduler:
            return False

        if cls._instance is None:
            cls._instance = super(BackgroundScheduler, cls).__new__(cls)

            scheduler = BScheduler()
            atexit.register(lambda: scheduler.shutdown())

            cls.log = logger.create()
            cls.scheduler = scheduler
            cls.scheduler.start()

        return cls._instance

    def add(self, func, trigger, **trigger_args):
        if use_APScheduler:
            return self.scheduler.add_job(func=func, trigger=trigger, **trigger_args)

    def add_task(self, user, task, trigger, **trigger_args):
        if use_APScheduler:
            def scheduled_task():
                worker_task = task()
                self.log.info(f'Running scheduled task in background: {worker_task.name} - {worker_task.message}')
                WorkerThread.add(user, worker_task)

            return self.add(func=scheduled_task, trigger=trigger, **trigger_args)
