# sqlalchemy/events.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Core event interfaces."""

from . import event, exc, util
engine = util.importlater('sqlalchemy', 'engine')
pool = util.importlater('sqlalchemy', 'pool')


class DDLEvents(event.Events):
    """
    Define event listeners for schema objects,
    that is, :class:`.SchemaItem` and :class:`.SchemaEvent`
    subclasses, including :class:`.MetaData`, :class:`.Table`,
    :class:`.Column`.

    :class:`.MetaData` and :class:`.Table` support events
    specifically regarding when CREATE and DROP
    DDL is emitted to the database.

    Attachment events are also provided to customize
    behavior whenever a child schema element is associated
    with a parent, such as, when a :class:`.Column` is associated
    with its :class:`.Table`, when a :class:`.ForeignKeyConstraint`
    is associated with a :class:`.Table`, etc.

    Example using the ``after_create`` event::

        from sqlalchemy import event
        from sqlalchemy import Table, Column, Metadata, Integer

        m = MetaData()
        some_table = Table('some_table', m, Column('data', Integer))

        def after_create(target, connection, **kw):
            connection.execute("ALTER TABLE %s SET name=foo_%s" %
                                    (target.name, target.name))

        event.listen(some_table, "after_create", after_create)

    DDL events integrate closely with the
    :class:`.DDL` class and the :class:`.DDLElement` hierarchy
    of DDL clause constructs, which are themselves appropriate
    as listener callables::

        from sqlalchemy import DDL
        event.listen(
            some_table,
            "after_create",
            DDL("ALTER TABLE %(table)s SET name=foo_%(table)s")
        )

    The methods here define the name of an event as well
    as the names of members that are passed to listener
    functions.

    See also:

        :ref:`event_toplevel`

        :class:`.DDLElement`

        :class:`.DDL`

        :ref:`schema_ddl_sequences`

    """

    def before_create(self, target, connection, **kw):
        """Called before CREATE statments are emitted.

        :param target: the :class:`.MetaData` or :class:`.Table`
         object which is the target of the event.
        :param connection: the :class:`.Connection` where the
         CREATE statement or statements will be emitted.
        :param \**kw: additional keyword arguments relevant
         to the event.  The contents of this dictionary
         may vary across releases, and include the
         list of tables being generated for a metadata-level
         event, the checkfirst flag, and other
         elements used by internal events.

        """

    def after_create(self, target, connection, **kw):
        """Called after CREATE statments are emitted.

        :param target: the :class:`.MetaData` or :class:`.Table`
         object which is the target of the event.
        :param connection: the :class:`.Connection` where the
         CREATE statement or statements have been emitted.
        :param \**kw: additional keyword arguments relevant
         to the event.  The contents of this dictionary
         may vary across releases, and include the
         list of tables being generated for a metadata-level
         event, the checkfirst flag, and other
         elements used by internal events.

        """

    def before_drop(self, target, connection, **kw):
        """Called before DROP statments are emitted.

        :param target: the :class:`.MetaData` or :class:`.Table`
         object which is the target of the event.
        :param connection: the :class:`.Connection` where the
         DROP statement or statements will be emitted.
        :param \**kw: additional keyword arguments relevant
         to the event.  The contents of this dictionary
         may vary across releases, and include the
         list of tables being generated for a metadata-level
         event, the checkfirst flag, and other
         elements used by internal events.

        """

    def after_drop(self, target, connection, **kw):
        """Called after DROP statments are emitted.

        :param target: the :class:`.MetaData` or :class:`.Table`
         object which is the target of the event.
        :param connection: the :class:`.Connection` where the
         DROP statement or statements have been emitted.
        :param \**kw: additional keyword arguments relevant
         to the event.  The contents of this dictionary
         may vary across releases, and include the
         list of tables being generated for a metadata-level
         event, the checkfirst flag, and other
         elements used by internal events.

        """

    def before_parent_attach(self, target, parent):
        """Called before a :class:`.SchemaItem` is associated with
        a parent :class:`.SchemaItem`.

        :param target: the target object
        :param parent: the parent to which the target is being attached.

        :func:`.event.listen` also accepts a modifier for this event:

        :param propagate=False: When True, the listener function will
         be established for any copies made of the target object,
         i.e. those copies that are generated when
         :meth:`.Table.tometadata` is used.

        """

    def after_parent_attach(self, target, parent):
        """Called after a :class:`.SchemaItem` is associated with
        a parent :class:`.SchemaItem`.

        :param target: the target object
        :param parent: the parent to which the target is being attached.

        :func:`.event.listen` also accepts a modifier for this event:

        :param propagate=False: When True, the listener function will
         be established for any copies made of the target object,
         i.e. those copies that are generated when
         :meth:`.Table.tometadata` is used.

        """

    def column_reflect(self, inspector, table, column_info):
        """Called for each unit of 'column info' retrieved when
        a :class:`.Table` is being reflected.

        The dictionary of column information as returned by the
        dialect is passed, and can be modified.  The dictionary
        is that returned in each element of the list returned
        by :meth:`.reflection.Inspector.get_columns`.

        The event is called before any action is taken against
        this dictionary, and the contents can be modified.
        The :class:`.Column` specific arguments ``info``, ``key``,
        and ``quote`` can also be added to the dictionary and
        will be passed to the constructor of :class:`.Column`.

        Note that this event is only meaningful if either
        associated with the :class:`.Table` class across the
        board, e.g.::

            from sqlalchemy.schema import Table
            from sqlalchemy import event

            def listen_for_reflect(inspector, table, column_info):
                "receive a column_reflect event"
                # ...

            event.listen(
                    Table,
                    'column_reflect',
                    listen_for_reflect)

        ...or with a specific :class:`.Table` instance using
        the ``listeners`` argument::

            def listen_for_reflect(inspector, table, column_info):
                "receive a column_reflect event"
                # ...

            t = Table(
                'sometable',
                autoload=True,
                listeners=[
                    ('column_reflect', listen_for_reflect)
                ])

        This because the reflection process initiated by ``autoload=True``
        completes within the scope of the constructor for :class:`.Table`.

        """


