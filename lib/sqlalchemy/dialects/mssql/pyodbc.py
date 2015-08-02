# mssql/pyodbc.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""
.. dialect:: mssql+pyodbc
    :name: PyODBC
    :dbapi: pyodbc
    :connectstring: mssql+pyodbc://<username>:<password>@<dsnname>
    :url: http://pypi.python.org/pypi/pyodbc/

Additional Connection Examples
-------------------------------

Examples of pyodbc connection string URLs:

* ``mssql+pyodbc://mydsn`` - connects using the specified DSN named ``mydsn``.
  The connection string that is created will appear like::

    dsn=mydsn;Trusted_Connection=Yes

* ``mssql+pyodbc://user:pass@mydsn`` - connects using the DSN named
  ``mydsn`` passing in the ``UID`` and ``PWD`` information. The
  connection string that is created will appear like::

    dsn=mydsn;UID=user;PWD=pass

* ``mssql+pyodbc://user:pass@mydsn/?LANGUAGE=us_english`` - connects
  using the DSN named ``mydsn`` passing in the ``UID`` and ``PWD``
  information, plus the additional connection configuration option
  ``LANGUAGE``. The connection string that is created will appear
  like::

    dsn=mydsn;UID=user;PWD=pass;LANGUAGE=us_english

* ``mssql+pyodbc://user:pass@host/db`` - connects using a connection
  that would appear like::

    DRIVER={SQL Server};Server=host;Database=db;UID=user;PWD=pass

* ``mssql+pyodbc://user:pass@host:123/db`` - connects using a connection
  string which includes the port
  information using the comma syntax. This will create the following
  connection string::

    DRIVER={SQL Server};Server=host,123;Database=db;UID=user;PWD=pass

* ``mssql+pyodbc://user:pass@host/db?port=123`` - connects using a connection
  string that includes the port
  information as a separate ``port`` keyword. This will create the
  following connection string::

    DRIVER={SQL Server};Server=host;Database=db;UID=user;PWD=pass;port=123

* ``mssql+pyodbc://user:pass@host/db?driver=MyDriver`` - connects using a connection
  string that includes a custom
  ODBC driver name.  This will create the following connection string::

    DRIVER={MyDriver};Server=host;Database=db;UID=user;PWD=pass

If you require a connection string that is outside the options
presented above, use the ``odbc_connect`` keyword to pass in a
urlencoded connection string. What gets passed in will be urldecoded
and passed directly.

For example::

    mssql+pyodbc:///?odbc_connect=dsn%3Dmydsn%3BDatabase%3Ddb

would create the following connection string::

    dsn=mydsn;Database=db

Encoding your connection string can be easily accomplished through
the python shell. For example::

    >>> import urllib
    >>> urllib.quote_plus('dsn=mydsn;Database=db')
    'dsn%3Dmydsn%3BDatabase%3Ddb'

Unicode Binds
-------------

The current state of PyODBC on a unix backend with FreeTDS and/or
EasySoft is poor regarding unicode; different OS platforms and versions of UnixODBC
versus IODBC versus FreeTDS/EasySoft versus PyODBC itself dramatically
alter how strings are received.  The PyODBC dialect attempts to use all the information
it knows to determine whether or not a Python unicode literal can be
passed directly to the PyODBC driver or not; while SQLAlchemy can encode
these to bytestrings first, some users have reported that PyODBC mis-handles
bytestrings for certain encodings and requires a Python unicode object,
while the author has observed widespread cases where a Python unicode
is completely misinterpreted by PyODBC, particularly when dealing with
the information schema tables used in table reflection, and the value
must first be encoded to a bytestring.

It is for this reason that whether or not unicode literals for bound
parameters be sent to PyODBC can be controlled using the
``supports_unicode_binds`` parameter to ``create_engine()``.  When
left at its default of ``None``, the PyODBC dialect will use its
best guess as to whether or not the driver deals with unicode literals
well.  When ``False``, unicode literals will be encoded first, and when
``True`` unicode literals will be passed straight through.  This is an interim
flag that hopefully should not be needed when the unicode situation stabilizes
for unix + PyODBC.

.. versionadded:: 0.7.7
    ``supports_unicode_binds`` parameter to ``create_engine()``\ .

