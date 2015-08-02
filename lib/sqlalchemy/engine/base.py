# engine/base.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php


"""Defines :class:`.Connection` and :class:`.Engine`.

"""

from __future__ import with_statement
import sys
from .. import exc, schema, util, log, interfaces
from ..sql import expression, util as sql_util
from .interfaces import Connectable, Compiled
from .util import _distill_params
import contextlib


class Connection(Connectable):
    """Provides high-level functionality for a wrapped DB-API connection.

    Provides execution support for string-based SQL statements as well as
    :class:`.ClauseElement`, :class:`.Compiled` and :class:`.DefaultGenerator`
    objects. Provides a :meth:`begin` method to return :class:`.Transaction`
    objects.

    The Connection object is **not** thread-safe.  While a Connection can be
    shared among threads using properly synchronized access, it is still
    possible that the underlying DBAPI connection may not support shared
    access between threads.  Check the DBAPI documentation for details.

    The Connection object represents a single dbapi connection checked out
    from the connection pool. In this state, the connection pool has no affect
    upon the connection, including its expiration or timeout state. For the
    connection pool to properly manage connections, connections should be
    returned to the connection pool (i.e. ``connection.close()``) whenever the
    connection is not in use.

    .. index::
      single: thread safety; Connection

    """

    def __init__(self, engine, connection=None, close_with_result=False,
                 _branch=False, _execution_options=None,
                 _dispatch=None,
                 _has_events=False):
        """Construct a new Connection.

        The constructor here is not public and is only called only by an
        :class:`.Engine`. See :meth:`.Engine.connect` and
        :meth:`.Engine.contextual_connect` methods.

        """
        self.engine = engine
        self.dialect = engine.dialect
        self.__connection = connection or engine.raw_connection()
        self.__transaction = None
        self.should_close_with_result = close_with_result
        self.__savepoint_seq = 0
        self.__branch = _branch
        self.__invalid = False
        self.__can_reconnect = True
        if _dispatch:
            self.dispatch = _dispatch
        elif engine._has_events:
            self.dispatch = self.dispatch._join(engine.dispatch)
        self._has_events = _has_events or engine._has_events

        self._echo = self.engine._should_log_info()
        if _execution_options:
            self._execution_options =\
                engine._execution_options.union(_execution_options)
        else:
            self._execution_options = engine._execution_options

    def _branch(self):
        """Return a new Connection which references this Connection's
        engine and connection; but does not have close_with_result enabled,
        and also whose close() method does nothing.

        This is used to execute "sub" statements within a single execution,
        usually an INSERT statement.
        """

        return self.engine._connection_cls(
                                self.engine,
                                self.__connection,
                                _branch=True,
                                _has_events=self._has_events,
                                _dispatch=self.dispatch)

    def _clone(self):
        """Create a shallow copy of this Connection.

        """
        c = self.__class__.__new__(self.__class__)
        c.__dict__ = self.__dict__.copy()
        return c

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def execution_options(self, **opt):
        """ Set non-SQL options for the connection which take effect
        during execution.

        The method returns a copy of this :class:`.Connection` which references
        the same underlying DBAPI connection, but also defines the given
        execution options which will take effect for a call to
        :meth:`execute`. As the new :class:`.Connection` references the same
        underlying resource, it's usually a good idea to ensure that the copies
        would be discarded immediately, which is implicit if used as in::

            result = connection.execution_options(stream_results=True).\\
                                execute(stmt)

        Note that any key/value can be passed to
        :meth:`.Connection.execution_options`, and it will be stored in the
        ``_execution_options`` dictionary of the :class:`.Connection`.   It
        is suitable for usage by end-user schemes to communicate with
        event listeners, for example.

        The keywords that are currently recognized by SQLAlchemy itself
        include all those listed under :meth:`.Executable.execution_options`,
        as well as others that are specific to :class:`.Connection`.

        :param autocommit: Available on: Connection, statement.
          When True, a COMMIT will be invoked after execution
          when executed in 'autocommit' mode, i.e. when an explicit
          transaction is not begun on the connection. Note that DBAPI
          connections by default are always in a transaction - SQLAlchemy uses
          rules applied to different kinds of statements to determine if
          COMMIT will be invoked in order to provide its "autocommit" feature.
          Typically, all INSERT/UPDATE/DELETE statements as well as
          CREATE/DROP statements have autocommit behavior enabled; SELECT
          constructs do not. Use this option when invoking a SELECT or other
          specific SQL construct where COMMIT is desired (typically when
          calling stored procedures and such), and an explicit
          transaction is not in progress.

        :param compiled_cache: Available on: Connection.
          A dictionary where :class:`.Compiled` objects
          will be cached when the :class:`.Connection` compiles a clause
          expression into a :class:`.Compiled` object.
          It is the user's responsibility to
          manage the size of this dictionary, which will have keys
          corresponding to the dialect, clause element, the column
          names within the VALUES or SET clause of an INSERT or UPDATE,
          as well as the "batch" mode for an INSERT or UPDATE statement.
          The format of this dictionary is not guaranteed to stay the
          same in future releases.

          Note that the ORM makes use of its own "compiled" caches for
          some operations, including flush operations.  The caching
          used by the ORM internally supersedes a cache dictionary
          specified here.

        :param isolation_level: Available on: Connection.
          Set the transaction isolation level for
          the lifespan of this connection.   Valid values include
          those string values accepted by the ``isolation_level``
          parameter passed to :func:`.create_engine`, and are
          database specific, including those for :ref:`sqlite_toplevel`,
          :ref:`postgresql_toplevel` - see those dialect's documentation
          for further info.

          Note that this option necessarily affects the underlying
          DBAPI connection for the lifespan of the originating
          :class:`.Connection`, and is not per-execution. This
          setting is not removed until the underlying DBAPI connection
          is returned to the connection pool, i.e.
          the :meth:`.Connection.close` method is called.

        :param no_parameters: When ``True``, if the final parameter
          list or dictionary is totally empty, will invoke the
          statement on the cursor as ``cursor.execute(statement)``,
          not passing the parameter collection at all.
          Some DBAPIs such as psycopg2 and mysql-python consider
          percent signs as significant only when parameters are
          present; this option allows code to generate SQL
          containing percent signs (and possibly other characters)
          that is neutral regarding whether it's executed by the DBAPI
          or piped into a script that's later invoked by
          command line tools.

          .. versionadded:: 0.7.6

        :param stream_results: Available on: Connection, statement.
          Indicate to the dialect that results should be
          "streamed" and not pre-buffered, if possible.  This is a limitation
          of many DBAPIs.  The flag is currently understood only by the
          psycopg2 dialect.

        """
        c = self._clone()
        c._execution_options = c._execution_options.union(opt)
        if 'isolation_level' in opt:
            c._set_isolation_level()
        return c

    def _set_isolation_level(self):
        self.dialect.set_isolation_level(self.connection,
                                self._execution_options['isolation_level'])
        self.connection._connection_record.finalize_callback = \
                    self.dialect.reset_isolation_level

    @property
    def closed(self):
        """Return True if this connection is closed."""

        return '_Connection__connection' not in self.__dict__ \
            and not self.__can_reconnect

    @property
    def invalidated(self):
        """Return True if this connection was invalidated."""

        return self.__invalid

    @property
    def connection(self):
        "The underlying DB-API connection managed by this Connection."

        try:
            return self.__connection
        except AttributeError:
            return self._revalidate_connection()

    def _revalidate_connection(self):
        if self.__can_reconnect and self.__invalid:
            if self.__transaction is not None:
                raise exc.InvalidRequestError(
                                "Can't reconnect until invalid "
                                "transaction is rolled back")
            self.__connection = self.engine.raw_connection()
            self.__invalid = False
            return self.__connection
        raise exc.ResourceClosedError("This Connection is closed")

    @property
    def _connection_is_valid(self):
        # use getattr() for is_valid to support exceptions raised in
        # dialect initializer, where the connection is not wrapped in
        # _ConnectionFairy

        return getattr(self.__connection, 'is_valid', False)

    @property
    def _still_open_and_connection_is_valid(self):
        return \
            not self.closed and \
            not self.invalidated and \
            getattr(self.__connection, 'is_valid', False)

    @property
    def info(self):
        """Info dictionary associated with the underlying DBAPI connection
        referred to by this :class:`.Connection`, allowing user-defined
        data to be associated with the connection.

        The data here will follow along with the DBAPI connection including
        after it is returned to the connection pool and used again
        in subsequent instances of :class:`.Connection`.

        """

        return self.connection.info

    def connect(self):
        """Returns a branched version of this :class:`.Connection`.

        The :meth:`.Connection.close` method on the returned
        :class:`.Connection` can be called and this
        :class:`.Connection` will remain open.

        This method provides usage symmetry with
        :meth:`.Engine.connect`, including for usage
        with context managers.

        """

        return self._branch()

    def contextual_connect(self, **kwargs):
        """Returns a branched version of this :class:`.Connection`.

        The :meth:`.Connection.close` method on the returned
        :class:`.Connection` can be called and this
        :class:`.Connection` will remain open.

        This method provides usage symmetry with
        :meth:`.Engine.contextual_connect`, including for usage
        with context managers.

        """

        return self._branch()

    def invalidate(self, exception=None):
        """Invalidate the underlying DBAPI connection associated with
        this Connection.

        The underlying DB-API connection is literally closed (if
        possible), and is discarded.  Its source connection pool will
        typically lazily create a new connection to replace it.

        Upon the next usage, this Connection will attempt to reconnect
        to the pool with a new connection.

        Transactions in progress remain in an "opened" state (even though the
        actual transaction is gone); these must be explicitly rolled back
        before a reconnect on this Connection can proceed. This is to prevent
        applications from accidentally continuing their transactional
        operations in a non-transactional state.

        """
        if self.invalidated:
            return

        if self.closed:
            raise exc.ResourceClosedError("This Connection is closed")

        if self._connection_is_valid:
            self.__connection.invalidate(exception)
        del self.__connection
        self.__invalid = True

    def detach(self):
        """Detach the underlying DB-API connection from its connection pool.

        This Connection instance will remain usable.  When closed,
        the DB-API connection will be literally closed and not
        returned to its pool.  The pool will typically lazily create a
        new connection to replace the detached connection.

        This method can be used to insulate the rest of an application
        from a modified state on a connection (such as a transaction
        isolation level or similar).  Also see
        :class:`~sqlalchemy.interfaces.PoolListener` for a mechanism to modify
        connection state when connections leave and return to their
        connection pool.
        """

        self.__connection.detach()

    def begin(self):
        """Begin a transaction and return a transaction handle.

        The returned object is an instance of :class:`.Transaction`.
        This object represents the "scope" of the transaction,
        which completes when either the :meth:`.Transaction.rollback`
        or :meth:`.Transaction.commit` method is called.

        Nested calls to :meth:`.begin` on the same :class:`.Connection`
        will return new :class:`.Transaction` objects that represent
        an emulated transaction within the scope of the enclosing
        transaction, that is::

            trans = conn.begin()   # outermost transaction
            trans2 = conn.begin()  # "nested"
            trans2.commit()        # does nothing
            trans.commit()         # actually commits

        Calls to :meth:`.Transaction.commit` only have an effect
        when invoked via the outermost :class:`.Transaction` object, though the
        :meth:`.Transaction.rollback` method of any of the
        :class:`.Transaction` objects will roll back the
        transaction.

        See also:

        :meth:`.Connection.begin_nested` - use a SAVEPOINT

        :meth:`.Connection.begin_twophase` - use a two phase /XID transaction

        :meth:`.Engine.begin` - context manager available from
        :class:`.Engine`.

        """

        if self.__transaction is None:
            self.__transaction = RootTransaction(self)
            return self.__transaction
        else:
            return Transaction(self, self.__transaction)

    def begin_nested(self):
        """Begin a nested transaction and return a transaction handle.

        The returned object is an instance of :class:`.NestedTransaction`.

        Nested transactions require SAVEPOINT support in the
        underlying database.  Any transaction in the hierarchy may
        ``commit`` and ``rollback``, however the outermost transaction
        still controls the overall ``commit`` or ``rollback`` of the
        transaction of a whole.

        See also :meth:`.Connection.begin`,
        :meth:`.Connection.begin_twophase`.
        """

        if self.__transaction is None:
            self.__transaction = RootTransaction(self)
        else:
            self.__transaction = NestedTransaction(self, self.__transaction)
        return self.__transaction

    def begin_twophase(self, xid=None):
        """Begin a two-phase or XA transaction and return a transaction
        handle.

        The returned object is an instance of :class:`.TwoPhaseTransaction`,
        which in addition to the methods provided by
        :class:`.Transaction`, also provides a
        :meth:`~.TwoPhaseTransaction.prepare` method.

        :param xid: the two phase transaction id.  If not supplied, a
          random id will be generated.

        See also :meth:`.Connection.begin`,
        :meth:`.Connection.begin_twophase`.

        """

        if self.__transaction is not None:
            raise exc.InvalidRequestError(
                "Cannot start a two phase transaction when a transaction "
                "is already in progress.")
        if xid is None:
            xid = self.engine.dialect.create_xid()
        self.__transaction = TwoPhaseTransaction(self, xid)
        return self.__transaction

    def recover_twophase(self):
        return self.engine.dialect.do_recover_twophase(self)

    def rollback_prepared(self, xid, recover=False):
        self.engine.dialect.do_rollback_twophase(self, xid, recover=recover)

    def commit_prepared(self, xid, recover=False):
        self.engine.dialect.do_commit_twophase(self, xid, recover=recover)

    def in_transaction(self):
        """Return True if a transaction is in progress."""

        return self.__transaction is not None

    def _begin_impl(self):
        if self._echo:
            self.engine.logger.info("BEGIN (implicit)")

        if self._has_events:
            self.dispatch.begin(self)

        try:
            self.engine.dialect.do_begin(self.connection)
        except Exception, e:
            self._handle_dbapi_exception(e, None, None, None, None)

    def _rollback_impl(self):
        if self._has_events:
            self.dispatch.rollback(self)

        if self._still_open_and_connection_is_valid:
            if self._echo:
                self.engine.logger.info("ROLLBACK")
            try:
                self.engine.dialect.do_rollback(self.connection)
                self.__transaction = None
            except Exception, e:
                self._handle_dbapi_exception(e, None, None, None, None)
        else:
            self.__transaction = None

    def _commit_impl(self, autocommit=False):
        if self._has_events:
            self.dispatch.commit(self)

        if self._echo:
            self.engine.logger.info("COMMIT")
        try:
            self.engine.dialect.do_commit(self.connection)
            self.__transaction = None
        except Exception, e:
            self._handle_dbapi_exception(e, None, None, None, None)

    def _savepoint_impl(self, name=None):
        if self._has_events:
            self.dispatch.savepoint(self, name)

        if name is None:
            self.__savepoint_seq += 1
            name = 'sa_savepoint_%s' % self.__savepoint_seq
        if self._still_open_and_connection_is_valid:
            self.engine.dialect.do_savepoint(self, name)
            return name

    def _rollback_to_savepoint_impl(self, name, context):
        if self._has_events:
            self.dispatch.rollback_savepoint(self, name, context)

        if self._still_open_and_connection_is_valid:
            self.engine.dialect.do_rollback_to_savepoint(self, name)
        self.__transaction = context

    def _release_savepoint_impl(self, name, context):
        if self._has_events:
            self.dispatch.release_savepoint(self, name, context)

        if self._still_open_and_connection_is_valid:
            self.engine.dialect.do_release_savepoint(self, name)
        self.__transaction = context

    def _begin_twophase_impl(self, xid):
        if self._echo:
            self.engine.logger.info("BEGIN TWOPHASE (implicit)")
        if self._has_events:
            self.dispatch.begin_twophase(self, xid)

        if self._still_open_and_connection_is_valid:
            self.engine.dialect.do_begin_twophase(self, xid)

    def _prepare_twophase_impl(self, xid):
        if self._has_events:
            self.dispatch.prepare_twophase(self, xid)

        if self._still_open_and_connection_is_valid:
            assert isinstance(self.__transaction, TwoPhaseTransaction)
            self.engine.dialect.do_prepare_twophase(self, xid)

    def _rollback_twophase_impl(self, xid, is_prepared):
        if self._has_events:
            self.dispatch.rollback_twophase(self, xid, is_prepared)

        if self._still_open_and_connection_is_valid:
            assert isinstance(self.__transaction, TwoPhaseTransaction)
            self.engine.dialect.do_rollback_twophase(self, xid, is_prepared)
        self.__transaction = None

    def _commit_twophase_impl(self, xid, is_prepared):
        if self._has_events:
            self.dispatch.commit_twophase(self, xid, is_prepared)

        if self._still_open_and_connection_is_valid:
            assert isinstance(self.__transaction, TwoPhaseTransaction)
            self.engine.dialect.do_commit_twophase(self, xid, is_prepared)
        self.__transaction = None

    def _autorollback(self):
        if not self.in_transaction():
            self._rollback_impl()

    def close(self):
        """Close this :class:`.Connection`.

        This results in a release of the underlying database
        resources, that is, the DBAPI connection referenced
        internally. The DBAPI connection is typically restored
        back to the connection-holding :class:`.Pool` referenced
        by the :class:`.Engine` that produced this
        :class:`.Connection`. Any transactional state present on
        the DBAPI connection is also unconditionally released via
        the DBAPI connection's ``rollback()`` method, regardless
        of any :class:`.Transaction` object that may be
        outstanding with regards to this :class:`.Connection`.

        After :meth:`~.Connection.close` is called, the
        :class:`.Connection` is permanently in a closed state,
        and will allow no further operations.

        """
        try:
            conn = self.__connection
        except AttributeError:
            pass
        else:
            if not self.__branch:
                conn.close()
            del self.__connection
        self.__can_reconnect = False
        self.__transaction = None

    def scalar(self, object, *multiparams, **params):
        """Executes and returns the first column of the first row.

        The underlying result/cursor is closed after execution.
        """

        return self.execute(object, *multiparams, **params).scalar()

    def execute(self, object, *multiparams, **params):
        """Executes the a SQL statement construct and returns a
        :class:`.ResultProxy`.

        :param object: The statement to be executed.  May be
         one of:

         * a plain string
         * any :class:`.ClauseElement` construct that is also
           a subclass of :class:`.Executable`, such as a
           :func:`~.expression.select` construct
         * a :class:`.FunctionElement`, such as that generated
           by :attr:`.func`, will be automatically wrapped in
           a SELECT statement, which is then executed.
         * a :class:`.DDLElement` object
         * a :class:`.DefaultGenerator` object
         * a :class:`.Compiled` object

        :param \*multiparams/\**params: represent bound parameter
         values to be used in the execution.   Typically,
         the format is either a collection of one or more
         dictionaries passed to \*multiparams::

             conn.execute(
                 table.insert(),
                 {"id":1, "value":"v1"},
                 {"id":2, "value":"v2"}
             )

         ...or individual key/values interpreted by \**params::

             conn.execute(
                 table.insert(), id=1, value="v1"
             )

         In the case that a plain SQL string is passed, and the underlying
         DBAPI accepts positional bind parameters, a collection of tuples
         or individual values in \*multiparams may be passed::

             conn.execute(
                 "INSERT INTO table (id, value) VALUES (?, ?)",
                 (1, "v1"), (2, "v2")
             )

             conn.execute(
                 "INSERT INTO table (id, value) VALUES (?, ?)",
                 1, "v1"
             )

         Note above, the usage of a question mark "?" or other
         symbol is contingent upon the "paramstyle" accepted by the DBAPI
         in use, which may be any of "qmark", "named", "pyformat", "format",
         "numeric".   See `pep-249 <http://www.python.org/dev/peps/pep-0249/>`_
         for details on paramstyle.

         To execute a textual SQL statement which uses bound parameters in a
         DBAPI-agnostic way, use the :func:`~.expression.text` construct.

        """
        for c in type(object).__mro__:
            if c in Connection.executors:
                return Connection.executors[c](
                                                self,
                                                object,
                                                multiparams,
                                                params)
        else:
            raise exc.InvalidRequestError(
                                "Unexecutable object type: %s" %
                                type(object))

    def _execute_function(self, func, multiparams, params):
        """Execute a sql.FunctionElement object."""

        return self._execute_clauseelement(func.select(),
                                            multiparams, params)

    def _execute_default(self, default, multiparams, params):
        """Execute a schema.ColumnDefault object."""

        if self._has_events:
            for fn in self.dispatch.before_execute:
                default, multiparams, params = \
                    fn(self, default, multiparams, params)

        try:
            try:
                conn = self.__connection
            except AttributeError:
                conn = self._revalidate_connection()

            dialect = self.dialect
            ctx = dialect.execution_ctx_cls._init_default(
                                dialect, self, conn)
        except Exception, e:
            self._handle_dbapi_exception(e, None, None, None, None)

        ret = ctx._exec_default(default, None)
        if self.should_close_with_result:
            self.close()

        if self._has_events:
            self.dispatch.after_execute(self,
                default, multiparams, params, ret)

        return ret

    def _execute_ddl(self, ddl, multiparams, params):
        """Execute a schema.DDL object."""

        if self._has_events:
            for fn in self.dispatch.before_execute:
                ddl, multiparams, params = \
                    fn(self, ddl, multiparams, params)

        dialect = self.dialect

        compiled = ddl.compile(dialect=dialect)
        ret = self._execute_context(
            dialect,
            dialect.execution_ctx_cls._init_ddl,
            compiled,
            None,
            compiled
        )
        if self._has_events:
            self.dispatch.after_execute(self,
                ddl, multiparams, params, ret)
        return ret

    def _execute_clauseelement(self, elem, multiparams, params):
        """Execute a sql.ClauseElement object."""

        if self._has_events:
            for fn in self.dispatch.before_execute:
                elem, multiparams, params = \
                    fn(self, elem, multiparams, params)

        distilled_params = _distill_params(multiparams, params)
        if distilled_params:
            keys = distilled_params[0].keys()
        else:
            keys = []

        dialect = self.dialect
        if 'compiled_cache' in self._execution_options:
            key = dialect, elem, tuple(keys), len(distilled_params) > 1
            if key in self._execution_options['compiled_cache']:
                compiled_sql = self._execution_options['compiled_cache'][key]
            else:
                compiled_sql = elem.compile(
                                dialect=dialect, column_keys=keys,
                                inline=len(distilled_params) > 1)
                self._execution_options['compiled_cache'][key] = compiled_sql
        else:
            compiled_sql = elem.compile(
                            dialect=dialect, column_keys=keys,
                            inline=len(distilled_params) > 1)

        ret = self._execute_context(
            dialect,
            dialect.execution_ctx_cls._init_compiled,
            compiled_sql,
            distilled_params,
            compiled_sql, distilled_params
        )
        if self._has_events:
            self.dispatch.after_execute(self,
                elem, multiparams, params, ret)
        return ret

    def _execute_compiled(self, compiled, multiparams, params):
        """Execute a sql.Compiled object."""

        if self._has_events:
            for fn in self.dispatch.before_execute:
                compiled, multiparams, params = \
                    fn(self, compiled, multiparams, params)

        dialect = self.dialect
        parameters = _distill_params(multiparams, params)
        ret = self._execute_context(
            dialect,
            dialect.execution_ctx_cls._init_compiled,
            compiled,
            parameters,
            compiled, parameters
        )
        if self._has_events:
            self.dispatch.after_execute(self,
                compiled, multiparams, params, ret)
        return ret

    def _execute_text(self, statement, multiparams, params):
        """Execute a string SQL statement."""

        if self._has_events:
            for fn in self.dispatch.before_execute:
                statement, multiparams, params = \
                    fn(self, statement, multiparams, params)

        dialect = self.dialect
        parameters = _distill_params(multiparams, params)
        ret = self._execute_context(
            dialect,
            dialect.execution_ctx_cls._init_statement,
            statement,
            parameters,
            statement, parameters
        )
        if self._has_events:
            self.dispatch.after_execute(self,
                statement, multiparams, params, ret)
        return ret

    def _execute_context(self, dialect, constructor,
                                    statement, parameters,
                                    *args):
        """Create an :class:`.ExecutionContext` and execute, returning
        a :class:`.ResultProxy`."""

        try:
            try:
                conn = self.__connection
            except AttributeError:
                conn = self._revalidate_connection()

            context = constructor(dialect, self, conn, *args)
        except Exception, e:
            self._handle_dbapi_exception(e,
                        str(statement), parameters,
                        None, None)

        if context.compiled:
            context.pre_exec()

        cursor, statement, parameters = context.cursor, \
                                        context.statement, \
                                        context.parameters

        if not context.executemany:
            parameters = parameters[0]

        if self._has_events:
            for fn in self.dispatch.before_cursor_execute:
                statement, parameters = \
                            fn(self, cursor, statement, parameters,
                                        context, context.executemany)

        if self._echo:
            self.engine.logger.info(statement)
            self.engine.logger.info("%r",
                    sql_util._repr_params(parameters, batches=10))
        try:
            if context.executemany:
                self.dialect.do_executemany(
                                    cursor,
                                    statement,
                                    parameters,
                                    context)
            elif not parameters and context.no_parameters:
                self.dialect.do_execute_no_params(
                                    cursor,
                                    statement,
                                    context)
            else:
                self.dialect.do_execute(
                                    cursor,
                                    statement,
                                    parameters,
                                    context)
        except Exception, e:
            self._handle_dbapi_exception(
                                e,
                                statement,
                                parameters,
                                cursor,
                                context)

        if self._has_events:
            self.dispatch.after_cursor_execute(self, cursor,
                                                statement,
                                                parameters,
                                                context,
                                                context.executemany)

        if context.compiled:
            context.post_exec()

            if context.isinsert and not context.executemany:
                context.post_insert()

        # create a resultproxy, get rowcount/implicit RETURNING
        # rows, close cursor if no further results pending
        result = context.get_result_proxy()
        if context.isinsert:
            if context._is_implicit_returning:
                context._fetch_implicit_returning(result)
                result.close(_autoclose_connection=False)
                result._metadata = None
            elif not context._is_explicit_returning:
                result.close(_autoclose_connection=False)
                result._metadata = None
        elif result._metadata is None:
            # no results, get rowcount
            # (which requires open cursor on some drivers
            # such as kintersbasdb, mxodbc),
            result.rowcount
            result.close(_autoclose_connection=False)

        if self.__transaction is None and context.should_autocommit:
            self._commit_impl(autocommit=True)

        if result.closed and self.should_close_with_result:
            self.close()

        return result

    def _cursor_execute(self, cursor, statement, parameters, context=None):
        """Execute a statement + params on the given cursor.

        Adds appropriate logging and exception handling.

        This method is used by DefaultDialect for special-case
        executions, such as for sequences and column defaults.
        The path of statement execution in the majority of cases
        terminates at _execute_context().

        """
        if self._has_events:
            for fn in self.dispatch.before_cursor_execute:
                statement, parameters = \
                            fn(self, cursor, statement, parameters,
                                        context,
                                        context.executemany
                                           if context is not None else False)

        if self._echo:
            self.engine.logger.info(statement)
            self.engine.logger.info("%r", parameters)
        try:
            self.dialect.do_execute(
                                cursor,
                                statement,
                                parameters)
        except Exception, e:
            self._handle_dbapi_exception(
                                e,
                                statement,
                                parameters,
                                cursor,
                                None)

    def _safe_close_cursor(self, cursor):
        """Close the given cursor, catching exceptions
        and turning into log warnings.

        """
        try:
            cursor.close()
        except Exception, e:
            try:
                ex_text = str(e)
            except TypeError:
                ex_text = repr(e)
            if not self.closed:
                self.connection._logger.warn(
                            "Error closing cursor: %s", ex_text)

            if isinstance(e, (SystemExit, KeyboardInterrupt)):
                raise

    _reentrant_error = False
    _is_disconnect = False

    def _handle_dbapi_exception(self,
                                    e,
                                    statement,
                                    parameters,
                                    cursor,
                                    context):

        exc_info = sys.exc_info()

        if not self._is_disconnect:
            self._is_disconnect = isinstance(e, self.dialect.dbapi.Error) and \
                not self.closed and \
                self.dialect.is_disconnect(e, self.__connection, cursor)

        if self._reentrant_error:
            util.raise_from_cause(
                        exc.DBAPIError.instance(statement,
                                            parameters,
                                            e,
                                            self.dialect.dbapi.Error),
                        exc_info
                        )
        self._reentrant_error = True
        try:
            # non-DBAPI error - if we already got a context,
            # or theres no string statement, don't wrap it
            should_wrap = isinstance(e, self.dialect.dbapi.Error) or \
                (statement is not None and context is None)

            if should_wrap and context:
                if self._has_events:
                    self.dispatch.dbapi_error(self,
                                                    cursor,
                                                    statement,
                                                    parameters,
                                                    context,
                                                    e)
                context.handle_dbapi_exception(e)

            if not self._is_disconnect:
                if cursor:
                    self._safe_close_cursor(cursor)
                self._autorollback()

            if should_wrap:
                util.raise_from_cause(
                                    exc.DBAPIError.instance(
                                        statement,
                                        parameters,
                                        e,
                                        self.dialect.dbapi.Error,
                                        connection_invalidated=self._is_disconnect),
                                    exc_info
                                )

            util.reraise(*exc_info)

        finally:
            del self._reentrant_error
            if self._is_disconnect:
                del self._is_disconnect
                dbapi_conn_wrapper = self.connection
                self.invalidate(e)
                if not hasattr(dbapi_conn_wrapper, '_pool') or \
                        dbapi_conn_wrapper._pool is self.engine.pool:
                    self.engine.dispose()
            if self.should_close_with_result:
                self.close()

    # poor man's multimethod/generic function thingy
    executors = {
        expression.FunctionElement: _execute_function,
        expression.ClauseElement: _execute_clauseelement,
        Compiled: _execute_compiled,
        schema.SchemaItem: _execute_default,
        schema.DDLElement: _execute_ddl,
        basestring: _execute_text
    }

    def default_schema_name(self):
        return self.engine.dialect.get_default_schema_name(self)

    def transaction(self, callable_, *args, **kwargs):
        """Execute the given function within a transaction boundary.

        The function is passed this :class:`.Connection`
        as the first argument, followed by the given \*args and \**kwargs,
        e.g.::

            def do_something(conn, x, y):
                conn.execute("some statement", {'x':x, 'y':y})

            conn.transaction(do_something, 5, 10)

        The operations inside the function are all invoked within the
        context of a single :class:`.Transaction`.
        Upon success, the transaction is committed.  If an
        exception is raised, the transaction is rolled back
        before propagating the exception.

        .. note::

           The :meth:`.transaction` method is superseded by
           the usage of the Python ``with:`` statement, which can
           be used with :meth:`.Connection.begin`::

               with conn.begin():
                   conn.execute("some statement", {'x':5, 'y':10})

           As well as with :meth:`.Engine.begin`::

               with engine.begin() as conn:
                   conn.execute("some statement", {'x':5, 'y':10})

        See also:

            :meth:`.Engine.begin` - engine-level transactional
            context

            :meth:`.Engine.transaction` - engine-level version of
            :meth:`.Connection.transaction`

        """

        trans = self.begin()
        try:
            ret = self.run_callable(callable_, *args, **kwargs)
            trans.commit()
            return ret
        except:
            with util.safe_reraise():
                trans.rollback()

    def run_callable(self, callable_, *args, **kwargs):
        """Given a callable object or function, execute it, passing
        a :class:`.Connection` as the first argument.

        The given \*args and \**kwargs are passed subsequent
        to the :class:`.Connection` argument.

        This function, along with :meth:`.Engine.run_callable`,
        allows a function to be run with a :class:`.Connection`
        or :class:`.Engine` object without the need to know
        which one is being dealt with.

        """
        return callable_(self, *args, **kwargs)

    def _run_visitor(self, visitorcallable, element, **kwargs):
        visitorcallable(self.dialect, self,
                            **kwargs).traverse_single(element)


