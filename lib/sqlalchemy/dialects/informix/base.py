# informix/base.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
# coding: gbk
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""
.. dialect:: informix
    :name: Informix

.. note::

    The Informix dialect functions on current SQLAlchemy versions
    but is not regularly tested, and may have many issues and
    caveats not currently handled.

"""


import datetime

from sqlalchemy import sql, schema, exc, pool, util
from sqlalchemy.sql import compiler, text
from sqlalchemy.engine import default, reflection
from sqlalchemy import types as sqltypes

RESERVED_WORDS = set(
    ["abs", "absolute", "access", "access_method", "acos", "active", "add",
    "address", "add_months", "admin", "after", "aggregate", "alignment",
    "all", "allocate", "all_rows", "alter", "and", "ansi", "any", "append",
    "array", "as", "asc", "ascii", "asin", "at", "atan", "atan2", "attach",
    "attributes", "audit", "authentication", "authid", "authorization",
    "authorized", "auto", "autofree", "auto_reprepare", "auto_stat_mode",
    "avg", "avoid_execute", "avoid_fact", "avoid_full", "avoid_hash",
    "avoid_index", "avoid_index_sj", "avoid_multi_index", "avoid_nl",
    "avoid_star_join", "avoid_subqf", "based", "before", "begin",
    "between", "bigint", "bigserial", "binary", "bitand", "bitandnot",
    "bitnot", "bitor", "bitxor", "blob", "blobdir", "boolean", "both",
    "bound_impl_pdq", "buffered", "builtin", "by", "byte", "cache", "call",
    "cannothash", "cardinality", "cascade", "case", "cast", "ceil", "char",
    "character", "character_length", "char_length", "check", "class",
    "class_origin", "client", "clob", "clobdir", "close", "cluster",
    "clustersize", "cobol", "codeset", "collation", "collection",
    "column", "columns", "commit", "committed", "commutator", "component",
    "components", "concat", "concurrent", "connect", "connection",
    "connection_name", "connect_by_iscycle", "connect_by_isleaf",
    "connect_by_rootconst", "constraint", "constraints", "constructor",
    "context", "continue", "copy", "cos", "costfunc", "count", "crcols",
    "create", "cross", "current", "current_role", "currval", "cursor",
    "cycle", "database", "datafiles", "dataskip", "date", "datetime",
    "day", "dba", "dbdate", "dbinfo", "dbpassword", "dbsecadm",
    "dbservername", "deallocate", "debug", "debugmode", "debug_env", "dec",
    "decimal", "declare", "decode", "decrypt_binary", "decrypt_char",
    "dec_t", "default", "default_role", "deferred", "deferred_prepare",
    "define", "delay", "delete", "deleting", "delimited", "delimiter",
    "deluxe", "desc", "describe", "descriptor", "detach", "diagnostics",
    "directives", "dirty", "disable", "disabled", "disconnect", "disk",
    "distinct", "distributebinary", "distributesreferences",
    "distributions", "document", "domain", "donotdistribute", "dormant",
    "double", "drop", "dtime_t", "each", "elif", "else", "enabled",
    "encryption", "encrypt_aes", "encrypt_tdes", "end", "enum",
    "environment", "error", "escape", "exception", "exclusive", "exec",
    "execute", "executeanywhere", "exemption", "exists", "exit", "exp",
    "explain", "explicit", "express", "expression", "extdirectives",
    "extend", "extent", "external", "fact", "false", "far", "fetch",
    "file", "filetoblob", "filetoclob", "fillfactor", "filtering", "first",
    "first_rows", "fixchar", "fixed", "float", "floor", "flush", "for",
    "force", "forced", "force_ddl_exec", "foreach", "foreign", "format",
    "format_units", "fortran", "found", "fraction", "fragment",
    "fragments", "free", "from", "full", "function", "general", "get",
    "gethint", "global", "go", "goto", "grant", "greaterthan",
    "greaterthanorequal", "group", "handlesnulls", "hash", "having", "hdr",
    "hex", "high", "hint", "hold", "home", "hour", "idslbacreadarray",
    "idslbacreadset", "idslbacreadtree", "idslbacrules",
    "idslbacwritearray", "idslbacwriteset", "idslbacwritetree",
    "idssecuritylabel", "if", "ifx_auto_reprepare", "ifx_batchedread_table",
    "ifx_int8_t", "ifx_lo_create_spec_t", "ifx_lo_stat_t", "immediate",
    "implicit", "implicit_pdq", "in", "inactive", "increment", "index",
    "indexes", "index_all", "index_sj", "indicator", "informix", "init",
    "initcap", "inline", "inner", "inout", "insert", "inserting", "instead",
    "int", "int8", "integ", "integer", "internal", "internallength",
    "interval", "into", "intrvl_t", "is", "iscanonical", "isolation",
    "item", "iterator", "java", "join", "keep", "key", "label", "labeleq",
    "labelge", "labelglb", "labelgt", "labelle", "labellt", "labellub",
    "labeltostring", "language", "last", "last_day", "leading", "left",
    "length", "lessthan", "lessthanorequal", "let", "level", "like",
    "limit", "list", "listing", "load", "local", "locator", "lock", "locks",
    "locopy", "loc_t", "log", "log10", "logn", "long", "loop", "lotofile",
    "low", "lower", "lpad", "ltrim", "lvarchar", "matched", "matches",
    "max", "maxerrors", "maxlen", "maxvalue", "mdy", "median", "medium",
    "memory", "memory_resident", "merge", "message_length", "message_text",
    "middle", "min", "minute", "minvalue", "mod", "mode", "moderate",
    "modify", "module", "money", "month", "months_between", "mounting",
    "multiset", "multi_index", "name", "nchar", "negator", "new", "next",
    "nextval", "next_day", "no", "nocache", "nocycle", "nomaxvalue",
    "nomigrate", "nominvalue", "none", "non_dim", "non_resident", "noorder",
    "normal", "not", "notemplatearg", "notequal", "null", "nullif",
    "numeric", "numrows", "numtodsinterval", "numtoyminterval", "nvarchar",
    "nvl", "octet_length", "of", "off", "old", "on", "online", "only",
    "opaque", "opclass", "open", "optcompind", "optical", "optimization",
    "option", "or", "order", "ordered", "out", "outer", "output",
    "override", "page", "parallelizable", "parameter", "partition",
    "pascal", "passedbyvalue", "password", "pdqpriority", "percaltl_cos",
    "pipe", "pli", "pload", "policy", "pow", "power", "precision",
    "prepare", "previous", "primary", "prior", "private", "privileges",
    "procedure", "properties", "public", "put", "raise", "range", "raw",
    "read", "real", "recordend", "references", "referencing", "register",
    "rejectfile", "relative", "release", "remainder", "rename",
    "reoptimization", "repeatable", "replace", "replication", "reserve",
    "resolution", "resource", "restart", "restrict", "resume", "retain",
    "retainupdatelocks", "return", "returned_sqlstate", "returning",
    "returns", "reuse", "revoke", "right", "robin", "role", "rollback",
    "rollforward", "root", "round", "routine", "row", "rowid", "rowids",
    "rows", "row_count", "rpad", "rtrim", "rule", "sameas", "samples",
    "sampling", "save", "savepoint", "schema", "scroll", "seclabel_by_comp",
    "seclabel_by_name", "seclabel_to_char", "second", "secondary",
    "section", "secured", "security", "selconst", "select", "selecting",
    "selfunc", "selfuncargs", "sequence", "serial", "serial8",
    "serializable", "serveruuid", "server_name", "session", "set",
    "setsessionauth", "share", "short", "siblings", "signed", "sin",
    "sitename", "size", "skall", "skinhibit", "skip", "skshow",
    "smallfloat", "smallint", "some", "specific", "sql", "sqlcode",
    "sqlcontext", "sqlerror", "sqlstate", "sqlwarning", "sqrt",
    "stability", "stack", "standard", "start", "star_join", "statchange",
    "statement", "static", "statistics", "statlevel", "status", "stdev",
    "step", "stop", "storage", "store", "strategies", "string",
    "stringtolabel", "struct", "style", "subclass_origin", "substr",
    "substring", "sum", "support", "sync", "synonym", "sysdate",
    "sysdbclose", "sysdbopen", "system", "sys_connect_by_path", "table",
    "tables", "tan", "task", "temp", "template", "test", "text", "then",
    "time", "timeout", "to", "today", "to_char", "to_date",
    "to_dsinterval", "to_number", "to_yminterval", "trace", "trailing",
    "transaction", "transition", "tree", "trigger", "triggers", "trim",
    "true", "trunc", "truncate", "trusted", "type", "typedef", "typeid",
    "typename", "typeof", "uid", "uncommitted", "under", "union",
    "unique", "units", "unknown", "unload", "unlock", "unsigned",
    "update", "updating", "upon", "upper", "usage", "use",
    "uselastcommitted", "user", "use_hash", "use_nl", "use_subqf",
    "using", "value", "values", "var", "varchar", "variable", "variance",
    "variant", "varying", "vercols", "view", "violations", "void",
    "volatile", "wait", "warning", "weekday", "when", "whenever", "where",
    "while", "with", "without", "work", "write", "writedown", "writeup",
    "xadatasource", "xid", "xload", "xunload", "year"
    ])


class InfoDateTime(sqltypes.DateTime):

    def bind_processor(self, dialect):
        def process(value):
            if value is not None:
                if value.microsecond:
                    value = value.replace(microsecond=0)
            return value
        return process


class InfoTime(sqltypes.Time):

    def bind_processor(self, dialect):
        def process(value):
            if value is not None:
                if value.microsecond:
                    value = value.replace(microsecond=0)
            return value
        return process

    def result_processor(self, dialect, coltype):
        def process(value):
            if isinstance(value, datetime.datetime):
                return value.time()
            else:
                return value
        return process

colspecs = {
    sqltypes.DateTime: InfoDateTime,
    sqltypes.TIMESTAMP: InfoDateTime,
    sqltypes.Time: InfoTime,
}


ischema_names = {
    0: sqltypes.CHAR,           # CHAR
    1: sqltypes.SMALLINT,       # SMALLINT
    2: sqltypes.INTEGER,        # INT
    3: sqltypes.FLOAT,          # Float
    3: sqltypes.Float,          # SmallFloat
    5: sqltypes.DECIMAL,        # DECIMAL
    6: sqltypes.Integer,        # Serial
    7: sqltypes.DATE,           # DATE
    8: sqltypes.Numeric,        # MONEY
    10: sqltypes.DATETIME,      # DATETIME
    11: sqltypes.LargeBinary,   # BYTE
    12: sqltypes.TEXT,          # TEXT
    13: sqltypes.VARCHAR,       # VARCHAR
    15: sqltypes.NCHAR,         # NCHAR
    16: sqltypes.NVARCHAR,      # NVARCHAR
    17: sqltypes.Integer,       # INT8
    18: sqltypes.Integer,       # Serial8
    43: sqltypes.String,        # LVARCHAR
    -1: sqltypes.BLOB,          # BLOB
    -1: sqltypes.CLOB,          # CLOB
}


class InfoTypeCompiler(compiler.GenericTypeCompiler):
    def visit_DATETIME(self, type_):
        return "DATETIME YEAR TO SECOND"

    def visit_TIME(self, type_):
        return "DATETIME HOUR TO SECOND"

    def visit_TIMESTAMP(self, type_):
        return "DATETIME YEAR TO SECOND"

    def visit_large_binary(self, type_):
        return "BYTE"

    def visit_boolean(self, type_):
        return "SMALLINT"


class InfoSQLCompiler(compiler.SQLCompiler):

    def default_from(self):
        return " from systables where tabname = 'systables' "

    def get_select_precolumns(self, select):
        s = ""
        if select._offset:
            s += "SKIP %s " % select._offset
        if select._limit:
            s += "FIRST %s " % select._limit
        s += select._distinct and "DISTINCT " or ""
        return s

    def visit_select(self, select, asfrom=False, parens=True, **kw):
        text = compiler.SQLCompiler.visit_select(self, select, asfrom, parens, **kw)
        if asfrom and parens and self.dialect.server_version_info < (11,):
            #assuming that 11 version doesn't need this, not tested
            return "table(multiset" + text + ")"
        else:
            return text

    def limit_clause(self, select):
        return ""

    def visit_function(self, func, **kw):
        if func.name.lower() == 'current_date':
            return "today"
        elif func.name.lower() == 'current_time':
            return "CURRENT HOUR TO SECOND"
        elif func.name.lower() in ('current_timestamp', 'now'):
            return "CURRENT YEAR TO SECOND"
        else:
            return compiler.SQLCompiler.visit_function(self, func, **kw)

    def visit_mod_binary(self, binary, operator, **kw):
        return "MOD(%s, %s)" % (self.process(binary.left, **kw),
                                self.process(binary.right, **kw))


class InfoDDLCompiler(compiler.DDLCompiler):

    def visit_add_constraint(self, create):
        preparer = self.preparer
        return "ALTER TABLE %s ADD CONSTRAINT %s" % (
            self.preparer.format_table(create.element.table),
            self.process(create.element)
        )

    def get_column_specification(self, column, **kw):
        colspec = self.preparer.format_column(column)
        first = None
        if column.primary_key and column.autoincrement:
            try:
                first = [c for c in column.table.primary_key.columns
                         if (c.autoincrement and
                             isinstance(c.type, sqltypes.Integer) and
                             not c.foreign_keys)].pop(0)
            except IndexError:
                pass

        if column is first:
            colspec += " SERIAL"
        else:
            colspec += " " + self.dialect.type_compiler.process(column.type)
            default = self.get_column_default_string(column)
            if default is not None:
                colspec += " DEFAULT " + default

        if not column.nullable:
            colspec += " NOT NULL"

        return colspec

    def get_column_default_string(self, column):
        if (isinstance(column.server_default, schema.DefaultClause) and
            isinstance(column.server_default.arg, basestring)):
                if isinstance(column.type, (sqltypes.Integer, sqltypes.Numeric)):
                    return self.sql_compiler.process(text(column.server_default.arg))

        return super(InfoDDLCompiler, self).get_column_default_string(column)

    ### Informix wants the constraint name at the end, hence this ist c&p from sql/compiler.py
    def visit_primary_key_constraint(self, constraint):
        if len(constraint) == 0:
            return ''
        text = "PRIMARY KEY "
        text += "(%s)" % ', '.join(self.preparer.quote(c.name, c.quote)
                                       for c in constraint)
        text += self.define_constraint_deferrability(constraint)

        if constraint.name is not None:
            text += " CONSTRAINT %s" % self.preparer.format_constraint(constraint)
        return text

    def visit_foreign_key_constraint(self, constraint):
        preparer = self.dialect.identifier_preparer
        remote_table = list(constraint._elements.values())[0].column.table
        text = "FOREIGN KEY (%s) REFERENCES %s (%s)" % (
            ', '.join(preparer.quote(f.parent.name, f.parent.quote)
                      for f in constraint._elements.values()),
            preparer.format_table(remote_table),
            ', '.join(preparer.quote(f.column.name, f.column.quote)
                      for f in constraint._elements.values())
        )
        text += self.define_constraint_cascades(constraint)
        text += self.define_constraint_deferrability(constraint)

        if constraint.name is not None:
            text += " CONSTRAINT %s " % \
                        preparer.format_constraint(constraint)
        return text

    def visit_unique_constraint(self, constraint):
        text = "UNIQUE (%s)" % (', '.join(self.preparer.quote(c.name, c.quote) for c in constraint))
        text += self.define_constraint_deferrability(constraint)

        if constraint.name is not None:
            text += "CONSTRAINT %s " % self.preparer.format_constraint(constraint)
        return text


class InformixIdentifierPreparer(compiler.IdentifierPreparer):

    reserved_words = RESERVED_WORDS


class InformixDialect(default.DefaultDialect):
    name = 'informix'

    max_identifier_length = 128  # adjusts at runtime based on server version

    type_compiler = InfoTypeCompiler
    statement_compiler = InfoSQLCompiler
    ddl_compiler = InfoDDLCompiler
    colspecs = colspecs
    ischema_names = ischema_names
    preparer = InformixIdentifierPreparer
    default_paramstyle = 'qmark'

    def initialize(self, connection):
        super(InformixDialect, self).initialize(connection)

        # http://www.querix.com/support/knowledge-base/error_number_message/error_200
        if self.server_version_info < (9, 2):
            self.max_identifier_length = 18
        else:
            self.max_identifier_length = 128

    def _get_table_names(self, connection, schema, type, **kw):
        schema = schema or self.default_schema_name
        s = "select tabname, owner from systables where owner=? and tabtype=?"
        return [row[0] for row in connection.execute(s, schema, type)]

    @reflection.cache
    def get_table_names(self, connection, schema=None, **kw):
        return self._get_table_names(connection, schema, 'T', **kw)

    @reflection.cache
    def get_view_names(self, connection, schema=None, **kw):
        return self._get_table_names(connection, schema, 'V', **kw)

    @reflection.cache
    def get_schema_names(self, connection, **kw):
        s = "select owner from systables"
        return [row[0] for row in connection.execute(s)]

    def has_table(self, connection, table_name, schema=None):
        schema = schema or self.default_schema_name
        cursor = connection.execute(
                """select tabname from systables where tabname=? and owner=?""",
                table_name, schema)
        return cursor.first() is not None

    @reflection.cache
    def get_columns(self, connection, table_name, schema=None, **kw):
        schema = schema or self.default_schema_name
        c = connection.execute(
            """select colname, coltype, collength, t3.default, t1.colno from
                syscolumns as t1 , systables as t2 , OUTER sysdefaults as t3
                where t1.tabid = t2.tabid and t2.tabname=? and t2.owner=?
                  and t3.tabid = t2.tabid and t3.colno = t1.colno
                order by t1.colno""", table_name, schema)

        pk_constraint = self.get_pk_constraint(connection, table_name, schema, **kw)
        primary_cols = pk_constraint['constrained_columns']

        columns = []
        rows = c.fetchall()
        for name, colattr, collength, default, colno in rows:
            name = name.lower()

            autoincrement = False
            primary_key = False

            if name in primary_cols:
                primary_key = True

            # in 7.31, coltype = 0x000
            #                       ^^-- column type
            #                      ^-- 1 not null, 0 null
            not_nullable, coltype = divmod(colattr, 256)
            if coltype not in (0, 13) and default:
                default = default.split()[-1]

            if coltype == 6:  # Serial, mark as autoincrement
                autoincrement = True

            if coltype == 0 or coltype == 13:  # char, varchar
                coltype = ischema_names[coltype](collength)
                if default:
                    default = "'%s'" % default
            elif coltype == 5:  # decimal
                precision, scale = (collength & 0xFF00) >> 8, collength & 0xFF
                if scale == 255:
                    scale = 0
                coltype = sqltypes.Numeric(precision, scale)
            else:
                try:
                    coltype = ischema_names[coltype]
                except KeyError:
                    util.warn("Did not recognize type '%s' of column '%s'" %
                              (coltype, name))
                    coltype = sqltypes.NULLTYPE

            column_info = dict(name=name, type=coltype, nullable=not not_nullable,
                               default=default, autoincrement=autoincrement,
                               primary_key=primary_key)
            columns.append(column_info)
        return columns

    @reflection.cache
    def get_foreign_keys(self, connection, table_name, schema=None, **kw):
        schema_sel = schema or self.default_schema_name
        c = connection.execute(
        """select t1.constrname as cons_name,
                 t4.colname as local_column, t7.tabname as remote_table,
                 t6.colname as remote_column, t7.owner as remote_owner
            from sysconstraints as t1 , systables as t2 ,
                 sysindexes as t3 , syscolumns as t4 ,
                 sysreferences as t5 , syscolumns as t6 , systables as t7 ,
                 sysconstraints as t8 , sysindexes as t9
           where t1.tabid = t2.tabid and t2.tabname=? and t2.owner=? and t1.constrtype = 'R'
             and t3.tabid = t2.tabid and t3.idxname = t1.idxname
             and t4.tabid = t2.tabid and t4.colno in (t3.part1, t3.part2, t3.part3,
             t3.part4, t3.part5, t3.part6, t3.part7, t3.part8, t3.part9, t3.part10,
             t3.part11, t3.part11, t3.part12, t3.part13, t3.part4, t3.part15, t3.part16)
             and t5.constrid = t1.constrid and t8.constrid = t5.primary
             and t6.tabid = t5.ptabid and t6.colno in (t9.part1, t9.part2, t9.part3,
             t9.part4, t9.part5, t9.part6, t9.part7, t9.part8, t9.part9, t9.part10,
             t9.part11, t9.part11, t9.part12, t9.part13, t9.part4, t9.part15, t9.part16) and t9.idxname =
             t8.idxname
             and t7.tabid = t5.ptabid""", table_name, schema_sel)

        def fkey_rec():
            return {
                 'name': None,
                 'constrained_columns': [],
                 'referred_schema': None,
                 'referred_table': None,
                 'referred_columns': []
             }

        fkeys = util.defaultdict(fkey_rec)

        rows = c.fetchall()
        for cons_name, local_column, \
                    remote_table, remote_column, remote_owner in rows:

            rec = fkeys[cons_name]
            rec['name'] = cons_name
            local_cols, remote_cols = \
                        rec['constrained_columns'], rec['referred_columns']

            if not rec['referred_table']:
                rec['referred_table'] = remote_table
                if schema is not None:
                    rec['referred_schema'] = remote_owner

            if local_column not in local_cols:
                local_cols.append(local_column)
            if remote_column not in remote_cols:
                remote_cols.append(remote_column)

        return fkeys.values()

    @reflection.cache
    def get_pk_constraint(self, connection, table_name, schema=None, **kw):
        schema = schema or self.default_schema_name

        # Select the column positions from sysindexes for sysconstraints
        data = connection.execute(
            """select t2.*
            from systables as t1, sysindexes as t2, sysconstraints as t3
            where t1.tabid=t2.tabid and t1.tabname=? and t1.owner=?
            and t2.idxname=t3.idxname and t3.constrtype='P'""",
            table_name, schema
        ).fetchall()

        colpositions = set()

        for row in data:
            colpos = set([getattr(row, 'part%d' % x) for x in range(1, 16)])
            colpositions |= colpos

        if not len(colpositions):
            return {'constrained_columns': [], 'name': None}

        # Select the column names using the columnpositions
        # TODO: Maybe cache a bit of those col infos (eg select all colnames for one table)
        place_holder = ','.join('?' * len(colpositions))
        c = connection.execute(
            """select t1.colname
            from syscolumns as t1, systables as t2
            where t2.tabname=? and t1.tabid = t2.tabid and
            t1.colno in (%s)""" % place_holder,
            table_name, *colpositions
        ).fetchall()

        cols = reduce(lambda x, y: list(x) + list(y), c, [])
        return {'constrained_columns': cols, 'name': None}

    @reflection.cache
    def get_indexes(self, connection, table_name, schema, **kw):
        # TODO: schema...
        c = connection.execute(
            """select t1.*
            from sysindexes as t1 , systables as t2
           where t1.tabid = t2.tabid and t2.tabname=?""",
             table_name)

        indexes = []
        for row in c.fetchall():
            colnames = [getattr(row, 'part%d' % x) for x in range(1, 16)]
            colnames = [x for x in colnames if x]
            place_holder = ','.join('?' * len(colnames))
            c = connection.execute(
                """select t1.colname
                from syscolumns as t1, systables as t2
                where t2.tabname=? and t1.tabid = t2.tabid and
                t1.colno in (%s)""" % place_holder,
                table_name, *colnames
            ).fetchall()
            c = reduce(lambda x, y: list(x) + list(y), c, [])
            indexes.append({
                'name': row.idxname,
                'unique': row.idxtype.lower() == 'u',
                'column_names': c
            })
        return indexes

    @reflection.cache
    def get_view_definition(self, connection, view_name, schema=None, **kw):
        schema = schema or self.default_schema_name
        c = connection.execute(
            """select t1.viewtext
            from sysviews as t1 , systables as t2
            where t1.tabid=t2.tabid and t2.tabname=?
            and t2.owner=? order by seqno""",
             view_name, schema).fetchall()

        return ''.join([row[0] for row in c])

    def _get_default_schema_name(self, connection):
        return connection.execute('select CURRENT_ROLE from systables').scalar()
