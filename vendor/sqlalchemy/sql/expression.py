# sql/expression.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Defines the base components of SQL expression trees.

All components are derived from a common base class
:class:`.ClauseElement`.  Common behaviors are organized
based on class hierarchies, in some cases via mixins.

All object construction from this package occurs via functions which
in some cases will construct composite :class:`.ClauseElement` structures
together, and in other cases simply return a single :class:`.ClauseElement`
constructed directly.  The function interface affords a more "DSL-ish"
feel to constructing SQL expressions and also allows future class
reorganizations.

Even though classes are not constructed directly from the outside,
most classes which have additional public methods are considered to be
public (i.e. have no leading underscore).  Other classes which are
"semi-public" are marked with a single leading underscore; these
classes usually have few or no public methods and are less guaranteed
to stay the same in future releases.

"""


import itertools
import re
from operator import attrgetter

from .. import util, exc, inspection
from . import operators
from .operators import ColumnOperators
from .visitors import Visitable, cloned_traverse
import operator

functions = util.importlater("sqlalchemy.sql", "functions")
sqlutil = util.importlater("sqlalchemy.sql", "util")
sqltypes = util.importlater("sqlalchemy", "types")
default = util.importlater("sqlalchemy.engine", "default")

__all__ = [
    'Alias', 'ClauseElement', 'ColumnCollection', 'ColumnElement',
    'CompoundSelect', 'Delete', 'FromClause', 'Insert', 'Join', 'Select',
    'Selectable', 'TableClause', 'Update', 'alias', 'and_', 'asc', 'between',
    'bindparam', 'case', 'cast', 'column', 'delete', 'desc', 'distinct',
    'except_', 'except_all', 'exists', 'extract', 'func', 'modifier',
    'collate', 'insert', 'intersect', 'intersect_all', 'join', 'label',
    'literal', 'literal_column', 'not_', 'null', 'nullsfirst', 'nullslast',
    'or_', 'outparam', 'outerjoin', 'over', 'select', 'subquery',
    'table', 'text',
    'tuple_', 'type_coerce', 'union', 'union_all', 'update', ]

PARSE_AUTOCOMMIT = util.symbol('PARSE_AUTOCOMMIT')
NO_ARG = util.symbol('NO_ARG')


def nullsfirst(column):
    """Return a NULLS FIRST ``ORDER BY`` clause element.

    e.g.::

      someselect.order_by(desc(table1.mycol).nullsfirst())

    produces::

      ORDER BY mycol DESC NULLS FIRST

    """
    return UnaryExpression(column, modifier=operators.nullsfirst_op)


def nullslast(column):
    """Return a NULLS LAST ``ORDER BY`` clause element.

    e.g.::

      someselect.order_by(desc(table1.mycol).nullslast())

    produces::

        ORDER BY mycol DESC NULLS LAST

    """
    return UnaryExpression(column, modifier=operators.nullslast_op)


def desc(column):
    """Return a descending ``ORDER BY`` clause element.

    e.g.::

      someselect.order_by(desc(table1.mycol))

    produces::

        ORDER BY mycol DESC

    """
    return UnaryExpression(column, modifier=operators.desc_op)


def asc(column):
    """Return an ascending ``ORDER BY`` clause element.

    e.g.::

      someselect.order_by(asc(table1.mycol))

    produces::

      ORDER BY mycol ASC

    """
    return UnaryExpression(column, modifier=operators.asc_op)


def outerjoin(left, right, onclause=None):
    """Return an ``OUTER JOIN`` clause element.

    The returned object is an instance of :class:`.Join`.

    Similar functionality is also available via the
    :meth:`~.FromClause.outerjoin()` method on any
    :class:`.FromClause`.

    :param left: The left side of the join.

    :param right: The right side of the join.

    :param onclause:  Optional criterion for the ``ON`` clause, is
      derived from foreign key relationships established between
      left and right otherwise.

    To chain joins together, use the :meth:`.FromClause.join` or
    :meth:`.FromClause.outerjoin` methods on the resulting
    :class:`.Join` object.

    """
    return Join(left, right, onclause, isouter=True)


def join(left, right, onclause=None, isouter=False):
    """Return a ``JOIN`` clause element (regular inner join).

    The returned object is an instance of :class:`.Join`.

    Similar functionality is also available via the
    :meth:`~.FromClause.join()` method on any
    :class:`.FromClause`.

    :param left: The left side of the join.

    :param right: The right side of the join.

    :param onclause:  Optional criterion for the ``ON`` clause, is
      derived from foreign key relationships established between
      left and right otherwise.

    To chain joins together, use the :meth:`.FromClause.join` or
    :meth:`.FromClause.outerjoin` methods on the resulting
    :class:`.Join` object.


    """
    return Join(left, right, onclause, isouter)


def select(columns=None, whereclause=None, from_obj=[], **kwargs):
    """Returns a ``SELECT`` clause element.

    Similar functionality is also available via the :func:`select()`
    method on any :class:`.FromClause`.

    The returned object is an instance of :class:`.Select`.

    All arguments which accept :class:`.ClauseElement` arguments also accept
    string arguments, which will be converted as appropriate into
    either :func:`text()` or :func:`literal_column()` constructs.

    .. seealso::

        :ref:`coretutorial_selecting` - Core Tutorial description of
        :func:`.select`.

    :param columns:
      A list of :class:`.ClauseElement` objects, typically
      :class:`.ColumnElement` objects or subclasses, which will form the
      columns clause of the resulting statement. For all members which are
      instances of :class:`.Selectable`, the individual :class:`.ColumnElement`
      members of the :class:`.Selectable` will be added individually to the
      columns clause. For example, specifying a
      :class:`~sqlalchemy.schema.Table` instance will result in all the
      contained :class:`~sqlalchemy.schema.Column` objects within to be added
      to the columns clause.

      This argument is not present on the form of :func:`select()`
      available on :class:`~sqlalchemy.schema.Table`.

    :param whereclause:
      A :class:`.ClauseElement` expression which will be used to form the
      ``WHERE`` clause.

    :param from_obj:
      A list of :class:`.ClauseElement` objects which will be added to the
      ``FROM`` clause of the resulting statement. Note that "from" objects are
      automatically located within the columns and whereclause ClauseElements.
      Use this parameter to explicitly specify "from" objects which are not
      automatically locatable. This could include
      :class:`~sqlalchemy.schema.Table` objects that aren't otherwise present,
      or :class:`.Join` objects whose presence will supercede that of the
      :class:`~sqlalchemy.schema.Table` objects already located in the other
      clauses.

    :param autocommit:
      Deprecated.  Use .execution_options(autocommit=<True|False>)
      to set the autocommit option.

    :param bind=None:
      an :class:`~.base.Engine` or :class:`~.base.Connection` instance
      to which the
      resulting :class:`.Select` object will be bound.  The :class:`.Select`
      object will otherwise automatically bind to whatever
      :class:`~.base.Connectable` instances can be located within its contained
      :class:`.ClauseElement` members.

    :param correlate=True:
      indicates that this :class:`.Select` object should have its
      contained :class:`.FromClause` elements "correlated" to an enclosing
      :class:`.Select` object.  This means that any :class:`.ClauseElement`
      instance within the "froms" collection of this :class:`.Select`
      which is also present in the "froms" collection of an
      enclosing select will not be rendered in the ``FROM`` clause
      of this select statement.

    :param distinct=False:
      when ``True``, applies a ``DISTINCT`` qualifier to the columns
      clause of the resulting statement.

      The boolean argument may also be a column expression or list
      of column expressions - this is a special calling form which
      is understood by the Postgresql dialect to render the
      ``DISTINCT ON (<columns>)`` syntax.

      ``distinct`` is also available via the :meth:`~.Select.distinct`
      generative method.

    :param for_update=False:
      when ``True``, applies ``FOR UPDATE`` to the end of the
      resulting statement.

      Certain database dialects also support
      alternate values for this parameter:

      * With the MySQL dialect, the value ``"read"`` translates to
        ``LOCK IN SHARE MODE``.
      * With the Oracle and Postgresql dialects, the value ``"nowait"``
        translates to ``FOR UPDATE NOWAIT``.
      * With the Postgresql dialect, the values "read" and ``"read_nowait"``
        translate to ``FOR SHARE`` and ``FOR SHARE NOWAIT``, respectively.

        .. versionadded:: 0.7.7

    :param group_by:
      a list of :class:`.ClauseElement` objects which will comprise the
      ``GROUP BY`` clause of the resulting select.

    :param having:
      a :class:`.ClauseElement` that will comprise the ``HAVING`` clause
      of the resulting select when ``GROUP BY`` is used.

    :param limit=None:
      a numerical value which usually compiles to a ``LIMIT``
      expression in the resulting select.  Databases that don't
      support ``LIMIT`` will attempt to provide similar
      functionality.

    :param offset=None:
      a numeric value which usually compiles to an ``OFFSET``
      expression in the resulting select.  Databases that don't
      support ``OFFSET`` will attempt to provide similar
      functionality.

    :param order_by:
      a scalar or list of :class:`.ClauseElement` objects which will
      comprise the ``ORDER BY`` clause of the resulting select.

    :param use_labels=False:
      when ``True``, the statement will be generated using labels
      for each column in the columns clause, which qualify each
      column with its parent table's (or aliases) name so that name
      conflicts between columns in different tables don't occur.
      The format of the label is <tablename>_<column>.  The "c"
      collection of the resulting :class:`.Select` object will use these
      names as well for targeting column members.

      use_labels is also available via the :meth:`~.SelectBase.apply_labels`
      generative method.

    """
    return Select(columns, whereclause=whereclause, from_obj=from_obj,
                  **kwargs)


def subquery(alias, *args, **kwargs):
    """Return an :class:`.Alias` object derived
    from a :class:`.Select`.

    name
      alias name

    \*args, \**kwargs

      all other arguments are delivered to the
      :func:`select` function.

    """
    return Select(*args, **kwargs).alias(alias)


def insert(table, values=None, inline=False, **kwargs):
    """Represent an ``INSERT`` statement via the :class:`.Insert` SQL
    construct.

    Similar functionality is available via the
    :meth:`~.TableClause.insert` method on
    :class:`~.schema.Table`.


    :param table: :class:`.TableClause` which is the subject of the insert.

    :param values: collection of values to be inserted; see
     :meth:`.Insert.values` for a description of allowed formats here.
     Can be omitted entirely; a :class:`.Insert` construct will also
     dynamically render the VALUES clause at execution time based on
     the parameters passed to :meth:`.Connection.execute`.

    :param inline: if True, SQL defaults will be compiled 'inline' into the
      statement and not pre-executed.

    If both `values` and compile-time bind parameters are present, the
    compile-time bind parameters override the information specified
    within `values` on a per-key basis.

    The keys within `values` can be either :class:`~sqlalchemy.schema.Column`
    objects or their string identifiers. Each key may reference one of:

    * a literal data value (i.e. string, number, etc.);
    * a Column object;
    * a SELECT statement.

    If a ``SELECT`` statement is specified which references this
    ``INSERT`` statement's table, the statement will be correlated
    against the ``INSERT`` statement.

    .. seealso::

        :ref:`coretutorial_insert_expressions` - SQL Expression Tutorial

        :ref:`inserts_and_updates` - SQL Expression Tutorial

    """
    return Insert(table, values, inline=inline, **kwargs)


def update(table, whereclause=None, values=None, inline=False, **kwargs):
    """Represent an ``UPDATE`` statement via the :class:`.Update` SQL
    construct.

    E.g.::

        from sqlalchemy import update

        stmt = update(users).where(users.c.id==5).\\
                values(name='user #5')

    Similar functionality is available via the
    :meth:`~.TableClause.update` method on
    :class:`.Table`::


        stmt = users.update().\\
                    where(users.c.id==5).\\
                    values(name='user #5')

    :param table: A :class:`.Table` object representing the database
     table to be updated.

    :param whereclause: Optional SQL expression describing the ``WHERE``
     condition of the ``UPDATE`` statement.   Modern applications
     may prefer to use the generative :meth:`~Update.where()`
     method to specify the ``WHERE`` clause.

     The WHERE clause can refer to multiple tables.
     For databases which support this, an ``UPDATE FROM`` clause will
     be generated, or on MySQL, a multi-table update.  The statement
     will fail on databases that don't have support for multi-table
     update statements.  A SQL-standard method of referring to
     additional tables in the WHERE clause is to use a correlated
     subquery::

        users.update().values(name='ed').where(
                users.c.name==select([addresses.c.email_address]).\\
                            where(addresses.c.user_id==users.c.id).\\
                            as_scalar()
                )

     .. versionchanged:: 0.7.4
         The WHERE clause can refer to multiple tables.

    :param values:
      Optional dictionary which specifies the ``SET`` conditions of the
      ``UPDATE``.  If left as ``None``, the ``SET``
      conditions are determined from those parameters passed to the
      statement during the execution and/or compilation of the
      statement.   When compiled standalone without any parameters,
      the ``SET`` clause generates for all columns.

      Modern applications may prefer to use the generative
      :meth:`.Update.values` method to set the values of the
      UPDATE statement.

    :param inline:
      if True, SQL defaults present on :class:`.Column` objects via
      the ``default`` keyword will be compiled 'inline' into the statement
      and not pre-executed.  This means that their values will not
      be available in the dictionary returned from
      :meth:`.ResultProxy.last_updated_params`.

    If both ``values`` and compile-time bind parameters are present, the
    compile-time bind parameters override the information specified
    within ``values`` on a per-key basis.

    The keys within ``values`` can be either :class:`.Column`
    objects or their string identifiers (specifically the "key" of the
    :class:`.Column`, normally but not necessarily equivalent to
    its "name").  Normally, the
    :class:`.Column` objects used here are expected to be
    part of the target :class:`.Table` that is the table
    to be updated.  However when using MySQL, a multiple-table
    UPDATE statement can refer to columns from any of
    the tables referred to in the WHERE clause.

    The values referred to in ``values`` are typically:

    * a literal data value (i.e. string, number, etc.)
    * a SQL expression, such as a related :class:`.Column`,
      a scalar-returning :func:`.select` construct,
      etc.

    When combining :func:`.select` constructs within the values
    clause of an :func:`.update` construct,
    the subquery represented by the :func:`.select` should be
    *correlated* to the parent table, that is, providing criterion
    which links the table inside the subquery to the outer table
    being updated::

        users.update().values(
                name=select([addresses.c.email_address]).\\
                        where(addresses.c.user_id==users.c.id).\\
                        as_scalar()
            )

    .. seealso::

        :ref:`inserts_and_updates` - SQL Expression
        Language Tutorial


    """
    return Update(
            table,
            whereclause=whereclause,
            values=values,
            inline=inline,
            **kwargs)


def delete(table, whereclause=None, **kwargs):
    """Represent a ``DELETE`` statement via the :class:`.Delete` SQL
    construct.

    Similar functionality is available via the
    :meth:`~.TableClause.delete` method on
    :class:`~.schema.Table`.

    :param table: The table to be updated.

    :param whereclause: A :class:`.ClauseElement` describing the ``WHERE``
      condition of the ``UPDATE`` statement. Note that the
      :meth:`~Delete.where()` generative method may be used instead.

    .. seealso::

        :ref:`deletes` - SQL Expression Tutorial

    """
    return Delete(table, whereclause, **kwargs)


def and_(*clauses):
    """Join a list of clauses together using the ``AND`` operator.

    The ``&`` operator is also overloaded on all :class:`.ColumnElement`
    subclasses to produce the
    same result.

    """
    if len(clauses) == 1:
        return clauses[0]
    return BooleanClauseList(operator=operators.and_, *clauses)


def or_(*clauses):
    """Join a list of clauses together using the ``OR`` operator.

    The ``|`` operator is also overloaded on all
    :class:`.ColumnElement` subclasses to produce the
    same result.

    """
    if len(clauses) == 1:
        return clauses[0]
    return BooleanClauseList(operator=operators.or_, *clauses)


def not_(clause):
    """Return a negation of the given clause, i.e. ``NOT(clause)``.

    The ``~`` operator is also overloaded on all
    :class:`.ColumnElement` subclasses to produce the
    same result.

    """
    return operators.inv(_literal_as_binds(clause))


def distinct(expr):
    """Return a ``DISTINCT`` clause.

    e.g.::

        distinct(a)

    renders::

        DISTINCT a

    """
    expr = _literal_as_binds(expr)
    return UnaryExpression(expr,
                operator=operators.distinct_op, type_=expr.type)


def between(ctest, cleft, cright):
    """Return a ``BETWEEN`` predicate clause.

    Equivalent of SQL ``clausetest BETWEEN clauseleft AND clauseright``.

    The :func:`between()` method on all
    :class:`.ColumnElement` subclasses provides
    similar functionality.

    """
    ctest = _literal_as_binds(ctest)
    return ctest.between(cleft, cright)


def case(whens, value=None, else_=None):
    """Produce a ``CASE`` statement.

    whens
      A sequence of pairs, or alternatively a dict,
      to be translated into "WHEN / THEN" clauses.

    value
      Optional for simple case statements, produces
      a column expression as in "CASE <expr> WHEN ..."

    else\_
      Optional as well, for case defaults produces
      the "ELSE" portion of the "CASE" statement.

    The expressions used for THEN and ELSE,
    when specified as strings, will be interpreted
    as bound values. To specify textual SQL expressions
    for these, use the :func:`literal_column`
    construct.

    The expressions used for the WHEN criterion
    may only be literal strings when "value" is
    present, i.e. CASE table.somecol WHEN "x" THEN "y".
    Otherwise, literal strings are not accepted
    in this position, and either the text(<string>)
    or literal(<string>) constructs must be used to
    interpret raw string values.

    Usage examples::

      case([(orderline.c.qty > 100, item.c.specialprice),
            (orderline.c.qty > 10, item.c.bulkprice)
          ], else_=item.c.regularprice)
      case(value=emp.c.type, whens={
              'engineer': emp.c.salary * 1.1,
              'manager':  emp.c.salary * 3,
          })

    Using :func:`literal_column()`, to allow for databases that
    do not support bind parameters in the ``then`` clause.  The type
    can be specified which determines the type of the :func:`case()` construct
    overall::

        case([(orderline.c.qty > 100,
                literal_column("'greaterthan100'", String)),
              (orderline.c.qty > 10, literal_column("'greaterthan10'",
                String))
            ], else_=literal_column("'lethan10'", String))

    """

    return Case(whens, value=value, else_=else_)


def cast(clause, totype, **kwargs):
    """Return a ``CAST`` function.

    Equivalent of SQL ``CAST(clause AS totype)``.

    Use with a :class:`~sqlalchemy.types.TypeEngine` subclass, i.e::

      cast(table.c.unit_price * table.c.qty, Numeric(10,4))

    or::

      cast(table.c.timestamp, DATE)

    """
    return Cast(clause, totype, **kwargs)


def extract(field, expr):
    """Return the clause ``extract(field FROM expr)``."""

    return Extract(field, expr)


def collate(expression, collation):
    """Return the clause ``expression COLLATE collation``.

    e.g.::

        collate(mycolumn, 'utf8_bin')

    produces::

        mycolumn COLLATE utf8_bin

    """

    expr = _literal_as_binds(expression)
    return BinaryExpression(
        expr,
        _literal_as_text(collation),
        operators.collate, type_=expr.type)


def exists(*args, **kwargs):
    """Return an ``EXISTS`` clause as applied to a :class:`.Select` object.

    Calling styles are of the following forms::

        # use on an existing select()
        s = select([table.c.col1]).where(table.c.col2==5)
        s = exists(s)

        # construct a select() at once
        exists(['*'], **select_arguments).where(criterion)

        # columns argument is optional, generates "EXISTS (SELECT *)"
        # by default.
        exists().where(table.c.col2==5)

    """
    return Exists(*args, **kwargs)


def union(*selects, **kwargs):
    """Return a ``UNION`` of multiple selectables.

    The returned object is an instance of
    :class:`.CompoundSelect`.

    A similar :func:`union()` method is available on all
    :class:`.FromClause` subclasses.

    \*selects
      a list of :class:`.Select` instances.

    \**kwargs
       available keyword arguments are the same as those of
       :func:`select`.

    """
    return CompoundSelect(CompoundSelect.UNION, *selects, **kwargs)


def union_all(*selects, **kwargs):
    """Return a ``UNION ALL`` of multiple selectables.

    The returned object is an instance of
    :class:`.CompoundSelect`.

    A similar :func:`union_all()` method is available on all
    :class:`.FromClause` subclasses.

    \*selects
      a list of :class:`.Select` instances.

    \**kwargs
      available keyword arguments are the same as those of
      :func:`select`.

    """
    return CompoundSelect(CompoundSelect.UNION_ALL, *selects, **kwargs)


def except_(*selects, **kwargs):
    """Return an ``EXCEPT`` of multiple selectables.

    The returned object is an instance of
    :class:`.CompoundSelect`.

    \*selects
      a list of :class:`.Select` instances.

    \**kwargs
      available keyword arguments are the same as those of
      :func:`select`.

    """
    return CompoundSelect(CompoundSelect.EXCEPT, *selects, **kwargs)


def except_all(*selects, **kwargs):
    """Return an ``EXCEPT ALL`` of multiple selectables.

    The returned object is an instance of
    :class:`.CompoundSelect`.

    \*selects
      a list of :class:`.Select` instances.

    \**kwargs
      available keyword arguments are the same as those of
      :func:`select`.

    """
    return CompoundSelect(CompoundSelect.EXCEPT_ALL, *selects, **kwargs)


def intersect(*selects, **kwargs):
    """Return an ``INTERSECT`` of multiple selectables.

    The returned object is an instance of
    :class:`.CompoundSelect`.

    \*selects
      a list of :class:`.Select` instances.

    \**kwargs
      available keyword arguments are the same as those of
      :func:`select`.

    """
    return CompoundSelect(CompoundSelect.INTERSECT, *selects, **kwargs)


def intersect_all(*selects, **kwargs):
    """Return an ``INTERSECT ALL`` of multiple selectables.

    The returned object is an instance of
    :class:`.CompoundSelect`.

    \*selects
      a list of :class:`.Select` instances.

    \**kwargs
      available keyword arguments are the same as those of
      :func:`select`.

    """
    return CompoundSelect(CompoundSelect.INTERSECT_ALL, *selects, **kwargs)


def alias(selectable, name=None):
    """Return an :class:`.Alias` object.

    An :class:`.Alias` represents any :class:`.FromClause`
    with an alternate name assigned within SQL, typically using the ``AS``
    clause when generated, e.g. ``SELECT * FROM table AS aliasname``.

    Similar functionality is available via the
    :meth:`~.FromClause.alias` method
    available on all :class:`.FromClause` subclasses.

    When an :class:`.Alias` is created from a :class:`.Table` object,
    this has the effect of the table being rendered
    as ``tablename AS aliasname`` in a SELECT statement.

    For :func:`.select` objects, the effect is that of creating a named
    subquery, i.e. ``(select ...) AS aliasname``.

    The ``name`` parameter is optional, and provides the name
    to use in the rendered SQL.  If blank, an "anonymous" name
    will be deterministically generated at compile time.
    Deterministic means the name is guaranteed to be unique against
    other constructs used in the same statement, and will also be the
    same name for each successive compilation of the same statement
    object.

    :param selectable: any :class:`.FromClause` subclass,
        such as a table, select statement, etc.

    :param name: string name to be assigned as the alias.
        If ``None``, a name will be deterministically generated
        at compile time.

    """
    return Alias(selectable, name=name)


def literal(value, type_=None):
    """Return a literal clause, bound to a bind parameter.

    Literal clauses are created automatically when non- :class:`.ClauseElement`
    objects (such as strings, ints, dates, etc.) are used in a comparison
    operation with a :class:`.ColumnElement`
    subclass, such as a :class:`~sqlalchemy.schema.Column` object.
    Use this function to force the
    generation of a literal clause, which will be created as a
    :class:`BindParameter` with a bound value.

    :param value: the value to be bound. Can be any Python object supported by
        the underlying DB-API, or is translatable via the given type argument.

    :param type\_: an optional :class:`~sqlalchemy.types.TypeEngine` which
        will provide bind-parameter translation for this literal.

    """
    return BindParameter(None, value, type_=type_, unique=True)


def tuple_(*expr):
    """Return a SQL tuple.

    Main usage is to produce a composite IN construct::

        tuple_(table.c.col1, table.c.col2).in_(
            [(1, 2), (5, 12), (10, 19)]
        )

    .. warning::

        The composite IN construct is not supported by all backends,
        and is currently known to work on Postgresql and MySQL,
        but not SQLite.   Unsupported backends will raise
        a subclass of :class:`~sqlalchemy.exc.DBAPIError` when such
        an expression is invoked.

    """
    return Tuple(*expr)


def type_coerce(expr, type_):
    """Coerce the given expression into the given type,
    on the Python side only.

    :func:`.type_coerce` is roughly similar to :func:`.cast`, except no
    "CAST" expression is rendered - the given type is only applied towards
    expression typing and against received result values.

    e.g.::

        from sqlalchemy.types import TypeDecorator
        import uuid

        class AsGuid(TypeDecorator):
            impl = String

            def process_bind_param(self, value, dialect):
                if value is not None:
                    return str(value)
                else:
                    return None

            def process_result_value(self, value, dialect):
                if value is not None:
                    return uuid.UUID(value)
                else:
                    return None

        conn.execute(
            select([type_coerce(mytable.c.ident, AsGuid)]).\\
                    where(
                        type_coerce(mytable.c.ident, AsGuid) ==
                        uuid.uuid3(uuid.NAMESPACE_URL, 'bar')
                    )
        )

    """
    type_ = sqltypes.to_instance(type_)

    if hasattr(expr, '__clause_element__'):
        return type_coerce(expr.__clause_element__(), type_)
    elif isinstance(expr, BindParameter):
        bp = expr._clone()
        bp.type = type_
        return bp
    elif not isinstance(expr, Visitable):
        if expr is None:
            return null()
        else:
            return literal(expr, type_=type_)
    else:
        return Label(None, expr, type_=type_)


def label(name, obj):
    """Return a :class:`Label` object for the
    given :class:`.ColumnElement`.

    A label changes the name of an element in the columns clause of a
    ``SELECT`` statement, typically via the ``AS`` SQL keyword.

    This functionality is more conveniently available via the
    :func:`label()` method on :class:`.ColumnElement`.

    name
      label name

    obj
      a :class:`.ColumnElement`.

    """
    return Label(name, obj)


def column(text, type_=None):
    """Return a textual column clause, as would be in the columns clause of a
    ``SELECT`` statement.

    The object returned is an instance of :class:`.ColumnClause`, which
    represents the "syntactical" portion of the schema-level
    :class:`~sqlalchemy.schema.Column` object.  It is often used directly
    within :func:`~.expression.select` constructs or with lightweight
    :func:`~.expression.table` constructs.

    Note that the :func:`~.expression.column` function is not part of
    the ``sqlalchemy`` namespace.  It must be imported from the
    ``sql`` package::

        from sqlalchemy.sql import table, column

    :param text: the name of the column.  Quoting rules will be applied
      to the clause like any other column name. For textual column constructs
      that are not to be quoted, use the :func:`literal_column` function.

    :param type\_: an optional :class:`~sqlalchemy.types.TypeEngine` object
      which will provide result-set translation for this column.

    See :class:`.ColumnClause` for further examples.

    """
    return ColumnClause(text, type_=type_)


def literal_column(text, type_=None):
    """Return a textual column expression, as would be in the columns
    clause of a ``SELECT`` statement.

    The object returned supports further expressions in the same way as any
    other column object, including comparison, math and string operations.
    The type\_ parameter is important to determine proper expression behavior
    (such as, '+' means string concatenation or numerical addition based on
    the type).

    :param text: the text of the expression; can be any SQL expression.
      Quoting rules will not be applied. To specify a column-name expression
      which should be subject to quoting rules, use the :func:`column`
      function.

    :param type\_: an optional :class:`~sqlalchemy.types.TypeEngine`
      object which will
      provide result-set translation and additional expression semantics for
      this column. If left as None the type will be NullType.

    """
    return ColumnClause(text, type_=type_, is_literal=True)


def table(name, *columns):
    """Represent a textual table clause.

    The object returned is an instance of :class:`.TableClause`, which
    represents the "syntactical" portion of the schema-level
    :class:`~.schema.Table` object.
    It may be used to construct lightweight table constructs.

    Note that the :func:`~.expression.table` function is not part of
    the ``sqlalchemy`` namespace.  It must be imported from the
    ``sql`` package::

        from sqlalchemy.sql import table, column

    :param name: Name of the table.

    :param columns: A collection of :func:`~.expression.column` constructs.

    See :class:`.TableClause` for further examples.

    """
    return TableClause(name, *columns)


def bindparam(key, value=NO_ARG, type_=None, unique=False, required=NO_ARG,
                        quote=None, callable_=None):
    """Create a bind parameter clause with the given key.

        :param key:
          the key for this bind param.  Will be used in the generated
          SQL statement for dialects that use named parameters.  This
          value may be modified when part of a compilation operation,
          if other :class:`BindParameter` objects exist with the same
          key, or if its length is too long and truncation is
          required.

        :param value:
          Initial value for this bind param.  This value may be
          overridden by the dictionary of parameters sent to statement
          compilation/execution.

          Defaults to ``None``, however if neither ``value`` nor
          ``callable`` are passed explicitly, the ``required`` flag will be
          set to ``True`` which has the effect of requiring a value be present
          when the statement is actually executed.

          .. versionchanged:: 0.8 The ``required`` flag is set to ``True``
             automatically if ``value`` or ``callable`` is not passed.

        :param callable\_:
          A callable function that takes the place of "value".  The function
          will be called at statement execution time to determine the
          ultimate value.   Used for scenarios where the actual bind
          value cannot be determined at the point at which the clause
          construct is created, but embedded bind values are still desirable.

        :param type\_:
          A ``TypeEngine`` object that will be used to pre-process the
          value corresponding to this :class:`BindParameter` at
          execution time.

        :param unique:
          if True, the key name of this BindParamClause will be
          modified if another :class:`BindParameter` of the same name
          already has been located within the containing
          :class:`.ClauseElement`.

        :param required:
          If ``True``, a value is required at execution time.  If not passed,
          is set to ``True`` or ``False`` based on whether or not
          one of ``value`` or ``callable`` were passed..

          .. versionchanged:: 0.8 If the ``required`` flag is not specified,
             it will be set automatically to ``True`` or ``False`` depending
             on whether or not the ``value`` or ``callable`` parameters
             were specified.

        :param quote:
          True if this parameter name requires quoting and is not
          currently known as a SQLAlchemy reserved word; this currently
          only applies to the Oracle backend.

    """
    if isinstance(key, ColumnClause):
        type_ = key.type
        key = key.name
    if required is NO_ARG:
        required = (value is NO_ARG and callable_ is None)
    if value is NO_ARG:
        value = None
    return BindParameter(key, value, type_=type_,
                            callable_=callable_,
                            unique=unique, required=required,
                            quote=quote)


def outparam(key, type_=None):
    """Create an 'OUT' parameter for usage in functions (stored procedures),
    for databases which support them.

    The ``outparam`` can be used like a regular function parameter.
    The "output" value will be available from the
    :class:`~sqlalchemy.engine.ResultProxy` object via its ``out_parameters``
    attribute, which returns a dictionary containing the values.

    """
    return BindParameter(
                key, None, type_=type_, unique=False, isoutparam=True)


def text(text, bind=None, *args, **kwargs):
    """Create a SQL construct that is represented by a literal string.

    E.g.::

        t = text("SELECT * FROM users")
        result = connection.execute(t)

    The advantages :func:`text` provides over a plain string are
    backend-neutral support for bind parameters, per-statement
    execution options, as well as
    bind parameter and result-column typing behavior, allowing
    SQLAlchemy type constructs to play a role when executing
    a statement that is specified literally.

    Bind parameters are specified by name, using the format ``:name``.
    E.g.::

        t = text("SELECT * FROM users WHERE id=:user_id")
        result = connection.execute(t, user_id=12)

    To invoke SQLAlchemy typing logic for bind parameters, the
    ``bindparams`` list allows specification of :func:`bindparam`
    constructs which specify the type for a given name::

        t = text("SELECT id FROM users WHERE updated_at>:updated",
                    bindparams=[bindparam('updated', DateTime())]
                )

    Typing during result row processing is also an important concern.
    Result column types
    are specified using the ``typemap`` dictionary, where the keys
    match the names of columns.  These names are taken from what
    the DBAPI returns as ``cursor.description``::

        t = text("SELECT id, name FROM users",
                typemap={
                    'id':Integer,
                    'name':Unicode
                }
        )

    The :func:`text` construct is used internally for most cases when
    a literal string is specified for part of a larger query, such as
    within :func:`select()`, :func:`update()`,
    :func:`insert()` or :func:`delete()`.   In those cases, the same
    bind parameter syntax is applied::

        s = select([users.c.id, users.c.name]).where("id=:user_id")
        result = connection.execute(s, user_id=12)

    Using :func:`text` explicitly usually implies the construction
    of a full, standalone statement.   As such, SQLAlchemy refers
    to it as an :class:`.Executable` object, and it supports
    the :meth:`Executable.execution_options` method.  For example,
    a :func:`text` construct that should be subject to "autocommit"
    can be set explicitly so using the ``autocommit`` option::

        t = text("EXEC my_procedural_thing()").\\
                execution_options(autocommit=True)

    Note that SQLAlchemy's usual "autocommit" behavior applies to
    :func:`text` constructs - that is, statements which begin
    with a phrase such as ``INSERT``, ``UPDATE``, ``DELETE``,
    or a variety of other phrases specific to certain backends, will
    be eligible for autocommit if no transaction is in progress.

    :param text:
      the text of the SQL statement to be created.  use ``:<param>``
      to specify bind parameters; they will be compiled to their
      engine-specific format.

    :param autocommit:
      Deprecated.  Use .execution_options(autocommit=<True|False>)
      to set the autocommit option.

    :param bind:
      an optional connection or engine to be used for this text query.

    :param bindparams:
      a list of :func:`bindparam()` instances which can be used to define
      the types and/or initial values for the bind parameters within
      the textual statement; the keynames of the bindparams must match
      those within the text of the statement.  The types will be used
      for pre-processing on bind values.

    :param typemap:
      a dictionary mapping the names of columns represented in the
      columns clause of a ``SELECT`` statement  to type objects,
      which will be used to perform post-processing on columns within
      the result set.   This argument applies to any expression
      that returns result sets.

    """
    return TextClause(text, bind=bind, *args, **kwargs)


def over(func, partition_by=None, order_by=None):
    """Produce an OVER clause against a function.

    Used against aggregate or so-called "window" functions,
    for database backends that support window functions.

    E.g.::

        from sqlalchemy import over
        over(func.row_number(), order_by='x')

    Would produce "ROW_NUMBER() OVER(ORDER BY x)".

    :param func: a :class:`.FunctionElement` construct, typically
     generated by :data:`~.expression.func`.
    :param partition_by: a column element or string, or a list
     of such, that will be used as the PARTITION BY clause
     of the OVER construct.
    :param order_by: a column element or string, or a list
     of such, that will be used as the ORDER BY clause
     of the OVER construct.

    This function is also available from the :data:`~.expression.func`
    construct itself via the :meth:`.FunctionElement.over` method.

    .. versionadded:: 0.7

    """
    return Over(func, partition_by=partition_by, order_by=order_by)


def null():
    """Return a :class:`Null` object, which compiles to ``NULL``.

    """
    return Null()


def true():
    """Return a :class:`True_` object, which compiles to ``true``, or the
    boolean equivalent for the target dialect.

    """
    return True_()


def false():
    """Return a :class:`False_` object, which compiles to ``false``, or the
    boolean equivalent for the target dialect.

    """
    return False_()


class _FunctionGenerator(object):
    """Generate :class:`.Function` objects based on getattr calls."""

    def __init__(self, **opts):
        self.__names = []
        self.opts = opts

    def __getattr__(self, name):
        # passthru __ attributes; fixes pydoc
        if name.startswith('__'):
            try:
                return self.__dict__[name]
            except KeyError:
                raise AttributeError(name)

        elif name.endswith('_'):
            name = name[0:-1]
        f = _FunctionGenerator(**self.opts)
        f.__names = list(self.__names) + [name]
        return f

    def __call__(self, *c, **kwargs):
        o = self.opts.copy()
        o.update(kwargs)

        tokens = len(self.__names)

        if tokens == 2:
            package, fname = self.__names
        elif tokens == 1:
            package, fname = "_default", self.__names[0]
        else:
            package = None

        if package is not None and \
            package in functions._registry and \
            fname in functions._registry[package]:
            func = functions._registry[package][fname]
            return func(*c, **o)

        return Function(self.__names[-1],
                        packagenames=self.__names[0:-1], *c, **o)

# "func" global - i.e. func.count()
func = _FunctionGenerator()
"""Generate SQL function expressions.

   :data:`.func` is a special object instance which generates SQL
   functions based on name-based attributes, e.g.::

        >>> print func.count(1)
        count(:param_1)

   The element is a column-oriented SQL element like any other, and is
   used in that way::

        >>> print select([func.count(table.c.id)])
        SELECT count(sometable.id) FROM sometable

   Any name can be given to :data:`.func`. If the function name is unknown to
   SQLAlchemy, it will be rendered exactly as is. For common SQL functions
   which SQLAlchemy is aware of, the name may be interpreted as a *generic
   function* which will be compiled appropriately to the target database::

        >>> print func.current_timestamp()
        CURRENT_TIMESTAMP

   To call functions which are present in dot-separated packages,
   specify them in the same manner::

        >>> print func.stats.yield_curve(5, 10)
        stats.yield_curve(:yield_curve_1, :yield_curve_2)

   SQLAlchemy can be made aware of the return type of functions to enable
   type-specific lexical and result-based behavior. For example, to ensure
   that a string-based function returns a Unicode value and is similarly
   treated as a string in expressions, specify
   :class:`~sqlalchemy.types.Unicode` as the type:

        >>> print func.my_string(u'hi', type_=Unicode) + ' ' + \
        ... func.my_string(u'there', type_=Unicode)
        my_string(:my_string_1) || :my_string_2 || my_string(:my_string_3)

   The object returned by a :data:`.func` call is usually an instance of
   :class:`.Function`.
   This object meets the "column" interface, including comparison and labeling
   functions.  The object can also be passed the :meth:`~.Connectable.execute`
   method of a :class:`.Connection` or :class:`.Engine`, where it will be
   wrapped inside of a SELECT statement first::

        print connection.execute(func.current_timestamp()).scalar()

   In a few exception cases, the :data:`.func` accessor
   will redirect a name to a built-in expression such as :func:`.cast`
   or :func:`.extract`, as these names have well-known meaning
   but are not exactly the same as "functions" from a SQLAlchemy
   perspective.

   .. versionadded:: 0.8 :data:`.func` can return non-function expression
      constructs for common quasi-functional names like :func:`.cast`
      and :func:`.extract`.

   Functions which are interpreted as "generic" functions know how to
   calculate their return type automatically. For a listing of known generic
   functions, see :ref:`generic_functions`.

