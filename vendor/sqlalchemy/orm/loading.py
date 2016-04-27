# orm/loading.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""private module containing functions used to convert database
rows into object instances and associated state.

the functions here are called primarily by Query, Mapper,
as well as some of the attribute loading strategies.

"""
from __future__ import absolute_import

from .. import util
from . import attributes, exc as orm_exc, state as statelib
from .interfaces import EXT_CONTINUE
from ..sql import util as sql_util
from .util import _none_set, state_str
from .. import exc as sa_exc
sessionlib = util.importlater("sqlalchemy.orm", "session")

_new_runid = util.counter()


def instances(query, cursor, context):
    """Return an ORM result as an iterator."""
    session = query.session

    context.runid = _new_runid()

    filter_fns = [ent.filter_fn
                for ent in query._entities]
    filtered = id in filter_fns

    single_entity = filtered and len(query._entities) == 1

    if filtered:
        if single_entity:
            filter_fn = id
        else:
            def filter_fn(row):
                return tuple(fn(x) for x, fn in zip(row, filter_fns))

    custom_rows = single_entity and \
                    query._entities[0].mapper.dispatch.append_result

    (process, labels) = \
                zip(*[
                    query_entity.row_processor(query,
                            context, custom_rows)
                    for query_entity in query._entities
                ])

    while True:
        context.progress = {}
        context.partials = {}

        if query._yield_per:
            fetch = cursor.fetchmany(query._yield_per)
            if not fetch:
                break
        else:
            fetch = cursor.fetchall()

        if custom_rows:
            rows = []
            for row in fetch:
                process[0](row, rows)
        elif single_entity:
            rows = [process[0](row, None) for row in fetch]
        else:
            rows = [util.KeyedTuple([proc(row, None) for proc in process],
                                    labels) for row in fetch]

        if filtered:
            rows = util.unique_list(rows, filter_fn)

        if context.refresh_state and query._only_load_props \
                    and context.refresh_state in context.progress:
            context.refresh_state._commit(
                    context.refresh_state.dict, query._only_load_props)
            context.progress.pop(context.refresh_state)

        statelib.InstanceState._commit_all_states(
            context.progress.items(),
            session.identity_map
        )

        for state, (dict_, attrs) in context.partials.iteritems():
            state._commit(dict_, attrs)

        for row in rows:
            yield row

        if not query._yield_per:
            break


def merge_result(query, iterator, load=True):
    """Merge a result into this :class:`.Query` object's Session."""

    from . import query as querylib

    session = query.session
    if load:
        # flush current contents if we expect to load data
        session._autoflush()

    autoflush = session.autoflush
    try:
        session.autoflush = False
        single_entity = len(query._entities) == 1
        if single_entity:
            if isinstance(query._entities[0], querylib._MapperEntity):
                result = [session._merge(
                        attributes.instance_state(instance),
                        attributes.instance_dict(instance),
                        load=load, _recursive={})
                        for instance in iterator]
            else:
                result = list(iterator)
        else:
            mapped_entities = [i for i, e in enumerate(query._entities)
                                    if isinstance(e, querylib._MapperEntity)]
            result = []
            keys = [ent._label_name for ent in query._entities]
            for row in iterator:
                newrow = list(row)
                for i in mapped_entities:
                    if newrow[i] is not None:
                        newrow[i] = session._merge(
                                attributes.instance_state(newrow[i]),
                                attributes.instance_dict(newrow[i]),
                                load=load, _recursive={})
                result.append(util.KeyedTuple(newrow, keys))

        return iter(result)
    finally:
        session.autoflush = autoflush


def get_from_identity(session, key, passive):
    """Look up the given key in the given session's identity map,
    check the object for expired state if found.

    """
    instance = session.identity_map.get(key)
    if instance is not None:

        state = attributes.instance_state(instance)

        # expired - ensure it still exists
        if state.expired:
            if not passive & attributes.SQL_OK:
                # TODO: no coverage here
                return attributes.PASSIVE_NO_RESULT
            elif not passive & attributes.RELATED_OBJECT_OK:
                # this mode is used within a flush and the instance's
                # expired state will be checked soon enough, if necessary
                return instance
            try:
                state(state, passive)
            except orm_exc.ObjectDeletedError:
                session._remove_newly_deleted([state])
                return None
        return instance
    else:
        return None


