# orm/state.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Defines instrumentation of instances.

This module is usually not directly visible to user applications, but
defines a large part of the ORM's interactivity.

"""

import weakref
from .. import util
from . import exc as orm_exc, attributes, util as orm_util, interfaces
from .attributes import (
    PASSIVE_NO_RESULT,
    SQL_OK, NEVER_SET, ATTR_WAS_SET, NO_VALUE,\
    PASSIVE_NO_INITIALIZE
    )
sessionlib = util.importlater("sqlalchemy.orm", "session")
instrumentation = util.importlater("sqlalchemy.orm", "instrumentation")
mapperlib = util.importlater("sqlalchemy.orm", "mapperlib")


class InstanceState(interfaces._InspectionAttr):
    """tracks state information at the instance level."""

    session_id = None
    key = None
    runid = None
    load_options = util.EMPTY_SET
    load_path = ()
    insert_order = None
    _strong_obj = None
    modified = False
    expired = False
    deleted = False
    _load_pending = False

    is_instance = True

    def __init__(self, obj, manager):
        self.class_ = obj.__class__
        self.manager = manager
        self.obj = weakref.ref(obj, self._cleanup)
        self.callables = {}
        self.committed_state = {}

    @util.memoized_property
    def attrs(self):
        """Return a namespace representing each attribute on
        the mapped object, including its current value
        and history.

        The returned object is an instance of :class:`.AttributeState`.

        """
        return util.ImmutableProperties(
            dict(
                (key, AttributeState(self, key))
                for key in self.manager
            )
        )

    @property
    def transient(self):
        """Return true if the object is transient."""
        return self.key is None and \
            not self._attached

    @property
    def pending(self):
        """Return true if the object is pending."""
        return self.key is None and \
            self._attached

    @property
    def persistent(self):
        """Return true if the object is persistent."""
        return self.key is not None and \
            self._attached

    @property
    def detached(self):
        """Return true if the object is detached."""
        return self.key is not None and \
            not self._attached

    @property
    def _attached(self):
        return self.session_id is not None and \
            self.session_id in sessionlib._sessions

    @property
    def session(self):
        """Return the owning :class:`.Session` for this instance,
        or ``None`` if none available."""

        return sessionlib._state_session(self)

    @property
    def object(self):
        """Return the mapped object represented by this
        :class:`.InstanceState`."""
        return self.obj()

    @property
    def identity(self):
        """Return the mapped identity of the mapped object.
        This is the primary key identity as persisted by the ORM
        which can always be passed directly to
        :meth:`.Query.get`.

        Returns ``None`` if the object has no primary key identity.

        .. note::
            An object which is transient or pending
            does **not** have a mapped identity until it is flushed,
            even if its attributes include primary key values.

        """
        if self.key is None:
            return None
        else:
            return self.key[1]

    @property
    def identity_key(self):
        """Return the identity key for the mapped object.

        This is the key used to locate the object within
        the :attr:`.Session.identity_map` mapping.   It contains
        the identity as returned by :attr:`.identity` within it.


        """
        # TODO: just change .key to .identity_key across
        # the board ?  probably
        return self.key

    @util.memoized_property
    def parents(self):
        return {}

    @util.memoized_property
    def _pending_mutations(self):
        return {}

    @util.memoized_property
    def mapper(self):
        """Return the :class:`.Mapper` used for this mapepd object."""
        return self.manager.mapper

    @property
    def has_identity(self):
        """Return ``True`` if this object has an identity key.

        This should always have the same value as the
        expression ``state.persistent or state.detached``.

        """
        return bool(self.key)

    def _detach(self):
        self.session_id = self._strong_obj = None

    def _dispose(self):
        self._detach()
        del self.obj

    def _cleanup(self, ref):
        instance_dict = self._instance_dict()
        if instance_dict:
            instance_dict.discard(self)

        self.callables = {}
        self.session_id = self._strong_obj = None
        del self.obj

    def obj(self):
        return None

    @property
    def dict(self):
        o = self.obj()
        if o is not None:
            return attributes.instance_dict(o)
        else:
            return {}

    def _initialize_instance(*mixed, **kwargs):
        self, instance, args = mixed[0], mixed[1], mixed[2:]
        manager = self.manager

        manager.dispatch.init(self, args, kwargs)

        try:
            return manager.original_init(*mixed[1:], **kwargs)
        except:
            manager.dispatch.init_failure(self, args, kwargs)
            raise

    def get_history(self, key, passive):
        return self.manager[key].impl.get_history(self, self.dict, passive)

    def get_impl(self, key):
        return self.manager[key].impl

    def _get_pending_mutation(self, key):
        if key not in self._pending_mutations:
            self._pending_mutations[key] = PendingCollection()
        return self._pending_mutations[key]

    def __getstate__(self):
        d = {'instance': self.obj()}
        d.update(
            (k, self.__dict__[k]) for k in (
                'committed_state', '_pending_mutations', 'modified', 'expired',
                'callables', 'key', 'parents', 'load_options',
                'class_',
            ) if k in self.__dict__
        )
        if self.load_path:
            d['load_path'] = self.load_path.serialize()

        self.manager.dispatch.pickle(self, d)

        return d

    def __setstate__(self, state):
        inst = state['instance']
        if inst is not None:
            self.obj = weakref.ref(inst, self._cleanup)
            self.class_ = inst.__class__
        else:
            # None being possible here generally new as of 0.7.4
            # due to storage of state in "parents".  "class_"
            # also new.
            self.obj = None
            self.class_ = state['class_']
        self.manager = manager = instrumentation.manager_of_class(self.class_)
        if manager is None:
            raise orm_exc.UnmappedInstanceError(
                        inst,
                        "Cannot deserialize object of type %r - "
                        "no mapper() has "
                        "been configured for this class within the current "
                        "Python process!" %
                        self.class_)
        elif manager.is_mapped and not manager.mapper.configured:
            mapperlib.configure_mappers()

        self.committed_state = state.get('committed_state', {})
        self._pending_mutations = state.get('_pending_mutations', {})
        self.parents = state.get('parents', {})
        self.modified = state.get('modified', False)
        self.expired = state.get('expired', False)
        self.callables = state.get('callables', {})

        self.__dict__.update([
            (k, state[k]) for k in (
                'key', 'load_options',
            ) if k in state
        ])

        if 'load_path' in state:
            self.load_path = orm_util.PathRegistry.\
                                deserialize(state['load_path'])

        # setup _sa_instance_state ahead of time so that
        # unpickle events can access the object normally.
        # see [ticket:2362]
        if inst is not None:
            manager.setup_instance(inst, self)
        manager.dispatch.unpickle(self, state)

    def _initialize(self, key):
        """Set this attribute to an empty value or collection,
           based on the AttributeImpl in use."""

        self.manager.get_impl(key).initialize(self, self.dict)

    def _reset(self, dict_, key):
        """Remove the given attribute and any
           callables associated with it."""

        old = dict_.pop(key, None)
        if old is not None and self.manager[key].impl.collection:
            self.manager[key].impl._invalidate_collection(old)
        self.callables.pop(key, None)

    def _expire_attribute_pre_commit(self, dict_, key):
        """a fast expire that can be called by column loaders during a load.

        The additional bookkeeping is finished up in commit_all().

        Should only be called for scalar attributes.

        This method is actually called a lot with joined-table
        loading, when the second table isn't present in the result.

        """
        dict_.pop(key, None)
        self.callables[key] = self

    @classmethod
    def _row_processor(cls, manager, fn, key):
        impl = manager[key].impl
        if impl.collection:
            def _set_callable(state, dict_, row):
                old = dict_.pop(key, None)
                if old is not None:
                    impl._invalidate_collection(old)
                state.callables[key] = fn
        else:
            def _set_callable(state, dict_, row):
                state.callables[key] = fn
        return _set_callable

    def _expire(self, dict_, modified_set):
        self.expired = True
        if self.modified:
            modified_set.discard(self)

        self.modified = False
        self._strong_obj = None

        self.committed_state.clear()

        InstanceState._pending_mutations._reset(self)

        # clear out 'parents' collection.  not
        # entirely clear how we can best determine
        # which to remove, or not.
        InstanceState.parents._reset(self)

        for key in self.manager:
            impl = self.manager[key].impl
            if impl.accepts_scalar_loader and \
                    (impl.expire_missing or key in dict_):
                self.callables[key] = self
            old = dict_.pop(key, None)
            if impl.collection and old is not None:
                impl._invalidate_collection(old)

        self.manager.dispatch.expire(self, None)

    def _expire_attributes(self, dict_, attribute_names):
        pending = self.__dict__.get('_pending_mutations', None)

        for key in attribute_names:
            impl = self.manager[key].impl
            if impl.accepts_scalar_loader:
                self.callables[key] = self
            old = dict_.pop(key, None)
            if impl.collection and old is not None:
                impl._invalidate_collection(old)

            self.committed_state.pop(key, None)
            if pending:
                pending.pop(key, None)

        self.manager.dispatch.expire(self, attribute_names)

    def __call__(self, state, passive):
        """__call__ allows the InstanceState to act as a deferred
        callable for loading expired attributes, which is also
        serializable (picklable).

        """

        if not passive & SQL_OK:
            return PASSIVE_NO_RESULT

        toload = self.expired_attributes.\
                        intersection(self.unmodified)

        self.manager.deferred_scalar_loader(self, toload)

        # if the loader failed, or this
        # instance state didn't have an identity,
        # the attributes still might be in the callables
        # dict.  ensure they are removed.
        for k in toload.intersection(self.callables):
            del self.callables[k]

        return ATTR_WAS_SET

    @property
    def unmodified(self):
        """Return the set of keys which have no uncommitted changes"""

        return set(self.manager).difference(self.committed_state)

    def unmodified_intersection(self, keys):
        """Return self.unmodified.intersection(keys)."""

        return set(keys).intersection(self.manager).\
                    difference(self.committed_state)

    @property
    def unloaded(self):
        """Return the set of keys which do not have a loaded value.

        This includes expired attributes and any other attribute that
        was never populated or modified.

        """
        return set(self.manager).\
                    difference(self.committed_state).\
                    difference(self.dict)

    @property
    def expired_attributes(self):
        """Return the set of keys which are 'expired' to be loaded by
           the manager's deferred scalar loader, assuming no pending
           changes.

           see also the ``unmodified`` collection which is intersected
           against this set when a refresh operation occurs.

        """
        return set([k for k, v in self.callables.items() if v is self])

    def _instance_dict(self):
        return None

    def _modified_event(self, dict_, attr, previous, collection=False):
        if attr.key not in self.committed_state:
            if collection:
                if previous is NEVER_SET:
                    if attr.key in dict_:
                        previous = dict_[attr.key]

                if previous not in (None, NO_VALUE, NEVER_SET):
                    previous = attr.copy(previous)

            self.committed_state[attr.key] = previous

        # assert self._strong_obj is None or self.modified

        if (self.session_id and self._strong_obj is None) \
                or not self.modified:
            instance_dict = self._instance_dict()
            if instance_dict:
                instance_dict._modified.add(self)

            # only create _strong_obj link if attached
            # to a session

            inst = self.obj()
            if self.session_id:
                self._strong_obj = inst

            if inst is None:
                raise orm_exc.ObjectDereferencedError(
                        "Can't emit change event for attribute '%s' - "
                        "parent object of type %s has been garbage "
                        "collected."
                        % (
                            self.manager[attr.key],
                            orm_util.state_class_str(self)
                        ))
            self.modified = True

    def _commit(self, dict_, keys):
        """Commit attributes.

        This is used by a partial-attribute load operation to mark committed
        those attributes which were refreshed from the database.

        Attributes marked as "expired" can potentially remain "expired" after
        this step if a value was not populated in state.dict.

        """
        for key in keys:
            self.committed_state.pop(key, None)

        self.expired = False

        for key in set(self.callables).\
                            intersection(keys).\
                            intersection(dict_):
            del self.callables[key]

    def _commit_all(self, dict_, instance_dict=None):
        """commit all attributes unconditionally.

        This is used after a flush() or a full load/refresh
        to remove all pending state from the instance.

         - all attributes are marked as "committed"
         - the "strong dirty reference" is removed
         - the "modified" flag is set to False
         - any "expired" markers/callables for attributes loaded are removed.

        Attributes marked as "expired" can potentially remain
        "expired" after this step if a value was not populated in state.dict.

        """
        self._commit_all_states([(self, dict_)], instance_dict)

    @classmethod
    def _commit_all_states(self, iter, instance_dict=None):
        """Mass version of commit_all()."""

        for state, dict_ in iter:
            state.committed_state.clear()
            InstanceState._pending_mutations._reset(state)

            callables = state.callables
            for key in list(callables):
                if key in dict_ and callables[key] is state:
                    del callables[key]

            if instance_dict and state.modified:
                instance_dict._modified.discard(state)

            state.modified = state.expired = False
            state._strong_obj = None


class AttributeState(object):
    """Provide an inspection interface corresponding
    to a particular attribute on a particular mapped object.

    The :class:`.AttributeState` object is accessed
    via the :attr:`.InstanceState.attrs` collection
    of a particular :class:`.InstanceState`::

        from sqlalchemy import inspect

        insp = inspect(some_mapped_object)
        attr_state = insp.attrs.some_attribute

    """

    def __init__(self, state, key):
        self.state = state
        self.key = key

    @property
    def loaded_value(self):
        """The current value of this attribute as loaded from the database.

        If the value has not been loaded, or is otherwise not present
        in the object's dictionary, returns NO_VALUE.

        """
        return self.state.dict.get(self.key, NO_VALUE)

    @property
    def value(self):
        """Return the value of this attribute.

        This operation is equivalent to accessing the object's
        attribute directly or via ``getattr()``, and will fire
        off any pending loader callables if needed.

        """
        return self.state.manager[self.key].__get__(
                        self.state.obj(), self.state.class_)

    @property
    def history(self):
        """Return the current pre-flush change history for
        this attribute, via the :class:`.History` interface.

        """
        return self.state.get_history(self.key,
                    PASSIVE_NO_INITIALIZE)


class PendingCollection(object):
    """A writable placeholder for an unloaded collection.

    Stores items appended to and removed from a collection that has not yet
    been loaded. When the collection is loaded, the changes stored in
    PendingCollection are applied to it to produce the final result.

    """
    def __init__(self):
        self.deleted_items = util.IdentitySet()
        self.added_items = util.OrderedIdentitySet()

    def append(self, value):
        if value in self.deleted_items:
            self.deleted_items.remove(value)
        else:
            self.added_items.add(value)

    def remove(self, value):
        if value in self.added_items:
            self.added_items.remove(value)
        else:
            self.deleted_items.add(value)