"""

# "modifier" global - i.e. modifier.distinct
# TODO: use UnaryExpression for this instead ?
modifier = _FunctionGenerator(group=False)


class _truncated_label(unicode):
    """A unicode subclass used to identify symbolic "
    "names that may require truncation."""

    def apply_map(self, map_):
        return self

# for backwards compatibility in case
# someone is re-implementing the
# _truncated_identifier() sequence in a custom
# compiler
_generated_label = _truncated_label


class _anonymous_label(_truncated_label):
    """A unicode subclass used to identify anonymously
    generated names."""

    def __add__(self, other):
        return _anonymous_label(
                    unicode(self) +
                    unicode(other))

    def __radd__(self, other):
        return _anonymous_label(
                    unicode(other) +
                    unicode(self))

    def apply_map(self, map_):
        return self % map_


def _as_truncated(value):
    """coerce the given value to :class:`._truncated_label`.

    Existing :class:`._truncated_label` and
    :class:`._anonymous_label` objects are passed
    unchanged.
    """

    if isinstance(value, _truncated_label):
        return value
    else:
        return _truncated_label(value)


def _string_or_unprintable(element):
    if isinstance(element, basestring):
        return element
    else:
        try:
            return str(element)
        except:
            return "unprintable element %r" % element


def _clone(element, **kw):
    return element._clone()


def _expand_cloned(elements):
    """expand the given set of ClauseElements to be the set of all 'cloned'
    predecessors.

    """
    return itertools.chain(*[x._cloned_set for x in elements])


def _select_iterables(elements):
    """expand tables into individual columns in the
    given list of column expressions.

    """
    return itertools.chain(*[c._select_iterable for c in elements])


def _cloned_intersection(a, b):
    """return the intersection of sets a and b, counting
    any overlap between 'cloned' predecessors.

    The returned set is in terms of the entities present within 'a'.

    """
    all_overlap = set(_expand_cloned(a)).intersection(_expand_cloned(b))
    return set(elem for elem in a
               if all_overlap.intersection(elem._cloned_set))

def _cloned_difference(a, b):
    all_overlap = set(_expand_cloned(a)).intersection(_expand_cloned(b))
    return set(elem for elem in a
                if not all_overlap.intersection(elem._cloned_set))

def _from_objects(*elements):
    return itertools.chain(*[element._from_objects for element in elements])


def _labeled(element):
    if not hasattr(element, 'name'):
        return element.label(None)
    else:
        return element


# there is some inconsistency here between the usage of
# inspect() vs. checking for Visitable and __clause_element__.
# Ideally all functions here would derive from inspect(),
# however the inspect() versions add significant callcount
# overhead for critical functions like _interpret_as_column_or_from().
# Generally, the column-based functions are more performance critical
# and are fine just checking for __clause_element__().  it's only
# _interpret_as_from() where we'd like to be able to receive ORM entities
# that have no defined namespace, hence inspect() is needed there.


def _column_as_key(element):
    if isinstance(element, basestring):
        return element
    if hasattr(element, '__clause_element__'):
        element = element.__clause_element__()
    try:
        return element.key
    except AttributeError:
        return None


def _clause_element_as_expr(element):
    if hasattr(element, '__clause_element__'):
        return element.__clause_element__()
    else:
        return element


def _literal_as_text(element):
    if isinstance(element, Visitable):
        return element
    elif hasattr(element, '__clause_element__'):
        return element.__clause_element__()
    elif isinstance(element, basestring):
        return TextClause(unicode(element))
    elif isinstance(element, (util.NoneType, bool)):
        return _const_expr(element)
    else:
        raise exc.ArgumentError(
            "SQL expression object or string expected."
        )


def _no_literals(element):
    if hasattr(element, '__clause_element__'):
        return element.__clause_element__()
    elif not isinstance(element, Visitable):
        raise exc.ArgumentError("Ambiguous literal: %r.  Use the 'text()' "
                                "function to indicate a SQL expression "
                                "literal, or 'literal()' to indicate a "
                                "bound value." % element)
    else:
        return element


def _is_literal(element):
    return not isinstance(element, Visitable) and \
            not hasattr(element, '__clause_element__')


def _only_column_elements_or_none(element, name):
    if element is None:
        return None
    else:
        return _only_column_elements(element, name)


def _only_column_elements(element, name):
    if hasattr(element, '__clause_element__'):
        element = element.__clause_element__()
    if not isinstance(element, ColumnElement):
        raise exc.ArgumentError(
                "Column-based expression object expected for argument "
                "'%s'; got: '%s', type %s" % (name, element, type(element)))
    return element


def _literal_as_binds(element, name=None, type_=None):
    if hasattr(element, '__clause_element__'):
        return element.__clause_element__()
    elif not isinstance(element, Visitable):
        if element is None:
            return null()
        else:
            return _BindParamClause(name, element, type_=type_, unique=True)
    else:
        return element


def _interpret_as_column_or_from(element):
    if isinstance(element, Visitable):
        return element
    elif hasattr(element, '__clause_element__'):
        return element.__clause_element__()

    insp = inspection.inspect(element, raiseerr=False)
    if insp is None:
        if isinstance(element, (util.NoneType, bool)):
            return _const_expr(element)
    elif hasattr(insp, "selectable"):
        return insp.selectable

    return literal_column(str(element))


def _interpret_as_from(element):
    insp = inspection.inspect(element, raiseerr=False)
    if insp is None:
        if isinstance(element, basestring):
            return TextClause(unicode(element))
    elif hasattr(insp, "selectable"):
        return insp.selectable
    raise exc.ArgumentError("FROM expression expected")

def _interpret_as_select(element):
    element = _interpret_as_from(element)
    if isinstance(element, Alias):
        element = element.original
    if not isinstance(element, Select):
        element = element.select()
    return element


def _const_expr(element):
    if isinstance(element, (Null, False_, True_)):
        return element
    elif element is None:
        return null()
    elif element is False:
        return false()
    elif element is True:
        return true()
    else:
        raise exc.ArgumentError(
            "Expected None, False, or True"
        )


