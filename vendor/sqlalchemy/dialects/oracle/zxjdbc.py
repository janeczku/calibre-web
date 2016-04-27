# oracle/zxjdbc.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""
.. dialect:: oracle+zxjdbc
    :name: zxJDBC for Jython
    :dbapi: zxjdbc
    :connectstring: oracle+zxjdbc://user:pass@host/dbname
    :driverurl: http://www.oracle.com/technology/software/tech/java/sqlj_jdbc/index.html.

"""
import decimal
import re

from sqlalchemy import sql, types as sqltypes, util
from sqlalchemy.connectors.zxJDBC import ZxJDBCConnector
from sqlalchemy.dialects.oracle.base import OracleCompiler, OracleDialect, OracleExecutionContext
from sqlalchemy.engine import result as _result
from sqlalchemy.sql import expression
import collections

SQLException = zxJDBC = None


class _ZxJDBCDate(sqltypes.Date):

    def result_processor(self, dialect, coltype):
        def process(value):
            if value is None:
                return None
            else:
                return value.date()
        return process


class _ZxJDBCNumeric(sqltypes.Numeric):

    def result_processor(self, dialect, coltype):
        #XXX: does the dialect return Decimal or not???
        # if it does (in all cases), we could use a None processor as well as
        # the to_float generic processor
        if self.asdecimal:
            def process(value):
                if isinstance(value, decimal.Decimal):
                    return value
                else:
                    return decimal.Decimal(str(value))
        else:
            def process(value):
                if isinstance(value, decimal.Decimal):
                    return float(value)
                else:
                    return value
        return process


class OracleCompiler_zxjdbc(OracleCompiler):

    def returning_clause(self, stmt, returning_cols):
        self.returning_cols = list(expression._select_iterables(returning_cols))

        # within_columns_clause=False so that labels (foo AS bar) don't render
        columns = [self.process(c, within_columns_clause=False, result_map=self.result_map)
                   for c in self.returning_cols]

        if not hasattr(self, 'returning_parameters'):
            self.returning_parameters = []

        binds = []
        for i, col in enumerate(self.returning_cols):
            dbtype = col.type.dialect_impl(self.dialect).get_dbapi_type(self.dialect.dbapi)
            self.returning_parameters.append((i + 1, dbtype))

            bindparam = sql.bindparam("ret_%d" % i, value=ReturningParam(dbtype))
            self.binds[bindparam.key] = bindparam
            binds.append(self.bindparam_string(self._truncate_bindparam(bindparam)))

        return 'RETURNING ' + ', '.join(columns) + " INTO " + ", ".join(binds)


class OracleExecutionContext_zxjdbc(OracleExecutionContext):

    def pre_exec(self):
        if hasattr(self.compiled, 'returning_parameters'):
            # prepare a zxJDBC statement so we can grab its underlying
            # OraclePreparedStatement's getReturnResultSet later
            self.statement = self.cursor.prepare(self.statement)

    def get_result_proxy(self):
        if hasattr(self.compiled, 'returning_parameters'):
            rrs = None
            try:
                try:
                    rrs = self.statement.__statement__.getReturnResultSet()
                    rrs.next()
                except SQLException, sqle:
                    msg = '%s [SQLCode: %d]' % (sqle.getMessage(), sqle.getErrorCode())
                    if sqle.getSQLState() is not None:
                        msg += ' [SQLState: %s]' % sqle.getSQLState()
                    raise zxJDBC.Error(msg)
                else:
                    row = tuple(self.cursor.datahandler.getPyObject(rrs, index, dbtype)
                                for index, dbtype in self.compiled.returning_parameters)
                    return ReturningResultProxy(self, row)
            finally:
                if rrs is not None:
                    try:
                        rrs.close()
                    except SQLException:
                        pass
                self.statement.close()

        return _result.ResultProxy(self)

    def create_cursor(self):
        cursor = self._dbapi_connection.cursor()
        cursor.datahandler = self.dialect.DataHandler(cursor.datahandler)
        return cursor


class ReturningResultProxy(_result.FullyBufferedResultProxy):

    """ResultProxy backed by the RETURNING ResultSet results."""

    def __init__(self, context, returning_row):
        self._returning_row = returning_row
        super(ReturningResultProxy, self).__init__(context)

    def _cursor_description(self):
        ret = []
        for c in self.context.compiled.returning_cols:
            if hasattr(c, 'name'):
                ret.append((c.name, c.type))
            else:
                ret.append((c.anon_label, c.type))
        return ret

    def _buffer_rows(self):
        return collections.deque([self._returning_row])


class ReturningParam(object):

    """A bindparam value representing a RETURNING parameter.

    Specially handled by OracleReturningDataHandler.
    """

    def __init__(self, type):
        self.type = type

    def __eq__(self, other):
        if isinstance(other, ReturningParam):
            return self.type == other.type
        return NotImplemented

    def __ne__(self, other):
        if isinstance(other, ReturningParam):
            return self.type != other.type
        return NotImplemented

    def __repr__(self):
        kls = self.__class__
        return '<%s.%s object at 0x%x type=%s>' % (kls.__module__, kls.__name__, id(self),
                                                   self.type)


class OracleDialect_zxjdbc(ZxJDBCConnector, OracleDialect):
    jdbc_db_name = 'oracle'
    jdbc_driver_name = 'oracle.jdbc.OracleDriver'

    statement_compiler = OracleCompiler_zxjdbc
    execution_ctx_cls = OracleExecutionContext_zxjdbc

    colspecs = util.update_copy(
        OracleDialect.colspecs,
        {
            sqltypes.Date: _ZxJDBCDate,
            sqltypes.Numeric: _ZxJDBCNumeric
        }
    )

    def __init__(self, *args, **kwargs):
        super(OracleDialect_zxjdbc, self).__init__(*args, **kwargs)
        global SQLException, zxJDBC
        from java.sql import SQLException
        from com.ziclix.python.sql import zxJDBC
        from com.ziclix.python.sql.handler import OracleDataHandler

        class OracleReturningDataHandler(OracleDataHandler):
            """zxJDBC DataHandler that specially handles ReturningParam."""

            def setJDBCObject(self, statement, index, object, dbtype=None):
                if type(object) is ReturningParam:
                    statement.registerReturnParameter(index, object.type)
                elif dbtype is None:
                    OracleDataHandler.setJDBCObject(
                        self, statement, index, object)
                else:
                    OracleDataHandler.setJDBCObject(
                        self, statement, index, object, dbtype)
        self.DataHandler = OracleReturningDataHandler

    def initialize(self, connection):
        super(OracleDialect_zxjdbc, self).initialize(connection)
        self.implicit_returning = connection.connection.driverversion >= '10.2'

    def _create_jdbc_url(self, url):
        return 'jdbc:oracle:thin:@%s:%s:%s' % (url.host, url.port or 1521, url.database)

    def _get_server_version_info(self, connection):
        version = re.search(r'Release ([\d\.]+)', connection.connection.dbversion).group(1)
        return tuple(int(x) for x in version.split('.'))

dialect = OracleDialect_zxjdbc
