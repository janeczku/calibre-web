# engine/__init__.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""SQL connections, SQL execution and high-level DB-API interface.

The engine package defines the basic components used to interface
DB-API modules with higher-level statement construction,
connection-management, execution and result contexts.  The primary
"entry point" class into this package is the Engine and it's public
constructor ``create_engine()``.

This package includes:

base.py
    Defines interface classes and some implementation classes which
    comprise the basic components used to interface between a DB-API,
    constructed and plain-text statements, connections, transactions,
    and results.

default.py
    Contains default implementations of some of the components defined
    in base.py.  All current database dialects use the classes in
    default.py as base classes for their own database-specific
    implementations.

strategies.py
    The mechanics of constructing ``Engine`` objects are represented
    here.  Defines the ``EngineStrategy`` class which represents how
    to go from arguments specified to the ``create_engine()``
    function, to a fully constructed ``Engine``, including
    initialization of connection pooling, dialects, and specific
    subclasses of ``Engine``.

threadlocal.py
    The ``TLEngine`` class is defined here, which is a subclass of
    the generic ``Engine`` and tracks ``Connection`` and
    ``Transaction`` objects against the identity of the current
    thread.  This allows certain programming patterns based around
    the concept of a "thread-local connection" to be possible.
    The ``TLEngine`` is created by using the "threadlocal" engine
    strategy in conjunction with the ``create_engine()`` function.

url.py
    Defines the ``URL`` class which represents the individual
    components of a string URL passed to ``create_engine()``.  Also
    defines a basic module-loading strategy for the dialect specifier
    within a URL.