def _type_from_args(args):
    for a in args:
        if not isinstance(a.type, sqltypes.NullType):
            return a.type
    else:
        return sqltypes.NullType


def _corresponding_column_or_error(fromclause, column,
                                        require_embedded=False):
    c = fromclause.corresponding_column(column,
            require_embedded=require_embedded)
    if c is None:
        raise exc.InvalidRequestError(
                "Given column '%s', attached to table '%s', "
                "failed to locate a corresponding column from table '%s'"
                %
                (column,
                    getattr(column, 'table', None),
                    fromclause.description)
                )
    return c


@util.decorator
def _generative(fn, *args, **kw):
    """Mark a method as generative."""

    self = args[0]._generate()
    fn(self, *args[1:], **kw)
    return self


def is_column(col):
    """True if ``col`` is an instance of :class:`.ColumnElement`."""

    return isinstance(col, ColumnElement)


class ClauseElement(Visitable):
    """Base class for elements of a programmatically constructed SQL
    expression.

    """
    __visit_name__ = 'clause'

    _annotations = {}
    supports_execution = False
    _from_objects = []
    bind = None
    _is_clone_of = None
    is_selectable = False
    is_clause_element = True

    def _clone(self):
        """Create a shallow copy of this ClauseElement.

        This method may be used by a generative API.  Its also used as
        part of the "deep" copy afforded by a traversal that combines
        the _copy_internals() method.

        """
        c = self.__class__.__new__(self.__class__)
        c.__dict__ = self.__dict__.copy()
        ClauseElement._cloned_set._reset(c)
        ColumnElement.comparator._reset(c)

        # this is a marker that helps to "equate" clauses to each other
        # when a Select returns its list of FROM clauses.  the cloning
        # process leaves around a lot of remnants of the previous clause
        # typically in the form of column expressions still attached to the
        # old table.
        c._is_clone_of = self

        return c

    @property
    def _constructor(self):
        """return the 'constructor' for this ClauseElement.

        This is for the purposes for creating a new object of
        this type.   Usually, its just the element's __class__.
        However, the "Annotated" version of the object overrides
        to return the class of its proxied element.

        """
        return self.__class__

    @util.memoized_property
    def _cloned_set(self):
        """Return the set consisting all cloned ancestors of this
        ClauseElement.

        Includes this ClauseElement.  This accessor tends to be used for
        FromClause objects to identify 'equivalent' FROM clauses, regardless
        of transformative operations.

        """
        s = util.column_set()
        f = self
        while f is not None:
            s.add(f)
            f = f._is_clone_of
        return s

    def __getstate__(self):
        d = self.__dict__.copy()
        d.pop('_is_clone_of', None)
        return d

    if util.jython:
        def __hash__(self):
            """Return a distinct hash code.

            ClauseElements may have special equality comparisons which
            makes us rely on them having unique hash codes for use in
            hash-based collections. Stock __hash__ doesn't guarantee
            unique values on platforms with moving GCs.
            """
            return id(self)

    def _annotate(self, values):
        """return a copy of this ClauseElement with annotations
        updated by the given dictionary.

        """
        return sqlutil.Annotated(self, values)

    def _with_annotations(self, values):
        """return a copy of this ClauseElement with annotations
        replaced by the given dictionary.

        """
        return sqlutil.Annotated(self, values)

    def _deannotate(self, values=None, clone=False):
        """return a copy of this :class:`.ClauseElement` with annotations
        removed.

        :param values: optional tuple of individual values
         to remove.

        """
        if clone:
            # clone is used when we are also copying
            # the expression for a deep deannotation
            return self._clone()
        else:
            # if no clone, since we have no annotations we return
            # self
            return self

    def unique_params(self, *optionaldict, **kwargs):
        """Return a copy with :func:`bindparam()` elements replaced.

        Same functionality as ``params()``, except adds `unique=True`
        to affected bind parameters so that multiple statements can be
        used.

        """
        return self._params(True, optionaldict, kwargs)

    def params(self, *optionaldict, **kwargs):
        """Return a copy with :func:`bindparam()` elements replaced.

        Returns a copy of this ClauseElement with :func:`bindparam()`
        elements replaced with values taken from the given dictionary::

          >>> clause = column('x') + bindparam('foo')
          >>> print clause.compile().params
          {'foo':None}
          >>> print clause.params({'foo':7}).compile().params
          {'foo':7}

        """
        return self._params(False, optionaldict, kwargs)

    def _params(self, unique, optionaldict, kwargs):
        if len(optionaldict) == 1:
            kwargs.update(optionaldict[0])
        elif len(optionaldict) > 1:
            raise exc.ArgumentError(
                "params() takes zero or one positional dictionary argument")

        def visit_bindparam(bind):
            if bind.key in kwargs:
                bind.value = kwargs[bind.key]
                bind.required = False
            if unique:
                bind._convert_to_unique()
        return cloned_traverse(self, {}, {'bindparam': visit_bindparam})

    def compare(self, other, **kw):
        """Compare this ClauseElement to the given ClauseElement.

        Subclasses should override the default behavior, which is a
        straight identity comparison.

        \**kw are arguments consumed by subclass compare() methods and
        may be used to modify the criteria for comparison.
        (see :class:`.ColumnElement`)

        """
        return self is other

    def _copy_internals(self, clone=_clone, **kw):
        """Reassign internal elements to be clones of themselves.

        Called during a copy-and-traverse operation on newly
        shallow-copied elements to create a deep copy.

        The given clone function should be used, which may be applying
        additional transformations to the element (i.e. replacement
        traversal, cloned traversal, annotations).

        """
        pass

    def get_children(self, **kwargs):
        """Return immediate child elements of this :class:`.ClauseElement`.

        This is used for visit traversal.

        \**kwargs may contain flags that change the collection that is
        returned, for example to return a subset of items in order to
        cut down on larger traversals, or to return child items from a
        different context (such as schema-level collections instead of
        clause-level).

        """
        return []

    def self_group(self, against=None):
        """Apply a 'grouping' to this :class:`.ClauseElement`.

        This method is overridden by subclasses to return a
        "grouping" construct, i.e. parenthesis.   In particular
        it's used by "binary" expressions to provide a grouping
        around themselves when placed into a larger expression,
        as well as by :func:`.select` constructs when placed into
        the FROM clause of another :func:`.select`.  (Note that
        subqueries should be normally created using the
        :func:`.Select.alias` method, as many platforms require
        nested SELECT statements to be named).

        As expressions are composed together, the application of
        :meth:`self_group` is automatic - end-user code should never
        need to use this method directly.  Note that SQLAlchemy's
        clause constructs take operator precedence into account -
        so parenthesis might not be needed, for example, in
        an expression like ``x OR (y AND z)`` - AND takes precedence
        over OR.

        The base :meth:`self_group` method of :class:`.ClauseElement`
        just returns self.
        """
        return self

    def compile(self, bind=None, dialect=None, **kw):
        """Compile this SQL expression.

        The return value is a :class:`~.Compiled` object.
        Calling ``str()`` or ``unicode()`` on the returned value will yield a
        string representation of the result. The
        :class:`~.Compiled` object also can return a
        dictionary of bind parameter names and values
        using the ``params`` accessor.

        :param bind: An ``Engine`` or ``Connection`` from which a
            ``Compiled`` will be acquired. This argument takes precedence over
            this :class:`.ClauseElement`'s bound engine, if any.

        :param column_keys: Used for INSERT and UPDATE statements, a list of
            column names which should be present in the VALUES clause of the
            compiled statement. If ``None``, all columns from the target table
            object are rendered.

        :param dialect: A ``Dialect`` instance from which a ``Compiled``
            will be acquired. This argument takes precedence over the `bind`
            argument as well as this :class:`.ClauseElement`'s bound engine, if
            any.

        :param inline: Used for INSERT statements, for a dialect which does
            not support inline retrieval of newly generated primary key
            columns, will force the expression used to create the new primary
            key value to be rendered inline within the INSERT statement's
            VALUES clause. This typically refers to Sequence execution but may
            also refer to any server-side default generation function
            associated with a primary key `Column`.

        """

        if not dialect:
            if bind:
                dialect = bind.dialect
            elif self.bind:
                dialect = self.bind.dialect
                bind = self.bind
            else:
                dialect = default.DefaultDialect()
        return self._compiler(dialect, bind=bind, **kw)

    def _compiler(self, dialect, **kw):
        """Return a compiler appropriate for this ClauseElement, given a
        Dialect."""

        return dialect.statement_compiler(dialect, self, **kw)

    def __str__(self):
        # Py3K
        #return unicode(self.compile())
        # Py2K
        return unicode(self.compile()).encode('ascii', 'backslashreplace')
        # end Py2K

    def __and__(self, other):
        return and_(self, other)

    def __or__(self, other):
        return or_(self, other)

    def __invert__(self):
        return self._negate()

    def __nonzero__(self):
        raise TypeError("Boolean value of this clause is not defined")

    def _negate(self):
        if hasattr(self, 'negation_clause'):
            return self.negation_clause
        else:
            return UnaryExpression(
                        self.self_group(against=operators.inv),
                        operator=operators.inv,
                        negate=None)

    def __repr__(self):
        friendly = getattr(self, 'description', None)
        if friendly is None:
            return object.__repr__(self)
        else:
            return '<%s.%s at 0x%x; %s>' % (
                self.__module__, self.__class__.__name__, id(self), friendly)

inspection._self_inspects(ClauseElement)


class Immutable(object):
    """mark a ClauseElement as 'immutable' when expressions are cloned."""

    def unique_params(self, *optionaldict, **kwargs):
        raise NotImplementedError("Immutable objects do not support copying")

    def params(self, *optionaldict, **kwargs):
        raise NotImplementedError("Immutable objects do not support copying")

    def _clone(self):
        return self


class _DefaultColumnComparator(operators.ColumnOperators):
    """Defines comparison and math operations.

    See :class:`.ColumnOperators` and :class:`.Operators` for descriptions
    of all operations.

    """

    @util.memoized_property
    def type(self):
        return self.expr.type

    def operate(self, op, *other, **kwargs):
        o = self.operators[op.__name__]
        return o[0](self, self.expr, op, *(other + o[1:]), **kwargs)

    def reverse_operate(self, op, other, **kwargs):
        o = self.operators[op.__name__]
        return o[0](self, self.expr, op, other, reverse=True, *o[1:], **kwargs)

    def _adapt_expression(self, op, other_comparator):
        """evaluate the return type of <self> <op> <othertype>,
        and apply any adaptations to the given operator.

        This method determines the type of a resulting binary expression
        given two source types and an operator.   For example, two
        :class:`.Column` objects, both of the type :class:`.Integer`, will
        produce a :class:`.BinaryExpression` that also has the type
        :class:`.Integer` when compared via the addition (``+``) operator.
        However, using the addition operator with an :class:`.Integer`
        and a :class:`.Date` object will produce a :class:`.Date`, assuming
        "days delta" behavior by the database (in reality, most databases
        other than Postgresql don't accept this particular operation).

        The method returns a tuple of the form <operator>, <type>.
        The resulting operator and type will be those applied to the
        resulting :class:`.BinaryExpression` as the final operator and the
        right-hand side of the expression.

        Note that only a subset of operators make usage of
        :meth:`._adapt_expression`,
        including math operators and user-defined operators, but not
        boolean comparison or special SQL keywords like MATCH or BETWEEN.

        """
        return op, other_comparator.type

    def _boolean_compare(self, expr, op, obj, negate=None, reverse=False,
                        _python_is_types=(util.NoneType, bool),
                        **kwargs):

        if isinstance(obj, _python_is_types + (Null, True_, False_)):

            # allow x ==/!= True/False to be treated as a literal.
            # this comes out to "== / != true/false" or "1/0" if those
            # constants aren't supported and works on all platforms
            if op in (operators.eq, operators.ne) and \
                    isinstance(obj, (bool, True_, False_)):
                return BinaryExpression(expr,
                                obj,
                                op,
                                type_=sqltypes.BOOLEANTYPE,
                                negate=negate, modifiers=kwargs)
            else:
                # all other None/True/False uses IS, IS NOT
                if op in (operators.eq, operators.is_):
                    return BinaryExpression(expr, _const_expr(obj),
                            operators.is_,
                            negate=operators.isnot)
                elif op in (operators.ne, operators.isnot):
                    return BinaryExpression(expr, _const_expr(obj),
                            operators.isnot,
                            negate=operators.is_)
                else:
                    raise exc.ArgumentError(
                        "Only '=', '!=', 'is_()', 'isnot()' operators can "
                        "be used with None/True/False")
        else:
            obj = self._check_literal(expr, op, obj)

        if reverse:
            return BinaryExpression(obj,
                            expr,
                            op,
                            type_=sqltypes.BOOLEANTYPE,
                            negate=negate, modifiers=kwargs)
        else:
            return BinaryExpression(expr,
                            obj,
                            op,
                            type_=sqltypes.BOOLEANTYPE,
                            negate=negate, modifiers=kwargs)

    def _binary_operate(self, expr, op, obj, reverse=False, result_type=None,
                            **kw):
        obj = self._check_literal(expr, op, obj)

        if reverse:
            left, right = obj, expr
        else:
            left, right = expr, obj

        if result_type is None:
            op, result_type = left.comparator._adapt_expression(
                                                op, right.comparator)

        return BinaryExpression(left, right, op, type_=result_type)

    def _scalar(self, expr, op, fn, **kw):
        return fn(expr)

    def _in_impl(self, expr, op, seq_or_selectable, negate_op, **kw):
        seq_or_selectable = _clause_element_as_expr(seq_or_selectable)

        if isinstance(seq_or_selectable, ScalarSelect):
            return self._boolean_compare(expr, op, seq_or_selectable,
                                  negate=negate_op)
        elif isinstance(seq_or_selectable, SelectBase):

            # TODO: if we ever want to support (x, y, z) IN (select x,
            # y, z from table), we would need a multi-column version of
            # as_scalar() to produce a multi- column selectable that
            # does not export itself as a FROM clause

            return self._boolean_compare(
                expr, op, seq_or_selectable.as_scalar(),
                negate=negate_op, **kw)
        elif isinstance(seq_or_selectable, (Selectable, TextClause)):
            return self._boolean_compare(expr, op, seq_or_selectable,
                                  negate=negate_op, **kw)

        # Handle non selectable arguments as sequences
        args = []
        for o in seq_or_selectable:
            if not _is_literal(o):
                if not isinstance(o, ColumnOperators):
                    raise exc.InvalidRequestError('in() function accept'
                            's either a list of non-selectable values, '
                            'or a selectable: %r' % o)
            elif o is None:
                o = null()
            else:
                o = expr._bind_param(op, o)
            args.append(o)
        if len(args) == 0:

            # Special case handling for empty IN's, behave like
            # comparison against zero row selectable.  We use != to
            # build the contradiction as it handles NULL values
            # appropriately, i.e. "not (x IN ())" should not return NULL
            # values for x.

            util.warn('The IN-predicate on "%s" was invoked with an '
                      'empty sequence. This results in a '
                      'contradiction, which nonetheless can be '
                      'expensive to evaluate.  Consider alternative '
                      'strategies for improved performance.' % expr)
            if op is operators.in_op:
                return expr != expr
            else:
                return expr == expr

        return self._boolean_compare(expr, op,
                              ClauseList(*args).self_group(against=op),
                              negate=negate_op)

    def _unsupported_impl(self, expr, op, *arg, **kw):
        raise NotImplementedError("Operator '%s' is not supported on "
                            "this expression" % op.__name__)

    def _neg_impl(self, expr, op, **kw):
        """See :meth:`.ColumnOperators.__neg__`."""
        return UnaryExpression(expr, operator=operators.neg)

    def _match_impl(self, expr, op, other, **kw):
        """See :meth:`.ColumnOperators.match`."""
        return self._boolean_compare(expr, operators.match_op,
                              self._check_literal(expr, operators.match_op,
                              other))

    def _distinct_impl(self, expr, op, **kw):
        """See :meth:`.ColumnOperators.distinct`."""
        return UnaryExpression(expr, operator=operators.distinct_op,
                                type_=expr.type)

    def _between_impl(self, expr, op, cleft, cright, **kw):
        """See :meth:`.ColumnOperators.between`."""
        return BinaryExpression(
                expr,
                ClauseList(
                    self._check_literal(expr, operators.and_, cleft),
                    self._check_literal(expr, operators.and_, cright),
                    operator=operators.and_,
                    group=False),
                operators.between_op)

    def _collate_impl(self, expr, op, other, **kw):
        return collate(expr, other)

    # a mapping of operators with the method they use, along with
    # their negated operator for comparison operators
    operators = {
        "add": (_binary_operate,),
        "mul": (_binary_operate,),
        "sub": (_binary_operate,),
        "div": (_binary_operate,),
        "mod": (_binary_operate,),
        "truediv": (_binary_operate,),
        "custom_op": (_binary_operate,),
        "concat_op": (_binary_operate,),
        "lt": (_boolean_compare, operators.ge),
        "le": (_boolean_compare, operators.gt),
        "ne": (_boolean_compare, operators.eq),
        "gt": (_boolean_compare, operators.le),
        "ge": (_boolean_compare, operators.lt),
        "eq": (_boolean_compare, operators.ne),
        "like_op": (_boolean_compare, operators.notlike_op),
        "ilike_op": (_boolean_compare, operators.notilike_op),
        "notlike_op": (_boolean_compare, operators.like_op),
        "notilike_op": (_boolean_compare, operators.ilike_op),
        "contains_op": (_boolean_compare, operators.notcontains_op),
        "startswith_op": (_boolean_compare, operators.notstartswith_op),
        "endswith_op": (_boolean_compare, operators.notendswith_op),
        "desc_op": (_scalar, desc),
        "asc_op": (_scalar, asc),
        "nullsfirst_op": (_scalar, nullsfirst),
        "nullslast_op": (_scalar, nullslast),
        "in_op": (_in_impl, operators.notin_op),
        "notin_op": (_in_impl, operators.in_op),
        "is_": (_boolean_compare, operators.is_),
        "isnot": (_boolean_compare, operators.isnot),
        "collate": (_collate_impl,),
        "match_op": (_match_impl,),
        "distinct_op": (_distinct_impl,),
        "between_op": (_between_impl, ),
        "neg": (_neg_impl,),
        "getitem": (_unsupported_impl,),
        "lshift": (_unsupported_impl,),
        "rshift": (_unsupported_impl,),
    }

    def _check_literal(self, expr, operator, other):
        if isinstance(other, (ColumnElement, TextClause)):
            if isinstance(other, BindParameter) and \
                isinstance(other.type, sqltypes.NullType):
                # TODO: perhaps we should not mutate the incoming
                # bindparam() here and instead make a copy of it.
                # this might be the only place that we're mutating
                # an incoming construct.
                other.type = expr.type
            return other
        elif hasattr(other, '__clause_element__'):
            other = other.__clause_element__()
        elif isinstance(other, sqltypes.TypeEngine.Comparator):
            other = other.expr

        if isinstance(other, (SelectBase, Alias)):
            return other.as_scalar()
        elif not isinstance(other, (ColumnElement, TextClause)):
            return expr._bind_param(operator, other)
        else:
            return other


class ColumnElement(ClauseElement, ColumnOperators):
    """Represent a column-oriented SQL expression suitable for usage in the
    "columns" clause, WHERE clause etc. of a statement.

    While the most familiar kind of :class:`.ColumnElement` is the
    :class:`.Column` object, :class:`.ColumnElement` serves as the basis
    for any unit that may be present in a SQL expression, including
    the expressions themselves, SQL functions, bound parameters,
    literal expressions, keywords such as ``NULL``, etc.
    :class:`.ColumnElement` is the ultimate base class for all such elements.

    A :class:`.ColumnElement` provides the ability to generate new
    :class:`.ColumnElement`
    objects using Python expressions.  This means that Python operators
    such as ``==``, ``!=`` and ``<`` are overloaded to mimic SQL operations,
    and allow the instantiation of further :class:`.ColumnElement` instances
    which are composed from other, more fundamental :class:`.ColumnElement`
    objects.  For example, two :class:`.ColumnClause` objects can be added
    together with the addition operator ``+`` to produce
    a :class:`.BinaryExpression`.
    Both :class:`.ColumnClause` and :class:`.BinaryExpression` are subclasses
    of :class:`.ColumnElement`::

        >>> from sqlalchemy.sql import column
        >>> column('a') + column('b')
        <sqlalchemy.sql.expression.BinaryExpression object at 0x101029dd0>
        >>> print column('a') + column('b')
        a + b

    :class:`.ColumnElement` supports the ability to be a *proxy* element,
    which indicates that the :class:`.ColumnElement` may be associated with
    a :class:`.Selectable` which was derived from another :class:`.Selectable`.
    An example of a "derived" :class:`.Selectable` is an :class:`.Alias` of a
    :class:`~sqlalchemy.schema.Table`.  For the ambitious, an in-depth
    discussion of this concept can be found at
    `Expression Transformations <http://techspot.zzzeek.org/2008/01/23/expression-transformations/>`_.

    """

    __visit_name__ = 'column'
    primary_key = False
    foreign_keys = []
    quote = None
    _label = None
    _key_label = None
    _alt_names = ()

    @util.memoized_property
    def type(self):
        return sqltypes.NULLTYPE

    @util.memoized_property
    def comparator(self):
        return self.type.comparator_factory(self)

    def __getattr__(self, key):
        try:
            return getattr(self.comparator, key)
        except AttributeError:
            raise AttributeError(
                    'Neither %r object nor %r object has an attribute %r' % (
                    type(self).__name__,
                    type(self.comparator).__name__,
                    key)
            )

    def operate(self, op, *other, **kwargs):
        return op(self.comparator, *other, **kwargs)

    def reverse_operate(self, op, other, **kwargs):
        return op(other, self.comparator, **kwargs)

    def _bind_param(self, operator, obj):
        return BindParameter(None, obj,
                                    _compared_to_operator=operator,
                                    _compared_to_type=self.type, unique=True)

    @property
    def expression(self):
        """Return a column expression.

        Part of the inspection interface; returns self.

        """
        return self

    @property
    def _select_iterable(self):
        return (self, )

    @util.memoized_property
    def base_columns(self):
        return util.column_set(c for c in self.proxy_set
                                     if not hasattr(c, '_proxies'))

    @util.memoized_property
    def proxy_set(self):
        s = util.column_set([self])
        if hasattr(self, '_proxies'):
            for c in self._proxies:
                s.update(c.proxy_set)
        return s

    def shares_lineage(self, othercolumn):
        """Return True if the given :class:`.ColumnElement`
        has a common ancestor to this :class:`.ColumnElement`."""

        return bool(self.proxy_set.intersection(othercolumn.proxy_set))

    def _compare_name_for_result(self, other):
        """Return True if the given column element compares to this one
        when targeting within a result row."""

        return hasattr(other, 'name') and hasattr(self, 'name') and \
                other.name == self.name

    def _make_proxy(self, selectable, name=None, name_is_truncatable=False, **kw):
        """Create a new :class:`.ColumnElement` representing this
        :class:`.ColumnElement` as it appears in the select list of a
        descending selectable.

        """
        if name is None:
            name = self.anon_label
            try:
                key = str(self)
            except exc.UnsupportedCompilationError:
                key = self.anon_label
        else:
            key = name
        co = ColumnClause(_as_truncated(name) if name_is_truncatable else name,
                            selectable,
                            type_=getattr(self,
                          'type', None))
        co._proxies = [self]
        if selectable._is_clone_of is not None:
            co._is_clone_of = \
                selectable._is_clone_of.columns.get(key)
        selectable._columns[key] = co
        return co

    def compare(self, other, use_proxies=False, equivalents=None, **kw):
        """Compare this ColumnElement to another.

        Special arguments understood:

        :param use_proxies: when True, consider two columns that
          share a common base column as equivalent (i.e. shares_lineage())

        :param equivalents: a dictionary of columns as keys mapped to sets
          of columns. If the given "other" column is present in this
          dictionary, if any of the columns in the corresponding set() pass the
          comparison test, the result is True. This is used to expand the
          comparison to other columns that may be known to be equivalent to
          this one via foreign key or other criterion.

        """
        to_compare = (other, )
        if equivalents and other in equivalents:
            to_compare = equivalents[other].union(to_compare)

        for oth in to_compare:
            if use_proxies and self.shares_lineage(oth):
                return True
            elif hash(oth) == hash(self):
                return True
        else:
            return False

    def label(self, name):
        """Produce a column label, i.e. ``<columnname> AS <name>``.

        This is a shortcut to the :func:`~.expression.label` function.

        if 'name' is None, an anonymous label name will be generated.

        """
        return Label(name, self, self.type)

    @util.memoized_property
    def anon_label(self):
        """provides a constant 'anonymous label' for this ColumnElement.

        This is a label() expression which will be named at compile time.
        The same label() is returned each time anon_label is called so
        that expressions can reference anon_label multiple times, producing
        the same label name at compile time.

        the compiler uses this function automatically at compile time
        for expressions that are known to be 'unnamed' like binary
        expressions and function calls.

        """
        return _anonymous_label('%%(%d %s)s' % (id(self), getattr(self,
                                'name', 'anon')))


