# sqlite/base.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""
.. dialect:: sqlite
    :name: SQLite


Date and Time Types
-------------------

SQLite does not have built-in DATE, TIME, or DATETIME types, and pysqlite
does not provide out of the box functionality for translating values between
Python `datetime` objects and a SQLite-supported format.  SQLAlchemy's own
:class:`~sqlalchemy.types.DateTime` and related types provide date formatting
and parsing functionality when SQlite is used. The implementation classes are
:class:`~.sqlite.DATETIME`, :class:`~.sqlite.DATE` and :class:`~.sqlite.TIME`.
These types represent dates and times as ISO formatted strings, which also
nicely support ordering.   There's no reliance on typical "libc" internals
for these functions so historical dates are fully supported.

Auto Incrementing Behavior
--------------------------

Background on SQLite's autoincrement is at: http://sqlite.org/autoinc.html

Two things to note:

* The AUTOINCREMENT keyword is **not** required for SQLite tables to
  generate primary key values automatically. AUTOINCREMENT only means that
  the algorithm used to generate ROWID values should be slightly different.
* SQLite does **not** generate primary key (i.e. ROWID) values, even for
  one column, if the table has a composite (i.e. multi-column) primary key.
  This is regardless of the AUTOINCREMENT keyword being present or not.

To specifically render the AUTOINCREMENT keyword on the primary key
column when rendering DDL, add the flag ``sqlite_autoincrement=True``
to the Table construct::

    Table('sometable', metadata,
            Column('id', Integer, primary_key=True),
            sqlite_autoincrement=True)

Transaction Isolation Level
---------------------------

:func:`.create_engine` accepts an ``isolation_level`` parameter which
results in the command ``PRAGMA read_uncommitted <level>`` being invoked for
every new connection.   Valid values for this parameter are ``SERIALIZABLE``
and ``READ UNCOMMITTED`` corresponding to a value of 0 and 1, respectively.
See the section :ref:`pysqlite_serializable` for an important workaround
when using serializable isolation with Pysqlite.

Database Locking Behavior / Concurrency
---------------------------------------

Note that SQLite is not designed for a high level of concurrency.   The
database itself, being a file, is locked completely during write operations
and within transactions, meaning exactly one connection has exclusive access
to the database during this period - all other connections will be blocked
during this time.

The Python DBAPI specification also calls for a connection model that is always
in a transaction; there is no BEGIN method, only commit and rollback.  This
implies that a SQLite DBAPI driver would technically allow only serialized
access to a particular database file at all times.   The pysqlite driver
attempts to ameliorate this by deferring the actual BEGIN statement until
the first DML (INSERT, UPDATE, or DELETE) is received within a
transaction.  While this breaks serializable isolation, it at least delays
the exclusive locking inherent in SQLite's design.

SQLAlchemy's default mode of usage with the ORM is known
as "autocommit=False", which means the moment the :class:`.Session` begins to
be used, a transaction is begun.   As the :class:`.Session` is used, the
autoflush feature, also on by default, will flush out pending changes to the
database before each query.  The effect of this is that a :class:`.Session`
used in its default mode will often emit DML early on, long before the
transaction is actually committed.  This again will have the effect of
serializing access to the SQLite database.   If highly concurrent reads are
desired against the SQLite database, it is advised that the autoflush feature
be disabled, and potentially even that autocommit be re-enabled, which has
the effect of each SQL statement and flush committing changes immediately.

For more information on SQLite's lack of concurrency by design, please
see `Situations Where Another RDBMS May Work Better - High
Concurrency <http://www.sqlite.org/whentouse.html>`_ near the bottom of
the page.

.. _sqlite_foreign_keys:

Foreign Key Support
-------------------

SQLite supports FOREIGN KEY syntax when emitting CREATE statements for tables,
however by default these constraints have no effect on the operation
of the table.

Constraint checking on SQLite has three prerequisites:

* At least version 3.6.19 of SQLite must be in use
* The SQLite libary must be compiled *without* the SQLITE_OMIT_FOREIGN_KEY
  or SQLITE_OMIT_TRIGGER symbols enabled.
* The ``PRAGMA foreign_keys = ON`` statement must be emitted on all connections
  before use.

SQLAlchemy allows for the ``PRAGMA`` statement to be emitted automatically
for new connections through the usage of events::

    from sqlalchemy.engine import Engine
    from sqlalchemy import event

    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

.. seealso::

    `SQLite Foreign Key Support <http://www.sqlite.org/foreignkeys.html>`_ -
    on the SQLite web site.

    :ref:`event_toplevel` - SQLAlchemy event API.

"""

import datetime
import re

from sqlalchemy import sql, exc
from sqlalchemy.engine import default, base, reflection
from sqlalchemy import types as sqltypes
from sqlalchemy import util
from sqlalchemy.sql import compiler
from sqlalchemy import processors

from sqlalchemy.types import BIGINT, BLOB, BOOLEAN, CHAR,\
    DECIMAL, FLOAT, REAL, INTEGER, NUMERIC, SMALLINT, TEXT,\
    TIMESTAMP, VARCHAR


class _DateTimeMixin(object):
    _reg = None
    _storage_format = None

    def __init__(self, storage_format=None, regexp=None, **kw):
        super(_DateTimeMixin, self).__init__(**kw)
        if regexp is not None:
            self._reg = re.compile(regexp)
        if storage_format is not None:
            self._storage_format = storage_format

    def adapt(self, cls, **kw):
        if self._storage_format:
            kw["storage_format"] = self._storage_format
        if self._reg:
            kw["regexp"] = self._reg
        return util.constructor_copy(self, cls, **kw)

class DATETIME(_DateTimeMixin, sqltypes.DateTime):
    """Represent a Python datetime object in SQLite using a string.

    The default string storage format is::

        "%(year)04d-%(month)02d-%(day)02d %(hour)02d:%(min)02d:%(second)02d.%(microsecond)06d"

    e.g.::

        2011-03-15 12:05:57.10558

    The storage format can be customized to some degree using the
    ``storage_format`` and ``regexp`` parameters, such as::

        import re
        from sqlalchemy.dialects.sqlite import DATETIME

        dt = DATETIME(
            storage_format="%(year)04d/%(month)02d/%(day)02d %(hour)02d:%(min)02d:%(second)02d",
            regexp=r"(\d+)/(\d+)/(\d+) (\d+)-(\d+)-(\d+)"
        )

    :param storage_format: format string which will be applied to the
     dict with keys year, month, day, hour, minute, second, and microsecond.

    :param regexp: regular expression which will be applied to
     incoming result rows. If the regexp contains named groups, the
     resulting match dict is applied to the Python datetime() constructor
     as keyword arguments. Otherwise, if positional groups are used, the
     the datetime() constructor is called with positional arguments via
     ``*map(int, match_obj.groups(0))``.
    """

    _storage_format = (
        "%(year)04d-%(month)02d-%(day)02d "
        "%(hour)02d:%(minute)02d:%(second)02d.%(microsecond)06d"
    )

    def __init__(self, *args, **kwargs):
        truncate_microseconds = kwargs.pop('truncate_microseconds', False)
        super(DATETIME, self).__init__(*args, **kwargs)
        if truncate_microseconds:
            assert 'storage_format' not in kwargs, "You can specify only "\
                "one of truncate_microseconds or storage_format."
            assert 'regexp' not in kwargs, "You can specify only one of "\
                "truncate_microseconds or regexp."
            self._storage_format = (
                "%(year)04d-%(month)02d-%(day)02d "
                "%(hour)02d:%(minute)02d:%(second)02d"
            )

    def bind_processor(self, dialect):
        datetime_datetime = datetime.datetime
        datetime_date = datetime.date
        format = self._storage_format

        def process(value):
            if value is None:
                return None
            elif isinstance(value, datetime_datetime):
                return format % {
                    'year': value.year,
                    'month': value.month,
                    'day': value.day,
                    'hour': value.hour,
                    'minute': value.minute,
                    'second': value.second,
                    'microsecond': value.microsecond,
                }
            elif isinstance(value, datetime_date):
                return format % {
                    'year': value.year,
                    'month': value.month,
                    'day': value.day,
                    'hour': 0,
                    'minute': 0,
                    'second': 0,
                    'microsecond': 0,
                }
            else:
                raise TypeError("SQLite DateTime type only accepts Python "
                                "datetime and date objects as input.")
        return process

    def result_processor(self, dialect, coltype):
        if self._reg:
            return processors.str_to_datetime_processor_factory(
                self._reg, datetime.datetime)
        else:
            return processors.str_to_datetime


class DATE(_DateTimeMixin, sqltypes.Date):
    """Represent a Python date object in SQLite using a string.

    The default string storage format is::

        "%(year)04d-%(month)02d-%(day)02d"

    e.g.::

        2011-03-15

    The storage format can be customized to some degree using the
    ``storage_format`` and ``regexp`` parameters, such as::

        import re
        from sqlalchemy.dialects.sqlite import DATE

        d = DATE(
                storage_format="%(month)02d/%(day)02d/%(year)04d",
                regexp=re.compile("(?P<month>\d+)/(?P<day>\d+)/(?P<year>\d+)")
            )

    :param storage_format: format string which will be applied to the
     dict with keys year, month, and day.

    :param regexp: regular expression which will be applied to
     incoming result rows. If the regexp contains named groups, the
     resulting match dict is applied to the Python date() constructor
     as keyword arguments. Otherwise, if positional groups are used, the
     the date() constructor is called with positional arguments via
     ``*map(int, match_obj.groups(0))``.
    """

    _storage_format = "%(year)04d-%(month)02d-%(day)02d"

    def bind_processor(self, dialect):
        datetime_date = datetime.date
        format = self._storage_format

        def process(value):
            if value is None:
                return None
            elif isinstance(value, datetime_date):
                return format % {
                    'year': value.year,
                    'month': value.month,
                    'day': value.day,
                }
            else:
                raise TypeError("SQLite Date type only accepts Python "
                                "date objects as input.")
        return process

    def result_processor(self, dialect, coltype):
        if self._reg:
            return processors.str_to_datetime_processor_factory(
                self._reg, datetime.date)
        else:
            return processors.str_to_date


class TIME(_DateTimeMixin, sqltypes.Time):
    """Represent a Python time object in SQLite using a string.

    The default string storage format is::

        "%(hour)02d:%(minute)02d:%(second)02d.%(microsecond)06d"

    e.g.::

        12:05:57.10558

    The storage format can be customized to some degree using the
    ``storage_format`` and ``regexp`` parameters, such as::

        import re
        from sqlalchemy.dialects.sqlite import TIME

        t = TIME(
            storage_format="%(hour)02d-%(minute)02d-%(second)02d-%(microsecond)06d",
            regexp=re.compile("(\d+)-(\d+)-(\d+)-(?:-(\d+))?")
        )

    :param storage_format: format string which will be applied to the
     dict with keys hour, minute, second, and microsecond.

    :param regexp: regular expression which will be applied to
     incoming result rows. If the regexp contains named groups, the
     resulting match dict is applied to the Python time() constructor
     as keyword arguments. Otherwise, if positional groups are used, the
     the time() constructor is called with positional arguments via
     ``*map(int, match_obj.groups(0))``.
    """

    _storage_format = "%(hour)02d:%(minute)02d:%(second)02d.%(microsecond)06d"

    def __init__(self, *args, **kwargs):
        truncate_microseconds = kwargs.pop('truncate_microseconds', False)
        super(TIME, self).__init__(*args, **kwargs)
        if truncate_microseconds:
            assert 'storage_format' not in kwargs, "You can specify only "\
                "one of truncate_microseconds or storage_format."
            assert 'regexp' not in kwargs, "You can specify only one of "\
                "truncate_microseconds or regexp."
            self._storage_format = "%(hour)02d:%(minute)02d:%(second)02d"

    def bind_processor(self, dialect):
        datetime_time = datetime.time
        format = self._storage_format

        def process(value):
            if value is None:
                return None
            elif isinstance(value, datetime_time):
                return format % {
                    'hour': value.hour,
                    'minute': value.minute,
                    'second': value.second,
                    'microsecond': value.microsecond,
                }
            else:
                raise TypeError("SQLite Time type only accepts Python "
                                "time objects as input.")
        return process

    def result_processor(self, dialect, coltype):
        if self._reg:
            return processors.str_to_datetime_processor_factory(
                self._reg, datetime.time)
        else:
            return processors.str_to_time

colspecs = {
    sqltypes.Date: DATE,
    sqltypes.DateTime: DATETIME,
    sqltypes.Time: TIME,
}

ischema_names = {
    'BIGINT': sqltypes.BIGINT,
    'BLOB': sqltypes.BLOB,
    'BOOL': sqltypes.BOOLEAN,
    'BOOLEAN': sqltypes.BOOLEAN,
    'CHAR': sqltypes.CHAR,
    'DATE': sqltypes.DATE,
    'DATETIME': sqltypes.DATETIME,
    'DECIMAL': sqltypes.DECIMAL,
    'FLOAT': sqltypes.FLOAT,
    'INT': sqltypes.INTEGER,
    'INTEGER': sqltypes.INTEGER,
    'NUMERIC': sqltypes.NUMERIC,
    'REAL': sqltypes.REAL,
    'SMALLINT': sqltypes.SMALLINT,
    'TEXT': sqltypes.TEXT,
    'TIME': sqltypes.TIME,
    'TIMESTAMP': sqltypes.TIMESTAMP,
    'VARCHAR': sqltypes.VARCHAR,
    'NVARCHAR': sqltypes.NVARCHAR,
    'NCHAR': sqltypes.NCHAR,
}


class SQLiteCompiler(compiler.SQLCompiler):
    extract_map = util.update_copy(
        compiler.SQLCompiler.extract_map,
        {
        'month': '%m',
        'day': '%d',
        'year': '%Y',
        'second': '%S',
        'hour': '%H',
        'doy': '%j',
        'minute': '%M',
        'epoch': '%s',
        'dow': '%w',
        'week': '%W'
    })

    def visit_now_func(self, fn, **kw):
        return "CURRENT_TIMESTAMP"

    def visit_localtimestamp_func(self, func, **kw):
        return 'DATETIME(CURRENT_TIMESTAMP, "localtime")'

    def visit_true(self, expr, **kw):
        return '1'

    def visit_false(self, expr, **kw):
        return '0'

    def visit_char_length_func(self, fn, **kw):
        return "length%s" % self.function_argspec(fn)

    def visit_cast(self, cast, **kwargs):
        if self.dialect.supports_cast:
            return super(SQLiteCompiler, self).visit_cast(cast)
        else:
            return self.process(cast.clause)

    def visit_extract(self, extract, **kw):
        try:
            return "CAST(STRFTIME('%s', %s) AS INTEGER)" % (
                self.extract_map[extract.field],
                self.process(extract.expr, **kw)
            )
        except KeyError:
            raise exc.CompileError(
                "%s is not a valid extract argument." % extract.field)

    def limit_clause(self, select):
        text = ""
        if select._limit is not None:
            text += "\n LIMIT " + self.process(sql.literal(select._limit))
        if select._offset is not None:
            if select._limit is None:
                text += "\n LIMIT " + self.process(sql.literal(-1))
            text += " OFFSET " + self.process(sql.literal(select._offset))
        else:
            text += " OFFSET " + self.process(sql.literal(0))
        return text

    def for_update_clause(self, select):
        # sqlite has no "FOR UPDATE" AFAICT
        return ''


class SQLiteDDLCompiler(compiler.DDLCompiler):

    def get_column_specification(self, column, **kwargs):
        coltype = self.dialect.type_compiler.process(column.type)
        colspec = self.preparer.format_column(column) + " " + coltype
        default = self.get_column_default_string(column)
        if default is not None:
            colspec += " DEFAULT " + default

        if not column.nullable:
            colspec += " NOT NULL"

        if (column.primary_key and
            column.table.kwargs.get('sqlite_autoincrement', False) and
            len(column.table.primary_key.columns) == 1 and
            issubclass(column.type._type_affinity, sqltypes.Integer) and
            not column.foreign_keys):
                colspec += " PRIMARY KEY AUTOINCREMENT"

        return colspec

    def visit_primary_key_constraint(self, constraint):
        # for columns with sqlite_autoincrement=True,
        # the PRIMARY KEY constraint can only be inline
        # with the column itself.
        if len(constraint.columns) == 1:
            c = list(constraint)[0]
            if c.primary_key and \
                c.table.kwargs.get('sqlite_autoincrement', False) and \
                issubclass(c.type._type_affinity, sqltypes.Integer) and \
                not c.foreign_keys:
                return None

        return super(SQLiteDDLCompiler, self).\
                    visit_primary_key_constraint(constraint)

    def visit_foreign_key_constraint(self, constraint):

        local_table = constraint._elements.values()[0].parent.table
        remote_table = list(constraint._elements.values())[0].column.table

        if local_table.schema != remote_table.schema:
            return None
        else:
            return super(SQLiteDDLCompiler, self).visit_foreign_key_constraint(constraint)

    def define_constraint_remote_table(self, constraint, table, preparer):
        """Format the remote table clause of a CREATE CONSTRAINT clause."""

        return preparer.format_table(table, use_schema=False)

    def visit_create_index(self, create):
        return super(SQLiteDDLCompiler, self).\
                    visit_create_index(create, include_table_schema=False)


class SQLiteTypeCompiler(compiler.GenericTypeCompiler):
    def visit_large_binary(self, type_):
        return self.visit_BLOB(type_)


class SQLiteIdentifierPreparer(compiler.IdentifierPreparer):
    reserved_words = set([
        'add', 'after', 'all', 'alter', 'analyze', 'and', 'as', 'asc',
        'attach', 'autoincrement', 'before', 'begin', 'between', 'by',
        'cascade', 'case', 'cast', 'check', 'collate', 'column', 'commit',
        'conflict', 'constraint', 'create', 'cross', 'current_date',
        'current_time', 'current_timestamp', 'database', 'default',
        'deferrable', 'deferred', 'delete', 'desc', 'detach', 'distinct',
        'drop', 'each', 'else', 'end', 'escape', 'except', 'exclusive',
        'explain', 'false', 'fail', 'for', 'foreign', 'from', 'full', 'glob',
        'group', 'having', 'if', 'ignore', 'immediate', 'in', 'index',
        'indexed', 'initially', 'inner', 'insert', 'instead', 'intersect',
        'into', 'is', 'isnull', 'join', 'key', 'left', 'like', 'limit',
        'match', 'natural', 'not', 'notnull', 'null', 'of', 'offset', 'on',
        'or', 'order', 'outer', 'plan', 'pragma', 'primary', 'query',
        'raise', 'references', 'reindex', 'rename', 'replace', 'restrict',
        'right', 'rollback', 'row', 'select', 'set', 'table', 'temp',
        'temporary', 'then', 'to', 'transaction', 'trigger', 'true', 'union',
        'unique', 'update', 'using', 'vacuum', 'values', 'view', 'virtual',
        'when', 'where',
        ])

    def format_index(self, index, use_schema=True, name=None):
        """Prepare a quoted index and schema name."""

        if name is None:
            name = index.name
        result = self.quote(name, index.quote)
        if (not self.omit_schema and
            use_schema and
            getattr(index.table, "schema", None)):
            result = self.quote_schema(
                index.table.schema, index.table.quote_schema) + "." + result
        return result


class SQLiteExecutionContext(default.DefaultExecutionContext):
    @util.memoized_property
    def _preserve_raw_colnames(self):
        return self.execution_options.get("sqlite_raw_colnames", False)

    def _translate_colname(self, colname):
        # adjust for dotted column names.  SQLite
        # in the case of UNION may store col names as
        # "tablename.colname"
        # in cursor.description
        if not self._preserve_raw_colnames  and "." in colname:
            return colname.split(".")[1], colname
        else:
            return colname, None


class SQLiteDialect(default.DefaultDialect):
    name = 'sqlite'
    supports_alter = False
    supports_unicode_statements = True
    supports_unicode_binds = True
    supports_default_values = True
    supports_empty_insert = False
    supports_cast = True
    supports_multivalues_insert = True

    default_paramstyle = 'qmark'
    execution_ctx_cls = SQLiteExecutionContext
    statement_compiler = SQLiteCompiler
    ddl_compiler = SQLiteDDLCompiler
    type_compiler = SQLiteTypeCompiler
    preparer = SQLiteIdentifierPreparer
    ischema_names = ischema_names
    colspecs = colspecs
    isolation_level = None

    supports_cast = True
    supports_default_values = True

    _broken_fk_pragma_quotes = False

    def __init__(self, isolation_level=None, native_datetime=False, **kwargs):
        default.DefaultDialect.__init__(self, **kwargs)
        self.isolation_level = isolation_level

        # this flag used by pysqlite dialect, and perhaps others in the
        # future, to indicate the driver is handling date/timestamp
        # conversions (and perhaps datetime/time as well on some
        # hypothetical driver ?)
        self.native_datetime = native_datetime

        if self.dbapi is not None:
            self.supports_default_values = \
                                self.dbapi.sqlite_version_info >= (3, 3, 8)
            self.supports_cast = \
                                self.dbapi.sqlite_version_info >= (3, 2, 3)
            self.supports_multivalues_insert = \
                                self.dbapi.sqlite_version_info >= (3, 7, 11)
                                #  http://www.sqlite.org/releaselog/3_7_11.html

            # see http://www.sqlalchemy.org/trac/ticket/2568
            # as well as http://www.sqlite.org/src/info/600482d161
            self._broken_fk_pragma_quotes = \
                                self.dbapi.sqlite_version_info < (3, 6, 14)


    _isolation_lookup = {
        'READ UNCOMMITTED': 1,
        'SERIALIZABLE': 0
    }

    def set_isolation_level(self, connection, level):
        try:
            isolation_level = self._isolation_lookup[level.replace('_', ' ')]
        except KeyError:
            raise exc.ArgumentError(
                "Invalid value '%s' for isolation_level. "
                "Valid isolation levels for %s are %s" %
                (level, self.name, ", ".join(self._isolation_lookup))
                )
        cursor = connection.cursor()
        cursor.execute("PRAGMA read_uncommitted = %d" % isolation_level)
        cursor.close()

    def get_isolation_level(self, connection):
        cursor = connection.cursor()
        cursor.execute('PRAGMA read_uncommitted')
        res = cursor.fetchone()
        if res:
            value = res[0]
        else:
            # http://www.sqlite.org/changes.html#version_3_3_3
            # "Optional READ UNCOMMITTED isolation (instead of the
            # default isolation level of SERIALIZABLE) and
            # table level locking when database connections
            # share a common cache.""
            # pre-SQLite 3.3.0 default to 0
            value = 0
        cursor.close()
        if value == 0:
            return "SERIALIZABLE"
        elif value == 1:
            return "READ UNCOMMITTED"
        else:
            assert False, "Unknown isolation level %s" % value

    def on_connect(self):
        if self.isolation_level is not None:
            def connect(conn):
                self.set_isolation_level(conn, self.isolation_level)
            return connect
        else:
            return None

    @reflection.cache
    def get_table_names(self, connection, schema=None, **kw):
        if schema is not None:
            qschema = self.identifier_preparer.quote_identifier(schema)
            master = '%s.sqlite_master' % qschema
            s = ("SELECT name FROM %s "
                 "WHERE type='table' ORDER BY name") % (master,)
            rs = connection.execute(s)
        else:
            try:
                s = ("SELECT name FROM "
                     " (SELECT * FROM sqlite_master UNION ALL "
                     "  SELECT * FROM sqlite_temp_master) "
                     "WHERE type='table' ORDER BY name")
                rs = connection.execute(s)
            except exc.DBAPIError:
                s = ("SELECT name FROM sqlite_master "
                     "WHERE type='table' ORDER BY name")
                rs = connection.execute(s)

        return [row[0] for row in rs]

    def has_table(self, connection, table_name, schema=None):
        quote = self.identifier_preparer.quote_identifier
        if schema is not None:
            pragma = "PRAGMA %s." % quote(schema)
        else:
            pragma = "PRAGMA "
        qtable = quote(table_name)
        statement = "%stable_info(%s)" % (pragma, qtable)
        cursor = _pragma_cursor(connection.execute(statement))
        row = cursor.fetchone()

        # consume remaining rows, to work around
        # http://www.sqlite.org/cvstrac/tktview?tn=1884
        while not cursor.closed and cursor.fetchone() is not None:
            pass

        return (row is not None)

    @reflection.cache
    def get_view_names(self, connection, schema=None, **kw):
        if schema is not None:
            qschema = self.identifier_preparer.quote_identifier(schema)
            master = '%s.sqlite_master' % qschema
            s = ("SELECT name FROM %s "
                 "WHERE type='view' ORDER BY name") % (master,)
            rs = connection.execute(s)
        else:
            try:
                s = ("SELECT name FROM "
                     " (SELECT * FROM sqlite_master UNION ALL "
                     "  SELECT * FROM sqlite_temp_master) "
                     "WHERE type='view' ORDER BY name")
                rs = connection.execute(s)
            except exc.DBAPIError:
                s = ("SELECT name FROM sqlite_master "
                     "WHERE type='view' ORDER BY name")
                rs = connection.execute(s)

        return [row[0] for row in rs]

    @reflection.cache
    def get_view_definition(self, connection, view_name, schema=None, **kw):
        quote = self.identifier_preparer.quote_identifier
        if schema is not None:
            qschema = self.identifier_preparer.quote_identifier(schema)
            master = '%s.sqlite_master' % qschema
            s = ("SELECT sql FROM %s WHERE name = '%s'"
                 "AND type='view'") % (master, view_name)
            rs = connection.execute(s)
        else:
            try:
                s = ("SELECT sql FROM "
                     " (SELECT * FROM sqlite_master UNION ALL "
                     "  SELECT * FROM sqlite_temp_master) "
                     "WHERE name = '%s' "
                     "AND type='view'") % view_name
                rs = connection.execute(s)
            except exc.DBAPIError:
                s = ("SELECT sql FROM sqlite_master WHERE name = '%s' "
                     "AND type='view'") % view_name
                rs = connection.execute(s)

        result = rs.fetchall()
        if result:
            return result[0].sql

    @reflection.cache
    def get_columns(self, connection, table_name, schema=None, **kw):
        quote = self.identifier_preparer.quote_identifier
        if schema is not None:
            pragma = "PRAGMA %s." % quote(schema)
        else:
            pragma = "PRAGMA "
        qtable = quote(table_name)
        statement = "%stable_info(%s)" % (pragma, qtable)
        c = _pragma_cursor(connection.execute(statement))

        rows = c.fetchall()
        columns = []
        for row in rows:
            (name, type_, nullable, default, primary_key) = \
                (row[1], row[2].upper(), not row[3],
                row[4], row[5])

            columns.append(self._get_column_info(name, type_, nullable,
                                    default, primary_key))
        return columns

    def _get_column_info(self, name, type_, nullable,
                                    default, primary_key):

        match = re.match(r'(\w+)(\(.*?\))?', type_)
        if match:
            coltype = match.group(1)
            args = match.group(2)
        else:
            coltype = "VARCHAR"
            args = ''
        try:
            coltype = self.ischema_names[coltype]
            if args is not None:
                args = re.findall(r'(\d+)', args)
                coltype = coltype(*[int(a) for a in args])
        except KeyError:
            util.warn("Did not recognize type '%s' of column '%s'" %
                      (coltype, name))
            coltype = sqltypes.NullType()

        if default is not None:
            default = unicode(default)

        return {
            'name': name,
            'type': coltype,
            'nullable': nullable,
            'default': default,
            'autoincrement': default is None,
            'primary_key': primary_key
        }

    @reflection.cache
    def get_pk_constraint(self, connection, table_name, schema=None, **kw):
        cols = self.get_columns(connection, table_name, schema, **kw)
        pkeys = []
        for col in cols:
            if col['primary_key']:
                pkeys.append(col['name'])
        return {'constrained_columns': pkeys, 'name': None}

    @reflection.cache
    def get_foreign_keys(self, connection, table_name, schema=None, **kw):
        quote = self.identifier_preparer.quote_identifier
        if schema is not None:
            pragma = "PRAGMA %s." % quote(schema)
        else:
            pragma = "PRAGMA "
        qtable = quote(table_name)
        statement = "%sforeign_key_list(%s)" % (pragma, qtable)
        c = _pragma_cursor(connection.execute(statement))
        fkeys = []
        fks = {}
        while True:
            row = c.fetchone()
            if row is None:
                break
            (numerical_id, rtbl, lcol, rcol) = (row[0], row[2], row[3], row[4])

            self._parse_fk(fks, fkeys, numerical_id, rtbl, lcol, rcol)
        return fkeys

    def _parse_fk(self, fks, fkeys, numerical_id, rtbl, lcol, rcol):
        # sqlite won't return rcol if the table
        # was created with REFERENCES <tablename>, no col
        if rcol is None:
            rcol = lcol

        if self._broken_fk_pragma_quotes:
            rtbl = re.sub(r'^[\"\[`\']|[\"\]`\']$', '', rtbl)

        try:
            fk = fks[numerical_id]
        except KeyError:
            fk = {
                'name': None,
                'constrained_columns': [],
                'referred_schema': None,
                'referred_table': rtbl,
                'referred_columns': []
            }
            fkeys.append(fk)
            fks[numerical_id] = fk

        if lcol not in fk['constrained_columns']:
            fk['constrained_columns'].append(lcol)
        if rcol not in fk['referred_columns']:
            fk['referred_columns'].append(rcol)
        return fk

    @reflection.cache
    def get_indexes(self, connection, table_name, schema=None, **kw):
        quote = self.identifier_preparer.quote_identifier
        if schema is not None:
            pragma = "PRAGMA %s." % quote(schema)
        else:
            pragma = "PRAGMA "
        include_auto_indexes = kw.pop('include_auto_indexes', False)
        qtable = quote(table_name)
        statement = "%sindex_list(%s)" % (pragma, qtable)
        c = _pragma_cursor(connection.execute(statement))
        indexes = []
        while True:
            row = c.fetchone()
            if row is None:
                break
            # ignore implicit primary key index.
            # http://www.mail-archive.com/sqlite-users@sqlite.org/msg30517.html
            elif (not include_auto_indexes and
                  row[1].startswith('sqlite_autoindex')):
                continue

            indexes.append(dict(name=row[1], column_names=[], unique=row[2]))
        # loop thru unique indexes to get the column names.
        for idx in indexes:
            statement = "%sindex_info(%s)" % (pragma, quote(idx['name']))
            c = connection.execute(statement)
            cols = idx['column_names']
            while True:
                row = c.fetchone()
                if row is None:
                    break
                cols.append(row[2])
        return indexes


def _pragma_cursor(cursor):
    """work around SQLite issue whereby cursor.description
    is blank when PRAGMA returns no rows."""

    if cursor.closed:
        cursor.fetchone = lambda: None
        cursor.fetchall = lambda: []
    return cursor