class Transaction(object):
    """Represent a database transaction in progress.

    The :class:`.Transaction` object is procured by
    calling the :meth:`~.Connection.begin` method of
    :class:`.Connection`::

        from sqlalchemy import create_engine
        engine = create_engine("postgresql://scott:tiger@localhost/test")
        connection = engine.connect()
        trans = connection.begin()
        connection.execute("insert into x (a, b) values (1, 2)")
        trans.commit()

    The object provides :meth:`.rollback` and :meth:`.commit`
    methods in order to control transaction boundaries.  It
    also implements a context manager interface so that
    the Python ``with`` statement can be used with the
    :meth:`.Connection.begin` method::

        with connection.begin():
            connection.execute("insert into x (a, b) values (1, 2)")

    The Transaction object is **not** threadsafe.

    See also:  :meth:`.Connection.begin`, :meth:`.Connection.begin_twophase`,
    :meth:`.Connection.begin_nested`.

    .. index::
      single: thread safety; Transaction
    """

    def __init__(self, connection, parent):
        self.connection = connection
        self._parent = parent or self
        self.is_active = True

    def close(self):
        """Close this :class:`.Transaction`.

        If this transaction is the base transaction in a begin/commit
        nesting, the transaction will rollback().  Otherwise, the
        method returns.

        This is used to cancel a Transaction without affecting the scope of
        an enclosing transaction.

        """
        if not self._parent.is_active:
            return
        if self._parent is self:
            self.rollback()

    def rollback(self):
        """Roll back this :class:`.Transaction`.

        """
        if not self._parent.is_active:
            return
        self._do_rollback()
        self.is_active = False

    def _do_rollback(self):
        self._parent.rollback()

    def commit(self):
        """Commit this :class:`.Transaction`."""

        if not self._parent.is_active:
            raise exc.InvalidRequestError("This transaction is inactive")
        self._do_commit()
        self.is_active = False

    def _do_commit(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if type is None and self.is_active:
            try:
                self.commit()
            except:
                with util.safe_reraise():
                    self.rollback()
        else:
            self.rollback()


class RootTransaction(Transaction):
    def __init__(self, connection):
        super(RootTransaction, self).__init__(connection, None)
        self.connection._begin_impl()

    def _do_rollback(self):
        if self.is_active:
            self.connection._rollback_impl()

    def _do_commit(self):
        if self.is_active:
            self.connection._commit_impl()


class NestedTransaction(Transaction):
    """Represent a 'nested', or SAVEPOINT transaction.

    A new :class:`.NestedTransaction` object may be procured
    using the :meth:`.Connection.begin_nested` method.

    The interface is the same as that of :class:`.Transaction`.

    """
    def __init__(self, connection, parent):
        super(NestedTransaction, self).__init__(connection, parent)
        self._savepoint = self.connection._savepoint_impl()

    def _do_rollback(self):
        if self.is_active:
            self.connection._rollback_to_savepoint_impl(
                                    self._savepoint, self._parent)

    def _do_commit(self):
        if self.is_active:
            self.connection._release_savepoint_impl(
                                    self._savepoint, self._parent)


class TwoPhaseTransaction(Transaction):
    """Represent a two-phase transaction.

    A new :class:`.TwoPhaseTransaction` object may be procured
    using the :meth:`.Connection.begin_twophase` method.

    The interface is the same as that of :class:`.Transaction`
    with the addition of the :meth:`prepare` method.

    """
    def __init__(self, connection, xid):
        super(TwoPhaseTransaction, self).__init__(connection, None)
        self._is_prepared = False
        self.xid = xid
        self.connection._begin_twophase_impl(self.xid)

    def prepare(self):
        """Prepare this :class:`.TwoPhaseTransaction`.

        After a PREPARE, the transaction can be committed.

        """
        if not self._parent.is_active:
            raise exc.InvalidRequestError("This transaction is inactive")
        self.connection._prepare_twophase_impl(self.xid)
        self._is_prepared = True

    def _do_rollback(self):
        self.connection._rollback_twophase_impl(self.xid, self._is_prepared)

    def _do_commit(self):
        self.connection._commit_twophase_impl(self.xid, self._is_prepared)


class Engine(Connectable, log.Identified):
    """
    Connects a :class:`~sqlalchemy.pool.Pool` and
    :class:`~sqlalchemy.engine.interfaces.Dialect` together to provide a
    source of database connectivity and behavior.

    An :class:`.Engine` object is instantiated publicly using the
    :func:`~sqlalchemy.create_engine` function.

    See also:

    :doc:`/core/engines`

    :ref:`connections_toplevel`

    """

    _execution_options = util.immutabledict()
    _has_events = False
    _connection_cls = Connection

    def __init__(self, pool, dialect, url,
                        logging_name=None, echo=None, proxy=None,
                        execution_options=None
                        ):
        self.pool = pool
        self.url = url
        self.dialect = dialect
        self.pool._dialect = dialect
        if logging_name:
            self.logging_name = logging_name
        self.echo = echo
        self.engine = self
        log.instance_logger(self, echoflag=echo)
        if proxy:
            interfaces.ConnectionProxy._adapt_listener(self, proxy)
        if execution_options:
            self.update_execution_options(**execution_options)

    def update_execution_options(self, **opt):
        """Update the default execution_options dictionary
        of this :class:`.Engine`.

        The given keys/values in \**opt are added to the
        default execution options that will be used for
        all connections.  The initial contents of this dictionary
        can be sent via the ``execution_options`` parameter
        to :func:`.create_engine`.

        .. seealso::

            :meth:`.Connection.execution_options`

            :meth:`.Engine.execution_options`

        """
        if 'isolation_level' in opt:
            raise exc.ArgumentError(
                "'isolation_level' execution option may "
                "only be specified on Connection.execution_options(). "
                "To set engine-wide isolation level, "
                "use the isolation_level argument to create_engine()."
            )
        self._execution_options = \
                self._execution_options.union(opt)

    def execution_options(self, **opt):
        """Return a new :class:`.Engine` that will provide
        :class:`.Connection` objects with the given execution options.

        The returned :class:`.Engine` remains related to the original
        :class:`.Engine` in that it shares the same connection pool and
        other state:

        * The :class:`.Pool` used by the new :class:`.Engine` is the
          same instance.  The :meth:`.Engine.dispose` method will replace
          the connection pool instance for the parent engine as well
          as this one.
        * Event listeners are "cascaded" - meaning, the new :class:`.Engine`
          inherits the events of the parent, and new events can be associated
          with the new :class:`.Engine` individually.
        * The logging configuration and logging_name is copied from the parent
          :class:`.Engine`.

        The intent of the :meth:`.Engine.execution_options` method is
        to implement "sharding" schemes where multiple :class:`.Engine`
        objects refer to the same connection pool, but are differentiated
        by options that would be consumed by a custom event::

            primary_engine = create_engine("mysql://")
            shard1 = primary_engine.execution_options(shard_id="shard1")
            shard2 = primary_engine.execution_options(shard_id="shard2")

        Above, the ``shard1`` engine serves as a factory for
        :class:`.Connection` objects that will contain the execution option
        ``shard_id=shard1``, and ``shard2`` will produce :class:`.Connection`
        objects that contain the execution option ``shard_id=shard2``.

        An event handler can consume the above execution option to perform
        a schema switch or other operation, given a connection.  Below
        we emit a MySQL ``use`` statement to switch databases, at the same
        time keeping track of which database we've established using the
        :attr:`.Connection.info` dictionary, which gives us a persistent
        storage space that follows the DBAPI connection::

            from sqlalchemy import event
            from sqlalchemy.engine import Engine

            shards = {"default": "base", shard_1: "db1", "shard_2": "db2"}

            @event.listens_for(Engine, "before_cursor_execute")
            def _switch_shard(conn, cursor, stmt, params, context, executemany):
                shard_id = conn._execution_options.get('shard_id', "default")
                current_shard = conn.info.get("current_shard", None)

                if current_shard != shard_id:
                    cursor.execute("use %s" % shards[shard_id])
                    conn.info["current_shard"] = shard_id

        .. versionadded:: 0.8

        .. seealso::

            :meth:`.Connection.execution_options` - update execution options
            on a :class:`.Connection` object.

            :meth:`.Engine.update_execution_options` - update the execution
            options for a given :class:`.Engine` in place.

        """
        return OptionEngine(self, opt)

    @property
    def name(self):
        """String name of the :class:`~sqlalchemy.engine.interfaces.Dialect`
        in use by this :class:`Engine`."""

        return self.dialect.name

    @property
    def driver(self):
        """Driver name of the :class:`~sqlalchemy.engine.interfaces.Dialect`
        in use by this :class:`Engine`."""

        return self.dialect.driver

    echo = log.echo_property()

    def __repr__(self):
        return 'Engine(%r)' % self.url

    def dispose(self):
        """Dispose of the connection pool used by this :class:`.Engine`.

        A new connection pool is created immediately after the old one has
        been disposed.   This new pool, like all SQLAlchemy connection pools,
        does not make any actual connections to the database until one is
        first requested.

        This method has two general use cases:

         * When a dropped connection is detected, it is assumed that all
           connections held by the pool are potentially dropped, and
           the entire pool is replaced.

         * An application may want to use :meth:`dispose` within a test
           suite that is creating multiple engines.

        It is critical to note that :meth:`dispose` does **not** guarantee
        that the application will release all open database connections - only
        those connections that are checked into the pool are closed.
        Connections which remain checked out or have been detached from
        the engine are not affected.

        """
        self.pool = self.pool._replace()

    def _execute_default(self, default):
        with self.contextual_connect() as conn:
            return conn._execute_default(default, (), {})

    @contextlib.contextmanager
    def _optional_conn_ctx_manager(self, connection=None):
        if connection is None:
            with self.contextual_connect() as conn:
                yield conn
        else:
            yield connection

    def _run_visitor(self, visitorcallable, element,
                                    connection=None, **kwargs):
        with self._optional_conn_ctx_manager(connection) as conn:
            conn._run_visitor(visitorcallable, element, **kwargs)

    class _trans_ctx(object):
        def __init__(self, conn, transaction, close_with_result):
            self.conn = conn
            self.transaction = transaction
            self.close_with_result = close_with_result

        def __enter__(self):
            return self.conn

        def __exit__(self, type, value, traceback):
            if type is not None:
                self.transaction.rollback()
            else:
                self.transaction.commit()
            if not self.close_with_result:
                self.conn.close()

    def begin(self, close_with_result=False):
        """Return a context manager delivering a :class:`.Connection`
        with a :class:`.Transaction` established.

        E.g.::

            with engine.begin() as conn:
                conn.execute("insert into table (x, y, z) values (1, 2, 3)")
                conn.execute("my_special_procedure(5)")

        Upon successful operation, the :class:`.Transaction`
        is committed.  If an error is raised, the :class:`.Transaction`
        is rolled back.

        The ``close_with_result`` flag is normally ``False``, and indicates
        that the :class:`.Connection` will be closed when the operation
        is complete.   When set to ``True``, it indicates the
        :class:`.Connection` is in "single use" mode, where the
        :class:`.ResultProxy` returned by the first call to
        :meth:`.Connection.execute` will close the :class:`.Connection` when
        that :class:`.ResultProxy` has exhausted all result rows.

        .. versionadded:: 0.7.6

        See also:

        :meth:`.Engine.connect` - procure a :class:`.Connection` from
        an :class:`.Engine`.

        :meth:`.Connection.begin` - start a :class:`.Transaction`
        for a particular :class:`.Connection`.

        """
        conn = self.contextual_connect(close_with_result=close_with_result)
        try:
            trans = conn.begin()
        except:
            with util.safe_reraise():
                conn.close()
        return Engine._trans_ctx(conn, trans, close_with_result)

    def transaction(self, callable_, *args, **kwargs):
        """Execute the given function within a transaction boundary.

        The function is passed a :class:`.Connection` newly procured
        from :meth:`.Engine.contextual_connect` as the first argument,
        followed by the given \*args and \**kwargs.

        e.g.::

            def do_something(conn, x, y):
                conn.execute("some statement", {'x':x, 'y':y})

            engine.transaction(do_something, 5, 10)

        The operations inside the function are all invoked within the
        context of a single :class:`.Transaction`.
        Upon success, the transaction is committed.  If an
        exception is raised, the transaction is rolled back
        before propagating the exception.

        .. note::

           The :meth:`.transaction` method is superseded by
           the usage of the Python ``with:`` statement, which can
           be used with :meth:`.Engine.begin`::

               with engine.begin() as conn:
                   conn.execute("some statement", {'x':5, 'y':10})

        See also:

            :meth:`.Engine.begin` - engine-level transactional
            context

            :meth:`.Connection.transaction` - connection-level version of
            :meth:`.Engine.transaction`

        """

        with self.contextual_connect() as conn:
            return conn.transaction(callable_, *args, **kwargs)

    def run_callable(self, callable_, *args, **kwargs):
        """Given a callable object or function, execute it, passing
        a :class:`.Connection` as the first argument.

        The given \*args and \**kwargs are passed subsequent
        to the :class:`.Connection` argument.

        This function, along with :meth:`.Connection.run_callable`,
        allows a function to be run with a :class:`.Connection`
        or :class:`.Engine` object without the need to know
        which one is being dealt with.

        """
        with self.contextual_connect() as conn:
            return conn.run_callable(callable_, *args, **kwargs)

    def execute(self, statement, *multiparams, **params):
        """Executes the given construct and returns a :class:`.ResultProxy`.

        The arguments are the same as those used by
        :meth:`.Connection.execute`.

        Here, a :class:`.Connection` is acquired using the
        :meth:`~.Engine.contextual_connect` method, and the statement executed
        with that connection. The returned :class:`.ResultProxy` is flagged
        such that when the :class:`.ResultProxy` is exhausted and its
        underlying cursor is closed, the :class:`.Connection` created here
        will also be closed, which allows its associated DBAPI connection
        resource to be returned to the connection pool.

        """

        connection = self.contextual_connect(close_with_result=True)
        return connection.execute(statement, *multiparams, **params)

    def scalar(self, statement, *multiparams, **params):
        return self.execute(statement, *multiparams, **params).scalar()

    def _execute_clauseelement(self, elem, multiparams=None, params=None):
        connection = self.contextual_connect(close_with_result=True)
        return connection._execute_clauseelement(elem, multiparams, params)

    def _execute_compiled(self, compiled, multiparams, params):
        connection = self.contextual_connect(close_with_result=True)
        return connection._execute_compiled(compiled, multiparams, params)

    def connect(self, **kwargs):
        """Return a new :class:`.Connection` object.

        The :class:`.Connection` object is a facade that uses a DBAPI
        connection internally in order to communicate with the database.  This
        connection is procured from the connection-holding :class:`.Pool`
        referenced by this :class:`.Engine`. When the
        :meth:`~.Connection.close` method of the :class:`.Connection` object
        is called, the underlying DBAPI connection is then returned to the
        connection pool, where it may be used again in a subsequent call to
        :meth:`~.Engine.connect`.

        """

        return self._connection_cls(self, **kwargs)

    def contextual_connect(self, close_with_result=False, **kwargs):
        """Return a :class:`.Connection` object which may be part of some
        ongoing context.

        By default, this method does the same thing as :meth:`.Engine.connect`.
        Subclasses of :class:`.Engine` may override this method
        to provide contextual behavior.

        :param close_with_result: When True, the first :class:`.ResultProxy`
          created by the :class:`.Connection` will call the
          :meth:`.Connection.close` method of that connection as soon as any
          pending result rows are exhausted. This is used to supply the
          "connectionless execution" behavior provided by the
          :meth:`.Engine.execute` method.

        """

        return self._connection_cls(self,
                                    self.pool.connect(),
                                    close_with_result=close_with_result,
                                    **kwargs)

    def table_names(self, schema=None, connection=None):
        """Return a list of all table names available in the database.

        :param schema: Optional, retrieve names from a non-default schema.

        :param connection: Optional, use a specified connection. Default is
          the ``contextual_connect`` for this ``Engine``.
        """

        with self._optional_conn_ctx_manager(connection) as conn:
            if not schema:
                schema = self.dialect.default_schema_name
            return self.dialect.get_table_names(conn, schema)

    def has_table(self, table_name, schema=None):
        return self.run_callable(self.dialect.has_table, table_name, schema)

    def raw_connection(self):
        """Return a "raw" DBAPI connection from the connection pool.

        The returned object is a proxied version of the DBAPI
        connection object used by the underlying driver in use.
        The object will have all the same behavior as the real DBAPI
        connection, except that its ``close()`` method will result in the
        connection being returned to the pool, rather than being closed
        for real.

        This method provides direct DBAPI connection access for
        special situations.  In most situations, the :class:`.Connection`
        object should be used, which is procured using the
        :meth:`.Engine.connect` method.

        """

        return self.pool.unique_connection()


class OptionEngine(Engine):
    def __init__(self, proxied, execution_options):
        self._proxied = proxied
        self.url = proxied.url
        self.dialect = proxied.dialect
        self.logging_name = proxied.logging_name
        self.echo = proxied.echo
        log.instance_logger(self, echoflag=self.echo)
        self.dispatch = self.dispatch._join(proxied.dispatch)
        self._execution_options = proxied._execution_options
        self.update_execution_options(**execution_options)

    def _get_pool(self):
        return self._proxied.pool

    def _set_pool(self, pool):
        self._proxied.pool = pool

    pool = property(_get_pool, _set_pool)

    def _get_has_events(self):
        return self._proxied._has_events or \
            self.__dict__.get('_has_events', False)

    def _set_has_events(self, value):
        self.__dict__['_has_events'] = value

    _has_events = property(_get_has_events, _set_has_events)
