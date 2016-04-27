# util/_collections.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Collection classes and helpers."""

import itertools
import weakref
import operator
from .compat import threading

EMPTY_SET = frozenset()


class KeyedTuple(tuple):
    """``tuple`` subclass that adds labeled names.

    E.g.::

        >>> k = KeyedTuple([1, 2, 3], labels=["one", "two", "three"])
        >>> k.one
        1
        >>> k.two
        2

    Result rows returned by :class:`.Query` that contain multiple
    ORM entities and/or column expressions make use of this
    class to return rows.

    The :class:`.KeyedTuple` exhibits similar behavior to the
    ``collections.namedtuple()`` construct provided in the Python
    standard library, however is architected very differently.
    Unlike ``collections.namedtuple()``, :class:`.KeyedTuple` is
    does not rely on creation of custom subtypes in order to represent
    a new series of keys, instead each :class:`.KeyedTuple` instance
    receives its list of keys in place.   The subtype approach
    of ``collections.namedtuple()`` introduces significant complexity
    and performance overhead, which is not necessary for the
    :class:`.Query` object's use case.

    .. versionchanged:: 0.8
        Compatibility methods with ``collections.namedtuple()`` have been
        added including :attr:`.KeyedTuple._fields` and
        :meth:`.KeyedTuple._asdict`.

    .. seealso::

        :ref:`ormtutorial_querying`

    """

    def __new__(cls, vals, labels=None):
        t = tuple.__new__(cls, vals)
        t._labels = []
        if labels:
            t.__dict__.update(zip(labels, vals))
            t._labels = labels
        return t

    def keys(self):
        """Return a list of string key names for this :class:`.KeyedTuple`.

        .. seealso::

            :attr:`.KeyedTuple._fields`

        """

        return [l for l in self._labels if l is not None]

    @property
    def _fields(self):
        """Return a tuple of string key names for this :class:`.KeyedTuple`.

        This method provides compatibility with ``collections.namedtuple()``.

        .. versionadded:: 0.8

        .. seealso::

            :meth:`.KeyedTuple.keys`

        """
        return tuple(self.keys())

    def _asdict(self):
        """Return the contents of this :class:`.KeyedTuple` as a dictionary.

        This method provides compatibility with ``collections.namedtuple()``,
        with the exception that the dictionary returned is **not** ordered.

        .. versionadded:: 0.8

        """
        return dict((key, self.__dict__[key]) for key in self.keys())


class ImmutableContainer(object):
    def _immutable(self, *arg, **kw):
        raise TypeError("%s object is immutable" % self.__class__.__name__)

    __delitem__ = __setitem__ = __setattr__ = _immutable


class immutabledict(ImmutableContainer, dict):

    clear = pop = popitem = setdefault = \
        update = ImmutableContainer._immutable

    def __new__(cls, *args):
        new = dict.__new__(cls)
        dict.__init__(new, *args)
        return new

    def __init__(self, *args):
        pass

    def __reduce__(self):
        return immutabledict, (dict(self), )

    def union(self, d):
        if not self:
            return immutabledict(d)
        else:
            d2 = immutabledict(self)
            dict.update(d2, d)
            return d2

    def __repr__(self):
        return "immutabledict(%s)" % dict.__repr__(self)


class Properties(object):
    """Provide a __getattr__/__setattr__ interface over a dict."""

    def __init__(self, data):
        self.__dict__['_data'] = data

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return self._data.itervalues()

    def __add__(self, other):
        return list(self) + list(other)

    def __setitem__(self, key, object):
        self._data[key] = object

    def __getitem__(self, key):
        return self._data[key]

    def __delitem__(self, key):
        del self._data[key]

    def __setattr__(self, key, object):
        self._data[key] = object

    def __getstate__(self):
        return {'_data': self.__dict__['_data']}

    def __setstate__(self, state):
        self.__dict__['_data'] = state['_data']

    def __getattr__(self, key):
        try:
            return self._data[key]
        except KeyError:
            raise AttributeError(key)

    def __contains__(self, key):
        return key in self._data

    def as_immutable(self):
        """Return an immutable proxy for this :class:`.Properties`."""

        return ImmutableProperties(self._data)

    def update(self, value):
        self._data.update(value)

    def get(self, key, default=None):
        if key in self:
            return self[key]
        else:
            return default

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def items(self):
        return self._data.items()

    def has_key(self, key):
        return key in self._data

    def clear(self):
        self._data.clear()


