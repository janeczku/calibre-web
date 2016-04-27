# sql/compiler.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Base SQL and DDL compiler implementations.

Classes provided include:

:class:`.compiler.SQLCompiler` - renders SQL
strings

:class:`.compiler.DDLCompiler` - renders DDL
(data definition language) strings

:class:`.compiler.GenericTypeCompiler` - renders
type specification strings.

To generate user-defined SQL strings, see
:doc:`/ext/compiler`.

"""

import re
import sys
from .. import schema, engine, util, exc, types
from . import (
    operators, functions, util as sql_util, visitors, expression as sql
)
import decimal
import itertools

RESERVED_WORDS = set([
    'all', 'analyse', 'analyze', 'and', 'any', 'array',
    'as', 'asc', 'asymmetric', 'authorization', 'between',
    'binary', 'both', 'case', 'cast', 'check', 'collate',
    'column', 'constraint', 'create', 'cross', 'current_date',
    'current_role', 'current_time', 'current_timestamp',
    'current_user', 'default', 'deferrable', 'desc',
    'distinct', 'do', 'else', 'end', 'except', 'false',
    'for', 'foreign', 'freeze', 'from', 'full', 'grant',
    'group', 'having', 'ilike', 'in', 'initially', 'inner',
    'intersect', 'into', 'is', 'isnull', 'join', 'leading',
    'left', 'like', 'limit', 'localtime', 'localtimestamp',
    'natural', 'new', 'not', 'notnull', 'null', 'off', 'offset',
    'old', 'on', 'only', 'or', 'order', 'outer', 'overlaps',
    'placing', 'primary', 'references', 'right', 'select',
    'session_user', 'set', 'similar', 'some', 'symmetric', 'table',
    'then', 'to', 'trailing', 'true', 'union', 'unique', 'user',
    'using', 'verbose', 'when', 'where'])

LEGAL_CHARACTERS = re.compile(r'^[A-Z0-9_$]+$', re.I)
ILLEGAL_INITIAL_CHARACTERS = set([str(x) for x in xrange(0, 10)]).union(['$'])

BIND_PARAMS = re.compile(r'(?<![:\w\$\x5c]):([\w\$]+)(?![:\w\$])', re.UNICODE)
BIND_PARAMS_ESC = re.compile(r'\x5c(:[\w\$]+)(?![:\w\$])', re.UNICODE)

BIND_TEMPLATES = {
    'pyformat': "%%(%(name)s)s",
    'qmark': "?",
    'format': "%%s",
    'numeric': ":[_POSITION]",
    'named': ":%(name)s"
}

REQUIRED = util.symbol('REQUIRED', """
Placeholder for the value within a :class:`.BindParameter`
which is required to be present when the statement is passed
to :meth:`.Connection.execute`.

This symbol is typically used when a :func:`.expression.insert`
or :func:`.expression.update` statement is compiled without parameter
values present.