"""

# not sure what this was used for
#import sqlalchemy.databases

from .interfaces import (
    Compiled,
    Connectable,
    Dialect,
    ExecutionContext,
    TypeCompiler
)

from .base import (
    Connection,
    Engine,
    NestedTransaction,
    RootTransaction,
    Transaction,
    TwoPhaseTransaction,
    )

from .result import (
    BufferedColumnResultProxy,
    BufferedColumnRow,
    BufferedRowResultProxy,
    FullyBufferedResultProxy,
    ResultProxy,
    RowProxy,
    )

from .util import (
    connection_memoize
    )

from . import util, strategies

default_strategy = 'plain'


def create_engine(*args, **kwargs):
    """Create a new :class:`.Engine` instance.

    The standard calling form is to send the URL as the
    first positional argument, usually a string
    that indicates database dialect and connection arguments.
    Additional keyword arguments may then follow it which
    establish various options on the resulting :class:`.Engine`
    and its underlying :class:`.Dialect` and :class:`.Pool`
    constructs.

    The string form of the URL is
    ``dialect+driver://user:password@host/dbname[?key=value..]``, where
    ``dialect`` is a database name such as ``mysql``, ``oracle``,
    ``postgresql``, etc., and ``driver`` the name of a DBAPI, such as
    ``psycopg2``, ``pyodbc``, ``cx_oracle``, etc.  Alternatively,
    the URL can be an instance of :class:`~sqlalchemy.engine.url.URL`.

    ``**kwargs`` takes a wide variety of options which are routed
    towards their appropriate components.  Arguments may be     specific
    to the :class:`.Engine`, the underlying :class:`.Dialect`, as well as
    the     :class:`.Pool`.  Specific dialects also accept keyword
    arguments that     are unique to that dialect.   Here, we describe the
    parameters     that are common to most :func:`.create_engine()` usage.

    Once established, the newly resulting :class:`.Engine` will
    request a connection from the underlying :class:`.Pool` once
    :meth:`.Engine.connect` is called, or a method which depends on it
    such as :meth:`.Engine.execute` is invoked.   The :class:`.Pool` in turn
    will establish the first actual DBAPI connection when this request
    is received.   The :func:`.create_engine` call itself does **not**
    establish any actual DBAPI connections directly.

    See also:

    :doc:`/core/engines`

    :ref:`connections_toplevel`

    :param case_sensitive=True: if False, result column names
       will match in a case-insensitive fashion, that is,
       ``row['SomeColumn']``.

       .. versionchanged:: 0.8
           By default, result row names match case-sensitively.
           In version 0.7 and prior, all matches were case-insensitive.

    :param connect_args: a dictionary of options which will be
        passed directly to the DBAPI's ``connect()`` method as
        additional keyword arguments.  See the example
        at :ref:`custom_dbapi_args`.

    :param convert_unicode=False: if set to True, sets
        the default behavior of ``convert_unicode`` on the
        :class:`.String` type to ``True``, regardless
        of a setting of ``False`` on an individual
        :class:`.String` type, thus causing all :class:`.String`
        -based columns
        to accommodate Python ``unicode`` objects.  This flag
        is useful as an engine-wide setting when using a
        DBAPI that does not natively support Python
        ``unicode`` objects and raises an error when
        one is received (such as pyodbc with FreeTDS).

        See :class:`.String` for further details on
        what this flag indicates.

    :param creator: a callable which returns a DBAPI connection.
        This creation function will be passed to the underlying
        connection pool and will be used to create all new database
        connections. Usage of this function causes connection
        parameters specified in the URL argument to be bypassed.

    :param echo=False: if True, the Engine will log all statements
        as well as a repr() of their parameter lists to the engines
        logger, which defaults to sys.stdout. The ``echo`` attribute of
        ``Engine`` can be modified at any time to turn logging on and
        off. If set to the string ``"debug"``, result rows will be
        printed to the standard output as well. This flag ultimately
        controls a Python logger; see :ref:`dbengine_logging` for
        information on how to configure logging directly.

    :param echo_pool=False: if True, the connection pool will log
        all checkouts/checkins to the logging stream, which defaults to
        sys.stdout. This flag ultimately controls a Python logger; see
        :ref:`dbengine_logging` for information on how to configure logging
        directly.

    :param encoding: Defaults to ``utf-8``.  This is the string
        encoding used by SQLAlchemy for string encode/decode
        operations which occur within SQLAlchemy, **outside of
        the DBAPI.**  Most modern DBAPIs feature some degree of
        direct support for Python ``unicode`` objects,
        what you see in Python 2 as a string of the form
        ``u'some string'``.  For those scenarios where the
        DBAPI is detected as not supporting a Python ``unicode``
        object, this encoding is used to determine the
        source/destination encoding.  It is **not used**
        for those cases where the DBAPI handles unicode
        directly.

        To properly configure a system to accommodate Python
        ``unicode`` objects, the DBAPI should be
        configured to handle unicode to the greatest
        degree as is appropriate - see
        the notes on unicode pertaining to the specific
        target database in use at :ref:`dialect_toplevel`.

        Areas where string encoding may need to be accommodated
        outside of the DBAPI include zero or more of:

        * the values passed to bound parameters, corresponding to
          the :class:`.Unicode` type or the :class:`.String` type
          when ``convert_unicode`` is ``True``;
        * the values returned in result set columns corresponding
          to the :class:`.Unicode` type or the :class:`.String`
          type when ``convert_unicode`` is ``True``;
        * the string SQL statement passed to the DBAPI's
          ``cursor.execute()`` method;
        * the string names of the keys in the bound parameter
          dictionary passed to the DBAPI's ``cursor.execute()``
          as well as ``cursor.setinputsizes()`` methods;
        * the string column names retrieved from the DBAPI's
          ``cursor.description`` attribute.

        When using Python 3, the DBAPI is required to support
        *all* of the above values as Python ``unicode`` objects,
        which in Python 3 are just known as ``str``.  In Python 2,
        the DBAPI does not specify unicode behavior at all,
        so SQLAlchemy must make decisions for each of the above
        values on a per-DBAPI basis - implementations are
        completely inconsistent in their behavior.

    :param execution_options: Dictionary execution options which will
        be applied to all connections.  See
        :meth:`~sqlalchemy.engine.Connection.execution_options`

    :param implicit_returning=True: When ``True``, a RETURNING-
        compatible construct, if available, will be used to
        fetch newly generated primary key values when a single row
        INSERT statement is emitted with no existing returning()
        clause.  This applies to those backends which support RETURNING
        or a compatible construct, including Postgresql, Firebird, Oracle,
        Microsoft SQL Server.   Set this to ``False`` to disable
        the automatic usage of RETURNING.

    :param label_length=None: optional integer value which limits
        the size of dynamically generated column labels to that many
        characters. If less than 6, labels are generated as
        "_(counter)". If ``None``, the value of
        ``dialect.max_identifier_length`` is used instead.

    :param listeners: A list of one or more
        :class:`~sqlalchemy.interfaces.PoolListener` objects which will
        receive connection pool events.

    :param logging_name:  String identifier which will be used within
        the "name" field of logging records generated within the
        "sqlalchemy.engine" logger. Defaults to a hexstring of the
        object's id.

    :param max_overflow=10: the number of connections to allow in
        connection pool "overflow", that is connections that can be
        opened above and beyond the pool_size setting, which defaults
        to five. this is only used with :class:`~sqlalchemy.pool.QueuePool`.

    :param module=None: reference to a Python module object (the module
        itself, not its string name).  Specifies an alternate DBAPI module to
        be used by the engine's dialect.  Each sub-dialect references a
        specific DBAPI which will be imported before first connect.  This
        parameter causes the import to be bypassed, and the given module to
        be used instead. Can be used for testing of DBAPIs as well as to
        inject "mock" DBAPI implementations into the :class:`.Engine`.

    :param pool=None: an already-constructed instance of
        :class:`~sqlalchemy.pool.Pool`, such as a
        :class:`~sqlalchemy.pool.QueuePool` instance. If non-None, this
        pool will be used directly as the underlying connection pool
        for the engine, bypassing whatever connection parameters are
        present in the URL argument. For information on constructing
        connection pools manually, see :ref:`pooling_toplevel`.

    :param poolclass=None: a :class:`~sqlalchemy.pool.Pool`
        subclass, which will be used to create a connection pool
        instance using the connection parameters given in the URL. Note
        this differs from ``pool`` in that you don't actually
        instantiate the pool in this case, you just indicate what type
        of pool to be used.

    :param pool_logging_name:  String identifier which will be used within
       the "name" field of logging records generated within the
       "sqlalchemy.pool" logger. Defaults to a hexstring of the object's
       id.

    :param pool_size=5: the number of connections to keep open
        inside the connection pool. This used with
        :class:`~sqlalchemy.pool.QueuePool` as
        well as :class:`~sqlalchemy.pool.SingletonThreadPool`.  With
        :class:`~sqlalchemy.pool.QueuePool`, a ``pool_size`` setting
        of 0 indicates no limit; to disable pooling, set ``poolclass`` to
        :class:`~sqlalchemy.pool.NullPool` instead.

    :param pool_recycle=-1: this setting causes the pool to recycle
        connections after the given number of seconds has passed. It
        defaults to -1, or no timeout. For example, setting to 3600
        means connections will be recycled after one hour. Note that
        MySQL in particular will disconnect automatically if no
        activity is detected on a connection for eight hours (although
        this is configurable with the MySQLDB connection itself and the
        server configuration as well).

    :param pool_reset_on_return='rollback': set the "reset on return"
        behavior of the pool, which is whether ``rollback()``,
        ``commit()``, or nothing is called upon connections
        being returned to the pool.  See the docstring for
        ``reset_on_return`` at :class:`.Pool`.

        .. versionadded:: 0.7.6

    :param pool_timeout=30: number of seconds to wait before giving
        up on getting a connection from the pool. This is only used
        with :class:`~sqlalchemy.pool.QueuePool`.

    :param strategy='plain': selects alternate engine implementations.
        Currently available are:

        * the ``threadlocal`` strategy, which is described in
          :ref:`threadlocal_strategy`;
        * the ``mock`` strategy, which dispatches all statement
          execution to a function passed as the argument ``executor``.
          See `example in the FAQ
          <http://www.sqlalchemy.org/trac/wiki/FAQ#HowcanIgettheCREATETABLEDROPTABLEoutputasastring>`_.

    :param executor=None: a function taking arguments
        ``(sql, *multiparams, **params)``, to which the ``mock`` strategy will
        dispatch all statement execution. Used only by ``strategy='mock'``.

    """

    strategy = kwargs.pop('strategy', default_strategy)
    strategy = strategies.strategies[strategy]
    return strategy.create(*args, **kwargs)


def engine_from_config(configuration, prefix='sqlalchemy.', **kwargs):
    """Create a new Engine instance using a configuration dictionary.

    The dictionary is typically produced from a config file where keys
    are prefixed, such as sqlalchemy.url, sqlalchemy.echo, etc.  The
    'prefix' argument indicates the prefix to be searched for.

    A select set of keyword arguments will be "coerced" to their
    expected type based on string values.  In a future release, this
    functionality will be expanded and include dialect-specific
    arguments.
    """

    opts = util._coerce_config(configuration, prefix)
    opts.update(kwargs)
    url = opts.pop('url')
    return create_engine(url, **opts)


__all__ = (
    'create_engine',
    'engine_from_config',
    )