class OrderedProperties(Properties):
    """Provide a __getattr__/__setattr__ interface with an OrderedDict
    as backing store."""
    def __init__(self):
        Properties.__init__(self, OrderedDict())


class ImmutableProperties(ImmutableContainer, Properties):
    """Provide immutable dict/object attribute to an underlying dictionary."""


class OrderedDict(dict):
    """A dict that returns keys/values/items in the order they were added."""

    def __init__(self, ____sequence=None, **kwargs):
        self._list = []
        if ____sequence is None:
            if kwargs:
                self.update(**kwargs)
        else:
            self.update(____sequence, **kwargs)

    def clear(self):
        self._list = []
        dict.clear(self)

    def copy(self):
        return self.__copy__()

    def __copy__(self):
        return OrderedDict(self)

    def sort(self, *arg, **kw):
        self._list.sort(*arg, **kw)

    def update(self, ____sequence=None, **kwargs):
        if ____sequence is not None:
            if hasattr(____sequence, 'keys'):
                for key in ____sequence.keys():
                    self.__setitem__(key, ____sequence[key])
            else:
                for key, value in ____sequence:
                    self[key] = value
        if kwargs:
            self.update(kwargs)

    def setdefault(self, key, value):
        if key not in self:
            self.__setitem__(key, value)
            return value
        else:
            return self.__getitem__(key)

    def __iter__(self):
        return iter(self._list)

    def values(self):
        return [self[key] for key in self._list]

    def itervalues(self):
        return iter([self[key] for key in self._list])

    def keys(self):
        return list(self._list)

    def iterkeys(self):
        return iter(self.keys())

    def items(self):
        return [(key, self[key]) for key in self.keys()]

    def iteritems(self):
        return iter(self.items())

    def __setitem__(self, key, object):
        if key not in self:
            try:
                self._list.append(key)
            except AttributeError:
                # work around Python pickle loads() with
                # dict subclass (seems to ignore __setstate__?)
                self._list = [key]
        dict.__setitem__(self, key, object)

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        self._list.remove(key)

    def pop(self, key, *default):
        present = key in self
        value = dict.pop(self, key, *default)
        if present:
            self._list.remove(key)
        return value

    def popitem(self):
        item = dict.popitem(self)
        self._list.remove(item[0])
        return item


class OrderedSet(set):
    def __init__(self, d=None):
        set.__init__(self)
        self._list = []
        if d is not None:
            self.update(d)

    def add(self, element):
        if element not in self:
            self._list.append(element)
        set.add(self, element)

    def remove(self, element):
        set.remove(self, element)
        self._list.remove(element)

    def insert(self, pos, element):
        if element not in self:
            self._list.insert(pos, element)
        set.add(self, element)

    def discard(self, element):
        if element in self:
            self._list.remove(element)
            set.remove(self, element)

    def clear(self):
        set.clear(self)
        self._list = []

    def __getitem__(self, key):
        return self._list[key]

    def __iter__(self):
        return iter(self._list)

    def __add__(self, other):
        return self.union(other)

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self._list)

    __str__ = __repr__

    def update(self, iterable):
        for e in iterable:
            if e not in self:
                self._list.append(e)
                set.add(self, e)
        return self

    __ior__ = update

    def union(self, other):
        result = self.__class__(self)
        result.update(other)
        return result

    __or__ = union

    def intersection(self, other):
        other = set(other)
        return self.__class__(a for a in self if a in other)

    __and__ = intersection

    def symmetric_difference(self, other):
        other = set(other)
        result = self.__class__(a for a in self if a not in other)
        result.update(a for a in other if a not in self)
        return result

    __xor__ = symmetric_difference

    def difference(self, other):
        other = set(other)
        return self.__class__(a for a in self if a not in other)

    __sub__ = difference

    def intersection_update(self, other):
        other = set(other)
        set.intersection_update(self, other)
        self._list = [a for a in self._list if a in other]
        return self

    __iand__ = intersection_update

    def symmetric_difference_update(self, other):
        set.symmetric_difference_update(self, other)
        self._list = [a for a in self._list if a in self]
        self._list += [a for a in other._list if a in self]
        return self

    __ixor__ = symmetric_difference_update

    def difference_update(self, other):
        set.difference_update(self, other)
        self._list = [a for a in self._list if a in self]
        return self

    __isub__ = difference_update