def load_on_ident(query, key,
                    refresh_state=None, lockmode=None,
                        only_load_props=None):
    """Load the given identity key from the database."""

    lockmode = lockmode or query._lockmode

    if key is not None:
        ident = key[1]
    else:
        ident = None

    if refresh_state is None:
        q = query._clone()
        q._get_condition()
    else:
        q = query._clone()

    if ident is not None:
        mapper = query._mapper_zero()

        (_get_clause, _get_params) = mapper._get_clause

        # None present in ident - turn those comparisons
        # into "IS NULL"
        if None in ident:
            nones = set([
                        _get_params[col].key for col, value in
                         zip(mapper.primary_key, ident) if value is None
                        ])
            _get_clause = sql_util.adapt_criterion_to_null(
                                            _get_clause, nones)

        _get_clause = q._adapt_clause(_get_clause, True, False)
        q._criterion = _get_clause

        params = dict([
            (_get_params[primary_key].key, id_val)
            for id_val, primary_key in zip(ident, mapper.primary_key)
        ])

        q._params = params

    if lockmode is not None:
        q._lockmode = lockmode
    q._get_options(
        populate_existing=bool(refresh_state),
        version_check=(lockmode is not None),
        only_load_props=only_load_props,
        refresh_state=refresh_state)
    q._order_by = None

    try:
        return q.one()
    except orm_exc.NoResultFound:
        return None


