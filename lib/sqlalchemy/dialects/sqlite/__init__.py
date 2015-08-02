# sqlite/__init__.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

from sqlalchemy.dialects.sqlite import base, pysqlite

# default dialect
base.dialect = pysqlite.dialect


from sqlalchemy.dialects.sqlite.base import \
    BLOB, BOOLEAN, CHAR, DATE, DATETIME, DECIMAL, FLOAT, INTEGER, REAL,\
    NUMERIC, SMALLINT, TEXT, TIME, TIMESTAMP, VARCHAR, dialect

__all__ = (
    'BLOB', 'BOOLEAN', 'CHAR', 'DATE', 'DATETIME', 'DECIMAL', 'FLOAT',
    'INTEGER', 'NUMERIC', 'SMALLINT', 'TEXT', 'TIME', 'TIMESTAMP', 'VARCHAR',
    'REAL', 'dialect'
)