class IdentitySet(object):
    """A set that considers only object id() for uniqueness.

    This strategy has edge cases for builtin types- it's possible to have
    two 'foo' strings in one of these sets, for example.  Use sparingly.

    """

    _working_set = set

    def __init__(self, iterable=None):
        self._members = dict()
        if iterable:
            for o in iterable:
                self.add(o)

    def add(self, value):
        self._members[id(value)] = value

    def __contains__(self, value):
        return id(value) in self._members

    def remove(self, value):
        del self._members[id(value)]

    def discard(self, value):
        try:
            self.remove(value)
        except KeyError:
            pass

    def pop(self):
        try:
            pair = self._members.popitem()
            return pair[1]
        except KeyError:
            raise KeyError('pop from an empty set')

    def clear(self):
        self._members.clear()

    def __cmp__(self, other):
        raise TypeError('cannot compare sets using cmp()')

    def __eq__(self, other):
        if isinstance(other, IdentitySet):
            return self._members == other._members
        else:
            return False

    def __ne__(self, other):
        if isinstance(other, IdentitySet):
            return self._members != other._members
        else:
            return True

    def issubset(self, iterable):
        other = type(self)(iterable)

        if len(self) > len(other):
            return False
        for m in itertools.ifilterfalse(other._members.__contains__,
                                        self._members.iterkeys()):
            return False
        return True

    def __le__(self, other):
        if not isinstance(other, IdentitySet):
            return NotImplemented
        return self.issubset(other)

    def __lt__(self, other):
        if not isinstance(other, IdentitySet):
            return NotImplemented
        return len(self) < len(other) and self.issubset(other)

    def issuperset(self, iterable):
        other = type(self)(iterable)

        if len(self) < len(other):
            return False

        for m in itertools.ifilterfalse(self._members.__contains__,
                                        other._members.iterkeys()):
            return False
        return True

    def __ge__(self, other):
        if not isinstance(other, IdentitySet):
            return NotImplemented
        return self.issuperset(other)

    def __gt__(self, other):
        if not isinstance(other, IdentitySet):
            return NotImplemented
        return len(self) > len(other) and self.issuperset(other)

    def union(self, iterable):
        result = type(self)()
        # testlib.pragma exempt:__hash__
        members = self._member_id_tuples()
        other = _iter_id(iterable)
        result._members.update(self._working_set(members).union(other))
        return result

    def __or__(self, other):
        if not isinstance(other, IdentitySet):
            return NotImplemented
        return self.union(other)

    def update(self, iterable):
        self._members = self.union(iterable)._members

    def __ior__(self, other):
        if not isinstance(other, IdentitySet):
            return NotImplemented
        self.update(other)
        return self

    def difference(self, iterable):
        result = type(self)()
        # testlib.pragma exempt:__hash__
        members = self._member_id_tuples()
        other = _iter_id(iterable)
        result._members.update(self._working_set(members).difference(other))
        return result

    def __sub__(self, other):
        if not isinstance(other, IdentitySet):
            return NotImplemented
        return self.difference(other)

    def difference_update(self, iterable):
        self._members = self.difference(iterable)._members

    def __isub__(self, other):
        if not isinstance(other, IdentitySet):
            return NotImplemented
        self.difference_update(other)
        return self

    def intersection(self, iterable):
        result = type(self)()
        # testlib.pragma exempt:__hash__
        members = self._member_id_tuples()
        other = _iter_id(iterable)
        result._members.update(self._working_set(members).intersection(other))
        return result

    def __and__(self, other):
        if not isinstance(other, IdentitySet):
            return NotImplemented
        return self.intersection(other)

    def intersection_update(self, iterable):
        self._members = self.intersection(iterable)._members

    def __iand__(self, other):
        if not isinstance(other, IdentitySet):
            return NotImplemented
        self.intersection_update(other)
        return self

    def symmetric_difference(self, iterable):
        result = type(self)()
        # testlib.pragma exempt:__hash__
        members = self._member_id_tuples()
        other = _iter_id(iterable)
        result._members.update(
            self._working_set(members).symmetric_difference(other))
        return result

    def _member_id_tuples(self):
        return ((id(v), v) for v in self._members.itervalues())

    def __xor__(self, other):
        if not isinstance(other, IdentitySet):
            return NotImplemented
        return self.symmetric_difference(other)

    def symmetric_difference_update(self, iterable):
        self._members = self.symmetric_difference(iterable)._members

    def __ixor__(self, other):
        if not isinstance(other, IdentitySet):
            return NotImplemented
        self.symmetric_difference(other)
        return self

    def copy(self):
        return type(self)(self._members.itervalues())

    __copy__ = copy

    def __len__(self):
        return len(self._members)

    def __iter__(self):
        return self._members.itervalues()

    def __hash__(self):
        raise TypeError('set objects are unhashable')

    def __repr__(self):
        return '%s(%r)' % (type(self).__name__, self._members.values())


