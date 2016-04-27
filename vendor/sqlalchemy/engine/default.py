# engine/default.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Default implementations of per-dialect sqlalchemy.engine classes.

These are semi-private implementation classes which are only of importance
to database dialect authors; dialects will usually use the classes here
as the base class for their own corresponding classes.

"""

import re
import random
from . import reflection, interfaces, result
from ..sql import compiler, expression
from .. import exc, types as sqltypes, util, pool, processors
import codecs
import weakref

AUTOCOMMIT_REGEXP = re.compile(
            r'\s*(?:UPDATE|INSERT|CREATE|DELETE|DROP|ALTER)',
            re.I | re.UNICODE)


class DefaultDialect(interfaces.Dialect):
    """Default implementation of Dialect"""

    statement_compiler = compiler.SQLCompiler
    ddl_compiler = compiler.DDLCompiler
    type_compiler = compiler.GenericTypeCompiler
    preparer = compiler.IdentifierPreparer
    supports_alter = True

    # the first value we'd get for an autoincrement
    # column.
    default_sequence_base = 1

    # most DBAPIs happy with this for execute().
    # not cx_oracle.
    execute_sequence_format = tuple

    supports_views = True
    supports_sequences = False
    sequences_optional = False
    preexecute_autoincrement_sequences = False
    postfetch_lastrowid = True
    implicit_returning = False

    supports_native_enum = False
    supports_native_boolean = False

    # if the NUMERIC type
    # returns decimal.Decimal.
    # *not* the FLOAT type however.
    supports_native_decimal = False

    # Py3K
    #supports_unicode_statements = True
    #supports_unicode_binds = True
    #returns_unicode_strings = True
    #description_encoding = None
    # Py2K
    supports_unicode_statements = False
    supports_unicode_binds = False
    returns_unicode_strings = False
    description_encoding = 'use_encoding'
    # end Py2K

    name = 'default'

    # length at which to truncate
    # any identifier.
    max_identifier_length = 9999

    # length at which to truncate
    # the name of an index.
    # Usually None to indicate
    # 'use max_identifier_length'.
    # thanks to MySQL, sigh
    max_index_name_length = None

    supports_sane_rowcount = True
    supports_sane_multi_rowcount = True
    dbapi_type_map = {}
    colspecs = {}
    default_paramstyle = 'named'
    supports_default_values = False
    supports_empty_insert = True
    supports_multivalues_insert = False

    server_version_info = None

    # indicates symbol names are
    # UPPERCASEd if they are case insensitive
    # within the database.
    # if this is True, the methods normalize_name()
    # and denormalize_name() must be provided.
    requires_name_normalize = False

    reflection_options = ()

    def __init__(self, convert_unicode=False,
                 encoding='utf-8', paramstyle=None, dbapi=None,
                 implicit_returning=None,
                 case_sensitive=True,
                 label_length=None, **kwargs):

        if not getattr(self, 'ported_sqla_06', True):
            util.warn(
                "The %s dialect is not yet ported to the 0.6 format" %
                self.name)

        self.convert_unicode = convert_unicode
        self.encoding = encoding
        self.positional = False
        self._ischema = None
        self.dbapi = dbapi
        if paramstyle is not None:
            self.paramstyle = paramstyle
        elif self.dbapi is not None:
            self.paramstyle = self.dbapi.paramstyle
        else:
            self.paramstyle = self.default_paramstyle
        if implicit_returning is not None:
            self.implicit_returning = implicit_returning
        self.positional = self.paramstyle in ('qmark', 'format', 'numeric')
        self.identifier_preparer = self.preparer(self)
        self.type_compiler = self.type_compiler(self)

        self.case_sensitive = case_sensitive

        if label_length and label_length > self.max_identifier_length:
            raise exc.ArgumentError(
                    "Label length of %d is greater than this dialect's"
                    " maximum identifier length of %d" %
                    (label_length, self.max_identifier_length))
        self.label_length = label_length

        if self.description_encoding == 'use_encoding':
            self._description_decoder = \
                            processors.to_unicode_processor_factory(
                                            encoding
                                    )
        elif self.description_encoding is not None:
            self._description_decoder = \
                            processors.to_unicode_processor_factory(
                                            self.description_encoding
                                    )
        self._encoder = codecs.getencoder(self.encoding)
        self._decoder = processors.to_unicode_processor_factory(self.encoding)

    @util.memoized_property
    def _type_memos(self):
        return weakref.WeakKeyDictionary()

    @property
    def dialect_description(self):
        return self.name + "+" + self.driver

    @classmethod
    def get_pool_class(cls, url):
        return getattr(cls, 'poolclass', pool.QueuePool)

    def initialize(self, connection):
        try:
            self.server_version_info = \
                            self._get_server_version_info(connection)
        except NotImplementedError:
            self.server_version_info = None
        try:
            self.default_schema_name = \
                            self._get_default_schema_name(connection)
        except NotImplementedError:
            self.default_schema_name = None

        try:
            self.default_isolation_level = \
                        self.get_isolation_level(connection.connection)
        except NotImplementedError:
            self.default_isolation_level = None

        self.returns_unicode_strings = self._check_unicode_returns(connection)

        self.do_rollback(connection.connection)

    def on_connect(self):
        """return a callable which sets up a newly created DBAPI connection.

        This is used to set dialect-wide per-connection options such as
        isolation modes, unicode modes, etc.

        If a callable is returned, it will be assembled into a pool listener
        that receives the direct DBAPI connection, with all wrappers removed.

        If None is returned, no listener will be generated.

        """
        return None

    def _check_unicode_returns(self, connection):
        # Py2K
        if self.supports_unicode_statements:
            cast_to = unicode
        else:
            cast_to = str
        # end Py2K
        # Py3K
        #cast_to = str

        def check_unicode(formatstr, type_):
            cursor = connection.connection.cursor()
            try:
                try:
                    cursor.execute(
                        cast_to(
                            expression.select(
                            [expression.cast(
                                expression.literal_column(
                                        "'test %s returns'" % formatstr),
                                        type_)
                            ]).compile(dialect=self)
                        )
                    )
                    row = cursor.fetchone()

                    return isinstance(row[0], unicode)
                except self.dbapi.Error, de:
                    util.warn("Exception attempting to "
                            "detect unicode returns: %r" % de)
                    return False
            finally:
                cursor.close()

        # detect plain VARCHAR
        unicode_for_varchar = check_unicode("plain", sqltypes.VARCHAR(60))

        # detect if there's an NVARCHAR type with different behavior available
        unicode_for_unicode = check_unicode("unicode", sqltypes.Unicode(60))

        if unicode_for_unicode and not unicode_for_varchar:
            return "conditional"
        else:
            return unicode_for_varchar

    def type_descriptor(self, typeobj):
        """Provide a database-specific :class:`.TypeEngine` object, given
        the generic object which comes from the types module.

        This method looks for a dictionary called
        ``colspecs`` as a class or instance-level variable,
        and passes on to :func:`.types.adapt_type`.

        """
        return sqltypes.adapt_type(typeobj, self.colspecs)

    def reflecttable(self, connection, table, include_columns,
                    exclude_columns=None):
        insp = reflection.Inspector.from_engine(connection)
        return insp.reflecttable(table, include_columns, exclude_columns)

    def get_pk_constraint(self, conn, table_name, schema=None, **kw):
        """Compatibility method, adapts the result of get_primary_keys()
        for those dialects which don't implement get_pk_constraint().

        """
        return {
            'constrained_columns':
                        self.get_primary_keys(conn, table_name,
                                                schema=schema, **kw)
        }

    def validate_identifier(self, ident):
        if len(ident) > self.max_identifier_length:
            raise exc.IdentifierError(
                "Identifier '%s' exceeds maximum length of %d characters" %
                (ident, self.max_identifier_length)
            )

    def connect(self, *cargs, **cparams):
        return self.dbapi.connect(*cargs, **cparams)

    def create_connect_args(self, url):
        opts = url.translate_connect_args()
        opts.update(url.query)
        return [[], opts]

    def do_begin(self, dbapi_connection):
        pass

    def do_rollback(self, dbapi_connection):
        dbapi_connection.rollback()

    def do_commit(self, dbapi_connection):
        dbapi_connection.commit()

    def do_close(self, dbapi_connection):
        dbapi_connection.close()

    def create_xid(self):
        """Create a random two-phase transaction ID.

        This id will be passed to do_begin_twophase(), do_rollback_twophase(),
        do_commit_twophase().  Its format is unspecified.
        """

        return "_sa_%032x" % random.randint(0, 2 ** 128)

    def do_savepoint(self, connection, name):
        connection.execute(expression.SavepointClause(name))

    def do_rollback_to_savepoint(self, connection, name):
        connection.execute(expression.RollbackToSavepointClause(name))

    def do_release_savepoint(self, connection, name):
        connection.execute(expression.ReleaseSavepointClause(name))

    def do_executemany(self, cursor, statement, parameters, context=None):
        cursor.executemany(statement, parameters)

    def do_execute(self, cursor, statement, parameters, context=None):
        cursor.execute(statement, parameters)

    def do_execute_no_params(self, cursor, statement, context=None):
        cursor.execute(statement)

    def is_disconnect(self, e, connection, cursor):
        return False

    def reset_isolation_level(self, dbapi_conn):
        # default_isolation_level is read from the first connection
        # after the initial set of 'isolation_level', if any, so is
        # the configured default of this dialect.
        self.set_isolation_level(dbapi_conn, self.default_isolation_level)


class DefaultExecutionContext(interfaces.ExecutionContext):
    isinsert = False
    isupdate = False
    isdelete = False
    isddl = False
    executemany = False
    result_map = None
    compiled = None
    statement = None
    postfetch_cols = None
    prefetch_cols = None
    _is_implicit_returning = False
    _is_explicit_returning = False

    # a hook for SQLite's translation of
    # result column names
    _translate_colname = None

    @classmethod
    def _init_ddl(cls, dialect, connection, dbapi_connection, compiled_ddl):
        """Initialize execution context for a DDLElement construct."""

        self = cls.__new__(cls)
        self.dialect = dialect
        self.root_connection = connection
        self._dbapi_connection = dbapi_connection
        self.engine = connection.engine

        self.compiled = compiled = compiled_ddl
        self.isddl = True

        self.execution_options = compiled.statement._execution_options
        if connection._execution_options:
            self.execution_options = dict(self.execution_options)
            self.execution_options.update(connection._execution_options)

        if not dialect.supports_unicode_statements:
            self.unicode_statement = unicode(compiled)
            self.statement = dialect._encoder(self.unicode_statement)[0]
        else:
            self.statement = self.unicode_statement = unicode(compiled)

        self.cursor = self.create_cursor()
        self.compiled_parameters = []

        if dialect.positional:
            self.parameters = [dialect.execute_sequence_format()]
        else:
            self.parameters = [{}]

        return self

    @classmethod
    def _init_compiled(cls, dialect, connection, dbapi_connection,
                    compiled, parameters):
        """Initialize execution context for a Compiled construct."""

        self = cls.__new__(cls)
        self.dialect = dialect
        self.root_connection = connection
        self._dbapi_connection = dbapi_connection
        self.engine = connection.engine

        self.compiled = compiled

        if not compiled.can_execute:
            raise exc.ArgumentError("Not an executable clause")

        self.execution_options = compiled.statement._execution_options
        if connection._execution_options:
            self.execution_options = dict(self.execution_options)
            self.execution_options.update(connection._execution_options)

        # compiled clauseelement.  process bind params, process table defaults,
        # track collections used by ResultProxy to target and process results

        self.result_map = compiled.result_map

        self.unicode_statement = unicode(compiled)
        if not dialect.supports_unicode_statements:
            self.statement = self.unicode_statement.encode(
                                        self.dialect.encoding)
        else:
            self.statement = self.unicode_statement

        self.isinsert = compiled.isinsert
        self.isupdate = compiled.isupdate
        self.isdelete = compiled.isdelete

        if self.isinsert or self.isupdate or self.isdelete:
            self._is_explicit_returning = bool(compiled.statement._returning)
            self._is_implicit_returning = bool(compiled.returning and \
                                            not compiled.statement._returning)

        if not parameters:
            self.compiled_parameters = [compiled.construct_params()]
        else:
            self.compiled_parameters = \
                        [compiled.construct_params(m, _group_number=grp) for
                                        grp, m in enumerate(parameters)]

            self.executemany = len(parameters) > 1

        self.cursor = self.create_cursor()
        if self.isinsert or self.isupdate:
            self.postfetch_cols = self.compiled.postfetch
            self.prefetch_cols = self.compiled.prefetch
            self.__process_defaults()

        processors = compiled._bind_processors

        # Convert the dictionary of bind parameter values
        # into a dict or list to be sent to the DBAPI's
        # execute() or executemany() method.
        parameters = []
        if dialect.positional:
            for compiled_params in self.compiled_parameters:
                param = []
                for key in self.compiled.positiontup:
                    if key in processors:
                        param.append(processors[key](compiled_params[key]))
                    else:
                        param.append(compiled_params[key])
                parameters.append(dialect.execute_sequence_format(param))
        else:
            encode = not dialect.supports_unicode_statements
            for compiled_params in self.compiled_parameters:
                param = {}
                if encode:
                    for key in compiled_params:
                        if key in processors:
                            param[dialect._encoder(key)[0]] = \
                                        processors[key](compiled_params[key])
                        else:
                            param[dialect._encoder(key)[0]] = \
                                    compiled_params[key]
                else:
                    for key in compiled_params:
                        if key in processors:
                            param[key] = processors[key](compiled_params[key])
                        else:
                            param[key] = compiled_params[key]
                parameters.append(param)
        self.parameters = dialect.execute_sequence_format(parameters)

        return self

    @classmethod
    def _init_statement(cls, dialect, connection, dbapi_connection,
                                                    statement, parameters):
        """Initialize execution context for a string SQL statement."""

        self = cls.__new__(cls)
        self.dialect = dialect
        self.root_connection = connection
        self._dbapi_connection = dbapi_connection
        self.engine = connection.engine

        # plain text statement
        self.execution_options = connection._execution_options

        if not parameters:
            if self.dialect.positional:
                self.parameters = [dialect.execute_sequence_format()]
            else:
                self.parameters = [{}]
        elif isinstance(parameters[0], dialect.execute_sequence_format):
            self.parameters = parameters
        elif isinstance(parameters[0], dict):
            if dialect.supports_unicode_statements:
                self.parameters = parameters
            else:
                self.parameters = [
                            dict((dialect._encoder(k)[0], d[k]) for k in d)
                            for d in parameters
                        ] or [{}]
        else:
            self.parameters = [dialect.execute_sequence_format(p)
                                    for p in parameters]

        self.executemany = len(parameters) > 1

        if not dialect.supports_unicode_statements and \
            isinstance(statement, unicode):
            self.unicode_statement = statement
            self.statement = dialect._encoder(statement)[0]
        else:
            self.statement = self.unicode_statement = statement

        self.cursor = self.create_cursor()
        return self

    @classmethod
    def _init_default(cls, dialect, connection, dbapi_connection):
        """Initialize execution context for a ColumnDefault construct."""

        self = cls.__new__(cls)
        self.dialect = dialect
        self.root_connection = connection
        self._dbapi_connection = dbapi_connection
        self.engine = connection.engine
        self.execution_options = connection._execution_options
        self.cursor = self.create_cursor()
        return self

    @util.memoized_property
    def no_parameters(self):
        return self.execution_options.get("no_parameters", False)

    @util.memoized_property
    def is_crud(self):
        return self.isinsert or self.isupdate or self.isdelete

    @util.memoized_property
    def should_autocommit(self):
        autocommit = self.execution_options.get('autocommit',
                                                not self.compiled and
                                                self.statement and
                                                expression.PARSE_AUTOCOMMIT
                                                or False)

        if autocommit is expression.PARSE_AUTOCOMMIT:
            return self.should_autocommit_text(self.unicode_statement)
        else:
            return autocommit

    def _execute_scalar(self, stmt, type_):
        """Execute a string statement on the current cursor, returning a
        scalar result.

        Used to fire off sequences, default phrases, and "select lastrowid"
        types of statements individually or in the context of a parent INSERT
        or UPDATE statement.

        """

        conn = self.root_connection
        if isinstance(stmt, unicode) and \
            not self.dialect.supports_unicode_statements:
            stmt = self.dialect._encoder(stmt)[0]

        if self.dialect.positional:
            default_params = self.dialect.execute_sequence_format()
        else:
            default_params = {}

        conn._cursor_execute(self.cursor, stmt, default_params, context=self)
        r = self.cursor.fetchone()[0]
        if type_ is not None:
            # apply type post processors to the result
            proc = type_._cached_result_processor(
                        self.dialect,
                        self.cursor.description[0][1]
                    )
            if proc:
                return proc(r)
        return r

    @property
    def connection(self):
        return self.root_connection._branch()

    def should_autocommit_text(self, statement):
        return AUTOCOMMIT_REGEXP.match(statement)

    def create_cursor(self):
        return self._dbapi_connection.cursor()

    def pre_exec(self):
        pass

    def post_exec(self):
        pass

    def get_result_processor(self, type_, colname, coltype):
        """Return a 'result processor' for a given type as present in
        cursor.description.

        This has a default implementation that dialects can override
        for context-sensitive result type handling.

        """
        return type_._cached_result_processor(self.dialect, coltype)

    def get_lastrowid(self):
        """return self.cursor.lastrowid, or equivalent, after an INSERT.

        This may involve calling special cursor functions,
        issuing a new SELECT on the cursor (or a new one),
        or returning a stored value that was
        calculated within post_exec().

        This function will only be called for dialects
        which support "implicit" primary key generation,
        keep preexecute_autoincrement_sequences set to False,
        and when no explicit id value was bound to the
        statement.

        The function is called once, directly after
        post_exec() and before the transaction is committed
        or ResultProxy is generated.   If the post_exec()
        method assigns a value to `self._lastrowid`, the
        value is used in place of calling get_lastrowid().

        Note that this method is *not* equivalent to the
        ``lastrowid`` method on ``ResultProxy``, which is a
        direct proxy to the DBAPI ``lastrowid`` accessor
        in all cases.

        """
        return self.cursor.lastrowid

    def handle_dbapi_exception(self, e):
        pass

    def get_result_proxy(self):
        return result.ResultProxy(self)

    @property
    def rowcount(self):
        return self.cursor.rowcount

    def supports_sane_rowcount(self):
        return self.dialect.supports_sane_rowcount

    def supports_sane_multi_rowcount(self):
        return self.dialect.supports_sane_multi_rowcount

    def post_insert(self):
        if not self._is_implicit_returning and \
            not self._is_explicit_returning and \
            not self.compiled.inline and \
            self.dialect.postfetch_lastrowid and \
            (not self.inserted_primary_key or \
                        None in self.inserted_primary_key):

            table = self.compiled.statement.table
            lastrowid = self.get_lastrowid()
            autoinc_col = table._autoincrement_column
            if autoinc_col is not None:
                # apply type post processors to the lastrowid
                proc = autoinc_col.type._cached_result_processor(
                                        self.dialect, None)
                if proc is not None:
                    lastrowid = proc(lastrowid)

            self.inserted_primary_key = [
                lastrowid if c is autoinc_col else v
                for c, v in zip(
                                    table.primary_key,
                                    self.inserted_primary_key)
            ]

    def _fetch_implicit_returning(self, resultproxy):
        table = self.compiled.statement.table
        row = resultproxy.fetchone()

        ipk = []
        for c, v in zip(table.primary_key, self.inserted_primary_key):
            if v is not None:
                ipk.append(v)
            else:
                ipk.append(row[c])

        self.inserted_primary_key = ipk

    def lastrow_has_defaults(self):
        return (self.isinsert or self.isupdate) and \
            bool(self.postfetch_cols)

    def set_input_sizes(self, translate=None, exclude_types=None):
        """Given a cursor and ClauseParameters, call the appropriate
        style of ``setinputsizes()`` on the cursor, using DB-API types
        from the bind parameter's ``TypeEngine`` objects.

        This method only called by those dialects which require it,
        currently cx_oracle.

        """

        if not hasattr(self.compiled, 'bind_names'):
            return

        types = dict(
                (self.compiled.bind_names[bindparam], bindparam.type)
                 for bindparam in self.compiled.bind_names)

        if self.dialect.positional:
            inputsizes = []
            for key in self.compiled.positiontup:
                typeengine = types[key]
                dbtype = typeengine.dialect_impl(self.dialect).\
                                    get_dbapi_type(self.dialect.dbapi)
                if dbtype is not None and \
                    (not exclude_types or dbtype not in exclude_types):
                    inputsizes.append(dbtype)
            try:
                self.cursor.setinputsizes(*inputsizes)
            except Exception, e:
                self.root_connection._handle_dbapi_exception(
                                e, None, None, None, self)
        else:
            inputsizes = {}
            for key in self.compiled.bind_names.values():
                typeengine = types[key]
                dbtype = typeengine.dialect_impl(self.dialect).\
                                get_dbapi_type(self.dialect.dbapi)
                if dbtype is not None and \
                        (not exclude_types or dbtype not in exclude_types):
                    if translate:
                        key = translate.get(key, key)
                    if not self.dialect.supports_unicode_binds:
                        key = self.dialect._encoder(key)[0]
                    inputsizes[key] = dbtype
            try:
                self.cursor.setinputsizes(**inputsizes)
            except Exception, e:
                self.root_connection._handle_dbapi_exception(
                                e, None, None, None, self)

    def _exec_default(self, default, type_):
        if default.is_sequence:
            return self.fire_sequence(default, type_)
        elif default.is_callable:
            return default.arg(self)
        elif default.is_clause_element:
            # TODO: expensive branching here should be
            # pulled into _exec_scalar()
            conn = self.connection
            c = expression.select([default.arg]).compile(bind=conn)
            return conn._execute_compiled(c, (), {}).scalar()
        else:
            return default.arg

    def get_insert_default(self, column):
        if column.default is None:
            return None
        else:
            return self._exec_default(column.default, column.type)

    def get_update_default(self, column):
        if column.onupdate is None:
            return None
        else:
            return self._exec_default(column.onupdate, column.type)

    def __process_defaults(self):
        """Generate default values for compiled insert/update statements,
        and generate inserted_primary_key collection.
        """

        if self.executemany:
            if len(self.compiled.prefetch):
                scalar_defaults = {}

                # pre-determine scalar Python-side defaults
                # to avoid many calls of get_insert_default()/
                # get_update_default()
                for c in self.prefetch_cols:
                    if self.isinsert and c.default and c.default.is_scalar:
                        scalar_defaults[c] = c.default.arg
                    elif self.isupdate and c.onupdate and c.onupdate.is_scalar:
                        scalar_defaults[c] = c.onupdate.arg

                for param in self.compiled_parameters:
                    self.current_parameters = param
                    for c in self.prefetch_cols:
                        if c in scalar_defaults:
                            val = scalar_defaults[c]
                        elif self.isinsert:
                            val = self.get_insert_default(c)
                        else:
                            val = self.get_update_default(c)
                        if val is not None:
                            param[c.key] = val
                del self.current_parameters
        else:
            self.current_parameters = compiled_parameters = \
                                        self.compiled_parameters[0]

            for c in self.compiled.prefetch:
                if self.isinsert:
                    val = self.get_insert_default(c)
                else:
                    val = self.get_update_default(c)

                if val is not None:
                    compiled_parameters[c.key] = val
            del self.current_parameters

            if self.isinsert:
                self.inserted_primary_key = [
                                self.compiled_parameters[0].get(c.key, None)
                                        for c in self.compiled.\
                                                statement.table.primary_key
                                ]


DefaultDialect.execution_ctx_cls = DefaultExecutionContext
