
from __future__ import division, print_function, unicode_literals
import threading

try:
    import queue
except ImportError:
    import Queue as queue
from datetime import datetime

from cps import calibre_db
from cps import logger
import abc

log = logger.create()

# task 'status' consts
STAT_WAITING = 0
STAT_FAIL = 1
STAT_STARTED = 2
STAT_FINISH_SUCCESS = 3


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

#Class for all worker tasks in the background
class WorkerThread(threading.Thread):
    _instance = None

    @classmethod
    def getInstance(cls):
        if cls._instance is None:
            cls._instance = WorkerThread()
        return cls._instance

    def __init__(self):
        threading.Thread.__init__(self)

        self.finished = list()

        self.db_queue = queue.Queue()
        calibre_db.add_queue(self.db_queue)

        self.doLock = threading.Lock()
        self.queue = ImprovedQueue()

        self.start()

    @classmethod
    def add(cls, user, task):
        ins = cls.getInstance()
        ins.queue.put((user, task))

    @property
    def tasks(self):
        with self.doLock:
            tasks = list(self.queue.to_list()) + self.finished
        return tasks  # todo: order by data added

    # Main thread loop starting the different tasks
    def run(self):
        main_thread = _get_main_thread()
        while main_thread.is_alive():
            user, item = self.queue.get()

            # add to list so that in-progress tasks show up
            with self.doLock:
                self.finished.append((user, item))

            # sometimes tasks (like Upload) don't actually have work to do and are created as already finished
            if item.stat is STAT_WAITING:
                # CalibreTask.start() should wrap all exceptions in it's own error handling
                item.start(self)

            self.queue.task_done()

    def _delete_completed_tasks(self):
        raise NotImplementedError()
        # for index, task in reversed(list(enumerate(self.UIqueue))):
        #     if task['progress'] == "100 %":
        #         # delete tasks
        #         self.queue.pop(index)
        #         self.UIqueue.pop(index)
        #         # if we are deleting entries before the current index, adjust the index
        #         if index <= self.current and self.current:
        #             self.current -= 1
        # self.last = len(self.queue)

class CalibreTask:
    __metaclass__ = abc.ABCMeta

    def __init__(self, message):
        self._progress = 0
        self.stat = STAT_WAITING
        self.error = None
        self.start_time = None
        self.end_time = None
        self.message = message

    @abc.abstractmethod
    def run(self, worker_thread):
        """Provides the caller some human-readable name for this class"""
        raise NotImplementedError

    @abc.abstractmethod
    def name(self):
        """Provides the caller some human-readable name for this class"""
        raise NotImplementedError

    def start(self, *args):
        self.start_time = datetime.now()
        self.stat = STAT_STARTED

        # catch any unhandled exceptions in a task and automatically fail it
        try:
            self.run(*args)
        except Exception as e:
            self._handleError(str(e))
            log.exception(e)

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

    @progress.setter
    def progress(self, x):
        # todo: throw error if outside of [0,1]
        self._progress = x

    def _handleError(self, error_message):
        log.error(error_message)
        self.stat = STAT_FAIL
        self.progress = 1
        self.error = error_message

    def _handleSuccess(self):
        self.stat = STAT_FINISH_SUCCESS
        self.progress = 1
