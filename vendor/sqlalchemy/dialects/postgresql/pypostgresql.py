# postgresql/pypostgresql.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""
.. dialect:: postgresql+pypostgresql
    :name: py-postgresql
    :dbapi: pypostgresql
    :connectstring: postgresql+pypostgresql://user:password@host:port/dbname[?key=value&key=value...]
    :url: http://python.projects.pgfoundry.org/


"""
from ... import util
from ... import types as sqltypes
from .base import PGDialect, PGExecutionContext
from ... import processors


class PGNumeric(sqltypes.Numeric):
    def bind_processor(self, dialect):
        return processors.to_str

    def result_processor(self, dialect, coltype):
        if self.asdecimal:
            return None
        else:
            return processors.to_float


class PGExecutionContext_pypostgresql(PGExecutionContext):
    pass


class PGDialect_pypostgresql(PGDialect):
    driver = 'pypostgresql'

    supports_unicode_statements = True
    supports_unicode_binds = True
    description_encoding = None
    default_paramstyle = 'pyformat'

    # requires trunk version to support sane rowcounts
    # TODO: use dbapi version information to set this flag appropriately
    supports_sane_rowcount = True
    supports_sane_multi_rowcount = False

    execution_ctx_cls = PGExecutionContext_pypostgresql
    colspecs = util.update_copy(
        PGDialect.colspecs,
        {
            sqltypes.Numeric: PGNumeric,

            # prevents PGNumeric from being used
            sqltypes.Float: sqltypes.Float,
        }
    )

    @classmethod
    def dbapi(cls):
        from postgresql.driver import dbapi20
        return dbapi20

    def create_connect_args(self, url):
        opts = url.translate_connect_args(username='user')
        if 'port' in opts:
            opts['port'] = int(opts['port'])
        else:
            opts['port'] = 5432
        opts.update(url.query)
        return ([], opts)

    def is_disconnect(self, e, connection, cursor):
        return "connection is closed" in str(e)

dialect = PGDialect_pypostgresql