class ColumnCollection(util.OrderedProperties):
    """An ordered dictionary that stores a list of ColumnElement
    instances.

    Overrides the ``__eq__()`` method to produce SQL clauses between
    sets of correlated columns.

    """

    def __init__(self, *cols):
        super(ColumnCollection, self).__init__()
        self._data.update((c.key, c) for c in cols)
        self.__dict__['_all_cols'] = util.column_set(self)

    def __str__(self):
        return repr([str(c) for c in self])

    def replace(self, column):
        """add the given column to this collection, removing unaliased
           versions of this column  as well as existing columns with the
           same key.

            e.g.::

                t = Table('sometable', metadata, Column('col1', Integer))
                t.columns.replace(Column('col1', Integer, key='columnone'))

            will remove the original 'col1' from the collection, and add
            the new column under the name 'columnname'.

           Used by schema.Column to override columns during table reflection.

        """
        if column.name in self and column.key != column.name:
            other = self[column.name]
            if other.name == other.key:
                del self._data[other.name]
                self._all_cols.remove(other)
        if column.key in self._data:
            self._all_cols.remove(self._data[column.key])
        self._all_cols.add(column)
        self._data[column.key] = column

    def add(self, column):
        """Add a column to this collection.

        The key attribute of the column will be used as the hash key
        for this dictionary.

        """
        self[column.key] = column

    def __delitem__(self, key):
        raise NotImplementedError()

    def __setattr__(self, key, object):
        raise NotImplementedError()

    def __setitem__(self, key, value):
        if key in self:

            # this warning is primarily to catch select() statements
            # which have conflicting column names in their exported
            # columns collection

            existing = self[key]
            if not existing.shares_lineage(value):
                util.warn('Column %r on table %r being replaced by '
                          '%r, which has the same key.  Consider '
                          'use_labels for select() statements.' % (key,
                          getattr(existing, 'table', None), value))
            self._all_cols.remove(existing)
            # pop out memoized proxy_set as this
            # operation may very well be occurring
            # in a _make_proxy operation
            ColumnElement.proxy_set._reset(value)
        self._all_cols.add(value)
        self._data[key] = value

    def clear(self):
        self._data.clear()
        self._all_cols.clear()

    def remove(self, column):
        del self._data[column.key]
        self._all_cols.remove(column)

    def update(self, value):
        self._data.update(value)
        self._all_cols.clear()
        self._all_cols.update(self._data.values())

    def extend(self, iter):
        self.update((c.key, c) for c in iter)

    __hash__ = None

    def __eq__(self, other):
        l = []
        for c in other:
            for local in self:
                if c.shares_lineage(local):
                    l.append(c == local)
        return and_(*l)

    def __contains__(self, other):
        if not isinstance(other, basestring):
            raise exc.ArgumentError("__contains__ requires a string argument")
        return util.OrderedProperties.__contains__(self, other)

    def __setstate__(self, state):
        self.__dict__['_data'] = state['_data']
        self.__dict__['_all_cols'] = util.column_set(self._data.values())

    def contains_column(self, col):
        # this has to be done via set() membership
        return col in self._all_cols

    def as_immutable(self):
        return ImmutableColumnCollection(self._data, self._all_cols)


class ImmutableColumnCollection(util.ImmutableProperties, ColumnCollection):
    def __init__(self, data, colset):
        util.ImmutableProperties.__init__(self, data)
        self.__dict__['_all_cols'] = colset

    extend = remove = util.ImmutableProperties._immutable


class ColumnSet(util.ordered_column_set):
    def contains_column(self, col):
        return col in self

    def extend(self, cols):
        for col in cols:
            self.add(col)

    def __add__(self, other):
        return list(self) + list(other)

    def __eq__(self, other):
        l = []
        for c in other:
            for local in self:
                if c.shares_lineage(local):
                    l.append(c == local)
        return and_(*l)

    def __hash__(self):
        return hash(tuple(x for x in self))


class Selectable(ClauseElement):
    """mark a class as being selectable"""
    __visit_name__ = 'selectable'

    is_selectable = True

    @property
    def selectable(self):
        return self


class FromClause(Selectable):
    """Represent an element that can be used within the ``FROM``
    clause of a ``SELECT`` statement.

    The most common forms of :class:`.FromClause` are the
    :class:`.Table` and the :func:`.select` constructs.  Key
    features common to all :class:`.FromClause` objects include:

    * a :attr:`.c` collection, which provides per-name access to a collection
      of :class:`.ColumnElement` objects.
    * a :attr:`.primary_key` attribute, which is a collection of all those
      :class:`.ColumnElement` objects that indicate the ``primary_key`` flag.
    * Methods to generate various derivations of a "from" clause, including
      :meth:`.FromClause.alias`, :meth:`.FromClause.join`,
      :meth:`.FromClause.select`.


    """
    __visit_name__ = 'fromclause'
    named_with_column = False
    _hide_froms = []
    quote = None
    schema = None
    _memoized_property = util.group_expirable_memoized_property(["_columns"])

    def count(self, whereclause=None, **params):
        """return a SELECT COUNT generated against this
        :class:`.FromClause`."""

        if self.primary_key:
            col = list(self.primary_key)[0]
        else:
            col = list(self.columns)[0]
        return select(
                    [func.count(col).label('tbl_row_count')],
                    whereclause,
                    from_obj=[self],
                    **params)

    def select(self, whereclause=None, **params):
        """return a SELECT of this :class:`.FromClause`.

        .. seealso::

            :func:`~.sql.expression.select` - general purpose
            method which allows for arbitrary column lists.

        """

        return select([self], whereclause, **params)

    def join(self, right, onclause=None, isouter=False):
        """return a join of this :class:`.FromClause` against another
        :class:`.FromClause`."""

        return Join(self, right, onclause, isouter)

    def outerjoin(self, right, onclause=None):
        """return an outer join of this :class:`.FromClause` against another
        :class:`.FromClause`."""

        return Join(self, right, onclause, True)

    def alias(self, name=None):
        """return an alias of this :class:`.FromClause`.

        This is shorthand for calling::

            from sqlalchemy import alias
            a = alias(self, name=name)

        See :func:`~.expression.alias` for details.

        """

        return Alias(self, name)

    def is_derived_from(self, fromclause):
        """Return True if this FromClause is 'derived' from the given
        FromClause.

        An example would be an Alias of a Table is derived from that Table.

        """
        # this is essentially an "identity" check in the base class.
        # Other constructs override this to traverse through
        # contained elements.
        return fromclause in self._cloned_set

    def _is_lexical_equivalent(self, other):
        """Return True if this FromClause and the other represent
        the same lexical identity.

        This tests if either one is a copy of the other, or
        if they are the same via annotation identity.

        """
        return self._cloned_set.intersection(other._cloned_set)

    def replace_selectable(self, old, alias):
        """replace all occurrences of FromClause 'old' with the given Alias
        object, returning a copy of this :class:`.FromClause`.

        """

        return sqlutil.ClauseAdapter(alias).traverse(self)

    def correspond_on_equivalents(self, column, equivalents):
        """Return corresponding_column for the given column, or if None
        search for a match in the given dictionary.

        """
        col = self.corresponding_column(column, require_embedded=True)
        if col is None and col in equivalents:
            for equiv in equivalents[col]:
                nc = self.corresponding_column(equiv, require_embedded=True)
                if nc:
                    return nc
        return col

    def corresponding_column(self, column, require_embedded=False):
        """Given a :class:`.ColumnElement`, return the exported
        :class:`.ColumnElement` object from this :class:`.Selectable`
        which corresponds to that original
        :class:`~sqlalchemy.schema.Column` via a common ancestor
        column.

        :param column: the target :class:`.ColumnElement` to be matched

        :param require_embedded: only return corresponding columns for
        the given :class:`.ColumnElement`, if the given
        :class:`.ColumnElement` is actually present within a sub-element
        of this :class:`.FromClause`.  Normally the column will match if
        it merely shares a common ancestor with one of the exported
        columns of this :class:`.FromClause`.

        """

        def embedded(expanded_proxy_set, target_set):
            for t in target_set.difference(expanded_proxy_set):
                if not set(_expand_cloned([t])
                            ).intersection(expanded_proxy_set):
                    return False
            return True

        # don't dig around if the column is locally present
        if self.c.contains_column(column):
            return column
        col, intersect = None, None
        target_set = column.proxy_set
        cols = self.c
        for c in cols:
            expanded_proxy_set = set(_expand_cloned(c.proxy_set))
            i = target_set.intersection(expanded_proxy_set)
            if i and (not require_embedded
                      or embedded(expanded_proxy_set, target_set)):
                if col is None:

                    # no corresponding column yet, pick this one.

                    col, intersect = c, i
                elif len(i) > len(intersect):

                    # 'c' has a larger field of correspondence than
                    # 'col'. i.e. selectable.c.a1_x->a1.c.x->table.c.x
                    # matches a1.c.x->table.c.x better than
                    # selectable.c.x->table.c.x does.

                    col, intersect = c, i
                elif i == intersect:

                    # they have the same field of correspondence. see
                    # which proxy_set has fewer columns in it, which
                    # indicates a closer relationship with the root
                    # column. Also take into account the "weight"
                    # attribute which CompoundSelect() uses to give
                    # higher precedence to columns based on vertical
                    # position in the compound statement, and discard
                    # columns that have no reference to the target
                    # column (also occurs with CompoundSelect)

                    col_distance = util.reduce(operator.add,
                            [sc._annotations.get('weight', 1) for sc in
                            col.proxy_set if sc.shares_lineage(column)])
                    c_distance = util.reduce(operator.add,
                            [sc._annotations.get('weight', 1) for sc in
                            c.proxy_set if sc.shares_lineage(column)])
                    if c_distance < col_distance:
                        col, intersect = c, i
        return col

    @property
    def description(self):
        """a brief description of this FromClause.

        Used primarily for error message formatting.

        """
        return getattr(self, 'name', self.__class__.__name__ + " object")

    def _reset_exported(self):
        """delete memoized collections when a FromClause is cloned."""

        self._memoized_property.expire_instance(self)

    @_memoized_property
    def columns(self):
        """A named-based collection of :class:`.ColumnElement` objects
        maintained by this :class:`.FromClause`.

        The :attr:`.columns`, or :attr:`.c` collection, is the gateway
        to the construction of SQL expressions using table-bound or
        other selectable-bound columns::

            select([mytable]).where(mytable.c.somecolumn == 5)

        """

        if '_columns' not in self.__dict__:
            self._init_collections()
            self._populate_column_collection()
        return self._columns.as_immutable()

    @_memoized_property
    def primary_key(self):
        """Return the collection of Column objects which comprise the
        primary key of this FromClause."""

        self._init_collections()
        self._populate_column_collection()
        return self.primary_key

    @_memoized_property
    def foreign_keys(self):
        """Return the collection of ForeignKey objects which this
        FromClause references."""

        self._init_collections()
        self._populate_column_collection()
        return self.foreign_keys

    c = property(attrgetter('columns'),
            doc="An alias for the :attr:`.columns` attribute.")
    _select_iterable = property(attrgetter('columns'))

    def _init_collections(self):
        assert '_columns' not in self.__dict__
        assert 'primary_key' not in self.__dict__
        assert 'foreign_keys' not in self.__dict__

        self._columns = ColumnCollection()
        self.primary_key = ColumnSet()
        self.foreign_keys = set()

    @property
    def _cols_populated(self):
        return '_columns' in self.__dict__

    def _populate_column_collection(self):
        """Called on subclasses to establish the .c collection.

        Each implementation has a different way of establishing
        this collection.

        """

    def _refresh_for_new_column(self, column):
        """Given a column added to the .c collection of an underlying
        selectable, produce the local version of that column, assuming this
        selectable ultimately should proxy this column.

        this is used to "ping" a derived selectable to add a new column
        to its .c. collection when a Column has been added to one of the
        Table objects it ultimtely derives from.

        If the given selectable hasn't populated it's .c. collection yet,
        it should at least pass on the message to the contained selectables,
        but it will return None.

        This method is currently used by Declarative to allow Table
        columns to be added to a partially constructed inheritance
        mapping that may have already produced joins.  The method
        isn't public right now, as the full span of implications
        and/or caveats aren't yet clear.

        It's also possible that this functionality could be invoked by
        default via an event, which would require that
        selectables maintain a weak referencing collection of all
        derivations.

        """
        if not self._cols_populated:
            return None
        elif column.key in self.columns and self.columns[column.key] is column:
            return column
        else:
            return None


class BindParameter(ColumnElement):
    """Represent a bind parameter.

    Public constructor is the :func:`bindparam()` function.

    """

    __visit_name__ = 'bindparam'
    quote = None

    _is_crud = False

    def __init__(self, key, value, type_=None, unique=False,
                            callable_=None,
                            isoutparam=False, required=False,
                            quote=None,
                            _compared_to_operator=None,
                            _compared_to_type=None):
        """Construct a BindParameter.

        :param key:
          the key for this bind param.  Will be used in the generated
          SQL statement for dialects that use named parameters.  This
          value may be modified when part of a compilation operation,
          if other :class:`BindParameter` objects exist with the same
          key, or if its length is too long and truncation is
          required.

        :param value:
          Initial value for this bind param.  This value may be
          overridden by the dictionary of parameters sent to statement
          compilation/execution.

        :param callable\_:
          A callable function that takes the place of "value".  The function
          will be called at statement execution time to determine the
          ultimate value.   Used for scenarios where the actual bind
          value cannot be determined at the point at which the clause
          construct is created, but embedded bind values are still desirable.

        :param type\_:
          A ``TypeEngine`` object that will be used to pre-process the
          value corresponding to this :class:`BindParameter` at
          execution time.

        :param unique:
          if True, the key name of this BindParamClause will be
          modified if another :class:`BindParameter` of the same name
          already has been located within the containing
          :class:`.ClauseElement`.

        :param quote:
          True if this parameter name requires quoting and is not
          currently known as a SQLAlchemy reserved word; this currently
          only applies to the Oracle backend.

        :param required:
          a value is required at execution time.

        :param isoutparam:
          if True, the parameter should be treated like a stored procedure
          "OUT" parameter.

        """
        if unique:
            self.key = _anonymous_label('%%(%d %s)s' % (id(self), key
                    or 'param'))
        else:
            self.key = key or _anonymous_label('%%(%d param)s'
                    % id(self))

        # identifying key that won't change across
        # clones, used to identify the bind's logical
        # identity
        self._identifying_key = self.key

        # key that was passed in the first place, used to
        # generate new keys
        self._orig_key = key or 'param'

        self.unique = unique
        self.value = value
        self.callable = callable_
        self.isoutparam = isoutparam
        self.required = required
        self.quote = quote
        if type_ is None:
            if _compared_to_type is not None:
                self.type = \
                    _compared_to_type.coerce_compared_value(
                        _compared_to_operator, value)
            else:
                self.type = sqltypes._type_map.get(type(value),
                        sqltypes.NULLTYPE)
        elif isinstance(type_, type):
            self.type = type_()
        else:
            self.type = type_

    @property
    def effective_value(self):
        """Return the value of this bound parameter,
        taking into account if the ``callable`` parameter
        was set.

        The ``callable`` value will be evaluated
        and returned if present, else ``value``.

        """
        if self.callable:
            return self.callable()
        else:
            return self.value

    def _clone(self):
        c = ClauseElement._clone(self)
        if self.unique:
            c.key = _anonymous_label('%%(%d %s)s' % (id(c), c._orig_key
                    or 'param'))
        return c

    def _convert_to_unique(self):
        if not self.unique:
            self.unique = True
            self.key = _anonymous_label('%%(%d %s)s' % (id(self),
                    self._orig_key or 'param'))

    def compare(self, other, **kw):
        """Compare this :class:`BindParameter` to the given
        clause."""

        return isinstance(other, BindParameter) \
            and self.type._compare_type_affinity(other.type) \
            and self.value == other.value

    def __getstate__(self):
        """execute a deferred value for serialization purposes."""

        d = self.__dict__.copy()
        v = self.value
        if self.callable:
            v = self.callable()
            d['callable'] = None
        d['value'] = v
        return d

    def __repr__(self):
        return 'BindParameter(%r, %r, type_=%r)' % (self.key,
                self.value, self.type)


class TypeClause(ClauseElement):
    """Handle a type keyword in a SQL statement.

    Used by the ``Case`` statement.

    """

    __visit_name__ = 'typeclause'

    def __init__(self, type):
        self.type = type


class Generative(object):
    """Allow a ClauseElement to generate itself via the
    @_generative decorator.

    """

    def _generate(self):
        s = self.__class__.__new__(self.__class__)
        s.__dict__ = self.__dict__.copy()
        return s


class Executable(Generative):
    """Mark a ClauseElement as supporting execution.

    :class:`.Executable` is a superclass for all "statement" types
    of objects, including :func:`select`, :func:`delete`, :func:`update`,
    :func:`insert`, :func:`text`.

    """

    supports_execution = True
    _execution_options = util.immutabledict()
    _bind = None

    @_generative
    def execution_options(self, **kw):
        """ Set non-SQL options for the statement which take effect during
        execution.

        Execution options can be set on a per-statement or
        per :class:`.Connection` basis.   Additionally, the
        :class:`.Engine` and ORM :class:`~.orm.query.Query` objects provide
        access to execution options which they in turn configure upon
        connections.

        The :meth:`execution_options` method is generative.  A new
        instance of this statement is returned that contains the options::

            statement = select([table.c.x, table.c.y])
            statement = statement.execution_options(autocommit=True)

        Note that only a subset of possible execution options can be applied
        to a statement - these include "autocommit" and "stream_results",
        but not "isolation_level" or "compiled_cache".
        See :meth:`.Connection.execution_options` for a full list of
        possible options.

        .. seealso::

            :meth:`.Connection.execution_options()`

            :meth:`.Query.execution_options()`

        """
        if 'isolation_level' in kw:
            raise exc.ArgumentError(
                "'isolation_level' execution option may only be specified "
                "on Connection.execution_options(), or "
                "per-engine using the isolation_level "
                "argument to create_engine()."
            )
        if 'compiled_cache' in kw:
            raise exc.ArgumentError(
                "'compiled_cache' execution option may only be specified "
                "on Connection.execution_options(), not per statement."
            )
        self._execution_options = self._execution_options.union(kw)

    def execute(self, *multiparams, **params):
        """Compile and execute this :class:`.Executable`."""

        e = self.bind
        if e is None:
            label = getattr(self, 'description', self.__class__.__name__)
            msg = ('This %s is not directly bound to a Connection or Engine.'
                   'Use the .execute() method of a Connection or Engine '
                   'to execute this construct.' % label)
            raise exc.UnboundExecutionError(msg)
        return e._execute_clauseelement(self, multiparams, params)

    def scalar(self, *multiparams, **params):
        """Compile and execute this :class:`.Executable`, returning the
        result's scalar representation.

        """
        return self.execute(*multiparams, **params).scalar()

    @property
    def bind(self):
        """Returns the :class:`.Engine` or :class:`.Connection` to
        which this :class:`.Executable` is bound, or None if none found.

        This is a traversal which checks locally, then
        checks among the "from" clauses of associated objects
        until a bound engine or connection is found.

        """
        if self._bind is not None:
            return self._bind

        for f in _from_objects(self):
            if f is self:
                continue
            engine = f.bind
            if engine is not None:
                return engine
        else:
            return None


# legacy, some outside users may be calling this
_Executable = Executable


