# dialects/postgres.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

# backwards compat with the old name
from sqlalchemy.util import warn_deprecated

warn_deprecated(
    "The SQLAlchemy PostgreSQL dialect has been renamed from 'postgres' to 'postgresql'. "
    "The new URL format is postgresql[+driver]://<user>:<pass>@<host>/<dbname>"
    )

from sqlalchemy.dialects.postgresql import *
from sqlalchemy.dialects.postgresql import base