class SchemaEventTarget(object):
    """Base class for elements that are the targets of :class:`.DDLEvents`
    events.

    This includes :class:`.SchemaItem` as well as :class:`.SchemaType`.

    """
    dispatch = event.dispatcher(DDLEvents)

    def _set_parent(self, parent):
        """Associate with this SchemaEvent's parent object."""

        raise NotImplementedError()

    def _set_parent_with_dispatch(self, parent):
        self.dispatch.before_parent_attach(self, parent)
        self._set_parent(parent)
        self.dispatch.after_parent_attach(self, parent)


class PoolEvents(event.Events):
    """Available events for :class:`.Pool`.

    The methods here define the name of an event as well
    as the names of members that are passed to listener
    functions.

    e.g.::

        from sqlalchemy import event

        def my_on_checkout(dbapi_conn, connection_rec, connection_proxy):
            "handle an on checkout event"

        event.listen(Pool, 'checkout', my_on_checkout)

    In addition to accepting the :class:`.Pool` class and
    :class:`.Pool` instances, :class:`.PoolEvents` also accepts
    :class:`.Engine` objects and the :class:`.Engine` class as
    targets, which will be resolved to the ``.pool`` attribute of the
    given engine or the :class:`.Pool` class::

        engine = create_engine("postgresql://scott:tiger@localhost/test")

        # will associate with engine.pool
        event.listen(engine, 'checkout', my_on_checkout)

    """

    @classmethod
    def _accept_with(cls, target):
        if isinstance(target, type):
            if issubclass(target, engine.Engine):
                return pool.Pool
            elif issubclass(target, pool.Pool):
                return target
        elif isinstance(target, engine.Engine):
            return target.pool
        else:
            return target

    def connect(self, dbapi_connection, connection_record):
        """Called once for each new DB-API connection or Pool's ``creator()``.

        :param dbapi_con:
          A newly connected raw DB-API connection (not a SQLAlchemy
          ``Connection`` wrapper).

        :param con_record:
          The ``_ConnectionRecord`` that persistently manages the connection

        """

    def first_connect(self, dbapi_connection, connection_record):
        """Called exactly once for the first DB-API connection.

        :param dbapi_con:
          A newly connected raw DB-API connection (not a SQLAlchemy
          ``Connection`` wrapper).

        :param con_record:
          The ``_ConnectionRecord`` that persistently manages the connection

        """

    def checkout(self, dbapi_connection, connection_record, connection_proxy):
        """Called when a connection is retrieved from the Pool.

        :param dbapi_con:
          A raw DB-API connection

        :param con_record:
          The ``_ConnectionRecord`` that persistently manages the connection

        :param con_proxy:
          The ``_ConnectionFairy`` which manages the connection for the span of
          the current checkout.

        If you raise a :class:`~sqlalchemy.exc.DisconnectionError`, the current
        connection will be disposed and a fresh connection retrieved.
        Processing of all checkout listeners will abort and restart
        using the new connection.
        """

    def checkin(self, dbapi_connection, connection_record):
        """Called when a connection returns to the pool.

        Note that the connection may be closed, and may be None if the
        connection has been invalidated.  ``checkin`` will not be called
        for detached connections.  (They do not return to the pool.)

        :param dbapi_con:
          A raw DB-API connection

        :param con_record:
          The ``_ConnectionRecord`` that persistently manages the connection

        """

    def reset(self, dbapi_con, con_record):
        """Called before the "reset" action occurs for a pooled connection.

        This event represents
        when the ``rollback()`` method is called on the DBAPI connection
        before it is returned to the pool.  The behavior of "reset" can
        be controlled, including disabled, using the ``reset_on_return``
        pool argument.


        The :meth:`.PoolEvents.reset` event is usually followed by the
        the :meth:`.PoolEvents.checkin` event is called, except in those
        cases where the connection is discarded immediately after reset.

        :param dbapi_con:
          A raw DB-API connection

        :param con_record:
          The ``_ConnectionRecord`` that persistently manages the connection

        .. versionadded:: 0.8

        .. seealso::

            :meth:`.ConnectionEvents.rollback`

            :meth:`.ConnectionEvents.commit`

        """



