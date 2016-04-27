# informix/informixdb.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""

.. dialect:: informix+informixdb
    :name: informixdb
    :dbapi: informixdb
    :connectstring: informix+informixdb://user:password@host/dbname
    :url: http://informixdb.sourceforge.net/

"""

import re

from sqlalchemy.dialects.informix.base import InformixDialect
from sqlalchemy.engine import default

VERSION_RE = re.compile(r'(\d+)\.(\d+)(.+\d+)')


class InformixExecutionContext_informixdb(default.DefaultExecutionContext):

    def post_exec(self):
        if self.isinsert:
            self._lastrowid = self.cursor.sqlerrd[1]

    def get_lastrowid(self):
        return self._lastrowid


class InformixDialect_informixdb(InformixDialect):
    driver = 'informixdb'
    execution_ctx_cls = InformixExecutionContext_informixdb

    @classmethod
    def dbapi(cls):
        return __import__('informixdb')

    def create_connect_args(self, url):
        if url.host:
            dsn = '%s@%s' % (url.database, url.host)
        else:
            dsn = url.database

        if url.username:
            opt = {'user': url.username, 'password': url.password}
        else:
            opt = {}

        return ([dsn], opt)

    def _get_server_version_info(self, connection):
        # http://informixdb.sourceforge.net/manual.html#inspecting-version-numbers
        v = VERSION_RE.split(connection.connection.dbms_version)
        return (int(v[1]), int(v[2]), v[3])

    def is_disconnect(self, e, connection, cursor):
        if isinstance(e, self.dbapi.OperationalError):
            return 'closed the connection' in str(e) \
                    or 'connection not open' in str(e)
        else:
            return False


dialect = InformixDialect_informixdb
