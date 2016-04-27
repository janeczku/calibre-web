# orm/interfaces.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""

Contains various base classes used throughout the ORM.

Defines the now deprecated ORM extension classes as well
as ORM internals.

Other than the deprecated extensions, this module and the
classes within should be considered mostly private.

"""
from __future__ import absolute_import

from .. import exc as sa_exc, util, inspect
from ..sql import operators
from collections import deque

orm_util = util.importlater('sqlalchemy.orm', 'util')
collections = util.importlater('sqlalchemy.orm', 'collections')

__all__ = (
    'AttributeExtension',
    'EXT_CONTINUE',
    'EXT_STOP',
    'ExtensionOption',
    'InstrumentationManager',
    'LoaderStrategy',
    'MapperExtension',
    'MapperOption',
    'MapperProperty',
    'PropComparator',
    'PropertyOption',
    'SessionExtension',
    'StrategizedOption',
    'StrategizedProperty',
    )

EXT_CONTINUE = util.symbol('EXT_CONTINUE')
EXT_STOP = util.symbol('EXT_STOP')

ONETOMANY = util.symbol('ONETOMANY')
MANYTOONE = util.symbol('MANYTOONE')
MANYTOMANY = util.symbol('MANYTOMANY')

from .deprecated_interfaces import AttributeExtension, \
    SessionExtension, \
    MapperExtension


NOT_EXTENSION = util.symbol('NOT_EXTENSION')
"""Symbol indicating an :class:`_InspectionAttr` that's
   not part of sqlalchemy.ext.

   Is assigned to the :attr:`._InspectionAttr.extension_type`
   attibute.

