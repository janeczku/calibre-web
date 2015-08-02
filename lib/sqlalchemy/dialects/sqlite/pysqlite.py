# sqlite/pysqlite.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""
.. dialect:: sqlite+pysqlite
    :name: pysqlite
    :dbapi: sqlite3
    :connectstring: sqlite+pysqlite:///file_path
    :url: http://docs.python.org/library/sqlite3.html

    Note that ``pysqlite`` is the same driver as the ``sqlite3``
    module included with the Python distribution.

Driver
------

When using Python 2.5 and above, the built in ``sqlite3`` driver is
already installed and no additional installation is needed.  Otherwise,
the ``pysqlite2`` driver needs to be present.  This is the same driver as
``sqlite3``, just with a different name.

The ``pysqlite2`` driver will be loaded first, and if not found, ``sqlite3``
is loaded.  This allows an explicitly installed pysqlite driver to take
precedence over the built in one.   As with all dialects, a specific
DBAPI module may be provided to :func:`~sqlalchemy.create_engine()` to control
this explicitly::

    from sqlite3 import dbapi2 as sqlite
    e = create_engine('sqlite+pysqlite:///file.db', module=sqlite)


Connect Strings
---------------

The file specification for the SQLite database is taken as the "database"
portion of the URL.  Note that the format of a SQLAlchemy url is::

    driver://user:pass@host/database

This means that the actual filename to be used starts with the characters to
the **right** of the third slash.   So connecting to a relative filepath
looks like::

    # relative path
    e = create_engine('sqlite:///path/to/database.db')

An absolute path, which is denoted by starting with a slash, means you
need **four** slashes::

    # absolute path
    e = create_engine('sqlite:////path/to/database.db')

To use a Windows path, regular drive specifications and backslashes can be
used. Double backslashes are probably needed::

    # absolute path on Windows
    e = create_engine('sqlite:///C:\\\\path\\\\to\\\\database.db')

The sqlite ``:memory:`` identifier is the default if no filepath is
present.  Specify ``sqlite://`` and nothing else::

    # in-memory database
    e = create_engine('sqlite://')

Compatibility with sqlite3 "native" date and datetime types
-----------------------------------------------------------

The pysqlite driver includes the sqlite3.PARSE_DECLTYPES and
sqlite3.PARSE_COLNAMES options, which have the effect of any column
or expression explicitly cast as "date" or "timestamp" will be converted
to a Python date or datetime object.  The date and datetime types provided
with the pysqlite dialect are not currently compatible with these options,
since they render the ISO date/datetime including microseconds, which
pysqlite's driver does not.   Additionally, SQLAlchemy does not at
this time automatically render the "cast" syntax required for the
freestanding functions "current_timestamp" and "current_date" to return
datetime/date types natively.   Unfortunately, pysqlite
does not provide the standard DBAPI types in ``cursor.description``,
leaving SQLAlchemy with no way to detect these types on the fly
without expensive per-row type checks.

Keeping in mind that pysqlite's parsing option is not recommended,
nor should be necessary, for use with SQLAlchemy, usage of PARSE_DECLTYPES
can be forced if one configures "native_datetime=True" on create_engine()::

    engine = create_engine('sqlite://',
        connect_args={'detect_types': sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES},
        native_datetime=True
    )

With this flag enabled, the DATE and TIMESTAMP types (but note - not the
DATETIME or TIME types...confused yet ?) will not perform any bind parameter
or result processing. Execution of "func.current_date()" will return a string.
"func.current_timestamp()" is registered as returning a DATETIME type in
SQLAlchemy, so this function still receives SQLAlchemy-level result processing.

.. _pysqlite_threading_pooling:

Threading/Pooling Behavior
---------------------------

Pysqlite's default behavior is to prohibit the usage of a single connection
in more than one thread.   This is originally intended to work with older
versions of SQLite that did not support multithreaded operation under
various circumstances.  In particular, older SQLite versions
did not allow a ``:memory:`` database to be used in multiple threads
under any circumstances.

