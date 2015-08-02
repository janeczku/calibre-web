# orm/descriptor_props.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Descriptor properties are more "auxiliary" properties
that exist as configurational elements, but don't participate
as actively in the load/persist ORM loop.

"""

from .interfaces import MapperProperty, PropComparator
from .util import _none_set
from . import attributes, strategies
from .. import util, sql, exc as sa_exc, event, schema
from ..sql import expression
properties = util.importlater('sqlalchemy.orm', 'properties')


class DescriptorProperty(MapperProperty):
    """:class:`.MapperProperty` which proxies access to a
        user-defined descriptor."""

    doc = None

    def instrument_class(self, mapper):
        prop = self

        class _ProxyImpl(object):
            accepts_scalar_loader = False
            expire_missing = True
            collection = False

            def __init__(self, key):
                self.key = key

            if hasattr(prop, 'get_history'):
                def get_history(self, state, dict_,
                        passive=attributes.PASSIVE_OFF):
                    return prop.get_history(state, dict_, passive)

        if self.descriptor is None:
            desc = getattr(mapper.class_, self.key, None)
            if mapper._is_userland_descriptor(desc):
                self.descriptor = desc

        if self.descriptor is None:
            def fset(obj, value):
                setattr(obj, self.name, value)

            def fdel(obj):
                delattr(obj, self.name)

            def fget(obj):
                return getattr(obj, self.name)

            self.descriptor = property(
                fget=fget,
                fset=fset,
                fdel=fdel,
            )

        proxy_attr = attributes.\
                    create_proxied_attribute(self.descriptor)\
                    (
                        self.parent.class_,
                        self.key,
                        self.descriptor,
                        lambda: self._comparator_factory(mapper),
                        doc=self.doc,
                        original_property=self
                    )
        proxy_attr.impl = _ProxyImpl(self.key)
        mapper.class_manager.instrument_attribute(self.key, proxy_attr)


class CompositeProperty(DescriptorProperty):
    """Defines a "composite" mapped attribute, representing a collection
    of columns as one attribute.

    :class:`.CompositeProperty` is constructed using the :func:`.composite`
    function.

    See also:

    :ref:`mapper_composite`

    """
    def __init__(self, class_, *attrs, **kwargs):
        self.attrs = attrs
        self.composite_class = class_
        self.active_history = kwargs.get('active_history', False)
        self.deferred = kwargs.get('deferred', False)
        self.group = kwargs.get('group', None)
        self.comparator_factory = kwargs.pop('comparator_factory',
                                            self.__class__.Comparator)
        if 'info' in kwargs:
            self.info = kwargs.pop('info')

        util.set_creation_order(self)
        self._create_descriptor()

    def instrument_class(self, mapper):
        super(CompositeProperty, self).instrument_class(mapper)
        self._setup_event_handlers()

    def do_init(self):
        """Initialization which occurs after the :class:`.CompositeProperty`
        has been associated with its parent mapper.

        """
        self._init_props()
        self._setup_arguments_on_columns()

    def _create_descriptor(self):
        """Create the Python descriptor that will serve as
        the access point on instances of the mapped class.

        """

        def fget(instance):
            dict_ = attributes.instance_dict(instance)
            state = attributes.instance_state(instance)

            if self.key not in dict_:
                # key not present.  Iterate through related
                # attributes, retrieve their values.  This
                # ensures they all load.
                values = [
                    getattr(instance, key)
                    for key in self._attribute_keys
                ]

                # current expected behavior here is that the composite is
                # created on access if the object is persistent or if
                # col attributes have non-None.  This would be better
                # if the composite were created unconditionally,
                # but that would be a behavioral change.
                if self.key not in dict_ and (
                    state.key is not None or
                    not _none_set.issuperset(values)
                ):
                    dict_[self.key] = self.composite_class(*values)
                    state.manager.dispatch.refresh(state, None, [self.key])

            return dict_.get(self.key, None)

        def fset(instance, value):
            dict_ = attributes.instance_dict(instance)
            state = attributes.instance_state(instance)
            attr = state.manager[self.key]
            previous = dict_.get(self.key, attributes.NO_VALUE)
            for fn in attr.dispatch.set:
                value = fn(state, value, previous, attr.impl)
            dict_[self.key] = value
            if value is None:
                for key in self._attribute_keys:
                    setattr(instance, key, None)
            else:
                for key, value in zip(
                        self._attribute_keys,
                        value.__composite_values__()):
                    setattr(instance, key, value)

        def fdel(instance):
            state = attributes.instance_state(instance)
            dict_ = attributes.instance_dict(instance)
            previous = dict_.pop(self.key, attributes.NO_VALUE)
            attr = state.manager[self.key]
            attr.dispatch.remove(state, previous, attr.impl)
            for key in self._attribute_keys:
                setattr(instance, key, None)

        self.descriptor = property(fget, fset, fdel)

    @util.memoized_property
    def _comparable_elements(self):
        return [
            getattr(self.parent.class_, prop.key)
            for prop in self.props
        ]

    def _init_props(self):
        self.props = props = []
        for attr in self.attrs:
            if isinstance(attr, basestring):
                prop = self.parent.get_property(attr)
            elif isinstance(attr, schema.Column):
                prop = self.parent._columntoproperty[attr]
            elif isinstance(attr, attributes.InstrumentedAttribute):
                prop = attr.property
            props.append(prop)

    @property
    def columns(self):
        return [a for a in self.attrs if isinstance(a, schema.Column)]

    def _setup_arguments_on_columns(self):
        """Propagate configuration arguments made on this composite
        to the target columns, for those that apply.

        """
        for prop in self.props:
            prop.active_history = self.active_history
            if self.deferred:
                prop.deferred = self.deferred
                prop.strategy_class = strategies.DeferredColumnLoader
            prop.group = self.group

    def _setup_event_handlers(self):
        """Establish events that populate/expire the composite attribute."""

        def load_handler(state, *args):
            dict_ = state.dict

            if self.key in dict_:
                return

            # if column elements aren't loaded, skip.
            # __get__() will initiate a load for those
            # columns
            for k in self._attribute_keys:
                if k not in dict_:
                    return

            #assert self.key not in dict_
            dict_[self.key] = self.composite_class(
                    *[state.dict[key] for key in
                    self._attribute_keys]
                )

        def expire_handler(state, keys):
            if keys is None or set(self._attribute_keys).intersection(keys):
                state.dict.pop(self.key, None)

        def insert_update_handler(mapper, connection, state):
            """After an insert or update, some columns may be expired due
            to server side defaults, or re-populated due to client side
            defaults.  Pop out the composite value here so that it
            recreates.

            """

            state.dict.pop(self.key, None)

        event.listen(self.parent, 'after_insert',
            insert_update_handler, raw=True)
        event.listen(self.parent, 'after_update',
            insert_update_handler, raw=True)
        event.listen(self.parent, 'load',
            load_handler, raw=True, propagate=True)
        event.listen(self.parent, 'refresh',
            load_handler, raw=True, propagate=True)
        event.listen(self.parent, 'expire',
            expire_handler, raw=True, propagate=True)

        # TODO: need a deserialize hook here

    @util.memoized_property
    def _attribute_keys(self):
        return [
            prop.key for prop in self.props
        ]

    def get_history(self, state, dict_, passive=attributes.PASSIVE_OFF):
        """Provided for userland code that uses attributes.get_history()."""

        added = []
        deleted = []

        has_history = False
        for prop in self.props:
            key = prop.key
            hist = state.manager[key].impl.get_history(state, dict_)
            if hist.has_changes():
                has_history = True

            non_deleted = hist.non_deleted()
            if non_deleted:
                added.extend(non_deleted)
            else:
                added.append(None)
            if hist.deleted:
                deleted.extend(hist.deleted)
            else:
                deleted.append(None)

        if has_history:
            return attributes.History(
                [self.composite_class(*added)],
                (),
                [self.composite_class(*deleted)]
            )
        else:
            return attributes.History(
                (), [self.composite_class(*added)], ()
            )

    def _comparator_factory(self, mapper):
        return self.comparator_factory(self, mapper)

    class Comparator(PropComparator):
        """Produce boolean, comparison, and other operators for
        :class:`.CompositeProperty` attributes.

        See the example in :ref:`composite_operations` for an overview
        of usage , as well as the documentation for :class:`.PropComparator`.

        See also:

        :class:`.PropComparator`

        :class:`.ColumnOperators`

        :ref:`types_operators`

        :attr:`.TypeEngine.comparator_factory`

        """

        def __clause_element__(self):
            return expression.ClauseList(group=False, *self._comparable_elements)

        __hash__ = None

        @util.memoized_property
        def _comparable_elements(self):
            if self.adapter:
                # we need to do a little fudging here because
                # the adapter function we're given only accepts
                # ColumnElements, but our prop._comparable_elements is returning
                # InstrumentedAttribute, because we support the use case
                # of composites that refer to relationships.  The better
                # solution here is to open up how AliasedClass interacts
                # with PropComparators so more context is available.
                return [self.adapter(x.__clause_element__())
                            for x in self.prop._comparable_elements]
            else:
                return self.prop._comparable_elements

        def __eq__(self, other):
            if other is None:
                values = [None] * len(self.prop._comparable_elements)
            else:
                values = other.__composite_values__()
            comparisons = [
                a == b
                for a, b in zip(self.prop._comparable_elements, values)
            ]
            if self.adapter:
                comparisons = [self.adapter(x) for x in comparisons]
            return sql.and_(*comparisons)

        def __ne__(self, other):
            return sql.not_(self.__eq__(other))

    def __str__(self):
        return str(self.parent.class_.__name__) + "." + self.key


class ConcreteInheritedProperty(DescriptorProperty):
    """A 'do nothing' :class:`.MapperProperty` that disables
    an attribute on a concrete subclass that is only present
    on the inherited mapper, not the concrete classes' mapper.

    Cases where this occurs include:

    * When the superclass mapper is mapped against a
      "polymorphic union", which includes all attributes from
      all subclasses.
    * When a relationship() is configured on an inherited mapper,
      but not on the subclass mapper.  Concrete mappers require
      that relationship() is configured explicitly on each
      subclass.

    """

    def _comparator_factory(self, mapper):
        comparator_callable = None

        for m in self.parent.iterate_to_root():
            p = m._props[self.key]
            if not isinstance(p, ConcreteInheritedProperty):
                comparator_callable = p.comparator_factory
                break
        return comparator_callable

    def __init__(self):
        def warn():
            raise AttributeError("Concrete %s does not implement "
                "attribute %r at the instance level.  Add this "
                "property explicitly to %s." %
                (self.parent, self.key, self.parent))

        class NoninheritedConcreteProp(object):
            def __set__(s, obj, value):
                warn()

            def __delete__(s, obj):
                warn()

            def __get__(s, obj, owner):
                if obj is None:
                    return self.descriptor
                warn()
        self.descriptor = NoninheritedConcreteProp()


class SynonymProperty(DescriptorProperty):

    def __init__(self, name, map_column=None,
                            descriptor=None, comparator_factory=None,
                            doc=None):
        self.name = name
        self.map_column = map_column
        self.descriptor = descriptor
        self.comparator_factory = comparator_factory
        self.doc = doc or (descriptor and descriptor.__doc__) or None

        util.set_creation_order(self)

    # TODO: when initialized, check _proxied_property,
    # emit a warning if its not a column-based property

    @util.memoized_property
    def _proxied_property(self):
        return getattr(self.parent.class_, self.name).property

    def _comparator_factory(self, mapper):
        prop = self._proxied_property

        if self.comparator_factory:
            comp = self.comparator_factory(prop, mapper)
        else:
            comp = prop.comparator_factory(prop, mapper)
        return comp

    def set_parent(self, parent, init):
        if self.map_column:
            # implement the 'map_column' option.
            if self.key not in parent.mapped_table.c:
                raise sa_exc.ArgumentError(
                    "Can't compile synonym '%s': no column on table "
                    "'%s' named '%s'"
                     % (self.name, parent.mapped_table.description, self.key))
            elif parent.mapped_table.c[self.key] in \
                    parent._columntoproperty and \
                    parent._columntoproperty[
                                            parent.mapped_table.c[self.key]
                                        ].key == self.name:
                raise sa_exc.ArgumentError(
                    "Can't call map_column=True for synonym %r=%r, "
                    "a ColumnProperty already exists keyed to the name "
                    "%r for column %r" %
                    (self.key, self.name, self.name, self.key)
                )
            p = properties.ColumnProperty(parent.mapped_table.c[self.key])
            parent._configure_property(
                                    self.name, p,
                                    init=init,
                                    setparent=True)
            p._mapped_by_synonym = self.key

        self.parent = parent


class ComparableProperty(DescriptorProperty):
    """Instruments a Python property for use in query expressions."""

    def __init__(self, comparator_factory, descriptor=None, doc=None):
        self.descriptor = descriptor
        self.comparator_factory = comparator_factory
        self.doc = doc or (descriptor and descriptor.__doc__) or None
        util.set_creation_order(self)

    def _comparator_factory(self, mapper):
        return self.comparator_factory(self, mapper)