"""

class _InspectionAttr(object):
    """A base class applied to all ORM objects that can be returned
    by the :func:`.inspect` function.

    The attributes defined here allow the usage of simple boolean
    checks to test basic facts about the object returned.

    While the boolean checks here are basically the same as using
    the Python isinstance() function, the flags here can be used without
    the need to import all of these classes, and also such that
    the SQLAlchemy class system can change while leaving the flags
    here intact for forwards-compatibility.

    """

    is_selectable = False
    """Return True if this object is an instance of :class:`.Selectable`."""

    is_aliased_class = False
    """True if this object is an instance of :class:`.AliasedClass`."""

    is_instance = False
    """True if this object is an instance of :class:`.InstanceState`."""

    is_mapper = False
    """True if this object is an instance of :class:`.Mapper`."""

    is_property = False
    """True if this object is an instance of :class:`.MapperProperty`."""

    is_attribute = False
    """True if this object is a Python :term:`descriptor`.

    This can refer to one of many types.   Usually a
    :class:`.QueryableAttribute` which handles attributes events on behalf
    of a :class:`.MapperProperty`.   But can also be an extension type
    such as :class:`.AssociationProxy` or :class:`.hybrid_property`.
    The :attr:`._InspectionAttr.extension_type` will refer to a constant
    identifying the specific subtype.

    .. seealso::

        :attr:`.Mapper.all_orm_descriptors`

    """

    is_clause_element = False
    """True if this object is an instance of :class:`.ClauseElement`."""

    extension_type = NOT_EXTENSION
    """The extension type, if any.
    Defaults to :data:`.interfaces.NOT_EXTENSION`

    .. versionadded:: 0.8.0

    .. seealso::

        :data:`.HYBRID_METHOD`

        :data:`.HYBRID_PROPERTY`

        :data:`.ASSOCIATION_PROXY`

    """

class _MappedAttribute(object):
    """Mixin for attributes which should be replaced by mapper-assigned
    attributes.

    """


class MapperProperty(_MappedAttribute, _InspectionAttr):
    """Manage the relationship of a ``Mapper`` to a single class
    attribute, as well as that attribute as it appears on individual
    instances of the class, including attribute instrumentation,
    attribute access, loading behavior, and dependency calculations.

    The most common occurrences of :class:`.MapperProperty` are the
    mapped :class:`.Column`, which is represented in a mapping as
    an instance of :class:`.ColumnProperty`,
    and a reference to another class produced by :func:`.relationship`,
    represented in the mapping as an instance of
    :class:`.RelationshipProperty`.

    """

    cascade = frozenset()
    """The set of 'cascade' attribute names.

    This collection is checked before the 'cascade_iterator' method is called.

    """

    is_property = True

    def setup(self, context, entity, path, adapter, **kwargs):
        """Called by Query for the purposes of constructing a SQL statement.

        Each MapperProperty associated with the target mapper processes the
        statement referenced by the query context, adding columns and/or
        criterion as appropriate.
        """

        pass

    def create_row_processor(self, context, path,
                                            mapper, row, adapter):
        """Return a 3-tuple consisting of three row processing functions.

        """
        return None, None, None

    def cascade_iterator(self, type_, state, visited_instances=None,
                            halt_on=None):
        """Iterate through instances related to the given instance for
        a particular 'cascade', starting with this MapperProperty.

        Return an iterator3-tuples (instance, mapper, state).

        Note that the 'cascade' collection on this MapperProperty is
        checked first for the given type before cascade_iterator is called.

        See PropertyLoader for the related instance implementation.
        """

        return iter(())

    def set_parent(self, parent, init):
        self.parent = parent

    def instrument_class(self, mapper):  # pragma: no-coverage
        raise NotImplementedError()

    @util.memoized_property
    def info(self):
        """Info dictionary associated with the object, allowing user-defined
        data to be associated with this :class:`.MapperProperty`.

        The dictionary is generated when first accessed.  Alternatively,
        it can be specified as a constructor argument to the
        :func:`.column_property`, :func:`.relationship`, or :func:`.composite`
        functions.

        .. versionadded:: 0.8  Added support for .info to all
           :class:`.MapperProperty` subclasses.

        .. seealso::

            :attr:`.QueryableAttribute.info`

            :attr:`.SchemaItem.info`

        """
        return {}

    _configure_started = False
    _configure_finished = False

    def init(self):
        """Called after all mappers are created to assemble
        relationships between mappers and perform other post-mapper-creation
        initialization steps.

        """
        self._configure_started = True
        self.do_init()
        self._configure_finished = True

    @property
    def class_attribute(self):
        """Return the class-bound descriptor corresponding to this
        :class:`.MapperProperty`.

        This is basically a ``getattr()`` call::

            return getattr(self.parent.class_, self.key)

        I.e. if this :class:`.MapperProperty` were named ``addresses``,
        and the class to which it is mapped is ``User``, this sequence
        is possible::

            >>> from sqlalchemy import inspect
            >>> mapper = inspect(User)
            >>> addresses_property = mapper.attrs.addresses
            >>> addresses_property.class_attribute is User.addresses
            True
            >>> User.addresses.property is addresses_property
            True


        """

        return getattr(self.parent.class_, self.key)

    def do_init(self):
        """Perform subclass-specific initialization post-mapper-creation
        steps.

        This is a template method called by the ``MapperProperty``
        object's init() method.

        """

        pass

    def post_instrument_class(self, mapper):
        """Perform instrumentation adjustments that need to occur
        after init() has completed.

        """
        pass

    def is_primary(self):
        """Return True if this ``MapperProperty``'s mapper is the
        primary mapper for its class.

        This flag is used to indicate that the ``MapperProperty`` can
        define attribute instrumentation for the class at the class
        level (as opposed to the individual instance level).
        """

        return not self.parent.non_primary

    def merge(self, session, source_state, source_dict, dest_state,
                dest_dict, load, _recursive):
        """Merge the attribute represented by this ``MapperProperty``
        from source to destination object"""

        pass

    def compare(self, operator, value, **kw):
        """Return a compare operation for the columns represented by
        this ``MapperProperty`` to the given value, which may be a
        column value or an instance.  'operator' is an operator from
        the operators module, or from sql.Comparator.

        By default uses the PropComparator attached to this MapperProperty
        under the attribute name "comparator".
        """

        return operator(self.comparator, value)

    def __repr__(self):
        return '<%s at 0x%x; %s>' % (
            self.__class__.__name__,
            id(self), getattr(self, 'key', 'no key'))

class PropComparator(operators.ColumnOperators):
    """Defines boolean, comparison, and other operators for
    :class:`.MapperProperty` objects.

    SQLAlchemy allows for operators to
    be redefined at both the Core and ORM level.  :class:`.PropComparator`
    is the base class of operator redefinition for ORM-level operations,
    including those of :class:`.ColumnProperty`,
    :class:`.RelationshipProperty`, and :class:`.CompositeProperty`.

    .. note:: With the advent of Hybrid properties introduced in SQLAlchemy
       0.7, as well as Core-level operator redefinition in
       SQLAlchemy 0.8, the use case for user-defined :class:`.PropComparator`
       instances is extremely rare.  See :ref:`hybrids_toplevel` as well
       as :ref:`types_operators`.

    User-defined subclasses of :class:`.PropComparator` may be created. The
    built-in Python comparison and math operator methods, such as
    :meth:`.operators.ColumnOperators.__eq__`,
    :meth:`.operators.ColumnOperators.__lt__`, and
    :meth:`.operators.ColumnOperators.__add__`, can be overridden to provide
    new operator behavior. The custom :class:`.PropComparator` is passed to
    the :class:`.MapperProperty` instance via the ``comparator_factory``
    argument. In each case,
    the appropriate subclass of :class:`.PropComparator` should be used::

        # definition of custom PropComparator subclasses

        from sqlalchemy.orm.properties import \\
                                ColumnProperty,\\
                                CompositeProperty,\\
                                RelationshipProperty

        class MyColumnComparator(ColumnProperty.Comparator):
            def __eq__(self, other):
                return self.__clause_element__() == other

        class MyRelationshipComparator(RelationshipProperty.Comparator):
            def any(self, expression):
                "define the 'any' operation"
                # ...

        class MyCompositeComparator(CompositeProperty.Comparator):
            def __gt__(self, other):
                "redefine the 'greater than' operation"

                return sql.and_(*[a>b for a, b in
                                  zip(self.__clause_element__().clauses,
                                      other.__composite_values__())])


        # application of custom PropComparator subclasses

        from sqlalchemy.orm import column_property, relationship, composite
        from sqlalchemy import Column, String

        class SomeMappedClass(Base):
            some_column = column_property(Column("some_column", String),
                                comparator_factory=MyColumnComparator)

            some_relationship = relationship(SomeOtherClass,
                                comparator_factory=MyRelationshipComparator)

            some_composite = composite(
                    Column("a", String), Column("b", String),
                    comparator_factory=MyCompositeComparator
                )

    Note that for column-level operator redefinition, it's usually
    simpler to define the operators at the Core level, using the
    :attr:`.TypeEngine.comparator_factory` attribute.  See
    :ref:`types_operators` for more detail.

    See also:

    :class:`.ColumnProperty.Comparator`

    :class:`.RelationshipProperty.Comparator`

    :class:`.CompositeProperty.Comparator`

    :class:`.ColumnOperators`

    :ref:`types_operators`

    :attr:`.TypeEngine.comparator_factory`

    """

    def __init__(self, prop, parentmapper, adapter=None):
        self.prop = self.property = prop
        self._parentmapper = parentmapper
        self.adapter = adapter

    def __clause_element__(self):
        raise NotImplementedError("%r" % self)

    def adapted(self, adapter):
        """Return a copy of this PropComparator which will use the given
        adaption function on the local side of generated expressions.

        """

        return self.__class__(self.prop, self._parentmapper, adapter)

    @util.memoized_property
    def info(self):
        return self.property.info

    @staticmethod
    def any_op(a, b, **kwargs):
        return a.any(b, **kwargs)

    @staticmethod
    def has_op(a, b, **kwargs):
        return a.has(b, **kwargs)

    @staticmethod
    def of_type_op(a, class_):
        return a.of_type(class_)

    def of_type(self, class_):
        """Redefine this object in terms of a polymorphic subclass.

        Returns a new PropComparator from which further criterion can be
        evaluated.

        e.g.::

            query.join(Company.employees.of_type(Engineer)).\\
               filter(Engineer.name=='foo')

        :param \class_: a class or mapper indicating that criterion will be
            against this specific subclass.


        """

        return self.operate(PropComparator.of_type_op, class_)

    def any(self, criterion=None, **kwargs):
        """Return true if this collection contains any member that meets the
        given criterion.

        The usual implementation of ``any()`` is
        :meth:`.RelationshipProperty.Comparator.any`.

        :param criterion: an optional ClauseElement formulated against the
          member class' table or attributes.

        :param \**kwargs: key/value pairs corresponding to member class
          attribute names which will be compared via equality to the
          corresponding values.

        """

        return self.operate(PropComparator.any_op, criterion, **kwargs)

    def has(self, criterion=None, **kwargs):
        """Return true if this element references a member which meets the
        given criterion.

        The usual implementation of ``has()`` is
        :meth:`.RelationshipProperty.Comparator.has`.

        :param criterion: an optional ClauseElement formulated against the
          member class' table or attributes.

        :param \**kwargs: key/value pairs corresponding to member class
          attribute names which will be compared via equality to the
          corresponding values.

        """

        return self.operate(PropComparator.has_op, criterion, **kwargs)


class StrategizedProperty(MapperProperty):
    """A MapperProperty which uses selectable strategies to affect
    loading behavior.

    There is a single strategy selected by default.  Alternate
    strategies can be selected at Query time through the usage of
    ``StrategizedOption`` objects via the Query.options() method.

    """

    strategy_wildcard_key = None

    @util.memoized_property
    def _wildcard_path(self):
        if self.strategy_wildcard_key:
            return ('loaderstrategy', (self.strategy_wildcard_key,))
        else:
            return None

    def _get_context_strategy(self, context, path):
        strategy_cls = path._inlined_get_for(self, context, 'loaderstrategy')

        if not strategy_cls:
            wc_key = self._wildcard_path
            if wc_key and wc_key in context.attributes:
                strategy_cls = context.attributes[wc_key]

        if strategy_cls:
            try:
                return self._strategies[strategy_cls]
            except KeyError:
                return self.__init_strategy(strategy_cls)
        return self.strategy

    def _get_strategy(self, cls):
        try:
            return self._strategies[cls]
        except KeyError:
            return self.__init_strategy(cls)

    def __init_strategy(self, cls):
        self._strategies[cls] = strategy = cls(self)
        return strategy

    def setup(self, context, entity, path, adapter, **kwargs):
        self._get_context_strategy(context, path).\
                    setup_query(context, entity, path,
                                    adapter, **kwargs)

    def create_row_processor(self, context, path, mapper, row, adapter):
        return self._get_context_strategy(context, path).\
                    create_row_processor(context, path,
                                    mapper, row, adapter)

    def do_init(self):
        self._strategies = {}
        self.strategy = self.__init_strategy(self.strategy_class)

    def post_instrument_class(self, mapper):
        if self.is_primary() and \
            not mapper.class_manager._attr_has_impl(self.key):
            self.strategy.init_class_attribute(mapper)


class MapperOption(object):
    """Describe a modification to a Query."""

    propagate_to_loaders = False
    """if True, indicate this option should be carried along
    Query object generated by scalar or object lazy loaders.
    """

    def process_query(self, query):
        pass

    def process_query_conditionally(self, query):
        """same as process_query(), except that this option may not
        apply to the given query.

        Used when secondary loaders resend existing options to a new
        Query."""

        self.process_query(query)


class PropertyOption(MapperOption):
    """A MapperOption that is applied to a property off the mapper or
    one of its child mappers, identified by a dot-separated key
    or list of class-bound attributes. """

    def __init__(self, key, mapper=None):
        self.key = key
        self.mapper = mapper

    def process_query(self, query):
        self._process(query, True)

    def process_query_conditionally(self, query):
        self._process(query, False)

    def _process(self, query, raiseerr):
        paths = self._process_paths(query, raiseerr)
        if paths:
            self.process_query_property(query, paths)

    def process_query_property(self, query, paths):
        pass

    def __getstate__(self):
        d = self.__dict__.copy()
        d['key'] = ret = []
        for token in util.to_list(self.key):
            if isinstance(token, PropComparator):
                ret.append((token._parentmapper.class_, token.key))
            else:
                ret.append(token)
        return d

    def __setstate__(self, state):
        ret = []
        for key in state['key']:
            if isinstance(key, tuple):
                cls, propkey = key
                ret.append(getattr(cls, propkey))
            else:
                ret.append(key)
        state['key'] = tuple(ret)
        self.__dict__ = state

    def _find_entity_prop_comparator(self, query, token, mapper, raiseerr):
        if orm_util._is_aliased_class(mapper):
            searchfor = mapper
        else:
            searchfor = orm_util._class_to_mapper(mapper)
        for ent in query._mapper_entities:
            if ent.corresponds_to(searchfor):
                return ent
        else:
            if raiseerr:
                if not list(query._mapper_entities):
                    raise sa_exc.ArgumentError(
                        "Query has only expression-based entities - "
                        "can't find property named '%s'."
                         % (token, )
                    )
                else:
                    raise sa_exc.ArgumentError(
                        "Can't find property '%s' on any entity "
                        "specified in this Query.  Note the full path "
                        "from root (%s) to target entity must be specified."
                        % (token, ",".join(str(x) for
                            x in query._mapper_entities))
                    )
            else:
                return None

    def _find_entity_basestring(self, query, token, raiseerr):
        for ent in query._mapper_entities:
            # return only the first _MapperEntity when searching
            # based on string prop name.   Ideally object
            # attributes are used to specify more exactly.
            return ent
        else:
            if raiseerr:
                raise sa_exc.ArgumentError(
                    "Query has only expression-based entities - "
                    "can't find property named '%s'."
                     % (token, )
                )
            else:
                return None

    def _process_paths(self, query, raiseerr):
        """reconcile the 'key' for this PropertyOption with
        the current path and entities of the query.

        Return a list of affected paths.

        """
        path = orm_util.PathRegistry.root
        entity = None
        paths = []
        no_result = []

        # _current_path implies we're in a
        # secondary load with an existing path
        current_path = list(query._current_path.path)

        tokens = deque(self.key)
        while tokens:
            token = tokens.popleft()
            if isinstance(token, basestring):
                # wildcard token
                if token.endswith(':*'):
                    return [path.token(token)]
                sub_tokens = token.split(".", 1)
                token = sub_tokens[0]
                tokens.extendleft(sub_tokens[1:])

                # exhaust current_path before
                # matching tokens to entities
                if current_path:
                    if current_path[1].key == token:
                        current_path = current_path[2:]
                        continue
                    else:
                        return no_result

                if not entity:
                    entity = self._find_entity_basestring(
                                        query,
                                        token,
                                        raiseerr)
                    if entity is None:
                        return no_result
                    path_element = entity.entity_zero
                    mapper = entity.mapper

                if hasattr(mapper.class_, token):
                    prop = getattr(mapper.class_, token).property
                else:
                    if raiseerr:
                        raise sa_exc.ArgumentError(
                            "Can't find property named '%s' on the "
                            "mapped entity %s in this Query. " % (
                                token, mapper)
                        )
                    else:
                        return no_result
            elif isinstance(token, PropComparator):
                prop = token.property

                # exhaust current_path before
                # matching tokens to entities
                if current_path:
                    if current_path[0:2] == \
                            [token._parententity, prop]:
                        current_path = current_path[2:]
                        continue
                    else:
                        return no_result

                if not entity:
                    entity = self._find_entity_prop_comparator(
                                            query,
                                            prop.key,
                                            token._parententity,
                                            raiseerr)
                    if not entity:
                        return no_result

                    path_element = entity.entity_zero
                    mapper = entity.mapper
            else:
                raise sa_exc.ArgumentError(
                        "mapper option expects "
                        "string key or list of attributes")
            assert prop is not None
            if raiseerr and not prop.parent.common_parent(mapper):
                raise sa_exc.ArgumentError("Attribute '%s' does not "
                            "link from element '%s'" % (token, path_element))

            path = path[path_element][prop]

            paths.append(path)

            if getattr(token, '_of_type', None):
                ac = token._of_type
                ext_info = inspect(ac)
                path_element = mapper = ext_info.mapper
                if not ext_info.is_aliased_class:
                    ac = orm_util.with_polymorphic(
                                ext_info.mapper.base_mapper,
                                ext_info.mapper, aliased=True,
                                _use_mapper_path=True)
                    ext_info = inspect(ac)
                path.set(query, "path_with_polymorphic", ext_info)
            else:
                path_element = mapper = getattr(prop, 'mapper', None)
                if mapper is None and tokens:
                    raise sa_exc.ArgumentError(
                        "Attribute '%s' of entity '%s' does not "
                        "refer to a mapped entity" %
                        (token, entity)
                    )

        if current_path:
            # ran out of tokens before
            # current_path was exhausted.
            assert not tokens
            return no_result

        return paths


class StrategizedOption(PropertyOption):
    """A MapperOption that affects which LoaderStrategy will be used
    for an operation by a StrategizedProperty.
    """

    chained = False

    def process_query_property(self, query, paths):
        strategy = self.get_strategy_class()
        if self.chained:
            for path in paths:
                path.set(
                    query,
                    "loaderstrategy",
                    strategy
                )
        else:
            paths[-1].set(
                query,
                "loaderstrategy",
                strategy
            )

    def get_strategy_class(self):
        raise NotImplementedError()


class LoaderStrategy(object):
    """Describe the loading behavior of a StrategizedProperty object.

    The ``LoaderStrategy`` interacts with the querying process in three
    ways:

    * it controls the configuration of the ``InstrumentedAttribute``
      placed on a class to handle the behavior of the attribute.  this
      may involve setting up class-level callable functions to fire
      off a select operation when the attribute is first accessed
      (i.e. a lazy load)

    * it processes the ``QueryContext`` at statement construction time,
      where it can modify the SQL statement that is being produced.
      Simple column attributes may add their represented column to the
      list of selected columns, *eager loading* properties may add
      ``LEFT OUTER JOIN`` clauses to the statement.

    * It produces "row processor" functions at result fetching time.
      These "row processor" functions populate a particular attribute
      on a particular mapped instance.

    """
    def __init__(self, parent):
        self.parent_property = parent
        self.is_class_level = False
        self.parent = self.parent_property.parent
        self.key = self.parent_property.key

    def init_class_attribute(self, mapper):
        pass

    def setup_query(self, context, entity, path, adapter, **kwargs):
        pass

    def create_row_processor(self, context, path, mapper,
                                row, adapter):
        """Return row processing functions which fulfill the contract
        specified by MapperProperty.create_row_processor.

        StrategizedProperty delegates its create_row_processor method
        directly to this method. """

        return None, None, None

    def __str__(self):
        return str(self.parent_property)