Pysqlite does include a now-undocumented flag known as
``check_same_thread`` which will disable this check, however note that pysqlite
connections are still not safe to use in concurrently in multiple threads.
In particular, any statement execution calls would need to be externally
mutexed, as Pysqlite does not provide for thread-safe propagation of error
messages among other things.   So while even ``:memory:`` databases can be
shared among threads in modern SQLite, Pysqlite doesn't provide enough
thread-safety to make this usage worth it.

SQLAlchemy sets up pooling to work with Pysqlite's default behavior:

* When a ``:memory:`` SQLite database is specified, the dialect by default
  will use :class:`.SingletonThreadPool`. This pool maintains a single
  connection per thread, so that all access to the engine within the current
  thread use the same ``:memory:`` database - other threads would access a
  different ``:memory:`` database.
* When a file-based database is specified, the dialect will use
  :class:`.NullPool` as the source of connections. This pool closes and
  discards connections which are returned to the pool immediately. SQLite
  file-based connections have extremely low overhead, so pooling is not
  necessary. The scheme also prevents a connection from being used again in
  a different thread and works best with SQLite's coarse-grained file locking.

  .. versionchanged:: 0.7
      Default selection of :class:`.NullPool` for SQLite file-based databases.
      Previous versions select :class:`.SingletonThreadPool` by
      default for all SQLite databases.


Using a Memory Database in Multiple Threads
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To use a ``:memory:`` database in a multithreaded scenario, the same connection
object must be shared among threads, since the database exists
only within the scope of that connection.   The
:class:`.StaticPool` implementation will maintain a single connection
globally, and the ``check_same_thread`` flag can be passed to Pysqlite
as ``False``::

    from sqlalchemy.pool import StaticPool
    engine = create_engine('sqlite://',
                        connect_args={'check_same_thread':False},
                        poolclass=StaticPool)

Note that using a ``:memory:`` database in multiple threads requires a recent
version of SQLite.

Using Temporary Tables with SQLite
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Due to the way SQLite deals with temporary tables, if you wish to use a
temporary table in a file-based SQLite database across multiple checkouts
from the connection pool, such as when using an ORM :class:`.Session` where
the temporary table should continue to remain after :meth:`.commit` or
:meth:`.rollback` is called, a pool which maintains a single connection must
be used.   Use :class:`.SingletonThreadPool` if the scope is only needed
within the current thread, or :class:`.StaticPool` is scope is needed within
multiple threads for this case::

    # maintain the same connection per thread
    from sqlalchemy.pool import SingletonThreadPool
    engine = create_engine('sqlite:///mydb.db',
                        poolclass=SingletonThreadPool)


    # maintain the same connection across all threads
    from sqlalchemy.pool import StaticPool
    engine = create_engine('sqlite:///mydb.db',
                        poolclass=StaticPool)

Note that :class:`.SingletonThreadPool` should be configured for the number
of threads that are to be used; beyond that number, connections will be
closed out in a non deterministic way.

Unicode
-------

The pysqlite driver only returns Python ``unicode`` objects in result sets,
never plain strings, and accommodates ``unicode`` objects within bound
parameter values in all cases.   Regardless of the SQLAlchemy string type in
use, string-based result values will by Python ``unicode`` in Python 2.
The :class:`.Unicode` type should still be used to indicate those columns that
require unicode, however, so that non-``unicode`` values passed inadvertently
will emit a warning.  Pysqlite will emit an error if a non-``unicode`` string
is passed containing non-ASCII characters.

.. _pysqlite_serializable:

Serializable Transaction Isolation
----------------------------------

The pysqlite DBAPI driver has a long-standing bug in which transactional
state is not begun until the first DML statement, that is INSERT, UPDATE
or DELETE, is emitted.  A SELECT statement will not cause transactional
state to begin.   While this mode of usage is fine for typical situations
and has the advantage that the SQLite database file is not prematurely
locked, it breaks serializable transaction isolation, which requires
that the database file be locked upon any SQL being emitted.

