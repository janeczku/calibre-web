# sqlalchemy/interfaces.py
# Copyright (C) 2007-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
# Copyright (C) 2007 Jason Kirtland jek@discorporate.us
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Deprecated core event interfaces.

This module is **deprecated** and is superseded by the
event system.

"""

from . import event, util


class PoolListener(object):
    """Hooks into the lifecycle of connections in a :class:`.Pool`.

    .. note::

       :class:`.PoolListener` is deprecated.   Please
       refer to :class:`.PoolEvents`.

    Usage::

        class MyListener(PoolListener):
            def connect(self, dbapi_con, con_record):
                '''perform connect operations'''
            # etc.

        # create a new pool with a listener
        p = QueuePool(..., listeners=[MyListener()])

        # add a listener after the fact
        p.add_listener(MyListener())

        # usage with create_engine()
        e = create_engine("url://", listeners=[MyListener()])

    All of the standard connection :class:`~sqlalchemy.pool.Pool` types can
    accept event listeners for key connection lifecycle events:
    creation, pool check-out and check-in.  There are no events fired
    when a connection closes.

    For any given DB-API connection, there will be one ``connect``
    event, `n` number of ``checkout`` events, and either `n` or `n - 1`
    ``checkin`` events.  (If a ``Connection`` is detached from its
    pool via the ``detach()`` method, it won't be checked back in.)

    These are low-level events for low-level objects: raw Python
    DB-API connections, without the conveniences of the SQLAlchemy
    ``Connection`` wrapper, ``Dialect`` services or ``ClauseElement``
    execution.  If you execute SQL through the connection, explicitly
    closing all cursors and other resources is recommended.

    Events also receive a ``_ConnectionRecord``, a long-lived internal
    ``Pool`` object that basically represents a "slot" in the
    connection pool.  ``_ConnectionRecord`` objects have one public
    attribute of note: ``info``, a dictionary whose contents are
    scoped to the lifetime of the DB-API connection managed by the
    record.  You can use this shared storage area however you like.

    There is no need to subclass ``PoolListener`` to handle events.
    Any class that implements one or more of these methods can be used
    as a pool listener.  The ``Pool`` will inspect the methods
    provided by a listener object and add the listener to one or more
    internal event queues based on its capabilities.  In terms of
    efficiency and function call overhead, you're much better off only
    providing implementations for the hooks you'll be using.

    """

    @classmethod
    def _adapt_listener(cls, self, listener):
        """Adapt a :class:`.PoolListener` to individual
        :class:`event.Dispatch` events.

        """

        listener = util.as_interface(listener, methods=('connect',
                                'first_connect', 'checkout', 'checkin'))
        if hasattr(listener, 'connect'):
            event.listen(self, 'connect', listener.connect)
        if hasattr(listener, 'first_connect'):
            event.listen(self, 'first_connect', listener.first_connect)
        if hasattr(listener, 'checkout'):
            event.listen(self, 'checkout', listener.checkout)
        if hasattr(listener, 'checkin'):
            event.listen(self, 'checkin', listener.checkin)

    def connect(self, dbapi_con, con_record):
        """Called once for each new DB-API connection or Pool's ``creator()``.

        dbapi_con
          A newly connected raw DB-API connection (not a SQLAlchemy
          ``Connection`` wrapper).

        con_record
          The ``_ConnectionRecord`` that persistently manages the connection

        """

    def first_connect(self, dbapi_con, con_record):
        """Called exactly once for the first DB-API connection.

        dbapi_con
          A newly connected raw DB-API connection (not a SQLAlchemy
          ``Connection`` wrapper).

        con_record
          The ``_ConnectionRecord`` that persistently manages the connection

        """

    def checkout(self, dbapi_con, con_record, con_proxy):
        """Called when a connection is retrieved from the Pool.

        dbapi_con
          A raw DB-API connection

        con_record
          The ``_ConnectionRecord`` that persistently manages the connection

        con_proxy
          The ``_ConnectionFairy`` which manages the connection for the span of
          the current checkout.

        If you raise an ``exc.DisconnectionError``, the current
        connection will be disposed and a fresh connection retrieved.
        Processing of all checkout listeners will abort and restart
        using the new connection.
        """

    def checkin(self, dbapi_con, con_record):
        """Called when a connection returns to the pool.

        Note that the connection may be closed, and may be None if the
        connection has been invalidated.  ``checkin`` will not be called
        for detached connections.  (They do not return to the pool.)

        dbapi_con
          A raw DB-API connection

        con_record
          The ``_ConnectionRecord`` that persistently manages the connection

        """


class ConnectionProxy(object):
    """Allows interception of statement execution by Connections.

    .. note::

       :class:`.ConnectionProxy` is deprecated.   Please
       refer to :class:`.ConnectionEvents`.

    Either or both of the ``execute()`` and ``cursor_execute()``
    may be implemented to intercept compiled statement and
    cursor level executions, e.g.::

        class MyProxy(ConnectionProxy):
            def execute(self, conn, execute, clauseelement,
                        *multiparams, **params):
                print "compiled statement:", clauseelement
                return execute(clauseelement, *multiparams, **params)

            def cursor_execute(self, execute, cursor, statement,
                               parameters, context, executemany):
                print "raw statement:", statement
                return execute(cursor, statement, parameters, context)

    The ``execute`` argument is a function that will fulfill the default
    execution behavior for the operation.  The signature illustrated
    in the example should be used.

    The proxy is installed into an :class:`~sqlalchemy.engine.Engine` via
    the ``proxy`` argument::

        e = create_engine('someurl://', proxy=MyProxy())

    """

    @classmethod
    def _adapt_listener(cls, self, listener):

        def adapt_execute(conn, clauseelement, multiparams, params):

            def execute_wrapper(clauseelement, *multiparams, **params):
                return clauseelement, multiparams, params

            return listener.execute(conn, execute_wrapper,
                                    clauseelement, *multiparams,
                                    **params)

        event.listen(self, 'before_execute', adapt_execute)

        def adapt_cursor_execute(conn, cursor, statement,
                                 parameters, context, executemany):

            def execute_wrapper(
                cursor,
                statement,
                parameters,
                context,
                ):
                return statement, parameters

            return listener.cursor_execute(
                execute_wrapper,
                cursor,
                statement,
                parameters,
                context,
                executemany,
                )

        event.listen(self, 'before_cursor_execute', adapt_cursor_execute)

        def do_nothing_callback(*arg, **kw):
            pass

        def adapt_listener(fn):

            def go(conn, *arg, **kw):
                fn(conn, do_nothing_callback, *arg, **kw)

            return util.update_wrapper(go, fn)

        event.listen(self, 'begin', adapt_listener(listener.begin))
        event.listen(self, 'rollback',
                     adapt_listener(listener.rollback))
        event.listen(self, 'commit', adapt_listener(listener.commit))
        event.listen(self, 'savepoint',
                     adapt_listener(listener.savepoint))
        event.listen(self, 'rollback_savepoint',
                     adapt_listener(listener.rollback_savepoint))
        event.listen(self, 'release_savepoint',
                     adapt_listener(listener.release_savepoint))
        event.listen(self, 'begin_twophase',
                     adapt_listener(listener.begin_twophase))
        event.listen(self, 'prepare_twophase',
                     adapt_listener(listener.prepare_twophase))
        event.listen(self, 'rollback_twophase',
                     adapt_listener(listener.rollback_twophase))
        event.listen(self, 'commit_twophase',
                     adapt_listener(listener.commit_twophase))

    def execute(self, conn, execute, clauseelement, *multiparams, **params):
        """Intercept high level execute() events."""

        return execute(clauseelement, *multiparams, **params)

    def cursor_execute(self, execute, cursor, statement, parameters,
                       context, executemany):
        """Intercept low-level cursor execute() events."""

        return execute(cursor, statement, parameters, context)

    def begin(self, conn, begin):
        """Intercept begin() events."""

        return begin()

    def rollback(self, conn, rollback):
        """Intercept rollback() events."""

        return rollback()

    def commit(self, conn, commit):
        """Intercept commit() events."""

        return commit()

    def savepoint(self, conn, savepoint, name=None):
        """Intercept savepoint() events."""

        return savepoint(name=name)

    def rollback_savepoint(self, conn, rollback_savepoint, name, context):
        """Intercept rollback_savepoint() events."""

        return rollback_savepoint(name, context)

    def release_savepoint(self, conn, release_savepoint, name, context):
        """Intercept release_savepoint() events."""

        return release_savepoint(name, context)

    def begin_twophase(self, conn, begin_twophase, xid):
        """Intercept begin_twophase() events."""

        return begin_twophase(xid)

    def prepare_twophase(self, conn, prepare_twophase, xid):
        """Intercept prepare_twophase() events."""

        return prepare_twophase(xid)

    def rollback_twophase(self, conn, rollback_twophase, xid, is_prepared):
        """Intercept rollback_twophase() events."""

        return rollback_twophase(xid, is_prepared)

    def commit_twophase(self, conn, commit_twophase, xid, is_prepared):
        """Intercept commit_twophase() events."""

        return commit_twophase(xid, is_prepared)
