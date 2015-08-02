# dialects/__init__.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

__all__ = (
    'drizzle',
    'firebird',
#    'informix',
    'mssql',
    'mysql',
    'oracle',
    'postgresql',
    'sqlite',
    'sybase',
    )

from .. import util

def _auto_fn(name):
    """default dialect importer.

    plugs into the :class:`.PluginLoader`
    as a first-hit system.

    """
    if "." in name:
        dialect, driver = name.split(".")
    else:
        dialect = name
        driver = "base"
    try:
        module = __import__('sqlalchemy.dialects.%s' % (dialect, )).dialects
    except ImportError:
        return None

    module = getattr(module, dialect)
    if hasattr(module, driver):
        module = getattr(module, driver)
        return lambda: module.dialect
    else:
        return None

registry = util.PluginLoader("sqlalchemy.dialects", auto_fn=_auto_fn)
