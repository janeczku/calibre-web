# firebird/__init__.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

from sqlalchemy.dialects.firebird import base, kinterbasdb, fdb

base.dialect = kinterbasdb.dialect

from sqlalchemy.dialects.firebird.base import \
    SMALLINT, BIGINT, FLOAT, FLOAT, DATE, TIME, \
    TEXT, NUMERIC, FLOAT, TIMESTAMP, VARCHAR, CHAR, BLOB,\
    dialect

__all__ = (
    'SMALLINT', 'BIGINT', 'FLOAT', 'FLOAT', 'DATE', 'TIME',
    'TEXT', 'NUMERIC', 'FLOAT', 'TIMESTAMP', 'VARCHAR', 'CHAR', 'BLOB',
    'dialect'
)
