# mssql/pymssql.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""
.. dialect:: mssql+pymssql
    :name: pymssql
    :dbapi: pymssql
    :connectstring: mssql+pymssql://<username>:<password>@<freetds_name>?charset=utf8
    :url: http://pymssql.sourceforge.net/

Limitations
-----------

pymssql inherits a lot of limitations from FreeTDS, including:

* no support for multibyte schema identifiers
* poor support for large decimals
* poor support for binary fields
* poor support for VARCHAR/CHAR fields over 255 characters

Please consult the pymssql documentation for further information.

"""
from .base import MSDialect
from ... import types as sqltypes, util, processors
import re


class _MSNumeric_pymssql(sqltypes.Numeric):
    def result_processor(self, dialect, type_):
        if not self.asdecimal:
            return processors.to_float
        else:
            return sqltypes.Numeric.result_processor(self, dialect, type_)


class MSDialect_pymssql(MSDialect):
    supports_sane_rowcount = False
    driver = 'pymssql'

    colspecs = util.update_copy(
        MSDialect.colspecs,
        {
            sqltypes.Numeric: _MSNumeric_pymssql,
            sqltypes.Float: sqltypes.Float,
        }
    )

    @classmethod
    def dbapi(cls):
        module = __import__('pymssql')
        # pymmsql doesn't have a Binary method.  we use string
        # TODO: monkeypatching here is less than ideal
        module.Binary = lambda x: x if hasattr(x, 'decode') else str(x)

        client_ver = tuple(int(x) for x in module.__version__.split("."))
        if client_ver < (1, ):
            util.warn("The pymssql dialect expects at least "
                            "the 1.0 series of the pymssql DBAPI.")
        return module

    def __init__(self, **params):
        super(MSDialect_pymssql, self).__init__(**params)
        self.use_scope_identity = True

    def _get_server_version_info(self, connection):
        vers = connection.scalar("select @@version")
        m = re.match(
            r"Microsoft SQL Server.*? - (\d+).(\d+).(\d+).(\d+)", vers)
        if m:
            return tuple(int(x) for x in m.group(1, 2, 3, 4))
        else:
            return None

    def create_connect_args(self, url):
        opts = url.translate_connect_args(username='user')
        opts.update(url.query)
        port = opts.pop('port', None)
        if port and 'host' in opts:
            opts['host'] = "%s:%s" % (opts['host'], port)
        return [[], opts]

    def is_disconnect(self, e, connection, cursor):
        for msg in (
            "Adaptive Server connection timed out",
            "message 20003",  # connection timeout
            "Error 10054",
            "Not connected to any MS SQL server",
            "Connection is closed"
        ):
            if msg in str(e):
                return True
        else:
            return False

dialect = MSDialect_pymssql