class TextClause(Executable, ClauseElement):
    """Represent a literal SQL text fragment.

    Public constructor is the :func:`text()` function.

    """

    __visit_name__ = 'textclause'

    _bind_params_regex = re.compile(r'(?<![:\w\x5c]):(\w+)(?!:)', re.UNICODE)
    _execution_options = \
        Executable._execution_options.union(
            {'autocommit': PARSE_AUTOCOMMIT})

    @property
    def _select_iterable(self):
        return (self,)

    @property
    def selectable(self):
        return self

    _hide_froms = []

    def __init__(
        self,
        text='',
        bind=None,
        bindparams=None,
        typemap=None,
        autocommit=None,
        ):
        self._bind = bind
        self.bindparams = {}
        self.typemap = typemap
        if autocommit is not None:
            util.warn_deprecated('autocommit on text() is deprecated.  '
                                 'Use .execution_options(autocommit=Tru'
                                 'e)')
            self._execution_options = \
                self._execution_options.union(
                  {'autocommit': autocommit})
        if typemap is not None:
            for key in typemap.keys():
                typemap[key] = sqltypes.to_instance(typemap[key])

        def repl(m):
            self.bindparams[m.group(1)] = bindparam(m.group(1))
            return ':%s' % m.group(1)

        # scan the string and search for bind parameter names, add them
        # to the list of bindparams

        self.text = self._bind_params_regex.sub(repl, text)
        if bindparams is not None:
            for b in bindparams:
                self.bindparams[b.key] = b

    @property
    def type(self):
        if self.typemap is not None and len(self.typemap) == 1:
            return list(self.typemap)[0]
        else:
            return sqltypes.NULLTYPE

    @property
    def comparator(self):
        return self.type.comparator_factory(self)

    def self_group(self, against=None):
        if against is operators.in_op:
            return Grouping(self)
        else:
            return self

    def _copy_internals(self, clone=_clone, **kw):
        self.bindparams = dict((b.key, clone(b, **kw))
                               for b in self.bindparams.values())

    def get_children(self, **kwargs):
        return self.bindparams.values()


class Null(ColumnElement):
    """Represent the NULL keyword in a SQL statement.

    Public constructor is the :func:`null()` function.

    """

    __visit_name__ = 'null'

    def __init__(self):
        self.type = sqltypes.NULLTYPE

    def compare(self, other):
        return isinstance(other, Null)


class False_(ColumnElement):
    """Represent the ``false`` keyword in a SQL statement.

    Public constructor is the :func:`false()` function.

    """

    __visit_name__ = 'false'

    def __init__(self):
        self.type = sqltypes.BOOLEANTYPE

    def compare(self, other):
        return isinstance(other, False_)

class True_(ColumnElement):
    """Represent the ``true`` keyword in a SQL statement.

    Public constructor is the :func:`true()` function.

    """

    __visit_name__ = 'true'

    def __init__(self):
        self.type = sqltypes.BOOLEANTYPE

    def compare(self, other):
        return isinstance(other, True_)


class ClauseList(ClauseElement):
    """Describe a list of clauses, separated by an operator.

    By default, is comma-separated, such as a column listing.

    """
    __visit_name__ = 'clauselist'

    def __init__(self, *clauses, **kwargs):
        self.operator = kwargs.pop('operator', operators.comma_op)
        self.group = kwargs.pop('group', True)
        self.group_contents = kwargs.pop('group_contents', True)
        if self.group_contents:
            self.clauses = [
                _literal_as_text(clause).self_group(against=self.operator)
                for clause in clauses if clause is not None]
        else:
            self.clauses = [
                _literal_as_text(clause)
                for clause in clauses if clause is not None]

    def __iter__(self):
        return iter(self.clauses)

    def __len__(self):
        return len(self.clauses)

    @property
    def _select_iterable(self):
        return iter(self)

    def append(self, clause):
        # TODO: not sure if i like the 'group_contents' flag.  need to
        # define the difference between a ClauseList of ClauseLists,
        # and a "flattened" ClauseList of ClauseLists.  flatten()
        # method ?
        if self.group_contents:
            self.clauses.append(_literal_as_text(clause).\
                                self_group(against=self.operator))
        else:
            self.clauses.append(_literal_as_text(clause))

    def _copy_internals(self, clone=_clone, **kw):
        self.clauses = [clone(clause, **kw) for clause in self.clauses]

    def get_children(self, **kwargs):
        return self.clauses

    @property
    def _from_objects(self):
        return list(itertools.chain(*[c._from_objects for c in self.clauses]))

    def self_group(self, against=None):
        if self.group and operators.is_precedent(self.operator, against):
            return Grouping(self)
        else:
            return self

    def compare(self, other, **kw):
        """Compare this :class:`.ClauseList` to the given :class:`.ClauseList`,
        including a comparison of all the clause items.

        """
        if not isinstance(other, ClauseList) and len(self.clauses) == 1:
            return self.clauses[0].compare(other, **kw)
        elif isinstance(other, ClauseList) and \
                len(self.clauses) == len(other.clauses):
            for i in range(0, len(self.clauses)):
                if not self.clauses[i].compare(other.clauses[i], **kw):
                    return False
            else:
                return self.operator == other.operator
        else:
            return False


class BooleanClauseList(ClauseList, ColumnElement):
    __visit_name__ = 'clauselist'

    def __init__(self, *clauses, **kwargs):
        super(BooleanClauseList, self).__init__(*clauses, **kwargs)
        self.type = sqltypes.to_instance(kwargs.get('type_',
                sqltypes.Boolean))

    @property
    def _select_iterable(self):
        return (self, )

    def self_group(self, against=None):
        if not self.clauses:
            return self
        else:
            return super(BooleanClauseList, self).self_group(against=against)


class Tuple(ClauseList, ColumnElement):

    def __init__(self, *clauses, **kw):
        clauses = [_literal_as_binds(c) for c in clauses]
        self.type = kw.pop('type_', None)
        if self.type is None:
            self.type = _type_from_args(clauses)
        super(Tuple, self).__init__(*clauses, **kw)

    @property
    def _select_iterable(self):
        return (self, )

    def _bind_param(self, operator, obj):
        return Tuple(*[
            BindParameter(None, o, _compared_to_operator=operator,
                             _compared_to_type=self.type, unique=True)
            for o in obj
        ]).self_group()


class Case(ColumnElement):
    __visit_name__ = 'case'

    def __init__(self, whens, value=None, else_=None):
        try:
            whens = util.dictlike_iteritems(whens)
        except TypeError:
            pass

        if value is not None:
            whenlist = [
                (_literal_as_binds(c).self_group(),
                _literal_as_binds(r)) for (c, r) in whens
            ]
        else:
            whenlist = [
                (_no_literals(c).self_group(),
                _literal_as_binds(r)) for (c, r) in whens
            ]

        if whenlist:
            type_ = list(whenlist[-1])[-1].type
        else:
            type_ = None

        if value is None:
            self.value = None
        else:
            self.value = _literal_as_binds(value)

        self.type = type_
        self.whens = whenlist
        if else_ is not None:
            self.else_ = _literal_as_binds(else_)
        else:
            self.else_ = None

    def _copy_internals(self, clone=_clone, **kw):
        if self.value is not None:
            self.value = clone(self.value, **kw)
        self.whens = [(clone(x, **kw), clone(y, **kw))
                            for x, y in self.whens]
        if self.else_ is not None:
            self.else_ = clone(self.else_, **kw)

    def get_children(self, **kwargs):
        if self.value is not None:
            yield self.value
        for x, y in self.whens:
            yield x
            yield y
        if self.else_ is not None:
            yield self.else_

    @property
    def _from_objects(self):
        return list(itertools.chain(*[x._from_objects for x in
                    self.get_children()]))


class FunctionElement(Executable, ColumnElement, FromClause):
    """Base for SQL function-oriented constructs.

    .. seealso::

        :class:`.Function` - named SQL function.

        :data:`.func` - namespace which produces registered or ad-hoc
        :class:`.Function` instances.

        :class:`.GenericFunction` - allows creation of registered function
        types.

    """

    packagenames = ()

    def __init__(self, *clauses, **kwargs):
        """Construct a :class:`.FunctionElement`.
        """
        args = [_literal_as_binds(c, self.name) for c in clauses]
        self.clause_expr = ClauseList(
                                operator=operators.comma_op,
                                 group_contents=True, *args).\
                                 self_group()

    @property
    def columns(self):
        """Fulfill the 'columns' contract of :class:`.ColumnElement`.

        Returns a single-element list consisting of this object.

        """
        return [self]

    @util.memoized_property
    def clauses(self):
        """Return the underlying :class:`.ClauseList` which contains
        the arguments for this :class:`.FunctionElement`.

        """
        return self.clause_expr.element

    def over(self, partition_by=None, order_by=None):
        """Produce an OVER clause against this function.

        Used against aggregate or so-called "window" functions,
        for database backends that support window functions.

        The expression::

            func.row_number().over(order_by='x')

        is shorthand for::

            from sqlalchemy import over
            over(func.row_number(), order_by='x')

        See :func:`~.expression.over` for a full description.

        .. versionadded:: 0.7

        """
        return over(self, partition_by=partition_by, order_by=order_by)

    @property
    def _from_objects(self):
        return self.clauses._from_objects

    def get_children(self, **kwargs):
        return self.clause_expr,

    def _copy_internals(self, clone=_clone, **kw):
        self.clause_expr = clone(self.clause_expr, **kw)
        self._reset_exported()
        FunctionElement.clauses._reset(self)

    def select(self):
        """Produce a :func:`~.expression.select` construct
        against this :class:`.FunctionElement`.

        This is shorthand for::

            s = select([function_element])

        """
        s = select([self])
        if self._execution_options:
            s = s.execution_options(**self._execution_options)
        return s

    def scalar(self):
        """Execute this :class:`.FunctionElement` against an embedded
        'bind' and return a scalar value.

        This first calls :meth:`~.FunctionElement.select` to
        produce a SELECT construct.

        Note that :class:`.FunctionElement` can be passed to
        the :meth:`.Connectable.scalar` method of :class:`.Connection`
        or :class:`.Engine`.

        """
        return self.select().execute().scalar()

    def execute(self):
        """Execute this :class:`.FunctionElement` against an embedded
        'bind'.

        This first calls :meth:`~.FunctionElement.select` to
        produce a SELECT construct.

        Note that :class:`.FunctionElement` can be passed to
        the :meth:`.Connectable.execute` method of :class:`.Connection`
        or :class:`.Engine`.

        """
        return self.select().execute()

    def _bind_param(self, operator, obj):
        return BindParameter(None, obj, _compared_to_operator=operator,
                                _compared_to_type=self.type, unique=True)


class Function(FunctionElement):
    """Describe a named SQL function.

    See the superclass :class:`.FunctionElement` for a description
    of public methods.

    .. seealso::

        :data:`.func` - namespace which produces registered or ad-hoc
        :class:`.Function` instances.

        :class:`.GenericFunction` - allows creation of registered function
        types.

    """

    __visit_name__ = 'function'

    def __init__(self, name, *clauses, **kw):
        """Construct a :class:`.Function`.

        The :data:`.func` construct is normally used to construct
        new :class:`.Function` instances.

        """
        self.packagenames = kw.pop('packagenames', None) or []
        self.name = name
        self._bind = kw.get('bind', None)
        self.type = sqltypes.to_instance(kw.get('type_', None))

        FunctionElement.__init__(self, *clauses, **kw)

    def _bind_param(self, operator, obj):
        return BindParameter(self.name, obj,
                                _compared_to_operator=operator,
                                _compared_to_type=self.type,
                                unique=True)


class Cast(ColumnElement):

    __visit_name__ = 'cast'

    def __init__(self, clause, totype, **kwargs):
        self.type = sqltypes.to_instance(totype)
        self.clause = _literal_as_binds(clause, None)
        self.typeclause = TypeClause(self.type)

    def _copy_internals(self, clone=_clone, **kw):
        self.clause = clone(self.clause, **kw)
        self.typeclause = clone(self.typeclause, **kw)

    def get_children(self, **kwargs):
        return self.clause, self.typeclause

    @property
    def _from_objects(self):
        return self.clause._from_objects


class Extract(ColumnElement):

    __visit_name__ = 'extract'

    def __init__(self, field, expr, **kwargs):
        self.type = sqltypes.Integer()
        self.field = field
        self.expr = _literal_as_binds(expr, None)

    def _copy_internals(self, clone=_clone, **kw):
        self.expr = clone(self.expr, **kw)

    def get_children(self, **kwargs):
        return self.expr,

    @property
    def _from_objects(self):
        return self.expr._from_objects


class UnaryExpression(ColumnElement):
    """Define a 'unary' expression.

    A unary expression has a single column expression
    and an operator.  The operator can be placed on the left
    (where it is called the 'operator') or right (where it is called the
    'modifier') of the column expression.

    """
    __visit_name__ = 'unary'

    def __init__(self, element, operator=None, modifier=None,
                            type_=None, negate=None):
        self.operator = operator
        self.modifier = modifier

        self.element = _literal_as_text(element).\
                    self_group(against=self.operator or self.modifier)
        self.type = sqltypes.to_instance(type_)
        self.negate = negate

    @property
    def _from_objects(self):
        return self.element._from_objects

    def _copy_internals(self, clone=_clone, **kw):
        self.element = clone(self.element, **kw)

    def get_children(self, **kwargs):
        return self.element,

    def compare(self, other, **kw):
        """Compare this :class:`UnaryExpression` against the given
        :class:`.ClauseElement`."""

        return (
            isinstance(other, UnaryExpression) and
            self.operator == other.operator and
            self.modifier == other.modifier and
            self.element.compare(other.element, **kw)
        )

    def _negate(self):
        if self.negate is not None:
            return UnaryExpression(
                self.element,
                operator=self.negate,
                negate=self.operator,
                modifier=self.modifier,
                type_=self.type)
        else:
            return super(UnaryExpression, self)._negate()

    def self_group(self, against=None):
        if self.operator and operators.is_precedent(self.operator,
                against):
            return Grouping(self)
        else:
            return self


class BinaryExpression(ColumnElement):
    """Represent an expression that is ``LEFT <operator> RIGHT``.

    A :class:`.BinaryExpression` is generated automatically
    whenever two column expressions are used in a Python binary expresion::

        >>> from sqlalchemy.sql import column
        >>> column('a') + column('b')
        <sqlalchemy.sql.expression.BinaryExpression object at 0x101029dd0>
        >>> print column('a') + column('b')
        a + b

    """

    __visit_name__ = 'binary'

    def __init__(self, left, right, operator, type_=None,
                    negate=None, modifiers=None):
        # allow compatibility with libraries that
        # refer to BinaryExpression directly and pass strings
        if isinstance(operator, basestring):
            operator = operators.custom_op(operator)
        self._orig = (left, right)
        self.left = _literal_as_text(left).self_group(against=operator)
        self.right = _literal_as_text(right).self_group(against=operator)
        self.operator = operator
        self.type = sqltypes.to_instance(type_)
        self.negate = negate

        if modifiers is None:
            self.modifiers = {}
        else:
            self.modifiers = modifiers

    def __nonzero__(self):
        if self.operator in (operator.eq, operator.ne):
            return self.operator(hash(self._orig[0]), hash(self._orig[1]))
        else:
            raise TypeError("Boolean value of this clause is not defined")

    @property
    def is_comparison(self):
        return operators.is_comparison(self.operator)

    @property
    def _from_objects(self):
        return self.left._from_objects + self.right._from_objects

    def _copy_internals(self, clone=_clone, **kw):
        self.left = clone(self.left, **kw)
        self.right = clone(self.right, **kw)

    def get_children(self, **kwargs):
        return self.left, self.right

    def compare(self, other, **kw):
        """Compare this :class:`BinaryExpression` against the
        given :class:`BinaryExpression`."""

        return (
            isinstance(other, BinaryExpression) and
            self.operator == other.operator and
            (
                self.left.compare(other.left, **kw) and
                self.right.compare(other.right, **kw) or
                (
                    operators.is_commutative(self.operator) and
                    self.left.compare(other.right, **kw) and
                    self.right.compare(other.left, **kw)
                )
            )
        )

    def self_group(self, against=None):
        if operators.is_precedent(self.operator, against):
            return Grouping(self)
        else:
            return self

    def _negate(self):
        if self.negate is not None:
            return BinaryExpression(
                self.left,
                self.right,
                self.negate,
                negate=self.operator,
                type_=sqltypes.BOOLEANTYPE,
                modifiers=self.modifiers)
        else:
            return super(BinaryExpression, self)._negate()


class Exists(UnaryExpression):
    __visit_name__ = UnaryExpression.__visit_name__
    _from_objects = []

    def __init__(self, *args, **kwargs):
        if args and isinstance(args[0], (SelectBase, ScalarSelect)):
            s = args[0]
        else:
            if not args:
                args = ([literal_column('*')],)
            s = select(*args, **kwargs).as_scalar().self_group()

        UnaryExpression.__init__(self, s, operator=operators.exists,
                                  type_=sqltypes.Boolean)

    def select(self, whereclause=None, **params):
        return select([self], whereclause, **params)

    def correlate(self, *fromclause):
        e = self._clone()
        e.element = self.element.correlate(*fromclause).self_group()
        return e

    def correlate_except(self, *fromclause):
        e = self._clone()
        e.element = self.element.correlate_except(*fromclause).self_group()
        return e

    def select_from(self, clause):
        """return a new :class:`.Exists` construct, applying the given
        expression to the :meth:`.Select.select_from` method of the select
        statement contained.

        """
        e = self._clone()
        e.element = self.element.select_from(clause).self_group()
        return e

    def where(self, clause):
        """return a new exists() construct with the given expression added to
        its WHERE clause, joined to the existing clause via AND, if any.

        """
        e = self._clone()
        e.element = self.element.where(clause).self_group()
        return e


class Join(FromClause):
    """represent a ``JOIN`` construct between two :class:`.FromClause`
    elements.

    The public constructor function for :class:`.Join` is the module-level
    :func:`join()` function, as well as the :func:`join()` method available
    off all :class:`.FromClause` subclasses.

    """
    __visit_name__ = 'join'

    def __init__(self, left, right, onclause=None, isouter=False):
        """Construct a new :class:`.Join`.

        The usual entrypoint here is the :func:`~.expression.join`
        function or the :meth:`.FromClause.join` method of any
        :class:`.FromClause` object.

        """
        self.left = _interpret_as_from(left)
        self.right = _interpret_as_from(right).self_group()

        if onclause is None:
            self.onclause = self._match_primaries(self.left, self.right)
        else:
            self.onclause = onclause

        self.isouter = isouter

    @property
    def description(self):
        return "Join object on %s(%d) and %s(%d)" % (
            self.left.description,
            id(self.left),
            self.right.description,
            id(self.right))

    def is_derived_from(self, fromclause):
        return fromclause is self or \
                self.left.is_derived_from(fromclause) or \
                self.right.is_derived_from(fromclause)

    def self_group(self, against=None):
        return FromGrouping(self)

    def _populate_column_collection(self):
        columns = [c for c in self.left.columns] + \
                        [c for c in self.right.columns]

        self.primary_key.extend(sqlutil.reduce_columns(
                (c for c in columns if c.primary_key), self.onclause))
        self._columns.update((col._label, col) for col in columns)
        self.foreign_keys.update(itertools.chain(
                        *[col.foreign_keys for col in columns]))

    def _refresh_for_new_column(self, column):
        col = self.left._refresh_for_new_column(column)
        if col is None:
            col = self.right._refresh_for_new_column(column)
        if col is not None:
            if self._cols_populated:
                self._columns[col._label] = col
                self.foreign_keys.add(col)
                if col.primary_key:
                    self.primary_key.add(col)
                return col
        return None

    def _copy_internals(self, clone=_clone, **kw):
        self._reset_exported()
        self.left = clone(self.left, **kw)
        self.right = clone(self.right, **kw)
        self.onclause = clone(self.onclause, **kw)

    def get_children(self, **kwargs):
        return self.left, self.right, self.onclause

    def _match_primaries(self, left, right):
        if isinstance(left, Join):
            left_right = left.right
        else:
            left_right = None
        return sqlutil.join_condition(left, right, a_subset=left_right)

    def select(self, whereclause=None, **kwargs):
        """Create a :class:`.Select` from this :class:`.Join`.

        The equivalent long-hand form, given a :class:`.Join` object
        ``j``, is::

            from sqlalchemy import select
            j = select([j.left, j.right], **kw).\\
                        where(whereclause).\\
                        select_from(j)

        :param whereclause: the WHERE criterion that will be sent to
          the :func:`select()` function

        :param \**kwargs: all other kwargs are sent to the
          underlying :func:`select()` function.

        """
        collist = [self.left, self.right]

        return select(collist, whereclause, from_obj=[self], **kwargs)

    @property
    def bind(self):
        return self.left.bind or self.right.bind

    def alias(self, name=None):
        """return an alias of this :class:`.Join`.

        Used against a :class:`.Join` object,
        :meth:`~.Join.alias` calls the :meth:`~.Join.select`
        method first so that a subquery against a
        :func:`.select` construct is generated.
        the :func:`~expression.select` construct also has the
        ``correlate`` flag set to ``False`` and will not
        auto-correlate inside an enclosing :func:`~expression.select`
        construct.

        The equivalent long-hand form, given a :class:`.Join` object
        ``j``, is::

            from sqlalchemy import select, alias
            j = alias(
                select([j.left, j.right]).\\
                    select_from(j).\\
                    with_labels(True).\\
                    correlate(False),
                name=name
            )

        See :func:`~.expression.alias` for further details on
        aliases.

        """
        return self.select(use_labels=True, correlate=False).alias(name)

    @property
    def _hide_froms(self):
        return itertools.chain(*[_from_objects(x.left, x.right)
                               for x in self._cloned_set])

    @property
    def _from_objects(self):
        return [self] + \
                self.onclause._from_objects + \
                self.left._from_objects + \
                self.right._from_objects


class Alias(FromClause):
    """Represents an table or selectable alias (AS).

    Represents an alias, as typically applied to any table or
    sub-select within a SQL statement using the ``AS`` keyword (or
    without the keyword on certain databases such as Oracle).

    This object is constructed from the :func:`~.expression.alias` module level
    function as well as the :meth:`.FromClause.alias` method available on all
    :class:`.FromClause` subclasses.

    """

    __visit_name__ = 'alias'
    named_with_column = True

    def __init__(self, selectable, name=None):
        baseselectable = selectable
        while isinstance(baseselectable, Alias):
            baseselectable = baseselectable.element
        self.original = baseselectable
        self.supports_execution = baseselectable.supports_execution
        if self.supports_execution:
            self._execution_options = baseselectable._execution_options
        self.element = selectable
        if name is None:
            if self.original.named_with_column:
                name = getattr(self.original, 'name', None)
            name = _anonymous_label('%%(%d %s)s' % (id(self), name
                    or 'anon'))
        self.name = name

    @property
    def description(self):
        # Py3K
        #return self.name
        # Py2K
        return self.name.encode('ascii', 'backslashreplace')
        # end Py2K

    def as_scalar(self):
        try:
            return self.element.as_scalar()
        except AttributeError:
            raise AttributeError("Element %s does not support "
                                 "'as_scalar()'" % self.element)

    def is_derived_from(self, fromclause):
        if fromclause in self._cloned_set:
            return True
        return self.element.is_derived_from(fromclause)

    def _populate_column_collection(self):
        for col in self.element.columns:
            col._make_proxy(self)

    def _refresh_for_new_column(self, column):
        col = self.element._refresh_for_new_column(column)
        if col is not None:
            if not self._cols_populated:
                return None
            else:
                return col._make_proxy(self)
        else:
            return None

    def _copy_internals(self, clone=_clone, **kw):
        # don't apply anything to an aliased Table
        # for now.   May want to drive this from
        # the given **kw.
        if isinstance(self.element, TableClause):
            return
        self._reset_exported()
        self.element = clone(self.element, **kw)
        baseselectable = self.element
        while isinstance(baseselectable, Alias):
            baseselectable = baseselectable.element
        self.original = baseselectable

    def get_children(self, column_collections=True, **kw):
        if column_collections:
            for c in self.c:
                yield c
        yield self.element

    @property
    def _from_objects(self):
        return [self]

    @property
    def bind(self):
        return self.element.bind


