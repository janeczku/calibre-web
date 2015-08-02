# oracle/base.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""
.. dialect:: oracle
    :name: Oracle

    Oracle version 8 through current (11g at the time of this writing) are supported.

Connect Arguments
-----------------

The dialect supports several :func:`~sqlalchemy.create_engine()` arguments which
affect the behavior of the dialect regardless of driver in use.

* *use_ansi* - Use ANSI JOIN constructs (see the section on Oracle 8).  Defaults
  to ``True``.  If ``False``, Oracle-8 compatible constructs are used for joins.

* *optimize_limits* - defaults to ``False``. see the section on LIMIT/OFFSET.

* *use_binds_for_limits* - defaults to ``True``.  see the section on LIMIT/OFFSET.

Auto Increment Behavior
-----------------------

SQLAlchemy Table objects which include integer primary keys are usually assumed to have
"autoincrementing" behavior, meaning they can generate their own primary key values upon
INSERT.  Since Oracle has no "autoincrement" feature, SQLAlchemy relies upon sequences
to produce these values.   With the Oracle dialect, *a sequence must always be explicitly
specified to enable autoincrement*.  This is divergent with the majority of documentation
examples which assume the usage of an autoincrement-capable database.   To specify sequences,
use the sqlalchemy.schema.Sequence object which is passed to a Column construct::

  t = Table('mytable', metadata,
        Column('id', Integer, Sequence('id_seq'), primary_key=True),
        Column(...), ...
  )

This step is also required when using table reflection, i.e. autoload=True::

  t = Table('mytable', metadata,
        Column('id', Integer, Sequence('id_seq'), primary_key=True),
        autoload=True
  )

Identifier Casing
-----------------

In Oracle, the data dictionary represents all case insensitive identifier names
using UPPERCASE text.   SQLAlchemy on the other hand considers an all-lower case identifier
name to be case insensitive.   The Oracle dialect converts all case insensitive identifiers
to and from those two formats during schema level communication, such as reflection of
tables and indexes.   Using an UPPERCASE name on the SQLAlchemy side indicates a
case sensitive identifier, and SQLAlchemy will quote the name - this will cause mismatches
against data dictionary data received from Oracle, so unless identifier names have been
truly created as case sensitive (i.e. using quoted names), all lowercase names should be
used on the SQLAlchemy side.

Unicode
-------

.. versionchanged:: 0.6
    SQLAlchemy uses the "native unicode" mode provided as of cx_oracle 5.
    cx_oracle 5.0.2 or greater is recommended for support of NCLOB.
    If not using cx_oracle 5, the NLS_LANG environment variable needs
    to be set in order for the oracle client library to use proper encoding,
    such as "AMERICAN_AMERICA.UTF8".

Also note that Oracle supports unicode data through the NVARCHAR and NCLOB data types.
When using the SQLAlchemy Unicode and UnicodeText types, these DDL types will be used
within CREATE TABLE statements.   Usage of VARCHAR2 and CLOB with unicode text still
requires NLS_LANG to be set.

LIMIT/OFFSET Support
--------------------

Oracle has no support for the LIMIT or OFFSET keywords.  SQLAlchemy uses
a wrapped subquery approach in conjunction with ROWNUM.  The exact methodology
is taken from
http://www.oracle.com/technology/oramag/oracle/06-sep/o56asktom.html .

There are two options which affect its behavior:

* the "FIRST ROWS()" optimization keyword is not used by default.  To enable the usage of this
  optimization directive, specify ``optimize_limits=True`` to :func:`.create_engine`.
* the values passed for the limit/offset are sent as bound parameters.   Some users have observed
  that Oracle produces a poor query plan when the values are sent as binds and not
  rendered literally.   To render the limit/offset values literally within the SQL
  statement, specify ``use_binds_for_limits=False`` to :func:`.create_engine`.

