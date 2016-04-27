# postgresql/pg8000.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""
.. dialect:: postgresql+pg8000
    :name: pg8000
    :dbapi: pg8000
    :connectstring: postgresql+pg8000://user:password@host:port/dbname[?key=value&key=value...]
    :url: http://pybrary.net/pg8000/

Unicode
-------

pg8000 requires that the postgresql client encoding be
configured in the postgresql.conf file in order to use encodings
other than ascii. Set this value to the same value as the
"encoding" parameter on create_engine(), usually "utf-8".

Interval
--------

Passing data from/to the Interval type is not supported as of
yet.

"""
from ... import util, exc
import decimal
from ... import processors
from ... import types as sqltypes
from .base import PGDialect, \
                PGCompiler, PGIdentifierPreparer, PGExecutionContext,\
                _DECIMAL_TYPES, _FLOAT_TYPES, _INT_TYPES


class _PGNumeric(sqltypes.Numeric):
    def result_processor(self, dialect, coltype):
        if self.asdecimal:
            if coltype in _FLOAT_TYPES:
                return processors.to_decimal_processor_factory(decimal.Decimal)
            elif coltype in _DECIMAL_TYPES or coltype in _INT_TYPES:
                # pg8000 returns Decimal natively for 1700
                return None
            else:
                raise exc.InvalidRequestError(
                            "Unknown PG numeric type: %d" % coltype)
        else:
            if coltype in _FLOAT_TYPES:
                # pg8000 returns float natively for 701
                return None
            elif coltype in _DECIMAL_TYPES or coltype in _INT_TYPES:
                return processors.to_float
            else:
                raise exc.InvalidRequestError(
                            "Unknown PG numeric type: %d" % coltype)


class _PGNumericNoBind(_PGNumeric):
    def bind_processor(self, dialect):
        return None


class PGExecutionContext_pg8000(PGExecutionContext):
    pass


class PGCompiler_pg8000(PGCompiler):
    def visit_mod_binary(self, binary, operator, **kw):
        return self.process(binary.left, **kw) + " %% " + \
                        self.process(binary.right, **kw)

    def post_process_text(self, text):
        if '%%' in text:
            util.warn("The SQLAlchemy postgresql dialect "
                      "now automatically escapes '%' in text() "
                      "expressions to '%%'.")
        return text.replace('%', '%%')


class PGIdentifierPreparer_pg8000(PGIdentifierPreparer):
    def _escape_identifier(self, value):
        value = value.replace(self.escape_quote, self.escape_to_quote)
        return value.replace('%', '%%')


class PGDialect_pg8000(PGDialect):
    driver = 'pg8000'

    supports_unicode_statements = True

    supports_unicode_binds = True

    default_paramstyle = 'format'
    supports_sane_multi_rowcount = False
    execution_ctx_cls = PGExecutionContext_pg8000
    statement_compiler = PGCompiler_pg8000
    preparer = PGIdentifierPreparer_pg8000
    description_encoding = 'use_encoding'

    colspecs = util.update_copy(
        PGDialect.colspecs,
        {
            sqltypes.Numeric: _PGNumericNoBind,
            sqltypes.Float: _PGNumeric
        }
    )

    @classmethod
    def dbapi(cls):
        return __import__('pg8000').dbapi

    def create_connect_args(self, url):
        opts = url.translate_connect_args(username='user')
        if 'port' in opts:
            opts['port'] = int(opts['port'])
        opts.update(url.query)
        return ([], opts)

    def is_disconnect(self, e, connection, cursor):
        return "connection is closed" in str(e)

dialect = PGDialect_pg8000
