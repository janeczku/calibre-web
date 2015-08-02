# firebird/base.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""

.. dialect:: firebird
    :name: Firebird

Firebird Dialects
-----------------

Firebird offers two distinct dialects_ (not to be confused with a
SQLAlchemy ``Dialect``):

dialect 1
  This is the old syntax and behaviour, inherited from Interbase pre-6.0.

dialect 3
  This is the newer and supported syntax, introduced in Interbase 6.0.

The SQLAlchemy Firebird dialect detects these versions and
adjusts its representation of SQL accordingly.  However,
support for dialect 1 is not well tested and probably has
incompatibilities.

Locking Behavior
----------------

Firebird locks tables aggressively.  For this reason, a DROP TABLE may
hang until other transactions are released.  SQLAlchemy does its best
to release transactions as quickly as possible.  The most common cause
of hanging transactions is a non-fully consumed result set, i.e.::

    result = engine.execute("select * from table")
    row = result.fetchone()
    return

Where above, the ``ResultProxy`` has not been fully consumed.  The
connection will be returned to the pool and the transactional state
rolled back once the Python garbage collector reclaims the objects
which hold onto the connection, which often occurs asynchronously.
The above use case can be alleviated by calling ``first()`` on the
``ResultProxy`` which will fetch the first row and immediately close
all remaining cursor/connection resources.

RETURNING support
-----------------

Firebird 2.0 supports returning a result set from inserts, and 2.1
extends that to deletes and updates. This is generically exposed by
the SQLAlchemy ``returning()`` method, such as::

    # INSERT..RETURNING
    result = table.insert().returning(table.c.col1, table.c.col2).\\
                   values(name='foo')
    print result.fetchall()

    # UPDATE..RETURNING
    raises = empl.update().returning(empl.c.id, empl.c.salary).\\
                  where(empl.c.sales>100).\\
                  values(dict(salary=empl.c.salary * 1.1))
    print raises.fetchall()


.. _dialects: http://mc-computing.com/Databases/Firebird/SQL_Dialect.html