""")


OPERATORS = {
    # binary
    operators.and_: ' AND ',
    operators.or_: ' OR ',
    operators.add: ' + ',
    operators.mul: ' * ',
    operators.sub: ' - ',
    # Py2K
    operators.div: ' / ',
    # end Py2K
    operators.mod: ' % ',
    operators.truediv: ' / ',
    operators.neg: '-',
    operators.lt: ' < ',
    operators.le: ' <= ',
    operators.ne: ' != ',
    operators.gt: ' > ',
    operators.ge: ' >= ',
    operators.eq: ' = ',
    operators.concat_op: ' || ',
    operators.between_op: ' BETWEEN ',
    operators.match_op: ' MATCH ',
    operators.in_op: ' IN ',
    operators.notin_op: ' NOT IN ',
    operators.comma_op: ', ',
    operators.from_: ' FROM ',
    operators.as_: ' AS ',
    operators.is_: ' IS ',
    operators.isnot: ' IS NOT ',
    operators.collate: ' COLLATE ',

    # unary
    operators.exists: 'EXISTS ',
    operators.distinct_op: 'DISTINCT ',
    operators.inv: 'NOT ',

    # modifiers
    operators.desc_op: ' DESC',
    operators.asc_op: ' ASC',
    operators.nullsfirst_op: ' NULLS FIRST',
    operators.nullslast_op: ' NULLS LAST',
}

FUNCTIONS = {
    functions.coalesce: 'coalesce%(expr)s',
    functions.current_date: 'CURRENT_DATE',
    functions.current_time: 'CURRENT_TIME',
    functions.current_timestamp: 'CURRENT_TIMESTAMP',
    functions.current_user: 'CURRENT_USER',
    functions.localtime: 'LOCALTIME',
    functions.localtimestamp: 'LOCALTIMESTAMP',
    functions.random: 'random%(expr)s',
    functions.sysdate: 'sysdate',
    functions.session_user: 'SESSION_USER',
    functions.user: 'USER'
}

EXTRACT_MAP = {
    'month': 'month',
    'day': 'day',
    'year': 'year',
    'second': 'second',
    'hour': 'hour',
    'doy': 'doy',
    'minute': 'minute',
    'quarter': 'quarter',
    'dow': 'dow',
    'week': 'week',
    'epoch': 'epoch',
    'milliseconds': 'milliseconds',
    'microseconds': 'microseconds',
    'timezone_hour': 'timezone_hour',
    'timezone_minute': 'timezone_minute'
}

COMPOUND_KEYWORDS = {
    sql.CompoundSelect.UNION: 'UNION',
    sql.CompoundSelect.UNION_ALL: 'UNION ALL',
    sql.CompoundSelect.EXCEPT: 'EXCEPT',
    sql.CompoundSelect.EXCEPT_ALL: 'EXCEPT ALL',
    sql.CompoundSelect.INTERSECT: 'INTERSECT',
    sql.CompoundSelect.INTERSECT_ALL: 'INTERSECT ALL'
}


class _CompileLabel(visitors.Visitable):
    """lightweight label object which acts as an expression.Label."""

    __visit_name__ = 'label'
    __slots__ = 'element', 'name'

    def __init__(self, col, name, alt_names=()):
        self.element = col
        self.name = name
        self._alt_names = (col,) + alt_names

    @property
    def proxy_set(self):
        return self.element.proxy_set

    @property
    def type(self):
        return self.element.type

    @property
    def quote(self):
        return self.element.quote


class SQLCompiler(engine.Compiled):
    """Default implementation of Compiled.

    Compiles ClauseElements into SQL strings.   Uses a similar visit
    paradigm as visitors.ClauseVisitor but implements its own traversal.

    """

    extract_map = EXTRACT_MAP

    compound_keywords = COMPOUND_KEYWORDS

    isdelete = isinsert = isupdate = False
    """class-level defaults which can be set at the instance
    level to define if this Compiled instance represents
    INSERT/UPDATE/DELETE
    """

    returning = None
    """holds the "returning" collection of columns if
    the statement is CRUD and defines returning columns
    either implicitly or explicitly
    """

    returning_precedes_values = False
    """set to True classwide to generate RETURNING
    clauses before the VALUES or WHERE clause (i.e. MSSQL)
    """

    render_table_with_column_in_update_from = False
    """set to True classwide to indicate the SET clause
    in a multi-table UPDATE statement should qualify
    columns with the table name (i.e. MySQL only)
    """

    ansi_bind_rules = False
    """SQL 92 doesn't allow bind parameters to be used
    in the columns clause of a SELECT, nor does it allow
    ambiguous expressions like "? = ?".  A compiler
    subclass can set this flag to False if the target
    driver/DB enforces this
    """

    def __init__(self, dialect, statement, column_keys=None,
                    inline=False, **kwargs):
        """Construct a new ``DefaultCompiler`` object.

        dialect
          Dialect to be used

        statement
          ClauseElement to be compiled

        column_keys
          a list of column names to be compiled into an INSERT or UPDATE
          statement.

        """
        self.column_keys = column_keys

        # compile INSERT/UPDATE defaults/sequences inlined (no pre-
        # execute)
        self.inline = inline or getattr(statement, 'inline', False)

        # a dictionary of bind parameter keys to BindParameter
        # instances.
        self.binds = {}

        # a dictionary of BindParameter instances to "compiled" names
        # that are actually present in the generated SQL
        self.bind_names = util.column_dict()

        # stack which keeps track of nested SELECT statements
        self.stack = []

        # relates label names in the final SQL to a tuple of local
        # column/label name, ColumnElement object (if any) and
        # TypeEngine. ResultProxy uses this for type processing and
        # column targeting
        self.result_map = {}

        # true if the paramstyle is positional
        self.positional = dialect.positional
        if self.positional:
            self.positiontup = []
        self.bindtemplate = BIND_TEMPLATES[dialect.paramstyle]

        self.ctes = None

        # an IdentifierPreparer that formats the quoting of identifiers
        self.preparer = dialect.identifier_preparer
        self.label_length = dialect.label_length \
            or dialect.max_identifier_length

        # a map which tracks "anonymous" identifiers that are created on
        # the fly here
        self.anon_map = util.PopulateDict(self._process_anon)

        # a map which tracks "truncated" names based on
        # dialect.label_length or dialect.max_identifier_length
        self.truncated_names = {}
        engine.Compiled.__init__(self, dialect, statement, **kwargs)

        if self.positional and dialect.paramstyle == 'numeric':
            self._apply_numbered_params()

    @util.memoized_instancemethod
    def _init_cte_state(self):
        """Initialize collections related to CTEs only if
        a CTE is located, to save on the overhead of
        these collections otherwise.

        """
        # collect CTEs to tack on top of a SELECT
        self.ctes = util.OrderedDict()
        self.ctes_by_name = {}
        self.ctes_recursive = False
        if self.positional:
            self.cte_positional = []

    def _apply_numbered_params(self):
        poscount = itertools.count(1)
        self.string = re.sub(
                        r'\[_POSITION\]',
                        lambda m: str(util.next(poscount)),
                        self.string)

    @util.memoized_property
    def _bind_processors(self):
        return dict(
                (key, value) for key, value in
                ((self.bind_names[bindparam],
                   bindparam.type._cached_bind_processor(self.dialect))
                  for bindparam in self.bind_names)
                 if value is not None
            )

    def is_subquery(self):
        return len(self.stack) > 1

    @property
    def sql_compiler(self):
        return self

    def construct_params(self, params=None, _group_number=None, _check=True):
        """return a dictionary of bind parameter keys and values"""

        if params:
            pd = {}
            for bindparam, name in self.bind_names.iteritems():
                if bindparam.key in params:
                    pd[name] = params[bindparam.key]
                elif name in params:
                    pd[name] = params[name]
                elif _check and bindparam.required:
                    if _group_number:
                        raise exc.InvalidRequestError(
                            "A value is required for bind parameter %r, "
                            "in parameter group %d" %
                            (bindparam.key, _group_number))
                    else:
                        raise exc.InvalidRequestError(
                            "A value is required for bind parameter %r"
                            % bindparam.key)
                else:
                    pd[name] = bindparam.effective_value
            return pd
        else:
            pd = {}
            for bindparam in self.bind_names:
                if _check and bindparam.required:
                    if _group_number:
                        raise exc.InvalidRequestError(
                            "A value is required for bind parameter %r, "
                            "in parameter group %d" %
                            (bindparam.key, _group_number))
                    else:
                        raise exc.InvalidRequestError(
                            "A value is required for bind parameter %r"
                            % bindparam.key)
                pd[self.bind_names[bindparam]] = bindparam.effective_value
            return pd

    @property
    def params(self):
        """Return the bind param dictionary embedded into this
        compiled object, for those values that are present."""
        return self.construct_params(_check=False)

    def default_from(self):
        """Called when a SELECT statement has no froms, and no FROM clause is
        to be appended.

        Gives Oracle a chance to tack on a ``FROM DUAL`` to the string output.

        """
        return ""

    def visit_grouping(self, grouping, asfrom=False, **kwargs):
        return "(" + grouping.element._compiler_dispatch(self, **kwargs) + ")"

    def visit_label(self, label,
                            add_to_result_map=None,
                            within_label_clause=False,
                            within_columns_clause=False, **kw):
        # only render labels within the columns clause
        # or ORDER BY clause of a select.  dialect-specific compilers
        # can modify this behavior.
        if within_columns_clause and not within_label_clause:
            if isinstance(label.name, sql._truncated_label):
                labelname = self._truncated_identifier("colident", label.name)
            else:
                labelname = label.name

            if add_to_result_map is not None:
                add_to_result_map(
                        labelname,
                        label.name,
                        (label, labelname, ) + label._alt_names,
                        label.type
                )

            return label.element._compiler_dispatch(self,
                                    within_columns_clause=True,
                                    within_label_clause=True,
                                    **kw) + \
                        OPERATORS[operators.as_] + \
                        self.preparer.format_label(label, labelname)
        else:
            return label.element._compiler_dispatch(self,
                                    within_columns_clause=False,
                                    **kw)

    def visit_column(self, column, add_to_result_map=None,
                                    include_table=True, **kwargs):
        name = orig_name = column.name
        if name is None:
            raise exc.CompileError("Cannot compile Column object until "
                                   "its 'name' is assigned.")

        is_literal = column.is_literal
        if not is_literal and isinstance(name, sql._truncated_label):
            name = self._truncated_identifier("colident", name)

        if add_to_result_map is not None:
            add_to_result_map(
                name,
                orig_name,
                (column, name, column.key),
                column.type
            )

        if is_literal:
            name = self.escape_literal_column(name)
        else:
            name = self.preparer.quote(name, column.quote)

        table = column.table
        if table is None or not include_table or not table.named_with_column:
            return name
        else:
            if table.schema:
                schema_prefix = self.preparer.quote_schema(
                                    table.schema,
                                    table.quote_schema) + '.'
            else:
                schema_prefix = ''
            tablename = table.name
            if isinstance(tablename, sql._truncated_label):
                tablename = self._truncated_identifier("alias", tablename)

            return schema_prefix + \
                    self.preparer.quote(tablename, table.quote) + \
                    "." + name

    def escape_literal_column(self, text):
        """provide escaping for the literal_column() construct."""

        # TODO: some dialects might need different behavior here
        return text.replace('%', '%%')

    def visit_fromclause(self, fromclause, **kwargs):
        return fromclause.name

    def visit_index(self, index, **kwargs):
        return index.name

    def visit_typeclause(self, typeclause, **kwargs):
        return self.dialect.type_compiler.process(typeclause.type)

    def post_process_text(self, text):
        return text

    def visit_textclause(self, textclause, **kwargs):
        if textclause.typemap is not None:
            for colname, type_ in textclause.typemap.iteritems():
                self.result_map[colname
                                if self.dialect.case_sensitive
                                else colname.lower()] = \
                                (colname, None, type_)

        def do_bindparam(m):
            name = m.group(1)
            if name in textclause.bindparams:
                return self.process(textclause.bindparams[name])
            else:
                return self.bindparam_string(name, **kwargs)

        # un-escape any \:params
        return BIND_PARAMS_ESC.sub(lambda m: m.group(1),
            BIND_PARAMS.sub(do_bindparam,
             self.post_process_text(textclause.text))
        )

    def visit_null(self, expr, **kw):
        return 'NULL'

    def visit_true(self, expr, **kw):
        return 'true'

    def visit_false(self, expr, **kw):
        return 'false'

    def visit_clauselist(self, clauselist, **kwargs):
        sep = clauselist.operator
        if sep is None:
            sep = " "
        else:
            sep = OPERATORS[clauselist.operator]
        return sep.join(
                    s for s in
                    (c._compiler_dispatch(self, **kwargs)
                    for c in clauselist.clauses)
                    if s)

    def visit_case(self, clause, **kwargs):
        x = "CASE "
        if clause.value is not None:
            x += clause.value._compiler_dispatch(self, **kwargs) + " "
        for cond, result in clause.whens:
            x += "WHEN " + cond._compiler_dispatch(
                            self, **kwargs
                            ) + " THEN " + result._compiler_dispatch(
                                            self, **kwargs) + " "
        if clause.else_ is not None:
            x += "ELSE " + clause.else_._compiler_dispatch(
                                self, **kwargs
                            ) + " "
        x += "END"
        return x

    def visit_cast(self, cast, **kwargs):
        return "CAST(%s AS %s)" % \
                    (cast.clause._compiler_dispatch(self, **kwargs),
                    cast.typeclause._compiler_dispatch(self, **kwargs))

    def visit_over(self, over, **kwargs):
        return "%s OVER (%s)" % (
            over.func._compiler_dispatch(self, **kwargs),
            ' '.join(
                 '%s BY %s' % (word, clause._compiler_dispatch(self, **kwargs))
                 for word, clause in (
                     ('PARTITION', over.partition_by),
                     ('ORDER', over.order_by)
                 )
                 if clause is not None and len(clause)
            )
        )

    def visit_extract(self, extract, **kwargs):
        field = self.extract_map.get(extract.field, extract.field)
        return "EXTRACT(%s FROM %s)" % (field,
                            extract.expr._compiler_dispatch(self, **kwargs))

    def visit_function(self, func, add_to_result_map=None, **kwargs):
        if add_to_result_map is not None:
            add_to_result_map(
                func.name, func.name, (), func.type
            )

        disp = getattr(self, "visit_%s_func" % func.name.lower(), None)
        if disp:
            return disp(func, **kwargs)
        else:
            name = FUNCTIONS.get(func.__class__, func.name + "%(expr)s")
            return ".".join(list(func.packagenames) + [name]) % \
                            {'expr': self.function_argspec(func, **kwargs)}

    def visit_next_value_func(self, next_value, **kw):
        return self.visit_sequence(next_value.sequence)

    def visit_sequence(self, sequence):
        raise NotImplementedError(
            "Dialect '%s' does not support sequence increments." %
            self.dialect.name
        )

    def function_argspec(self, func, **kwargs):
        return func.clause_expr._compiler_dispatch(self, **kwargs)

    def visit_compound_select(self, cs, asfrom=False,
                            parens=True, compound_index=0, **kwargs):
        toplevel = not self.stack
        entry = self._default_stack_entry if toplevel else self.stack[-1]

        self.stack.append(
                    {
                        'correlate_froms': entry['correlate_froms'],
                        'iswrapper': toplevel,
                        'asfrom_froms': entry['asfrom_froms']
                    })

        keyword = self.compound_keywords.get(cs.keyword)

        text = (" " + keyword + " ").join(
                            (c._compiler_dispatch(self,
                                            asfrom=asfrom, parens=False,
                                            compound_index=i, **kwargs)
                            for i, c in enumerate(cs.selects))
                        )

        group_by = cs._group_by_clause._compiler_dispatch(
                                self, asfrom=asfrom, **kwargs)
        if group_by:
            text += " GROUP BY " + group_by

        text += self.order_by_clause(cs, **kwargs)
        text += (cs._limit is not None or cs._offset is not None) and \
                        self.limit_clause(cs) or ""

        if self.ctes and \
            compound_index == 0 and toplevel:
            text = self._render_cte_clause() + text

        self.stack.pop(-1)
        if asfrom and parens:
            return "(" + text + ")"
        else:
            return text

    def visit_unary(self, unary, **kw):
        if unary.operator:
            if unary.modifier:
                raise exc.CompileError(
                        "Unary expression does not support operator "
                        "and modifier simultaneously")
            disp = getattr(self, "visit_%s_unary_operator" %
                                    unary.operator.__name__, None)
            if disp:
                return disp(unary, unary.operator, **kw)
            else:
                return self._generate_generic_unary_operator(unary,
                                    OPERATORS[unary.operator], **kw)
        elif unary.modifier:
            disp = getattr(self, "visit_%s_unary_modifier" %
                                    unary.modifier.__name__, None)
            if disp:
                return disp(unary, unary.modifier, **kw)
            else:
                return self._generate_generic_unary_modifier(unary,
                                    OPERATORS[unary.modifier], **kw)
        else:
            raise exc.CompileError(
                            "Unary expression has no operator or modifier")

    def visit_binary(self, binary, **kw):
        # don't allow "? = ?" to render
        if self.ansi_bind_rules and \
            isinstance(binary.left, sql.BindParameter) and \
            isinstance(binary.right, sql.BindParameter):
            kw['literal_binds'] = True

        operator = binary.operator
        disp = getattr(self, "visit_%s_binary" % operator.__name__, None)
        if disp:
            return disp(binary, operator, **kw)
        else:
            try:
                opstring = OPERATORS[operator]
            except KeyError:
                raise exc.UnsupportedCompilationError(self, operator)
            else:
                return self._generate_generic_binary(binary, opstring, **kw)

    def visit_custom_op_binary(self, element, operator, **kw):
        return self._generate_generic_binary(element,
                            " " + operator.opstring + " ", **kw)

    def visit_custom_op_unary_operator(self, element, operator, **kw):
        return self._generate_generic_unary_operator(element,
                            operator.opstring + " ", **kw)

    def visit_custom_op_unary_modifier(self, element, operator, **kw):
        return self._generate_generic_unary_modifier(element,
                            " " + operator.opstring, **kw)

    def _generate_generic_binary(self, binary, opstring, **kw):
        return binary.left._compiler_dispatch(self, **kw) + \
                                        opstring + \
                            binary.right._compiler_dispatch(self, **kw)

    def _generate_generic_unary_operator(self, unary, opstring, **kw):
        return opstring + unary.element._compiler_dispatch(self, **kw)

    def _generate_generic_unary_modifier(self, unary, opstring, **kw):
        return unary.element._compiler_dispatch(self, **kw) + opstring

    @util.memoized_property
    def _like_percent_literal(self):
        return sql.literal_column("'%'", type_=types.String())

    def visit_contains_op_binary(self, binary, operator, **kw):
        binary = binary._clone()
        percent = self._like_percent_literal
        binary.right = percent.__add__(binary.right).__add__(percent)
        return self.visit_like_op_binary(binary, operator, **kw)

    def visit_notcontains_op_binary(self, binary, operator, **kw):
        binary = binary._clone()
        percent = self._like_percent_literal
        binary.right = percent.__add__(binary.right).__add__(percent)
        return self.visit_notlike_op_binary(binary, operator, **kw)

    def visit_startswith_op_binary(self, binary, operator, **kw):
        binary = binary._clone()
        percent = self._like_percent_literal
        binary.right = percent.__radd__(
                    binary.right
                )
        return self.visit_like_op_binary(binary, operator, **kw)

    def visit_notstartswith_op_binary(self, binary, operator, **kw):
        binary = binary._clone()
        percent = self._like_percent_literal
        binary.right = percent.__radd__(
                    binary.right
                )
        return self.visit_notlike_op_binary(binary, operator, **kw)

    def visit_endswith_op_binary(self, binary, operator, **kw):
        binary = binary._clone()
        percent = self._like_percent_literal
        binary.right = percent.__add__(binary.right)
        return self.visit_like_op_binary(binary, operator, **kw)

    def visit_notendswith_op_binary(self, binary, operator, **kw):
        binary = binary._clone()
        percent = self._like_percent_literal
        binary.right = percent.__add__(binary.right)
        return self.visit_notlike_op_binary(binary, operator, **kw)

    def visit_like_op_binary(self, binary, operator, **kw):
        escape = binary.modifiers.get("escape", None)
        return '%s LIKE %s' % (
                            binary.left._compiler_dispatch(self, **kw),
                            binary.right._compiler_dispatch(self, **kw)) \
            + (escape and
                    (' ESCAPE ' + self.render_literal_value(escape, None))
                    or '')

    def visit_notlike_op_binary(self, binary, operator, **kw):
        escape = binary.modifiers.get("escape", None)
        return '%s NOT LIKE %s' % (
                            binary.left._compiler_dispatch(self, **kw),
                            binary.right._compiler_dispatch(self, **kw)) \
            + (escape and
                    (' ESCAPE ' + self.render_literal_value(escape, None))
                    or '')

    def visit_ilike_op_binary(self, binary, operator, **kw):
        escape = binary.modifiers.get("escape", None)
        return 'lower(%s) LIKE lower(%s)' % (
                            binary.left._compiler_dispatch(self, **kw),
                            binary.right._compiler_dispatch(self, **kw)) \
            + (escape and
                    (' ESCAPE ' + self.render_literal_value(escape, None))
                    or '')

    def visit_notilike_op_binary(self, binary, operator, **kw):
        escape = binary.modifiers.get("escape", None)
        return 'lower(%s) NOT LIKE lower(%s)' % (
                            binary.left._compiler_dispatch(self, **kw),
                            binary.right._compiler_dispatch(self, **kw)) \
            + (escape and
                    (' ESCAPE ' + self.render_literal_value(escape, None))
                    or '')

    def visit_bindparam(self, bindparam, within_columns_clause=False,
                                            literal_binds=False,
                                            skip_bind_expression=False,
                                            **kwargs):

        if not skip_bind_expression and bindparam.type._has_bind_expression:
            bind_expression = bindparam.type.bind_expression(bindparam)
            return self.process(bind_expression,
                                skip_bind_expression=True)

        if literal_binds or \
            (within_columns_clause and \
                self.ansi_bind_rules):
            if bindparam.value is None:
                raise exc.CompileError("Bind parameter without a "
                                        "renderable value not allowed here.")
            return self.render_literal_bindparam(bindparam,
                            within_columns_clause=True, **kwargs)

        name = self._truncate_bindparam(bindparam)

        if name in self.binds:
            existing = self.binds[name]
            if existing is not bindparam:
                if (existing.unique or bindparam.unique) and \
                        not existing.proxy_set.intersection(
                                                        bindparam.proxy_set):
                    raise exc.CompileError(
                            "Bind parameter '%s' conflicts with "
                            "unique bind parameter of the same name" %
                            bindparam.key
                        )
                elif existing._is_crud or bindparam._is_crud:
                    raise exc.CompileError(
                        "bindparam() name '%s' is reserved "
                        "for automatic usage in the VALUES or SET "
                        "clause of this "
                        "insert/update statement.   Please use a "
                        "name other than column name when using bindparam() "
                        "with insert() or update() (for example, 'b_%s')."
                        % (bindparam.key, bindparam.key)
                    )

        self.binds[bindparam.key] = self.binds[name] = bindparam

        return self.bindparam_string(name, quote=bindparam.quote, **kwargs)

    def render_literal_bindparam(self, bindparam, **kw):
        value = bindparam.value
        processor = bindparam.type._cached_bind_processor(self.dialect)
        if processor:
            value = processor(value)
        return self.render_literal_value(value, bindparam.type)

    def render_literal_value(self, value, type_):
        """Render the value of a bind parameter as a quoted literal.

        This is used for statement sections that do not accept bind parameters
        on the target driver/database.

        This should be implemented by subclasses using the quoting services
        of the DBAPI.

        """
        if isinstance(value, basestring):
            value = value.replace("'", "''")
            return "'%s'" % value
        elif value is None:
            return "NULL"
        elif isinstance(value, (float, int, long)):
            return repr(value)
        elif isinstance(value, decimal.Decimal):
            return str(value)
        elif isinstance(value, util.binary_type):
            # only would occur on py3k b.c. on 2k the string_types
            # directive above catches this.
            # see #2838
            value = value.decode(self.dialect.encoding).replace("'", "''")
            return "'%s'" % value

        else:
            raise NotImplementedError(
                        "Don't know how to literal-quote value %r" % value)

    def _truncate_bindparam(self, bindparam):
        if bindparam in self.bind_names:
            return self.bind_names[bindparam]

        bind_name = bindparam.key
        if isinstance(bind_name, sql._truncated_label):
            bind_name = self._truncated_identifier("bindparam", bind_name)

        # add to bind_names for translation
        self.bind_names[bindparam] = bind_name

        return bind_name

    def _truncated_identifier(self, ident_class, name):
        if (ident_class, name) in self.truncated_names:
            return self.truncated_names[(ident_class, name)]

        anonname = name.apply_map(self.anon_map)

        if len(anonname) > self.label_length:
            counter = self.truncated_names.get(ident_class, 1)
            truncname = anonname[0:max(self.label_length - 6, 0)] + \
                                "_" + hex(counter)[2:]
            self.truncated_names[ident_class] = counter + 1
        else:
            truncname = anonname
        self.truncated_names[(ident_class, name)] = truncname
        return truncname

    def _anonymize(self, name):
        return name % self.anon_map

    def _process_anon(self, key):
        (ident, derived) = key.split(' ', 1)
        anonymous_counter = self.anon_map.get(derived, 1)
        self.anon_map[derived] = anonymous_counter + 1
        return derived + "_" + str(anonymous_counter)

    def bindparam_string(self, name, quote=None,
                        positional_names=None, **kw):
        if self.positional:
            if positional_names is not None:
                positional_names.append(name)
            else:
                self.positiontup.append(name)
        return self.bindtemplate % {'name': name}

    def visit_cte(self, cte, asfrom=False, ashint=False,
                                fromhints=None,
                                **kwargs):
        self._init_cte_state()
        if self.positional:
            kwargs['positional_names'] = self.cte_positional

        if isinstance(cte.name, sql._truncated_label):
            cte_name = self._truncated_identifier("alias", cte.name)
        else:
            cte_name = cte.name

        if cte_name in self.ctes_by_name:
            existing_cte = self.ctes_by_name[cte_name]
            # we've generated a same-named CTE that we are enclosed in,
            # or this is the same CTE.  just return the name.
            if cte in existing_cte._restates or cte is existing_cte:
                return self.preparer.format_alias(cte, cte_name)
            elif existing_cte in cte._restates:
                # we've generated a same-named CTE that is
                # enclosed in us - we take precedence, so
                # discard the text for the "inner".
                del self.ctes[existing_cte]
            else:
                raise exc.CompileError(
                        "Multiple, unrelated CTEs found with "
                        "the same name: %r" %
                        cte_name)

        self.ctes_by_name[cte_name] = cte

        if cte._cte_alias is not None:
            orig_cte = cte._cte_alias
            if orig_cte not in self.ctes:
                self.visit_cte(orig_cte)
            cte_alias_name = cte._cte_alias.name
            if isinstance(cte_alias_name, sql._truncated_label):
                cte_alias_name = self._truncated_identifier("alias", cte_alias_name)
        else:
            orig_cte = cte
            cte_alias_name = None
        if not cte_alias_name and cte not in self.ctes:
            if cte.recursive:
                self.ctes_recursive = True
            text = self.preparer.format_alias(cte, cte_name)
            if cte.recursive:
                if isinstance(cte.original, sql.Select):
                    col_source = cte.original
                elif isinstance(cte.original, sql.CompoundSelect):
                    col_source = cte.original.selects[0]
                else:
                    assert False
                recur_cols = [c for c in
                            util.unique_list(col_source.inner_columns)
                                if c is not None]

                text += "(%s)" % (", ".join(
                                    self.preparer.format_column(ident)
                                    for ident in recur_cols))
            text += " AS \n" + \
                        cte.original._compiler_dispatch(
                                self, asfrom=True, **kwargs
                            )
            self.ctes[cte] = text

        if asfrom:
            if cte_alias_name:
                text = self.preparer.format_alias(cte, cte_alias_name)
                text += " AS " + cte_name
            else:
                return self.preparer.format_alias(cte, cte_name)
            return text

    def visit_alias(self, alias, asfrom=False, ashint=False,
                                iscrud=False,
                                fromhints=None, **kwargs):
        if asfrom or ashint:
            if isinstance(alias.name, sql._truncated_label):
                alias_name = self._truncated_identifier("alias", alias.name)
            else:
                alias_name = alias.name

        if ashint:
            return self.preparer.format_alias(alias, alias_name)
        elif asfrom:
            ret = alias.original._compiler_dispatch(self,
                                asfrom=True, **kwargs) + \
                                " AS " + \
                    self.preparer.format_alias(alias, alias_name)

            if fromhints and alias in fromhints:
                ret = self.format_from_hint_text(ret, alias,
                                fromhints[alias], iscrud)

            return ret
        else:
            return alias.original._compiler_dispatch(self, **kwargs)

    def _add_to_result_map(self, keyname, name, objects, type_):
        if not self.dialect.case_sensitive:
            keyname = keyname.lower()

        if keyname in self.result_map:
            # conflicting keyname, just double up the list
            # of objects.  this will cause an "ambiguous name"
            # error if an attempt is made by the result set to
            # access.
            e_name, e_obj, e_type = self.result_map[keyname]
            self.result_map[keyname] = e_name, e_obj + objects, e_type
        else:
            self.result_map[keyname] = name, objects, type_

    def _label_select_column(self, select, column,
                                    populate_result_map,
                                    asfrom, column_clause_args,
                                    name=None,
                                    within_columns_clause=True):
        """produce labeled columns present in a select()."""

        if column.type._has_column_expression and \
                populate_result_map:
            col_expr = column.type.column_expression(column)
            add_to_result_map = lambda keyname, name, objects, type_: \
                                self._add_to_result_map(
                                        keyname, name,
                                        objects + (column,), type_)
        else:
            col_expr = column
            if populate_result_map:
                add_to_result_map = self._add_to_result_map
            else:
                add_to_result_map = None

        if not within_columns_clause:
            result_expr = col_expr
        elif isinstance(column, sql.Label):
            if col_expr is not column:
                result_expr = _CompileLabel(
                        col_expr,
                        column.name,
                        alt_names=(column.element,)
                    )
            else:
                result_expr = col_expr

        elif select is not None and name:
            result_expr = _CompileLabel(
                    col_expr,
                    name,
                    alt_names=(column._key_label,)
                )

        elif \
            asfrom and \
            isinstance(column, sql.ColumnClause) and \
            not column.is_literal and \
            column.table is not None and \
                not isinstance(column.table, sql.Select):
            result_expr = _CompileLabel(col_expr,
                                    sql._as_truncated(column.name),
                                    alt_names=(column.key,))
        elif not isinstance(column,
                    (sql.UnaryExpression, sql.TextClause)) \
                and (not hasattr(column, 'name') or \
                        isinstance(column, sql.Function)):
            result_expr = _CompileLabel(col_expr, column.anon_label)
        elif col_expr is not column:
            # TODO: are we sure "column" has a .name and .key here ?
            # assert isinstance(column, sql.ColumnClause)
            result_expr = _CompileLabel(col_expr,
                            sql._as_truncated(column.name),
                            alt_names=(column.key,))
        else:
            result_expr = col_expr

        column_clause_args.update(
                    within_columns_clause=within_columns_clause,
                    add_to_result_map=add_to_result_map
                )
        return result_expr._compiler_dispatch(
                       self,
                        **column_clause_args
                    )

    def format_from_hint_text(self, sqltext, table, hint, iscrud):
        hinttext = self.get_from_hint_text(table, hint)
        if hinttext:
            sqltext += " " + hinttext
        return sqltext

    def get_select_hint_text(self, byfroms):
        return None

    def get_from_hint_text(self, table, text):
        return None

    def get_crud_hint_text(self, table, text):
        return None



    _default_stack_entry = util.immutabledict([
                                        ('iswrapper', False),
                                        ('correlate_froms', frozenset()),
                                        ('asfrom_froms', frozenset())
                                    ])

    def _display_froms_for_select(self, select, asfrom):
        # utility method to help external dialects
        # get the correct from list for a select.
        # specifically the oracle dialect needs this feature
        # right now.
        toplevel = not self.stack
        entry = self._default_stack_entry if toplevel else self.stack[-1]

        correlate_froms = entry['correlate_froms']
        asfrom_froms = entry['asfrom_froms']

        if asfrom:
            froms = select._get_display_froms(
                            explicit_correlate_froms=\
                                correlate_froms.difference(asfrom_froms),
                            implicit_correlate_froms=())
        else:
            froms = select._get_display_froms(
                            explicit_correlate_froms=correlate_froms,
                            implicit_correlate_froms=asfrom_froms)
        return froms

    def visit_select(self, select, asfrom=False, parens=True,
                            iswrapper=False, fromhints=None,
                            compound_index=0,
                            force_result_map=False,
                            positional_names=None,
                            **kwargs):

        toplevel = not self.stack
        entry = self._default_stack_entry if toplevel else self.stack[-1]


        populate_result_map = force_result_map or (
                                        compound_index == 0 and (
                                            toplevel or \
                                            entry['iswrapper']
                                        )
                                    )


        correlate_froms = entry['correlate_froms']
        asfrom_froms = entry['asfrom_froms']

        if asfrom:
            froms = select._get_display_froms(
                            explicit_correlate_froms=
                                correlate_froms.difference(asfrom_froms),
                            implicit_correlate_froms=())
        else:
            froms = select._get_display_froms(
                            explicit_correlate_froms=correlate_froms,
                            implicit_correlate_froms=asfrom_froms)


        new_correlate_froms = set(sql._from_objects(*froms))
        all_correlate_froms = new_correlate_froms.union(correlate_froms)

        new_entry = {
                    'asfrom_froms': new_correlate_froms,
                    'iswrapper': iswrapper,
                    'correlate_froms': all_correlate_froms
                }
        self.stack.append(new_entry)

        column_clause_args = kwargs.copy()
        column_clause_args.update({
                'positional_names': positional_names,
                'within_label_clause': False,
                'within_columns_clause': False
            })

        # the actual list of columns to print in the SELECT column list.
        inner_columns = [
            c for c in [
                self._label_select_column(select,
                                    column,
                                    populate_result_map, asfrom,
                                    column_clause_args,
                                    name=name)
                for name, column in select._columns_plus_names
                ]
            if c is not None
        ]

        text = "SELECT "  # we're off to a good start !

        if select._hints:
            byfrom = dict([
                            (from_, hinttext % {
                                'name':from_._compiler_dispatch(
                                    self, ashint=True)
                            })
                            for (from_, dialect), hinttext in
                            select._hints.iteritems()
                            if dialect in ('*', self.dialect.name)
                        ])
            hint_text = self.get_select_hint_text(byfrom)
            if hint_text:
                text += hint_text + " "

        if select._prefixes:
            text += self._generate_prefixes(select, select._prefixes, **kwargs)

        text += self.get_select_precolumns(select)
        text += ', '.join(inner_columns)

        if froms:
            text += " \nFROM "

            if select._hints:
                text += ', '.join([f._compiler_dispatch(self,
                                    asfrom=True, fromhints=byfrom,
                                    **kwargs)
                                for f in froms])
            else:
                text += ', '.join([f._compiler_dispatch(self,
                                    asfrom=True, **kwargs)
                                for f in froms])
        else:
            text += self.default_from()

        if select._whereclause is not None:
            t = select._whereclause._compiler_dispatch(self, **kwargs)
            if t:
                text += " \nWHERE " + t

        if select._group_by_clause.clauses:
            group_by = select._group_by_clause._compiler_dispatch(
                                        self, **kwargs)
            if group_by:
                text += " GROUP BY " + group_by

        if select._having is not None:
            t = select._having._compiler_dispatch(self, **kwargs)
            if t:
                text += " \nHAVING " + t

        if select._order_by_clause.clauses:
            text += self.order_by_clause(select, **kwargs)
        if select._limit is not None or select._offset is not None:
            text += self.limit_clause(select)
        if select.for_update:
            text += self.for_update_clause(select)

        if self.ctes and \
            compound_index == 0 and toplevel:
            text = self._render_cte_clause() + text

        self.stack.pop(-1)

        if asfrom and parens:
            return "(" + text + ")"
        else:
            return text

    def _generate_prefixes(self, stmt, prefixes, **kw):
        clause = " ".join(
                            prefix._compiler_dispatch(self, **kw)
                            for prefix, dialect_name in prefixes
                            if dialect_name is None or
                                dialect_name == self.dialect.name
                            )
        if clause:
            clause += " "
        return clause

    def _render_cte_clause(self):
        if self.positional:
            self.positiontup = self.cte_positional + self.positiontup
        cte_text = self.get_cte_preamble(self.ctes_recursive) + " "
        cte_text += ", \n".join(
            [txt for txt in self.ctes.values()]
        )
        cte_text += "\n "
        return cte_text

    def get_cte_preamble(self, recursive):
        if recursive:
            return "WITH RECURSIVE"
        else:
            return "WITH"

    def get_select_precolumns(self, select):
        """Called when building a ``SELECT`` statement, position is just
        before column list.

        """
        return select._distinct and "DISTINCT " or ""

    def order_by_clause(self, select, **kw):
        order_by = select._order_by_clause._compiler_dispatch(self, **kw)
        if order_by:
            return " ORDER BY " + order_by
        else:
            return ""

    def for_update_clause(self, select):
        if select.for_update:
            return " FOR UPDATE"
        else:
            return ""

    def returning_clause(self, stmt, returning_cols):
        raise exc.CompileError(
                    "RETURNING is not supported by this "
                    "dialect's statement compiler.")

    def limit_clause(self, select):
        text = ""
        if select._limit is not None:
            text += "\n LIMIT " + self.process(sql.literal(select._limit))
        if select._offset is not None:
            if select._limit is None:
                text += "\n LIMIT -1"
            text += " OFFSET " + self.process(sql.literal(select._offset))
        return text

    def visit_table(self, table, asfrom=False, iscrud=False, ashint=False,
                        fromhints=None, **kwargs):
        if asfrom or ashint:
            if getattr(table, "schema", None):
                ret = self.preparer.quote_schema(table.schema,
                                table.quote_schema) + \
                                "." + self.preparer.quote(table.name,
                                                table.quote)
            else:
                ret = self.preparer.quote(table.name, table.quote)
            if fromhints and table in fromhints:
                ret = self.format_from_hint_text(ret, table,
                                    fromhints[table], iscrud)
            return ret
        else:
            return ""

    def visit_join(self, join, asfrom=False, **kwargs):
        return (
            join.left._compiler_dispatch(self, asfrom=True, **kwargs) +
            (join.isouter and " LEFT OUTER JOIN " or " JOIN ") +
            join.right._compiler_dispatch(self, asfrom=True, **kwargs) +
            " ON " +
            join.onclause._compiler_dispatch(self, **kwargs)
        )

    def visit_insert(self, insert_stmt, **kw):
        self.isinsert = True
        colparams = self._get_colparams(insert_stmt)

        if not colparams and \
                not self.dialect.supports_default_values and \
                not self.dialect.supports_empty_insert:
            raise exc.CompileError("The '%s' dialect with current database "
                                    "version settings does not support empty "
                                    "inserts." %
                                    self.dialect.name)

        if insert_stmt._has_multi_parameters:
            if not self.dialect.supports_multivalues_insert:
                raise exc.CompileError("The '%s' dialect with current database "
                                    "version settings does not support "
                                    "in-place multirow inserts." %
                                    self.dialect.name)
            colparams_single = colparams[0]
        else:
            colparams_single = colparams


        preparer = self.preparer
        supports_default_values = self.dialect.supports_default_values

        text = "INSERT "

        if insert_stmt._prefixes:
            text += self._generate_prefixes(insert_stmt,
                                insert_stmt._prefixes, **kw)

        text += "INTO "
        table_text = preparer.format_table(insert_stmt.table)

        if insert_stmt._hints:
            dialect_hints = dict([
                (table, hint_text)
                for (table, dialect), hint_text in
                insert_stmt._hints.items()
                if dialect in ('*', self.dialect.name)
            ])
            if insert_stmt.table in dialect_hints:
                table_text = self.format_from_hint_text(
                                    table_text,
                                    insert_stmt.table,
                                    dialect_hints[insert_stmt.table],
                                    True
                                )

        text += table_text

        if colparams_single or not supports_default_values:
            text += " (%s)" % ', '.join([preparer.format_column(c[0])
                       for c in colparams_single])

        if self.returning or insert_stmt._returning:
            self.returning = self.returning or insert_stmt._returning
            returning_clause = self.returning_clause(
                                    insert_stmt, self.returning)

            if self.returning_precedes_values:
                text += " " + returning_clause

        if insert_stmt.select is not None:
            text += " %s" % self.process(insert_stmt.select, **kw)
        elif not colparams and supports_default_values:
            text += " DEFAULT VALUES"
        elif insert_stmt._has_multi_parameters:
            text += " VALUES %s" % (
                        ", ".join(
                            "(%s)" % (
                                ', '.join(c[1] for c in colparam_set)
                            )
                            for colparam_set in colparams
                            )
                        )
        else:
            text += " VALUES (%s)" % \
                     ', '.join([c[1] for c in colparams])

        if self.returning and not self.returning_precedes_values:
            text += " " + returning_clause

        return text

    def update_limit_clause(self, update_stmt):
        """Provide a hook for MySQL to add LIMIT to the UPDATE"""
        return None

    def update_tables_clause(self, update_stmt, from_table,
                                            extra_froms, **kw):
        """Provide a hook to override the initial table clause
        in an UPDATE statement.

        MySQL overrides this.

        """
        return from_table._compiler_dispatch(self, asfrom=True,
                                iscrud=True, **kw)

    def update_from_clause(self, update_stmt,
                                from_table, extra_froms,
                                from_hints,
                                **kw):
        """Provide a hook to override the generation of an
        UPDATE..FROM clause.

        MySQL and MSSQL override this.

        """
        return "FROM " + ', '.join(
                    t._compiler_dispatch(self, asfrom=True,
                                    fromhints=from_hints, **kw)
                    for t in extra_froms)

    def visit_update(self, update_stmt, **kw):
        self.stack.append(
                        {'correlate_froms': set([update_stmt.table]),
                        "iswrapper": False,
                        "asfrom_froms": set([update_stmt.table])})

        self.isupdate = True

        extra_froms = update_stmt._extra_froms

        text = "UPDATE "

        if update_stmt._prefixes:
            text += self._generate_prefixes(update_stmt,
                                update_stmt._prefixes, **kw)

        table_text = self.update_tables_clause(update_stmt, update_stmt.table,
                                               extra_froms, **kw)

        colparams = self._get_colparams(update_stmt, extra_froms)

        if update_stmt._hints:
            dialect_hints = dict([
                (table, hint_text)
                for (table, dialect), hint_text in
                update_stmt._hints.items()
                if dialect in ('*', self.dialect.name)
            ])
            if update_stmt.table in dialect_hints:
                table_text = self.format_from_hint_text(
                                    table_text,
                                    update_stmt.table,
                                    dialect_hints[update_stmt.table],
                                    True
                                )
        else:
            dialect_hints = None

        text += table_text

        text += ' SET '
        include_table = extra_froms and \
                        self.render_table_with_column_in_update_from
        text += ', '.join(
                        c[0]._compiler_dispatch(self,
                            include_table=include_table) +
                        '=' + c[1] for c in colparams
                        )

        if update_stmt._returning:
            self.returning = update_stmt._returning
            if self.returning_precedes_values:
                text += " " + self.returning_clause(
                                    update_stmt, update_stmt._returning)

        if extra_froms:
            extra_from_text = self.update_from_clause(
                                        update_stmt,
                                        update_stmt.table,
                                        extra_froms,
                                        dialect_hints, **kw)
            if extra_from_text:
                text += " " + extra_from_text

        if update_stmt._whereclause is not None:
            text += " WHERE " + self.process(update_stmt._whereclause)

        limit_clause = self.update_limit_clause(update_stmt)
        if limit_clause:
            text += " " + limit_clause

        if self.returning and not self.returning_precedes_values:
            text += " " + self.returning_clause(
                                    update_stmt, update_stmt._returning)

        self.stack.pop(-1)

        return text

    def _create_crud_bind_param(self, col, value, required=False, name=None):
        if name is None:
            name = col.key
        bindparam = sql.bindparam(name, value,
                            type_=col.type, required=required,
                            quote=col.quote)
        bindparam._is_crud = True
        return bindparam._compiler_dispatch(self)

    def _get_colparams(self, stmt, extra_tables=None):
        """create a set of tuples representing column/string pairs for use
        in an INSERT or UPDATE statement.

        Also generates the Compiled object's postfetch, prefetch, and
        returning column collections, used for default handling and ultimately
        populating the ResultProxy's prefetch_cols() and postfetch_cols()
        collections.

        """

        self.postfetch = []
        self.prefetch = []
        self.returning = []

        # no parameters in the statement, no parameters in the
        # compiled params - return binds for all columns
        if self.column_keys is None and stmt.parameters is None:
            return [
                        (c, self._create_crud_bind_param(c,
                                    None, required=True))
                        for c in stmt.table.columns
                    ]

        if stmt._has_multi_parameters:
            stmt_parameters = stmt.parameters[0]
        else:
            stmt_parameters = stmt.parameters

        # if we have statement parameters - set defaults in the
        # compiled params
        if self.column_keys is None:
            parameters = {}
        else:
            parameters = dict((sql._column_as_key(key), REQUIRED)
                              for key in self.column_keys
                              if not stmt_parameters or
                              key not in stmt_parameters)

        # create a list of column assignment clauses as tuples
        values = []

        if stmt_parameters is not None:
            for k, v in stmt_parameters.iteritems():
                colkey = sql._column_as_key(k)
                if colkey is not None:
                    parameters.setdefault(colkey, v)
                else:
                    # a non-Column expression on the left side;
                    # add it to values() in an "as-is" state,
                    # coercing right side to bound param
                    if sql._is_literal(v):
                        v = self.process(sql.bindparam(None, v, type_=k.type))
                    else:
                        v = self.process(v.self_group())

                    values.append((k, v))

        need_pks = self.isinsert and \
                        not self.inline and \
                        not stmt._returning

        implicit_returning = need_pks and \
                                self.dialect.implicit_returning and \
                                stmt.table.implicit_returning

        postfetch_lastrowid = need_pks and self.dialect.postfetch_lastrowid

        check_columns = {}
        # special logic that only occurs for multi-table UPDATE
        # statements
        if extra_tables and stmt_parameters:
            normalized_params = dict(
                (sql._clause_element_as_expr(c), param)
                for c, param in stmt_parameters.items()
            )
            assert self.isupdate
            affected_tables = set()
            for t in extra_tables:
                for c in t.c:
                    if c in normalized_params:
                        affected_tables.add(t)
                        check_columns[c.key] = c
                        value = normalized_params[c]
                        if sql._is_literal(value):
                            value = self._create_crud_bind_param(
                                c, value, required=value is REQUIRED)
                        else:
                            self.postfetch.append(c)
                            value = self.process(value.self_group())
                        values.append((c, value))
            # determine tables which are actually
            # to be updated - process onupdate and
            # server_onupdate for these
            for t in affected_tables:
                for c in t.c:
                    if c in normalized_params:
                        continue
                    elif c.onupdate is not None and not c.onupdate.is_sequence:
                        if c.onupdate.is_clause_element:
                            values.append(
                                (c, self.process(c.onupdate.arg.self_group()))
                            )
                            self.postfetch.append(c)
                        else:
                            values.append(
                                (c, self._create_crud_bind_param(c, None))
                            )
                            self.prefetch.append(c)
                    elif c.server_onupdate is not None:
                        self.postfetch.append(c)

        # iterating through columns at the top to maintain ordering.
        # otherwise we might iterate through individual sets of
        # "defaults", "primary key cols", etc.
        for c in stmt.table.columns:
            if c.key in parameters and c.key not in check_columns:
                value = parameters.pop(c.key)
                if sql._is_literal(value):
                    value = self._create_crud_bind_param(
                                    c, value, required=value is REQUIRED,
                                    name=c.key
                                        if not stmt._has_multi_parameters
                                        else "%s_0" % c.key
                                    )
                elif c.primary_key and implicit_returning:
                    self.returning.append(c)
                    value = self.process(value.self_group())
                else:
                    self.postfetch.append(c)
                    value = self.process(value.self_group())
                values.append((c, value))

            elif self.isinsert:
                if c.primary_key and \
                    need_pks and \
                    (
                        implicit_returning or
                        not postfetch_lastrowid or
                        c is not stmt.table._autoincrement_column
                    ):

                    if implicit_returning:
                        if c.default is not None:
                            if c.default.is_sequence:
                                if self.dialect.supports_sequences and \
                                    (not c.default.optional or \
                                    not self.dialect.sequences_optional):
                                    proc = self.process(c.default)
                                    values.append((c, proc))
                                self.returning.append(c)
                            elif c.default.is_clause_element:
                                values.append(
                                    (c,
                                    self.process(c.default.arg.self_group()))
                                )
                                self.returning.append(c)
                            else:
                                values.append(
                                    (c, self._create_crud_bind_param(c, None))
                                )
                                self.prefetch.append(c)
                        else:
                            self.returning.append(c)
                    else:
                        if c.default is not None or \
                            c is stmt.table._autoincrement_column and (
                                self.dialect.supports_sequences or
                                self.dialect.preexecute_autoincrement_sequences
                            ):

                            values.append(
                                (c, self._create_crud_bind_param(c, None))
                            )

                            self.prefetch.append(c)

                elif c.default is not None:
                    if c.default.is_sequence:
                        if self.dialect.supports_sequences and \
                            (not c.default.optional or \
                            not self.dialect.sequences_optional):
                            proc = self.process(c.default)
                            values.append((c, proc))
                            if not c.primary_key:
                                self.postfetch.append(c)
                    elif c.default.is_clause_element:
                        values.append(
                            (c, self.process(c.default.arg.self_group()))
                        )

                        if not c.primary_key:
                            # dont add primary key column to postfetch
                            self.postfetch.append(c)
                    else:
                        values.append(
                            (c, self._create_crud_bind_param(c, None))
                        )
                        self.prefetch.append(c)
                elif c.server_default is not None:
                    if not c.primary_key:
                        self.postfetch.append(c)

            elif self.isupdate:
                if c.onupdate is not None and not c.onupdate.is_sequence:
                    if c.onupdate.is_clause_element:
                        values.append(
                            (c, self.process(c.onupdate.arg.self_group()))
                        )
                        self.postfetch.append(c)
                    else:
                        values.append(
                            (c, self._create_crud_bind_param(c, None))
                        )
                        self.prefetch.append(c)
                elif c.server_onupdate is not None:
                    self.postfetch.append(c)

        if parameters and stmt_parameters:
            check = set(parameters).intersection(
                sql._column_as_key(k) for k in stmt.parameters
            ).difference(check_columns)
            if check:
                raise exc.CompileError(
                    "Unconsumed column names: %s" %
                    (", ".join(check))
                )

        if stmt._has_multi_parameters:
            values_0 = values
            values = [values]

            values.extend(
                [
                        (
                            c,
                                self._create_crud_bind_param(
                                        c, row[c.key],
                                        name="%s_%d" % (c.key, i + 1)
                                )
                                if c.key in row else param
                        )
                        for (c, param) in values_0
                    ]
                    for i, row in enumerate(stmt.parameters[1:])
            )

        return values

    def visit_delete(self, delete_stmt, **kw):
        self.stack.append({'correlate_froms': set([delete_stmt.table]),
                            "iswrapper": False,
                            "asfrom_froms": set([delete_stmt.table])})
        self.isdelete = True

        text = "DELETE "

        if delete_stmt._prefixes:
            text += self._generate_prefixes(delete_stmt,
                                delete_stmt._prefixes, **kw)

        text += "FROM "
        table_text = delete_stmt.table._compiler_dispatch(self,
                                asfrom=True, iscrud=True)

        if delete_stmt._hints:
            dialect_hints = dict([
                (table, hint_text)
                for (table, dialect), hint_text in
                delete_stmt._hints.items()
                if dialect in ('*', self.dialect.name)
            ])
            if delete_stmt.table in dialect_hints:
                table_text = self.format_from_hint_text(
                                    table_text,
                                    delete_stmt.table,
                                    dialect_hints[delete_stmt.table],
                                    True
                                )

        else:
            dialect_hints = None

        text += table_text

        if delete_stmt._returning:
            self.returning = delete_stmt._returning
            if self.returning_precedes_values:
                text += " " + self.returning_clause(
                                delete_stmt, delete_stmt._returning)

        if delete_stmt._whereclause is not None:
            text += " WHERE "
            text += delete_stmt._whereclause._compiler_dispatch(self)

        if self.returning and not self.returning_precedes_values:
            text += " " + self.returning_clause(
                                delete_stmt, delete_stmt._returning)

        self.stack.pop(-1)

        return text

    def visit_savepoint(self, savepoint_stmt):
        return "SAVEPOINT %s" % self.preparer.format_savepoint(savepoint_stmt)

    def visit_rollback_to_savepoint(self, savepoint_stmt):
        return "ROLLBACK TO SAVEPOINT %s" % \
                self.preparer.format_savepoint(savepoint_stmt)

    def visit_release_savepoint(self, savepoint_stmt):
        return "RELEASE SAVEPOINT %s" % \
                self.preparer.format_savepoint(savepoint_stmt)


class DDLCompiler(engine.Compiled):

    @util.memoized_property
    def sql_compiler(self):
        return self.dialect.statement_compiler(self.dialect, None)

    @util.memoized_property
    def type_compiler(self):
        return self.dialect.type_compiler

    @property
    def preparer(self):
        return self.dialect.identifier_preparer

    def construct_params(self, params=None):
        return None

    def visit_ddl(self, ddl, **kwargs):
        # table events can substitute table and schema name
        context = ddl.context
        if isinstance(ddl.target, schema.Table):
            context = context.copy()

            preparer = self.dialect.identifier_preparer
            path = preparer.format_table_seq(ddl.target)
            if len(path) == 1:
                table, sch = path[0], ''
            else:
                table, sch = path[-1], path[0]

            context.setdefault('table', table)
            context.setdefault('schema', sch)
            context.setdefault('fullname', preparer.format_table(ddl.target))

        return self.sql_compiler.post_process_text(ddl.statement % context)

    def visit_create_schema(self, create):
        schema = self.preparer.format_schema(create.element, create.quote)
        return "CREATE SCHEMA " + schema

    def visit_drop_schema(self, drop):
        schema = self.preparer.format_schema(drop.element, drop.quote)
        text = "DROP SCHEMA " + schema
        if drop.cascade:
            text += " CASCADE"
        return text

    def visit_create_table(self, create):
        table = create.element
        preparer = self.dialect.identifier_preparer

        text = "\n" + " ".join(['CREATE'] + \
                                    table._prefixes + \
                                    ['TABLE',
                                     preparer.format_table(table),
                                     "("])
        separator = "\n"

        # if only one primary key, specify it along with the column
        first_pk = False
        for create_column in create.columns:
            column = create_column.element
            try:
                processed = self.process(create_column,
                                    first_pk=column.primary_key
                                    and not first_pk)
                if processed is not None:
                    text += separator
                    separator = ", \n"
                    text += "\t" + processed
                if column.primary_key:
                    first_pk = True
            except exc.CompileError, ce:
                # Py3K
                #raise exc.CompileError("(in table '%s', column '%s'): %s"
                #                             % (
                #                                table.description,
                #                                column.name,
                #                                ce.args[0]
                #                            )) from ce
                # Py2K
                raise exc.CompileError("(in table '%s', column '%s'): %s"
                                            % (
                                                table.description,
                                                column.name,
                                                ce.args[0]
                                            )), None, sys.exc_info()[2]
                # end Py2K

        const = self.create_table_constraints(table)
        if const:
            text += ", \n\t" + const

        text += "\n)%s\n\n" % self.post_create_table(table)
        return text

    def visit_create_column(self, create, first_pk=False):
        column = create.element

        if column.system:
            return None

        text = self.get_column_specification(
                        column,
                        first_pk=first_pk
                    )
        const = " ".join(self.process(constraint) \
                        for constraint in column.constraints)
        if const:
            text += " " + const

        return text

    def create_table_constraints(self, table):

        # On some DB order is significant: visit PK first, then the
        # other constraints (engine.ReflectionTest.testbasic failed on FB2)
        constraints = []
        if table.primary_key:
            constraints.append(table.primary_key)

        constraints.extend([c for c in table._sorted_constraints
                                if c is not table.primary_key])

        return ", \n\t".join(p for p in
                        (self.process(constraint)
                        for constraint in constraints
                        if (
                            constraint._create_rule is None or
                            constraint._create_rule(self))
                        and (
                            not self.dialect.supports_alter or
                            not getattr(constraint, 'use_alter', False)
                        )) if p is not None
                )

    def visit_drop_table(self, drop):
        return "\nDROP TABLE " + self.preparer.format_table(drop.element)

    def visit_drop_view(self, drop):
        return "\nDROP VIEW " + self.preparer.format_table(drop.element)


    def _verify_index_table(self, index):
        if index.table is None:
            raise exc.CompileError("Index '%s' is not associated "
                            "with any table." % index.name)


    def visit_create_index(self, create, include_schema=False,
                                include_table_schema=True):
        index = create.element
        self._verify_index_table(index)
        preparer = self.preparer
        text = "CREATE "
        if index.unique:
            text += "UNIQUE "
        text += "INDEX %s ON %s (%s)" \
                    % (
                        self._prepared_index_name(index,
                                include_schema=include_schema),
                       preparer.format_table(index.table,
                                    use_schema=include_table_schema),
                       ', '.join(
                            self.sql_compiler.process(expr,
                                include_table=False, literal_binds=True) for
                                expr in index.expressions)
                        )
        return text

    def visit_drop_index(self, drop):
        index = drop.element
        return "\nDROP INDEX " + self._prepared_index_name(index,
                                        include_schema=True)

    def _prepared_index_name(self, index, include_schema=False):
        if include_schema and index.table is not None and index.table.schema:
            schema = index.table.schema
            schema_name = self.preparer.quote_schema(schema,
                                index.table.quote_schema)
        else:
            schema_name = None

        ident = index.name
        if isinstance(ident, sql._truncated_label):
            max_ = self.dialect.max_index_name_length or \
                        self.dialect.max_identifier_length
            if len(ident) > max_:
                ident = ident[0:max_ - 8] + \
                                "_" + util.md5_hex(ident)[-4:]
        else:
            self.dialect.validate_identifier(ident)

        index_name = self.preparer.quote(
                                    ident,
                                    index.quote)

        if schema_name:
            index_name = schema_name + "." + index_name
        return index_name

    def visit_add_constraint(self, create):
        return "ALTER TABLE %s ADD %s" % (
            self.preparer.format_table(create.element.table),
            self.process(create.element)
        )

    def visit_create_sequence(self, create):
        text = "CREATE SEQUENCE %s" % \
                self.preparer.format_sequence(create.element)
        if create.element.increment is not None:
            text += " INCREMENT BY %d" % create.element.increment
        if create.element.start is not None:
            text += " START WITH %d" % create.element.start
        return text

    def visit_drop_sequence(self, drop):
        return "DROP SEQUENCE %s" % \
                self.preparer.format_sequence(drop.element)

    def visit_drop_constraint(self, drop):
        return "ALTER TABLE %s DROP CONSTRAINT %s%s" % (
            self.preparer.format_table(drop.element.table),
            self.preparer.format_constraint(drop.element),
            drop.cascade and " CASCADE" or ""
        )

    def get_column_specification(self, column, **kwargs):
        colspec = self.preparer.format_column(column) + " " + \
                        self.dialect.type_compiler.process(column.type)
        default = self.get_column_default_string(column)
        if default is not None:
            colspec += " DEFAULT " + default

        if not column.nullable:
            colspec += " NOT NULL"
        return colspec

    def post_create_table(self, table):
        return ''

    def get_column_default_string(self, column):
        if isinstance(column.server_default, schema.DefaultClause):
            if isinstance(column.server_default.arg, basestring):
                return "'%s'" % column.server_default.arg
            else:
                return self.sql_compiler.process(column.server_default.arg)
        else:
            return None

    def visit_check_constraint(self, constraint):
        text = ""
        if constraint.name is not None:
            text += "CONSTRAINT %s " % \
                        self.preparer.format_constraint(constraint)
        text += "CHECK (%s)" % self.sql_compiler.process(constraint.sqltext,
                                                            include_table=False,
                                                            literal_binds=True)
        text += self.define_constraint_deferrability(constraint)
        return text

    def visit_column_check_constraint(self, constraint):
        text = ""
        if constraint.name is not None:
            text += "CONSTRAINT %s " % \
                        self.preparer.format_constraint(constraint)
        text += "CHECK (%s)" % constraint.sqltext
        text += self.define_constraint_deferrability(constraint)
        return text

    def visit_primary_key_constraint(self, constraint):
        if len(constraint) == 0:
            return ''
        text = ""
        if constraint.name is not None:
            text += "CONSTRAINT %s " % \
                    self.preparer.format_constraint(constraint)
        text += "PRIMARY KEY "
        text += "(%s)" % ', '.join(self.preparer.quote(c.name, c.quote)
                                       for c in constraint)
        text += self.define_constraint_deferrability(constraint)
        return text

    def visit_foreign_key_constraint(self, constraint):
        preparer = self.dialect.identifier_preparer
        text = ""
        if constraint.name is not None:
            text += "CONSTRAINT %s " % \
                        preparer.format_constraint(constraint)
        remote_table = list(constraint._elements.values())[0].column.table
        text += "FOREIGN KEY(%s) REFERENCES %s (%s)" % (
            ', '.join(preparer.quote(f.parent.name, f.parent.quote)
                      for f in constraint._elements.values()),
            self.define_constraint_remote_table(
                            constraint, remote_table, preparer),
            ', '.join(preparer.quote(f.column.name, f.column.quote)
                      for f in constraint._elements.values())
        )
        text += self.define_constraint_match(constraint)
        text += self.define_constraint_cascades(constraint)
        text += self.define_constraint_deferrability(constraint)
        return text

    def define_constraint_remote_table(self, constraint, table, preparer):
        """Format the remote table clause of a CREATE CONSTRAINT clause."""

        return preparer.format_table(table)

    def visit_unique_constraint(self, constraint):
        text = ""
        if constraint.name is not None:
            text += "CONSTRAINT %s " % \
                    self.preparer.format_constraint(constraint)
        text += "UNIQUE (%s)" % (
                    ', '.join(self.preparer.quote(c.name, c.quote)
                            for c in constraint))
        text += self.define_constraint_deferrability(constraint)
        return text

    def define_constraint_cascades(self, constraint):
        text = ""
        if constraint.ondelete is not None:
            text += " ON DELETE %s" % constraint.ondelete
        if constraint.onupdate is not None:
            text += " ON UPDATE %s" % constraint.onupdate
        return text

    def define_constraint_deferrability(self, constraint):
        text = ""
        if constraint.deferrable is not None:
            if constraint.deferrable:
                text += " DEFERRABLE"
            else:
                text += " NOT DEFERRABLE"
        if constraint.initially is not None:
            text += " INITIALLY %s" % constraint.initially
        return text

    def define_constraint_match(self, constraint):
        text = ""
        if constraint.match is not None:
            text += " MATCH %s" % constraint.match
        return text


class GenericTypeCompiler(engine.TypeCompiler):

    def visit_FLOAT(self, type_):
        return "FLOAT"

    def visit_REAL(self, type_):
        return "REAL"

    def visit_NUMERIC(self, type_):
        if type_.precision is None:
            return "NUMERIC"
        elif type_.scale is None:
            return "NUMERIC(%(precision)s)" % \
                        {'precision': type_.precision}
        else:
            return "NUMERIC(%(precision)s, %(scale)s)" % \
                        {'precision': type_.precision,
                        'scale': type_.scale}

    def visit_DECIMAL(self, type_):
        if type_.precision is None:
            return "DECIMAL"
        elif type_.scale is None:
            return "DECIMAL(%(precision)s)" % \
                        {'precision': type_.precision}
        else:
            return "DECIMAL(%(precision)s, %(scale)s)" % \
                        {'precision': type_.precision,
                        'scale': type_.scale}

    def visit_INTEGER(self, type_):
        return "INTEGER"

    def visit_SMALLINT(self, type_):
        return "SMALLINT"

    def visit_BIGINT(self, type_):
        return "BIGINT"

    def visit_TIMESTAMP(self, type_):
        return 'TIMESTAMP'

    def visit_DATETIME(self, type_):
        return "DATETIME"

    def visit_DATE(self, type_):
        return "DATE"

    def visit_TIME(self, type_):
        return "TIME"

    def visit_CLOB(self, type_):
        return "CLOB"

    def visit_NCLOB(self, type_):
        return "NCLOB"

    def _render_string_type(self, type_, name):

        text = name
        if type_.length:
            text += "(%d)" % type_.length
        if type_.collation:
            text += ' COLLATE "%s"' % type_.collation
        return text

    def visit_CHAR(self, type_):
        return self._render_string_type(type_, "CHAR")

    def visit_NCHAR(self, type_):
        return self._render_string_type(type_, "NCHAR")

    def visit_VARCHAR(self, type_):
        return self._render_string_type(type_, "VARCHAR")

    def visit_NVARCHAR(self, type_):
        return self._render_string_type(type_, "NVARCHAR")

    def visit_TEXT(self, type_):
        return self._render_string_type(type_, "TEXT")

    def visit_BLOB(self, type_):
        return "BLOB"

    def visit_BINARY(self, type_):
        return "BINARY" + (type_.length and "(%d)" % type_.length or "")

    def visit_VARBINARY(self, type_):
        return "VARBINARY" + (type_.length and "(%d)" % type_.length or "")

    def visit_BOOLEAN(self, type_):
        return "BOOLEAN"

    def visit_large_binary(self, type_):
        return self.visit_BLOB(type_)

    def visit_boolean(self, type_):
        return self.visit_BOOLEAN(type_)

    def visit_time(self, type_):
        return self.visit_TIME(type_)

    def visit_datetime(self, type_):
        return self.visit_DATETIME(type_)

    def visit_date(self, type_):
        return self.visit_DATE(type_)

    def visit_big_integer(self, type_):
        return self.visit_BIGINT(type_)

    def visit_small_integer(self, type_):
        return self.visit_SMALLINT(type_)

    def visit_integer(self, type_):
        return self.visit_INTEGER(type_)

    def visit_real(self, type_):
        return self.visit_REAL(type_)

    def visit_float(self, type_):
        return self.visit_FLOAT(type_)

    def visit_numeric(self, type_):
        return self.visit_NUMERIC(type_)

    def visit_string(self, type_):
        return self.visit_VARCHAR(type_)

    def visit_unicode(self, type_):
        return self.visit_VARCHAR(type_)

    def visit_text(self, type_):
        return self.visit_TEXT(type_)

    def visit_unicode_text(self, type_):
        return self.visit_TEXT(type_)

    def visit_enum(self, type_):
        return self.visit_VARCHAR(type_)

    def visit_null(self, type_):
        raise NotImplementedError("Can't generate DDL for the null type")

    def visit_type_decorator(self, type_):
        return self.process(type_.type_engine(self.dialect))

    def visit_user_defined(self, type_):
        return type_.get_col_spec()


class IdentifierPreparer(object):
    """Handle quoting and case-folding of identifiers based on options."""

    reserved_words = RESERVED_WORDS

    legal_characters = LEGAL_CHARACTERS

    illegal_initial_characters = ILLEGAL_INITIAL_CHARACTERS

    def __init__(self, dialect, initial_quote='"',
                    final_quote=None, escape_quote='"', omit_schema=False):
        """Construct a new ``IdentifierPreparer`` object.

        initial_quote
          Character that begins a delimited identifier.

        final_quote
          Character that ends a delimited identifier. Defaults to
          `initial_quote`.

        omit_schema
          Prevent prepending schema name. Useful for databases that do
          not support schemae.
        """

        self.dialect = dialect
        self.initial_quote = initial_quote
        self.final_quote = final_quote or self.initial_quote
        self.escape_quote = escape_quote
        self.escape_to_quote = self.escape_quote * 2
        self.omit_schema = omit_schema
        self._strings = {}

    def _escape_identifier(self, value):
        """Escape an identifier.

        Subclasses should override this to provide database-dependent
        escaping behavior.
        """

        return value.replace(self.escape_quote, self.escape_to_quote)

    def _unescape_identifier(self, value):
        """Canonicalize an escaped identifier.

        Subclasses should override this to provide database-dependent
        unescaping behavior that reverses _escape_identifier.
        """

        return value.replace(self.escape_to_quote, self.escape_quote)

    def quote_identifier(self, value):
        """Quote an identifier.

        Subclasses should override this to provide database-dependent
        quoting behavior.
        """

        return self.initial_quote + \
                    self._escape_identifier(value) + \
                    self.final_quote

    def _requires_quotes(self, value):
        """Return True if the given identifier requires quoting."""
        lc_value = value.lower()
        return (lc_value in self.reserved_words
                or value[0] in self.illegal_initial_characters
                or not self.legal_characters.match(unicode(value))
                or (lc_value != value))

    def quote_schema(self, schema, force):
        """Quote a schema.

        Subclasses should override this to provide database-dependent
        quoting behavior.
        """
        return self.quote(schema, force)

    def quote(self, ident, force):
        if force is None:
            if ident in self._strings:
                return self._strings[ident]
            else:
                if self._requires_quotes(ident):
                    self._strings[ident] = self.quote_identifier(ident)
                else:
                    self._strings[ident] = ident
                return self._strings[ident]
        elif force:
            return self.quote_identifier(ident)
        else:
            return ident

    def format_sequence(self, sequence, use_schema=True):
        name = self.quote(sequence.name, sequence.quote)
        if not self.omit_schema and use_schema and \
            sequence.schema is not None:
            name = self.quote_schema(sequence.schema, sequence.quote) + \
                        "." + name
        return name

    def format_label(self, label, name=None):
        return self.quote(name or label.name, label.quote)

    def format_alias(self, alias, name=None):
        return self.quote(name or alias.name, alias.quote)

    def format_savepoint(self, savepoint, name=None):
        return self.quote(name or savepoint.ident, savepoint.quote)

    def format_constraint(self, constraint):
        return self.quote(constraint.name, constraint.quote)

    def format_table(self, table, use_schema=True, name=None):
        """Prepare a quoted table and schema name."""

        if name is None:
            name = table.name
        result = self.quote(name, table.quote)
        if not self.omit_schema and use_schema \
            and getattr(table, "schema", None):
            result = self.quote_schema(table.schema, table.quote_schema) + \
                                "." + result
        return result

    def format_schema(self, name, quote):
        """Prepare a quoted schema name."""

        return self.quote(name, quote)

    def format_column(self, column, use_table=False,
                            name=None, table_name=None):
        """Prepare a quoted column name."""

        if name is None:
            name = column.name
        if not getattr(column, 'is_literal', False):
            if use_table:
                return self.format_table(
                            column.table, use_schema=False,
                            name=table_name) + "." + \
                            self.quote(name, column.quote)
            else:
                return self.quote(name, column.quote)
        else:
            # literal textual elements get stuck into ColumnClause a lot,
            # which shouldn't get quoted

            if use_table:
                return self.format_table(column.table,
                        use_schema=False, name=table_name) + '.' + name
            else:
                return name

    def format_table_seq(self, table, use_schema=True):
        """Format table name and schema as a tuple."""

        # Dialects with more levels in their fully qualified references
        # ('database', 'owner', etc.) could override this and return
        # a longer sequence.

        if not self.omit_schema and use_schema and \
                getattr(table, 'schema', None):
            return (self.quote_schema(table.schema, table.quote_schema),
                    self.format_table(table, use_schema=False))
        else:
            return (self.format_table(table, use_schema=False), )

    @util.memoized_property
    def _r_identifiers(self):
        initial, final, escaped_final = \
                 [re.escape(s) for s in
                  (self.initial_quote, self.final_quote,
                   self._escape_identifier(self.final_quote))]
        r = re.compile(
            r'(?:'
            r'(?:%(initial)s((?:%(escaped)s|[^%(final)s])+)%(final)s'
            r'|([^\.]+))(?=\.|$))+' %
            {'initial': initial,
             'final': final,
             'escaped': escaped_final})
        return r

    def unformat_identifiers(self, identifiers):
        """Unpack 'schema.table.column'-like strings into components."""

        r = self._r_identifiers
        return [self._unescape_identifier(i)
                for i in [a or b for a, b in r.findall(identifiers)]]
