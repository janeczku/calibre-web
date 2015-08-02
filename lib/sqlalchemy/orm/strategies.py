# orm/strategies.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""sqlalchemy.orm.interfaces.LoaderStrategy
   implementations, and related MapperOptions."""

from .. import exc as sa_exc, inspect
from .. import util, log, event
from ..sql import util as sql_util, visitors
from . import (
        attributes, interfaces, exc as orm_exc, loading,
        unitofwork, util as orm_util
    )
from .state import InstanceState
from .util import _none_set
from .interfaces import (
    LoaderStrategy, StrategizedOption, MapperOption, PropertyOption,
    StrategizedProperty
    )
from .session import _state_session
import itertools


def _register_attribute(strategy, mapper, useobject,
        compare_function=None,
        typecallable=None,
        uselist=False,
        callable_=None,
        proxy_property=None,
        active_history=False,
        impl_class=None,
        **kw
):

    prop = strategy.parent_property

    attribute_ext = list(util.to_list(prop.extension, default=[]))

    listen_hooks = []

    if useobject and prop.single_parent:
        listen_hooks.append(single_parent_validator)

    if prop.key in prop.parent.validators:
        fn, include_removes = prop.parent.validators[prop.key]
        listen_hooks.append(
            lambda desc, prop: orm_util._validator_events(desc,
                                prop.key, fn, include_removes)
            )

    if useobject:
        listen_hooks.append(unitofwork.track_cascade_events)

    # need to assemble backref listeners
    # after the singleparentvalidator, mapper validator
    backref = kw.pop('backref', None)
    if backref:
        listen_hooks.append(
            lambda desc, prop: attributes.backref_listeners(desc,
                                backref,
                                uselist)
        )

    for m in mapper.self_and_descendants:
        if prop is m._props.get(prop.key):

            desc = attributes.register_attribute_impl(
                m.class_,
                prop.key,
                parent_token=prop,
                uselist=uselist,
                compare_function=compare_function,
                useobject=useobject,
                extension=attribute_ext,
                trackparent=useobject and (prop.single_parent
                                or prop.direction is interfaces.ONETOMANY),
                typecallable=typecallable,
                callable_=callable_,
                active_history=active_history,
                impl_class=impl_class,
                doc=prop.doc,
                **kw
                )

            for hook in listen_hooks:
                hook(desc, prop)


class UninstrumentedColumnLoader(LoaderStrategy):
    """Represent the a non-instrumented MapperProperty.

    The polymorphic_on argument of mapper() often results in this,
    if the argument is against the with_polymorphic selectable.

    """
    def __init__(self, parent):
        super(UninstrumentedColumnLoader, self).__init__(parent)
        self.columns = self.parent_property.columns

    def setup_query(self, context, entity, path, adapter,
                            column_collection=None, **kwargs):
        for c in self.columns:
            if adapter:
                c = adapter.columns[c]
            column_collection.append(c)

    def create_row_processor(self, context, path, mapper, row, adapter):
        return None, None, None


class ColumnLoader(LoaderStrategy):
    """Provide loading behavior for a :class:`.ColumnProperty`."""

    def __init__(self, parent):
        super(ColumnLoader, self).__init__(parent)
        self.columns = self.parent_property.columns
        self.is_composite = hasattr(self.parent_property, 'composite_class')

    def setup_query(self, context, entity, path,
                            adapter, column_collection, **kwargs):
        for c in self.columns:
            if adapter:
                c = adapter.columns[c]
            column_collection.append(c)

    def init_class_attribute(self, mapper):
        self.is_class_level = True
        coltype = self.columns[0].type
        # TODO: check all columns ?  check for foreign key as well?
        active_history = self.parent_property.active_history or \
                            self.columns[0].primary_key

        _register_attribute(self, mapper, useobject=False,
            compare_function=coltype.compare_values,
            active_history=active_history
       )

    def create_row_processor(self, context, path,
                                            mapper, row, adapter):
        key = self.key
        # look through list of columns represented here
        # to see which, if any, is present in the row.
        for col in self.columns:
            if adapter:
                col = adapter.columns[col]
            if col is not None and col in row:
                def fetch_col(state, dict_, row):
                    dict_[key] = row[col]
                return fetch_col, None, None
        else:
            def expire_for_non_present_col(state, dict_, row):
                state._expire_attribute_pre_commit(dict_, key)
            return expire_for_non_present_col, None, None


log.class_logger(ColumnLoader)


class DeferredColumnLoader(LoaderStrategy):
    """Provide loading behavior for a deferred :class:`.ColumnProperty`."""

    def __init__(self, parent):
        super(DeferredColumnLoader, self).__init__(parent)
        if hasattr(self.parent_property, 'composite_class'):
            raise NotImplementedError("Deferred loading for composite "
                                    "types not implemented yet")
        self.columns = self.parent_property.columns
        self.group = self.parent_property.group

    def create_row_processor(self, context, path, mapper, row, adapter):
        col = self.columns[0]
        if adapter:
            col = adapter.columns[col]

        key = self.key
        if col in row:
            return self.parent_property._get_strategy(ColumnLoader).\
                        create_row_processor(
                                context, path, mapper, row, adapter)

        elif not self.is_class_level:
            set_deferred_for_local_state = InstanceState._row_processor(
                                                mapper.class_manager,
                                                LoadDeferredColumns(key), key)
            return set_deferred_for_local_state, None, None
        else:
            def reset_col_for_deferred(state, dict_, row):
                # reset state on the key so that deferred callables
                # fire off on next access.
                state._reset(dict_, key)
            return reset_col_for_deferred, None, None

    def init_class_attribute(self, mapper):
        self.is_class_level = True

        _register_attribute(self, mapper, useobject=False,
             compare_function=self.columns[0].type.compare_values,
             callable_=self._load_for_state,
             expire_missing=False
        )

    def setup_query(self, context, entity, path, adapter,
                                only_load_props=None, **kwargs):
        if (
                self.group is not None and
                context.attributes.get(('undefer', self.group), False)
            ) or (only_load_props and self.key in only_load_props):
            self.parent_property._get_strategy(ColumnLoader).\
                            setup_query(context, entity,
                                        path, adapter, **kwargs)

    def _load_for_state(self, state, passive):
        if not state.key:
            return attributes.ATTR_EMPTY

        if not passive & attributes.SQL_OK:
            return attributes.PASSIVE_NO_RESULT

        localparent = state.manager.mapper

        if self.group:
            toload = [
                    p.key for p in
                    localparent.iterate_properties
                    if isinstance(p, StrategizedProperty) and
                      isinstance(p.strategy, DeferredColumnLoader) and
                      p.group == self.group
                    ]
        else:
            toload = [self.key]

        # narrow the keys down to just those which have no history
        group = [k for k in toload if k in state.unmodified]

        session = _state_session(state)
        if session is None:
            raise orm_exc.DetachedInstanceError(
                "Parent instance %s is not bound to a Session; "
                "deferred load operation of attribute '%s' cannot proceed" %
                (orm_util.state_str(state), self.key)
                )

        query = session.query(localparent)
        if loading.load_on_ident(query, state.key,
                    only_load_props=group, refresh_state=state) is None:
            raise orm_exc.ObjectDeletedError(state)

        return attributes.ATTR_WAS_SET


log.class_logger(DeferredColumnLoader)


class LoadDeferredColumns(object):
    """serializable loader object used by DeferredColumnLoader"""

    def __init__(self, key):
        self.key = key

    def __call__(self, state, passive=attributes.PASSIVE_OFF):
        key = self.key

        localparent = state.manager.mapper
        prop = localparent._props[key]
        strategy = prop._strategies[DeferredColumnLoader]
        return strategy._load_for_state(state, passive)


class DeferredOption(StrategizedOption):
    propagate_to_loaders = True

    def __init__(self, key, defer=False):
        super(DeferredOption, self).__init__(key)
        self.defer = defer

    def get_strategy_class(self):
        if self.defer:
            return DeferredColumnLoader
        else:
            return ColumnLoader


class UndeferGroupOption(MapperOption):
    propagate_to_loaders = True

    def __init__(self, group):
        self.group = group

    def process_query(self, query):
        query._attributes[("undefer", self.group)] = True


class AbstractRelationshipLoader(LoaderStrategy):
    """LoaderStratgies which deal with related objects."""

    def __init__(self, parent):
        super(AbstractRelationshipLoader, self).__init__(parent)
        self.mapper = self.parent_property.mapper
        self.target = self.parent_property.target
        self.uselist = self.parent_property.uselist



class NoLoader(AbstractRelationshipLoader):
    """Provide loading behavior for a :class:`.RelationshipProperty`
    with "lazy=None".

    """

    def init_class_attribute(self, mapper):
        self.is_class_level = True

        _register_attribute(self, mapper,
            useobject=True,
            uselist=self.parent_property.uselist,
            typecallable=self.parent_property.collection_class,
        )

    def create_row_processor(self, context, path, mapper, row, adapter):
        def invoke_no_load(state, dict_, row):
            state._initialize(self.key)
        return invoke_no_load, None, None


log.class_logger(NoLoader)


class LazyLoader(AbstractRelationshipLoader):
    """Provide loading behavior for a :class:`.RelationshipProperty`
    with "lazy=True", that is loads when first accessed.

    """

    def __init__(self, parent):
        super(LazyLoader, self).__init__(parent)
        join_condition = self.parent_property._join_condition
        self._lazywhere, \
        self._bind_to_col, \
        self._equated_columns = join_condition.create_lazy_clause()

        self._rev_lazywhere, \
        self._rev_bind_to_col, \
        self._rev_equated_columns = join_condition.create_lazy_clause(
                                                reverse_direction=True)

        self.logger.info("%s lazy loading clause %s", self, self._lazywhere)

        # determine if our "lazywhere" clause is the same as the mapper's
        # get() clause.  then we can just use mapper.get()
        #from sqlalchemy.orm import query
        self.use_get = not self.uselist and \
                        self.mapper._get_clause[0].compare(
                            self._lazywhere,
                            use_proxies=True,
                            equivalents=self.mapper._equivalent_columns
                        )

        if self.use_get:
            for col in self._equated_columns.keys():
                if col in self.mapper._equivalent_columns:
                    for c in self.mapper._equivalent_columns[col]:
                        self._equated_columns[c] = self._equated_columns[col]

            self.logger.info("%s will use query.get() to "
                                    "optimize instance loads" % self)

    def init_class_attribute(self, mapper):
        self.is_class_level = True

        active_history = (
            self.parent_property.active_history or
            self.parent_property.direction is not interfaces.MANYTOONE or
            not self.use_get
        )

        # MANYTOONE currently only needs the
        # "old" value for delete-orphan
        # cascades.  the required _SingleParentValidator
        # will enable active_history
        # in that case.  otherwise we don't need the
        # "old" value during backref operations.
        _register_attribute(self,
            mapper,
            useobject=True,
            callable_=self._load_for_state,
            uselist=self.parent_property.uselist,
            backref=self.parent_property.back_populates,
            typecallable=self.parent_property.collection_class,
            active_history=active_history
        )

    def lazy_clause(self, state, reverse_direction=False,
                                alias_secondary=False,
                                adapt_source=None,
                                passive=None):
        if state is None:
            return self._lazy_none_clause(
                                        reverse_direction,
                                        adapt_source=adapt_source)

        if not reverse_direction:
            criterion, bind_to_col, rev = \
                                            self._lazywhere, \
                                            self._bind_to_col, \
                                            self._equated_columns
        else:
            criterion, bind_to_col, rev = \
                                            self._rev_lazywhere, \
                                            self._rev_bind_to_col, \
                                            self._rev_equated_columns

        if reverse_direction:
            mapper = self.parent_property.mapper
        else:
            mapper = self.parent_property.parent

        o = state.obj()  # strong ref
        dict_ = attributes.instance_dict(o)

        # use the "committed state" only if we're in a flush
        # for this state.

        if passive and passive & attributes.LOAD_AGAINST_COMMITTED:
            def visit_bindparam(bindparam):
                if bindparam._identifying_key in bind_to_col:
                    bindparam.callable = \
                        lambda: mapper._get_committed_state_attr_by_column(
                            state, dict_,
                            bind_to_col[bindparam._identifying_key])
        else:
            def visit_bindparam(bindparam):
                if bindparam._identifying_key in bind_to_col:
                    bindparam.callable = \
                            lambda: mapper._get_state_attr_by_column(
                                    state, dict_,
                                    bind_to_col[bindparam._identifying_key])

        if self.parent_property.secondary is not None and alias_secondary:
            criterion = sql_util.ClauseAdapter(
                                self.parent_property.secondary.alias()).\
                                traverse(criterion)

        criterion = visitors.cloned_traverse(
                                criterion, {}, {'bindparam': visit_bindparam})

        if adapt_source:
            criterion = adapt_source(criterion)
        return criterion

    def _lazy_none_clause(self, reverse_direction=False, adapt_source=None):
        if not reverse_direction:
            criterion, bind_to_col, rev = \
                                        self._lazywhere, \
                                        self._bind_to_col,\
                                        self._equated_columns
        else:
            criterion, bind_to_col, rev = \
                                            self._rev_lazywhere, \
                                            self._rev_bind_to_col, \
                                            self._rev_equated_columns

        criterion = sql_util.adapt_criterion_to_null(criterion, bind_to_col)

        if adapt_source:
            criterion = adapt_source(criterion)
        return criterion

    def _load_for_state(self, state, passive):
        if not state.key and \
            (
                (
                    not self.parent_property.load_on_pending
                    and not state._load_pending
                )
                or not state.session_id
            ):
            return attributes.ATTR_EMPTY

        pending = not state.key
        ident_key = None

        if (
            (not passive & attributes.SQL_OK and not self.use_get)
            or
            (not passive & attributes.NON_PERSISTENT_OK and pending)
        ):
            return attributes.PASSIVE_NO_RESULT

        session = _state_session(state)
        if not session:
            raise orm_exc.DetachedInstanceError(
                "Parent instance %s is not bound to a Session; "
                "lazy load operation of attribute '%s' cannot proceed" %
                (orm_util.state_str(state), self.key)
            )

        # if we have a simple primary key load, check the
        # identity map without generating a Query at all
        if self.use_get:
            ident = self._get_ident_for_use_get(
                session,
                state,
                passive
            )
            if attributes.PASSIVE_NO_RESULT in ident:
                return attributes.PASSIVE_NO_RESULT
            elif attributes.NEVER_SET in ident:
                return attributes.NEVER_SET

            if _none_set.issuperset(ident):
                return None

            ident_key = self.mapper.identity_key_from_primary_key(ident)
            instance = loading.get_from_identity(session, ident_key, passive)
            if instance is not None:
                return instance
            elif not passive & attributes.SQL_OK or \
                not passive & attributes.RELATED_OBJECT_OK:
                return attributes.PASSIVE_NO_RESULT

        return self._emit_lazyload(session, state, ident_key, passive)

    def _get_ident_for_use_get(self, session, state, passive):
        instance_mapper = state.manager.mapper

        if passive & attributes.LOAD_AGAINST_COMMITTED:
            get_attr = instance_mapper._get_committed_state_attr_by_column
        else:
            get_attr = instance_mapper._get_state_attr_by_column

        dict_ = state.dict

        return [
            get_attr(
                    state,
                    dict_,
                    self._equated_columns[pk],
                    passive=passive)
            for pk in self.mapper.primary_key
        ]

    def _emit_lazyload(self, session, state, ident_key, passive):
        q = session.query(self.mapper)._adapt_all_clauses()

        q = q._with_invoke_all_eagers(False)

        pending = not state.key

        # don't autoflush on pending
        if pending:
            q = q.autoflush(False)

        if state.load_path:
            q = q._with_current_path(state.load_path[self.parent_property])

        if state.load_options:
            q = q._conditional_options(*state.load_options)

        if self.use_get:
            return loading.load_on_ident(q, ident_key)

        if self.parent_property.order_by:
            q = q.order_by(*util.to_list(self.parent_property.order_by))

        for rev in self.parent_property._reverse_property:
            # reverse props that are MANYTOONE are loading *this*
            # object from get(), so don't need to eager out to those.
            if rev.direction is interfaces.MANYTOONE and \
                        rev._use_get and \
                        not isinstance(rev.strategy, LazyLoader):
                q = q.options(EagerLazyOption((rev.key,), lazy='select'))

        lazy_clause = self.lazy_clause(state, passive=passive)

        if pending:
            bind_values = sql_util.bind_values(lazy_clause)
            if None in bind_values:
                return None

        q = q.filter(lazy_clause)

        result = q.all()
        if self.uselist:
            return result
        else:
            l = len(result)
            if l:
                if l > 1:
                    util.warn(
                        "Multiple rows returned with "
                        "uselist=False for lazily-loaded attribute '%s' "
                        % self.parent_property)

                return result[0]
            else:
                return None

    def create_row_processor(self, context, path,
                                    mapper, row, adapter):
        key = self.key
        if not self.is_class_level:
            # we are not the primary manager for this attribute
            # on this class - set up a
            # per-instance lazyloader, which will override the
            # class-level behavior.
            # this currently only happens when using a
            # "lazyload" option on a "no load"
            # attribute - "eager" attributes always have a
            # class-level lazyloader installed.
            set_lazy_callable = InstanceState._row_processor(
                                        mapper.class_manager,
                                        LoadLazyAttribute(key), key)

            return set_lazy_callable, None, None
        else:
            def reset_for_lazy_callable(state, dict_, row):
                # we are the primary manager for this attribute on
                # this class - reset its
                # per-instance attribute state, so that the class-level
                # lazy loader is
                # executed when next referenced on this instance.
                # this is needed in
                # populate_existing() types of scenarios to reset
                # any existing state.
                state._reset(dict_, key)

            return reset_for_lazy_callable, None, None


log.class_logger(LazyLoader)


class LoadLazyAttribute(object):
    """serializable loader object used by LazyLoader"""

    def __init__(self, key):
        self.key = key

    def __call__(self, state, passive=attributes.PASSIVE_OFF):
        key = self.key
        instance_mapper = state.manager.mapper
        prop = instance_mapper._props[key]
        strategy = prop._strategies[LazyLoader]

        return strategy._load_for_state(state, passive)


class ImmediateLoader(AbstractRelationshipLoader):
    def init_class_attribute(self, mapper):
        self.parent_property.\
                _get_strategy(LazyLoader).\
                init_class_attribute(mapper)

    def setup_query(self, context, entity,
                        path, adapter, column_collection=None,
                        parentmapper=None, **kwargs):
        pass

    def create_row_processor(self, context, path,
                                mapper, row, adapter):
        def load_immediate(state, dict_, row):
            state.get_impl(self.key).get(state, dict_)

        return None, None, load_immediate


class SubqueryLoader(AbstractRelationshipLoader):
    def __init__(self, parent):
        super(SubqueryLoader, self).__init__(parent)
        self.join_depth = self.parent_property.join_depth

    def init_class_attribute(self, mapper):
        self.parent_property.\
                _get_strategy(LazyLoader).\
                init_class_attribute(mapper)

    def setup_query(self, context, entity,
                        path, adapter,
                        column_collection=None,
                        parentmapper=None, **kwargs):

        if not context.query._enable_eagerloads:
            return

        path = path[self.parent_property]

        # build up a path indicating the path from the leftmost
        # entity to the thing we're subquery loading.
        with_poly_info = path.get(context, "path_with_polymorphic", None)
        if with_poly_info is not None:
            effective_entity = with_poly_info.entity
        else:
            effective_entity = self.mapper

        subq_path = context.attributes.get(('subquery_path', None),
                                orm_util.PathRegistry.root)

        subq_path = subq_path + path

        # if not via query option, check for
        # a cycle
        if not path.contains(context, "loaderstrategy"):
            if self.join_depth:
                if path.length / 2 > self.join_depth:
                    return
            elif subq_path.contains_mapper(self.mapper):
                return

        subq_mapper, leftmost_mapper, leftmost_attr, leftmost_relationship = \
                self._get_leftmost(subq_path)

        orig_query = context.attributes.get(
                                ("orig_query", SubqueryLoader),
                                context.query)

        # generate a new Query from the original, then
        # produce a subquery from it.
        left_alias = self._generate_from_original_query(
                            orig_query, leftmost_mapper,
                            leftmost_attr, leftmost_relationship,
                            entity.mapper
        )

        # generate another Query that will join the
        # left alias to the target relationships.
        # basically doing a longhand
        # "from_self()".  (from_self() itself not quite industrial
        # strength enough for all contingencies...but very close)
        q = orig_query.session.query(effective_entity)
        q._attributes = {
            ("orig_query", SubqueryLoader): orig_query,
            ('subquery_path', None): subq_path
        }
        q = q._enable_single_crit(False)

        to_join, local_attr, parent_alias = \
                    self._prep_for_joins(left_alias, subq_path)
        q = q.order_by(*local_attr)
        q = q.add_columns(*local_attr)

        q = self._apply_joins(q, to_join, left_alias,
                            parent_alias, effective_entity)

        q = self._setup_options(q, subq_path, orig_query, effective_entity)
        q = self._setup_outermost_orderby(q)

        # add new query to attributes to be picked up
        # by create_row_processor
        path.set(context, "subquery", q)

    def _get_leftmost(self, subq_path):
        subq_path = subq_path.path
        subq_mapper = orm_util._class_to_mapper(subq_path[0])

        # determine attributes of the leftmost mapper
        if self.parent.isa(subq_mapper) and self.parent_property is subq_path[1]:
            leftmost_mapper, leftmost_prop = \
                                    self.parent, self.parent_property
        else:
            leftmost_mapper, leftmost_prop = \
                                    subq_mapper, \
                                    subq_path[1]

        leftmost_cols = leftmost_prop.local_columns

        leftmost_attr = [
            leftmost_mapper._columntoproperty[c].class_attribute
            for c in leftmost_cols
        ]
        return subq_mapper, leftmost_mapper, leftmost_attr, leftmost_prop

    def _generate_from_original_query(self,
            orig_query, leftmost_mapper,
            leftmost_attr, leftmost_relationship,
            entity_mapper
    ):
        # reformat the original query
        # to look only for significant columns
        q = orig_query._clone().correlate(None)

        # set a real "from" if not present, as this is more
        # accurate than just going off of the column expression
        if not q._from_obj and entity_mapper.isa(leftmost_mapper):
            q._set_select_from([entity_mapper], False)

        target_cols = q._adapt_col_list(leftmost_attr)

        # select from the identity columns of the outer
        q._set_entities(target_cols)

        distinct_target_key = leftmost_relationship.distinct_target_key

        if distinct_target_key is True:
            q._distinct = True
        elif distinct_target_key is None:
            # if target_cols refer to a non-primary key or only
            # part of a composite primary key, set the q as distinct
            for t in set(c.table for c in target_cols):
                if not set(target_cols).issuperset(t.primary_key):
                    q._distinct = True
                    break

        if q._order_by is False:
            q._order_by = leftmost_mapper.order_by

        # don't need ORDER BY if no limit/offset
        if q._limit is None and q._offset is None:
            q._order_by = None

        # the original query now becomes a subquery
        # which we'll join onto.

        embed_q = q.with_labels().subquery()
        left_alias = orm_util.AliasedClass(leftmost_mapper, embed_q,
                            use_mapper_path=True)
        return left_alias

    def _prep_for_joins(self, left_alias, subq_path):
        # figure out what's being joined.  a.k.a. the fun part
        to_join = []
        pairs = list(subq_path.pairs())

        for i, (mapper, prop) in enumerate(pairs):
            if i > 0:
                # look at the previous mapper in the chain -
                # if it is as or more specific than this prop's
                # mapper, use that instead.
                # note we have an assumption here that
                # the non-first element is always going to be a mapper,
                # not an AliasedClass

                prev_mapper = pairs[i - 1][1].mapper
                to_append = prev_mapper if prev_mapper.isa(mapper) else mapper
            else:
                to_append = mapper

            to_join.append((to_append, prop.key))

        # determine the immediate parent class we are joining from,
        # which needs to be aliased.
        if len(to_join) > 1:
            info = inspect(to_join[-1][0])

        if len(to_join) < 2:
            # in the case of a one level eager load, this is the
            # leftmost "left_alias".
            parent_alias = left_alias
        elif info.mapper.isa(self.parent):
            # In the case of multiple levels, retrieve
            # it from subq_path[-2]. This is the same as self.parent
            # in the vast majority of cases, and [ticket:2014]
            # illustrates a case where sub_path[-2] is a subclass
            # of self.parent
            parent_alias = orm_util.AliasedClass(to_join[-1][0],
                                use_mapper_path=True)
        else:
            # if of_type() were used leading to this relationship,
            # self.parent is more specific than subq_path[-2]
            parent_alias = orm_util.AliasedClass(self.parent,
                                use_mapper_path=True)

        local_cols = self.parent_property.local_columns

        local_attr = [
            getattr(parent_alias, self.parent._columntoproperty[c].key)
            for c in local_cols
        ]
        return to_join, local_attr, parent_alias

    def _apply_joins(self, q, to_join, left_alias, parent_alias,
                    effective_entity):
        for i, (mapper, key) in enumerate(to_join):

            # we need to use query.join() as opposed to
            # orm.join() here because of the
            # rich behavior it brings when dealing with
            # "with_polymorphic" mappers.  "aliased"
            # and "from_joinpoint" take care of most of
            # the chaining and aliasing for us.

            first = i == 0
            middle = i < len(to_join) - 1
            second_to_last = i == len(to_join) - 2
            last = i == len(to_join) - 1

            if first:
                attr = getattr(left_alias, key)
                if last and effective_entity is not self.mapper:
                    attr = attr.of_type(effective_entity)
            else:
                if last and effective_entity is not self.mapper:
                    attr = getattr(parent_alias, key).\
                                    of_type(effective_entity)
                else:
                    attr = key

            if second_to_last:
                q = q.join(parent_alias, attr, from_joinpoint=True)
            else:
                q = q.join(attr, aliased=middle, from_joinpoint=True)
        return q

    def _setup_options(self, q, subq_path, orig_query, effective_entity):
        # propagate loader options etc. to the new query.
        # these will fire relative to subq_path.
        q = q._with_current_path(subq_path)
        q = q._conditional_options(*orig_query._with_options)
        if orig_query._populate_existing:
            q._populate_existing = orig_query._populate_existing

        return q

    def _setup_outermost_orderby(self, q):
        if self.parent_property.order_by:
            # if there's an ORDER BY, alias it the same
            # way joinedloader does, but we have to pull out
            # the "eagerjoin" from the query.
            # this really only picks up the "secondary" table
            # right now.
            eagerjoin = q._from_obj[0]
            eager_order_by = \
                            eagerjoin._target_adapter.\
                                copy_and_process(
                                    util.to_list(
                                        self.parent_property.order_by
                                    )
                                )
            q = q.order_by(*eager_order_by)
        return q

    def create_row_processor(self, context, path,
                                    mapper, row, adapter):
        if not self.parent.class_manager[self.key].impl.supports_population:
            raise sa_exc.InvalidRequestError(
                        "'%s' does not support object "
                        "population - eager loading cannot be applied." %
                        self)

        path = path[self.parent_property]

        subq = path.get(context, 'subquery')

        if subq is None:
            return None, None, None

        local_cols = self.parent_property.local_columns

        # cache the loaded collections in the context
        # so that inheriting mappers don't re-load when they
        # call upon create_row_processor again
        collections = path.get(context, "collections")
        if collections is None:
            collections = dict(
                    (k, [v[0] for v in v])
                    for k, v in itertools.groupby(
                        subq,
                        lambda x: x[1:]
                    ))
            path.set(context, 'collections', collections)

        if adapter:
            local_cols = [adapter.columns[c] for c in local_cols]

        if self.uselist:
            return self._create_collection_loader(collections, local_cols)
        else:
            return self._create_scalar_loader(collections, local_cols)

    def _create_collection_loader(self, collections, local_cols):
        def load_collection_from_subq(state, dict_, row):
            collection = collections.get(
                tuple([row[col] for col in local_cols]),
                ()
            )
            state.get_impl(self.key).\
                    set_committed_value(state, dict_, collection)

        return load_collection_from_subq, None, None

    def _create_scalar_loader(self, collections, local_cols):
        def load_scalar_from_subq(state, dict_, row):
            collection = collections.get(
                tuple([row[col] for col in local_cols]),
                (None,)
            )
            if len(collection) > 1:
                util.warn(
                    "Multiple rows returned with "
                    "uselist=False for eagerly-loaded attribute '%s' "
                    % self)

            scalar = collection[0]
            state.get_impl(self.key).\
                    set_committed_value(state, dict_, scalar)

        return load_scalar_from_subq, None, None


log.class_logger(SubqueryLoader)


class JoinedLoader(AbstractRelationshipLoader):
    """Provide loading behavior for a :class:`.RelationshipProperty`
    using joined eager loading.

    """
    def __init__(self, parent):
        super(JoinedLoader, self).__init__(parent)
        self.join_depth = self.parent_property.join_depth

    def init_class_attribute(self, mapper):
        self.parent_property.\
            _get_strategy(LazyLoader).init_class_attribute(mapper)

    def setup_query(self, context, entity, path, adapter, \
                                column_collection=None, parentmapper=None,
                                allow_innerjoin=True,
                                **kwargs):
        """Add a left outer join to the statement thats being constructed."""

        if not context.query._enable_eagerloads:
            return

        path = path[self.parent_property]

        with_polymorphic = None

        user_defined_adapter = path.get(context,
                                "user_defined_eager_row_processor",
                                False)
        if user_defined_adapter is not False:
            clauses, adapter, add_to_collection = \
                self._get_user_defined_adapter(
                    context, entity, path, adapter,
                    user_defined_adapter
                )
        else:
            # if not via query option, check for
            # a cycle
            if not path.contains(context, "loaderstrategy"):
                if self.join_depth:
                    if path.length / 2 > self.join_depth:
                        return
                elif path.contains_mapper(self.mapper):
                    return

            clauses, adapter, add_to_collection, \
                allow_innerjoin = self._generate_row_adapter(
                    context, entity, path, adapter,
                    column_collection, parentmapper, allow_innerjoin
                )

        with_poly_info = path.get(
            context,
            "path_with_polymorphic",
            None
        )
        if with_poly_info is not None:
            with_polymorphic = with_poly_info.with_polymorphic_mappers
        else:
            with_polymorphic = None

        path = path[self.mapper]

        for value in self.mapper._iterate_polymorphic_properties(
                                mappers=with_polymorphic):
            value.setup(
                context,
                entity,
                path,
                clauses,
                parentmapper=self.mapper,
                column_collection=add_to_collection,
                allow_innerjoin=allow_innerjoin)

    def _get_user_defined_adapter(self, context, entity,
                                path, adapter, user_defined_adapter):

            adapter = entity._get_entity_clauses(context.query, context)
            if adapter and user_defined_adapter:
                user_defined_adapter = user_defined_adapter.wrap(adapter)
                path.set(context, "user_defined_eager_row_processor",
                                        user_defined_adapter)
            elif adapter:
                user_defined_adapter = adapter
                path.set(context, "user_defined_eager_row_processor",
                                        user_defined_adapter)

            add_to_collection = context.primary_columns
            return user_defined_adapter, adapter, add_to_collection

    def _generate_row_adapter(self,
        context, entity, path, adapter,
        column_collection, parentmapper, allow_innerjoin
    ):
        with_poly_info = path.get(
            context,
            "path_with_polymorphic",
            None
        )
        if with_poly_info:
            to_adapt = with_poly_info.entity
        else:
            to_adapt = orm_util.AliasedClass(self.mapper,
                                use_mapper_path=True)
        clauses = orm_util.ORMAdapter(
                    to_adapt,
                    equivalents=self.mapper._equivalent_columns,
                    adapt_required=True)
        assert clauses.aliased_class is not None

        if self.parent_property.direction != interfaces.MANYTOONE:
            context.multi_row_eager_loaders = True

        innerjoin = allow_innerjoin and path.get(context,
                            "eager_join_type",
                            self.parent_property.innerjoin)
        if not innerjoin:
            # if this is an outer join, all eager joins from
            # here must also be outer joins
            allow_innerjoin = False

        context.create_eager_joins.append(
            (self._create_eager_join, context,
            entity, path, adapter,
            parentmapper, clauses, innerjoin)
        )

        add_to_collection = context.secondary_columns
        path.set(context, "eager_row_processor", clauses)

        return clauses, adapter, add_to_collection, allow_innerjoin

    def _create_eager_join(self, context, entity,
                            path, adapter, parentmapper,
                            clauses, innerjoin):

        if parentmapper is None:
            localparent = entity.mapper
        else:
            localparent = parentmapper

        # whether or not the Query will wrap the selectable in a subquery,
        # and then attach eager load joins to that (i.e., in the case of
        # LIMIT/OFFSET etc.)
        should_nest_selectable = context.multi_row_eager_loaders and \
            context.query._should_nest_selectable

        entity_key = None

        if entity not in context.eager_joins and \
            not should_nest_selectable and \
            context.from_clause:
            index, clause = \
                sql_util.find_join_source(
                                context.from_clause, entity.selectable)
            if clause is not None:
                # join to an existing FROM clause on the query.
                # key it to its list index in the eager_joins dict.
                # Query._compile_context will adapt as needed and
                # append to the FROM clause of the select().
                entity_key, default_towrap = index, clause

        if entity_key is None:
            entity_key, default_towrap = entity, entity.selectable

        towrap = context.eager_joins.setdefault(entity_key, default_towrap)

        if adapter:
            if getattr(adapter, 'aliased_class', None):
                onclause = getattr(
                                adapter.aliased_class, self.key,
                                self.parent_property)
            else:
                onclause = getattr(
                                orm_util.AliasedClass(
                                        self.parent,
                                        adapter.selectable,
                                        use_mapper_path=True
                                ),
                                self.key, self.parent_property
                            )

        else:
            onclause = self.parent_property

        assert clauses.aliased_class is not None
        context.eager_joins[entity_key] = eagerjoin = \
                                orm_util.join(
                                            towrap,
                                            clauses.aliased_class,
                                            onclause,
                                            isouter=not innerjoin
                                            )

        # send a hint to the Query as to where it may "splice" this join
        eagerjoin.stop_on = entity.selectable

        if self.parent_property.secondary is None and \
                not parentmapper:
            # for parentclause that is the non-eager end of the join,
            # ensure all the parent cols in the primaryjoin are actually
            # in the
            # columns clause (i.e. are not deferred), so that aliasing applied
            # by the Query propagates those columns outward.
            # This has the effect
            # of "undefering" those columns.
            for col in sql_util.find_columns(
                                self.parent_property.primaryjoin):
                if localparent.mapped_table.c.contains_column(col):
                    if adapter:
                        col = adapter.columns[col]
                    context.primary_columns.append(col)

        if self.parent_property.order_by:
            context.eager_order_by += \
                            eagerjoin._target_adapter.\
                                copy_and_process(
                                    util.to_list(
                                        self.parent_property.order_by
                                    )
                                )

    def _create_eager_adapter(self, context, row, adapter, path):
        user_defined_adapter = path.get(context,
                                "user_defined_eager_row_processor",
                                False)
        if user_defined_adapter is not False:
            decorator = user_defined_adapter
            # user defined eagerloads are part of the "primary"
            # portion of the load.
            # the adapters applied to the Query should be honored.
            if context.adapter and decorator:
                decorator = decorator.wrap(context.adapter)
            elif context.adapter:
                decorator = context.adapter
        else:
            decorator = path.get(context, "eager_row_processor")
            if decorator is None:
                return False

        try:
            self.mapper.identity_key_from_row(row, decorator)
            return decorator
        except KeyError:
            # no identity key - dont return a row
            # processor, will cause a degrade to lazy
            return False

    def create_row_processor(self, context, path, mapper, row, adapter):
        if not self.parent.class_manager[self.key].impl.supports_population:
            raise sa_exc.InvalidRequestError(
                        "'%s' does not support object "
                        "population - eager loading cannot be applied." %
                        self)

        our_path = path[self.parent_property]

        eager_adapter = self._create_eager_adapter(
                                                context,
                                                row,
                                                adapter, our_path)

        if eager_adapter is not False:
            key = self.key

            _instance = loading.instance_processor(
                                self.mapper,
                                context,
                                our_path[self.mapper],
                                eager_adapter)

            if not self.uselist:
                return self._create_scalar_loader(context, key, _instance)
            else:
                return self._create_collection_loader(context, key, _instance)
        else:
            return self.parent_property.\
                            _get_strategy(LazyLoader).\
                            create_row_processor(
                                            context, path,
                                            mapper, row, adapter)

    def _create_collection_loader(self, context, key, _instance):
        def load_collection_from_joined_new_row(state, dict_, row):
            collection = attributes.init_state_collection(
                                            state, dict_, key)
            result_list = util.UniqueAppender(collection,
                                              'append_without_event')
            context.attributes[(state, key)] = result_list
            _instance(row, result_list)

        def load_collection_from_joined_existing_row(state, dict_, row):
            if (state, key) in context.attributes:
                result_list = context.attributes[(state, key)]
            else:
                # appender_key can be absent from context.attributes
                # with isnew=False when self-referential eager loading
                # is used; the same instance may be present in two
                # distinct sets of result columns
                collection = attributes.init_state_collection(state,
                                dict_, key)
                result_list = util.UniqueAppender(
                                        collection,
                                        'append_without_event')
                context.attributes[(state, key)] = result_list
            _instance(row, result_list)

        def load_collection_from_joined_exec(state, dict_, row):
            _instance(row, None)

        return load_collection_from_joined_new_row, \
                load_collection_from_joined_existing_row, \
                None, load_collection_from_joined_exec

    def _create_scalar_loader(self, context, key, _instance):
        def load_scalar_from_joined_new_row(state, dict_, row):
            # set a scalar object instance directly on the parent
            # object, bypassing InstrumentedAttribute event handlers.
            dict_[key] = _instance(row, None)

        def load_scalar_from_joined_existing_row(state, dict_, row):
            # call _instance on the row, even though the object has
            # been created, so that we further descend into properties
            existing = _instance(row, None)
            if existing is not None \
                and key in dict_ \
                and existing is not dict_[key]:
                util.warn(
                    "Multiple rows returned with "
                    "uselist=False for eagerly-loaded attribute '%s' "
                    % self)

        def load_scalar_from_joined_exec(state, dict_, row):
            _instance(row, None)

        return load_scalar_from_joined_new_row, \
                load_scalar_from_joined_existing_row, \
                None, load_scalar_from_joined_exec


log.class_logger(JoinedLoader)


class EagerLazyOption(StrategizedOption):
    def __init__(self, key, lazy=True, chained=False,
                    propagate_to_loaders=True
                    ):
        if isinstance(key[0], basestring) and key[0] == '*':
            if len(key) != 1:
                raise sa_exc.ArgumentError(
                        "Wildcard identifier '*' must "
                        "be specified alone.")
            key = ("relationship:*",)
            propagate_to_loaders = False
        super(EagerLazyOption, self).__init__(key)
        self.lazy = lazy
        self.chained = chained
        self.propagate_to_loaders = propagate_to_loaders
        self.strategy_cls = factory(lazy)

    def get_strategy_class(self):
        return self.strategy_cls

_factory = {
    False: JoinedLoader,
    "joined": JoinedLoader,
    None: NoLoader,
    "noload": NoLoader,
    "select": LazyLoader,
    True: LazyLoader,
    "subquery": SubqueryLoader,
    "immediate": ImmediateLoader
}


def factory(identifier):
    return _factory.get(identifier, LazyLoader)


class EagerJoinOption(PropertyOption):

    def __init__(self, key, innerjoin, chained=False):
        super(EagerJoinOption, self).__init__(key)
        self.innerjoin = innerjoin
        self.chained = chained

    def process_query_property(self, query, paths):
        if self.chained:
            for path in paths:
                path.set(query, "eager_join_type", self.innerjoin)
        else:
            paths[-1].set(query, "eager_join_type", self.innerjoin)


class LoadEagerFromAliasOption(PropertyOption):

    def __init__(self, key, alias=None, chained=False):
        super(LoadEagerFromAliasOption, self).__init__(key)
        if alias is not None:
            if not isinstance(alias, basestring):
                info = inspect(alias)
                alias = info.selectable
        self.alias = alias
        self.chained = chained

    def process_query_property(self, query, paths):
        if self.chained:
            for path in paths[0:-1]:
                (root_mapper, prop) = path.path[-2:]
                adapter = query._polymorphic_adapters.get(prop.mapper, None)
                path.setdefault(query,
                            "user_defined_eager_row_processor",
                            adapter)

        root_mapper, prop = paths[-1].path[-2:]
        if self.alias is not None:
            if isinstance(self.alias, basestring):
                self.alias = prop.target.alias(self.alias)
            paths[-1].set(query, "user_defined_eager_row_processor",
                sql_util.ColumnAdapter(self.alias,
                                equivalents=prop.mapper._equivalent_columns)
            )
        else:
            if paths[-1].contains(query, "path_with_polymorphic"):
                with_poly_info = paths[-1].get(query, "path_with_polymorphic")
                adapter = orm_util.ORMAdapter(
                            with_poly_info.entity,
                            equivalents=prop.mapper._equivalent_columns,
                            adapt_required=True)
            else:
                adapter = query._polymorphic_adapters.get(prop.mapper, None)
            paths[-1].set(query, "user_defined_eager_row_processor",
                                    adapter)


def single_parent_validator(desc, prop):
    def _do_check(state, value, oldvalue, initiator):
        if value is not None and initiator.key == prop.key:
            hasparent = initiator.hasparent(attributes.instance_state(value))
            if hasparent and oldvalue is not value:
                raise sa_exc.InvalidRequestError(
                    "Instance %s is already associated with an instance "
                    "of %s via its %s attribute, and is only allowed a "
                    "single parent." %
                    (orm_util.instance_str(value), state.class_, prop)
                )
        return value

    def append(state, value, initiator):
        return _do_check(state, value, None, initiator)

    def set_(state, value, oldvalue, initiator):
        return _do_check(state, value, oldvalue, initiator)

    event.listen(desc, 'append', append, raw=True, retval=True,
                            active_history=True)
    event.listen(desc, 'set', set_, raw=True, retval=True,
                            active_history=True)
