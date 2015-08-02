# orm/collections.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Support for collections of mapped entities.

The collections package supplies the machinery used to inform the ORM of
collection membership changes.  An instrumentation via decoration approach is
used, allowing arbitrary types (including built-ins) to be used as entity
collections without requiring inheritance from a base class.

Instrumentation decoration relays membership change events to the
:class:`.CollectionAttributeImpl` that is currently managing the collection.
The decorators observe function call arguments and return values, tracking
entities entering or leaving the collection.  Two decorator approaches are
provided.  One is a bundle of generic decorators that map function arguments
and return values to events::

  from sqlalchemy.orm.collections import collection
  class MyClass(object):
      # ...

      @collection.adds(1)
      def store(self, item):
          self.data.append(item)

      @collection.removes_return()
      def pop(self):
          return self.data.pop()


The second approach is a bundle of targeted decorators that wrap appropriate
append and remove notifiers around the mutation methods present in the
standard Python ``list``, ``set`` and ``dict`` interfaces.  These could be
specified in terms of generic decorator recipes, but are instead hand-tooled
for increased efficiency.  The targeted decorators occasionally implement
adapter-like behavior, such as mapping bulk-set methods (``extend``,
``update``, ``__setslice__``, etc.) into the series of atomic mutation events
that the ORM requires.

The targeted decorators are used internally for automatic instrumentation of
entity collection classes.  Every collection class goes through a
transformation process roughly like so:

1. If the class is a built-in, substitute a trivial sub-class
2. Is this class already instrumented?
3. Add in generic decorators
4. Sniff out the collection interface through duck-typing
5. Add targeted decoration to any undecorated interface method

This process modifies the class at runtime, decorating methods and adding some
bookkeeping properties.  This isn't possible (or desirable) for built-in
classes like ``list``, so trivial sub-classes are substituted to hold
decoration::

  class InstrumentedList(list):
      pass

Collection classes can be specified in ``relationship(collection_class=)`` as
types or a function that returns an instance.  Collection classes are
inspected and instrumented during the mapper compilation phase.  The
collection_class callable will be executed once to produce a specimen
instance, and the type of that specimen will be instrumented.  Functions that
return built-in types like ``lists`` will be adapted to produce instrumented
instances.

When extending a known type like ``list``, additional decorations are not
generally not needed.  Odds are, the extension method will delegate to a
method that's already instrumented.  For example::

  class QueueIsh(list):
     def push(self, item):
         self.append(item)
     def shift(self):
         return self.pop(0)

There's no need to decorate these methods.  ``append`` and ``pop`` are already
instrumented as part of the ``list`` interface.  Decorating them would fire
duplicate events, which should be avoided.

The targeted decoration tries not to rely on other methods in the underlying
collection class, but some are unavoidable.  Many depend on 'read' methods
being present to properly instrument a 'write', for example, ``__setitem__``
needs ``__getitem__``.  "Bulk" methods like ``update`` and ``extend`` may also
reimplemented in terms of atomic appends and removes, so the ``extend``
decoration will actually perform many ``append`` operations and not call the
underlying method at all.

Tight control over bulk operation and the firing of events is also possible by
implementing the instrumentation internally in your methods.  The basic
instrumentation package works under the general assumption that collection
mutation will not raise unusual exceptions.  If you want to closely
orchestrate append and remove events with exception management, internal
instrumentation may be the answer.  Within your method,
``collection_adapter(self)`` will retrieve an object that you can use for
explicit control over triggering append and remove events.

The owning object and :class:`.CollectionAttributeImpl` are also reachable
through the adapter, allowing for some very sophisticated behavior.