class CTE(Alias):
    """Represent a Common Table Expression.

    The :class:`.CTE` object is obtained using the
    :meth:`.SelectBase.cte` method from any selectable.
    See that method for complete examples.

    .. versionadded:: 0.7.6

    """
    __visit_name__ = 'cte'

    def __init__(self, selectable,
                        name=None,
                        recursive=False,
                        _cte_alias=None,
                        _restates=frozenset()):
        self.recursive = recursive
        self._cte_alias = _cte_alias
        self._restates = _restates
        super(CTE, self).__init__(selectable, name=name)

    def alias(self, name=None):
        return CTE(
            self.original,
            name=name,
            recursive=self.recursive,
            _cte_alias=self,
          )

    def union(self, other):
        return CTE(
            self.original.union(other),
            name=self.name,
            recursive=self.recursive,
            _restates=self._restates.union([self])
        )

    def union_all(self, other):
        return CTE(
            self.original.union_all(other),
            name=self.name,
            recursive=self.recursive,
            _restates=self._restates.union([self])
        )


class Grouping(ColumnElement):
    """Represent a grouping within a column expression"""

    __visit_name__ = 'grouping'

    def __init__(self, element):
        self.element = element
        self.type = getattr(element, 'type', sqltypes.NULLTYPE)

    @property
    def _label(self):
        return getattr(self.element, '_label', None) or self.anon_label

    def _copy_internals(self, clone=_clone, **kw):
        self.element = clone(self.element, **kw)

    def get_children(self, **kwargs):
        return self.element,

    @property
    def _from_objects(self):
        return self.element._from_objects

    def __getattr__(self, attr):
        return getattr(self.element, attr)

    def __getstate__(self):
        return {'element': self.element, 'type': self.type}

    def __setstate__(self, state):
        self.element = state['element']
        self.type = state['type']

    def compare(self, other, **kw):
        return isinstance(other, Grouping) and \
            self.element.compare(other.element)


class FromGrouping(FromClause):
    """Represent a grouping of a FROM clause"""
    __visit_name__ = 'grouping'

    def __init__(self, element):
        self.element = element

    def _init_collections(self):
        pass

    @property
    def columns(self):
        return self.element.columns

    @property
    def primary_key(self):
        return self.element.primary_key

    @property
    def foreign_keys(self):
        # this could be
        # self.element.foreign_keys
        # see SelectableTest.test_join_condition
        return set()

    @property
    def _hide_froms(self):
        return self.element._hide_froms

    def get_children(self, **kwargs):
        return self.element,

    def _copy_internals(self, clone=_clone, **kw):
        self.element = clone(self.element, **kw)

    @property
    def _from_objects(self):
        return self.element._from_objects

    def __getattr__(self, attr):
        return getattr(self.element, attr)

    def __getstate__(self):
        return {'element': self.element}

    def __setstate__(self, state):
        self.element = state['element']


class Over(ColumnElement):
    """Represent an OVER clause.

    This is a special operator against a so-called
    "window" function, as well as any aggregate function,
    which produces results relative to the result set
    itself.  It's supported only by certain database
    backends.

    """
    __visit_name__ = 'over'

    order_by = None
    partition_by = None

    def __init__(self, func, partition_by=None, order_by=None):
        self.func = func
        if order_by is not None:
            self.order_by = ClauseList(*util.to_list(order_by))
        if partition_by is not None:
            self.partition_by = ClauseList(*util.to_list(partition_by))

    @util.memoized_property
    def type(self):
        return self.func.type

    def get_children(self, **kwargs):
        return [c for c in
                (self.func, self.partition_by, self.order_by)
                if c is not None]

    def _copy_internals(self, clone=_clone, **kw):
        self.func = clone(self.func, **kw)
        if self.partition_by is not None:
            self.partition_by = clone(self.partition_by, **kw)
        if self.order_by is not None:
            self.order_by = clone(self.order_by, **kw)

    @property
    def _from_objects(self):
        return list(itertools.chain(
            *[c._from_objects for c in
                (self.func, self.partition_by, self.order_by)
            if c is not None]
        ))


class Label(ColumnElement):
    """Represents a column label (AS).

    Represent a label, as typically applied to any column-level
    element using the ``AS`` sql keyword.

    This object is constructed from the :func:`label()` module level
    function as well as the :func:`label()` method available on all
    :class:`.ColumnElement` subclasses.

    """

    __visit_name__ = 'label'

    def __init__(self, name, element, type_=None):
        while isinstance(element, Label):
            element = element.element
        if name:
            self.name = name
        else:
            self.name = _anonymous_label('%%(%d %s)s' % (id(self),
                                getattr(element, 'name', 'anon')))
        self.key = self._label = self._key_label = self.name
        self._element = element
        self._type = type_
        self.quote = element.quote
        self._proxies = [element]

    def __reduce__(self):
        return self.__class__, (self.name, self._element, self._type)

    @util.memoized_property
    def type(self):
        return sqltypes.to_instance(
                    self._type or getattr(self._element, 'type', None)
                )

    @util.memoized_property
    def element(self):
        return self._element.self_group(against=operators.as_)

    def self_group(self, against=None):
        sub_element = self._element.self_group(against=against)
        if sub_element is not self._element:
            return Label(self.name,
                        sub_element,
                        type_=self._type)
        else:
            return self

    @property
    def primary_key(self):
        return self.element.primary_key

    @property
    def foreign_keys(self):
        return self.element.foreign_keys

    def get_children(self, **kwargs):
        return self.element,

    def _copy_internals(self, clone=_clone, **kw):
        self.element = clone(self.element, **kw)

    @property
    def _from_objects(self):
        return self.element._from_objects

    def _make_proxy(self, selectable, name=None, **kw):
        e = self.element._make_proxy(selectable,
                                name=name if name else self.name)
        e._proxies.append(self)
        if self._type is not None:
            e.type = self._type
        return e


class ColumnClause(Immutable, ColumnElement):
    """Represents a generic column expression from any textual string.

    This includes columns associated with tables, aliases and select
    statements, but also any arbitrary text.  May or may not be bound
    to an underlying :class:`.Selectable`.

    :class:`.ColumnClause` is constructed by itself typically via
    the :func:`~.expression.column` function.  It may be placed directly
    into constructs such as :func:`.select` constructs::

        from sqlalchemy.sql import column, select

        c1, c2 = column("c1"), column("c2")
        s = select([c1, c2]).where(c1==5)

    There is also a variant on :func:`~.expression.column` known
    as :func:`~.expression.literal_column` - the difference is that
    in the latter case, the string value is assumed to be an exact
    expression, rather than a column name, so that no quoting rules
    or similar are applied::

        from sqlalchemy.sql import literal_column, select

        s = select([literal_column("5 + 7")])

    :class:`.ColumnClause` can also be used in a table-like
    fashion by combining the :func:`~.expression.column` function
    with the :func:`~.expression.table` function, to produce
    a "lightweight" form of table metadata::

        from sqlalchemy.sql import table, column

        user = table("user",
                column("id"),
                column("name"),
                column("description"),
        )

    The above construct can be created in an ad-hoc fashion and is
    not associated with any :class:`.schema.MetaData`, unlike it's
    more full fledged :class:`.schema.Table` counterpart.

    :param text: the text of the element.

    :param selectable: parent selectable.

    :param type: :class:`.types.TypeEngine` object which can associate
      this :class:`.ColumnClause` with a type.

    :param is_literal: if True, the :class:`.ColumnClause` is assumed to
      be an exact expression that will be delivered to the output with no
      quoting rules applied regardless of case sensitive settings. the
      :func:`literal_column()` function is usually used to create such a
      :class:`.ColumnClause`.


    """
    __visit_name__ = 'column'

    onupdate = default = server_default = server_onupdate = None

    _memoized_property = util.group_expirable_memoized_property()

    def __init__(self, text, selectable=None, type_=None, is_literal=False):
        self.key = self.name = text
        self.table = selectable
        self.type = sqltypes.to_instance(type_)
        self.is_literal = is_literal

    def _compare_name_for_result(self, other):
        if self.is_literal or \
            self.table is None or \
            not hasattr(other, 'proxy_set') or (
            isinstance(other, ColumnClause) and other.is_literal
        ):
            return super(ColumnClause, self).\
                    _compare_name_for_result(other)
        else:
            return other.proxy_set.intersection(self.proxy_set)

    def _get_table(self):
        return self.__dict__['table']

    def _set_table(self, table):
        self._memoized_property.expire_instance(self)
        self.__dict__['table'] = table
    table = property(_get_table, _set_table)

    @_memoized_property
    def _from_objects(self):
        t = self.table
        if t is not None:
            return [t]
        else:
            return []

    @util.memoized_property
    def description(self):
        # Py3K
        #return self.name
        # Py2K
        return self.name.encode('ascii', 'backslashreplace')
        # end Py2K

    @_memoized_property
    def _key_label(self):
        if self.key != self.name:
            return self._gen_label(self.key)
        else:
            return self._label

    @_memoized_property
    def _label(self):
        return self._gen_label(self.name)

    def _gen_label(self, name):
        t = self.table
        if self.is_literal:
            return None

        elif t is not None and t.named_with_column:
            if getattr(t, 'schema', None):
                label = t.schema.replace('.', '_') + "_" + \
                            t.name + "_" + name
            else:
                label = t.name + "_" + name

            # ensure the label name doesn't conflict with that
            # of an existing column
            if label in t.c:
                _label = label
                counter = 1
                while _label in t.c:
                    _label = label + "_" + str(counter)
                    counter += 1
                label = _label

            return _as_truncated(label)

        else:
            return name

    def _bind_param(self, operator, obj):
        return BindParameter(self.name, obj,
                                _compared_to_operator=operator,
                                _compared_to_type=self.type,
                                unique=True)

    def _make_proxy(self, selectable, name=None, attach=True,
                            name_is_truncatable=False, **kw):
        # propagate the "is_literal" flag only if we are keeping our name,
        # otherwise its considered to be a label
        is_literal = self.is_literal and (name is None or name == self.name)
        c = self._constructor(
                    _as_truncated(name or self.name) if \
                                    name_is_truncatable else \
                                    (name or self.name),
                    selectable=selectable,
                    type_=self.type,
                    is_literal=is_literal
                )
        if name is None:
            c.key = self.key
        c._proxies = [self]
        if selectable._is_clone_of is not None:
            c._is_clone_of = \
                selectable._is_clone_of.columns.get(c.key)

        if attach:
            selectable._columns[c.key] = c
        return c


class TableClause(Immutable, FromClause):
    """Represents a minimal "table" construct.

    The constructor for :class:`.TableClause` is the
    :func:`~.expression.table` function.   This produces
    a lightweight table object that has only a name and a
    collection of columns, which are typically produced
    by the :func:`~.expression.column` function::

        from sqlalchemy.sql import table, column

        user = table("user",
                column("id"),
                column("name"),
                column("description"),
        )

    The :class:`.TableClause` construct serves as the base for
    the more commonly used :class:`~.schema.Table` object, providing
    the usual set of :class:`~.expression.FromClause` services including
    the ``.c.`` collection and statement generation methods.

    It does **not** provide all the additional schema-level services
    of :class:`~.schema.Table`, including constraints, references to other
    tables, or support for :class:`.MetaData`-level services.  It's useful
    on its own as an ad-hoc construct used to generate quick SQL
    statements when a more fully fledged :class:`~.schema.Table`
    is not on hand.

    """

    __visit_name__ = 'table'

    named_with_column = True

    implicit_returning = False
    """:class:`.TableClause` doesn't support having a primary key or column
    -level defaults, so implicit returning doesn't apply."""

    _autoincrement_column = None
    """No PK or default support so no autoincrement column."""

    def __init__(self, name, *columns):
        super(TableClause, self).__init__()
        self.name = self.fullname = name
        self._columns = ColumnCollection()
        self.primary_key = ColumnSet()
        self.foreign_keys = set()
        for c in columns:
            self.append_column(c)

    def _init_collections(self):
        pass

    @util.memoized_property
    def description(self):
        # Py3K
        #return self.name
        # Py2K
        return self.name.encode('ascii', 'backslashreplace')
        # end Py2K

    def append_column(self, c):
        self._columns[c.key] = c
        c.table = self

    def get_children(self, column_collections=True, **kwargs):
        if column_collections:
            return [c for c in self.c]
        else:
            return []

    def count(self, whereclause=None, **params):
        """return a SELECT COUNT generated against this
        :class:`.TableClause`."""

        if self.primary_key:
            col = list(self.primary_key)[0]
        else:
            col = list(self.columns)[0]
        return select(
                    [func.count(col).label('tbl_row_count')],
                    whereclause,
                    from_obj=[self],
                    **params)

    def insert(self, values=None, inline=False, **kwargs):
        """Generate an :func:`.insert` construct against this
        :class:`.TableClause`.

        E.g.::

            table.insert().values(name='foo')

        See :func:`.insert` for argument and usage information.

        """

        return insert(self, values=values, inline=inline, **kwargs)

    def update(self, whereclause=None, values=None, inline=False, **kwargs):
        """Generate an :func:`.update` construct against this
        :class:`.TableClause`.

        E.g.::

            table.update().where(table.c.id==7).values(name='foo')

        See :func:`.update` for argument and usage information.

        """

        return update(self, whereclause=whereclause,
                            values=values, inline=inline, **kwargs)

    def delete(self, whereclause=None, **kwargs):
        """Generate a :func:`.delete` construct against this
        :class:`.TableClause`.

        E.g.::

            table.delete().where(table.c.id==7)

        See :func:`.delete` for argument and usage information.

        """

        return delete(self, whereclause, **kwargs)

    @property
    def _from_objects(self):
        return [self]


class SelectBase(Executable, FromClause):
    """Base class for :class:`.Select` and :class:`.CompoundSelect`."""

    _order_by_clause = ClauseList()
    _group_by_clause = ClauseList()
    _limit = None
    _offset = None

    def __init__(self,
            use_labels=False,
            for_update=False,
            limit=None,
            offset=None,
            order_by=None,
            group_by=None,
            bind=None,
            autocommit=None):
        self.use_labels = use_labels
        self.for_update = for_update
        if autocommit is not None:
            util.warn_deprecated('autocommit on select() is '
                                 'deprecated.  Use .execution_options(a'
                                 'utocommit=True)')
            self._execution_options = \
                self._execution_options.union(
                  {'autocommit': autocommit})
        if limit is not None:
            self._limit = util.asint(limit)
        if offset is not None:
            self._offset = util.asint(offset)
        self._bind = bind

        if order_by is not None:
            self._order_by_clause = ClauseList(*util.to_list(order_by))
        if group_by is not None:
            self._group_by_clause = ClauseList(*util.to_list(group_by))

    def as_scalar(self):
        """return a 'scalar' representation of this selectable, which can be
        used as a column expression.

        Typically, a select statement which has only one column in its columns
        clause is eligible to be used as a scalar expression.

        The returned object is an instance of
        :class:`ScalarSelect`.

        """
        return ScalarSelect(self)

    @_generative
    def apply_labels(self):
        """return a new selectable with the 'use_labels' flag set to True.

        This will result in column expressions being generated using labels
        against their table name, such as "SELECT somecolumn AS
        tablename_somecolumn". This allows selectables which contain multiple
        FROM clauses to produce a unique set of column names regardless of
        name conflicts among the individual FROM clauses.

        """
        self.use_labels = True

    def label(self, name):
        """return a 'scalar' representation of this selectable, embedded as a
        subquery with a label.

        .. seealso::

            :meth:`~.SelectBase.as_scalar`.

        """
        return self.as_scalar().label(name)

    def cte(self, name=None, recursive=False):
        """Return a new :class:`.CTE`, or Common Table Expression instance.

        Common table expressions are a SQL standard whereby SELECT
        statements can draw upon secondary statements specified along
        with the primary statement, using a clause called "WITH".
        Special semantics regarding UNION can also be employed to
        allow "recursive" queries, where a SELECT statement can draw
        upon the set of rows that have previously been selected.

        SQLAlchemy detects :class:`.CTE` objects, which are treated
        similarly to :class:`.Alias` objects, as special elements
        to be delivered to the FROM clause of the statement as well
        as to a WITH clause at the top of the statement.

        .. versionadded:: 0.7.6

        :param name: name given to the common table expression.  Like
         :meth:`._FromClause.alias`, the name can be left as ``None``
         in which case an anonymous symbol will be used at query
         compile time.
        :param recursive: if ``True``, will render ``WITH RECURSIVE``.
         A recursive common table expression is intended to be used in
         conjunction with UNION ALL in order to derive rows
         from those already selected.

        The following examples illustrate two examples from
        Postgresql's documentation at
        http://www.postgresql.org/docs/8.4/static/queries-with.html.

        Example 1, non recursive::

            from sqlalchemy import Table, Column, String, Integer, MetaData, \\
                select, func

            metadata = MetaData()

            orders = Table('orders', metadata,
                Column('region', String),
                Column('amount', Integer),
                Column('product', String),
                Column('quantity', Integer)
            )

            regional_sales = select([
                                orders.c.region,
                                func.sum(orders.c.amount).label('total_sales')
                            ]).group_by(orders.c.region).cte("regional_sales")


            top_regions = select([regional_sales.c.region]).\\
                    where(
                        regional_sales.c.total_sales >
                        select([
                            func.sum(regional_sales.c.total_sales)/10
                        ])
                    ).cte("top_regions")

            statement = select([
                        orders.c.region,
                        orders.c.product,
                        func.sum(orders.c.quantity).label("product_units"),
                        func.sum(orders.c.amount).label("product_sales")
                ]).where(orders.c.region.in_(
                    select([top_regions.c.region])
                )).group_by(orders.c.region, orders.c.product)

            result = conn.execute(statement).fetchall()

        Example 2, WITH RECURSIVE::

            from sqlalchemy import Table, Column, String, Integer, MetaData, \\
                select, func

            metadata = MetaData()

            parts = Table('parts', metadata,
                Column('part', String),
                Column('sub_part', String),
                Column('quantity', Integer),
            )

            included_parts = select([
                                parts.c.sub_part,
                                parts.c.part,
                                parts.c.quantity]).\\
                                where(parts.c.part=='our part').\\
                                cte(recursive=True)


            incl_alias = included_parts.alias()
            parts_alias = parts.alias()
            included_parts = included_parts.union_all(
                select([
                    parts_alias.c.part,
                    parts_alias.c.sub_part,
                    parts_alias.c.quantity
                ]).
                    where(parts_alias.c.part==incl_alias.c.sub_part)
            )

            statement = select([
                        included_parts.c.sub_part,
                        func.sum(included_parts.c.quantity).
                          label('total_quantity')
                    ]).\
                    select_from(included_parts.join(parts,
                                included_parts.c.part==parts.c.part)).\\
                    group_by(included_parts.c.sub_part)

            result = conn.execute(statement).fetchall()


        .. seealso::

            :meth:`.orm.query.Query.cte` - ORM version of :meth:`.SelectBase.cte`.

        """
        return CTE(self, name=name, recursive=recursive)

    @_generative
    @util.deprecated('0.6',
                     message=":func:`.autocommit` is deprecated. Use "
                     ":func:`.Executable.execution_options` with the "
                     "'autocommit' flag.")
    def autocommit(self):
        """return a new selectable with the 'autocommit' flag set to
        True."""

        self._execution_options = \
            self._execution_options.union({'autocommit': True})

    def _generate(self):
        """Override the default _generate() method to also clear out
        exported collections."""

        s = self.__class__.__new__(self.__class__)
        s.__dict__ = self.__dict__.copy()
        s._reset_exported()
        return s

    @_generative
    def limit(self, limit):
        """return a new selectable with the given LIMIT criterion
        applied."""

        self._limit = util.asint(limit)

    @_generative
    def offset(self, offset):
        """return a new selectable with the given OFFSET criterion
        applied."""

        self._offset = util.asint(offset)

    @_generative
    def order_by(self, *clauses):
        """return a new selectable with the given list of ORDER BY
        criterion applied.

        The criterion will be appended to any pre-existing ORDER BY
        criterion.

        """

        self.append_order_by(*clauses)

    @_generative
    def group_by(self, *clauses):
        """return a new selectable with the given list of GROUP BY
        criterion applied.

        The criterion will be appended to any pre-existing GROUP BY
        criterion.

        """

        self.append_group_by(*clauses)

    def append_order_by(self, *clauses):
        """Append the given ORDER BY criterion applied to this selectable.

        The criterion will be appended to any pre-existing ORDER BY criterion.

        This is an **in-place** mutation method; the
        :meth:`~.SelectBase.order_by` method is preferred, as it provides standard
        :term:`method chaining`.

        """
        if len(clauses) == 1 and clauses[0] is None:
            self._order_by_clause = ClauseList()
        else:
            if getattr(self, '_order_by_clause', None) is not None:
                clauses = list(self._order_by_clause) + list(clauses)
            self._order_by_clause = ClauseList(*clauses)

    def append_group_by(self, *clauses):
        """Append the given GROUP BY criterion applied to this selectable.

        The criterion will be appended to any pre-existing GROUP BY criterion.

        This is an **in-place** mutation method; the
        :meth:`~.SelectBase.group_by` method is preferred, as it provides standard
        :term:`method chaining`.

        """
        if len(clauses) == 1 and clauses[0] is None:
            self._group_by_clause = ClauseList()
        else:
            if getattr(self, '_group_by_clause', None) is not None:
                clauses = list(self._group_by_clause) + list(clauses)
            self._group_by_clause = ClauseList(*clauses)

    @property
    def _from_objects(self):
        return [self]


