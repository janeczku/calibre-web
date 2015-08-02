# mysql/zxjdbc.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""

.. dialect:: mysql+zxjdbc
    :name: zxjdbc for Jython
    :dbapi: zxjdbc
    :connectstring: mysql+zxjdbc://<user>:<password>@<hostname>[:<port>]/<database>
    :driverurl: http://dev.mysql.com/downloads/connector/j/

Character Sets
--------------

SQLAlchemy zxjdbc dialects pass unicode straight through to the
zxjdbc/JDBC layer. To allow multiple character sets to be sent from the
MySQL Connector/J JDBC driver, by default SQLAlchemy sets its
``characterEncoding`` connection property to ``UTF-8``. It may be
overriden via a ``create_engine`` URL parameter.

"""
import re

from ... import types as sqltypes, util
from ...connectors.zxJDBC import ZxJDBCConnector
from .base import BIT, MySQLDialect, MySQLExecutionContext


class _ZxJDBCBit(BIT):
    def result_processor(self, dialect, coltype):
        """Converts boolean or byte arrays from MySQL Connector/J to longs."""
        def process(value):
            if value is None:
                return value
            if isinstance(value, bool):
                return int(value)
            v = 0L
            for i in value:
                v = v << 8 | (i & 0xff)
            value = v
            return value
        return process


class MySQLExecutionContext_zxjdbc(MySQLExecutionContext):
    def get_lastrowid(self):
        cursor = self.create_cursor()
        cursor.execute("SELECT LAST_INSERT_ID()")
        lastrowid = cursor.fetchone()[0]
        cursor.close()
        return lastrowid


class MySQLDialect_zxjdbc(ZxJDBCConnector, MySQLDialect):
    jdbc_db_name = 'mysql'
    jdbc_driver_name = 'com.mysql.jdbc.Driver'

    execution_ctx_cls = MySQLExecutionContext_zxjdbc

    colspecs = util.update_copy(
        MySQLDialect.colspecs,
        {
            sqltypes.Time: sqltypes.Time,
            BIT: _ZxJDBCBit
        }
    )

    def _detect_charset(self, connection):
        """Sniff out the character set in use for connection results."""
        # Prefer 'character_set_results' for the current connection over the
        # value in the driver.  SET NAMES or individual variable SETs will
        # change the charset without updating the driver's view of the world.
        #
        # If it's decided that issuing that sort of SQL leaves you SOL, then
        # this can prefer the driver value.
        rs = connection.execute("SHOW VARIABLES LIKE 'character_set%%'")
        opts = dict((row[0], row[1]) for row in self._compat_fetchall(rs))
        for key in ('character_set_connection', 'character_set'):
            if opts.get(key, None):
                return opts[key]

        util.warn("Could not detect the connection character set.  Assuming latin1.")
        return 'latin1'

    def _driver_kwargs(self):
        """return kw arg dict to be sent to connect()."""
        return dict(characterEncoding='UTF-8', yearIsDateType='false')

    def _extract_error_code(self, exception):
        # e.g.: DBAPIError: (Error) Table 'test.u2' doesn't exist
        # [SQLCode: 1146], [SQLState: 42S02] 'DESCRIBE `u2`' ()
        m = re.compile(r"\[SQLCode\: (\d+)\]").search(str(exception.args))
        c = m.group(1)
        if c:
            return int(c)

    def _get_server_version_info(self, connection):
        dbapi_con = connection.connection
        version = []
        r = re.compile('[.\-]')
        for n in r.split(dbapi_con.dbversion):
            try:
                version.append(int(n))
            except ValueError:
                version.append(n)
        return tuple(version)

dialect = MySQLDialect_zxjdbc
