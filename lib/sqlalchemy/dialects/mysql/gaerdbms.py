# mysql/gaerdbms.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
"""
.. dialect:: mysql+gaerdbms
    :name: Google Cloud SQL
    :dbapi: rdbms
    :connectstring: mysql+gaerdbms:///<dbname>?instance=<instancename>
    :url: https://developers.google.com/appengine/docs/python/cloud-sql/developers-guide

    This dialect is based primarily on the :mod:`.mysql.mysqldb` dialect with minimal
    changes.

    .. versionadded:: 0.7.8


Pooling
-------

Google App Engine connections appear to be randomly recycled,
so the dialect does not pool connections.  The :class:`.NullPool`
implementation is installed within the :class:`.Engine` by
default.

"""

import os

from .mysqldb import MySQLDialect_mysqldb
from ...pool import NullPool
import re


def _is_dev_environment():
    return os.environ.get('SERVER_SOFTWARE', '').startswith('Development/')


class MySQLDialect_gaerdbms(MySQLDialect_mysqldb):

    @classmethod
    def dbapi(cls):
        # from django:
        # http://code.google.com/p/googleappengine/source/
        #     browse/trunk/python/google/storage/speckle/
        #     python/django/backend/base.py#118
        # see also [ticket:2649]
        # see also http://stackoverflow.com/q/14224679/34549
        from google.appengine.api import apiproxy_stub_map

        if _is_dev_environment():
            from google.appengine.api import rdbms_mysqldb
            return rdbms_mysqldb
        elif apiproxy_stub_map.apiproxy.GetStub('rdbms'):
            from google.storage.speckle.python.api import rdbms_apiproxy
            return rdbms_apiproxy
        else:
            from google.storage.speckle.python.api import rdbms_googleapi
            return rdbms_googleapi

    @classmethod
    def get_pool_class(cls, url):
        # Cloud SQL connections die at any moment
        return NullPool

    def create_connect_args(self, url):
        opts = url.translate_connect_args()
        if not _is_dev_environment():
            # 'dsn' and 'instance' are because we are skipping
            # the traditional google.api.rdbms wrapper
            opts['dsn'] = ''
            opts['instance'] = url.query['instance']
        return [], opts

    def _extract_error_code(self, exception):
        match = re.compile(r"^(\d+)L?:|^\((\d+)L?,").match(str(exception))
        # The rdbms api will wrap then re-raise some types of errors
        # making this regex return no matches.
        code = match.group(1) or match.group(2) if match else None
        if code:
            return int(code)

dialect = MySQLDialect_gaerdbms
