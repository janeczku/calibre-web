# orm/dynamic.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Dynamic collection API.

Dynamic collections act like Query() objects for read operations and support
basic add/delete mutation.

"""

from .. import log, util, exc
from ..sql import operators
from . import (
    attributes, object_session, util as orm_util, strategies,
    object_mapper, exc as orm_exc
    )
from .query import Query


class DynaLoader(strategies.AbstractRelationshipLoader):
    def init_class_attribute(self, mapper):
        self.is_class_level = True
        if not self.uselist:
            raise exc.InvalidRequestError(
                "On relationship %s, 'dynamic' loaders cannot be used with "
                "many-to-one/one-to-one relationships and/or "
                "uselist=False." % self.parent_property)
        strategies._register_attribute(self,
            mapper,
            useobject=True,
            uselist=True,
            impl_class=DynamicAttributeImpl,
            target_mapper=self.parent_property.mapper,
            order_by=self.parent_property.order_by,
            query_class=self.parent_property.query_class,
            backref=self.parent_property.back_populates,
        )

log.class_logger(DynaLoader)


class DynamicAttributeImpl(attributes.AttributeImpl):
    uses_objects = True
    accepts_scalar_loader = False
    supports_population = False
    collection = False

    def __init__(self, class_, key, typecallable,
                     dispatch,
                     target_mapper, order_by, query_class=None, **kw):
        super(DynamicAttributeImpl, self).\
                    __init__(class_, key, typecallable, dispatch, **kw)
        self.target_mapper = target_mapper
        self.order_by = order_by
        if not query_class:
            self.query_class = AppenderQuery
        elif AppenderMixin in query_class.mro():
            self.query_class = query_class
        else:
            self.query_class = mixin_user_query(query_class)

    def get(self, state, dict_, passive=attributes.PASSIVE_OFF):
        if not passive & attributes.SQL_OK:
            return self._get_collection_history(state,
                    attributes.PASSIVE_NO_INITIALIZE).added_items
        else:
            return self.query_class(self, state)

    def get_collection(self, state, dict_, user_data=None,
                            passive=attributes.PASSIVE_NO_INITIALIZE):
        if not passive & attributes.SQL_OK:
            return self._get_collection_history(state,
                    passive).added_items
        else:
            history = self._get_collection_history(state, passive)
            return history.added_plus_unchanged

    def fire_append_event(self, state, dict_, value, initiator,
                                                    collection_history=None):
        if collection_history is None:
            collection_history = self._modified_event(state, dict_)

        collection_history.add_added(value)

        for fn in self.dispatch.append:
            value = fn(state, value, initiator or self)

        if self.trackparent and value is not None:
            self.sethasparent(attributes.instance_state(value), state, True)

    def fire_remove_event(self, state, dict_, value, initiator,
                                                    collection_history=None):
        if collection_history is None:
            collection_history = self._modified_event(state, dict_)

        collection_history.add_removed(value)

        if self.trackparent and value is not None:
            self.sethasparent(attributes.instance_state(value), state, False)

        for fn in self.dispatch.remove:
            fn(state, value, initiator or self)

    def _modified_event(self, state, dict_):

        if self.key not in state.committed_state:
            state.committed_state[self.key] = CollectionHistory(self, state)

        state._modified_event(dict_,
                                self,
                                attributes.NEVER_SET)

        # this is a hack to allow the fixtures.ComparableEntity fixture
        # to work
        dict_[self.key] = True
        return state.committed_state[self.key]

    def set(self, state, dict_, value, initiator,
                        passive=attributes.PASSIVE_OFF,
                        check_old=None, pop=False):
        if initiator and initiator.parent_token is self.parent_token:
            return

        if pop and value is None:
            return
        self._set_iterable(state, dict_, value)

    def _set_iterable(self, state, dict_, iterable, adapter=None):
        new_values = list(iterable)
        if state.has_identity:
            old_collection = util.IdentitySet(self.get(state, dict_))

        collection_history = self._modified_event(state, dict_)
        if not state.has_identity:
            old_collection = collection_history.added_items
        else:
            old_collection = old_collection.union(
                                    collection_history.added_items)

        idset = util.IdentitySet
        constants = old_collection.intersection(new_values)
        additions = idset(new_values).difference(constants)
        removals = old_collection.difference(constants)

        for member in new_values:
            if member in additions:
                self.fire_append_event(state, dict_, member, None,
                                        collection_history=collection_history)

        for member in removals:
            self.fire_remove_event(state, dict_, member, None,
                                        collection_history=collection_history)

    def delete(self, *args, **kwargs):
        raise NotImplementedError()

    def set_committed_value(self, state, dict_, value):
        raise NotImplementedError("Dynamic attributes don't support "
                                  "collection population.")

    def get_history(self, state, dict_, passive=attributes.PASSIVE_OFF):
        c = self._get_collection_history(state, passive)
        return c.as_history()

    def get_all_pending(self, state, dict_):
        c = self._get_collection_history(
            state, attributes.PASSIVE_NO_INITIALIZE)
        return [
                (attributes.instance_state(x), x)
                for x in
                c.all_items
            ]

    def _get_collection_history(self, state, passive=attributes.PASSIVE_OFF):
        if self.key in state.committed_state:
            c = state.committed_state[self.key]
        else:
            c = CollectionHistory(self, state)

        if state.has_identity and (passive & attributes.INIT_OK):
            return CollectionHistory(self, state, apply_to=c)
        else:
            return c

    def append(self, state, dict_, value, initiator,
                            passive=attributes.PASSIVE_OFF):
        if initiator is not self:
            self.fire_append_event(state, dict_, value, initiator)

    def remove(self, state, dict_, value, initiator,
                            passive=attributes.PASSIVE_OFF):
        if initiator is not self:
            self.fire_remove_event(state, dict_, value, initiator)

    def pop(self, state, dict_, value, initiator,
                                            passive=attributes.PASSIVE_OFF):
        self.remove(state, dict_, value, initiator, passive=passive)


class AppenderMixin(object):
    query_class = None

    def __init__(self, attr, state):
        super(AppenderMixin, self).__init__(attr.target_mapper, None)
        self.instance = instance = state.obj()
        self.attr = attr

        mapper = object_mapper(instance)
        prop = mapper._props[self.attr.key]
        self._criterion = prop.compare(
                            operators.eq,
                            instance,
                            value_is_parent=True,
                            alias_secondary=False)

        if self.attr.order_by:
            self._order_by = self.attr.order_by

    def session(self):
        sess = object_session(self.instance)
        if sess is not None and self.autoflush and sess.autoflush \
            and self.instance in sess:
            sess.flush()
        if not orm_util.has_identity(self.instance):
            return None
        else:
            return sess
    session = property(session, lambda s, x: None)

    def __iter__(self):
        sess = self.session
        if sess is None:
            return iter(self.attr._get_collection_history(
                attributes.instance_state(self.instance),
                attributes.PASSIVE_NO_INITIALIZE).added_items)
        else:
            return iter(self._clone(sess))

    def __getitem__(self, index):
        sess = self.session
        if sess is None:
            return self.attr._get_collection_history(
                attributes.instance_state(self.instance),
                attributes.PASSIVE_NO_INITIALIZE).indexed(index)
        else:
            return self._clone(sess).__getitem__(index)

    def count(self):
        sess = self.session
        if sess is None:
            return len(self.attr._get_collection_history(
                attributes.instance_state(self.instance),
                attributes.PASSIVE_NO_INITIALIZE).added_items)
        else:
            return self._clone(sess).count()

    def _clone(self, sess=None):
        # note we're returning an entirely new Query class instance
        # here without any assignment capabilities; the class of this
        # query is determined by the session.
        instance = self.instance
        if sess is None:
            sess = object_session(instance)
            if sess is None:
                raise orm_exc.DetachedInstanceError(
                    "Parent instance %s is not bound to a Session, and no "
                    "contextual session is established; lazy load operation "
                    "of attribute '%s' cannot proceed" % (
                        orm_util.instance_str(instance), self.attr.key))

        if self.query_class:
            query = self.query_class(self.attr.target_mapper, session=sess)
        else:
            query = sess.query(self.attr.target_mapper)

        query._criterion = self._criterion
        query._order_by = self._order_by

        return query

    def extend(self, iterator):
        for item in iterator:
            self.attr.append(
                attributes.instance_state(self.instance),
                attributes.instance_dict(self.instance), item, None)

    def append(self, item):
        self.attr.append(
            attributes.instance_state(self.instance),
            attributes.instance_dict(self.instance), item, None)

    def remove(self, item):
        self.attr.remove(
            attributes.instance_state(self.instance),
            attributes.instance_dict(self.instance), item, None)


class AppenderQuery(AppenderMixin, Query):
    """A dynamic query that supports basic collection storage operations."""


def mixin_user_query(cls):
    """Return a new class with AppenderQuery functionality layered over."""
    name = 'Appender' + cls.__name__
    return type(name, (AppenderMixin, cls), {'query_class': cls})


class CollectionHistory(object):
    """Overrides AttributeHistory to receive append/remove events directly."""

    def __init__(self, attr, state, apply_to=None):
        if apply_to:
            coll = AppenderQuery(attr, state).autoflush(False)
            self.unchanged_items = util.OrderedIdentitySet(coll)
            self.added_items = apply_to.added_items
            self.deleted_items = apply_to.deleted_items
            self._reconcile_collection = True
        else:
            self.deleted_items = util.OrderedIdentitySet()
            self.added_items = util.OrderedIdentitySet()
            self.unchanged_items = util.OrderedIdentitySet()
            self._reconcile_collection = False

    @property
    def added_plus_unchanged(self):
        return list(self.added_items.union(self.unchanged_items))

    @property
    def all_items(self):
        return list(self.added_items.union(
                        self.unchanged_items).union(self.deleted_items))

    def as_history(self):
        if self._reconcile_collection:
            added = self.added_items.difference(self.unchanged_items)
            deleted = self.deleted_items.intersection(self.unchanged_items)
            unchanged = self.unchanged_items.difference(deleted)
        else:
            added, unchanged, deleted = self.added_items,\
                                            self.unchanged_items,\
                                            self.deleted_items
        return attributes.History(
                    list(added),
                    list(unchanged),
                    list(deleted),
                )

    def indexed(self, index):
        return list(self.added_items)[index]

    def add_added(self, value):
        self.added_items.add(value)

    def add_removed(self, value):
        if value in self.added_items:
            self.added_items.remove(value)
        else:
            self.deleted_items.add(value)

