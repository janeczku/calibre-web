# connectors/pyodbc.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

from . import Connector
from ..util import asbool

import sys
import re
import urllib


class PyODBCConnector(Connector):
    driver = 'pyodbc'

    supports_sane_multi_rowcount = False
    # PyODBC unicode is broken on UCS-4 builds
    supports_unicode = sys.maxunicode == 65535
    supports_unicode_statements = supports_unicode
    supports_native_decimal = True
    default_paramstyle = 'named'

    # for non-DSN connections, this should
    # hold the desired driver name
    pyodbc_driver_name = None

    # will be set to True after initialize()
    # if the freetds.so is detected
    freetds = False

    # will be set to the string version of
    # the FreeTDS driver if freetds is detected
    freetds_driver_version = None

    # will be set to True after initialize()
    # if the libessqlsrv.so is detected
    easysoft = False

    def __init__(self, supports_unicode_binds=None, **kw):
        super(PyODBCConnector, self).__init__(**kw)
        self._user_supports_unicode_binds = supports_unicode_binds

    @classmethod
    def dbapi(cls):
        return __import__('pyodbc')

    def create_connect_args(self, url):
        opts = url.translate_connect_args(username='user')
        opts.update(url.query)

        keys = opts
        query = url.query

        connect_args = {}
        for param in ('ansi', 'unicode_results', 'autocommit'):
            if param in keys:
                connect_args[param] = asbool(keys.pop(param))

        if 'odbc_connect' in keys:
            connectors = [urllib.unquote_plus(keys.pop('odbc_connect'))]
        else:
            dsn_connection = 'dsn' in keys or \
                            ('host' in keys and 'database' not in keys)
            if dsn_connection:
                connectors = ['dsn=%s' % (keys.pop('host', '') or \
                            keys.pop('dsn', ''))]
            else:
                port = ''
                if 'port' in keys and not 'port' in query:
                    port = ',%d' % int(keys.pop('port'))

                connectors = ["DRIVER={%s}" %
                                keys.pop('driver', self.pyodbc_driver_name),
                              'Server=%s%s' % (keys.pop('host', ''), port),
                              'Database=%s' % keys.pop('database', '')]

            user = keys.pop("user", None)
            if user:
                connectors.append("UID=%s" % user)
                connectors.append("PWD=%s" % keys.pop('password', ''))
            else:
                connectors.append("Trusted_Connection=Yes")

            # if set to 'Yes', the ODBC layer will try to automagically
            # convert textual data from your database encoding to your
            # client encoding.  This should obviously be set to 'No' if
            # you query a cp1253 encoded database from a latin1 client...
            if 'odbc_autotranslate' in keys:
                connectors.append("AutoTranslate=%s" %
                                    keys.pop("odbc_autotranslate"))

            connectors.extend(['%s=%s' % (k, v) for k, v in keys.iteritems()])
        return [[";".join(connectors)], connect_args]

    def is_disconnect(self, e, connection, cursor):
        if isinstance(e, self.dbapi.ProgrammingError):
            return "The cursor's connection has been closed." in str(e) or \
                            'Attempt to use a closed connection.' in str(e)
        elif isinstance(e, self.dbapi.Error):
            return '[08S01]' in str(e)
        else:
            return False

    def initialize(self, connection):
        # determine FreeTDS first.   can't issue SQL easily
        # without getting unicode_statements/binds set up.

        pyodbc = self.dbapi

        dbapi_con = connection.connection

        _sql_driver_name = dbapi_con.getinfo(pyodbc.SQL_DRIVER_NAME)
        self.freetds = bool(re.match(r".*libtdsodbc.*\.so", _sql_driver_name
                            ))
        self.easysoft = bool(re.match(r".*libessqlsrv.*\.so", _sql_driver_name
                            ))

        if self.freetds:
            self.freetds_driver_version = dbapi_con.getinfo(
                pyodbc.SQL_DRIVER_VER)

        # the "Py2K only" part here is theoretical.
        # have not tried pyodbc + python3.1 yet.
        # Py2K
        self.supports_unicode_statements = (
            not self.freetds and not self.easysoft)
        if self._user_supports_unicode_binds is not None:
            self.supports_unicode_binds = self._user_supports_unicode_binds
        else:
            self.supports_unicode_binds = (
                not self.freetds or self.freetds_driver_version >= '0.91'
            ) and not self.easysoft
        # end Py2K

        # run other initialization which asks for user name, etc.
        super(PyODBCConnector, self).initialize(connection)

    def _dbapi_version(self):
        if not self.dbapi:
            return ()
        return self._parse_dbapi_version(self.dbapi.version)

    def _parse_dbapi_version(self, vers):
        m = re.match(
                r'(?:py.*-)?([\d\.]+)(?:-(\w+))?',
                vers
            )
        if not m:
            return ()
        vers = tuple([int(x) for x in m.group(1).split(".")])
        if m.group(2):
            vers += (m.group(2),)
        return vers

    def _get_server_version_info(self, connection):
        dbapi_con = connection.connection
        version = []
        r = re.compile('[.\-]')
        for n in r.split(dbapi_con.getinfo(self.dbapi.SQL_DBMS_VER)):
            try:
                version.append(int(n))
            except ValueError:
                version.append(n)
        return tuple(version)