class ConnectionEvents(event.Events):
    """Available events for :class:`.Connectable`, which includes
    :class:`.Connection` and :class:`.Engine`.

    The methods here define the name of an event as well as the names of
    members that are passed to listener functions.

    An event listener can be associated with any :class:`.Connectable`
    class or instance, such as an :class:`.Engine`, e.g.::

        from sqlalchemy import event, create_engine

        def before_cursor_execute(conn, cursor, statement, parameters, context,
                                                        executemany):
            log.info("Received statement: %s" % statement)

        engine = create_engine('postgresql://scott:tiger@localhost/test')
        event.listen(engine, "before_cursor_execute", before_cursor_execute)

    or with a specific :class:`.Connection`::

        with engine.begin() as conn:
            @event.listens_for(conn, 'before_cursor_execute')
            def before_cursor_execute(conn, cursor, statement, parameters,
                                            context, executemany):
                log.info("Received statement: %s" % statement)

    The :meth:`.before_execute` and :meth:`.before_cursor_execute`
    events can also be established with the ``retval=True`` flag, which
    allows modification of the statement and parameters to be sent
    to the database.  The :meth:`.before_cursor_execute` event is
    particularly useful here to add ad-hoc string transformations, such
    as comments, to all executions::

        from sqlalchemy.engine import Engine
        from sqlalchemy import event

        @event.listens_for(Engine, "before_cursor_execute", retval=True)
        def comment_sql_calls(conn, cursor, statement, parameters,
                                            context, executemany):
            statement = statement + " -- some comment"
            return statement, parameters

    .. note:: :class:`.ConnectionEvents` can be established on any
       combination of :class:`.Engine`, :class:`.Connection`, as well
       as instances of each of those classes.  Events across all
       four scopes will fire off for a given instance of
       :class:`.Connection`.  However, for performance reasons, the
       :class:`.Connection` object determines at instantiation time
       whether or not its parent :class:`.Engine` has event listeners
       established.   Event listeners added to the :class:`.Engine`
       class or to an instance of :class:`.Engine` *after* the instantiation
       of a dependent :class:`.Connection` instance will usually
       *not* be available on that :class:`.Connection` instance.  The newly
       added listeners will instead take effect for :class:`.Connection`
       instances created subsequent to those event listeners being
       established on the parent :class:`.Engine` class or instance.

    :param retval=False: Applies to the :meth:`.before_execute` and
      :meth:`.before_cursor_execute` events only.  When True, the
      user-defined event function must have a return value, which
      is a tuple of parameters that replace the given statement
      and parameters.  See those methods for a description of
      specific return arguments.

    .. versionchanged:: 0.8 :class:`.ConnectionEvents` can now be associated
       with any :class:`.Connectable` including :class:`.Connection`,
       in addition to the existing support for :class:`.Engine`.

    """

    @classmethod
    def _listen(cls, target, identifier, fn, retval=False):
        target._has_events = True

        if not retval:
            if identifier == 'before_execute':
                orig_fn = fn

                def wrap_before_execute(conn, clauseelement,
                                                multiparams, params):
                    orig_fn(conn, clauseelement, multiparams, params)
                    return clauseelement, multiparams, params
                fn = wrap_before_execute
            elif identifier == 'before_cursor_execute':
                orig_fn = fn

                def wrap_before_cursor_execute(conn, cursor, statement,
                        parameters, context, executemany):
                    orig_fn(conn, cursor, statement,
                        parameters, context, executemany)
                    return statement, parameters
                fn = wrap_before_cursor_execute

        elif retval and \
            identifier not in ('before_execute', 'before_cursor_execute'):
            raise exc.ArgumentError(
                    "Only the 'before_execute' and "
                    "'before_cursor_execute' engine "
                    "event listeners accept the 'retval=True' "
                    "argument.")
        event.Events._listen(target, identifier, fn)

    def before_execute(self, conn, clauseelement, multiparams, params):
        """Intercept high level execute() events, receiving uncompiled
        SQL constructs and other objects prior to rendering into SQL.

        This event is good for debugging SQL compilation issues as well
        as early manipulation of the parameters being sent to the database,
        as the parameter lists will be in a consistent format here.

        This event can be optionally established with the ``retval=True``
        flag.  The ``clauseelement``, ``multiparams``, and ``params``
        arguments should be returned as a three-tuple in this case::

            @event.listens_for(Engine, "before_execute", retval=True)
            def before_execute(conn, conn, clauseelement, multiparams, params):
                # do something with clauseelement, multiparams, params
                return clauseelement, multiparams, params

        :param conn: :class:`.Connection` object
        :param clauseelement: SQL expression construct, :class:`.Compiled`
         instance, or string statement passed to :meth:`.Connection.execute`.
        :param multiparams: Multiple parameter sets, a list of dictionaries.
        :param params: Single parameter set, a single dictionary.

        See also:

        :meth:`.before_cursor_execute`

        """

    def after_execute(self, conn, clauseelement, multiparams, params, result):
        """Intercept high level execute() events after execute.


        :param conn: :class:`.Connection` object
        :param clauseelement: SQL expression construct, :class:`.Compiled`
         instance, or string statement passed to :meth:`.Connection.execute`.
        :param multiparams: Multiple parameter sets, a list of dictionaries.
        :param params: Single parameter set, a single dictionary.
        :param result: :class:`.ResultProxy` generated by the execution.

        """

    def before_cursor_execute(self, conn, cursor, statement,
                        parameters, context, executemany):
        """Intercept low-level cursor execute() events before execution,
        receiving the string
        SQL statement and DBAPI-specific parameter list to be invoked
        against a cursor.

        This event is a good choice for logging as well as late modifications
        to the SQL string.  It's less ideal for parameter modifications except
        for those which are specific to a target backend.

        This event can be optionally established with the ``retval=True``
        flag.  The ``statement`` and ``parameters`` arguments should be
        returned as a two-tuple in this case::

            @event.listens_for(Engine, "before_cursor_execute", retval=True)
            def before_cursor_execute(conn, cursor, statement,
                            parameters, context, executemany):
                # do something with statement, parameters
                return statement, parameters

        See the example at :class:`.ConnectionEvents`.

        :param conn: :class:`.Connection` object
        :param cursor: DBAPI cursor object
        :param statement: string SQL statement
        :param parameters: Dictionary, tuple, or list of parameters being
         passed to the ``execute()`` or ``executemany()`` method of the
         DBAPI ``cursor``.  In some cases may be ``None``.
        :param context: :class:`.ExecutionContext` object in use.  May
         be ``None``.
        :param executemany: boolean, if ``True``, this is an ``executemany()``
         call, if ``False``, this is an ``execute()`` call.

        See also:

        :meth:`.before_execute`

        :meth:`.after_cursor_execute`

        """

    def after_cursor_execute(self, conn, cursor, statement,
                        parameters, context, executemany):
        """Intercept low-level cursor execute() events after execution.

        :param conn: :class:`.Connection` object
        :param cursor: DBAPI cursor object.  Will have results pending
         if the statement was a SELECT, but these should not be consumed
         as they will be needed by the :class:`.ResultProxy`.
        :param statement: string SQL statement
        :param parameters: Dictionary, tuple, or list of parameters being
         passed to the ``execute()`` or ``executemany()`` method of the
         DBAPI ``cursor``.  In some cases may be ``None``.
        :param context: :class:`.ExecutionContext` object in use.  May
         be ``None``.
        :param executemany: boolean, if ``True``, this is an ``executemany()``
         call, if ``False``, this is an ``execute()`` call.

        """

    def dbapi_error(self, conn, cursor, statement, parameters,
                        context, exception):
        """Intercept a raw DBAPI error.

        This event is called with the DBAPI exception instance
        received from the DBAPI itself, *before* SQLAlchemy wraps the
        exception with it's own exception wrappers, and before any
        other operations are performed on the DBAPI cursor; the
        existing transaction remains in effect as well as any state
        on the cursor.

        The use case here is to inject low-level exception handling
        into an :class:`.Engine`, typically for logging and
        debugging purposes.   In general, user code should **not** modify
        any state or throw any exceptions here as this will
        interfere with SQLAlchemy's cleanup and error handling
        routines.

        Subsequent to this hook, SQLAlchemy may attempt any
        number of operations on the connection/cursor, including
        closing the cursor, rolling back of the transaction in the
        case of connectionless execution, and disposing of the entire
        connection pool if a "disconnect" was detected.   The
        exception is then wrapped in a SQLAlchemy DBAPI exception
        wrapper and re-thrown.

        :param conn: :class:`.Connection` object
        :param cursor: DBAPI cursor object
        :param statement: string SQL statement
        :param parameters: Dictionary, tuple, or list of parameters being
         passed to the ``execute()`` or ``executemany()`` method of the
         DBAPI ``cursor``.  In some cases may be ``None``.
        :param context: :class:`.ExecutionContext` object in use.  May
         be ``None``.
        :param exception: The **unwrapped** exception emitted directly from the
         DBAPI.  The class here is specific to the DBAPI module in use.

        .. versionadded:: 0.7.7

        """

    def begin(self, conn):
        """Intercept begin() events.

        :param conn: :class:`.Connection` object

        """

    def rollback(self, conn):
        """Intercept rollback() events, as initiated by a
        :class:`.Transaction`.

        Note that the :class:`.Pool` also "auto-rolls back"
        a DBAPI connection upon checkin, if the ``reset_on_return``
        flag is set to its default value of ``'rollback'``.
        To intercept this
        rollback, use the :meth:`.PoolEvents.reset` hook.

        :param conn: :class:`.Connection` object

        .. seealso::

            :meth:`.PoolEvents.reset`

        """

    def commit(self, conn):
        """Intercept commit() events, as initiated by a
        :class:`.Transaction`.

        Note that the :class:`.Pool` may also "auto-commit"
        a DBAPI connection upon checkin, if the ``reset_on_return``
        flag is set to the value ``'commit'``.  To intercept this
        commit, use the :meth:`.PoolEvents.reset` hook.

        :param conn: :class:`.Connection` object
        """

    def savepoint(self, conn, name=None):
        """Intercept savepoint() events.

        :param conn: :class:`.Connection` object
        :param name: specified name used for the savepoint.

        """

    def rollback_savepoint(self, conn, name, context):
        """Intercept rollback_savepoint() events.

        :param conn: :class:`.Connection` object
        :param name: specified name used for the savepoint.
        :param context: :class:`.ExecutionContext` in use.  May be ``None``.

        """

    def release_savepoint(self, conn, name, context):
        """Intercept release_savepoint() events.

        :param conn: :class:`.Connection` object
        :param name: specified name used for the savepoint.
        :param context: :class:`.ExecutionContext` in use.  May be ``None``.

        """

    def begin_twophase(self, conn, xid):
        """Intercept begin_twophase() events.

        :param conn: :class:`.Connection` object
        :param xid: two-phase XID identifier

        """

    def prepare_twophase(self, conn, xid):
        """Intercept prepare_twophase() events.

        :param conn: :class:`.Connection` object
        :param xid: two-phase XID identifier
        """

    def rollback_twophase(self, conn, xid, is_prepared):
        """Intercept rollback_twophase() events.

        :param conn: :class:`.Connection` object
        :param xid: two-phase XID identifier
        :param is_prepared: boolean, indicates if
         :meth:`.TwoPhaseTransaction.prepare` was called.

        """

    def commit_twophase(self, conn, xid, is_prepared):
        """Intercept commit_twophase() events.

        :param conn: :class:`.Connection` object
        :param xid: two-phase XID identifier
        :param is_prepared: boolean, indicates if
         :meth:`.TwoPhaseTransaction.prepare` was called.

        """
