# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2020 pwr
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program. If not, see <http://www.gnu.org/licenses/>.

import threading
import abc
import uuid
import time

try:
    import queue
except ImportError:
    import Queue as queue
from datetime import datetime
from collections import namedtuple

from cps import logger

log = logger.create()

# task 'status' consts
STAT_WAITING = 0
STAT_FAIL = 1
STAT_STARTED = 2
STAT_FINISH_SUCCESS = 3
STAT_ENDED = 4
STAT_CANCELLED = 5

# Only retain this many tasks in dequeued list
TASK_CLEANUP_TRIGGER = 20

QueuedTask = namedtuple('QueuedTask', 'num, user, added, task, hidden')


def _get_main_thread():
    for t in threading.enumerate():
        if t.__class__.__name__ == '_MainThread':
            return t
    raise Exception("main thread not found?!")


class ImprovedQueue(queue.Queue):
    def to_list(self):
        """
        Returns a copy of all items in the queue without removing them.
        """

        with self.mutex:
            return list(self.queue)


# Class for all worker tasks in the background
class WorkerThread(threading.Thread):
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = WorkerThread()
        return cls._instance

    def __init__(self):
        threading.Thread.__init__(self)

        self.dequeued = list()

        self.doLock = threading.Lock()
        self.queue = ImprovedQueue()
        self.num = 0
        self.start()

    @classmethod
    def add(cls, user, task, hidden=False):
        ins = cls.get_instance()
        ins.num += 1
        username = user if user is not None else 'System'
        log.debug("Add Task for user: {} - {}".format(username, task))
        ins.queue.put(QueuedTask(
            num=ins.num,
            user=username,
            added=datetime.now(),
            task=task,
            hidden=hidden
        ))

    @property
    def tasks(self):
        with self.doLock:
            tasks = self.queue.to_list() + self.dequeued
            return sorted(tasks, key=lambda x: x.num)

    def cleanup_tasks(self):
        with self.doLock:
            dead = []
            alive = []
            for x in self.dequeued:
                (dead if x.task.dead else alive).append(x)

            # if the ones that we need to keep are within the trigger, do nothing else
            delta = len(self.dequeued) - len(dead)
            if delta > TASK_CLEANUP_TRIGGER:
                ret = alive
            else:
                # otherwise, loop off the oldest dead tasks until we hit the target trigger
                ret = sorted(dead, key=lambda y: y.task.end_time)[-TASK_CLEANUP_TRIGGER:] + alive

            self.dequeued = sorted(ret, key=lambda y: y.num)

    # Main thread loop starting the different tasks
    def run(self):
        main_thread = _get_main_thread()
        while main_thread.is_alive():
            try:
                # this blocks until something is available. This can cause issues when the main thread dies - this
                # thread will remain alive. We implement a timeout to unblock every second which allows us to check if
                # the main thread is still alive.
                # We don't use a daemon here because we don't want the tasks to just be abruptly halted, leading to
                # possible file / database corruption
                item = self.queue.get(timeout=1)
            except queue.Empty:
                time.sleep(1)
                continue

            with self.doLock:
                # add to list so that in-progress tasks show up
                self.dequeued.append(item)

            # once we hit our trigger, start cleaning up dead tasks
            if len(self.dequeued) > TASK_CLEANUP_TRIGGER:
                self.cleanup_tasks()

            # sometimes tasks (like Upload) don't actually have work to do and are created as already finished
            if item.task.stat is STAT_WAITING:
                # CalibreTask.start() should wrap all exceptions in its own error handling
                item.task.start(self)

            # remove self_cleanup tasks and hidden "System Tasks" from list
            if item.task.self_cleanup or item.hidden:
                self.dequeued.remove(item)

            self.queue.task_done()

    def end_task(self, task_id):
        ins = self.get_instance()
        for __, __, __, task, __ in ins.tasks:
            if str(task.id) == str(task_id) and task.is_cancellable:
                task.stat = STAT_CANCELLED if task.stat == STAT_WAITING else STAT_ENDED


class CalibreTask:
    __metaclass__ = abc.ABCMeta

    def __init__(self, message):
        self._progress = 0
        self.stat = STAT_WAITING
        self.error = None
        self.start_time = None
        self.end_time = None
        self.message = message
        self.id = uuid.uuid4()
        self.self_cleanup = False
        self._scheduled = False

    @abc.abstractmethod
    def run(self, worker_thread):
        """The main entry-point for this task"""
        raise NotImplementedError

    @abc.abstractmethod
    def name(self):
        """Provides the caller some human-readable name for this class"""
        raise NotImplementedError

    @abc.abstractmethod
    def is_cancellable(self):
        """Does this task gracefully handle being cancelled (STAT_ENDED, STAT_CANCELLED)?"""
        raise NotImplementedError

    def start(self, *args):
        self.start_time = datetime.now()
        self.stat = STAT_STARTED

        # catch any unhandled exceptions in a task and automatically fail it
        try:
            self.run(*args)
        except Exception as ex:
            self._handleError(str(ex))
            log.error_or_exception(ex)

        self.end_time = datetime.now()

    @property
    def stat(self):
        return self._stat

    @stat.setter
    def stat(self, x):
        self._stat = x

    @property
    def progress(self):
        return self._progress

    @progress.setter
    def progress(self, x):
        if not 0 <= x <= 1:
            raise ValueError("Task progress should within [0, 1] range")
        self._progress = x

    @property
    def error(self):
        return self._error

    @error.setter
    def error(self, x):
        self._error = x

    @property
    def runtime(self):
        return (self.end_time or datetime.now()) - self.start_time

    @property
    def dead(self):
        """Determines whether or not this task can be garbage collected

        We have a separate dictating this because there may be certain tasks that want to override this
        """
        # By default, we're good to clean a task if it's "Done"
        return self.stat in (STAT_FINISH_SUCCESS, STAT_FAIL, STAT_ENDED, STAT_CANCELLED)

    @property
    def self_cleanup(self):
        return self._self_cleanup

    @self_cleanup.setter
    def self_cleanup(self, is_self_cleanup):
        self._self_cleanup = is_self_cleanup

    @property
    def scheduled(self):
        return self._scheduled

    @scheduled.setter
    def scheduled(self, is_scheduled):
        self._scheduled = is_scheduled

    def _handleError(self, error_message):
        self.stat = STAT_FAIL
        self.progress = 1
        self.error = error_message

    def _handleSuccess(self):
        self.stat = STAT_FINISH_SUCCESS
        self.progress = 1

    def __str__(self):
        return self.name
