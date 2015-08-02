# orm/properties.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""MapperProperty implementations.

This is a private module which defines the behavior of invidual ORM-
mapped attributes.

"""

from .. import sql, util, log, exc as sa_exc, inspect
from ..sql import operators, expression
from . import (
    attributes, mapper,
    strategies, configure_mappers, relationships,
    dependency
    )
from .util import CascadeOptions, \
        _orm_annotate, _orm_deannotate, _orm_full_deannotate

from .interfaces import MANYTOMANY, MANYTOONE, ONETOMANY,\
        PropComparator, StrategizedProperty

mapperlib = util.importlater("sqlalchemy.orm", "mapperlib")
NoneType = type(None)

from descriptor_props import CompositeProperty, SynonymProperty, \
            ComparableProperty, ConcreteInheritedProperty

__all__ = ['ColumnProperty', 'CompositeProperty', 'SynonymProperty',
           'ComparableProperty', 'RelationshipProperty', 'RelationProperty']


class ColumnProperty(StrategizedProperty):
    """Describes an object attribute that corresponds to a table column.

    Public constructor is the :func:`.orm.column_property` function.

    """

    def __init__(self, *columns, **kwargs):
        """Construct a ColumnProperty.

        Note the public constructor is the :func:`.orm.column_property`
        function.

        :param \*columns: The list of `columns` describes a single
          object property. If there are multiple tables joined
          together for the mapper, this list represents the equivalent
          column as it appears across each table.

        :param group:

        :param deferred:

        :param comparator_factory:

        :param descriptor:

        :param expire_on_flush:

        :param extension:

        :param info: Optional data dictionary which will be populated into the
         :attr:`.info` attribute of this object.

        """
        self._orig_columns = [expression._labeled(c) for c in columns]
        self.columns = [expression._labeled(_orm_full_deannotate(c))
                            for c in columns]
        self.group = kwargs.pop('group', None)
        self.deferred = kwargs.pop('deferred', False)
        self.instrument = kwargs.pop('_instrument', True)
        self.comparator_factory = kwargs.pop('comparator_factory',
                                            self.__class__.Comparator)
        self.descriptor = kwargs.pop('descriptor', None)
        self.extension = kwargs.pop('extension', None)
        self.active_history = kwargs.pop('active_history', False)
        self.expire_on_flush = kwargs.pop('expire_on_flush', True)

        if 'info' in kwargs:
            self.info = kwargs.pop('info')

        if 'doc' in kwargs:
            self.doc = kwargs.pop('doc')
        else:
            for col in reversed(self.columns):
                doc = getattr(col, 'doc', None)
                if doc is not None:
                    self.doc = doc
                    break
            else:
                self.doc = None

        if kwargs:
            raise TypeError(
                "%s received unexpected keyword argument(s): %s" % (
                    self.__class__.__name__,
                    ', '.join(sorted(kwargs.keys()))))

        util.set_creation_order(self)
        if not self.instrument:
            self.strategy_class = strategies.UninstrumentedColumnLoader
        elif self.deferred:
            self.strategy_class = strategies.DeferredColumnLoader
        else:
            self.strategy_class = strategies.ColumnLoader

    @property
    def expression(self):
        """Return the primary column or expression for this ColumnProperty.

        """
        return self.columns[0]

    def instrument_class(self, mapper):
        if not self.instrument:
            return

        attributes.register_descriptor(
            mapper.class_,
            self.key,
            comparator=self.comparator_factory(self, mapper),
            parententity=mapper,
            doc=self.doc
            )

    def do_init(self):
        super(ColumnProperty, self).do_init()
        if len(self.columns) > 1 and \
                set(self.parent.primary_key).issuperset(self.columns):
            util.warn(
                ("On mapper %s, primary key column '%s' is being combined "
                 "with distinct primary key column '%s' in attribute '%s'.  "
                 "Use explicit properties to give each column its own mapped "
                 "attribute name.") % (self.parent, self.columns[1],
                                       self.columns[0], self.key))

    def copy(self):
        return ColumnProperty(
                        deferred=self.deferred,
                        group=self.group,
                        active_history=self.active_history,
                        *self.columns)

    def _getcommitted(self, state, dict_, column,
                    passive=attributes.PASSIVE_OFF):
        return state.get_impl(self.key).\
                    get_committed_value(state, dict_, passive=passive)

    def merge(self, session, source_state, source_dict, dest_state,
                                dest_dict, load, _recursive):
        if not self.instrument:
            return
        elif self.key in source_dict:
            value = source_dict[self.key]

            if not load:
                dest_dict[self.key] = value
            else:
                impl = dest_state.get_impl(self.key)
                impl.set(dest_state, dest_dict, value, None)
        elif dest_state.has_identity and self.key not in dest_dict:
            dest_state._expire_attributes(dest_dict, [self.key])

    class Comparator(PropComparator):
        """Produce boolean, comparison, and other operators for
        :class:`.ColumnProperty` attributes.

        See the documentation for :class:`.PropComparator` for a brief
        overview.

        See also:

        :class:`.PropComparator`

        :class:`.ColumnOperators`

        :ref:`types_operators`

        :attr:`.TypeEngine.comparator_factory`

        """
        @util.memoized_instancemethod
        def __clause_element__(self):
            if self.adapter:
                return self.adapter(self.prop.columns[0])
            else:
                return self.prop.columns[0]._annotate({
                    "parententity": self._parentmapper,
                    "parentmapper": self._parentmapper})

        @util.memoized_property
        def info(self):
            ce = self.__clause_element__()
            try:
                return ce.info
            except AttributeError:
                return self.prop.info

        def __getattr__(self, key):
            """proxy attribute access down to the mapped column.

            this allows user-defined comparison methods to be accessed.
            """
            return getattr(self.__clause_element__(), key)

        def operate(self, op, *other, **kwargs):
            return op(self.__clause_element__(), *other, **kwargs)

        def reverse_operate(self, op, other, **kwargs):
            col = self.__clause_element__()
            return op(col._bind_param(op, other), col, **kwargs)

    # TODO: legacy..do we need this ? (0.5)
    ColumnComparator = Comparator

    def __str__(self):
        return str(self.parent.class_.__name__) + "." + self.key

log.class_logger(ColumnProperty)


class RelationshipProperty(StrategizedProperty):
    """Describes an object property that holds a single item or list
    of items that correspond to a related database table.

    Public constructor is the :func:`.orm.relationship` function.

    See also:

    :ref:`relationship_config_toplevel`

    """

    strategy_wildcard_key = 'relationship:*'

    _dependency_processor = None

    def __init__(self, argument,
        secondary=None, primaryjoin=None,
        secondaryjoin=None,
        foreign_keys=None,
        uselist=None,
        order_by=False,
        backref=None,
        back_populates=None,
        post_update=False,
        cascade=False, extension=None,
        viewonly=False, lazy=True,
        collection_class=None, passive_deletes=False,
        passive_updates=True, remote_side=None,
        enable_typechecks=True, join_depth=None,
        comparator_factory=None,
        single_parent=False, innerjoin=False,
        distinct_target_key=False,
        doc=None,
        active_history=False,
        cascade_backrefs=True,
        load_on_pending=False,
        strategy_class=None, _local_remote_pairs=None,
        query_class=None,
            info=None):

        self.uselist = uselist
        self.argument = argument
        self.secondary = secondary
        self.primaryjoin = primaryjoin
        self.secondaryjoin = secondaryjoin
        self.post_update = post_update
        self.direction = None
        self.viewonly = viewonly
        self.lazy = lazy
        self.single_parent = single_parent
        self._user_defined_foreign_keys = foreign_keys
        self.collection_class = collection_class
        self.passive_deletes = passive_deletes
        self.cascade_backrefs = cascade_backrefs
        self.passive_updates = passive_updates
        self.remote_side = remote_side
        self.enable_typechecks = enable_typechecks
        self.query_class = query_class
        self.innerjoin = innerjoin
        self.distinct_target_key = distinct_target_key
        self.doc = doc
        self.active_history = active_history
        self.join_depth = join_depth
        self.local_remote_pairs = _local_remote_pairs
        self.extension = extension
        self.load_on_pending = load_on_pending
        self.comparator_factory = comparator_factory or \
                                    RelationshipProperty.Comparator
        self.comparator = self.comparator_factory(self, None)
        util.set_creation_order(self)

        if info is not None:
            self.info = info

        if strategy_class:
            self.strategy_class = strategy_class
        elif self.lazy == 'dynamic':
            from sqlalchemy.orm import dynamic
            self.strategy_class = dynamic.DynaLoader
        else:
            self.strategy_class = strategies.factory(self.lazy)

        self._reverse_property = set()

        self.cascade = cascade if cascade is not False \
                            else "save-update, merge"

        self.order_by = order_by

        self.back_populates = back_populates

        if self.back_populates:
            if backref:
                raise sa_exc.ArgumentError(
                            "backref and back_populates keyword arguments "
                            "are mutually exclusive")
            self.backref = None
        else:
            self.backref = backref

    def instrument_class(self, mapper):
        attributes.register_descriptor(
            mapper.class_,
            self.key,
            comparator=self.comparator_factory(self, mapper),
            parententity=mapper,
            doc=self.doc,
            )

    class Comparator(PropComparator):
        """Produce boolean, comparison, and other operators for
        :class:`.RelationshipProperty` attributes.

        See the documentation for :class:`.PropComparator` for a brief overview
        of ORM level operator definition.

        See also:

        :class:`.PropComparator`

        :class:`.ColumnProperty.Comparator`

        :class:`.ColumnOperators`

        :ref:`types_operators`

        :attr:`.TypeEngine.comparator_factory`

        """

        _of_type = None

        def __init__(self, prop, parentmapper, of_type=None, adapter=None):
            """Construction of :class:`.RelationshipProperty.Comparator`
            is internal to the ORM's attribute mechanics.

            """
            self.prop = prop
            self._parentmapper = parentmapper
            self.adapter = adapter
            if of_type:
                self._of_type = of_type

        def adapted(self, adapter):
            """Return a copy of this PropComparator which will use the
            given adaption function on the local side of generated
            expressions.

            """

            return self.__class__(self.property, self._parentmapper,
                                  getattr(self, '_of_type', None),
                                  adapter)

        @util.memoized_property
        def mapper(self):
            """The target :class:`.Mapper` referred to by this
            :class:`.RelationshipProperty.Comparator.

            This is the "target" or "remote" side of the
            :func:`.relationship`.

            """
            return self.property.mapper

        @util.memoized_property
        def _parententity(self):
            return self.property.parent

        def _source_selectable(self):
            elem = self.property.parent._with_polymorphic_selectable
            if self.adapter:
                return self.adapter(elem)
            else:
                return elem

        def __clause_element__(self):
            adapt_from = self._source_selectable()
            if self._of_type:
                of_type = inspect(self._of_type).mapper
            else:
                of_type = None

            pj, sj, source, dest, \
            secondary, target_adapter = self.property._create_joins(
                            source_selectable=adapt_from,
                            source_polymorphic=True,
                            of_type=of_type)
            if sj is not None:
                return pj & sj
            else:
                return pj

        def of_type(self, cls):
            """Produce a construct that represents a particular 'subtype' of
            attribute for the parent class.

            Currently this is usable in conjunction with :meth:`.Query.join`
            and :meth:`.Query.outerjoin`.

            """
            return RelationshipProperty.Comparator(
                                        self.property,
                                        self._parentmapper,
                                        cls, adapter=self.adapter)

        def in_(self, other):
            """Produce an IN clause - this is not implemented
            for :func:`~.orm.relationship`-based attributes at this time.

            """
            raise NotImplementedError('in_() not yet supported for '
                    'relationships.  For a simple many-to-one, use '
                    'in_() against the set of foreign key values.')

        __hash__ = None

        def __eq__(self, other):
            """Implement the ``==`` operator.

            In a many-to-one context, such as::

              MyClass.some_prop == <some object>

            this will typically produce a
            clause such as::

              mytable.related_id == <some id>

            Where ``<some id>`` is the primary key of the given
            object.

            The ``==`` operator provides partial functionality for non-
            many-to-one comparisons:

            * Comparisons against collections are not supported.
              Use :meth:`~.RelationshipProperty.Comparator.contains`.
            * Compared to a scalar one-to-many, will produce a
              clause that compares the target columns in the parent to
              the given target.
            * Compared to a scalar many-to-many, an alias
              of the association table will be rendered as
              well, forming a natural join that is part of the
              main body of the query. This will not work for
              queries that go beyond simple AND conjunctions of
              comparisons, such as those which use OR. Use
              explicit joins, outerjoins, or
              :meth:`~.RelationshipProperty.Comparator.has` for
              more comprehensive non-many-to-one scalar
              membership tests.
            * Comparisons against ``None`` given in a one-to-many
              or many-to-many context produce a NOT EXISTS clause.

            """
            if isinstance(other, (NoneType, expression.Null)):
                if self.property.direction in [ONETOMANY, MANYTOMANY]:
                    return ~self._criterion_exists()
                else:
                    return _orm_annotate(self.property._optimized_compare(
                            None, adapt_source=self.adapter))
            elif self.property.uselist:
                raise sa_exc.InvalidRequestError("Can't compare a colle"
                        "ction to an object or collection; use "
                        "contains() to test for membership.")
            else:
                return _orm_annotate(self.property._optimized_compare(other,
                        adapt_source=self.adapter))

        def _criterion_exists(self, criterion=None, **kwargs):
            if getattr(self, '_of_type', None):
                info = inspect(self._of_type)
                target_mapper, to_selectable, is_aliased_class = \
                    info.mapper, info.selectable, info.is_aliased_class
                if self.property._is_self_referential and not is_aliased_class:
                    to_selectable = to_selectable.alias()

                single_crit = target_mapper._single_table_criterion
                if single_crit is not None:
                    if criterion is not None:
                        criterion = single_crit & criterion
                    else:
                        criterion = single_crit
            else:
                is_aliased_class = False
                to_selectable = None

            if self.adapter:
                source_selectable = self._source_selectable()
            else:
                source_selectable = None

            pj, sj, source, dest, secondary, target_adapter = \
                self.property._create_joins(dest_polymorphic=True,
                        dest_selectable=to_selectable,
                        source_selectable=source_selectable)

            for k in kwargs:
                crit = getattr(self.property.mapper.class_, k) == kwargs[k]
                if criterion is None:
                    criterion = crit
                else:
                    criterion = criterion & crit

            # annotate the *local* side of the join condition, in the case
            # of pj + sj this is the full primaryjoin, in the case of just
            # pj its the local side of the primaryjoin.
            if sj is not None:
                j = _orm_annotate(pj) & sj
            else:
                j = _orm_annotate(pj, exclude=self.property.remote_side)

            if criterion is not None and target_adapter and not is_aliased_class:
                # limit this adapter to annotated only?
                criterion = target_adapter.traverse(criterion)

            # only have the "joined left side" of what we
            # return be subject to Query adaption.  The right
            # side of it is used for an exists() subquery and
            # should not correlate or otherwise reach out
            # to anything in the enclosing query.
            if criterion is not None:
                criterion = criterion._annotate(
                    {'no_replacement_traverse': True})

            crit = j & criterion

            ex = sql.exists([1], crit, from_obj=dest).correlate_except(dest)
            if secondary is not None:
                ex = ex.correlate_except(secondary)
            return ex

        def any(self, criterion=None, **kwargs):
            """Produce an expression that tests a collection against
            particular criterion, using EXISTS.

            An expression like::

                session.query(MyClass).filter(
                    MyClass.somereference.any(SomeRelated.x==2)
                )


            Will produce a query like::

                SELECT * FROM my_table WHERE
                EXISTS (SELECT 1 FROM related WHERE related.my_id=my_table.id
                AND related.x=2)

            Because :meth:`~.RelationshipProperty.Comparator.any` uses
            a correlated subquery, its performance is not nearly as
            good when compared against large target tables as that of
            using a join.

            :meth:`~.RelationshipProperty.Comparator.any` is particularly
            useful for testing for empty collections::

                session.query(MyClass).filter(
                    ~MyClass.somereference.any()
                )

            will produce::

                SELECT * FROM my_table WHERE
                NOT EXISTS (SELECT 1 FROM related WHERE
                related.my_id=my_table.id)

            :meth:`~.RelationshipProperty.Comparator.any` is only
            valid for collections, i.e. a :func:`.relationship`
            that has ``uselist=True``.  For scalar references,
            use :meth:`~.RelationshipProperty.Comparator.has`.

            """
            if not self.property.uselist:
                raise sa_exc.InvalidRequestError(
                            "'any()' not implemented for scalar "
                            "attributes. Use has()."
                        )

            return self._criterion_exists(criterion, **kwargs)

        def has(self, criterion=None, **kwargs):
            """Produce an expression that tests a scalar reference against
            particular criterion, using EXISTS.

            An expression like::

                session.query(MyClass).filter(
                    MyClass.somereference.has(SomeRelated.x==2)
                )


            Will produce a query like::

                SELECT * FROM my_table WHERE
                EXISTS (SELECT 1 FROM related WHERE
                related.id==my_table.related_id AND related.x=2)

            Because :meth:`~.RelationshipProperty.Comparator.has` uses
            a correlated subquery, its performance is not nearly as
            good when compared against large target tables as that of
            using a join.

            :meth:`~.RelationshipProperty.Comparator.has` is only
            valid for scalar references, i.e. a :func:`.relationship`
            that has ``uselist=False``.  For collection references,
            use :meth:`~.RelationshipProperty.Comparator.any`.

            """
            if self.property.uselist:
                raise sa_exc.InvalidRequestError(
                            "'has()' not implemented for collections.  "
                            "Use any().")
            return self._criterion_exists(criterion, **kwargs)

        def contains(self, other, **kwargs):
            """Return a simple expression that tests a collection for
            containment of a particular item.

            :meth:`~.RelationshipProperty.Comparator.contains` is
            only valid for a collection, i.e. a
            :func:`~.orm.relationship` that implements
            one-to-many or many-to-many with ``uselist=True``.

            When used in a simple one-to-many context, an
            expression like::

                MyClass.contains(other)

            Produces a clause like::

                mytable.id == <some id>

            Where ``<some id>`` is the value of the foreign key
            attribute on ``other`` which refers to the primary
            key of its parent object. From this it follows that
            :meth:`~.RelationshipProperty.Comparator.contains` is
            very useful when used with simple one-to-many
            operations.

            For many-to-many operations, the behavior of
            :meth:`~.RelationshipProperty.Comparator.contains`
            has more caveats. The association table will be
            rendered in the statement, producing an "implicit"
            join, that is, includes multiple tables in the FROM
            clause which are equated in the WHERE clause::

                query(MyClass).filter(MyClass.contains(other))

            Produces a query like::

                SELECT * FROM my_table, my_association_table AS
                my_association_table_1 WHERE
                my_table.id = my_association_table_1.parent_id
                AND my_association_table_1.child_id = <some id>

            Where ``<some id>`` would be the primary key of
            ``other``. From the above, it is clear that
            :meth:`~.RelationshipProperty.Comparator.contains`
            will **not** work with many-to-many collections when
            used in queries that move beyond simple AND
            conjunctions, such as multiple
            :meth:`~.RelationshipProperty.Comparator.contains`
            expressions joined by OR. In such cases subqueries or
            explicit "outer joins" will need to be used instead.
            See :meth:`~.RelationshipProperty.Comparator.any` for
            a less-performant alternative using EXISTS, or refer
            to :meth:`.Query.outerjoin` as well as :ref:`ormtutorial_joins`
            for more details on constructing outer joins.

            """
            if not self.property.uselist:
                raise sa_exc.InvalidRequestError(
                            "'contains' not implemented for scalar "
                            "attributes.  Use ==")
            clause = self.property._optimized_compare(other,
                    adapt_source=self.adapter)

            if self.property.secondaryjoin is not None:
                clause.negation_clause = \
                    self.__negated_contains_or_equals(other)

            return clause

        def __negated_contains_or_equals(self, other):
            if self.property.direction == MANYTOONE:
                state = attributes.instance_state(other)

                def state_bindparam(x, state, col):
                    o = state.obj()  # strong ref
                    return sql.bindparam(x, unique=True, callable_=lambda: \
                        self.property.mapper._get_committed_attr_by_column(o, col))

                def adapt(col):
                    if self.adapter:
                        return self.adapter(col)
                    else:
                        return col

                if self.property._use_get:
                    return sql.and_(*[
                        sql.or_(
                            adapt(x) != state_bindparam(adapt(x), state, y),
                            adapt(x) == None)
                        for (x, y) in self.property.local_remote_pairs])

            criterion = sql.and_(*[x == y for (x, y) in
                                zip(
                                    self.property.mapper.primary_key,
                                    self.property.\
                                            mapper.\
                                            primary_key_from_instance(other))
                                    ])
            return ~self._criterion_exists(criterion)

        def __ne__(self, other):
            """Implement the ``!=`` operator.

            In a many-to-one context, such as::

              MyClass.some_prop != <some object>

            This will typically produce a clause such as::

              mytable.related_id != <some id>

            Where ``<some id>`` is the primary key of the
            given object.

            The ``!=`` operator provides partial functionality for non-
            many-to-one comparisons:

            * Comparisons against collections are not supported.
              Use
              :meth:`~.RelationshipProperty.Comparator.contains`
              in conjunction with :func:`~.expression.not_`.
            * Compared to a scalar one-to-many, will produce a
              clause that compares the target columns in the parent to
              the given target.
            * Compared to a scalar many-to-many, an alias
              of the association table will be rendered as
              well, forming a natural join that is part of the
              main body of the query. This will not work for
              queries that go beyond simple AND conjunctions of
              comparisons, such as those which use OR. Use
              explicit joins, outerjoins, or
              :meth:`~.RelationshipProperty.Comparator.has` in
              conjunction with :func:`~.expression.not_` for
              more comprehensive non-many-to-one scalar
              membership tests.
            * Comparisons against ``None`` given in a one-to-many
              or many-to-many context produce an EXISTS clause.

            """
            if isinstance(other, (NoneType, expression.Null)):
                if self.property.direction == MANYTOONE:
                    return sql.or_(*[x != None for x in
                                   self.property._calculated_foreign_keys])
                else:
                    return self._criterion_exists()
            elif self.property.uselist:
                raise sa_exc.InvalidRequestError("Can't compare a collection"
                        " to an object or collection; use "
                        "contains() to test for membership.")
            else:
                return self.__negated_contains_or_equals(other)

        @util.memoized_property
        def property(self):
            if mapperlib.module._new_mappers:
                configure_mappers()
            return self.prop

    def compare(self, op, value,
                            value_is_parent=False,
                            alias_secondary=True):
        if op == operators.eq:
            if value is None:
                if self.uselist:
                    return ~sql.exists([1], self.primaryjoin)
                else:
                    return self._optimized_compare(None,
                                    value_is_parent=value_is_parent,
                                    alias_secondary=alias_secondary)
            else:
                return self._optimized_compare(value,
                                value_is_parent=value_is_parent,
                                alias_secondary=alias_secondary)
        else:
            return op(self.comparator, value)

    def _optimized_compare(self, value, value_is_parent=False,
                                    adapt_source=None,
                                    alias_secondary=True):
        if value is not None:
            value = attributes.instance_state(value)
        return self._get_strategy(strategies.LazyLoader).lazy_clause(value,
                reverse_direction=not value_is_parent,
                alias_secondary=alias_secondary,
                adapt_source=adapt_source)

    def __str__(self):
        return str(self.parent.class_.__name__) + "." + self.key

    def merge(self,
                    session,
                    source_state,
                    source_dict,
                    dest_state,
                    dest_dict,
                    load, _recursive):

        if load:
            for r in self._reverse_property:
                if (source_state, r) in _recursive:
                    return

        if not "merge" in self._cascade:
            return

        if self.key not in source_dict:
            return

        if self.uselist:
            instances = source_state.get_impl(self.key).\
                            get(source_state, source_dict)
            if hasattr(instances, '_sa_adapter'):
                # convert collections to adapters to get a true iterator
                instances = instances._sa_adapter

            if load:
                # for a full merge, pre-load the destination collection,
                # so that individual _merge of each item pulls from identity
                # map for those already present.
                # also assumes CollectionAttrbiuteImpl behavior of loading
                # "old" list in any case
                dest_state.get_impl(self.key).get(dest_state, dest_dict)

            dest_list = []
            for current in instances:
                current_state = attributes.instance_state(current)
                current_dict = attributes.instance_dict(current)
                _recursive[(current_state, self)] = True
                obj = session._merge(current_state, current_dict,
                        load=load, _recursive=_recursive)
                if obj is not None:
                    dest_list.append(obj)

            if not load:
                coll = attributes.init_state_collection(dest_state,
                        dest_dict, self.key)
                for c in dest_list:
                    coll.append_without_event(c)
            else:
                dest_state.get_impl(self.key)._set_iterable(dest_state,
                        dest_dict, dest_list)
        else:
            current = source_dict[self.key]
            if current is not None:
                current_state = attributes.instance_state(current)
                current_dict = attributes.instance_dict(current)
                _recursive[(current_state, self)] = True
                obj = session._merge(current_state, current_dict,
                        load=load, _recursive=_recursive)
            else:
                obj = None

            if not load:
                dest_dict[self.key] = obj
            else:
                dest_state.get_impl(self.key).set(dest_state,
                        dest_dict, obj, None)

    def _value_as_iterable(self, state, dict_, key,
                                    passive=attributes.PASSIVE_OFF):
        """Return a list of tuples (state, obj) for the given
        key.

        returns an empty list if the value is None/empty/PASSIVE_NO_RESULT
        """

        impl = state.manager[key].impl
        x = impl.get(state, dict_, passive=passive)
        if x is attributes.PASSIVE_NO_RESULT or x is None:
            return []
        elif hasattr(impl, 'get_collection'):
            return [
                (attributes.instance_state(o), o) for o in
                impl.get_collection(state, dict_, x, passive=passive)
            ]
        else:
            return [(attributes.instance_state(x), x)]

    def cascade_iterator(self, type_, state, dict_,
                         visited_states, halt_on=None):
        #assert type_ in self._cascade

        # only actively lazy load on the 'delete' cascade
        if type_ != 'delete' or self.passive_deletes:
            passive = attributes.PASSIVE_NO_INITIALIZE
        else:
            passive = attributes.PASSIVE_OFF

        if type_ == 'save-update':
            tuples = state.manager[self.key].impl.\
                        get_all_pending(state, dict_)

        else:
            tuples = self._value_as_iterable(state, dict_, self.key,
                            passive=passive)

        skip_pending = type_ == 'refresh-expire' and 'delete-orphan' \
            not in self._cascade

        for instance_state, c in tuples:
            if instance_state in visited_states:
                continue

            if c is None:
                # would like to emit a warning here, but
                # would not be consistent with collection.append(None)
                # current behavior of silently skipping.
                # see [ticket:2229]
                continue

            instance_dict = attributes.instance_dict(c)

            if halt_on and halt_on(instance_state):
                continue

            if skip_pending and not instance_state.key:
                continue

            instance_mapper = instance_state.manager.mapper

            if not instance_mapper.isa(self.mapper.class_manager.mapper):
                raise AssertionError("Attribute '%s' on class '%s' "
                                    "doesn't handle objects "
                                    "of type '%s'" % (
                                        self.key,
                                        self.parent.class_,
                                        c.__class__
                                    ))

            visited_states.add(instance_state)

            yield c, instance_mapper, instance_state, instance_dict

    def _add_reverse_property(self, key):
        other = self.mapper.get_property(key, _configure_mappers=False)
        self._reverse_property.add(other)
        other._reverse_property.add(self)

        if not other.mapper.common_parent(self.parent):
            raise sa_exc.ArgumentError('reverse_property %r on '
                    'relationship %s references relationship %s, which '
                    'does not reference mapper %s' % (key, self, other,
                    self.parent))
        if self.direction in (ONETOMANY, MANYTOONE) and self.direction \
                        == other.direction:
            raise sa_exc.ArgumentError('%s and back-reference %s are '
                    'both of the same direction %r.  Did you mean to '
                    'set remote_side on the many-to-one side ?'
                    % (other, self, self.direction))

    @util.memoized_property
    def mapper(self):
        """Return the targeted :class:`.Mapper` for this
        :class:`.RelationshipProperty`.

        This is a lazy-initializing static attribute.

        """
        if isinstance(self.argument, type):
            mapper_ = mapper.class_mapper(self.argument,
                    configure=False)
        elif isinstance(self.argument, mapper.Mapper):
            mapper_ = self.argument
        elif util.callable(self.argument):

            # accept a callable to suit various deferred-
            # configurational schemes

            mapper_ = mapper.class_mapper(self.argument(),
                    configure=False)
        else:
            raise sa_exc.ArgumentError("relationship '%s' expects "
                    "a class or a mapper argument (received: %s)"
                    % (self.key, type(self.argument)))
        assert isinstance(mapper_, mapper.Mapper), mapper_
        return mapper_

    @util.memoized_property
    @util.deprecated("0.7", "Use .target")
    def table(self):
        """Return the selectable linked to this
        :class:`.RelationshipProperty` object's target
        :class:`.Mapper`."""
        return self.target

    def do_init(self):
        self._check_conflicts()
        self._process_dependent_arguments()
        self._setup_join_conditions()
        self._check_cascade_settings(self._cascade)
        self._post_init()
        self._generate_backref()
        super(RelationshipProperty, self).do_init()

    def _process_dependent_arguments(self):
        """Convert incoming configuration arguments to their
        proper form.

        Callables are resolved, ORM annotations removed.

        """
        # accept callables for other attributes which may require
        # deferred initialization.  This technique is used
        # by declarative "string configs" and some recipes.
        for attr in (
            'order_by', 'primaryjoin', 'secondaryjoin',
            'secondary', '_user_defined_foreign_keys', 'remote_side',
                ):
            attr_value = getattr(self, attr)
            if util.callable(attr_value):
                setattr(self, attr, attr_value())

        # remove "annotations" which are present if mapped class
        # descriptors are used to create the join expression.
        for attr in 'primaryjoin', 'secondaryjoin':
            val = getattr(self, attr)
            if val is not None:
                setattr(self, attr, _orm_deannotate(
                    expression._only_column_elements(val, attr))
                )

        # ensure expressions in self.order_by, foreign_keys,
        # remote_side are all columns, not strings.
        if self.order_by is not False and self.order_by is not None:
            self.order_by = [
                    expression._only_column_elements(x, "order_by")
                    for x in
                    util.to_list(self.order_by)]

        self._user_defined_foreign_keys = \
            util.column_set(
                    expression._only_column_elements(x, "foreign_keys")
                    for x in util.to_column_set(
                        self._user_defined_foreign_keys
                    ))

        self.remote_side = \
            util.column_set(
                    expression._only_column_elements(x, "remote_side")
                    for x in
                    util.to_column_set(self.remote_side))

        self.target = self.mapper.mapped_table


    def _setup_join_conditions(self):
        self._join_condition = jc = relationships.JoinCondition(
                    parent_selectable=self.parent.mapped_table,
                    child_selectable=self.mapper.mapped_table,
                    parent_local_selectable=self.parent.local_table,
                    child_local_selectable=self.mapper.local_table,
                    primaryjoin=self.primaryjoin,
                    secondary=self.secondary,
                    secondaryjoin=self.secondaryjoin,
                    parent_equivalents=self.parent._equivalent_columns,
                    child_equivalents=self.mapper._equivalent_columns,
                    consider_as_foreign_keys=self._user_defined_foreign_keys,
                    local_remote_pairs=self.local_remote_pairs,
                    remote_side=self.remote_side,
                    self_referential=self._is_self_referential,
                    prop=self,
                    support_sync=not self.viewonly,
                    can_be_synced_fn=self._columns_are_mapped
        )
        self.primaryjoin = jc.deannotated_primaryjoin
        self.secondaryjoin = jc.deannotated_secondaryjoin
        self.direction = jc.direction
        self.local_remote_pairs = jc.local_remote_pairs
        self.remote_side = jc.remote_columns
        self.local_columns = jc.local_columns
        self.synchronize_pairs = jc.synchronize_pairs
        self._calculated_foreign_keys = jc.foreign_key_columns
        self.secondary_synchronize_pairs = jc.secondary_synchronize_pairs

    def _check_conflicts(self):
        """Test that this relationship is legal, warn about
        inheritance conflicts."""

        if not self.is_primary() \
            and not mapper.class_mapper(
                                self.parent.class_,
                                configure=False).has_property(self.key):
            raise sa_exc.ArgumentError("Attempting to assign a new "
                    "relationship '%s' to a non-primary mapper on "
                    "class '%s'.  New relationships can only be added "
                    "to the primary mapper, i.e. the very first mapper "
                    "created for class '%s' " % (self.key,
                    self.parent.class_.__name__,
                    self.parent.class_.__name__))

        # check for conflicting relationship() on superclass
        if not self.parent.concrete:
            for inheriting in self.parent.iterate_to_root():
                if inheriting is not self.parent \
                        and inheriting.has_property(self.key):
                    util.warn("Warning: relationship '%s' on mapper "
                              "'%s' supersedes the same relationship "
                              "on inherited mapper '%s'; this can "
                              "cause dependency issues during flush"
                              % (self.key, self.parent, inheriting))

    def _get_cascade(self):
        """Return the current cascade setting for this
        :class:`.RelationshipProperty`.
        """
        return self._cascade

    def _set_cascade(self, cascade):
        cascade = CascadeOptions(cascade)
        if 'mapper' in self.__dict__:
            self._check_cascade_settings(cascade)
        self._cascade = cascade

        if self._dependency_processor:
            self._dependency_processor.cascade = cascade

    cascade = property(_get_cascade, _set_cascade)

    def _check_cascade_settings(self, cascade):
        if cascade.delete_orphan and not self.single_parent \
            and (self.direction is MANYTOMANY or self.direction
                 is MANYTOONE):
            raise sa_exc.ArgumentError(
                    'On %s, delete-orphan cascade is not supported '
                    'on a many-to-many or many-to-one relationship '
                    'when single_parent is not set.   Set '
                    'single_parent=True on the relationship().'
                    % self)
        if self.direction is MANYTOONE and self.passive_deletes:
            util.warn("On %s, 'passive_deletes' is normally configured "
                      "on one-to-many, one-to-one, many-to-many "
                      "relationships only."
                       % self)

        if self.passive_deletes == 'all' and \
                    ("delete" in cascade or
                    "delete-orphan" in cascade):
            raise sa_exc.ArgumentError(
                    "On %s, can't set passive_deletes='all' in conjunction "
                    "with 'delete' or 'delete-orphan' cascade" % self)

        if cascade.delete_orphan:
            self.mapper.primary_mapper()._delete_orphans.append(
                            (self.key, self.parent.class_)
                        )

    def _columns_are_mapped(self, *cols):
        """Return True if all columns in the given collection are
        mapped by the tables referenced by this :class:`.Relationship`.

        """
        for c in cols:
            if self.secondary is not None \
                    and self.secondary.c.contains_column(c):
                continue
            if not self.parent.mapped_table.c.contains_column(c) and \
                    not self.target.c.contains_column(c):
                return False
        return True

    def _generate_backref(self):
        """Interpret the 'backref' instruction to create a
        :func:`.relationship` complementary to this one."""

        if not self.is_primary():
            return
        if self.backref is not None and not self.back_populates:
            if isinstance(self.backref, basestring):
                backref_key, kwargs = self.backref, {}
            else:
                backref_key, kwargs = self.backref
            mapper = self.mapper.primary_mapper()

            check = set(mapper.iterate_to_root()).\
                        union(mapper.self_and_descendants)
            for m in check:
                if m.has_property(backref_key):
                    raise sa_exc.ArgumentError("Error creating backref "
                            "'%s' on relationship '%s': property of that "
                            "name exists on mapper '%s'" % (backref_key,
                            self, m))

            # determine primaryjoin/secondaryjoin for the
            # backref.  Use the one we had, so that
            # a custom join doesn't have to be specified in
            # both directions.
            if self.secondary is not None:
                # for many to many, just switch primaryjoin/
                # secondaryjoin.   use the annotated
                # pj/sj on the _join_condition.
                pj = kwargs.pop('primaryjoin',
                                self._join_condition.secondaryjoin_minus_local)
                sj = kwargs.pop('secondaryjoin',
                                self._join_condition.primaryjoin_minus_local)
            else:
                pj = kwargs.pop('primaryjoin',
                        self._join_condition.primaryjoin_reverse_remote)
                sj = kwargs.pop('secondaryjoin', None)
                if sj:
                    raise sa_exc.InvalidRequestError(
                        "Can't assign 'secondaryjoin' on a backref "
                        "against a non-secondary relationship."
                    )

            foreign_keys = kwargs.pop('foreign_keys',
                    self._user_defined_foreign_keys)
            parent = self.parent.primary_mapper()
            kwargs.setdefault('viewonly', self.viewonly)
            kwargs.setdefault('post_update', self.post_update)
            kwargs.setdefault('passive_updates', self.passive_updates)
            self.back_populates = backref_key
            relationship = RelationshipProperty(
                parent, self.secondary,
                pj, sj,
                foreign_keys=foreign_keys,
                back_populates=self.key,
                **kwargs)
            mapper._configure_property(backref_key, relationship)

        if self.back_populates:
            self._add_reverse_property(self.back_populates)

    def _post_init(self):
        if self.uselist is None:
            self.uselist = self.direction is not MANYTOONE
        if not self.viewonly:
            self._dependency_processor = \
                dependency.DependencyProcessor.from_relationship(self)

    @util.memoized_property
    def _use_get(self):
        """memoize the 'use_get' attribute of this RelationshipLoader's
        lazyloader."""

        strategy = self._get_strategy(strategies.LazyLoader)
        return strategy.use_get

    @util.memoized_property
    def _is_self_referential(self):
        return self.mapper.common_parent(self.parent)

    def _create_joins(self, source_polymorphic=False,
                            source_selectable=None, dest_polymorphic=False,
                            dest_selectable=None, of_type=None):
        if source_selectable is None:
            if source_polymorphic and self.parent.with_polymorphic:
                source_selectable = self.parent._with_polymorphic_selectable

        aliased = False
        if dest_selectable is None:
            if dest_polymorphic and self.mapper.with_polymorphic:
                dest_selectable = self.mapper._with_polymorphic_selectable
                aliased = True
            else:
                dest_selectable = self.mapper.mapped_table

            if self._is_self_referential and source_selectable is None:
                dest_selectable = dest_selectable.alias()
                aliased = True
        else:
            aliased = True

        dest_mapper = of_type or self.mapper

        single_crit = dest_mapper._single_table_criterion
        aliased = aliased or (source_selectable is not None)

        primaryjoin, secondaryjoin, secondary, target_adapter, dest_selectable = \
            self._join_condition.join_targets(
                source_selectable, dest_selectable, aliased, single_crit
            )
        if source_selectable is None:
            source_selectable = self.parent.local_table
        if dest_selectable is None:
            dest_selectable = self.mapper.local_table
        return (primaryjoin, secondaryjoin, source_selectable,
            dest_selectable, secondary, target_adapter)


PropertyLoader = RelationProperty = RelationshipProperty
log.class_logger(RelationshipProperty)