"""

from .base import MSExecutionContext, MSDialect
from ...connectors.pyodbc import PyODBCConnector
from ... import types as sqltypes, util
import decimal


class _MSNumeric_pyodbc(sqltypes.Numeric):
    """Turns Decimals with adjusted() < 0 or > 7 into strings.

    The routines here are needed for older pyodbc versions
    as well as current mxODBC versions.

    """

    def bind_processor(self, dialect):

        super_process = super(_MSNumeric_pyodbc, self).\
                        bind_processor(dialect)

        if not dialect._need_decimal_fix:
            return super_process

        def process(value):
            if self.asdecimal and \
                    isinstance(value, decimal.Decimal):

                adjusted = value.adjusted()
                if adjusted < 0:
                    return self._small_dec_to_string(value)
                elif adjusted > 7:
                    return self._large_dec_to_string(value)

            if super_process:
                return super_process(value)
            else:
                return value
        return process

    # these routines needed for older versions of pyodbc.
    # as of 2.1.8 this logic is integrated.

    def _small_dec_to_string(self, value):
        return "%s0.%s%s" % (
                    (value < 0 and '-' or ''),
                    '0' * (abs(value.adjusted()) - 1),
                    "".join([str(nint) for nint in value.as_tuple()[1]]))

    def _large_dec_to_string(self, value):
        _int = value.as_tuple()[1]
        if 'E' in str(value):
            result = "%s%s%s" % (
                    (value < 0 and '-' or ''),
                    "".join([str(s) for s in _int]),
                    "0" * (value.adjusted() - (len(_int) - 1)))
        else:
            if (len(_int) - 1) > value.adjusted():
                result = "%s%s.%s" % (
                (value < 0 and '-' or ''),
                "".join(
                    [str(s) for s in _int][0:value.adjusted() + 1]),
                "".join(
                    [str(s) for s in _int][value.adjusted() + 1:]))
            else:
                result = "%s%s" % (
                (value < 0 and '-' or ''),
                "".join(
                    [str(s) for s in _int][0:value.adjusted() + 1]))
        return result


class MSExecutionContext_pyodbc(MSExecutionContext):
    _embedded_scope_identity = False

    def pre_exec(self):
        """where appropriate, issue "select scope_identity()" in the same
        statement.

        Background on why "scope_identity()" is preferable to "@@identity":
        http://msdn.microsoft.com/en-us/library/ms190315.aspx

        Background on why we attempt to embed "scope_identity()" into the same
        statement as the INSERT:
        http://code.google.com/p/pyodbc/wiki/FAQs#How_do_I_retrieve_autogenerated/identity_values?

        """

        super(MSExecutionContext_pyodbc, self).pre_exec()

        # don't embed the scope_identity select into an
        # "INSERT .. DEFAULT VALUES"
        if self._select_lastrowid and \
                self.dialect.use_scope_identity and \
                len(self.parameters[0]):
            self._embedded_scope_identity = True

            self.statement += "; select scope_identity()"

    def post_exec(self):
        if self._embedded_scope_identity:
            # Fetch the last inserted id from the manipulated statement
            # We may have to skip over a number of result sets with
            # no data (due to triggers, etc.)
            while True:
                try:
                    # fetchall() ensures the cursor is consumed
                    # without closing it (FreeTDS particularly)
                    row = self.cursor.fetchall()[0]
                    break
                except self.dialect.dbapi.Error, e:
                    # no way around this - nextset() consumes the previous set
                    # so we need to just keep flipping
                    self.cursor.nextset()

            self._lastrowid = int(row[0])
        else:
            super(MSExecutionContext_pyodbc, self).post_exec()


class MSDialect_pyodbc(PyODBCConnector, MSDialect):

    execution_ctx_cls = MSExecutionContext_pyodbc

    pyodbc_driver_name = 'SQL Server'

    colspecs = util.update_copy(
        MSDialect.colspecs,
        {
            sqltypes.Numeric: _MSNumeric_pyodbc
        }
    )

    def __init__(self, description_encoding=None, **params):
        super(MSDialect_pyodbc, self).__init__(**params)
        self.description_encoding = description_encoding
        self.use_scope_identity = self.use_scope_identity and \
                        self.dbapi and \
                        hasattr(self.dbapi.Cursor, 'nextset')
        self._need_decimal_fix = self.dbapi and \
                            self._dbapi_version() < (2, 1, 8)

dialect = MSDialect_pyodbc
