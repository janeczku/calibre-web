# databases/__init__.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Include imports from the sqlalchemy.dialects package for backwards
compatibility with pre 0.6 versions.

"""
from ..dialects.sqlite import base as sqlite
from ..dialects.postgresql import base as postgresql
postgres = postgresql
from ..dialects.mysql import base as mysql
from ..dialects.drizzle import base as drizzle
from ..dialects.oracle import base as oracle
from ..dialects.firebird import base as firebird
from ..dialects.informix import base as informix
from ..dialects.mssql import base as mssql
from ..dialects.sybase import base as sybase


__all__ = (
    'drizzle',
    'firebird',
    'informix',
    'mssql',
    'mysql',
    'postgresql',
    'sqlite',
    'oracle',
    'sybase',
    )