class ScalarSelect(Generative, Grouping):
    _from_objects = []

    def __init__(self, element):
        self.element = element
        self.type = element._scalar_type()

    @property
    def columns(self):
        raise exc.InvalidRequestError('Scalar Select expression has no '
                'columns; use this object directly within a '
                'column-level expression.')
    c = columns

    @_generative
    def where(self, crit):
        """Apply a WHERE clause to the SELECT statement referred to
        by this :class:`.ScalarSelect`.

        """
        self.element = self.element.where(crit)

    def self_group(self, **kwargs):
        return self


class CompoundSelect(SelectBase):
    """Forms the basis of ``UNION``, ``UNION ALL``, and other
        SELECT-based set operations.

       .. seealso::

          :func:`.union`

          :func:`.union_all`

          :func:`.intersect`

          :func:`.intersect_all`

          :func:`.except`

          :func:`.except_all`

    """

    __visit_name__ = 'compound_select'

    UNION = util.symbol('UNION')
    UNION_ALL = util.symbol('UNION ALL')
    EXCEPT = util.symbol('EXCEPT')
    EXCEPT_ALL = util.symbol('EXCEPT ALL')
    INTERSECT = util.symbol('INTERSECT')
    INTERSECT_ALL = util.symbol('INTERSECT ALL')

    def __init__(self, keyword, *selects, **kwargs):
        self._auto_correlate = kwargs.pop('correlate', False)
        self.keyword = keyword
        self.selects = []

        numcols = None

        # some DBs do not like ORDER BY in the inner queries of a UNION, etc.
        for n, s in enumerate(selects):
            s = _clause_element_as_expr(s)

            if not numcols:
                numcols = len(s.c)
            elif len(s.c) != numcols:
                raise exc.ArgumentError('All selectables passed to '
                        'CompoundSelect must have identical numbers of '
                        'columns; select #%d has %d columns, select '
                        '#%d has %d' % (1, len(self.selects[0].c), n
                        + 1, len(s.c)))

            self.selects.append(s.self_group(self))

        SelectBase.__init__(self, **kwargs)

    def _scalar_type(self):
        return self.selects[0]._scalar_type()

    def self_group(self, against=None):
        return FromGrouping(self)

    def is_derived_from(self, fromclause):
        for s in self.selects:
            if s.is_derived_from(fromclause):
                return True
        return False

    def _populate_column_collection(self):
        for cols in zip(*[s.c for s in self.selects]):

            # this is a slightly hacky thing - the union exports a
            # column that resembles just that of the *first* selectable.
            # to get at a "composite" column, particularly foreign keys,
            # you have to dig through the proxies collection which we
            # generate below.  We may want to improve upon this, such as
            # perhaps _make_proxy can accept a list of other columns
            # that are "shared" - schema.column can then copy all the
            # ForeignKeys in. this would allow the union() to have all
            # those fks too.

            proxy = cols[0]._make_proxy(self,
                    name=cols[0]._label if self.use_labels else None,
                    key=cols[0]._key_label if self.use_labels else None)

            # hand-construct the "_proxies" collection to include all
            # derived columns place a 'weight' annotation corresponding
            # to how low in the list of select()s the column occurs, so
            # that the corresponding_column() operation can resolve
            # conflicts

            proxy._proxies = [c._annotate({'weight': i + 1}) for (i,
                             c) in enumerate(cols)]

    def _refresh_for_new_column(self, column):
        for s in self.selects:
            s._refresh_for_new_column(column)

        if not self._cols_populated:
            return None

        raise NotImplementedError("CompoundSelect constructs don't support "
                "addition of columns to underlying selectables")

    def _copy_internals(self, clone=_clone, **kw):
        self._reset_exported()
        self.selects = [clone(s, **kw) for s in self.selects]
        if hasattr(self, '_col_map'):
            del self._col_map
        for attr in ('_order_by_clause', '_group_by_clause'):
            if getattr(self, attr) is not None:
                setattr(self, attr, clone(getattr(self, attr), **kw))

    def get_children(self, column_collections=True, **kwargs):
        return (column_collections and list(self.c) or []) \
            + [self._order_by_clause, self._group_by_clause] \
            + list(self.selects)

    def bind(self):
        if self._bind:
            return self._bind
        for s in self.selects:
            e = s.bind
            if e:
                return e
        else:
            return None

    def _set_bind(self, bind):
        self._bind = bind
    bind = property(bind, _set_bind)


class HasPrefixes(object):
    _prefixes = ()

    @_generative
    def prefix_with(self, *expr, **kw):
        """Add one or more expressions following the statement keyword, i.e.
        SELECT, INSERT, UPDATE, or DELETE. Generative.

        This is used to support backend-specific prefix keywords such as those
        provided by MySQL.

        E.g.::

            stmt = table.insert().prefix_with("LOW_PRIORITY", dialect="mysql")

        Multiple prefixes can be specified by multiple calls
        to :meth:`.prefix_with`.

        :param \*expr: textual or :class:`.ClauseElement` construct which
         will be rendered following the INSERT, UPDATE, or DELETE
         keyword.
        :param \**kw: A single keyword 'dialect' is accepted.  This is an
         optional string dialect name which will
         limit rendering of this prefix to only that dialect.

        """
        dialect = kw.pop('dialect', None)
        if kw:
            raise exc.ArgumentError("Unsupported argument(s): %s" %
                            ",".join(kw))
        self._setup_prefixes(expr, dialect)

    def _setup_prefixes(self, prefixes, dialect=None):
        self._prefixes = self._prefixes + tuple(
                            [(_literal_as_text(p), dialect) for p in prefixes])


class Select(HasPrefixes, SelectBase):
    """Represents a ``SELECT`` statement.

    .. seealso::

        :func:`~.expression.select` - the function which creates
        a :class:`.Select` object.

        :ref:`coretutorial_selecting` - Core Tutorial description
        of :func:`.select`.

    """

    __visit_name__ = 'select'

    _prefixes = ()
    _hints = util.immutabledict()
    _distinct = False
    _from_cloned = None
    _correlate = ()
    _correlate_except = None
    _memoized_property = SelectBase._memoized_property

    def __init__(self,
                columns,
                whereclause=None,
                from_obj=None,
                distinct=False,
                having=None,
                correlate=True,
                prefixes=None,
                **kwargs):
        """Construct a Select object.

        The public constructor for Select is the
        :func:`select` function; see that function for
        argument descriptions.

        Additional generative and mutator methods are available on the
        :class:`SelectBase` superclass.

        """
        self._auto_correlate = correlate
        if distinct is not False:
            if distinct is True:
                self._distinct = True
            else:
                self._distinct = [
                                _literal_as_text(e)
                                for e in util.to_list(distinct)
                            ]

        if from_obj is not None:
            self._from_obj = util.OrderedSet(
                                _interpret_as_from(f)
                                for f in util.to_list(from_obj))
        else:
            self._from_obj = util.OrderedSet()

        try:
            cols_present = bool(columns)
        except TypeError:
            raise exc.ArgumentError("columns argument to select() must "
                                "be a Python list or other iterable")

        if cols_present:
            self._raw_columns = []
            for c in columns:
                c = _interpret_as_column_or_from(c)
                if isinstance(c, ScalarSelect):
                    c = c.self_group(against=operators.comma_op)
                self._raw_columns.append(c)
        else:
            self._raw_columns = []

        if whereclause is not None:
            self._whereclause = _literal_as_text(whereclause)
        else:
            self._whereclause = None

        if having is not None:
            self._having = _literal_as_text(having)
        else:
            self._having = None

        if prefixes:
            self._setup_prefixes(prefixes)

        SelectBase.__init__(self, **kwargs)

    @property
    def _froms(self):
        # would love to cache this,
        # but there's just enough edge cases, particularly now that
        # declarative encourages construction of SQL expressions
        # without tables present, to just regen this each time.
        froms = []
        seen = set()
        translate = self._from_cloned

        def add(items):
            for item in items:
                if item is self:
                    raise exc.InvalidRequestError(
                            "select() construct refers to itself as a FROM")
                if translate and item in translate:
                    item = translate[item]
                if not seen.intersection(item._cloned_set):
                    froms.append(item)
                seen.update(item._cloned_set)

        add(_from_objects(*self._raw_columns))
        if self._whereclause is not None:
            add(_from_objects(self._whereclause))
        add(self._from_obj)

        return froms

    def _get_display_froms(self, explicit_correlate_froms=None,
                                    implicit_correlate_froms=None):
        """Return the full list of 'from' clauses to be displayed.

        Takes into account a set of existing froms which may be
        rendered in the FROM clause of enclosing selects; this Select
        may want to leave those absent if it is automatically
        correlating.

        """
        froms = self._froms

        toremove = set(itertools.chain(*[
                            _expand_cloned(f._hide_froms)
                            for f in froms]))
        if toremove:
            # if we're maintaining clones of froms,
            # add the copies out to the toremove list.  only include
            # clones that are lexical equivalents.
            if self._from_cloned:
                toremove.update(
                    self._from_cloned[f] for f in
                    toremove.intersection(self._from_cloned)
                    if self._from_cloned[f]._is_lexical_equivalent(f)
                )
            # filter out to FROM clauses not in the list,
            # using a list to maintain ordering
            froms = [f for f in froms if f not in toremove]

        if self._correlate:
            to_correlate = self._correlate
            if to_correlate:
                froms = [
                    f for f in froms if f not in
                    _cloned_intersection(
                        _cloned_intersection(froms, explicit_correlate_froms or ()),
                        to_correlate
                    )
                ]

        if self._correlate_except is not None:

            froms = [
                f for f in froms if f not in
                _cloned_difference(
                    _cloned_intersection(froms, explicit_correlate_froms or ()),
                    self._correlate_except
                )
            ]

        if self._auto_correlate and \
            implicit_correlate_froms and \
            len(froms) > 1:

            froms = [
                f for f in froms if f not in
                _cloned_intersection(froms, implicit_correlate_froms)
            ]

            if not len(froms):
                raise exc.InvalidRequestError("Select statement '%s"
                        "' returned no FROM clauses due to "
                        "auto-correlation; specify "
                        "correlate(<tables>) to control "
                        "correlation manually." % self)

        return froms

    def _scalar_type(self):
        elem = self._raw_columns[0]
        cols = list(elem._select_iterable)
        return cols[0].type

    @property
    def froms(self):
        """Return the displayed list of FromClause elements."""

        return self._get_display_froms()

    @_generative
    def with_hint(self, selectable, text, dialect_name='*'):
        """Add an indexing hint for the given selectable to this
        :class:`.Select`.

        The text of the hint is rendered in the appropriate
        location for the database backend in use, relative
        to the given :class:`.Table` or :class:`.Alias` passed as the
        ``selectable`` argument. The dialect implementation
        typically uses Python string substitution syntax
        with the token ``%(name)s`` to render the name of
        the table or alias. E.g. when using Oracle, the
        following::

            select([mytable]).\\
                with_hint(mytable, "+ index(%(name)s ix_mytable)")

        Would render SQL as::

            select /*+ index(mytable ix_mytable) */ ... from mytable

        The ``dialect_name`` option will limit the rendering of a particular
        hint to a particular backend. Such as, to add hints for both Oracle
        and Sybase simultaneously::

            select([mytable]).\\
                with_hint(mytable, "+ index(%(name)s ix_mytable)", 'oracle').\\
                with_hint(mytable, "WITH INDEX ix_mytable", 'sybase')

        """
        self._hints = self._hints.union(
                    {(selectable, dialect_name): text})

    @property
    def type(self):
        raise exc.InvalidRequestError("Select objects don't have a type.  "
                    "Call as_scalar() on this Select object "
                    "to return a 'scalar' version of this Select.")

    @_memoized_property.method
    def locate_all_froms(self):
        """return a Set of all FromClause elements referenced by this Select.

        This set is a superset of that returned by the ``froms`` property,
        which is specifically for those FromClause elements that would
        actually be rendered.

        """
        froms = self._froms
        return froms + list(_from_objects(*froms))

    @property
    def inner_columns(self):
        """an iterator of all ColumnElement expressions which would
        be rendered into the columns clause of the resulting SELECT statement.

        """
        return _select_iterables(self._raw_columns)

    def is_derived_from(self, fromclause):
        if self in fromclause._cloned_set:
            return True

        for f in self.locate_all_froms():
            if f.is_derived_from(fromclause):
                return True
        return False

    def _copy_internals(self, clone=_clone, **kw):

        # Select() object has been cloned and probably adapted by the
        # given clone function.  Apply the cloning function to internal
        # objects

        # 1. keep a dictionary of the froms we've cloned, and what
        # they've become.  This is consulted later when we derive
        # additional froms from "whereclause" and the columns clause,
        # which may still reference the uncloned parent table.
        # as of 0.7.4 we also put the current version of _froms, which
        # gets cleared on each generation.  previously we were "baking"
        # _froms into self._from_obj.
        self._from_cloned = from_cloned = dict((f, clone(f, **kw))
                for f in self._from_obj.union(self._froms))

        # 3. update persistent _from_obj with the cloned versions.
        self._from_obj = util.OrderedSet(from_cloned[f] for f in
                self._from_obj)

        # the _correlate collection is done separately, what can happen
        # here is the same item is _correlate as in _from_obj but the
        # _correlate version has an annotation on it - (specifically
        # RelationshipProperty.Comparator._criterion_exists() does
        # this). Also keep _correlate liberally open with it's previous
        # contents, as this set is used for matching, not rendering.
        self._correlate = set(clone(f) for f in
                              self._correlate).union(self._correlate)

        # 4. clone other things.   The difficulty here is that Column
        # objects are not actually cloned, and refer to their original
        # .table, resulting in the wrong "from" parent after a clone
        # operation.  Hence _from_cloned and _from_obj supercede what is
        # present here.
        self._raw_columns = [clone(c, **kw) for c in self._raw_columns]
        for attr in '_whereclause', '_having', '_order_by_clause', \
            '_group_by_clause':
            if getattr(self, attr) is not None:
                setattr(self, attr, clone(getattr(self, attr), **kw))

        # erase exported column list, _froms collection,
        # etc.
        self._reset_exported()

    def get_children(self, column_collections=True, **kwargs):
        """return child elements as per the ClauseElement specification."""

        return (column_collections and list(self.columns) or []) + \
            self._raw_columns + list(self._froms) + \
            [x for x in
                (self._whereclause, self._having,
                    self._order_by_clause, self._group_by_clause)
            if x is not None]

    @_generative
    def column(self, column):
        """return a new select() construct with the given column expression
            added to its columns clause.

        """
        self.append_column(column)

    def reduce_columns(self, only_synonyms=True):
        """Return a new :func`.select` construct with redundantly
        named, equivalently-valued columns removed from the columns clause.

        "Redundant" here means two columns where one refers to the
        other either based on foreign key, or via a simple equality
        comparison in the WHERE clause of the statement.   The primary purpose
        of this method is to automatically construct a select statement
        with all uniquely-named columns, without the need to use
        table-qualified labels as :meth:`.apply_labels` does.

        When columns are omitted based on foreign key, the referred-to
        column is the one that's kept.  When columns are omitted based on
        WHERE eqivalence, the first column in the columns clause is the
        one that's kept.

        :param only_synonyms: when True, limit the removal of columns
         to those which have the same name as the equivalent.   Otherwise,
         all columns that are equivalent to another are removed.

        .. versionadded:: 0.8

        """
        return self.with_only_columns(
                sqlutil.reduce_columns(
                        self.inner_columns,
                        only_synonyms=only_synonyms,
                        *(self._whereclause, ) + tuple(self._from_obj)
                )
            )

    @_generative
    def with_only_columns(self, columns):
        """Return a new :func:`.select` construct with its columns
        clause replaced with the given columns.

        .. versionchanged:: 0.7.3
            Due to a bug fix, this method has a slight
            behavioral change as of version 0.7.3.
            Prior to version 0.7.3, the FROM clause of
            a :func:`.select` was calculated upfront and as new columns
            were added; in 0.7.3 and later it's calculated
            at compile time, fixing an issue regarding late binding
            of columns to parent tables.  This changes the behavior of
            :meth:`.Select.with_only_columns` in that FROM clauses no
            longer represented in the new list are dropped,
            but this behavior is more consistent in
            that the FROM clauses are consistently derived from the
            current columns clause.  The original intent of this method
            is to allow trimming of the existing columns list to be fewer
            columns than originally present; the use case of replacing
            the columns list with an entirely different one hadn't
            been anticipated until 0.7.3 was released; the usage
            guidelines below illustrate how this should be done.

        This method is exactly equivalent to as if the original
        :func:`.select` had been called with the given columns
        clause.   I.e. a statement::

            s = select([table1.c.a, table1.c.b])
            s = s.with_only_columns([table1.c.b])

        should be exactly equivalent to::

            s = select([table1.c.b])

        This means that FROM clauses which are only derived
        from the column list will be discarded if the new column
        list no longer contains that FROM::

            >>> table1 = table('t1', column('a'), column('b'))
            >>> table2 = table('t2', column('a'), column('b'))
            >>> s1 = select([table1.c.a, table2.c.b])
            >>> print s1
            SELECT t1.a, t2.b FROM t1, t2
            >>> s2 = s1.with_only_columns([table2.c.b])
            >>> print s2
            SELECT t2.b FROM t1

        The preferred way to maintain a specific FROM clause
        in the construct, assuming it won't be represented anywhere
        else (i.e. not in the WHERE clause, etc.) is to set it using
        :meth:`.Select.select_from`::

            >>> s1 = select([table1.c.a, table2.c.b]).\\
            ...         select_from(table1.join(table2,
            ...                 table1.c.a==table2.c.a))
            >>> s2 = s1.with_only_columns([table2.c.b])
            >>> print s2
            SELECT t2.b FROM t1 JOIN t2 ON t1.a=t2.a

        Care should also be taken to use the correct
        set of column objects passed to :meth:`.Select.with_only_columns`.
        Since the method is essentially equivalent to calling the
        :func:`.select` construct in the first place with the given
        columns, the columns passed to :meth:`.Select.with_only_columns`
        should usually be a subset of those which were passed
        to the :func:`.select` construct, not those which are available
        from the ``.c`` collection of that :func:`.select`.  That
        is::

            s = select([table1.c.a, table1.c.b]).select_from(table1)
            s = s.with_only_columns([table1.c.b])

        and **not**::

            # usually incorrect
            s = s.with_only_columns([s.c.b])

        The latter would produce the SQL::

            SELECT b
            FROM (SELECT t1.a AS a, t1.b AS b
            FROM t1), t1

        Since the :func:`.select` construct is essentially being
        asked to select both from ``table1`` as well as itself.

        """
        self._reset_exported()
        rc = []
        for c in columns:
            c = _interpret_as_column_or_from(c)
            if isinstance(c, ScalarSelect):
                c = c.self_group(against=operators.comma_op)
            rc.append(c)
        self._raw_columns = rc

    @_generative
    def where(self, whereclause):
        """return a new select() construct with the given expression added to
        its WHERE clause, joined to the existing clause via AND, if any.

        """

        self.append_whereclause(whereclause)

    @_generative
    def having(self, having):
        """return a new select() construct with the given expression added to
        its HAVING clause, joined to the existing clause via AND, if any.

        """
        self.append_having(having)

    @_generative
    def distinct(self, *expr):
        """Return a new select() construct which will apply DISTINCT to its
        columns clause.

        :param \*expr: optional column expressions.  When present,
         the Postgresql dialect will render a ``DISTINCT ON (<expressions>>)``
         construct.

        """
        if expr:
            expr = [_literal_as_text(e) for e in expr]
            if isinstance(self._distinct, list):
                self._distinct = self._distinct + expr
            else:
                self._distinct = expr
        else:
            self._distinct = True

    @_generative
    def select_from(self, fromclause):
        """return a new :func:`.select` construct with the
        given FROM expression
        merged into its list of FROM objects.

        E.g.::

            table1 = table('t1', column('a'))
            table2 = table('t2', column('b'))
            s = select([table1.c.a]).\\
                select_from(
                    table1.join(table2, table1.c.a==table2.c.b)
                )

        The "from" list is a unique set on the identity of each element,
        so adding an already present :class:`.Table` or other selectable
        will have no effect.   Passing a :class:`.Join` that refers
        to an already present :class:`.Table` or other selectable will have
        the effect of concealing the presence of that selectable as
        an individual element in the rendered FROM list, instead
        rendering it into a JOIN clause.

        While the typical purpose of :meth:`.Select.select_from` is to
        replace the default, derived FROM clause with a join, it can
        also be called with individual table elements, multiple times
        if desired, in the case that the FROM clause cannot be fully
        derived from the columns clause::

            select([func.count('*')]).select_from(table1)

        """
        self.append_from(fromclause)

    @_generative
    def correlate(self, *fromclauses):
        """return a new :class:`.Select` which will correlate the given FROM
        clauses to that of an enclosing :class:`.Select`.

        Calling this method turns off the :class:`.Select` object's
        default behavior of "auto-correlation".  Normally, FROM elements
        which appear in a :class:`.Select` that encloses this one via
        its :term:`WHERE clause`, ORDER BY, HAVING or
        :term:`columns clause` will be omitted from this :class:`.Select`
        object's :term:`FROM clause`.
        Setting an explicit correlation collection using the
        :meth:`.Select.correlate` method provides a fixed list of FROM objects
        that can potentially take place in this process.

        When :meth:`.Select.correlate` is used to apply specific FROM clauses
        for correlation, the FROM elements become candidates for
        correlation regardless of how deeply nested this :class:`.Select`
        object is, relative to an enclosing :class:`.Select` which refers to
        the same FROM object.  This is in contrast to the behavior of
        "auto-correlation" which only correlates to an immediate enclosing
        :class:`.Select`.   Multi-level correlation ensures that the link
        between enclosed and enclosing :class:`.Select` is always via
        at least one WHERE/ORDER BY/HAVING/columns clause in order for
        correlation to take place.

        If ``None`` is passed, the :class:`.Select` object will correlate
        none of its FROM entries, and all will render unconditionally
        in the local FROM clause.

        :param \*fromclauses: a list of one or more :class:`.FromClause`
         constructs, or other compatible constructs (i.e. ORM-mapped
         classes) to become part of the correlate collection.

         .. versionchanged:: 0.8.0 ORM-mapped classes are accepted by
            :meth:`.Select.correlate`.

        .. versionchanged:: 0.8.0 The :meth:`.Select.correlate` method no
           longer unconditionally removes entries from the FROM clause; instead,
           the candidate FROM entries must also be matched by a FROM entry
           located in an enclosing :class:`.Select`, which ultimately encloses
           this one as present in the WHERE clause, ORDER BY clause, HAVING
           clause, or columns clause of an enclosing :meth:`.Select`.

        .. versionchanged:: 0.8.2 explicit correlation takes place
           via any level of nesting of :class:`.Select` objects; in previous
           0.8 versions, correlation would only occur relative to the immediate
           enclosing :class:`.Select` construct.

        .. seealso::

            :meth:`.Select.correlate_except`

            :ref:`correlated_subqueries`

        """
        self._auto_correlate = False
        if fromclauses and fromclauses[0] is None:
            self._correlate = ()
        else:
            self._correlate = set(self._correlate).union(
                    _interpret_as_from(f) for f in fromclauses)

    @_generative
    def correlate_except(self, *fromclauses):
        """return a new :class:`.Select` which will omit the given FROM
        clauses from the auto-correlation process.

        Calling :meth:`.Select.correlate_except` turns off the
        :class:`.Select` object's default behavior of
        "auto-correlation" for the given FROM elements.  An element
        specified here will unconditionally appear in the FROM list, while
        all other FROM elements remain subject to normal auto-correlation
        behaviors.

        .. versionchanged:: 0.8.2 The :meth:`.Select.correlate_except`
           method was improved to fully prevent FROM clauses specified here
           from being omitted from the immediate FROM clause of this
           :class:`.Select`.

        If ``None`` is passed, the :class:`.Select` object will correlate
        all of its FROM entries.

        .. versionchanged:: 0.8.2 calling ``correlate_except(None)`` will
           correctly auto-correlate all FROM clauses.

        :param \*fromclauses: a list of one or more :class:`.FromClause`
         constructs, or other compatible constructs (i.e. ORM-mapped
         classes) to become part of the correlate-exception collection.

        .. seealso::

            :meth:`.Select.correlate`

            :ref:`correlated_subqueries`

        """

        self._auto_correlate = False
        if fromclauses and fromclauses[0] is None:
            self._correlate_except = ()
        else:
            self._correlate_except = set(self._correlate_except or ()).union(
                    _interpret_as_from(f) for f in fromclauses)

    def append_correlation(self, fromclause):
        """append the given correlation expression to this select()
        construct.

        This is an **in-place** mutation method; the
        :meth:`~.Select.correlate` method is preferred, as it provides standard
        :term:`method chaining`.

        """

        self._auto_correlate = False
        self._correlate = set(self._correlate).union(
                _interpret_as_from(f) for f in fromclause)

    def append_column(self, column):
        """append the given column expression to the columns clause of this
        select() construct.

        This is an **in-place** mutation method; the
        :meth:`~.Select.column` method is preferred, as it provides standard
        :term:`method chaining`.

        """
        self._reset_exported()
        column = _interpret_as_column_or_from(column)

        if isinstance(column, ScalarSelect):
            column = column.self_group(against=operators.comma_op)

        self._raw_columns = self._raw_columns + [column]

    def append_prefix(self, clause):
        """append the given columns clause prefix expression to this select()
        construct.

        This is an **in-place** mutation method; the
        :meth:`~.Select.prefix_with` method is preferred, as it provides standard
        :term:`method chaining`.

        """
        clause = _literal_as_text(clause)
        self._prefixes = self._prefixes + (clause,)

    def append_whereclause(self, whereclause):
        """append the given expression to this select() construct's WHERE
        criterion.

        The expression will be joined to existing WHERE criterion via AND.

        This is an **in-place** mutation method; the
        :meth:`~.Select.where` method is preferred, as it provides standard
        :term:`method chaining`.

        """
        self._reset_exported()
        whereclause = _literal_as_text(whereclause)

        if self._whereclause is not None:
            self._whereclause = and_(self._whereclause, whereclause)
        else:
            self._whereclause = whereclause

    def append_having(self, having):
        """append the given expression to this select() construct's HAVING
        criterion.

        The expression will be joined to existing HAVING criterion via AND.

        This is an **in-place** mutation method; the
        :meth:`~.Select.having` method is preferred, as it provides standard
        :term:`method chaining`.

        """
        if self._having is not None:
            self._having = and_(self._having, _literal_as_text(having))
        else:
            self._having = _literal_as_text(having)

    def append_from(self, fromclause):
        """append the given FromClause expression to this select() construct's
        FROM clause.

        This is an **in-place** mutation method; the
        :meth:`~.Select.select_from` method is preferred, as it provides standard
        :term:`method chaining`.

        """
        self._reset_exported()
        fromclause = _interpret_as_from(fromclause)
        self._from_obj = self._from_obj.union([fromclause])


    @_memoized_property
    def _columns_plus_names(self):
        if self.use_labels:
            names = set()
            def name_for_col(c):
                if c._label is None:
                    return (None, c)
                name = c._label
                if name in names:
                    name = c.anon_label
                else:
                    names.add(name)
                return name, c

            return [
                name_for_col(c)
                for c in util.unique_list(_select_iterables(self._raw_columns))
            ]
        else:
            return [
                (None, c)
                for c in util.unique_list(_select_iterables(self._raw_columns))
            ]

    def _populate_column_collection(self):
        for name, c in self._columns_plus_names:
            if not hasattr(c, '_make_proxy'):
                continue
            if name is None:
                key = None
            elif self.use_labels:
                key = c._key_label
                if key is not None and key in self.c:
                    key = c.anon_label
            else:
                key = None

            c._make_proxy(self, key=key,
                    name=name,
                    name_is_truncatable=True)

    def _refresh_for_new_column(self, column):
        for fromclause in self._froms:
            col = fromclause._refresh_for_new_column(column)
            if col is not None:
                if col in self.inner_columns and self._cols_populated:
                    our_label = col._key_label if self.use_labels else col.key
                    if our_label not in self.c:
                        return col._make_proxy(self,
                            name=col._label if self.use_labels else None,
                            key=col._key_label if self.use_labels else None,
                            name_is_truncatable=True)
                return None
        return None

    def self_group(self, against=None):
        """return a 'grouping' construct as per the ClauseElement
        specification.

        This produces an element that can be embedded in an expression. Note
        that this method is called automatically as needed when constructing
        expressions and should not require explicit use.

        """
        if isinstance(against, CompoundSelect):
            return self
        return FromGrouping(self)

    def union(self, other, **kwargs):
        """return a SQL UNION of this select() construct against the given
        selectable."""

        return union(self, other, **kwargs)

    def union_all(self, other, **kwargs):
        """return a SQL UNION ALL of this select() construct against the given
        selectable.

        """
        return union_all(self, other, **kwargs)

    def except_(self, other, **kwargs):
        """return a SQL EXCEPT of this select() construct against the given
        selectable."""

        return except_(self, other, **kwargs)

    def except_all(self, other, **kwargs):
        """return a SQL EXCEPT ALL of this select() construct against the
        given selectable.

        """
        return except_all(self, other, **kwargs)

    def intersect(self, other, **kwargs):
        """return a SQL INTERSECT of this select() construct against the given
        selectable.

        """
        return intersect(self, other, **kwargs)

    def intersect_all(self, other, **kwargs):
        """return a SQL INTERSECT ALL of this select() construct against the
        given selectable.

        """
        return intersect_all(self, other, **kwargs)

    def bind(self):
        if self._bind:
            return self._bind
        froms = self._froms
        if not froms:
            for c in self._raw_columns:
                e = c.bind
                if e:
                    self._bind = e
                    return e
        else:
            e = list(froms)[0].bind
            if e:
                self._bind = e
                return e

        return None

    def _set_bind(self, bind):
        self._bind = bind
    bind = property(bind, _set_bind)