Some users have reported better performance when the entirely different approach of a
window query is used, i.e. ROW_NUMBER() OVER (ORDER BY), to provide LIMIT/OFFSET (note
that the majority of users don't observe this).  To suit this case the
method used for LIMIT/OFFSET can be replaced entirely.  See the recipe at
http://www.sqlalchemy.org/trac/wiki/UsageRecipes/WindowFunctionsByDefault
which installs a select compiler that overrides the generation of limit/offset with
a window function.

ON UPDATE CASCADE
-----------------

Oracle doesn't have native ON UPDATE CASCADE functionality.  A trigger based solution
is available at http://asktom.oracle.com/tkyte/update_cascade/index.html .

When using the SQLAlchemy ORM, the ORM has limited ability to manually issue
cascading updates - specify ForeignKey objects using the
"deferrable=True, initially='deferred'" keyword arguments,
and specify "passive_updates=False" on each relationship().

Oracle 8 Compatibility
----------------------

When Oracle 8 is detected, the dialect internally configures itself to the following
behaviors:

* the use_ansi flag is set to False.  This has the effect of converting all
  JOIN phrases into the WHERE clause, and in the case of LEFT OUTER JOIN
  makes use of Oracle's (+) operator.

* the NVARCHAR2 and NCLOB datatypes are no longer generated as DDL when
  the :class:`~sqlalchemy.types.Unicode` is used - VARCHAR2 and CLOB are issued
  instead.   This because these types don't seem to work correctly on Oracle 8
  even though they are available.  The :class:`~sqlalchemy.types.NVARCHAR`
  and :class:`~sqlalchemy.dialects.oracle.NCLOB` types will always generate NVARCHAR2 and NCLOB.

* the "native unicode" mode is disabled when using cx_oracle, i.e. SQLAlchemy
  encodes all Python unicode objects to "string" before passing in as bind parameters.

Synonym/DBLINK Reflection
-------------------------

When using reflection with Table objects, the dialect can optionally search for tables
indicated by synonyms, either in local or remote schemas or accessed over DBLINK,
by passing the flag oracle_resolve_synonyms=True as a
keyword argument to the Table construct.   If synonyms are not in use
this flag should be left off.

"""

import re

from sqlalchemy import util, sql
from sqlalchemy.engine import default, base, reflection
from sqlalchemy.sql import compiler, visitors, expression
from sqlalchemy.sql import operators as sql_operators, functions as sql_functions
from sqlalchemy import types as sqltypes
from sqlalchemy.types import VARCHAR, NVARCHAR, CHAR, DATE, DATETIME, \
                BLOB, CLOB, TIMESTAMP, FLOAT

RESERVED_WORDS = \
    set('SHARE RAW DROP BETWEEN FROM DESC OPTION PRIOR LONG THEN '\
        'DEFAULT ALTER IS INTO MINUS INTEGER NUMBER GRANT IDENTIFIED '\
        'ALL TO ORDER ON FLOAT DATE HAVING CLUSTER NOWAIT RESOURCE '\
        'ANY TABLE INDEX FOR UPDATE WHERE CHECK SMALLINT WITH DELETE '\
        'BY ASC REVOKE LIKE SIZE RENAME NOCOMPRESS NULL GROUP VALUES '\
        'AS IN VIEW EXCLUSIVE COMPRESS SYNONYM SELECT INSERT EXISTS '\
        'NOT TRIGGER ELSE CREATE INTERSECT PCTFREE DISTINCT USER '\
        'CONNECT SET MODE OF UNIQUE VARCHAR2 VARCHAR LOCK OR CHAR '\
        'DECIMAL UNION PUBLIC AND START UID COMMENT CURRENT LEVEL'.split())

NO_ARG_FNS = set('UID CURRENT_DATE SYSDATE USER '
                'CURRENT_TIME CURRENT_TIMESTAMP'.split())


class RAW(sqltypes._Binary):
    __visit_name__ = 'RAW'
OracleRaw = RAW


class NCLOB(sqltypes.Text):
    __visit_name__ = 'NCLOB'


class VARCHAR2(VARCHAR):
    __visit_name__ = 'VARCHAR2'

NVARCHAR2 = NVARCHAR


class NUMBER(sqltypes.Numeric, sqltypes.Integer):
    __visit_name__ = 'NUMBER'

    def __init__(self, precision=None, scale=None, asdecimal=None):
        if asdecimal is None:
            asdecimal = bool(scale and scale > 0)

        super(NUMBER, self).__init__(precision=precision, scale=scale, asdecimal=asdecimal)

    def adapt(self, impltype):
        ret = super(NUMBER, self).adapt(impltype)
        # leave a hint for the DBAPI handler
        ret._is_oracle_number = True
        return ret

    @property
    def _type_affinity(self):
        if bool(self.scale and self.scale > 0):
            return sqltypes.Numeric
        else:
            return sqltypes.Integer


class DOUBLE_PRECISION(sqltypes.Numeric):
    __visit_name__ = 'DOUBLE_PRECISION'

    def __init__(self, precision=None, scale=None, asdecimal=None):
        if asdecimal is None:
            asdecimal = False

        super(DOUBLE_PRECISION, self).__init__(precision=precision, scale=scale, asdecimal=asdecimal)


class BFILE(sqltypes.LargeBinary):
    __visit_name__ = 'BFILE'


class LONG(sqltypes.Text):
    __visit_name__ = 'LONG'


class INTERVAL(sqltypes.TypeEngine):
    __visit_name__ = 'INTERVAL'

    def __init__(self,
                    day_precision=None,
                    second_precision=None):
        """Construct an INTERVAL.

        Note that only DAY TO SECOND intervals are currently supported.
        This is due to a lack of support for YEAR TO MONTH intervals
        within available DBAPIs (cx_oracle and zxjdbc).

        :param day_precision: the day precision value.  this is the number of digits
          to store for the day field.  Defaults to "2"
        :param second_precision: the second precision value.  this is the number of digits
          to store for the fractional seconds field.  Defaults to "6".

        """
        self.day_precision = day_precision
        self.second_precision = second_precision

    @classmethod
    def _adapt_from_generic_interval(cls, interval):
        return INTERVAL(day_precision=interval.day_precision,
                        second_precision=interval.second_precision)

    @property
    def _type_affinity(self):
        return sqltypes.Interval


class ROWID(sqltypes.TypeEngine):
    """Oracle ROWID type.

    When used in a cast() or similar, generates ROWID.

    """
    __visit_name__ = 'ROWID'


class _OracleBoolean(sqltypes.Boolean):
    def get_dbapi_type(self, dbapi):
        return dbapi.NUMBER

colspecs = {
    sqltypes.Boolean: _OracleBoolean,
    sqltypes.Interval: INTERVAL,
}

ischema_names = {
    'VARCHAR2': VARCHAR,
    'NVARCHAR2': NVARCHAR,
    'CHAR': CHAR,
    'DATE': DATE,
    'NUMBER': NUMBER,
    'BLOB': BLOB,
    'BFILE': BFILE,
    'CLOB': CLOB,
    'NCLOB': NCLOB,
    'TIMESTAMP': TIMESTAMP,
    'TIMESTAMP WITH TIME ZONE': TIMESTAMP,
    'INTERVAL DAY TO SECOND': INTERVAL,
    'RAW': RAW,
    'FLOAT': FLOAT,
    'DOUBLE PRECISION': DOUBLE_PRECISION,
    'LONG': LONG,
}


class OracleTypeCompiler(compiler.GenericTypeCompiler):
    # Note:
    # Oracle DATE == DATETIME
    # Oracle does not allow milliseconds in DATE
    # Oracle does not support TIME columns

    def visit_datetime(self, type_):
        return self.visit_DATE(type_)

    def visit_float(self, type_):
        return self.visit_FLOAT(type_)

    def visit_unicode(self, type_):
        if self.dialect._supports_nchar:
            return self.visit_NVARCHAR2(type_)
        else:
            return self.visit_VARCHAR2(type_)

    def visit_INTERVAL(self, type_):
        return "INTERVAL DAY%s TO SECOND%s" % (
            type_.day_precision is not None and
                "(%d)" % type_.day_precision or
                "",
            type_.second_precision is not None and
                "(%d)" % type_.second_precision or
                "",
        )

    def visit_LONG(self, type_):
        return "LONG"

    def visit_TIMESTAMP(self, type_):
        if type_.timezone:
            return "TIMESTAMP WITH TIME ZONE"
        else:
            return "TIMESTAMP"

    def visit_DOUBLE_PRECISION(self, type_):
        return self._generate_numeric(type_, "DOUBLE PRECISION")

    def visit_NUMBER(self, type_, **kw):
        return self._generate_numeric(type_, "NUMBER", **kw)

    def _generate_numeric(self, type_, name, precision=None, scale=None):
        if precision is None:
            precision = type_.precision

        if scale is None:
            scale = getattr(type_, 'scale', None)

        if precision is None:
            return name
        elif scale is None:
            n = "%(name)s(%(precision)s)"
            return n % {'name': name, 'precision': precision}
        else:
            n = "%(name)s(%(precision)s, %(scale)s)"
            return n % {'name': name, 'precision': precision, 'scale': scale}

    def visit_string(self, type_):
        return self.visit_VARCHAR2(type_)

    def visit_VARCHAR2(self, type_):
        return self._visit_varchar(type_, '', '2')

    def visit_NVARCHAR2(self, type_):
        return self._visit_varchar(type_, 'N', '2')
    visit_NVARCHAR = visit_NVARCHAR2

    def visit_VARCHAR(self, type_):
        return self._visit_varchar(type_, '', '')

    def _visit_varchar(self, type_, n, num):
        if not n and self.dialect._supports_char_length:
            varchar = "VARCHAR%(two)s(%(length)s CHAR)"
            return varchar % {'length': type_.length, 'two': num}
        else:
            varchar = "%(n)sVARCHAR%(two)s(%(length)s)"
            return varchar % {'length': type_.length, 'two': num, 'n': n}

    def visit_text(self, type_):
        return self.visit_CLOB(type_)

    def visit_unicode_text(self, type_):
        if self.dialect._supports_nchar:
            return self.visit_NCLOB(type_)
        else:
            return self.visit_CLOB(type_)

    def visit_large_binary(self, type_):
        return self.visit_BLOB(type_)

    def visit_big_integer(self, type_):
        return self.visit_NUMBER(type_, precision=19)

    def visit_boolean(self, type_):
        return self.visit_SMALLINT(type_)

    def visit_RAW(self, type_):
        if type_.length:
            return "RAW(%(length)s)" % {'length': type_.length}
        else:
            return "RAW"

    def visit_ROWID(self, type_):
        return "ROWID"


class OracleCompiler(compiler.SQLCompiler):
    """Oracle compiler modifies the lexical structure of Select
    statements to work under non-ANSI configured Oracle databases, if
    the use_ansi flag is False.
    """

    compound_keywords = util.update_copy(
        compiler.SQLCompiler.compound_keywords,
        {
        expression.CompoundSelect.EXCEPT: 'MINUS'
        }
    )

    def __init__(self, *args, **kwargs):
        self.__wheres = {}
        self._quoted_bind_names = {}
        super(OracleCompiler, self).__init__(*args, **kwargs)

    def visit_mod_binary(self, binary, operator, **kw):
        return "mod(%s, %s)" % (self.process(binary.left, **kw),
                                self.process(binary.right, **kw))

    def visit_now_func(self, fn, **kw):
        return "CURRENT_TIMESTAMP"

    def visit_char_length_func(self, fn, **kw):
        return "LENGTH" + self.function_argspec(fn, **kw)

    def visit_match_op_binary(self, binary, operator, **kw):
        return "CONTAINS (%s, %s)" % (self.process(binary.left),
                                        self.process(binary.right))

    def visit_true(self, expr, **kw):
        return '1'

    def visit_false(self, expr, **kw):
        return '0'

    def get_select_hint_text(self, byfroms):
        return " ".join(
            "/*+ %s */" % text for table, text in byfroms.items()
        )

    def function_argspec(self, fn, **kw):
        if len(fn.clauses) > 0 or fn.name.upper() not in NO_ARG_FNS:
            return compiler.SQLCompiler.function_argspec(self, fn, **kw)
        else:
            return ""

    def default_from(self):
        """Called when a ``SELECT`` statement has no froms,
        and no ``FROM`` clause is to be appended.

        The Oracle compiler tacks a "FROM DUAL" to the statement.
        """

        return " FROM DUAL"

    def visit_join(self, join, **kwargs):
        if self.dialect.use_ansi:
            return compiler.SQLCompiler.visit_join(self, join, **kwargs)
        else:
            kwargs['asfrom'] = True
            return self.process(join.left, **kwargs) + \
                        ", " + self.process(join.right, **kwargs)

    def _get_nonansi_join_whereclause(self, froms):
        clauses = []

        def visit_join(join):
            if join.isouter:
                def visit_binary(binary):
                    if binary.operator == sql_operators.eq:
                        if binary.left.table is join.right:
                            binary.left = _OuterJoinColumn(binary.left)
                        elif binary.right.table is join.right:
                            binary.right = _OuterJoinColumn(binary.right)
                clauses.append(visitors.cloned_traverse(join.onclause, {},
                                {'binary': visit_binary}))
            else:
                clauses.append(join.onclause)

            for j in join.left, join.right:
                if isinstance(j, expression.Join):
                    visit_join(j)

        for f in froms:
            if isinstance(f, expression.Join):
                visit_join(f)

        if not clauses:
            return None
        else:
            return sql.and_(*clauses)

    def visit_outer_join_column(self, vc):
        return self.process(vc.column) + "(+)"

    def visit_sequence(self, seq):
        return self.dialect.identifier_preparer.format_sequence(seq) + ".nextval"

    def visit_alias(self, alias, asfrom=False, ashint=False, **kwargs):
        """Oracle doesn't like ``FROM table AS alias``.  Is the AS standard SQL??"""

        if asfrom or ashint:
            alias_name = isinstance(alias.name, expression._truncated_label) and \
                            self._truncated_identifier("alias", alias.name) or alias.name

        if ashint:
            return alias_name
        elif asfrom:
            return self.process(alias.original, asfrom=asfrom, **kwargs) + \
                            " " + self.preparer.format_alias(alias, alias_name)
        else:
            return self.process(alias.original, **kwargs)

    def returning_clause(self, stmt, returning_cols):

        columns = []
        binds = []
        for i, column in enumerate(expression._select_iterables(returning_cols)):
            if column.type._has_column_expression:
                col_expr = column.type.column_expression(column)
            else:
                col_expr = column
            outparam = sql.outparam("ret_%d" % i, type_=column.type)
            self.binds[outparam.key] = outparam
            binds.append(self.bindparam_string(self._truncate_bindparam(outparam)))
            columns.append(self.process(col_expr, within_columns_clause=False))
            self.result_map[outparam.key] = (
                outparam.key,
                (column, getattr(column, 'name', None),
                                        getattr(column, 'key', None)),
                column.type
            )

        return 'RETURNING ' + ', '.join(columns) + " INTO " + ", ".join(binds)

    def _TODO_visit_compound_select(self, select):
        """Need to determine how to get ``LIMIT``/``OFFSET`` into a ``UNION`` for Oracle."""
        pass

    def visit_select(self, select, **kwargs):
        """Look for ``LIMIT`` and OFFSET in a select statement, and if
        so tries to wrap it in a subquery with ``rownum`` criterion.
        """

        if not getattr(select, '_oracle_visit', None):
            if not self.dialect.use_ansi:
                froms = self._display_froms_for_select(
                                    select, kwargs.get('asfrom', False))
                whereclause = self._get_nonansi_join_whereclause(froms)
                if whereclause is not None:
                    select = select.where(whereclause)
                    select._oracle_visit = True

            if select._limit is not None or select._offset is not None:
                # See http://www.oracle.com/technology/oramag/oracle/06-sep/o56asktom.html
                #
                # Generalized form of an Oracle pagination query:
                #   select ... from (
                #     select /*+ FIRST_ROWS(N) */ ...., rownum as ora_rn from (
                #         select distinct ... where ... order by ...
                #     ) where ROWNUM <= :limit+:offset
                #   ) where ora_rn > :offset
                # Outer select and "ROWNUM as ora_rn" can be dropped if limit=0

                # TODO: use annotations instead of clone + attr set ?
                select = select._generate()
                select._oracle_visit = True

                # Wrap the middle select and add the hint
                limitselect = sql.select([c for c in select.c])
                if select._limit and self.dialect.optimize_limits:
                    limitselect = limitselect.prefix_with("/*+ FIRST_ROWS(%d) */" % select._limit)

                limitselect._oracle_visit = True
                limitselect._is_wrapper = True

                # If needed, add the limiting clause
                if select._limit is not None:
                    max_row = select._limit
                    if select._offset is not None:
                        max_row += select._offset
                    if not self.dialect.use_binds_for_limits:
                        max_row = sql.literal_column("%d" % max_row)
                    limitselect.append_whereclause(
                            sql.literal_column("ROWNUM") <= max_row)

                # If needed, add the ora_rn, and wrap again with offset.
                if select._offset is None:
                    limitselect.for_update = select.for_update
                    select = limitselect
                else:
                    limitselect = limitselect.column(
                             sql.literal_column("ROWNUM").label("ora_rn"))
                    limitselect._oracle_visit = True
                    limitselect._is_wrapper = True

                    offsetselect = sql.select(
                             [c for c in limitselect.c if c.key != 'ora_rn'])
                    offsetselect._oracle_visit = True
                    offsetselect._is_wrapper = True

                    offset_value = select._offset
                    if not self.dialect.use_binds_for_limits:
                        offset_value = sql.literal_column("%d" % offset_value)
                    offsetselect.append_whereclause(
                             sql.literal_column("ora_rn") > offset_value)

                    offsetselect.for_update = select.for_update
                    select = offsetselect

        kwargs['iswrapper'] = getattr(select, '_is_wrapper', False)
        return compiler.SQLCompiler.visit_select(self, select, **kwargs)

    def limit_clause(self, select):
        return ""

    def for_update_clause(self, select):
        if self.is_subquery():
            return ""
        elif select.for_update == "nowait":
            return " FOR UPDATE NOWAIT"
        else:
            return super(OracleCompiler, self).for_update_clause(select)


class OracleDDLCompiler(compiler.DDLCompiler):

    def define_constraint_cascades(self, constraint):
        text = ""
        if constraint.ondelete is not None:
            text += " ON DELETE %s" % constraint.ondelete

        # oracle has no ON UPDATE CASCADE -
        # its only available via triggers http://asktom.oracle.com/tkyte/update_cascade/index.html
        if constraint.onupdate is not None:
            util.warn(
                "Oracle does not contain native UPDATE CASCADE "
                 "functionality - onupdates will not be rendered for foreign keys. "
                 "Consider using deferrable=True, initially='deferred' or triggers.")

        return text

    def visit_create_index(self, create, **kw):
        return super(OracleDDLCompiler, self).\
                    visit_create_index(create, include_schema=True)


class OracleIdentifierPreparer(compiler.IdentifierPreparer):

    reserved_words = set([x.lower() for x in RESERVED_WORDS])
    illegal_initial_characters = set(xrange(0, 10)).union(["_", "$"])

    def _bindparam_requires_quotes(self, value):
        """Return True if the given identifier requires quoting."""
        lc_value = value.lower()
        return (lc_value in self.reserved_words
                or value[0] in self.illegal_initial_characters
                or not self.legal_characters.match(unicode(value))
                )

    def format_savepoint(self, savepoint):
        name = re.sub(r'^_+', '', savepoint.ident)
        return super(OracleIdentifierPreparer, self).format_savepoint(savepoint, name)


class OracleExecutionContext(default.DefaultExecutionContext):
    def fire_sequence(self, seq, type_):
        return self._execute_scalar("SELECT " +
                    self.dialect.identifier_preparer.format_sequence(seq) +
                    ".nextval FROM DUAL", type_)


class OracleDialect(default.DefaultDialect):
    name = 'oracle'
    supports_alter = True
    supports_unicode_statements = False
    supports_unicode_binds = False
    max_identifier_length = 30
    supports_sane_rowcount = True
    supports_sane_multi_rowcount = False

    supports_sequences = True
    sequences_optional = False
    postfetch_lastrowid = False

    default_paramstyle = 'named'
    colspecs = colspecs
    ischema_names = ischema_names
    requires_name_normalize = True

    supports_default_values = False
    supports_empty_insert = False

    statement_compiler = OracleCompiler
    ddl_compiler = OracleDDLCompiler
    type_compiler = OracleTypeCompiler
    preparer = OracleIdentifierPreparer
    execution_ctx_cls = OracleExecutionContext

    reflection_options = ('oracle_resolve_synonyms', )

    def __init__(self,
                use_ansi=True,
                optimize_limits=False,
                use_binds_for_limits=True,
                **kwargs):
        default.DefaultDialect.__init__(self, **kwargs)
        self.use_ansi = use_ansi
        self.optimize_limits = optimize_limits
        self.use_binds_for_limits = use_binds_for_limits

    def initialize(self, connection):
        super(OracleDialect, self).initialize(connection)
        self.implicit_returning = self.__dict__.get(
                                    'implicit_returning',
                                    self.server_version_info > (10, )
                                    )

        if self._is_oracle_8:
            self.colspecs = self.colspecs.copy()
            self.colspecs.pop(sqltypes.Interval)
            self.use_ansi = False

    @property
    def _is_oracle_8(self):
        return self.server_version_info and \
                    self.server_version_info < (9, )

    @property
    def _supports_char_length(self):
        return not self._is_oracle_8

    @property
    def _supports_nchar(self):
        return not self._is_oracle_8

    def do_release_savepoint(self, connection, name):
        # Oracle does not support RELEASE SAVEPOINT
        pass

    def has_table(self, connection, table_name, schema=None):
        if not schema:
            schema = self.default_schema_name
        cursor = connection.execute(
            sql.text("SELECT table_name FROM all_tables "
                     "WHERE table_name = :name AND owner = :schema_name"),
            name=self.denormalize_name(table_name), schema_name=self.denormalize_name(schema))
        return cursor.first() is not None

    def has_sequence(self, connection, sequence_name, schema=None):
        if not schema:
            schema = self.default_schema_name
        cursor = connection.execute(
            sql.text("SELECT sequence_name FROM all_sequences "
                     "WHERE sequence_name = :name AND sequence_owner = :schema_name"),
            name=self.denormalize_name(sequence_name), schema_name=self.denormalize_name(schema))
        return cursor.first() is not None

    def normalize_name(self, name):
        if name is None:
            return None
        # Py2K
        if isinstance(name, str):
            name = name.decode(self.encoding)
        # end Py2K
        if name.upper() == name and \
              not self.identifier_preparer._requires_quotes(name.lower()):
            return name.lower()
        else:
            return name

    def denormalize_name(self, name):
        if name is None:
            return None
        elif name.lower() == name and not self.identifier_preparer._requires_quotes(name.lower()):
            name = name.upper()
        # Py2K
        if not self.supports_unicode_binds:
            name = name.encode(self.encoding)
        else:
            name = unicode(name)
        # end Py2K
        return name

    def _get_default_schema_name(self, connection):
        return self.normalize_name(connection.execute(u'SELECT USER FROM DUAL').scalar())

    def _resolve_synonym(self, connection, desired_owner=None, desired_synonym=None, desired_table=None):
        """search for a local synonym matching the given desired owner/name.

        if desired_owner is None, attempts to locate a distinct owner.

        returns the actual name, owner, dblink name, and synonym name if found.
        """

        q = "SELECT owner, table_owner, table_name, db_link, "\
                    "synonym_name FROM all_synonyms WHERE "
        clauses = []
        params = {}
        if desired_synonym:
            clauses.append("synonym_name = :synonym_name")
            params['synonym_name'] = desired_synonym
        if desired_owner:
            clauses.append("owner = :desired_owner")
            params['desired_owner'] = desired_owner
        if desired_table:
            clauses.append("table_name = :tname")
            params['tname'] = desired_table

        q += " AND ".join(clauses)

        result = connection.execute(sql.text(q), **params)
        if desired_owner:
            row = result.first()
            if row:
                return row['table_name'], row['table_owner'], row['db_link'], row['synonym_name']
            else:
                return None, None, None, None
        else:
            rows = result.fetchall()
            if len(rows) > 1:
                raise AssertionError("There are multiple tables visible to the schema, you must specify owner")
            elif len(rows) == 1:
                row = rows[0]
                return row['table_name'], row['table_owner'], row['db_link'], row['synonym_name']
            else:
                return None, None, None, None

    @reflection.cache
    def _prepare_reflection_args(self, connection, table_name, schema=None,
                                 resolve_synonyms=False, dblink='', **kw):

        if resolve_synonyms:
            actual_name, owner, dblink, synonym = self._resolve_synonym(
                        connection,
                         desired_owner=self.denormalize_name(schema),
                         desired_synonym=self.denormalize_name(table_name)
                       )
        else:
            actual_name, owner, dblink, synonym = None, None, None, None
        if not actual_name:
            actual_name = self.denormalize_name(table_name)

        if dblink:
            # using user_db_links here since all_db_links appears
            # to have more restricted permissions.
            # http://docs.oracle.com/cd/B28359_01/server.111/b28310/ds_admin005.htm
            # will need to hear from more users if we are doing
            # the right thing here.  See [ticket:2619]
            owner = connection.scalar(
                            sql.text("SELECT username FROM user_db_links "
                                    "WHERE db_link=:link"), link=dblink)
            dblink = "@" + dblink
        elif not owner:
            owner = self.denormalize_name(schema or self.default_schema_name)

        return (actual_name, owner, dblink or '', synonym)

    @reflection.cache
    def get_schema_names(self, connection, **kw):
        s = "SELECT username FROM all_users ORDER BY username"
        cursor = connection.execute(s,)
        return [self.normalize_name(row[0]) for row in cursor]

    @reflection.cache
    def get_table_names(self, connection, schema=None, **kw):
        schema = self.denormalize_name(schema or self.default_schema_name)

        # note that table_names() isnt loading DBLINKed or synonym'ed tables
        if schema is None:
            schema = self.default_schema_name
        s = sql.text(
            "SELECT table_name FROM all_tables "
            "WHERE nvl(tablespace_name, 'no tablespace') NOT IN ('SYSTEM', 'SYSAUX') "
            "AND OWNER = :owner "
            "AND IOT_NAME IS NULL")
        cursor = connection.execute(s, owner=schema)
        return [self.normalize_name(row[0]) for row in cursor]

    @reflection.cache
    def get_view_names(self, connection, schema=None, **kw):
        schema = self.denormalize_name(schema or self.default_schema_name)
        s = sql.text("SELECT view_name FROM all_views WHERE owner = :owner")
        cursor = connection.execute(s, owner=self.denormalize_name(schema))
        return [self.normalize_name(row[0]) for row in cursor]

    @reflection.cache
    def get_columns(self, connection, table_name, schema=None, **kw):
        """

        kw arguments can be:

            oracle_resolve_synonyms

            dblink

        """

        resolve_synonyms = kw.get('oracle_resolve_synonyms', False)
        dblink = kw.get('dblink', '')
        info_cache = kw.get('info_cache')

        (table_name, schema, dblink, synonym) = \
            self._prepare_reflection_args(connection, table_name, schema,
                                          resolve_synonyms, dblink,
                                          info_cache=info_cache)
        columns = []
        if self._supports_char_length:
            char_length_col = 'char_length'
        else:
            char_length_col = 'data_length'

        params = {"table_name": table_name}
        text = "SELECT column_name, data_type, %(char_length_col)s, "\
                "data_precision, data_scale, "\
                "nullable, data_default FROM ALL_TAB_COLUMNS%(dblink)s "\
                "WHERE table_name = :table_name"
        if schema is not None:
            params['owner'] = schema
            text += " AND owner = :owner "
        text += " ORDER BY column_id"
        text = text % {'dblink': dblink, 'char_length_col': char_length_col}

        c = connection.execute(sql.text(text), **params)

        for row in c:
            (colname, orig_colname, coltype, length, precision, scale, nullable, default) = \
                (self.normalize_name(row[0]), row[0], row[1], row[2], row[3], row[4], row[5] == 'Y', row[6])

            if coltype == 'NUMBER':
                coltype = NUMBER(precision, scale)
            elif coltype in ('VARCHAR2', 'NVARCHAR2', 'CHAR'):
                coltype = self.ischema_names.get(coltype)(length)
            elif 'WITH TIME ZONE' in coltype:
                coltype = TIMESTAMP(timezone=True)
            else:
                coltype = re.sub(r'\(\d+\)', '', coltype)
                try:
                    coltype = self.ischema_names[coltype]
                except KeyError:
                    util.warn("Did not recognize type '%s' of column '%s'" %
                              (coltype, colname))
                    coltype = sqltypes.NULLTYPE

            cdict = {
                'name': colname,
                'type': coltype,
                'nullable': nullable,
                'default': default,
                'autoincrement': default is None
            }
            if orig_colname.lower() == orig_colname:
                cdict['quote'] = True

            columns.append(cdict)
        return columns

    @reflection.cache
    def get_indexes(self, connection, table_name, schema=None,
                    resolve_synonyms=False, dblink='', **kw):

        info_cache = kw.get('info_cache')
        (table_name, schema, dblink, synonym) = \
            self._prepare_reflection_args(connection, table_name, schema,
                                          resolve_synonyms, dblink,
                                          info_cache=info_cache)
        indexes = []

        params = {'table_name': table_name}
        text = \
            "SELECT a.index_name, a.column_name, b.uniqueness "\
            "\nFROM ALL_IND_COLUMNS%(dblink)s a, "\
            "\nALL_INDEXES%(dblink)s b "\
            "\nWHERE "\
            "\na.index_name = b.index_name "\
            "\nAND a.table_owner = b.table_owner "\
            "\nAND a.table_name = b.table_name "\
            "\nAND a.table_name = :table_name "

        if schema is not None:
            params['schema'] = schema
            text += "AND a.table_owner = :schema "

        text += "ORDER BY a.index_name, a.column_position"

        text = text % {'dblink': dblink}

        q = sql.text(text)
        rp = connection.execute(q, **params)
        indexes = []
        last_index_name = None
        pk_constraint = self.get_pk_constraint(
            connection, table_name, schema, resolve_synonyms=resolve_synonyms,
            dblink=dblink, info_cache=kw.get('info_cache'))
        pkeys = pk_constraint['constrained_columns']
        uniqueness = dict(NONUNIQUE=False, UNIQUE=True)

        oracle_sys_col = re.compile(r'SYS_NC\d+\$', re.IGNORECASE)

        def upper_name_set(names):
            return set([i.upper() for i in names])

        pk_names = upper_name_set(pkeys)

        def remove_if_primary_key(index):
            # don't include the primary key index
            if index is not None and \
               upper_name_set(index['column_names']) == pk_names:
                indexes.pop()

        index = None
        for rset in rp:
            if rset.index_name != last_index_name:
                remove_if_primary_key(index)
                index = dict(name=self.normalize_name(rset.index_name), column_names=[])
                indexes.append(index)
            index['unique'] = uniqueness.get(rset.uniqueness, False)

            # filter out Oracle SYS_NC names.  could also do an outer join
            # to the all_tab_columns table and check for real col names there.
            if not oracle_sys_col.match(rset.column_name):
                index['column_names'].append(self.normalize_name(rset.column_name))
            last_index_name = rset.index_name
        remove_if_primary_key(index)
        return indexes

    @reflection.cache
    def _get_constraint_data(self, connection, table_name, schema=None,
                            dblink='', **kw):

        params = {'table_name': table_name}

        text = \
            "SELECT"\
            "\nac.constraint_name,"\
            "\nac.constraint_type,"\
            "\nloc.column_name AS local_column,"\
            "\nrem.table_name AS remote_table,"\
            "\nrem.column_name AS remote_column,"\
            "\nrem.owner AS remote_owner,"\
            "\nloc.position as loc_pos,"\
            "\nrem.position as rem_pos"\
            "\nFROM all_constraints%(dblink)s ac,"\
            "\nall_cons_columns%(dblink)s loc,"\
            "\nall_cons_columns%(dblink)s rem"\
            "\nWHERE ac.table_name = :table_name"\
            "\nAND ac.constraint_type IN ('R','P')"

        if schema is not None:
            params['owner'] = schema
            text += "\nAND ac.owner = :owner"

        text += \
            "\nAND ac.owner = loc.owner"\
            "\nAND ac.constraint_name = loc.constraint_name"\
            "\nAND ac.r_owner = rem.owner(+)"\
            "\nAND ac.r_constraint_name = rem.constraint_name(+)"\
            "\nAND (rem.position IS NULL or loc.position=rem.position)"\
            "\nORDER BY ac.constraint_name, loc.position"

        text = text % {'dblink': dblink}
        rp = connection.execute(sql.text(text), **params)
        constraint_data = rp.fetchall()
        return constraint_data

    @reflection.cache
    def get_pk_constraint(self, connection, table_name, schema=None, **kw):
        resolve_synonyms = kw.get('oracle_resolve_synonyms', False)
        dblink = kw.get('dblink', '')
        info_cache = kw.get('info_cache')

        (table_name, schema, dblink, synonym) = \
            self._prepare_reflection_args(connection, table_name, schema,
                                          resolve_synonyms, dblink,
                                          info_cache=info_cache)
        pkeys = []
        constraint_name = None
        constraint_data = self._get_constraint_data(connection, table_name,
                                        schema, dblink,
                                        info_cache=kw.get('info_cache'))

        for row in constraint_data:
            (cons_name, cons_type, local_column, remote_table, remote_column, remote_owner) = \
                row[0:2] + tuple([self.normalize_name(x) for x in row[2:6]])
            if cons_type == 'P':
                if constraint_name is None:
                    constraint_name = self.normalize_name(cons_name)
                pkeys.append(local_column)
        return {'constrained_columns': pkeys, 'name': constraint_name}

    @reflection.cache
    def get_foreign_keys(self, connection, table_name, schema=None, **kw):
        """

        kw arguments can be:

            oracle_resolve_synonyms

            dblink

        """

        requested_schema = schema  # to check later on
        resolve_synonyms = kw.get('oracle_resolve_synonyms', False)
        dblink = kw.get('dblink', '')
        info_cache = kw.get('info_cache')

        (table_name, schema, dblink, synonym) = \
            self._prepare_reflection_args(connection, table_name, schema,
                                          resolve_synonyms, dblink,
                                          info_cache=info_cache)

        constraint_data = self._get_constraint_data(connection, table_name,
                                                schema, dblink,
                                                info_cache=kw.get('info_cache'))

        def fkey_rec():
            return {
                'name': None,
                'constrained_columns': [],
                'referred_schema': None,
                'referred_table': None,
                'referred_columns': []
            }

        fkeys = util.defaultdict(fkey_rec)

        for row in constraint_data:
            (cons_name, cons_type, local_column, remote_table, remote_column, remote_owner) = \
                    row[0:2] + tuple([self.normalize_name(x) for x in row[2:6]])

            if cons_type == 'R':
                if remote_table is None:
                    # ticket 363
                    util.warn(
                        ("Got 'None' querying 'table_name' from "
                         "all_cons_columns%(dblink)s - does the user have "
                         "proper rights to the table?") % {'dblink': dblink})
                    continue

                rec = fkeys[cons_name]
                rec['name'] = cons_name
                local_cols, remote_cols = rec['constrained_columns'], rec['referred_columns']

                if not rec['referred_table']:
                    if resolve_synonyms:
                        ref_remote_name, ref_remote_owner, ref_dblink, ref_synonym = \
                                self._resolve_synonym(
                                    connection,
                                    desired_owner=self.denormalize_name(remote_owner),
                                    desired_table=self.denormalize_name(remote_table)
                                )
                        if ref_synonym:
                            remote_table = self.normalize_name(ref_synonym)
                            remote_owner = self.normalize_name(ref_remote_owner)

                    rec['referred_table'] = remote_table

                    if requested_schema is not None or self.denormalize_name(remote_owner) != schema:
                        rec['referred_schema'] = remote_owner

                local_cols.append(local_column)
                remote_cols.append(remote_column)

        return fkeys.values()

    @reflection.cache
    def get_view_definition(self, connection, view_name, schema=None,
                            resolve_synonyms=False, dblink='', **kw):
        info_cache = kw.get('info_cache')
        (view_name, schema, dblink, synonym) = \
            self._prepare_reflection_args(connection, view_name, schema,
                                          resolve_synonyms, dblink,
                                          info_cache=info_cache)

        params = {'view_name': view_name}
        text = "SELECT text FROM all_views WHERE view_name=:view_name"

        if schema is not None:
            text += " AND owner = :schema"
            params['schema'] = schema

        rp = connection.execute(sql.text(text), **params).scalar()
        if rp:
            return rp.decode(self.encoding)
        else:
            return None


class _OuterJoinColumn(sql.ClauseElement):
    __visit_name__ = 'outer_join_column'

    def __init__(self, column):
        self.column = column
