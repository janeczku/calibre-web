# orm/persistence.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""private module containing functions used to emit INSERT, UPDATE
and DELETE statements on behalf of a :class:`.Mapper` and its descending
mappers.

The functions here are called only by the unit of work functions
in unitofwork.py.

"""

import operator
from itertools import groupby
from .. import sql, util, exc as sa_exc, schema
from . import attributes, sync, exc as orm_exc, evaluator
from .util import _state_mapper, state_str, _attr_as_key
from ..sql import expression
from . import loading


def save_obj(base_mapper, states, uowtransaction, single=False):
    """Issue ``INSERT`` and/or ``UPDATE`` statements for a list
    of objects.

    This is called within the context of a UOWTransaction during a
    flush operation, given a list of states to be flushed.  The
    base mapper in an inheritance hierarchy handles the inserts/
    updates for all descendant mappers.

    """

    # if batch=false, call _save_obj separately for each object
    if not single and not base_mapper.batch:
        for state in _sort_states(states):
            save_obj(base_mapper, [state], uowtransaction, single=True)
        return

    states_to_insert, states_to_update = _organize_states_for_save(
                                                base_mapper,
                                                states,
                                                uowtransaction)

    cached_connections = _cached_connection_dict(base_mapper)

    for table, mapper in base_mapper._sorted_tables.iteritems():
        insert = _collect_insert_commands(base_mapper, uowtransaction,
                                table, states_to_insert)

        update = _collect_update_commands(base_mapper, uowtransaction,
                                table, states_to_update)

        if update:
            _emit_update_statements(base_mapper, uowtransaction,
                                    cached_connections,
                                    mapper, table, update)

        if insert:
            _emit_insert_statements(base_mapper, uowtransaction,
                                    cached_connections,
                                    table, insert)

    _finalize_insert_update_commands(base_mapper, uowtransaction,
                                    states_to_insert, states_to_update)


def post_update(base_mapper, states, uowtransaction, post_update_cols):
    """Issue UPDATE statements on behalf of a relationship() which
    specifies post_update.

    """
    cached_connections = _cached_connection_dict(base_mapper)

    states_to_update = _organize_states_for_post_update(
                                    base_mapper,
                                    states, uowtransaction)

    for table, mapper in base_mapper._sorted_tables.iteritems():
        update = _collect_post_update_commands(base_mapper, uowtransaction,
                                            table, states_to_update,
                                            post_update_cols)

        if update:
            _emit_post_update_statements(base_mapper, uowtransaction,
                                    cached_connections,
                                    mapper, table, update)


def delete_obj(base_mapper, states, uowtransaction):
    """Issue ``DELETE`` statements for a list of objects.

    This is called within the context of a UOWTransaction during a
    flush operation.

    """

    cached_connections = _cached_connection_dict(base_mapper)

    states_to_delete = _organize_states_for_delete(
                                        base_mapper,
                                        states,
                                        uowtransaction)

    table_to_mapper = base_mapper._sorted_tables

    for table in reversed(table_to_mapper.keys()):
        delete = _collect_delete_commands(base_mapper, uowtransaction,
                                table, states_to_delete)

        mapper = table_to_mapper[table]

        _emit_delete_statements(base_mapper, uowtransaction,
                    cached_connections, mapper, table, delete)

    for state, state_dict, mapper, has_identity, connection \
                        in states_to_delete:
        mapper.dispatch.after_delete(mapper, connection, state)


def _organize_states_for_save(base_mapper, states, uowtransaction):
    """Make an initial pass across a set of states for INSERT or
    UPDATE.

    This includes splitting out into distinct lists for
    each, calling before_insert/before_update, obtaining
    key information for each state including its dictionary,
    mapper, the connection to use for the execution per state,
    and the identity flag.

    """

    states_to_insert = []
    states_to_update = []

    for state, dict_, mapper, connection in _connections_for_states(
                                            base_mapper, uowtransaction,
                                            states):

        has_identity = bool(state.key)
        instance_key = state.key or mapper._identity_key_from_state(state)

        row_switch = None

        # call before_XXX extensions
        if not has_identity:
            mapper.dispatch.before_insert(mapper, connection, state)
        else:
            mapper.dispatch.before_update(mapper, connection, state)

        if mapper._validate_polymorphic_identity:
            mapper._validate_polymorphic_identity(mapper, state, dict_)

        # detect if we have a "pending" instance (i.e. has
        # no instance_key attached to it), and another instance
        # with the same identity key already exists as persistent.
        # convert to an UPDATE if so.
        if not has_identity and \
                instance_key in uowtransaction.session.identity_map:
            instance = \
                uowtransaction.session.identity_map[instance_key]
            existing = attributes.instance_state(instance)
            if not uowtransaction.is_deleted(existing):
                raise orm_exc.FlushError(
                    "New instance %s with identity key %s conflicts "
                    "with persistent instance %s" %
                    (state_str(state), instance_key,
                     state_str(existing)))

            base_mapper._log_debug(
                "detected row switch for identity %s.  "
                "will update %s, remove %s from "
                "transaction", instance_key,
                state_str(state), state_str(existing))

            # remove the "delete" flag from the existing element
            uowtransaction.remove_state_actions(existing)
            row_switch = existing

        if not has_identity and not row_switch:
            states_to_insert.append(
                (state, dict_, mapper, connection,
                has_identity, instance_key, row_switch)
            )
        else:
            states_to_update.append(
                (state, dict_, mapper, connection,
                has_identity, instance_key, row_switch)
            )

    return states_to_insert, states_to_update


def _organize_states_for_post_update(base_mapper, states,
                                                uowtransaction):
    """Make an initial pass across a set of states for UPDATE
    corresponding to post_update.

    This includes obtaining key information for each state
    including its dictionary, mapper, the connection to use for
    the execution per state.

    """
    return list(_connections_for_states(base_mapper, uowtransaction,
                                            states))


def _organize_states_for_delete(base_mapper, states, uowtransaction):
    """Make an initial pass across a set of states for DELETE.

    This includes calling out before_delete and obtaining
    key information for each state including its dictionary,
    mapper, the connection to use for the execution per state.

    """
    states_to_delete = []

    for state, dict_, mapper, connection in _connections_for_states(
                                            base_mapper, uowtransaction,
                                            states):

        mapper.dispatch.before_delete(mapper, connection, state)

        states_to_delete.append((state, dict_, mapper,
                bool(state.key), connection))
    return states_to_delete


def _collect_insert_commands(base_mapper, uowtransaction, table,
                                                states_to_insert):
    """Identify sets of values to use in INSERT statements for a
    list of states.

    """
    insert = []
    for state, state_dict, mapper, connection, has_identity, \
                    instance_key, row_switch in states_to_insert:
        if table not in mapper._pks_by_table:
            continue

        pks = mapper._pks_by_table[table]

        params = {}
        value_params = {}

        has_all_pks = True
        for col in mapper._cols_by_table[table]:
            if col is mapper.version_id_col:
                params[col.key] = mapper.version_id_generator(None)
            else:
                # pull straight from the dict for
                # pending objects
                prop = mapper._columntoproperty[col]
                value = state_dict.get(prop.key, None)

                if value is None:
                    if col in pks:
                        has_all_pks = False
                    elif col.default is None and \
                         col.server_default is None:
                        params[col.key] = value

                elif isinstance(value, sql.ClauseElement):
                    value_params[col] = value
                else:
                    params[col.key] = value

        insert.append((state, state_dict, params, mapper,
                        connection, value_params, has_all_pks))
    return insert


def _collect_update_commands(base_mapper, uowtransaction,
                                table, states_to_update):
    """Identify sets of values to use in UPDATE statements for a
    list of states.

    This function works intricately with the history system
    to determine exactly what values should be updated
    as well as how the row should be matched within an UPDATE
    statement.  Includes some tricky scenarios where the primary
    key of an object might have been changed.

    """

    update = []
    for state, state_dict, mapper, connection, has_identity, \
                    instance_key, row_switch in states_to_update:
        if table not in mapper._pks_by_table:
            continue

        pks = mapper._pks_by_table[table]

        params = {}
        value_params = {}

        hasdata = hasnull = False
        for col in mapper._cols_by_table[table]:
            if col is mapper.version_id_col:
                params[col._label] = \
                    mapper._get_committed_state_attr_by_column(
                                    row_switch or state,
                                    row_switch and row_switch.dict
                                                or state_dict,
                                    col)

                prop = mapper._columntoproperty[col]
                history = attributes.get_state_history(
                    state, prop.key,
                    attributes.PASSIVE_NO_INITIALIZE
                )
                if history.added:
                    params[col.key] = history.added[0]
                    hasdata = True
                else:
                    params[col.key] = mapper.version_id_generator(
                                                params[col._label])

                    # HACK: check for history, in case the
                    # history is only
                    # in a different table than the one
                    # where the version_id_col is.
                    for prop in mapper._columntoproperty.itervalues():
                        history = attributes.get_state_history(
                                state, prop.key,
                                attributes.PASSIVE_NO_INITIALIZE)
                        if history.added:
                            hasdata = True
            else:
                prop = mapper._columntoproperty[col]
                history = attributes.get_state_history(
                                state, prop.key,
                                attributes.PASSIVE_NO_INITIALIZE)
                if history.added:
                    if isinstance(history.added[0],
                                    sql.ClauseElement):
                        value_params[col] = history.added[0]
                    else:
                        value = history.added[0]
                        params[col.key] = value

                    if col in pks:
                        if history.deleted and \
                            not row_switch:
                            # if passive_updates and sync detected
                            # this was a  pk->pk sync, use the new
                            # value to locate the row, since the
                            # DB would already have set this
                            if ("pk_cascaded", state, col) in \
                                            uowtransaction.attributes:
                                value = history.added[0]
                                params[col._label] = value
                            else:
                                # use the old value to
                                # locate the row
                                value = history.deleted[0]
                                params[col._label] = value
                            hasdata = True
                        else:
                            # row switch logic can reach us here
                            # remove the pk from the update params
                            # so the update doesn't
                            # attempt to include the pk in the
                            # update statement
                            del params[col.key]
                            value = history.added[0]
                            params[col._label] = value
                        if value is None:
                            hasnull = True
                    else:
                        hasdata = True
                elif col in pks:
                    value = state.manager[prop.key].impl.get(
                                                    state, state_dict)
                    if value is None:
                        hasnull = True
                    params[col._label] = value
        if hasdata:
            if hasnull:
                raise orm_exc.FlushError(
                            "Can't update table "
                            "using NULL for primary "
                            "key value")
            update.append((state, state_dict, params, mapper,
                            connection, value_params))
    return update


def _collect_post_update_commands(base_mapper, uowtransaction, table,
                        states_to_update, post_update_cols):
    """Identify sets of values to use in UPDATE statements for a
    list of states within a post_update operation.

    """

    update = []
    for state, state_dict, mapper, connection in states_to_update:
        if table not in mapper._pks_by_table:
            continue
        pks = mapper._pks_by_table[table]
        params = {}
        hasdata = False

        for col in mapper._cols_by_table[table]:
            if col in pks:
                params[col._label] = \
                        mapper._get_state_attr_by_column(
                                        state,
                                        state_dict, col)
            elif col in post_update_cols:
                prop = mapper._columntoproperty[col]
                history = attributes.get_state_history(
                            state, prop.key,
                            attributes.PASSIVE_NO_INITIALIZE)
                if history.added:
                    value = history.added[0]
                    params[col.key] = value
                    hasdata = True
        if hasdata:
            update.append((state, state_dict, params, mapper,
                            connection))
    return update


def _collect_delete_commands(base_mapper, uowtransaction, table,
                                states_to_delete):
    """Identify values to use in DELETE statements for a list of
    states to be deleted."""

    delete = util.defaultdict(list)

    for state, state_dict, mapper, has_identity, connection \
                                        in states_to_delete:
        if not has_identity or table not in mapper._pks_by_table:
            continue

        params = {}
        delete[connection].append(params)
        for col in mapper._pks_by_table[table]:
            params[col.key] = \
                    value = \
                    mapper._get_state_attr_by_column(
                                    state, state_dict, col)
            if value is None:
                raise orm_exc.FlushError(
                            "Can't delete from table "
                            "using NULL for primary "
                            "key value")

        if mapper.version_id_col is not None and \
                    table.c.contains_column(mapper.version_id_col):
            params[mapper.version_id_col.key] = \
                        mapper._get_committed_state_attr_by_column(
                                state, state_dict,
                                mapper.version_id_col)
    return delete


def _emit_update_statements(base_mapper, uowtransaction,
                        cached_connections, mapper, table, update):
    """Emit UPDATE statements corresponding to value lists collected
    by _collect_update_commands()."""

    needs_version_id = mapper.version_id_col is not None and \
                table.c.contains_column(mapper.version_id_col)

    def update_stmt():
        clause = sql.and_()

        for col in mapper._pks_by_table[table]:
            clause.clauses.append(col == sql.bindparam(col._label,
                                            type_=col.type))

        if needs_version_id:
            clause.clauses.append(mapper.version_id_col ==\
                    sql.bindparam(mapper.version_id_col._label,
                                    type_=mapper.version_id_col.type))

        return table.update(clause)

    statement = base_mapper._memo(('update', table), update_stmt)

    rows = 0
    for state, state_dict, params, mapper, \
                connection, value_params in update:

        if value_params:
            c = connection.execute(
                                statement.values(value_params),
                                params)
        else:
            c = cached_connections[connection].\
                                execute(statement, params)

        _postfetch(
                mapper,
                uowtransaction,
                table,
                state,
                state_dict,
                c.context.prefetch_cols,
                c.context.postfetch_cols,
                c.context.compiled_parameters[0],
                value_params)
        rows += c.rowcount

    if connection.dialect.supports_sane_rowcount:
        if rows != len(update):
            raise orm_exc.StaleDataError(
                    "UPDATE statement on table '%s' expected to "
                    "update %d row(s); %d were matched." %
                    (table.description, len(update), rows))

    elif needs_version_id:
        util.warn("Dialect %s does not support updated rowcount "
                "- versioning cannot be verified." %
                c.dialect.dialect_description,
                stacklevel=12)


def _emit_insert_statements(base_mapper, uowtransaction,
                        cached_connections, table, insert):
    """Emit INSERT statements corresponding to value lists collected
    by _collect_insert_commands()."""

    statement = base_mapper._memo(('insert', table), table.insert)

    for (connection, pkeys, hasvalue, has_all_pks), \
        records in groupby(insert,
                            lambda rec: (rec[4],
                                    rec[2].keys(),
                                    bool(rec[5]),
                                    rec[6])
    ):
        if has_all_pks and not hasvalue:
            records = list(records)
            multiparams = [rec[2] for rec in records]
            c = cached_connections[connection].\
                                execute(statement, multiparams)

            for (state, state_dict, params, mapper,
                    conn, value_params, has_all_pks), \
                    last_inserted_params in \
                    zip(records, c.context.compiled_parameters):
                _postfetch(
                        mapper,
                        uowtransaction,
                        table,
                        state,
                        state_dict,
                        c.context.prefetch_cols,
                        c.context.postfetch_cols,
                        last_inserted_params,
                        value_params)

        else:
            for state, state_dict, params, mapper, \
                        connection, value_params, \
                        has_all_pks in records:

                if value_params:
                    result = connection.execute(
                                statement.values(value_params),
                                params)
                else:
                    result = cached_connections[connection].\
                                        execute(statement, params)

                primary_key = result.context.inserted_primary_key

                if primary_key is not None:
                    # set primary key attributes
                    for pk, col in zip(primary_key,
                                    mapper._pks_by_table[table]):
                        prop = mapper._columntoproperty[col]
                        if state_dict.get(prop.key) is None:
                            # TODO: would rather say:
                            #state_dict[prop.key] = pk
                            mapper._set_state_attr_by_column(
                                        state,
                                        state_dict,
                                        col, pk)

                _postfetch(
                        mapper,
                        uowtransaction,
                        table,
                        state,
                        state_dict,
                        result.context.prefetch_cols,
                        result.context.postfetch_cols,
                        result.context.compiled_parameters[0],
                        value_params)


def _emit_post_update_statements(base_mapper, uowtransaction,
                            cached_connections, mapper, table, update):
    """Emit UPDATE statements corresponding to value lists collected
    by _collect_post_update_commands()."""

    def update_stmt():
        clause = sql.and_()

        for col in mapper._pks_by_table[table]:
            clause.clauses.append(col == sql.bindparam(col._label,
                                            type_=col.type))

        return table.update(clause)

    statement = base_mapper._memo(('post_update', table), update_stmt)

    # execute each UPDATE in the order according to the original
    # list of states to guarantee row access order, but
    # also group them into common (connection, cols) sets
    # to support executemany().
    for key, grouper in groupby(
        update, lambda rec: (rec[4], rec[2].keys())
    ):
        connection = key[0]
        multiparams = [params for state, state_dict,
                                params, mapper, conn in grouper]
        cached_connections[connection].\
                            execute(statement, multiparams)


def _emit_delete_statements(base_mapper, uowtransaction, cached_connections,
                                    mapper, table, delete):
    """Emit DELETE statements corresponding to value lists collected
    by _collect_delete_commands()."""

    need_version_id = mapper.version_id_col is not None and \
        table.c.contains_column(mapper.version_id_col)

    def delete_stmt():
        clause = sql.and_()
        for col in mapper._pks_by_table[table]:
            clause.clauses.append(
                    col == sql.bindparam(col.key, type_=col.type))

        if need_version_id:
            clause.clauses.append(
                mapper.version_id_col ==
                sql.bindparam(
                        mapper.version_id_col.key,
                        type_=mapper.version_id_col.type
                )
            )

        return table.delete(clause)

    for connection, del_objects in delete.iteritems():
        statement = base_mapper._memo(('delete', table), delete_stmt)

        connection = cached_connections[connection]

        if need_version_id:
            # TODO: need test coverage for this [ticket:1761]
            if connection.dialect.supports_sane_rowcount:
                rows = 0
                # execute deletes individually so that versioned
                # rows can be verified
                for params in del_objects:
                    c = connection.execute(statement, params)
                    rows += c.rowcount
                if rows != len(del_objects):
                    raise orm_exc.StaleDataError(
                        "DELETE statement on table '%s' expected to "
                        "delete %d row(s); %d were matched." %
                        (table.description, len(del_objects), c.rowcount)
                    )
            else:
                util.warn(
                    "Dialect %s does not support deleted rowcount "
                    "- versioning cannot be verified." %
                    connection.dialect.dialect_description,
                    stacklevel=12)
                connection.execute(statement, del_objects)
        else:
            connection.execute(statement, del_objects)


def _finalize_insert_update_commands(base_mapper, uowtransaction,
                            states_to_insert, states_to_update):
    """finalize state on states that have been inserted or updated,
    including calling after_insert/after_update events.

    """
    for state, state_dict, mapper, connection, has_identity, \
                    instance_key, row_switch in states_to_insert + \
                                                    states_to_update:

        if mapper._readonly_props:
            readonly = state.unmodified_intersection(
                [p.key for p in mapper._readonly_props
                    if p.expire_on_flush or p.key not in state.dict]
            )
            if readonly:
                state._expire_attributes(state.dict, readonly)

        # if eager_defaults option is enabled,
        # refresh whatever has been expired.
        if base_mapper.eager_defaults and state.unloaded:
            state.key = base_mapper._identity_key_from_state(state)
            loading.load_on_ident(
                uowtransaction.session.query(base_mapper),
                state.key, refresh_state=state,
                only_load_props=state.unloaded)

        # call after_XXX extensions
        if not has_identity:
            mapper.dispatch.after_insert(mapper, connection, state)
        else:
            mapper.dispatch.after_update(mapper, connection, state)


def _postfetch(mapper, uowtransaction, table,
                state, dict_, prefetch_cols, postfetch_cols,
                            params, value_params):
    """Expire attributes in need of newly persisted database state,
    after an INSERT or UPDATE statement has proceeded for that
    state."""

    if mapper.version_id_col is not None:
        prefetch_cols = list(prefetch_cols) + [mapper.version_id_col]

    for c in prefetch_cols:
        if c.key in params and c in mapper._columntoproperty:
            mapper._set_state_attr_by_column(state, dict_, c, params[c.key])

    if postfetch_cols:
        state._expire_attributes(state.dict,
                            [mapper._columntoproperty[c].key
                            for c in postfetch_cols if c in
                            mapper._columntoproperty]
                        )

    # synchronize newly inserted ids from one table to the next
    # TODO: this still goes a little too often.  would be nice to
    # have definitive list of "columns that changed" here
    for m, equated_pairs in mapper._table_to_equated[table]:
        sync.populate(state, m, state, m,
                                        equated_pairs,
                                        uowtransaction,
                                        mapper.passive_updates)


def _connections_for_states(base_mapper, uowtransaction, states):
    """Return an iterator of (state, state.dict, mapper, connection).

    The states are sorted according to _sort_states, then paired
    with the connection they should be using for the given
    unit of work transaction.

    """
    # if session has a connection callable,
    # organize individual states with the connection
    # to use for update
    if uowtransaction.session.connection_callable:
        connection_callable = \
                uowtransaction.session.connection_callable
    else:
        connection = None
        connection_callable = None

    for state in _sort_states(states):
        if connection_callable:
            connection = connection_callable(base_mapper, state.obj())
        elif not connection:
            connection = uowtransaction.transaction.connection(
                                                    base_mapper)

        mapper = _state_mapper(state)

        yield state, state.dict, mapper, connection


def _cached_connection_dict(base_mapper):
    # dictionary of connection->connection_with_cache_options.
    return util.PopulateDict(
        lambda conn: conn.execution_options(
        compiled_cache=base_mapper._compiled_cache
    ))


def _sort_states(states):
    pending = set(states)
    persistent = set(s for s in pending if s.key is not None)
    pending.difference_update(persistent)
    return sorted(pending, key=operator.attrgetter("insert_order")) + \
                sorted(persistent, key=lambda q: q.key[1])


class BulkUD(object):
    """Handle bulk update and deletes via a :class:`.Query`."""

    def __init__(self, query):
        self.query = query.enable_eagerloads(False)

    @classmethod
    def _factory(cls, lookup, synchronize_session, *arg):
        try:
            klass = lookup[synchronize_session]
        except KeyError:
            raise sa_exc.ArgumentError(
                            "Valid strategies for session synchronization "
                            "are %s" % (", ".join(sorted(repr(x)
                                for x in lookup.keys()))))
        else:
            return klass(*arg)

    def exec_(self):
        self._do_pre()
        self._do_pre_synchronize()
        self._do_exec()
        self._do_post_synchronize()
        self._do_post()

    def _do_pre(self):
        query = self.query
        self.context = context = query._compile_context()
        if len(context.statement.froms) != 1 or \
                    not isinstance(context.statement.froms[0], schema.Table):

            self.primary_table = query._only_entity_zero(
                    "This operation requires only one Table or "
                    "entity be specified as the target."
                ).mapper.local_table
        else:
            self.primary_table = context.statement.froms[0]

        session = query.session

        if query._autoflush:
            session._autoflush()

    def _do_pre_synchronize(self):
        pass

    def _do_post_synchronize(self):
        pass


class BulkEvaluate(BulkUD):
    """BulkUD which does the 'evaluate' method of session state resolution."""

    def _additional_evaluators(self, evaluator_compiler):
        pass

    def _do_pre_synchronize(self):
        query = self.query
        try:
            evaluator_compiler = evaluator.EvaluatorCompiler()
            if query.whereclause is not None:
                eval_condition = evaluator_compiler.process(
                                                query.whereclause)
            else:
                def eval_condition(obj):
                    return True

            self._additional_evaluators(evaluator_compiler)

        except evaluator.UnevaluatableError:
            raise sa_exc.InvalidRequestError(
                    "Could not evaluate current criteria in Python. "
                    "Specify 'fetch' or False for the "
                    "synchronize_session parameter.")
        target_cls = query._mapper_zero().class_

        #TODO: detect when the where clause is a trivial primary key match
        self.matched_objects = [
                            obj for (cls, pk), obj in
                            query.session.identity_map.iteritems()
                            if issubclass(cls, target_cls) and
                            eval_condition(obj)]


class BulkFetch(BulkUD):
    """BulkUD which does the 'fetch' method of session state resolution."""

    def _do_pre_synchronize(self):
        query = self.query
        session = query.session
        select_stmt = self.context.statement.with_only_columns(
                                            self.primary_table.primary_key)
        self.matched_rows = session.execute(
                                    select_stmt,
                                    params=query._params).fetchall()


class BulkUpdate(BulkUD):
    """BulkUD which handles UPDATEs."""

    def __init__(self, query, values):
        super(BulkUpdate, self).__init__(query)
        self.query._no_select_modifiers("update")
        self.values = values

    @classmethod
    def factory(cls, query, synchronize_session, values):
        return BulkUD._factory({
            "evaluate": BulkUpdateEvaluate,
            "fetch": BulkUpdateFetch,
            False: BulkUpdate
        }, synchronize_session, query, values)

    def _do_exec(self):
        update_stmt = sql.update(self.primary_table,
                            self.context.whereclause, self.values)

        self.result = self.query.session.execute(
                            update_stmt, params=self.query._params)
        self.rowcount = self.result.rowcount

    def _do_post(self):
        session = self.query.session
        session.dispatch.after_bulk_update(session, self.query,
                                self.context, self.result)


class BulkDelete(BulkUD):
    """BulkUD which handles DELETEs."""

    def __init__(self, query):
        super(BulkDelete, self).__init__(query)
        self.query._no_select_modifiers("delete")

    @classmethod
    def factory(cls, query, synchronize_session):
        return BulkUD._factory({
            "evaluate": BulkDeleteEvaluate,
            "fetch": BulkDeleteFetch,
            False: BulkDelete
        }, synchronize_session, query)

    def _do_exec(self):
        delete_stmt = sql.delete(self.primary_table,
                                    self.context.whereclause)

        self.result = self.query.session.execute(delete_stmt,
                                    params=self.query._params)
        self.rowcount = self.result.rowcount

    def _do_post(self):
        session = self.query.session
        session.dispatch.after_bulk_delete(session, self.query,
                        self.context, self.result)


class BulkUpdateEvaluate(BulkEvaluate, BulkUpdate):
    """BulkUD which handles UPDATEs using the "evaluate"
    method of session resolution."""

    def _additional_evaluators(self, evaluator_compiler):
        self.value_evaluators = {}
        for key, value in self.values.iteritems():
            key = _attr_as_key(key)
            self.value_evaluators[key] = evaluator_compiler.process(
                                expression._literal_as_binds(value))

    def _do_post_synchronize(self):
        session = self.query.session
        states = set()
        evaluated_keys = self.value_evaluators.keys()
        for obj in self.matched_objects:
            state, dict_ = attributes.instance_state(obj),\
                                    attributes.instance_dict(obj)

            # only evaluate unmodified attributes
            to_evaluate = state.unmodified.intersection(
                                                    evaluated_keys)
            for key in to_evaluate:
                dict_[key] = self.value_evaluators[key](obj)

            state._commit(dict_, list(to_evaluate))

            # expire attributes with pending changes
            # (there was no autoflush, so they are overwritten)
            state._expire_attributes(dict_,
                            set(evaluated_keys).
                                difference(to_evaluate))
            states.add(state)
        session._register_altered(states)


class BulkDeleteEvaluate(BulkEvaluate, BulkDelete):
    """BulkUD which handles DELETEs using the "evaluate"
    method of session resolution."""

    def _do_post_synchronize(self):
        self.query.session._remove_newly_deleted(
                [attributes.instance_state(obj)
                    for obj in self.matched_objects])


class BulkUpdateFetch(BulkFetch, BulkUpdate):
    """BulkUD which handles UPDATEs using the "fetch"
    method of session resolution."""

    def _do_post_synchronize(self):
        session = self.query.session
        target_mapper = self.query._mapper_zero()

        states = set([
            attributes.instance_state(session.identity_map[identity_key])
            for identity_key in [
                target_mapper.identity_key_from_primary_key(
                                                        list(primary_key))
                for primary_key in self.matched_rows
            ]
            if identity_key in session.identity_map
        ])
        attrib = [_attr_as_key(k) for k in self.values]
        for state in states:
            session._expire_state(state, attrib)
        session._register_altered(states)


class BulkDeleteFetch(BulkFetch, BulkDelete):
    """BulkUD which handles DELETEs using the "fetch"
    method of session resolution."""

    def _do_post_synchronize(self):
        session = self.query.session
        target_mapper = self.query._mapper_zero()
        for primary_key in self.matched_rows:
            # TODO: inline this and call remove_newly_deleted
            # once
            identity_key = target_mapper.identity_key_from_primary_key(
                                                        list(primary_key))
            if identity_key in session.identity_map:
                session._remove_newly_deleted(
                    [attributes.instance_state(
                        session.identity_map[identity_key]
                    )]
                )