"""

import inspect
import operator
import weakref

from ..sql import expression
from .. import util, exc as sa_exc
orm_util = util.importlater("sqlalchemy.orm", "util")
attributes = util.importlater("sqlalchemy.orm", "attributes")


__all__ = ['collection', 'collection_adapter',
           'mapped_collection', 'column_mapped_collection',
           'attribute_mapped_collection']

__instrumentation_mutex = util.threading.Lock()


class _PlainColumnGetter(object):
    """Plain column getter, stores collection of Column objects
    directly.

    Serializes to a :class:`._SerializableColumnGetterV2`
    which has more expensive __call__() performance
    and some rare caveats.

    """
    def __init__(self, cols):
        self.cols = cols
        self.composite = len(cols) > 1

    def __reduce__(self):
        return _SerializableColumnGetterV2._reduce_from_cols(self.cols)

    def _cols(self, mapper):
        return self.cols

    def __call__(self, value):
        state = attributes.instance_state(value)
        m = orm_util._state_mapper(state)

        key = [
            m._get_state_attr_by_column(state, state.dict, col)
            for col in self._cols(m)
        ]

        if self.composite:
            return tuple(key)
        else:
            return key[0]


class _SerializableColumnGetter(object):
    """Column-based getter used in version 0.7.6 only.

    Remains here for pickle compatibility with 0.7.6.

    """
    def __init__(self, colkeys):
        self.colkeys = colkeys
        self.composite = len(colkeys) > 1

    def __reduce__(self):
        return _SerializableColumnGetter, (self.colkeys,)

    def __call__(self, value):
        state = attributes.instance_state(value)
        m = orm_util._state_mapper(state)
        key = [m._get_state_attr_by_column(
                        state, state.dict,
                        m.mapped_table.columns[k])
                     for k in self.colkeys]
        if self.composite:
            return tuple(key)
        else:
            return key[0]


class _SerializableColumnGetterV2(_PlainColumnGetter):
    """Updated serializable getter which deals with
    multi-table mapped classes.

    Two extremely unusual cases are not supported.
    Mappings which have tables across multiple metadata
    objects, or which are mapped to non-Table selectables
    linked across inheriting mappers may fail to function
    here.

    """

    def __init__(self, colkeys):
        self.colkeys = colkeys
        self.composite = len(colkeys) > 1

    def __reduce__(self):
        return self.__class__, (self.colkeys,)

    @classmethod
    def _reduce_from_cols(cls, cols):
        def _table_key(c):
            if not isinstance(c.table, expression.TableClause):
                return None
            else:
                return c.table.key
        colkeys = [(c.key, _table_key(c)) for c in cols]
        return _SerializableColumnGetterV2, (colkeys,)

    def _cols(self, mapper):
        cols = []
        metadata = getattr(mapper.local_table, 'metadata', None)
        for (ckey, tkey) in self.colkeys:
            if tkey is None or \
                metadata is None or \
                tkey not in metadata:
                cols.append(mapper.local_table.c[ckey])
            else:
                cols.append(metadata.tables[tkey].c[ckey])
        return cols


def column_mapped_collection(mapping_spec):
    """A dictionary-based collection type with column-based keying.

    Returns a :class:`.MappedCollection` factory with a keying function
    generated from mapping_spec, which may be a Column or a sequence
    of Columns.

    The key value must be immutable for the lifetime of the object.  You
    can not, for example, map on foreign key values if those key values will
    change during the session, i.e. from None to a database-assigned integer
    after a session flush.

    """
    cols = [expression._only_column_elements(q, "mapping_spec")
                for q in util.to_list(mapping_spec)
            ]
    keyfunc = _PlainColumnGetter(cols)
    return lambda: MappedCollection(keyfunc)


class _SerializableAttrGetter(object):
    def __init__(self, name):
        self.name = name
        self.getter = operator.attrgetter(name)

    def __call__(self, target):
        return self.getter(target)

    def __reduce__(self):
        return _SerializableAttrGetter, (self.name, )


def attribute_mapped_collection(attr_name):
    """A dictionary-based collection type with attribute-based keying.

    Returns a :class:`.MappedCollection` factory with a keying based on the
    'attr_name' attribute of entities in the collection, where ``attr_name``
    is the string name of the attribute.

    The key value must be immutable for the lifetime of the object.  You
    can not, for example, map on foreign key values if those key values will
    change during the session, i.e. from None to a database-assigned integer
    after a session flush.

    """
    getter = _SerializableAttrGetter(attr_name)
    return lambda: MappedCollection(getter)


def mapped_collection(keyfunc):
    """A dictionary-based collection type with arbitrary keying.

    Returns a :class:`.MappedCollection` factory with a keying function
    generated from keyfunc, a callable that takes an entity and returns a
    key value.

    The key value must be immutable for the lifetime of the object.  You
    can not, for example, map on foreign key values if those key values will
    change during the session, i.e. from None to a database-assigned integer
    after a session flush.

    """
    return lambda: MappedCollection(keyfunc)


class collection(object):
    """Decorators for entity collection classes.

    The decorators fall into two groups: annotations and interception recipes.

    The annotating decorators (appender, remover, iterator, linker, converter,
    internally_instrumented) indicate the method's purpose and take no
    arguments.  They are not written with parens::

        @collection.appender
        def append(self, append): ...

    The recipe decorators all require parens, even those that take no
    arguments::

        @collection.adds('entity')
        def insert(self, position, entity): ...

        @collection.removes_return()
        def popitem(self): ...

    """
    # Bundled as a class solely for ease of use: packaging, doc strings,
    # importability.

    @staticmethod
    def appender(fn):
        """Tag the method as the collection appender.

        The appender method is called with one positional argument: the value
        to append. The method will be automatically decorated with 'adds(1)'
        if not already decorated::

            @collection.appender
            def add(self, append): ...

            # or, equivalently
            @collection.appender
            @collection.adds(1)
            def add(self, append): ...

            # for mapping type, an 'append' may kick out a previous value
            # that occupies that slot.  consider d['a'] = 'foo'- any previous
            # value in d['a'] is discarded.
            @collection.appender
            @collection.replaces(1)
            def add(self, entity):
                key = some_key_func(entity)
                previous = None
                if key in self:
                    previous = self[key]
                self[key] = entity
                return previous

        If the value to append is not allowed in the collection, you may
        raise an exception.  Something to remember is that the appender
        will be called for each object mapped by a database query.  If the
        database contains rows that violate your collection semantics, you
        will need to get creative to fix the problem, as access via the
        collection will not work.

        If the appender method is internally instrumented, you must also
        receive the keyword argument '_sa_initiator' and ensure its
        promulgation to collection events.

        """
        setattr(fn, '_sa_instrument_role', 'appender')
        return fn

    @staticmethod
    def remover(fn):
        """Tag the method as the collection remover.

        The remover method is called with one positional argument: the value
        to remove. The method will be automatically decorated with
        :meth:`removes_return` if not already decorated::

            @collection.remover
            def zap(self, entity): ...

            # or, equivalently
            @collection.remover
            @collection.removes_return()
            def zap(self, ): ...

        If the value to remove is not present in the collection, you may
        raise an exception or return None to ignore the error.

        If the remove method is internally instrumented, you must also
        receive the keyword argument '_sa_initiator' and ensure its
        promulgation to collection events.

        """
        setattr(fn, '_sa_instrument_role', 'remover')
        return fn

    @staticmethod
    def iterator(fn):
        """Tag the method as the collection remover.

        The iterator method is called with no arguments.  It is expected to
        return an iterator over all collection members::

            @collection.iterator
            def __iter__(self): ...

        """
        setattr(fn, '_sa_instrument_role', 'iterator')
        return fn

    @staticmethod
    def internally_instrumented(fn):
        """Tag the method as instrumented.

        This tag will prevent any decoration from being applied to the
        method. Use this if you are orchestrating your own calls to
        :func:`.collection_adapter` in one of the basic SQLAlchemy
        interface methods, or to prevent an automatic ABC method
        decoration from wrapping your implementation::

            # normally an 'extend' method on a list-like class would be
            # automatically intercepted and re-implemented in terms of
            # SQLAlchemy events and append().  your implementation will
            # never be called, unless:
            @collection.internally_instrumented
            def extend(self, items): ...

        """
        setattr(fn, '_sa_instrumented', True)
        return fn

    @staticmethod
    def linker(fn):
        """Tag the method as a "linked to attribute" event handler.

        This optional event handler will be called when the collection class
        is linked to or unlinked from the InstrumentedAttribute.  It is
        invoked immediately after the '_sa_adapter' property is set on
        the instance.  A single argument is passed: the collection adapter
        that has been linked, or None if unlinking.

        """
        setattr(fn, '_sa_instrument_role', 'linker')
        return fn

    link = linker
    """deprecated; synonym for :meth:`.collection.linker`."""

    @staticmethod
    def converter(fn):
        """Tag the method as the collection converter.

        This optional method will be called when a collection is being
        replaced entirely, as in::

            myobj.acollection = [newvalue1, newvalue2]

        The converter method will receive the object being assigned and should
        return an iterable of values suitable for use by the ``appender``
        method.  A converter must not assign values or mutate the collection,
        it's sole job is to adapt the value the user provides into an iterable
        of values for the ORM's use.

        The default converter implementation will use duck-typing to do the
        conversion.  A dict-like collection will be convert into an iterable
        of dictionary values, and other types will simply be iterated::

            @collection.converter
            def convert(self, other): ...

        If the duck-typing of the object does not match the type of this
        collection, a TypeError is raised.

        Supply an implementation of this method if you want to expand the
        range of possible types that can be assigned in bulk or perform
        validation on the values about to be assigned.

        """
        setattr(fn, '_sa_instrument_role', 'converter')
        return fn

    @staticmethod
    def adds(arg):
        """Mark the method as adding an entity to the collection.

        Adds "add to collection" handling to the method.  The decorator
        argument indicates which method argument holds the SQLAlchemy-relevant
        value.  Arguments can be specified positionally (i.e. integer) or by
        name::

            @collection.adds(1)
            def push(self, item): ...

            @collection.adds('entity')
            def do_stuff(self, thing, entity=None): ...

        """
        def decorator(fn):
            setattr(fn, '_sa_instrument_before', ('fire_append_event', arg))
            return fn
        return decorator

    @staticmethod
    def replaces(arg):
        """Mark the method as replacing an entity in the collection.

        Adds "add to collection" and "remove from collection" handling to
        the method.  The decorator argument indicates which method argument
        holds the SQLAlchemy-relevant value to be added, and return value, if
        any will be considered the value to remove.

        Arguments can be specified positionally (i.e. integer) or by name::

            @collection.replaces(2)
            def __setitem__(self, index, item): ...

        """
        def decorator(fn):
            setattr(fn, '_sa_instrument_before', ('fire_append_event', arg))
            setattr(fn, '_sa_instrument_after', 'fire_remove_event')
            return fn
        return decorator

    @staticmethod
    def removes(arg):
        """Mark the method as removing an entity in the collection.

        Adds "remove from collection" handling to the method.  The decorator
        argument indicates which method argument holds the SQLAlchemy-relevant
        value to be removed. Arguments can be specified positionally (i.e.
        integer) or by name::

            @collection.removes(1)
            def zap(self, item): ...

        For methods where the value to remove is not known at call-time, use
        collection.removes_return.

        """
        def decorator(fn):
            setattr(fn, '_sa_instrument_before', ('fire_remove_event', arg))
            return fn
        return decorator

    @staticmethod
    def removes_return():
        """Mark the method as removing an entity in the collection.

        Adds "remove from collection" handling to the method.  The return value
        of the method, if any, is considered the value to remove.  The method
        arguments are not inspected::

            @collection.removes_return()
            def pop(self): ...

        For methods where the value to remove is known at call-time, use
        collection.remove.

        """
        def decorator(fn):
            setattr(fn, '_sa_instrument_after', 'fire_remove_event')
            return fn
        return decorator


# public instrumentation interface for 'internally instrumented'
# implementations
def collection_adapter(collection):
    """Fetch the :class:`.CollectionAdapter` for a collection."""

    return getattr(collection, '_sa_adapter', None)


def collection_iter(collection):
    """Iterate over an object supporting the @iterator or __iter__ protocols.

    If the collection is an ORM collection, it need not be attached to an
    object to be iterable.

    """
    try:
        return getattr(collection, '_sa_iterator',
                       getattr(collection, '__iter__'))()
    except AttributeError:
        raise TypeError("'%s' object is not iterable" %
                        type(collection).__name__)


class CollectionAdapter(object):
    """Bridges between the ORM and arbitrary Python collections.

    Proxies base-level collection operations (append, remove, iterate)
    to the underlying Python collection, and emits add/remove events for
    entities entering or leaving the collection.

    The ORM uses :class:`.CollectionAdapter` exclusively for interaction with
    entity collections.

    The usage of getattr()/setattr() is currently to allow injection
    of custom methods, such as to unwrap Zope security proxies.

    """
    invalidated = False

    def __init__(self, attr, owner_state, data):
        self._key = attr.key
        self._data = weakref.ref(data)
        self.owner_state = owner_state
        self.link_to_self(data)

    def _warn_invalidated(self):
        util.warn("This collection has been invalidated.")

    @property
    def data(self):
        "The entity collection being adapted."
        return self._data()

    @util.memoized_property
    def attr(self):
        return self.owner_state.manager[self._key].impl

    def link_to_self(self, data):
        """Link a collection to this adapter, and fire a link event."""
        setattr(data, '_sa_adapter', self)
        if hasattr(data, '_sa_linker'):
            getattr(data, '_sa_linker')(self)

    def unlink(self, data):
        """Unlink a collection from any adapter, and fire a link event."""
        setattr(data, '_sa_adapter', None)
        if hasattr(data, '_sa_linker'):
            getattr(data, '_sa_linker')(None)

    def adapt_like_to_iterable(self, obj):
        """Converts collection-compatible objects to an iterable of values.

        Can be passed any type of object, and if the underlying collection
        determines that it can be adapted into a stream of values it can
        use, returns an iterable of values suitable for append()ing.

        This method may raise TypeError or any other suitable exception
        if adaptation fails.

        If a converter implementation is not supplied on the collection,
        a default duck-typing-based implementation is used.

        """
        converter = getattr(self._data(), '_sa_converter', None)
        if converter is not None:
            return converter(obj)

        setting_type = util.duck_type_collection(obj)
        receiving_type = util.duck_type_collection(self._data())

        if obj is None or setting_type != receiving_type:
            given = obj is None and 'None' or obj.__class__.__name__
            if receiving_type is None:
                wanted = self._data().__class__.__name__
            else:
                wanted = receiving_type.__name__

            raise TypeError(
                "Incompatible collection type: %s is not %s-like" % (
                given, wanted))

        # If the object is an adapted collection, return the (iterable)
        # adapter.
        if getattr(obj, '_sa_adapter', None) is not None:
            return getattr(obj, '_sa_adapter')
        elif setting_type == dict:
            # Py3K
            #return obj.values()
            # Py2K
            return getattr(obj, 'itervalues', getattr(obj, 'values'))()
            # end Py2K
        else:
            return iter(obj)

    def append_with_event(self, item, initiator=None):
        """Add an entity to the collection, firing mutation events."""

        getattr(self._data(), '_sa_appender')(item, _sa_initiator=initiator)

    def append_without_event(self, item):
        """Add or restore an entity to the collection, firing no events."""
        getattr(self._data(), '_sa_appender')(item, _sa_initiator=False)

    def append_multiple_without_event(self, items):
        """Add or restore an entity to the collection, firing no events."""
        appender = getattr(self._data(), '_sa_appender')
        for item in items:
            appender(item, _sa_initiator=False)

    def remove_with_event(self, item, initiator=None):
        """Remove an entity from the collection, firing mutation events."""
        getattr(self._data(), '_sa_remover')(item, _sa_initiator=initiator)

    def remove_without_event(self, item):
        """Remove an entity from the collection, firing no events."""
        getattr(self._data(), '_sa_remover')(item, _sa_initiator=False)

    def clear_with_event(self, initiator=None):
        """Empty the collection, firing a mutation event for each entity."""

        remover = getattr(self._data(), '_sa_remover')
        for item in list(self):
            remover(item, _sa_initiator=initiator)

    def clear_without_event(self):
        """Empty the collection, firing no events."""

        remover = getattr(self._data(), '_sa_remover')
        for item in list(self):
            remover(item, _sa_initiator=False)

    def __iter__(self):
        """Iterate over entities in the collection."""

        # Py3K requires iter() here
        return iter(getattr(self._data(), '_sa_iterator')())

    def __len__(self):
        """Count entities in the collection."""
        return len(list(getattr(self._data(), '_sa_iterator')()))

    def __nonzero__(self):
        return True

    def fire_append_event(self, item, initiator=None):
        """Notify that a entity has entered the collection.

        Initiator is a token owned by the InstrumentedAttribute that
        initiated the membership mutation, and should be left as None
        unless you are passing along an initiator value from a chained
        operation.

        """
        if initiator is not False:
            if self.invalidated:
                self._warn_invalidated()
            return self.attr.fire_append_event(
                                    self.owner_state,
                                    self.owner_state.dict,
                                    item, initiator)
        else:
            return item

    def fire_remove_event(self, item, initiator=None):
        """Notify that a entity has been removed from the collection.

        Initiator is the InstrumentedAttribute that initiated the membership
        mutation, and should be left as None unless you are passing along
        an initiator value from a chained operation.

        """
        if initiator is not False:
            if self.invalidated:
                self._warn_invalidated()
            self.attr.fire_remove_event(
                                    self.owner_state,
                                    self.owner_state.dict,
                                    item, initiator)

    def fire_pre_remove_event(self, initiator=None):
        """Notify that an entity is about to be removed from the collection.

        Only called if the entity cannot be removed after calling
        fire_remove_event().

        """
        if self.invalidated:
            self._warn_invalidated()
        self.attr.fire_pre_remove_event(
                                    self.owner_state,
                                    self.owner_state.dict,
                                    initiator=initiator)

    def __getstate__(self):
        return {'key': self._key,
                'owner_state': self.owner_state,
                'data': self.data}

    def __setstate__(self, d):
        self._key = d['key']
        self.owner_state = d['owner_state']
        self._data = weakref.ref(d['data'])


def bulk_replace(values, existing_adapter, new_adapter):
    """Load a new collection, firing events based on prior like membership.

    Appends instances in ``values`` onto the ``new_adapter``. Events will be
    fired for any instance not present in the ``existing_adapter``.  Any
    instances in ``existing_adapter`` not present in ``values`` will have
    remove events fired upon them.

    :param values: An iterable of collection member instances

    :param existing_adapter: A :class:`.CollectionAdapter` of
     instances to be replaced

    :param new_adapter: An empty :class:`.CollectionAdapter`
     to load with ``values``


    """
    if not isinstance(values, list):
        values = list(values)

    idset = util.IdentitySet
    existing_idset = idset(existing_adapter or ())
    constants = existing_idset.intersection(values or ())
    additions = idset(values or ()).difference(constants)
    removals = existing_idset.difference(constants)

    for member in values or ():
        if member in additions:
            new_adapter.append_with_event(member)
        elif member in constants:
            new_adapter.append_without_event(member)

    if existing_adapter:
        for member in removals:
            existing_adapter.remove_with_event(member)


def prepare_instrumentation(factory):
    """Prepare a callable for future use as a collection class factory.

    Given a collection class factory (either a type or no-arg callable),
    return another factory that will produce compatible instances when
    called.

    This function is responsible for converting collection_class=list
    into the run-time behavior of collection_class=InstrumentedList.

    """
    # Convert a builtin to 'Instrumented*'
    if factory in __canned_instrumentation:
        factory = __canned_instrumentation[factory]

    # Create a specimen
    cls = type(factory())

    # Did factory callable return a builtin?
    if cls in __canned_instrumentation:
        # Wrap it so that it returns our 'Instrumented*'
        factory = __converting_factory(cls, factory)
        cls = factory()

    # Instrument the class if needed.
    if __instrumentation_mutex.acquire():
        try:
            if getattr(cls, '_sa_instrumented', None) != id(cls):
                _instrument_class(cls)
        finally:
            __instrumentation_mutex.release()

    return factory


def __converting_factory(specimen_cls, original_factory):
    """Return a wrapper that converts a "canned" collection like
    set, dict, list into the Instrumented* version.

    """

    instrumented_cls = __canned_instrumentation[specimen_cls]

    def wrapper():
        collection = original_factory()
        return instrumented_cls(collection)

    # often flawed but better than nothing
    wrapper.__name__ = "%sWrapper" % original_factory.__name__
    wrapper.__doc__ = original_factory.__doc__

    return wrapper

def _instrument_class(cls):
    """Modify methods in a class and install instrumentation."""

    # In the normal call flow, a request for any of the 3 basic collection
    # types is transformed into one of our trivial subclasses
    # (e.g. InstrumentedList).  Catch anything else that sneaks in here...
    if cls.__module__ == '__builtin__':
        raise sa_exc.ArgumentError(
            "Can not instrument a built-in type. Use a "
            "subclass, even a trivial one.")

    roles = {}
    methods = {}

    # search for _sa_instrument_role-decorated methods in
    # method resolution order, assign to roles
    for supercls in cls.__mro__:
        for name, method in vars(supercls).items():
            if not util.callable(method):
                continue

            # note role declarations
            if hasattr(method, '_sa_instrument_role'):
                role = method._sa_instrument_role
                assert role in ('appender', 'remover', 'iterator',
                                'linker', 'converter')
                roles.setdefault(role, name)

            # transfer instrumentation requests from decorated function
            # to the combined queue
            before, after = None, None
            if hasattr(method, '_sa_instrument_before'):
                op, argument = method._sa_instrument_before
                assert op in ('fire_append_event', 'fire_remove_event')
                before = op, argument
            if hasattr(method, '_sa_instrument_after'):
                op = method._sa_instrument_after
                assert op in ('fire_append_event', 'fire_remove_event')
                after = op
            if before:
                methods[name] = before[0], before[1], after
            elif after:
                methods[name] = None, None, after

    # see if this class has "canned" roles based on a known
    # collection type (dict, set, list).  Apply those roles
    # as needed to the "roles" dictionary, and also
    # prepare "decorator" methods
    collection_type = util.duck_type_collection(cls)
    if collection_type in __interfaces:
        canned_roles, decorators = __interfaces[collection_type]
        for role, name in canned_roles.items():
            roles.setdefault(role, name)

        # apply ABC auto-decoration to methods that need it
        for method, decorator in decorators.items():
            fn = getattr(cls, method, None)
            if (fn and method not in methods and
                not hasattr(fn, '_sa_instrumented')):
                setattr(cls, method, decorator(fn))

    # ensure all roles are present, and apply implicit instrumentation if
    # needed
    if 'appender' not in roles or not hasattr(cls, roles['appender']):
        raise sa_exc.ArgumentError(
            "Type %s must elect an appender method to be "
            "a collection class" % cls.__name__)
    elif (roles['appender'] not in methods and
          not hasattr(getattr(cls, roles['appender']), '_sa_instrumented')):
        methods[roles['appender']] = ('fire_append_event', 1, None)

    if 'remover' not in roles or not hasattr(cls, roles['remover']):
        raise sa_exc.ArgumentError(
            "Type %s must elect a remover method to be "
            "a collection class" % cls.__name__)
    elif (roles['remover'] not in methods and
          not hasattr(getattr(cls, roles['remover']), '_sa_instrumented')):
        methods[roles['remover']] = ('fire_remove_event', 1, None)

    if 'iterator' not in roles or not hasattr(cls, roles['iterator']):
        raise sa_exc.ArgumentError(
            "Type %s must elect an iterator method to be "
            "a collection class" % cls.__name__)

    # apply ad-hoc instrumentation from decorators, class-level defaults
    # and implicit role declarations
    for method_name, (before, argument, after) in methods.items():
        setattr(cls, method_name,
                _instrument_membership_mutator(getattr(cls, method_name),
                                               before, argument, after))
    # intern the role map
    for role, method_name in roles.items():
        setattr(cls, '_sa_%s' % role, getattr(cls, method_name))

    setattr(cls, '_sa_instrumented', id(cls))


def _instrument_membership_mutator(method, before, argument, after):
    """Route method args and/or return value through the collection adapter."""
    # This isn't smart enough to handle @adds(1) for 'def fn(self, (a, b))'
    if before:
        fn_args = list(util.flatten_iterator(inspect.getargspec(method)[0]))
        if type(argument) is int:
            pos_arg = argument
            named_arg = len(fn_args) > argument and fn_args[argument] or None
        else:
            if argument in fn_args:
                pos_arg = fn_args.index(argument)
            else:
                pos_arg = None
            named_arg = argument
        del fn_args

    def wrapper(*args, **kw):
        if before:
            if pos_arg is None:
                if named_arg not in kw:
                    raise sa_exc.ArgumentError(
                        "Missing argument %s" % argument)
                value = kw[named_arg]
            else:
                if len(args) > pos_arg:
                    value = args[pos_arg]
                elif named_arg in kw:
                    value = kw[named_arg]
                else:
                    raise sa_exc.ArgumentError(
                        "Missing argument %s" % argument)

        initiator = kw.pop('_sa_initiator', None)
        if initiator is False:
            executor = None
        else:
            executor = getattr(args[0], '_sa_adapter', None)

        if before and executor:
            getattr(executor, before)(value, initiator)

        if not after or not executor:
            return method(*args, **kw)
        else:
            res = method(*args, **kw)
            if res is not None:
                getattr(executor, after)(res, initiator)
            return res

    wrapper._sa_instrumented = True
    if hasattr(method, "_sa_instrument_role"):
        wrapper._sa_instrument_role = method._sa_instrument_role
    wrapper.__name__ = method.__name__
    wrapper.__doc__ = method.__doc__
    return wrapper


def __set(collection, item, _sa_initiator=None):
    """Run set events, may eventually be inlined into decorators."""

    if _sa_initiator is not False:
        executor = getattr(collection, '_sa_adapter', None)
        if executor:
            item = getattr(executor, 'fire_append_event')(item, _sa_initiator)
    return item


def __del(collection, item, _sa_initiator=None):
    """Run del events, may eventually be inlined into decorators."""
    if _sa_initiator is not False:
        executor = getattr(collection, '_sa_adapter', None)
        if executor:
            getattr(executor, 'fire_remove_event')(item, _sa_initiator)


def __before_delete(collection, _sa_initiator=None):
    """Special method to run 'commit existing value' methods"""
    executor = getattr(collection, '_sa_adapter', None)
    if executor:
        getattr(executor, 'fire_pre_remove_event')(_sa_initiator)


def _list_decorators():
    """Tailored instrumentation wrappers for any list-like class."""

    def _tidy(fn):
        setattr(fn, '_sa_instrumented', True)
        fn.__doc__ = getattr(getattr(list, fn.__name__), '__doc__')

    def append(fn):
        def append(self, item, _sa_initiator=None):
            item = __set(self, item, _sa_initiator)
            fn(self, item)
        _tidy(append)
        return append

    def remove(fn):
        def remove(self, value, _sa_initiator=None):
            __before_delete(self, _sa_initiator)
            # testlib.pragma exempt:__eq__
            fn(self, value)
            __del(self, value, _sa_initiator)
        _tidy(remove)
        return remove

    def insert(fn):
        def insert(self, index, value):
            value = __set(self, value)
            fn(self, index, value)
        _tidy(insert)
        return insert

    def __setitem__(fn):
        def __setitem__(self, index, value):
            if not isinstance(index, slice):
                existing = self[index]
                if existing is not None:
                    __del(self, existing)
                value = __set(self, value)
                fn(self, index, value)
            else:
                # slice assignment requires __delitem__, insert, __len__
                step = index.step or 1
                start = index.start or 0
                if start < 0:
                    start += len(self)
                if index.stop is not None:
                    stop = index.stop
                else:
                    stop = len(self)
                if stop < 0:
                    stop += len(self)

                if step == 1:
                    for i in xrange(start, stop, step):
                        if len(self) > start:
                            del self[start]

                    for i, item in enumerate(value):
                        self.insert(i + start, item)
                else:
                    rng = range(start, stop, step)
                    if len(value) != len(rng):
                        raise ValueError(
                            "attempt to assign sequence of size %s to "
                            "extended slice of size %s" % (len(value),
                                                           len(rng)))
                    for i, item in zip(rng, value):
                        self.__setitem__(i, item)
        _tidy(__setitem__)
        return __setitem__

    def __delitem__(fn):
        def __delitem__(self, index):
            if not isinstance(index, slice):
                item = self[index]
                __del(self, item)
                fn(self, index)
            else:
                # slice deletion requires __getslice__ and a slice-groking
                # __getitem__ for stepped deletion
                # note: not breaking this into atomic dels
                for item in self[index]:
                    __del(self, item)
                fn(self, index)
        _tidy(__delitem__)
        return __delitem__

    # Py2K
    def __setslice__(fn):
        def __setslice__(self, start, end, values):
            for value in self[start:end]:
                __del(self, value)
            values = [__set(self, value) for value in values]
            fn(self, start, end, values)
        _tidy(__setslice__)
        return __setslice__

    def __delslice__(fn):
        def __delslice__(self, start, end):
            for value in self[start:end]:
                __del(self, value)
            fn(self, start, end)
        _tidy(__delslice__)
        return __delslice__
    # end Py2K

    def extend(fn):
        def extend(self, iterable):
            for value in iterable:
                self.append(value)
        _tidy(extend)
        return extend

    def __iadd__(fn):
        def __iadd__(self, iterable):
            # list.__iadd__ takes any iterable and seems to let TypeError raise
            # as-is instead of returning NotImplemented
            for value in iterable:
                self.append(value)
            return self
        _tidy(__iadd__)
        return __iadd__

    def pop(fn):
        def pop(self, index=-1):
            __before_delete(self)
            item = fn(self, index)
            __del(self, item)
            return item
        _tidy(pop)
        return pop

    # __imul__ : not wrapping this.  all members of the collection are already
    # present, so no need to fire appends... wrapping it with an explicit
    # decorator is still possible, so events on *= can be had if they're
    # desired.  hard to imagine a use case for __imul__, though.

    l = locals().copy()
    l.pop('_tidy')
    return l


def _dict_decorators():
    """Tailored instrumentation wrappers for any dict-like mapping class."""

    def _tidy(fn):
        setattr(fn, '_sa_instrumented', True)
        fn.__doc__ = getattr(getattr(dict, fn.__name__), '__doc__')

    Unspecified = util.symbol('Unspecified')

    def __setitem__(fn):
        def __setitem__(self, key, value, _sa_initiator=None):
            if key in self:
                __del(self, self[key], _sa_initiator)
            value = __set(self, value, _sa_initiator)
            fn(self, key, value)
        _tidy(__setitem__)
        return __setitem__

    def __delitem__(fn):
        def __delitem__(self, key, _sa_initiator=None):
            if key in self:
                __del(self, self[key], _sa_initiator)
            fn(self, key)
        _tidy(__delitem__)
        return __delitem__

    def clear(fn):
        def clear(self):
            for key in self:
                __del(self, self[key])
            fn(self)
        _tidy(clear)
        return clear

    def pop(fn):
        def pop(self, key, default=Unspecified):
            if key in self:
                __del(self, self[key])
            if default is Unspecified:
                return fn(self, key)
            else:
                return fn(self, key, default)
        _tidy(pop)
        return pop

    def popitem(fn):
        def popitem(self):
            __before_delete(self)
            item = fn(self)
            __del(self, item[1])
            return item
        _tidy(popitem)
        return popitem

    def setdefault(fn):
        def setdefault(self, key, default=None):
            if key not in self:
                self.__setitem__(key, default)
                return default
            else:
                return self.__getitem__(key)
        _tidy(setdefault)
        return setdefault

    def update(fn):
        def update(self, __other=Unspecified, **kw):
            if __other is not Unspecified:
                if hasattr(__other, 'keys'):
                    for key in __other.keys():
                        if (key not in self or
                            self[key] is not __other[key]):
                            self[key] = __other[key]
                else:
                    for key, value in __other:
                        if key not in self or self[key] is not value:
                            self[key] = value
            for key in kw:
                if key not in self or self[key] is not kw[key]:
                    self[key] = kw[key]
        _tidy(update)
        return update

    l = locals().copy()
    l.pop('_tidy')
    l.pop('Unspecified')
    return l

if util.py3k_warning:
    _set_binop_bases = (set, frozenset)
else:
    import sets
    _set_binop_bases = (set, frozenset, sets.BaseSet)


def _set_binops_check_strict(self, obj):
    """Allow only set, frozenset and self.__class__-derived
    objects in binops."""
    return isinstance(obj, _set_binop_bases + (self.__class__,))


def _set_binops_check_loose(self, obj):
    """Allow anything set-like to participate in set binops."""
    return (isinstance(obj, _set_binop_bases + (self.__class__,)) or
            util.duck_type_collection(obj) == set)


def _set_decorators():
    """Tailored instrumentation wrappers for any set-like class."""

    def _tidy(fn):
        setattr(fn, '_sa_instrumented', True)
        fn.__doc__ = getattr(getattr(set, fn.__name__), '__doc__')

    Unspecified = util.symbol('Unspecified')

    def add(fn):
        def add(self, value, _sa_initiator=None):
            if value not in self:
                value = __set(self, value, _sa_initiator)
            # testlib.pragma exempt:__hash__
            fn(self, value)
        _tidy(add)
        return add

    def discard(fn):
        def discard(self, value, _sa_initiator=None):
            # testlib.pragma exempt:__hash__
            if value in self:
                __del(self, value, _sa_initiator)
                # testlib.pragma exempt:__hash__
            fn(self, value)
        _tidy(discard)
        return discard

    def remove(fn):
        def remove(self, value, _sa_initiator=None):
            # testlib.pragma exempt:__hash__
            if value in self:
                __del(self, value, _sa_initiator)
            # testlib.pragma exempt:__hash__
            fn(self, value)
        _tidy(remove)
        return remove

    def pop(fn):
        def pop(self):
            __before_delete(self)
            item = fn(self)
            __del(self, item)
            return item
        _tidy(pop)
        return pop

    def clear(fn):
        def clear(self):
            for item in list(self):
                self.remove(item)
        _tidy(clear)
        return clear

    def update(fn):
        def update(self, value):
            for item in value:
                self.add(item)
        _tidy(update)
        return update

    def __ior__(fn):
        def __ior__(self, value):
            if not _set_binops_check_strict(self, value):
                return NotImplemented
            for item in value:
                self.add(item)
            return self
        _tidy(__ior__)
        return __ior__

    def difference_update(fn):
        def difference_update(self, value):
            for item in value:
                self.discard(item)
        _tidy(difference_update)
        return difference_update

    def __isub__(fn):
        def __isub__(self, value):
            if not _set_binops_check_strict(self, value):
                return NotImplemented
            for item in value:
                self.discard(item)
            return self
        _tidy(__isub__)
        return __isub__

    def intersection_update(fn):
        def intersection_update(self, other):
            want, have = self.intersection(other), set(self)
            remove, add = have - want, want - have

            for item in remove:
                self.remove(item)
            for item in add:
                self.add(item)
        _tidy(intersection_update)
        return intersection_update

    def __iand__(fn):
        def __iand__(self, other):
            if not _set_binops_check_strict(self, other):
                return NotImplemented
            want, have = self.intersection(other), set(self)
            remove, add = have - want, want - have

            for item in remove:
                self.remove(item)
            for item in add:
                self.add(item)
            return self
        _tidy(__iand__)
        return __iand__

    def symmetric_difference_update(fn):
        def symmetric_difference_update(self, other):
            want, have = self.symmetric_difference(other), set(self)
            remove, add = have - want, want - have

            for item in remove:
                self.remove(item)
            for item in add:
                self.add(item)
        _tidy(symmetric_difference_update)
        return symmetric_difference_update

    def __ixor__(fn):
        def __ixor__(self, other):
            if not _set_binops_check_strict(self, other):
                return NotImplemented
            want, have = self.symmetric_difference(other), set(self)
            remove, add = have - want, want - have

            for item in remove:
                self.remove(item)
            for item in add:
                self.add(item)
            return self
        _tidy(__ixor__)
        return __ixor__

    l = locals().copy()
    l.pop('_tidy')
    l.pop('Unspecified')
    return l


class InstrumentedList(list):
    """An instrumented version of the built-in list."""


class InstrumentedSet(set):
    """An instrumented version of the built-in set."""


class InstrumentedDict(dict):
    """An instrumented version of the built-in dict."""


__canned_instrumentation = {
    list: InstrumentedList,
    set: InstrumentedSet,
    dict: InstrumentedDict,
    }

__interfaces = {
    list: (
        {'appender': 'append', 'remover': 'remove',
           'iterator': '__iter__'}, _list_decorators()
        ),

    set: ({'appender': 'add',
          'remover': 'remove',
          'iterator': '__iter__'}, _set_decorators()
        ),

    # decorators are required for dicts and object collections.
    # Py3K
    #dict: ({'iterator': 'values'}, _dict_decorators()),
    # Py2K
    dict: ({'iterator': 'itervalues'}, _dict_decorators()),
    # end Py2K
    }


class MappedCollection(dict):
    """A basic dictionary-based collection class.

    Extends dict with the minimal bag semantics that collection
    classes require. ``set`` and ``remove`` are implemented in terms
    of a keying function: any callable that takes an object and
    returns an object for use as a dictionary key.

    """

    def __init__(self, keyfunc):
        """Create a new collection with keying provided by keyfunc.

        keyfunc may be any callable any callable that takes an object and
        returns an object for use as a dictionary key.

        The keyfunc will be called every time the ORM needs to add a member by
        value-only (such as when loading instances from the database) or
        remove a member.  The usual cautions about dictionary keying apply-
        ``keyfunc(object)`` should return the same output for the life of the
        collection.  Keying based on mutable properties can result in
        unreachable instances "lost" in the collection.

        """
        self.keyfunc = keyfunc

    @collection.appender
    @collection.internally_instrumented
    def set(self, value, _sa_initiator=None):
        """Add an item by value, consulting the keyfunc for the key."""

        key = self.keyfunc(value)
        self.__setitem__(key, value, _sa_initiator)

    @collection.remover
    @collection.internally_instrumented
    def remove(self, value, _sa_initiator=None):
        """Remove an item by value, consulting the keyfunc for the key."""

        key = self.keyfunc(value)
        # Let self[key] raise if key is not in this collection
        # testlib.pragma exempt:__ne__
        if self[key] != value:
            raise sa_exc.InvalidRequestError(
                "Can not remove '%s': collection holds '%s' for key '%s'. "
                "Possible cause: is the MappedCollection key function "
                "based on mutable properties or properties that only obtain "
                "values after flush?" %
                (value, self[key], key))
        self.__delitem__(key, _sa_initiator)

    @collection.converter
    def _convert(self, dictlike):
        """Validate and convert a dict-like object into values for set()ing.

        This is called behind the scenes when a MappedCollection is replaced
        entirely by another collection, as in::

          myobj.mappedcollection = {'a':obj1, 'b': obj2} # ...

        Raises a TypeError if the key in any (key, value) pair in the dictlike
        object does not match the key that this collection's keyfunc would
        have assigned for that value.

        """
        for incoming_key, value in util.dictlike_iteritems(dictlike):
            new_key = self.keyfunc(value)
            if incoming_key != new_key:
                raise TypeError(
                    "Found incompatible key %r for value %r; this "
                    "collection's "
                    "keying function requires a key of %r for this value." % (
                    incoming_key, value, new_key))
            yield value

# ensure instrumentation is associated with
# these built-in classes; if a user-defined class
# subclasses these and uses @internally_instrumented,
# the superclass is otherwise not instrumented.
# see [ticket:2406].
_instrument_class(MappedCollection)
_instrument_class(InstrumentedList)
_instrument_class(InstrumentedSet)