class WeakSequence(object):
    def __init__(self, __elements=()):
        self._storage = [
            weakref.ref(element, self._remove) for element in __elements
        ]

    def append(self, item):
        self._storage.append(weakref.ref(item, self._remove))

    def _remove(self, ref):
        self._storage.remove(ref)

    def __len__(self):
        return len(self._storage)

    def __iter__(self):
        return (obj for obj in
                    (ref() for ref in self._storage) if obj is not None)

    def __getitem__(self, index):
        try:
            obj = self._storage[index]
        except KeyError:
            raise IndexError("Index %s out of range" % index)
        else:
            return obj()


class OrderedIdentitySet(IdentitySet):
    class _working_set(OrderedSet):
        # a testing pragma: exempt the OIDS working set from the test suite's
        # "never call the user's __hash__" assertions.  this is a big hammer,
        # but it's safe here: IDS operates on (id, instance) tuples in the
        # working set.
        __sa_hash_exempt__ = True

    def __init__(self, iterable=None):
        IdentitySet.__init__(self)
        self._members = OrderedDict()
        if iterable:
            for o in iterable:
                self.add(o)


class PopulateDict(dict):
    """A dict which populates missing values via a creation function.

    Note the creation function takes a key, unlike
    collections.defaultdict.

    """

    def __init__(self, creator):
        self.creator = creator

    def __missing__(self, key):
        self[key] = val = self.creator(key)
        return val

# Define collections that are capable of storing
# ColumnElement objects as hashable keys/elements.
# At this point, these are mostly historical, things
# used to be more complicated.
column_set = set
column_dict = dict
ordered_column_set = OrderedSet
populate_column_dict = PopulateDict

def unique_list(seq, hashfunc=None):
    seen = {}
    if not hashfunc:
        return [x for x in seq
                if x not in seen
                and not seen.__setitem__(x, True)]
    else:
        return [x for x in seq
                if hashfunc(x) not in seen
                and not seen.__setitem__(hashfunc(x), True)]


class UniqueAppender(object):
    """Appends items to a collection ensuring uniqueness.

    Additional appends() of the same object are ignored.  Membership is
    determined by identity (``is a``) not equality (``==``).
    """

    def __init__(self, data, via=None):
        self.data = data
        self._unique = {}
        if via:
            self._data_appender = getattr(data, via)
        elif hasattr(data, 'append'):
            self._data_appender = data.append
        elif hasattr(data, 'add'):
            self._data_appender = data.add

    def append(self, item):
        id_ = id(item)
        if id_ not in self._unique:
            self._data_appender(item)
            self._unique[id_] = True

    def __iter__(self):
        return iter(self.data)


def to_list(x, default=None):
    if x is None:
        return default
    if not isinstance(x, (list, tuple)):
        return [x]
    else:
        return x


