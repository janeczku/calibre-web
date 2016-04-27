"""
.. dialect:: drizzle+mysqldb
    :name: MySQL-Python
    :dbapi: mysqldb
    :connectstring: drizzle+mysqldb://<user>:<password>@<host>[:<port>]/<dbname>
    :url: http://sourceforge.net/projects/mysql-python


"""

from sqlalchemy.dialects.drizzle.base import (
    DrizzleDialect,
    DrizzleExecutionContext,
    DrizzleCompiler,
    DrizzleIdentifierPreparer)
from sqlalchemy.connectors.mysqldb import (
    MySQLDBExecutionContext,
    MySQLDBCompiler,
    MySQLDBIdentifierPreparer,
    MySQLDBConnector)


class DrizzleExecutionContext_mysqldb(MySQLDBExecutionContext,
                                      DrizzleExecutionContext):
    pass


class DrizzleCompiler_mysqldb(MySQLDBCompiler, DrizzleCompiler):
    pass


class DrizzleIdentifierPreparer_mysqldb(MySQLDBIdentifierPreparer,
                                        DrizzleIdentifierPreparer):
    pass


class DrizzleDialect_mysqldb(MySQLDBConnector, DrizzleDialect):
    execution_ctx_cls = DrizzleExecutionContext_mysqldb
    statement_compiler = DrizzleCompiler_mysqldb
    preparer = DrizzleIdentifierPreparer_mysqldb

    def _detect_charset(self, connection):
        """Sniff out the character set in use for connection results."""

        return 'utf8'


dialect = DrizzleDialect_mysqldb