class UpdateBase(HasPrefixes, Executable, ClauseElement):
    """Form the base for ``INSERT``, ``UPDATE``, and ``DELETE`` statements.

    """

    __visit_name__ = 'update_base'

    _execution_options = \
        Executable._execution_options.union({'autocommit': True})
    kwargs = util.immutabledict()
    _hints = util.immutabledict()
    _prefixes = ()

    def _process_colparams(self, parameters):
        def process_single(p):
            if isinstance(p, (list, tuple)):
                return dict(
                    (c.key, pval)
                    for c, pval in zip(self.table.c, p)
                )
            else:
                return p

        if isinstance(parameters, (list, tuple)) and \
              isinstance(parameters[0], (list, tuple, dict)):

            if not self._supports_multi_parameters:
                raise exc.InvalidRequestError(
                    "This construct does not support "
                    "multiple parameter sets.")

            return [process_single(p) for p in parameters], True
        else:
            return process_single(parameters), False

    def params(self, *arg, **kw):
        """Set the parameters for the statement.

        This method raises ``NotImplementedError`` on the base class,
        and is overridden by :class:`.ValuesBase` to provide the
        SET/VALUES clause of UPDATE and INSERT.

        """
        raise NotImplementedError(
            "params() is not supported for INSERT/UPDATE/DELETE statements."
            " To set the values for an INSERT or UPDATE statement, use"
            " stmt.values(**parameters).")

    def bind(self):
        """Return a 'bind' linked to this :class:`.UpdateBase`
        or a :class:`.Table` associated with it.

        """
        return self._bind or self.table.bind

    def _set_bind(self, bind):
        self._bind = bind
    bind = property(bind, _set_bind)

    @_generative
    def returning(self, *cols):
        """Add a RETURNING or equivalent clause to this statement.

        The given list of columns represent columns within the table that is
        the target of the INSERT, UPDATE, or DELETE. Each element can be any
        column expression. :class:`~sqlalchemy.schema.Table` objects will be
        expanded into their individual columns.

        Upon compilation, a RETURNING clause, or database equivalent,
        will be rendered within the statement.   For INSERT and UPDATE,
        the values are the newly inserted/updated values.  For DELETE,
        the values are those of the rows which were deleted.

        Upon execution, the values of the columns to be returned
        are made available via the result set and can be iterated
        using ``fetchone()`` and similar.   For DBAPIs which do not
        natively support returning values (i.e. cx_oracle),
        SQLAlchemy will approximate this behavior at the result level
        so that a reasonable amount of behavioral neutrality is
        provided.

        Note that not all databases/DBAPIs
        support RETURNING.   For those backends with no support,
        an exception is raised upon compilation and/or execution.
        For those who do support it, the functionality across backends
        varies greatly, including restrictions on executemany()
        and other statements which return multiple rows. Please
        read the documentation notes for the database in use in
        order to determine the availability of RETURNING.

        """
        self._returning = cols

    @_generative
    def with_hint(self, text, selectable=None, dialect_name="*"):
        """Add a table hint for a single table to this
        INSERT/UPDATE/DELETE statement.

        .. note::

         :meth:`.UpdateBase.with_hint` currently applies only to
         Microsoft SQL Server.  For MySQL INSERT/UPDATE/DELETE hints, use
         :meth:`.UpdateBase.prefix_with`.

        The text of the hint is rendered in the appropriate
        location for the database backend in use, relative
        to the :class:`.Table` that is the subject of this
        statement, or optionally to that of the given
        :class:`.Table` passed as the ``selectable`` argument.

        The ``dialect_name`` option will limit the rendering of a particular
        hint to a particular backend. Such as, to add a hint
        that only takes effect for SQL Server::

            mytable.insert().with_hint("WITH (PAGLOCK)", dialect_name="mssql")

        .. versionadded:: 0.7.6

        :param text: Text of the hint.
        :param selectable: optional :class:`.Table` that specifies
         an element of the FROM clause within an UPDATE or DELETE
         to be the subject of the hint - applies only to certain backends.
        :param dialect_name: defaults to ``*``, if specified as the name
         of a particular dialect, will apply these hints only when
         that dialect is in use.
         """
        if selectable is None:
            selectable = self.table

        self._hints = self._hints.union(
                        {(selectable, dialect_name): text})


class ValuesBase(UpdateBase):
    """Supplies support for :meth:`.ValuesBase.values` to
    INSERT and UPDATE constructs."""

    __visit_name__ = 'values_base'

    _supports_multi_parameters = False
    _has_multi_parameters = False
    select = None

    def __init__(self, table, values, prefixes):
        self.table = _interpret_as_from(table)
        self.parameters, self._has_multi_parameters = \
                            self._process_colparams(values)
        if prefixes:
            self._setup_prefixes(prefixes)

    @_generative
    def values(self, *args, **kwargs):
        """specify a fixed VALUES clause for an INSERT statement, or the SET
        clause for an UPDATE.

        Note that the :class:`.Insert` and :class:`.Update` constructs support
        per-execution time formatting of the VALUES and/or SET clauses,
        based on the arguments passed to :meth:`.Connection.execute`.  However,
        the :meth:`.ValuesBase.values` method can be used to "fix" a particular
        set of parameters into the statement.

        Multiple calls to :meth:`.ValuesBase.values` will produce a new
        construct, each one with the parameter list modified to include
        the new parameters sent.  In the typical case of a single
        dictionary of parameters, the newly passed keys will replace
        the same keys in the previous construct.  In the case of a list-based
        "multiple values" construct, each new list of values is extended
        onto the existing list of values.

        :param \**kwargs: key value pairs representing the string key
          of a :class:`.Column` mapped to the value to be rendered into the
          VALUES or SET clause::

                users.insert().values(name="some name")

                users.update().where(users.c.id==5).values(name="some name")

        :param \*args: Alternatively, a dictionary, tuple or list
         of dictionaries or tuples can be passed as a single positional
         argument in order to form the VALUES or
         SET clause of the statement.  The single dictionary form
         works the same as the kwargs form::

            users.insert().values({"name": "some name"})

         If a tuple is passed, the tuple should contain the same number
         of columns as the target :class:`.Table`::

            users.insert().values((5, "some name"))

         The :class:`.Insert` construct also supports multiply-rendered VALUES
         construct, for those backends which support this SQL syntax
         (SQLite, Postgresql, MySQL).  This mode is indicated by passing a list
         of one or more dictionaries/tuples::

            users.insert().values([
                                {"name": "some name"},
                                {"name": "some other name"},
                                {"name": "yet another name"},
                            ])

         In the case of an :class:`.Update`
         construct, only the single dictionary/tuple form is accepted,
         else an exception is raised.  It is also an exception case to
         attempt to mix the single-/multiple- value styles together,
         either through multiple :meth:`.ValuesBase.values` calls
         or by sending a list + kwargs at the same time.

         .. note::

             Passing a multiple values list is *not* the same
             as passing a multiple values list to the :meth:`.Connection.execute`
             method.  Passing a list of parameter sets to :meth:`.ValuesBase.values`
             produces a construct of this form::

                INSERT INTO table (col1, col2, col3) VALUES
                                (col1_0, col2_0, col3_0),
                                (col1_1, col2_1, col3_1),
                                ...

             whereas a multiple list passed to :meth:`.Connection.execute`
             has the effect of using the DBAPI
             `executemany() <http://www.python.org/dev/peps/pep-0249/#id18>`_
             method, which provides a high-performance system of invoking
             a single-row INSERT statement many times against a series
             of parameter sets.   The "executemany" style is supported by
             all database backends, as it does not depend on a special SQL
             syntax.

         .. versionadded:: 0.8
             Support for multiple-VALUES INSERT statements.


        .. seealso::

            :ref:`inserts_and_updates` - SQL Expression
            Language Tutorial

            :func:`~.expression.insert` - produce an ``INSERT`` statement

            :func:`~.expression.update` - produce an ``UPDATE`` statement

        """
        if self.select is not None:
            raise exc.InvalidRequestError(
                        "This construct already inserts from a SELECT")
        if self._has_multi_parameters and kwargs:
            raise exc.InvalidRequestError(
                        "This construct already has multiple parameter sets.")

        if args:
            if len(args) > 1:
                raise exc.ArgumentError(
                            "Only a single dictionary/tuple or list of "
                            "dictionaries/tuples is accepted positionally.")
            v = args[0]
        else:
            v = {}

        if self.parameters is None:
            self.parameters, self._has_multi_parameters = \
                    self._process_colparams(v)
        else:
            if self._has_multi_parameters:
                self.parameters = list(self.parameters)
                p, self._has_multi_parameters = self._process_colparams(v)
                if not self._has_multi_parameters:
                    raise exc.ArgumentError(
                        "Can't mix single-values and multiple values "
                        "formats in one statement")

                self.parameters.extend(p)
            else:
                self.parameters = self.parameters.copy()
                p, self._has_multi_parameters = self._process_colparams(v)
                if self._has_multi_parameters:
                    raise exc.ArgumentError(
                        "Can't mix single-values and multiple values "
                        "formats in one statement")
                self.parameters.update(p)

        if kwargs:
            if self._has_multi_parameters:
                raise exc.ArgumentError(
                            "Can't pass kwargs and multiple parameter sets "
                            "simultaenously")
            else:
                self.parameters.update(kwargs)


class Insert(ValuesBase):
    """Represent an INSERT construct.

    The :class:`.Insert` object is created using the
    :func:`~.expression.insert()` function.

    .. seealso::

        :ref:`coretutorial_insert_expressions`

    """
    __visit_name__ = 'insert'

    _supports_multi_parameters = True

    def __init__(self,
                table,
                values=None,
                inline=False,
                bind=None,
                prefixes=None,
                returning=None,
                **kwargs):
        ValuesBase.__init__(self, table, values, prefixes)
        self._bind = bind
        self.select = None
        self.inline = inline
        self._returning = returning
        self.kwargs = kwargs

    def get_children(self, **kwargs):
        if self.select is not None:
            return self.select,
        else:
            return ()

    @_generative
    def from_select(self, names, select):
        """Return a new :class:`.Insert` construct which represents
        an ``INSERT...FROM SELECT`` statement.

        e.g.::

            sel = select([table1.c.a, table1.c.b]).where(table1.c.c > 5)
            ins = table2.insert().from_select(['a', 'b'], sel)

        :param names: a sequence of string column names or :class:`.Column`
         objects representing the target columns.
        :param select: a :func:`.select` construct, :class:`.FromClause`
         or other construct which resolves into a :class:`.FromClause`,
         such as an ORM :class:`.Query` object, etc.  The order of
         columns returned from this FROM clause should correspond to the
         order of columns sent as the ``names`` parameter;  while this
         is not checked before passing along to the database, the database
         would normally raise an exception if these column lists don't
         correspond.

        .. note::

           Depending on backend, it may be necessary for the :class:`.Insert`
           statement to be constructed using the ``inline=True`` flag; this
           flag will prevent the implicit usage of ``RETURNING`` when the
           ``INSERT`` statement is rendered, which isn't supported on a backend
           such as Oracle in conjunction with an ``INSERT..SELECT`` combination::

             sel = select([table1.c.a, table1.c.b]).where(table1.c.c > 5)
             ins = table2.insert(inline=True).from_select(['a', 'b'], sel)

        .. versionadded:: 0.8.3

        """
        if self.parameters:
            raise exc.InvalidRequestError(
                        "This construct already inserts value expressions")

        self.parameters, self._has_multi_parameters = \
                self._process_colparams(dict((n, null()) for n in names))

        self.select = _interpret_as_select(select)

    def _copy_internals(self, clone=_clone, **kw):
        # TODO: coverage
        self.parameters = self.parameters.copy()
        if self.select is not None:
            self.select = _clone(self.select)


class Update(ValuesBase):
    """Represent an Update construct.

    The :class:`.Update` object is created using the :func:`update()` function.

    """
    __visit_name__ = 'update'

    def __init__(self,
                table,
                whereclause,
                values=None,
                inline=False,
                bind=None,
                prefixes=None,
                returning=None,
                **kwargs):
        ValuesBase.__init__(self, table, values, prefixes)
        self._bind = bind
        self._returning = returning
        if whereclause is not None:
            self._whereclause = _literal_as_text(whereclause)
        else:
            self._whereclause = None
        self.inline = inline
        self.kwargs = kwargs


    def get_children(self, **kwargs):
        if self._whereclause is not None:
            return self._whereclause,
        else:
            return ()

    def _copy_internals(self, clone=_clone, **kw):
        # TODO: coverage
        self._whereclause = clone(self._whereclause, **kw)
        self.parameters = self.parameters.copy()

    @_generative
    def where(self, whereclause):
        """return a new update() construct with the given expression added to
        its WHERE clause, joined to the existing clause via AND, if any.

        """
        if self._whereclause is not None:
            self._whereclause = and_(self._whereclause,
                    _literal_as_text(whereclause))
        else:
            self._whereclause = _literal_as_text(whereclause)

    @property
    def _extra_froms(self):
        # TODO: this could be made memoized
        # if the memoization is reset on each generative call.
        froms = []
        seen = set([self.table])

        if self._whereclause is not None:
            for item in _from_objects(self._whereclause):
                if not seen.intersection(item._cloned_set):
                    froms.append(item)
                seen.update(item._cloned_set)

        return froms


class Delete(UpdateBase):
    """Represent a DELETE construct.

    The :class:`.Delete` object is created using the :func:`delete()` function.

    """

    __visit_name__ = 'delete'

    def __init__(self,
            table,
            whereclause,
            bind=None,
            returning=None,
            prefixes=None,
            **kwargs):
        self._bind = bind
        self.table = _interpret_as_from(table)
        self._returning = returning

        if prefixes:
            self._setup_prefixes(prefixes)

        if whereclause is not None:
            self._whereclause = _literal_as_text(whereclause)
        else:
            self._whereclause = None

        self.kwargs = kwargs

    def get_children(self, **kwargs):
        if self._whereclause is not None:
            return self._whereclause,
        else:
            return ()

    @_generative
    def where(self, whereclause):
        """Add the given WHERE clause to a newly returned delete construct."""

        if self._whereclause is not None:
            self._whereclause = and_(self._whereclause,
                    _literal_as_text(whereclause))
        else:
            self._whereclause = _literal_as_text(whereclause)

    def _copy_internals(self, clone=_clone, **kw):
        # TODO: coverage
        self._whereclause = clone(self._whereclause, **kw)


class _IdentifiedClause(Executable, ClauseElement):

    __visit_name__ = 'identified'
    _execution_options = \
        Executable._execution_options.union({'autocommit': False})
    quote = None

    def __init__(self, ident):
        self.ident = ident


class SavepointClause(_IdentifiedClause):
    __visit_name__ = 'savepoint'


class RollbackToSavepointClause(_IdentifiedClause):
    __visit_name__ = 'rollback_to_savepoint'


class ReleaseSavepointClause(_IdentifiedClause):
    __visit_name__ = 'release_savepoint'

# old names for compatibility
_BindParamClause = BindParameter
_Label = Label
_SelectBase = SelectBase
_BinaryExpression = BinaryExpression
_Cast = Cast
_Null = Null
_False = False_
_True = True_
_TextClause = TextClause
_UnaryExpression = UnaryExpression
_Case = Case
_Tuple = Tuple
_Over = Over
_Generative = Generative
_TypeClause = TypeClause
_Extract = Extract
_Exists = Exists
_Grouping = Grouping
_FromGrouping = FromGrouping
_ScalarSelect = ScalarSelect