To work around this issue, the ``BEGIN`` keyword can be emitted
at the start of each transaction.   The following recipe establishes
a :meth:`.ConnectionEvents.begin` handler to achieve this::

    from sqlalchemy import create_engine, event

    engine = create_engine("sqlite:///myfile.db", isolation_level='SERIALIZABLE')

    @event.listens_for(engine, "begin")
    def do_begin(conn):
        conn.execute("BEGIN")

"""

from sqlalchemy.dialects.sqlite.base import SQLiteDialect, DATETIME, DATE
from sqlalchemy import exc, pool
from sqlalchemy import types as sqltypes
from sqlalchemy import util

import os


class _SQLite_pysqliteTimeStamp(DATETIME):
    def bind_processor(self, dialect):
        if dialect.native_datetime:
            return None
        else:
            return DATETIME.bind_processor(self, dialect)

    def result_processor(self, dialect, coltype):
        if dialect.native_datetime:
            return None
        else:
            return DATETIME.result_processor(self, dialect, coltype)


class _SQLite_pysqliteDate(DATE):
    def bind_processor(self, dialect):
        if dialect.native_datetime:
            return None
        else:
            return DATE.bind_processor(self, dialect)

    def result_processor(self, dialect, coltype):
        if dialect.native_datetime:
            return None
        else:
            return DATE.result_processor(self, dialect, coltype)


class SQLiteDialect_pysqlite(SQLiteDialect):
    default_paramstyle = 'qmark'

    colspecs = util.update_copy(
        SQLiteDialect.colspecs,
        {
            sqltypes.Date: _SQLite_pysqliteDate,
            sqltypes.TIMESTAMP: _SQLite_pysqliteTimeStamp,
        }
    )

    # Py3K
    #description_encoding = None

    driver = 'pysqlite'

    def __init__(self, **kwargs):
        SQLiteDialect.__init__(self, **kwargs)

        if self.dbapi is not None:
            sqlite_ver = self.dbapi.version_info
            if sqlite_ver < (2, 1, 3):
                util.warn(
                    ("The installed version of pysqlite2 (%s) is out-dated "
                     "and will cause errors in some cases.  Version 2.1.3 "
                     "or greater is recommended.") %
                    '.'.join([str(subver) for subver in sqlite_ver]))

    @classmethod
    def dbapi(cls):
        try:
            from pysqlite2 import dbapi2 as sqlite
        except ImportError, e:
            try:
                from sqlite3 import dbapi2 as sqlite  # try 2.5+ stdlib name.
            except ImportError:
                raise e
        return sqlite

    @classmethod
    def get_pool_class(cls, url):
        if url.database and url.database != ':memory:':
            return pool.NullPool
        else:
            return pool.SingletonThreadPool

    def _get_server_version_info(self, connection):
        return self.dbapi.sqlite_version_info

    def create_connect_args(self, url):
        if url.username or url.password or url.host or url.port:
            raise exc.ArgumentError(
                "Invalid SQLite URL: %s\n"
                "Valid SQLite URL forms are:\n"
                " sqlite:///:memory: (or, sqlite://)\n"
                " sqlite:///relative/path/to/file.db\n"
                " sqlite:////absolute/path/to/file.db" % (url,))
        filename = url.database or ':memory:'
        if filename != ':memory:':
            filename = os.path.abspath(filename)

        opts = url.query.copy()
        util.coerce_kw_type(opts, 'timeout', float)
        util.coerce_kw_type(opts, 'isolation_level', str)
        util.coerce_kw_type(opts, 'detect_types', int)
        util.coerce_kw_type(opts, 'check_same_thread', bool)
        util.coerce_kw_type(opts, 'cached_statements', int)

        return ([filename], opts)

    def is_disconnect(self, e, connection, cursor):
        return isinstance(e, self.dbapi.ProgrammingError) and \
                "Cannot operate on a closed database." in str(e)

dialect = SQLiteDialect_pysqlite