def to_set(x):
    if x is None:
        return set()
    if not isinstance(x, set):
        return set(to_list(x))
    else:
        return x


def to_column_set(x):
    if x is None:
        return column_set()
    if not isinstance(x, column_set):
        return column_set(to_list(x))
    else:
        return x


def update_copy(d, _new=None, **kw):
    """Copy the given dict and update with the given values."""

    d = d.copy()
    if _new:
        d.update(_new)
    d.update(**kw)
    return d


def flatten_iterator(x):
    """Given an iterator of which further sub-elements may also be
    iterators, flatten the sub-elements into a single iterator.

    """
    for elem in x:
        if not isinstance(elem, basestring) and hasattr(elem, '__iter__'):
            for y in flatten_iterator(elem):
                yield y
        else:
            yield elem


class LRUCache(dict):
    """Dictionary with 'squishy' removal of least
    recently used items.

    """
    def __init__(self, capacity=100, threshold=.5):
        self.capacity = capacity
        self.threshold = threshold
        self._counter = 0

    def _inc_counter(self):
        self._counter += 1
        return self._counter

    def __getitem__(self, key):
        item = dict.__getitem__(self, key)
        item[2] = self._inc_counter()
        return item[1]

    def values(self):
        return [i[1] for i in dict.values(self)]

    def setdefault(self, key, value):
        if key in self:
            return self[key]
        else:
            self[key] = value
            return value

    def __setitem__(self, key, value):
        item = dict.get(self, key)
        if item is None:
            item = [key, value, self._inc_counter()]
            dict.__setitem__(self, key, item)
        else:
            item[1] = value
        self._manage_size()

    def _manage_size(self):
        while len(self) > self.capacity + self.capacity * self.threshold:
            by_counter = sorted(dict.values(self),
                            key=operator.itemgetter(2),
                            reverse=True)
            for item in by_counter[self.capacity:]:
                try:
                    del self[item[0]]
                except KeyError:
                    # if we couldnt find a key, most
                    # likely some other thread broke in
                    # on us. loop around and try again
                    break


class ScopedRegistry(object):
    """A Registry that can store one or multiple instances of a single
    class on the basis of a "scope" function.

    The object implements ``__call__`` as the "getter", so by
    calling ``myregistry()`` the contained object is returned
    for the current scope.

    :param createfunc:
      a callable that returns a new object to be placed in the registry

    :param scopefunc:
      a callable that will return a key to store/retrieve an object.
    """

    def __init__(self, createfunc, scopefunc):
        """Construct a new :class:`.ScopedRegistry`.

        :param createfunc:  A creation function that will generate
          a new value for the current scope, if none is present.

        :param scopefunc:  A function that returns a hashable
          token representing the current scope (such as, current
          thread identifier).

        """
        self.createfunc = createfunc
        self.scopefunc = scopefunc
        self.registry = {}

    def __call__(self):
        key = self.scopefunc()
        try:
            return self.registry[key]
        except KeyError:
            return self.registry.setdefault(key, self.createfunc())

    def has(self):
        """Return True if an object is present in the current scope."""

        return self.scopefunc() in self.registry

    def set(self, obj):
        """Set the value forthe current scope."""

        self.registry[self.scopefunc()] = obj

    def clear(self):
        """Clear the current scope, if any."""

        try:
            del self.registry[self.scopefunc()]
        except KeyError:
            pass


class ThreadLocalRegistry(ScopedRegistry):
    """A :class:`.ScopedRegistry` that uses a ``threading.local()``
    variable for storage.

    """
    def __init__(self, createfunc):
        self.createfunc = createfunc
        self.registry = threading.local()

    def __call__(self):
        try:
            return self.registry.value
        except AttributeError:
            val = self.registry.value = self.createfunc()
            return val

    def has(self):
        return hasattr(self.registry, "value")

    def set(self, obj):
        self.registry.value = obj

    def clear(self):
        try:
            del self.registry.value
        except AttributeError:
            pass


def _iter_id(iterable):
    """Generator: ((id(o), o) for o in iterable)."""

    for item in iterable:
        yield id(item), item
