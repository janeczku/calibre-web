# util/queue.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""An adaptation of Py2.3/2.4's Queue module which supports reentrant
behavior, using RLock instead of Lock for its mutex object.  The
Queue object is used exclusively by the sqlalchemy.pool.QueuePool
class.

This is to support the connection pool's usage of weakref callbacks to return
connections to the underlying Queue, which can in extremely
rare cases be invoked within the ``get()`` method of the Queue itself,
producing a ``put()`` inside the ``get()`` and therefore a reentrant
condition.

An additional change includes a special "abort" method which can be used
to immediately raise a special exception for threads that are blocking
on get().  This is to accommodate a rare race condition that can occur
within QueuePool.

"""

from collections import deque
from time import time as _time
from .compat import threading
import sys

if sys.version_info < (2, 6):
    def notify_all(condition):
        condition.notify()
else:
    def notify_all(condition):
        condition.notify_all()

__all__ = ['Empty', 'Full', 'Queue', 'SAAbort']


class Empty(Exception):
    "Exception raised by Queue.get(block=0)/get_nowait()."

    pass


class Full(Exception):
    "Exception raised by Queue.put(block=0)/put_nowait()."

    pass


class SAAbort(Exception):
    "Special SQLA exception to abort waiting"
    def __init__(self, context):
        self.context = context


class Queue:
    def __init__(self, maxsize=0):
        """Initialize a queue object with a given maximum size.

        If `maxsize` is <= 0, the queue size is infinite.
        """

        self._init(maxsize)
        # mutex must be held whenever the queue is mutating.  All methods
        # that acquire mutex must release it before returning.  mutex
        # is shared between the two conditions, so acquiring and
        # releasing the conditions also acquires and releases mutex.
        self.mutex = threading.RLock()
        # Notify not_empty whenever an item is added to the queue; a
        # thread waiting to get is notified then.
        self.not_empty = threading.Condition(self.mutex)
        # Notify not_full whenever an item is removed from the queue;
        # a thread waiting to put is notified then.
        self.not_full = threading.Condition(self.mutex)

        # when this is set, SAAbort is raised within get().
        self._sqla_abort_context = False

    def qsize(self):
        """Return the approximate size of the queue (not reliable!)."""

        self.mutex.acquire()
        n = self._qsize()
        self.mutex.release()
        return n

    def empty(self):
        """Return True if the queue is empty, False otherwise (not
        reliable!)."""

        self.mutex.acquire()
        n = self._empty()
        self.mutex.release()
        return n

    def full(self):
        """Return True if the queue is full, False otherwise (not
        reliable!)."""

        self.mutex.acquire()
        n = self._full()
        self.mutex.release()
        return n

    def put(self, item, block=True, timeout=None):
        """Put an item into the queue.

        If optional args `block` is True and `timeout` is None (the
        default), block if necessary until a free slot is
        available. If `timeout` is a positive number, it blocks at
        most `timeout` seconds and raises the ``Full`` exception if no
        free slot was available within that time.  Otherwise (`block`
        is false), put an item on the queue if a free slot is
        immediately available, else raise the ``Full`` exception
        (`timeout` is ignored in that case).
        """

        self.not_full.acquire()
        try:
            if not block:
                if self._full():
                    raise Full
            elif timeout is None:
                while self._full():
                    self.not_full.wait()
            else:
                if timeout < 0:
                    raise ValueError("'timeout' must be a positive number")
                endtime = _time() + timeout
                while self._full():
                    remaining = endtime - _time()
                    if remaining <= 0.0:
                        raise Full
                    self.not_full.wait(remaining)
            self._put(item)
            self.not_empty.notify()
        finally:
            self.not_full.release()

    def put_nowait(self, item):
        """Put an item into the queue without blocking.

        Only enqueue the item if a free slot is immediately available.
        Otherwise raise the ``Full`` exception.
        """
        return self.put(item, False)

    def get(self, block=True, timeout=None):
        """Remove and return an item from the queue.

        If optional args `block` is True and `timeout` is None (the
        default), block if necessary until an item is available. If
        `timeout` is a positive number, it blocks at most `timeout`
        seconds and raises the ``Empty`` exception if no item was
        available within that time.  Otherwise (`block` is false),
        return an item if one is immediately available, else raise the
        ``Empty`` exception (`timeout` is ignored in that case).
        """

        self.not_empty.acquire()
        try:
            if not block:
                if self._empty():
                    raise Empty
            elif timeout is None:
                while self._empty():
                    self.not_empty.wait()
                    if self._sqla_abort_context:
                        raise SAAbort(self._sqla_abort_context)
            else:
                if timeout < 0:
                    raise ValueError("'timeout' must be a positive number")
                endtime = _time() + timeout
                while self._empty():
                    remaining = endtime - _time()
                    if remaining <= 0.0:
                        raise Empty
                    self.not_empty.wait(remaining)
                    if self._sqla_abort_context:
                        raise SAAbort(self._sqla_abort_context)
            item = self._get()
            self.not_full.notify()
            return item
        finally:
            self.not_empty.release()

    def abort(self, context):
        """Issue an 'abort', will force any thread waiting on get()
        to stop waiting and raise SAAbort.

        """
        self._sqla_abort_context = context
        if not self.not_full.acquire(False):
            return
        try:
            notify_all(self.not_empty)
        finally:
            self.not_full.release()

    def get_nowait(self):
        """Remove and return an item from the queue without blocking.

        Only get an item if one is immediately available. Otherwise
        raise the ``Empty`` exception.
        """

        return self.get(False)

    # Override these methods to implement other queue organizations
    # (e.g. stack or priority queue).
    # These will only be called with appropriate locks held

    # Initialize the queue representation
    def _init(self, maxsize):
        self.maxsize = maxsize
        self.queue = deque()

    def _qsize(self):
        return len(self.queue)

    # Check whether the queue is empty
    def _empty(self):
        return not self.queue

    # Check whether the queue is full
    def _full(self):
        return self.maxsize > 0 and len(self.queue) == self.maxsize

    # Put a new item in the queue
    def _put(self, item):
        self.queue.append(item)

    # Get an item from the queue
    def _get(self):
        return self.queue.popleft()
