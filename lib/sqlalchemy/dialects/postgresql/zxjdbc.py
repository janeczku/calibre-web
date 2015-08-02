# postgresql/zxjdbc.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""
.. dialect:: postgresql+zxjdbc
    :name: zxJDBC for Jython
    :dbapi: zxjdbc
    :connectstring: postgresql+zxjdbc://scott:tiger@localhost/db
    :driverurl: http://jdbc.postgresql.org/


"""
from ...connectors.zxJDBC import ZxJDBCConnector
from .base import PGDialect, PGExecutionContext


class PGExecutionContext_zxjdbc(PGExecutionContext):

    def create_cursor(self):
        cursor = self._dbapi_connection.cursor()
        cursor.datahandler = self.dialect.DataHandler(cursor.datahandler)
        return cursor


class PGDialect_zxjdbc(ZxJDBCConnector, PGDialect):
    jdbc_db_name = 'postgresql'
    jdbc_driver_name = 'org.postgresql.Driver'

    execution_ctx_cls = PGExecutionContext_zxjdbc

    supports_native_decimal = True

    def __init__(self, *args, **kwargs):
        super(PGDialect_zxjdbc, self).__init__(*args, **kwargs)
        from com.ziclix.python.sql.handler import PostgresqlDataHandler
        self.DataHandler = PostgresqlDataHandler

    def _get_server_version_info(self, connection):
        parts = connection.connection.dbversion.split('.')
        return tuple(int(x) for x in parts)

dialect = PGDialect_zxjdbc
