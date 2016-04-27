# util/compat.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Handle Python version/platform incompatibilities."""

import sys

try:
    import threading
except ImportError:
    import dummy_threading as threading

py33 = sys.version_info >= (3, 3)
py32 = sys.version_info >= (3, 2)
py26 = sys.version_info >= (2, 6)
py3k_warning = getattr(sys, 'py3kwarning', False) or sys.version_info >= (3, 0)
py3k = sys.version_info >= (3, 0)
py2k = sys.version_info < (3, 0)
jython = sys.platform.startswith('java')
pypy = hasattr(sys, 'pypy_version_info')
win32 = sys.platform.startswith('win')
cpython = not pypy and not jython  # TODO: something better for this ?

if py3k_warning:
    set_types = set
elif sys.version_info < (2, 6):
    import sets
    set_types = set, sets.Set
else:
    # 2.6 deprecates sets.Set, but we still need to be able to detect them
    # in user code and as return values from DB-APIs
    ignore = ('ignore', None, DeprecationWarning, None, 0)
    import warnings
    try:
        warnings.filters.insert(0, ignore)
    except Exception:
        import sets
    else:
        import sets
        warnings.filters.remove(ignore)

    set_types = set, sets.Set

if sys.version_info < (2, 6):
    def next(iter):
        return iter.next()
else:
    next = next
if py3k_warning:
    import pickle
else:
    try:
        import cPickle as pickle
    except ImportError:
        import pickle

if sys.version_info < (2, 6):
    # emits a nasty deprecation warning
    # in newer pythons
    from cgi import parse_qsl
else:
    from urlparse import parse_qsl

# Py3K
#from inspect import getfullargspec as inspect_getfullargspec
# Py2K
from inspect import getargspec as inspect_getfullargspec
# end Py2K

if py3k_warning:
    # they're bringing it back in 3.2.  brilliant !
    def callable(fn):
        return hasattr(fn, '__call__')

    def cmp(a, b):
        return (a > b) - (a < b)

    from functools import reduce
else:
    callable = callable
    cmp = cmp
    reduce = reduce

try:
    from collections import namedtuple
except ImportError:
    def namedtuple(typename, fieldnames):
        def __new__(cls, *values):
            tup = tuple.__new__(cls, values)
            for i, fname in enumerate(fieldnames):
                setattr(tup, fname, tup[i])
            return tup
        tuptype = type(typename, (tuple, ), {'__new__': __new__})
        return tuptype

try:
    from weakref import WeakSet
except:
    import weakref

    class WeakSet(object):
        """Implement the small subset of set() which SQLAlchemy needs
        here. """
        def __init__(self, values=None):
            self._storage = weakref.WeakKeyDictionary()
            if values is not None:
                self._storage.update((value, None) for value in values)

        def __iter__(self):
            return iter(self._storage)

        def union(self, other):
            return WeakSet(set(self).union(other))

        def add(self, other):
            self._storage[other] = True

import time
if win32 or jython:
    time_func = time.clock
else:
    time_func = time.time


if sys.version_info >= (2, 6):
    from operator import attrgetter as dottedgetter
else:
    def dottedgetter(attr):
        def g(obj):
            for name in attr.split("."):
                obj = getattr(obj, name)
            return obj
        return g

if py3k:

    string_types = str,
    binary_type = bytes
    text_type = str
    int_types = int,

    def u(s):
        return s

    def ue(s):
        return s

    def b(s):
        return s.encode("latin-1")

else:
    string_types = basestring,
    binary_type = str
    text_type = unicode
    int_types = int, long

    def b(s):
        return s

    def u(s):
        # this differs from what six does, which doesn't support non-ASCII
        # strings - we only use u() with
        # literal source strings, and all our source files with non-ascii
        # in them (all are tests) are utf-8 encoded.
        return unicode(s, "utf-8")

    def ue(s):
        return unicode(s, "unicode_escape")

    def b(s):
        return s


if py3k:
    def reraise(tp, value, tb=None, cause=None):
        if cause is not None:
            value.__cause__ = cause
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value

    def raise_from_cause(exception, exc_info):
        exc_type, exc_value, exc_tb = exc_info
        reraise(type(exception), exception, tb=exc_tb, cause=exc_value)
else:
    exec("def reraise(tp, value, tb=None, cause=None):\n"
            "    raise tp, value, tb\n")

    def raise_from_cause(exception, exc_info):
        # not as nice as that of Py3K, but at least preserves
        # the code line where the issue occurred
        exc_type, exc_value, exc_tb = exc_info
        reraise(type(exception), exception, tb=exc_tb)