def instance_processor(mapper, context, path, adapter,
                            polymorphic_from=None,
                            only_load_props=None,
                            refresh_state=None,
                            polymorphic_discriminator=None):

    """Produce a mapper level row processor callable
       which processes rows into mapped instances."""

    # note that this method, most of which exists in a closure
    # called _instance(), resists being broken out, as
    # attempts to do so tend to add significant function
    # call overhead.  _instance() is the most
    # performance-critical section in the whole ORM.

    pk_cols = mapper.primary_key

    if polymorphic_from or refresh_state:
        polymorphic_on = None
    else:
        if polymorphic_discriminator is not None:
            polymorphic_on = polymorphic_discriminator
        else:
            polymorphic_on = mapper.polymorphic_on
        polymorphic_instances = util.PopulateDict(
                                    _configure_subclass_mapper(
                                            mapper,
                                            context, path, adapter)
                                    )

    version_id_col = mapper.version_id_col

    if adapter:
        pk_cols = [adapter.columns[c] for c in pk_cols]
        if polymorphic_on is not None:
            polymorphic_on = adapter.columns[polymorphic_on]
        if version_id_col is not None:
            version_id_col = adapter.columns[version_id_col]

    identity_class = mapper._identity_class

    new_populators = []
    existing_populators = []
    eager_populators = []

    load_path = context.query._current_path + path \
                if context.query._current_path.path \
                else path

    def populate_state(state, dict_, row, isnew, only_load_props):
        if isnew:
            if context.propagate_options:
                state.load_options = context.propagate_options
            if state.load_options:
                state.load_path = load_path

        if not new_populators:
            _populators(mapper, context, path, row, adapter,
                            new_populators,
                            existing_populators,
                            eager_populators
            )

        if isnew:
            populators = new_populators
        else:
            populators = existing_populators

        if only_load_props is None:
            for key, populator in populators:
                populator(state, dict_, row)
        elif only_load_props:
            for key, populator in populators:
                if key in only_load_props:
                    populator(state, dict_, row)

    session_identity_map = context.session.identity_map

    listeners = mapper.dispatch

    translate_row = listeners.translate_row or None
    create_instance = listeners.create_instance or None
    populate_instance = listeners.populate_instance or None
    append_result = listeners.append_result or None
    populate_existing = context.populate_existing or mapper.always_refresh
    invoke_all_eagers = context.invoke_all_eagers

    if mapper.allow_partial_pks:
        is_not_primary_key = _none_set.issuperset
    else:
        is_not_primary_key = _none_set.issubset

    def _instance(row, result):
        if not new_populators and invoke_all_eagers:
            _populators(mapper, context, path, row, adapter,
                            new_populators,
                            existing_populators,
                            eager_populators
            )

        if translate_row:
            for fn in translate_row:
                ret = fn(mapper, context, row)
                if ret is not EXT_CONTINUE:
                    row = ret
                    break

        if polymorphic_on is not None:
            discriminator = row[polymorphic_on]
            if discriminator is not None:
                _instance = polymorphic_instances[discriminator]
                if _instance:
                    return _instance(row, result)

        # determine identity key
        if refresh_state:
            identitykey = refresh_state.key
            if identitykey is None:
                # super-rare condition; a refresh is being called
                # on a non-instance-key instance; this is meant to only
                # occur within a flush()
                identitykey = mapper._identity_key_from_state(refresh_state)
        else:
            identitykey = (
                            identity_class,
                            tuple([row[column] for column in pk_cols])
                        )

        instance = session_identity_map.get(identitykey)
        if instance is not None:
            state = attributes.instance_state(instance)
            dict_ = attributes.instance_dict(instance)

            isnew = state.runid != context.runid
            currentload = not isnew
            loaded_instance = False

            if not currentload and \
                    version_id_col is not None and \
                    context.version_check and \
                    mapper._get_state_attr_by_column(
                            state,
                            dict_,
                            mapper.version_id_col) != \
                                    row[version_id_col]:

                raise orm_exc.StaleDataError(
                        "Instance '%s' has version id '%s' which "
                        "does not match database-loaded version id '%s'."
                        % (state_str(state),
                            mapper._get_state_attr_by_column(
                                        state, dict_,
                                        mapper.version_id_col),
                                row[version_id_col]))
        elif refresh_state:
            # out of band refresh_state detected (i.e. its not in the
            # session.identity_map) honor it anyway.  this can happen
            # if a _get() occurs within save_obj(), such as
            # when eager_defaults is True.
            state = refresh_state
            instance = state.obj()
            dict_ = attributes.instance_dict(instance)
            isnew = state.runid != context.runid
            currentload = True
            loaded_instance = False
        else:
            # check for non-NULL values in the primary key columns,
            # else no entity is returned for the row
            if is_not_primary_key(identitykey[1]):
                return None

            isnew = True
            currentload = True
            loaded_instance = True

            if create_instance:
                for fn in create_instance:
                    instance = fn(mapper, context,
                                        row, mapper.class_)
                    if instance is not EXT_CONTINUE:
                        manager = attributes.manager_of_class(
                                                instance.__class__)
                        # TODO: if manager is None, raise a friendly error
                        # about returning instances of unmapped types
                        manager.setup_instance(instance)
                        break
                else:
                    instance = mapper.class_manager.new_instance()
            else:
                instance = mapper.class_manager.new_instance()

            dict_ = attributes.instance_dict(instance)
            state = attributes.instance_state(instance)
            state.key = identitykey

            # attach instance to session.
            state.session_id = context.session.hash_key
            session_identity_map.add(state)

        if currentload or populate_existing:
            # state is being fully loaded, so populate.
            # add to the "context.progress" collection.
            if isnew:
                state.runid = context.runid
                context.progress[state] = dict_

            if populate_instance:
                for fn in populate_instance:
                    ret = fn(mapper, context, row, state,
                        only_load_props=only_load_props,
                        instancekey=identitykey, isnew=isnew)
                    if ret is not EXT_CONTINUE:
                        break
                else:
                    populate_state(state, dict_, row, isnew, only_load_props)
            else:
                populate_state(state, dict_, row, isnew, only_load_props)

            if loaded_instance:
                state.manager.dispatch.load(state, context)
            elif isnew:
                state.manager.dispatch.refresh(state, context, only_load_props)

        elif state in context.partials or state.unloaded or eager_populators:
            # state is having a partial set of its attributes
            # refreshed.  Populate those attributes,
            # and add to the "context.partials" collection.
            if state in context.partials:
                isnew = False
                (d_, attrs) = context.partials[state]
            else:
                isnew = True
                attrs = state.unloaded
                context.partials[state] = (dict_, attrs)

            if populate_instance:
                for fn in populate_instance:
                    ret = fn(mapper, context, row, state,
                        only_load_props=attrs,
                        instancekey=identitykey, isnew=isnew)
                    if ret is not EXT_CONTINUE:
                        break
                else:
                    populate_state(state, dict_, row, isnew, attrs)
            else:
                populate_state(state, dict_, row, isnew, attrs)

            for key, pop in eager_populators:
                if key not in state.unloaded:
                    pop(state, dict_, row)

            if isnew:
                state.manager.dispatch.refresh(state, context, attrs)

        if result is not None:
            if append_result:
                for fn in append_result:
                    if fn(mapper, context, row, state,
                                result, instancekey=identitykey,
                                isnew=isnew) is not EXT_CONTINUE:
                        break
                else:
                    result.append(instance)
            else:
                result.append(instance)

        return instance
    return _instance