"""

import datetime

from sqlalchemy import schema as sa_schema
from sqlalchemy import exc, types as sqltypes, sql, util
from sqlalchemy.sql import expression
from sqlalchemy.engine import base, default, reflection
from sqlalchemy.sql import compiler


from sqlalchemy.types import (BIGINT, BLOB, DATE, FLOAT, INTEGER, NUMERIC,
                              SMALLINT, TEXT, TIME, TIMESTAMP, Integer)


RESERVED_WORDS = set([
    "active", "add", "admin", "after", "all", "alter", "and", "any", "as",
    "asc", "ascending", "at", "auto", "avg", "before", "begin", "between",
    "bigint", "bit_length", "blob", "both", "by", "case", "cast", "char",
    "character", "character_length", "char_length", "check", "close",
    "collate", "column", "commit", "committed", "computed", "conditional",
    "connect", "constraint", "containing", "count", "create", "cross",
    "cstring", "current", "current_connection", "current_date",
    "current_role", "current_time", "current_timestamp",
    "current_transaction", "current_user", "cursor", "database", "date",
    "day", "dec", "decimal", "declare", "default", "delete", "desc",
    "descending", "disconnect", "distinct", "do", "domain", "double",
    "drop", "else", "end", "entry_point", "escape", "exception",
    "execute", "exists", "exit", "external", "extract", "fetch", "file",
    "filter", "float", "for", "foreign", "from", "full", "function",
    "gdscode", "generator", "gen_id", "global", "grant", "group",
    "having", "hour", "if", "in", "inactive", "index", "inner",
    "input_type", "insensitive", "insert", "int", "integer", "into", "is",
    "isolation", "join", "key", "leading", "left", "length", "level",
    "like", "long", "lower", "manual", "max", "maximum_segment", "merge",
    "min", "minute", "module_name", "month", "names", "national",
    "natural", "nchar", "no", "not", "null", "numeric", "octet_length",
    "of", "on", "only", "open", "option", "or", "order", "outer",
    "output_type", "overflow", "page", "pages", "page_size", "parameter",
    "password", "plan", "position", "post_event", "precision", "primary",
    "privileges", "procedure", "protected", "rdb$db_key", "read", "real",
    "record_version", "recreate", "recursive", "references", "release",
    "reserv", "reserving", "retain", "returning_values", "returns",
    "revoke", "right", "rollback", "rows", "row_count", "savepoint",
    "schema", "second", "segment", "select", "sensitive", "set", "shadow",
    "shared", "singular", "size", "smallint", "snapshot", "some", "sort",
    "sqlcode", "stability", "start", "starting", "starts", "statistics",
    "sub_type", "sum", "suspend", "table", "then", "time", "timestamp",
    "to", "trailing", "transaction", "trigger", "trim", "uncommitted",
    "union", "unique", "update", "upper", "user", "using", "value",
    "values", "varchar", "variable", "varying", "view", "wait", "when",
    "where", "while", "with", "work", "write", "year",
    ])


class _StringType(sqltypes.String):
    """Base for Firebird string types."""

    def __init__(self, charset=None, **kw):
        self.charset = charset
        super(_StringType, self).__init__(**kw)


class VARCHAR(_StringType, sqltypes.VARCHAR):
    """Firebird VARCHAR type"""
    __visit_name__ = 'VARCHAR'

    def __init__(self, length=None, **kwargs):
        super(VARCHAR, self).__init__(length=length, **kwargs)


class CHAR(_StringType, sqltypes.CHAR):
    """Firebird CHAR type"""
    __visit_name__ = 'CHAR'

    def __init__(self, length=None, **kwargs):
        super(CHAR, self).__init__(length=length, **kwargs)


class _FBDateTime(sqltypes.DateTime):
    def bind_processor(self, dialect):
        def process(value):
            if type(value) == datetime.date:
                return datetime.datetime(value.year, value.month, value.day)
            else:
                return value
        return process

colspecs = {
    sqltypes.DateTime: _FBDateTime
}

ischema_names = {
      'SHORT': SMALLINT,
       'LONG': INTEGER,
       'QUAD': FLOAT,
      'FLOAT': FLOAT,
       'DATE': DATE,
       'TIME': TIME,
       'TEXT': TEXT,
      'INT64': BIGINT,
     'DOUBLE': FLOAT,
  'TIMESTAMP': TIMESTAMP,
    'VARYING': VARCHAR,
    'CSTRING': CHAR,
       'BLOB': BLOB,
    }


# TODO: date conversion types (should be implemented as _FBDateTime,
# _FBDate, etc. as bind/result functionality is required)

class FBTypeCompiler(compiler.GenericTypeCompiler):
    def visit_boolean(self, type_):
        return self.visit_SMALLINT(type_)

    def visit_datetime(self, type_):
        return self.visit_TIMESTAMP(type_)

    def visit_TEXT(self, type_):
        return "BLOB SUB_TYPE 1"

    def visit_BLOB(self, type_):
        return "BLOB SUB_TYPE 0"

    def _extend_string(self, type_, basic):
        charset = getattr(type_, 'charset',  None)
        if charset is None:
            return basic
        else:
            return '%s CHARACTER SET %s' % (basic, charset)

    def visit_CHAR(self, type_):
        basic = super(FBTypeCompiler, self).visit_CHAR(type_)
        return self._extend_string(type_, basic)

    def visit_VARCHAR(self, type_):
        if not type_.length:
            raise exc.CompileError(
                    "VARCHAR requires a length on dialect %s" %
                    self.dialect.name)
        basic = super(FBTypeCompiler, self).visit_VARCHAR(type_)
        return self._extend_string(type_, basic)


class FBCompiler(sql.compiler.SQLCompiler):
    """Firebird specific idiosyncrasies"""

    ansi_bind_rules = True

    #def visit_contains_op_binary(self, binary, operator, **kw):
        # cant use CONTAINING b.c. it's case insensitive.

    #def visit_notcontains_op_binary(self, binary, operator, **kw):
        # cant use NOT CONTAINING b.c. it's case insensitive.

    def visit_now_func(self, fn, **kw):
        return "CURRENT_TIMESTAMP"

    def visit_startswith_op_binary(self, binary, operator, **kw):
        return '%s STARTING WITH %s' % (
                            binary.left._compiler_dispatch(self, **kw),
                            binary.right._compiler_dispatch(self, **kw))

    def visit_notstartswith_op_binary(self, binary, operator, **kw):
        return '%s NOT STARTING WITH %s' % (
                            binary.left._compiler_dispatch(self, **kw),
                            binary.right._compiler_dispatch(self, **kw))

    def visit_mod_binary(self, binary, operator, **kw):
        return "mod(%s, %s)" % (
                                self.process(binary.left, **kw),
                                self.process(binary.right, **kw))

    def visit_alias(self, alias, asfrom=False, **kwargs):
        if self.dialect._version_two:
            return super(FBCompiler, self).\
                        visit_alias(alias, asfrom=asfrom, **kwargs)
        else:
            # Override to not use the AS keyword which FB 1.5 does not like
            if asfrom:
                alias_name = isinstance(alias.name,
                                expression._truncated_label) and \
                                self._truncated_identifier("alias",
                                alias.name) or alias.name

                return self.process(
                            alias.original, asfrom=asfrom, **kwargs) + \
                            " " + \
                            self.preparer.format_alias(alias, alias_name)
            else:
                return self.process(alias.original, **kwargs)

    def visit_substring_func(self, func, **kw):
        s = self.process(func.clauses.clauses[0])
        start = self.process(func.clauses.clauses[1])
        if len(func.clauses.clauses) > 2:
            length = self.process(func.clauses.clauses[2])
            return "SUBSTRING(%s FROM %s FOR %s)" % (s, start, length)
        else:
            return "SUBSTRING(%s FROM %s)" % (s, start)

    def visit_length_func(self, function, **kw):
        if self.dialect._version_two:
            return "char_length" + self.function_argspec(function)
        else:
            return "strlen" + self.function_argspec(function)

    visit_char_length_func = visit_length_func

    def function_argspec(self, func, **kw):
        # TODO: this probably will need to be
        # narrowed to a fixed list, some no-arg functions
        # may require parens - see similar example in the oracle
        # dialect
        if func.clauses is not None and len(func.clauses):
            return self.process(func.clause_expr, **kw)
        else:
            return ""

    def default_from(self):
        return " FROM rdb$database"

    def visit_sequence(self, seq):
        return "gen_id(%s, 1)" % self.preparer.format_sequence(seq)

    def get_select_precolumns(self, select):
        """Called when building a ``SELECT`` statement, position is just
        before column list Firebird puts the limit and offset right
        after the ``SELECT``...
        """

        result = ""
        if select._limit:
            result += "FIRST %s " % self.process(sql.literal(select._limit))
        if select._offset:
            result += "SKIP %s " % self.process(sql.literal(select._offset))
        if select._distinct:
            result += "DISTINCT "
        return result

    def limit_clause(self, select):
        """Already taken care of in the `get_select_precolumns` method."""

        return ""

    def returning_clause(self, stmt, returning_cols):
        columns = [
                self._label_select_column(None, c, True, False, {})
                for c in expression._select_iterables(returning_cols)
            ]

        return 'RETURNING ' + ', '.join(columns)


class FBDDLCompiler(sql.compiler.DDLCompiler):
    """Firebird syntactic idiosyncrasies"""

    def visit_create_sequence(self, create):
        """Generate a ``CREATE GENERATOR`` statement for the sequence."""

        # no syntax for these
        # http://www.firebirdsql.org/manual/generatorguide-sqlsyntax.html
        if create.element.start is not None:
            raise NotImplemented(
                        "Firebird SEQUENCE doesn't support START WITH")
        if create.element.increment is not None:
            raise NotImplemented(
                        "Firebird SEQUENCE doesn't support INCREMENT BY")

        if self.dialect._version_two:
            return "CREATE SEQUENCE %s" % \
                        self.preparer.format_sequence(create.element)
        else:
            return "CREATE GENERATOR %s" % \
                        self.preparer.format_sequence(create.element)

    def visit_drop_sequence(self, drop):
        """Generate a ``DROP GENERATOR`` statement for the sequence."""

        if self.dialect._version_two:
            return "DROP SEQUENCE %s" % \
                        self.preparer.format_sequence(drop.element)
        else:
            return "DROP GENERATOR %s" % \
                        self.preparer.format_sequence(drop.element)


class FBIdentifierPreparer(sql.compiler.IdentifierPreparer):
    """Install Firebird specific reserved words."""

    reserved_words = RESERVED_WORDS

    def __init__(self, dialect):
        super(FBIdentifierPreparer, self).__init__(dialect, omit_schema=True)


class FBExecutionContext(default.DefaultExecutionContext):
    def fire_sequence(self, seq, type_):
        """Get the next value from the sequence using ``gen_id()``."""

        return self._execute_scalar(
                "SELECT gen_id(%s, 1) FROM rdb$database" %
                self.dialect.identifier_preparer.format_sequence(seq),
                type_
                )


class FBDialect(default.DefaultDialect):
    """Firebird dialect"""

    name = 'firebird'

    max_identifier_length = 31

    supports_sequences = True
    sequences_optional = False
    supports_default_values = True
    postfetch_lastrowid = False

    supports_native_boolean = False

    requires_name_normalize = True
    supports_empty_insert = False

    statement_compiler = FBCompiler
    ddl_compiler = FBDDLCompiler
    preparer = FBIdentifierPreparer
    type_compiler = FBTypeCompiler
    execution_ctx_cls = FBExecutionContext

    colspecs = colspecs
    ischema_names = ischema_names

    # defaults to dialect ver. 3,
    # will be autodetected off upon
    # first connect
    _version_two = True

    def initialize(self, connection):
        super(FBDialect, self).initialize(connection)
        self._version_two = ('firebird' in self.server_version_info and \
                                self.server_version_info >= (2, )
                            ) or \
                            ('interbase' in self.server_version_info and \
                                self.server_version_info >= (6, )
                            )

        if not self._version_two:
            # TODO: whatever other pre < 2.0 stuff goes here
            self.ischema_names = ischema_names.copy()
            self.ischema_names['TIMESTAMP'] = sqltypes.DATE
            self.colspecs = {
                sqltypes.DateTime: sqltypes.DATE
            }

        self.implicit_returning = self._version_two  and \
                            self.__dict__.get('implicit_returning', True)

    def normalize_name(self, name):
        # Remove trailing spaces: FB uses a CHAR() type,
        # that is padded with spaces
        name = name and name.rstrip()
        if name is None:
            return None
        elif name.upper() == name and \
            not self.identifier_preparer._requires_quotes(name.lower()):
            return name.lower()
        else:
            return name

    def denormalize_name(self, name):
        if name is None:
            return None
        elif name.lower() == name and \
            not self.identifier_preparer._requires_quotes(name.lower()):
            return name.upper()
        else:
            return name

    def has_table(self, connection, table_name, schema=None):
        """Return ``True`` if the given table exists, ignoring
        the `schema`."""

        tblqry = """
        SELECT 1 AS has_table FROM rdb$database
        WHERE EXISTS (SELECT rdb$relation_name
                      FROM rdb$relations
                      WHERE rdb$relation_name=?)
        """
        c = connection.execute(tblqry, [self.denormalize_name(table_name)])
        return c.first() is not None

    def has_sequence(self, connection, sequence_name, schema=None):
        """Return ``True`` if the given sequence (generator) exists."""

        genqry = """
        SELECT 1 AS has_sequence FROM rdb$database
        WHERE EXISTS (SELECT rdb$generator_name
                      FROM rdb$generators
                      WHERE rdb$generator_name=?)
        """
        c = connection.execute(genqry, [self.denormalize_name(sequence_name)])
        return c.first() is not None

    @reflection.cache
    def get_table_names(self, connection, schema=None, **kw):
        s = """
        SELECT DISTINCT rdb$relation_name
        FROM rdb$relation_fields
        WHERE rdb$system_flag=0 AND rdb$view_context IS NULL
        """
        return [self.normalize_name(row[0]) for row in connection.execute(s)]

    @reflection.cache
    def get_view_names(self, connection, schema=None, **kw):
        s = """
        SELECT distinct rdb$view_name
        FROM rdb$view_relations
        """
        return [self.normalize_name(row[0]) for row in connection.execute(s)]

    @reflection.cache
    def get_view_definition(self, connection, view_name, schema=None, **kw):
        qry = """
        SELECT rdb$view_source AS view_source
        FROM rdb$relations
        WHERE rdb$relation_name=?
        """
        rp = connection.execute(qry, [self.denormalize_name(view_name)])
        row = rp.first()
        if row:
            return row['view_source']
        else:
            return None

    @reflection.cache
    def get_pk_constraint(self, connection, table_name, schema=None, **kw):
        # Query to extract the PK/FK constrained fields of the given table
        keyqry = """
        SELECT se.rdb$field_name AS fname
        FROM rdb$relation_constraints rc
             JOIN rdb$index_segments se ON rc.rdb$index_name=se.rdb$index_name
        WHERE rc.rdb$constraint_type=? AND rc.rdb$relation_name=?
        """
        tablename = self.denormalize_name(table_name)
        # get primary key fields
        c = connection.execute(keyqry, ["PRIMARY KEY", tablename])
        pkfields = [self.normalize_name(r['fname']) for r in c.fetchall()]
        return {'constrained_columns': pkfields, 'name': None}

    @reflection.cache
    def get_column_sequence(self, connection,
                                table_name, column_name,
                                schema=None, **kw):
        tablename = self.denormalize_name(table_name)
        colname = self.denormalize_name(column_name)
        # Heuristic-query to determine the generator associated to a PK field
        genqry = """
        SELECT trigdep.rdb$depended_on_name AS fgenerator
        FROM rdb$dependencies tabdep
             JOIN rdb$dependencies trigdep
                  ON tabdep.rdb$dependent_name=trigdep.rdb$dependent_name
                     AND trigdep.rdb$depended_on_type=14
                     AND trigdep.rdb$dependent_type=2
             JOIN rdb$triggers trig ON
                    trig.rdb$trigger_name=tabdep.rdb$dependent_name
        WHERE tabdep.rdb$depended_on_name=?
          AND tabdep.rdb$depended_on_type=0
          AND trig.rdb$trigger_type=1
          AND tabdep.rdb$field_name=?
          AND (SELECT count(*)
           FROM rdb$dependencies trigdep2
           WHERE trigdep2.rdb$dependent_name = trigdep.rdb$dependent_name) = 2
        """
        genr = connection.execute(genqry, [tablename, colname]).first()
        if genr is not None:
            return dict(name=self.normalize_name(genr['fgenerator']))

    @reflection.cache
    def get_columns(self, connection, table_name, schema=None, **kw):
        # Query to extract the details of all the fields of the given table
        tblqry = """
        SELECT r.rdb$field_name AS fname,
                        r.rdb$null_flag AS null_flag,
                        t.rdb$type_name AS ftype,
                        f.rdb$field_sub_type AS stype,
                        f.rdb$field_length/
                            COALESCE(cs.rdb$bytes_per_character,1) AS flen,
                        f.rdb$field_precision AS fprec,
                        f.rdb$field_scale AS fscale,
                        COALESCE(r.rdb$default_source,
                                f.rdb$default_source) AS fdefault
        FROM rdb$relation_fields r
             JOIN rdb$fields f ON r.rdb$field_source=f.rdb$field_name
             JOIN rdb$types t
              ON t.rdb$type=f.rdb$field_type AND
                    t.rdb$field_name='RDB$FIELD_TYPE'
             LEFT JOIN rdb$character_sets cs ON
                    f.rdb$character_set_id=cs.rdb$character_set_id
        WHERE f.rdb$system_flag=0 AND r.rdb$relation_name=?
        ORDER BY r.rdb$field_position
        """
        # get the PK, used to determine the eventual associated sequence
        pk_constraint = self.get_pk_constraint(connection, table_name)
        pkey_cols = pk_constraint['constrained_columns']

        tablename = self.denormalize_name(table_name)
        # get all of the fields for this table
        c = connection.execute(tblqry, [tablename])
        cols = []
        while True:
            row = c.fetchone()
            if row is None:
                break
            name = self.normalize_name(row['fname'])
            orig_colname = row['fname']

            # get the data type
            colspec = row['ftype'].rstrip()
            coltype = self.ischema_names.get(colspec)
            if coltype is None:
                util.warn("Did not recognize type '%s' of column '%s'" %
                          (colspec, name))
                coltype = sqltypes.NULLTYPE
            elif issubclass(coltype, Integer) and row['fprec'] != 0:
                coltype = NUMERIC(
                                precision=row['fprec'],
                                scale=row['fscale'] * -1)
            elif colspec in ('VARYING', 'CSTRING'):
                coltype = coltype(row['flen'])
            elif colspec == 'TEXT':
                coltype = TEXT(row['flen'])
            elif colspec == 'BLOB':
                if row['stype'] == 1:
                    coltype = TEXT()
                else:
                    coltype = BLOB()
            else:
                coltype = coltype()

            # does it have a default value?
            defvalue = None
            if row['fdefault'] is not None:
                # the value comes down as "DEFAULT 'value'": there may be
                # more than one whitespace around the "DEFAULT" keyword
                # and it may also be lower case
                # (see also http://tracker.firebirdsql.org/browse/CORE-356)
                defexpr = row['fdefault'].lstrip()
                assert defexpr[:8].rstrip().upper() == \
                            'DEFAULT', "Unrecognized default value: %s" % \
                            defexpr
                defvalue = defexpr[8:].strip()
                if defvalue == 'NULL':
                    # Redundant
                    defvalue = None
            col_d = {
                'name': name,
                'type': coltype,
                'nullable': not bool(row['null_flag']),
                'default': defvalue,
                'autoincrement': defvalue is None
            }

            if orig_colname.lower() == orig_colname:
                col_d['quote'] = True

            # if the PK is a single field, try to see if its linked to
            # a sequence thru a trigger
            if len(pkey_cols) == 1 and name == pkey_cols[0]:
                seq_d = self.get_column_sequence(connection, tablename, name)
                if seq_d is not None:
                    col_d['sequence'] = seq_d

            cols.append(col_d)
        return cols

    @reflection.cache
    def get_foreign_keys(self, connection, table_name, schema=None, **kw):
        # Query to extract the details of each UK/FK of the given table
        fkqry = """
        SELECT rc.rdb$constraint_name AS cname,
               cse.rdb$field_name AS fname,
               ix2.rdb$relation_name AS targetrname,
               se.rdb$field_name AS targetfname
        FROM rdb$relation_constraints rc
             JOIN rdb$indices ix1 ON ix1.rdb$index_name=rc.rdb$index_name
             JOIN rdb$indices ix2 ON ix2.rdb$index_name=ix1.rdb$foreign_key
             JOIN rdb$index_segments cse ON
                        cse.rdb$index_name=ix1.rdb$index_name
             JOIN rdb$index_segments se
                  ON se.rdb$index_name=ix2.rdb$index_name
                     AND se.rdb$field_position=cse.rdb$field_position
        WHERE rc.rdb$constraint_type=? AND rc.rdb$relation_name=?
        ORDER BY se.rdb$index_name, se.rdb$field_position
        """
        tablename = self.denormalize_name(table_name)

        c = connection.execute(fkqry, ["FOREIGN KEY", tablename])
        fks = util.defaultdict(lambda: {
            'name': None,
            'constrained_columns': [],
            'referred_schema': None,
            'referred_table': None,
            'referred_columns': []
        })

        for row in c:
            cname = self.normalize_name(row['cname'])
            fk = fks[cname]
            if not fk['name']:
                fk['name'] = cname
                fk['referred_table'] = self.normalize_name(row['targetrname'])
            fk['constrained_columns'].append(
                                self.normalize_name(row['fname']))
            fk['referred_columns'].append(
                                self.normalize_name(row['targetfname']))
        return fks.values()

    @reflection.cache
    def get_indexes(self, connection, table_name, schema=None, **kw):
        qry = """
        SELECT ix.rdb$index_name AS index_name,
               ix.rdb$unique_flag AS unique_flag,
               ic.rdb$field_name AS field_name
        FROM rdb$indices ix
             JOIN rdb$index_segments ic
                  ON ix.rdb$index_name=ic.rdb$index_name
             LEFT OUTER JOIN rdb$relation_constraints
                  ON rdb$relation_constraints.rdb$index_name =
                        ic.rdb$index_name
        WHERE ix.rdb$relation_name=? AND ix.rdb$foreign_key IS NULL
          AND rdb$relation_constraints.rdb$constraint_type IS NULL
        ORDER BY index_name, field_name
        """
        c = connection.execute(qry, [self.denormalize_name(table_name)])

        indexes = util.defaultdict(dict)
        for row in c:
            indexrec = indexes[row['index_name']]
            if 'name' not in indexrec:
                indexrec['name'] = self.normalize_name(row['index_name'])
                indexrec['column_names'] = []
                indexrec['unique'] = bool(row['unique_flag'])

            indexrec['column_names'].append(
                                self.normalize_name(row['field_name']))

        return indexes.values()

