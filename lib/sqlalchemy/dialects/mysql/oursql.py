# mysql/oursql.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""

.. dialect:: mysql+oursql
    :name: OurSQL
    :dbapi: oursql
    :connectstring: mysql+oursql://<user>:<password>@<host>[:<port>]/<dbname>
    :url: http://packages.python.org/oursql/

Unicode
-------

oursql defaults to using ``utf8`` as the connection charset, but other
encodings may be used instead. Like the MySQL-Python driver, unicode support
can be completely disabled::

  # oursql sets the connection charset to utf8 automatically; all strings come
  # back as utf8 str
  create_engine('mysql+oursql:///mydb?use_unicode=0')

To not automatically use ``utf8`` and instead use whatever the connection
defaults to, there is a separate parameter::

  # use the default connection charset; all strings come back as unicode
  create_engine('mysql+oursql:///mydb?default_charset=1')

  # use latin1 as the connection charset; all strings come back as unicode
  create_engine('mysql+oursql:///mydb?charset=latin1')
"""

import re

from .base import (BIT, MySQLDialect, MySQLExecutionContext)
from ... import types as sqltypes, util


class _oursqlBIT(BIT):
    def result_processor(self, dialect, coltype):
        """oursql already converts mysql bits, so."""

        return None


class MySQLExecutionContext_oursql(MySQLExecutionContext):

    @property
    def plain_query(self):
        return self.execution_options.get('_oursql_plain_query', False)


class MySQLDialect_oursql(MySQLDialect):
    driver = 'oursql'
# Py2K
    supports_unicode_binds = True
    supports_unicode_statements = True
# end Py2K

    supports_native_decimal = True

    supports_sane_rowcount = True
    supports_sane_multi_rowcount = True
    execution_ctx_cls = MySQLExecutionContext_oursql

    colspecs = util.update_copy(
        MySQLDialect.colspecs,
        {
            sqltypes.Time: sqltypes.Time,
            BIT: _oursqlBIT,
        }
    )

    @classmethod
    def dbapi(cls):
        return __import__('oursql')

    def do_execute(self, cursor, statement, parameters, context=None):
        """Provide an implementation of *cursor.execute(statement, parameters)*."""

        if context and context.plain_query:
            cursor.execute(statement, plain_query=True)
        else:
            cursor.execute(statement, parameters)

    def do_begin(self, connection):
        connection.cursor().execute('BEGIN', plain_query=True)

    def _xa_query(self, connection, query, xid):
# Py2K
        arg = connection.connection._escape_string(xid)
# end Py2K
# Py3K
#        charset = self._connection_charset
#        arg = connection.connection._escape_string(xid.encode(charset)).decode(charset)
        arg = "'%s'" % arg
        connection.execution_options(_oursql_plain_query=True).execute(query % arg)

    # Because mysql is bad, these methods have to be
    # reimplemented to use _PlainQuery. Basically, some queries
    # refuse to return any data if they're run through
    # the parameterized query API, or refuse to be parameterized
    # in the first place.
    def do_begin_twophase(self, connection, xid):
        self._xa_query(connection, 'XA BEGIN %s', xid)

    def do_prepare_twophase(self, connection, xid):
        self._xa_query(connection, 'XA END %s', xid)
        self._xa_query(connection, 'XA PREPARE %s', xid)

    def do_rollback_twophase(self, connection, xid, is_prepared=True,
                             recover=False):
        if not is_prepared:
            self._xa_query(connection, 'XA END %s', xid)
        self._xa_query(connection, 'XA ROLLBACK %s', xid)

    def do_commit_twophase(self, connection, xid, is_prepared=True,
                           recover=False):
        if not is_prepared:
            self.do_prepare_twophase(connection, xid)
        self._xa_query(connection, 'XA COMMIT %s', xid)

    # Q: why didn't we need all these "plain_query" overrides earlier ?
    # am i on a newer/older version of OurSQL ?
    def has_table(self, connection, table_name, schema=None):
        return MySQLDialect.has_table(
          self,
          connection.connect().execution_options(_oursql_plain_query=True),
          table_name,
          schema
        )

    def get_table_options(self, connection, table_name, schema=None, **kw):
        return MySQLDialect.get_table_options(
            self,
            connection.connect().execution_options(_oursql_plain_query=True),
            table_name,
            schema=schema,
            **kw
        )

    def get_columns(self, connection, table_name, schema=None, **kw):
        return MySQLDialect.get_columns(
            self,
            connection.connect().execution_options(_oursql_plain_query=True),
            table_name,
            schema=schema,
            **kw
        )

    def get_view_names(self, connection, schema=None, **kw):
        return MySQLDialect.get_view_names(
            self,
            connection.connect().execution_options(_oursql_plain_query=True),
            schema=schema,
            **kw
        )

    def get_table_names(self, connection, schema=None, **kw):
        return MySQLDialect.get_table_names(
            self,
            connection.connect().execution_options(_oursql_plain_query=True),
            schema
        )

    def get_schema_names(self, connection, **kw):
        return MySQLDialect.get_schema_names(
            self,
            connection.connect().execution_options(_oursql_plain_query=True),
            **kw
        )

    def initialize(self, connection):
        return MySQLDialect.initialize(
            self,
            connection.execution_options(_oursql_plain_query=True)
        )

    def _show_create_table(self, connection, table, charset=None,
                           full_name=None):
        return MySQLDialect._show_create_table(
            self,
            connection.contextual_connect(close_with_result=True).
            execution_options(_oursql_plain_query=True),
            table, charset, full_name
        )

    def is_disconnect(self, e, connection, cursor):
        if isinstance(e, self.dbapi.ProgrammingError):
            return e.errno is None and 'cursor' not in e.args[1] and e.args[1].endswith('closed')
        else:
            return e.errno in (2006, 2013, 2014, 2045, 2055)

    def create_connect_args(self, url):
        opts = url.translate_connect_args(database='db', username='user',
                                          password='passwd')
        opts.update(url.query)

        util.coerce_kw_type(opts, 'port', int)
        util.coerce_kw_type(opts, 'compress', bool)
        util.coerce_kw_type(opts, 'autoping', bool)
        util.coerce_kw_type(opts, 'raise_on_warnings', bool)

        util.coerce_kw_type(opts, 'default_charset', bool)
        if opts.pop('default_charset', False):
            opts['charset'] = None
        else:
            util.coerce_kw_type(opts, 'charset', str)
        opts['use_unicode'] = opts.get('use_unicode', True)
        util.coerce_kw_type(opts, 'use_unicode', bool)

        # FOUND_ROWS must be set in CLIENT_FLAGS to enable
        # supports_sane_rowcount.
        opts.setdefault('found_rows', True)

        ssl = {}
        for key in ['ssl_ca', 'ssl_key', 'ssl_cert',
                        'ssl_capath', 'ssl_cipher']:
            if key in opts:
                ssl[key[4:]] = opts[key]
                util.coerce_kw_type(ssl, key[4:], str)
                del opts[key]
        if ssl:
            opts['ssl'] = ssl

        return [[], opts]

    def _get_server_version_info(self, connection):
        dbapi_con = connection.connection
        version = []
        r = re.compile('[.\-]')
        for n in r.split(dbapi_con.server_info):
            try:
                version.append(int(n))
            except ValueError:
                version.append(n)
        return tuple(version)

    def _extract_error_code(self, exception):
        return exception.errno

    def _detect_charset(self, connection):
        """Sniff out the character set in use for connection results."""

        return connection.connection.charset

    def _compat_fetchall(self, rp, charset=None):
        """oursql isn't super-broken like MySQLdb, yaaay."""
        return rp.fetchall()

    def _compat_fetchone(self, rp, charset=None):
        """oursql isn't super-broken like MySQLdb, yaaay."""
        return rp.fetchone()

    def _compat_first(self, rp, charset=None):
        return rp.first()


dialect = MySQLDialect_oursql