def _populators(mapper, context, path, row, adapter,
        new_populators, existing_populators, eager_populators):
    """Produce a collection of attribute level row processor
    callables."""

    delayed_populators = []
    pops = (new_populators, existing_populators, delayed_populators,
                        eager_populators)

    for prop in mapper._props.itervalues():

        for i, pop in enumerate(prop.create_row_processor(
                                    context,
                                    path,
                                    mapper, row, adapter)):
            if pop is not None:
                pops[i].append((prop.key, pop))

    if delayed_populators:
        new_populators.extend(delayed_populators)


def _configure_subclass_mapper(mapper, context, path, adapter):
    """Produce a mapper level row processor callable factory for mappers
    inheriting this one."""

    def configure_subclass_mapper(discriminator):
        try:
            sub_mapper = mapper.polymorphic_map[discriminator]
        except KeyError:
            raise AssertionError(
                    "No such polymorphic_identity %r is defined" %
                    discriminator)
        if sub_mapper is mapper:
            return None

        return instance_processor(
                            sub_mapper,
                            context,
                            path,
                            adapter,
                            polymorphic_from=mapper)
    return configure_subclass_mapper


def load_scalar_attributes(mapper, state, attribute_names):
    """initiate a column-based attribute refresh operation."""

    #assert mapper is _state_mapper(state)
    session = sessionlib._state_session(state)
    if not session:
        raise orm_exc.DetachedInstanceError(
                    "Instance %s is not bound to a Session; "
                    "attribute refresh operation cannot proceed" %
                    (state_str(state)))

    has_key = bool(state.key)

    result = False

    if mapper.inherits and not mapper.concrete:
        statement = mapper._optimized_get_statement(state, attribute_names)
        if statement is not None:
            result = load_on_ident(
                        session.query(mapper).from_statement(statement),
                            None,
                            only_load_props=attribute_names,
                            refresh_state=state
                        )

    if result is False:
        if has_key:
            identity_key = state.key
        else:
            # this codepath is rare - only valid when inside a flush, and the
            # object is becoming persistent but hasn't yet been assigned
            # an identity_key.
            # check here to ensure we have the attrs we need.
            pk_attrs = [mapper._columntoproperty[col].key
                        for col in mapper.primary_key]
            if state.expired_attributes.intersection(pk_attrs):
                raise sa_exc.InvalidRequestError(
                            "Instance %s cannot be refreshed - it's not "
                            " persistent and does not "
                            "contain a full primary key." % state_str(state))
            identity_key = mapper._identity_key_from_state(state)

        if (_none_set.issubset(identity_key) and \
                not mapper.allow_partial_pks) or \
                _none_set.issuperset(identity_key):
            util.warn("Instance %s to be refreshed doesn't "
                        "contain a full primary key - can't be refreshed "
                        "(and shouldn't be expired, either)."
                        % state_str(state))
            return

        result = load_on_ident(
                    session.query(mapper),
                                identity_key,
                                refresh_state=state,
                                only_load_props=attribute_names)

    # if instance is pending, a refresh operation
    # may not complete (even if PK attributes are assigned)
    if has_key and result is None:
        raise orm_exc.ObjectDeletedError(state)
