# postgresql/base.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""
.. dialect:: postgresql
    :name: PostgreSQL


Sequences/SERIAL
----------------

PostgreSQL supports sequences, and SQLAlchemy uses these as the default means
of creating new primary key values for integer-based primary key columns. When
creating tables, SQLAlchemy will issue the ``SERIAL`` datatype for
integer-based primary key columns, which generates a sequence and server side
default corresponding to the column.

To specify a specific named sequence to be used for primary key generation,
use the :func:`~sqlalchemy.schema.Sequence` construct::

    Table('sometable', metadata,
            Column('id', Integer, Sequence('some_id_seq'), primary_key=True)
        )

When SQLAlchemy issues a single INSERT statement, to fulfill the contract of
having the "last insert identifier" available, a RETURNING clause is added to
the INSERT statement which specifies the primary key columns should be
returned after the statement completes. The RETURNING functionality only takes
place if Postgresql 8.2 or later is in use. As a fallback approach, the
sequence, whether specified explicitly or implicitly via ``SERIAL``, is
executed independently beforehand, the returned value to be used in the
subsequent insert. Note that when an
:func:`~sqlalchemy.sql.expression.insert()` construct is executed using
"executemany" semantics, the "last inserted identifier" functionality does not
apply; no RETURNING clause is emitted nor is the sequence pre-executed in this
case.

To force the usage of RETURNING by default off, specify the flag
``implicit_returning=False`` to :func:`.create_engine`.

.. _postgresql_isolation_level:

Transaction Isolation Level
---------------------------

All Postgresql dialects support setting of transaction isolation level
both via a dialect-specific parameter ``isolation_level``
accepted by :func:`.create_engine`,
as well as the ``isolation_level`` argument as passed to :meth:`.Connection.execution_options`.
When using a non-psycopg2 dialect, this feature works by issuing the
command ``SET SESSION CHARACTERISTICS AS TRANSACTION ISOLATION LEVEL
<level>`` for each new connection.

To set isolation level using :func:`.create_engine`::

    engine = create_engine(
                    "postgresql+pg8000://scott:tiger@localhost/test",
                    isolation_level="READ UNCOMMITTED"
                )

To set using per-connection execution options::

    connection = engine.connect()
    connection = connection.execution_options(isolation_level="READ COMMITTED")

Valid values for ``isolation_level`` include:

* ``READ COMMITTED``
* ``READ UNCOMMITTED``
* ``REPEATABLE READ``
* ``SERIALIZABLE``

The :mod:`~sqlalchemy.dialects.postgresql.psycopg2` dialect also offers the special level ``AUTOCOMMIT``.  See
:ref:`psycopg2_isolation_level` for details.


Remote / Cross-Schema Table Introspection
-----------------------------------------

Tables can be introspected from any accessible schema, including
inter-schema foreign key relationships.   However, care must be taken
when specifying the "schema" argument for a given :class:`.Table`, when
the given schema is also present in PostgreSQL's ``search_path`` variable
for the current connection.

If a FOREIGN KEY constraint reports that the remote table's schema is within
the current ``search_path``, the "schema" attribute of the resulting
:class:`.Table` will be set to ``None``, unless the actual schema of the
remote table matches that of the referencing table, and the "schema" argument
was explicitly stated on the referencing table.

The best practice here is to not use the ``schema`` argument
on :class:`.Table` for any schemas that are present in ``search_path``.
``search_path`` defaults to "public", but care should be taken
to inspect the actual value using::

    SHOW search_path;

.. versionchanged:: 0.7.3
    Prior to this version, cross-schema foreign keys when the schemas
    were also in the ``search_path`` could make an incorrect assumption
    if the schemas were explicitly stated on each :class:`.Table`.

Background on PG's ``search_path`` is at:
http://www.postgresql.org/docs/9.0/static/ddl-schemas.html#DDL-SCHEMAS-PATH

INSERT/UPDATE...RETURNING
-------------------------

The dialect supports PG 8.2's ``INSERT..RETURNING``, ``UPDATE..RETURNING`` and
``DELETE..RETURNING`` syntaxes.   ``INSERT..RETURNING`` is used by default
for single-row INSERT statements in order to fetch newly generated
primary key identifiers.   To specify an explicit ``RETURNING`` clause,
use the :meth:`._UpdateBase.returning` method on a per-statement basis::

    # INSERT..RETURNING
    result = table.insert().returning(table.c.col1, table.c.col2).\\
        values(name='foo')
    print result.fetchall()

    # UPDATE..RETURNING
    result = table.update().returning(table.c.col1, table.c.col2).\\
        where(table.c.name=='foo').values(name='bar')
    print result.fetchall()

    # DELETE..RETURNING
    result = table.delete().returning(table.c.col1, table.c.col2).\\
        where(table.c.name=='foo')
    print result.fetchall()

FROM ONLY ...
------------------------

The dialect supports PostgreSQL's ONLY keyword for targeting only a particular
table in an inheritance hierarchy. This can be used to produce the
``SELECT ... FROM ONLY``, ``UPDATE ONLY ...``, and ``DELETE FROM ONLY ...``
syntaxes. It uses SQLAlchemy's hints mechanism::

    # SELECT ... FROM ONLY ...
    result = table.select().with_hint(table, 'ONLY', 'postgresql')
    print result.fetchall()

    # UPDATE ONLY ...
    table.update(values=dict(foo='bar')).with_hint('ONLY',
                                                   dialect_name='postgresql')

    # DELETE FROM ONLY ...
    table.delete().with_hint('ONLY', dialect_name='postgresql')

.. _postgresql_indexes:

Postgresql-Specific Index Options
---------------------------------

Several extensions to the :class:`.Index` construct are available, specific
to the PostgreSQL dialect.

Partial Indexes
^^^^^^^^^^^^^^^^

Partial indexes add criterion to the index definition so that the index is
applied to a subset of rows.   These can be specified on :class:`.Index`
using the ``postgresql_where`` keyword argument::

  Index('my_index', my_table.c.id, postgresql_where=tbl.c.value > 10)

Operator Classes
^^^^^^^^^^^^^^^^^

PostgreSQL allows the specification of an *operator class* for each column of
an index (see
http://www.postgresql.org/docs/8.3/interactive/indexes-opclass.html).
The :class:`.Index` construct allows these to be specified via the
``postgresql_ops`` keyword argument::

    Index('my_index', my_table.c.id, my_table.c.data,
                            postgresql_ops={
                                'data': 'text_pattern_ops',
                                'id': 'int4_ops'
                            })

.. versionadded:: 0.7.2
    ``postgresql_ops`` keyword argument to :class:`.Index` construct.

Note that the keys in the ``postgresql_ops`` dictionary are the "key" name of
the :class:`.Column`, i.e. the name used to access it from the ``.c``
collection of :class:`.Table`, which can be configured to be different than
the actual name of the column as expressed in the database.

Index Types
^^^^^^^^^^^^

PostgreSQL provides several index types: B-Tree, Hash, GiST, and GIN, as well
as the ability for users to create their own (see
http://www.postgresql.org/docs/8.3/static/indexes-types.html). These can be
specified on :class:`.Index` using the ``postgresql_using`` keyword argument::

    Index('my_index', my_table.c.data, postgresql_using='gin')

The value passed to the keyword argument will be simply passed through to the
underlying CREATE INDEX command, so it *must* be a valid index type for your
version of PostgreSQL.

"""

from collections import defaultdict
import re

from ... import sql, schema, exc, util
from ...engine import default, reflection
from ...sql import compiler, expression, util as sql_util, operators
from ... import types as sqltypes

try:
    from uuid import UUID as _python_UUID
except ImportError:
    _python_UUID = None

from sqlalchemy.types import INTEGER, BIGINT, SMALLINT, VARCHAR, \
        CHAR, TEXT, FLOAT, NUMERIC, \
        DATE, BOOLEAN, REAL

RESERVED_WORDS = set(
    ["all", "analyse", "analyze", "and", "any", "array", "as", "asc",
    "asymmetric", "both", "case", "cast", "check", "collate", "column",
    "constraint", "create", "current_catalog", "current_date",
    "current_role", "current_time", "current_timestamp", "current_user",
    "default", "deferrable", "desc", "distinct", "do", "else", "end",
    "except", "false", "fetch", "for", "foreign", "from", "grant", "group",
    "having", "in", "initially", "intersect", "into", "leading", "limit",
    "localtime", "localtimestamp", "new", "not", "null", "off", "offset",
    "old", "on", "only", "or", "order", "placing", "primary", "references",
    "returning", "select", "session_user", "some", "symmetric", "table",
    "then", "to", "trailing", "true", "union", "unique", "user", "using",
    "variadic", "when", "where", "window", "with", "authorization",
    "between", "binary", "cross", "current_schema", "freeze", "full",
    "ilike", "inner", "is", "isnull", "join", "left", "like", "natural",
    "notnull", "outer", "over", "overlaps", "right", "similar", "verbose"
    ])

_DECIMAL_TYPES = (1231, 1700)
_FLOAT_TYPES = (700, 701, 1021, 1022)
_INT_TYPES = (20, 21, 23, 26, 1005, 1007, 1016)


class BYTEA(sqltypes.LargeBinary):
    __visit_name__ = 'BYTEA'


class DOUBLE_PRECISION(sqltypes.Float):
    __visit_name__ = 'DOUBLE_PRECISION'


class INET(sqltypes.TypeEngine):
    __visit_name__ = "INET"
PGInet = INET


class CIDR(sqltypes.TypeEngine):
    __visit_name__ = "CIDR"
PGCidr = CIDR


class MACADDR(sqltypes.TypeEngine):
    __visit_name__ = "MACADDR"
PGMacAddr = MACADDR


class TIMESTAMP(sqltypes.TIMESTAMP):
    def __init__(self, timezone=False, precision=None):
        super(TIMESTAMP, self).__init__(timezone=timezone)
        self.precision = precision


class TIME(sqltypes.TIME):
    def __init__(self, timezone=False, precision=None):
        super(TIME, self).__init__(timezone=timezone)
        self.precision = precision


class INTERVAL(sqltypes.TypeEngine):
    """Postgresql INTERVAL type.

    The INTERVAL type may not be supported on all DBAPIs.
    It is known to work on psycopg2 and not pg8000 or zxjdbc.

    """
    __visit_name__ = 'INTERVAL'

    def __init__(self, precision=None):
        self.precision = precision

    @classmethod
    def _adapt_from_generic_interval(cls, interval):
        return INTERVAL(precision=interval.second_precision)

    @property
    def _type_affinity(self):
        return sqltypes.Interval

PGInterval = INTERVAL


class BIT(sqltypes.TypeEngine):
    __visit_name__ = 'BIT'

    def __init__(self, length=None, varying=False):
        if not varying:
            # BIT without VARYING defaults to length 1
            self.length = length or 1
        else:
            # but BIT VARYING can be unlimited-length, so no default
            self.length = length
        self.varying = varying

PGBit = BIT


class UUID(sqltypes.TypeEngine):
    """Postgresql UUID type.

    Represents the UUID column type, interpreting
    data either as natively returned by the DBAPI
    or as Python uuid objects.

    The UUID type may not be supported on all DBAPIs.
    It is known to work on psycopg2 and not pg8000.

    """
    __visit_name__ = 'UUID'

    def __init__(self, as_uuid=False):
        """Construct a UUID type.


        :param as_uuid=False: if True, values will be interpreted
         as Python uuid objects, converting to/from string via the
         DBAPI.

         """
        if as_uuid and _python_UUID is None:
            raise NotImplementedError(
                "This version of Python does not support the native UUID type."
            )
        self.as_uuid = as_uuid

    def bind_processor(self, dialect):
        if self.as_uuid:
            def process(value):
                if value is not None:
                    value = str(value)
                return value
            return process
        else:
            return None

    def result_processor(self, dialect, coltype):
        if self.as_uuid:
            def process(value):
                if value is not None:
                    value = _python_UUID(value)
                return value
            return process
        else:
            return None

PGUuid = UUID


class _Slice(expression.ColumnElement):
    __visit_name__ = 'slice'
    type = sqltypes.NULLTYPE

    def __init__(self, slice_, source_comparator):
        self.start = source_comparator._check_literal(
                            source_comparator.expr,
                            operators.getitem, slice_.start)
        self.stop = source_comparator._check_literal(
                            source_comparator.expr,
                            operators.getitem, slice_.stop)


class Any(expression.ColumnElement):
    """Represent the clause ``left operator ANY (right)``.  ``right`` must be
    an array expression.

    .. seealso::

        :class:`.postgresql.ARRAY`

        :meth:`.postgresql.ARRAY.Comparator.any` - ARRAY-bound method

    """
    __visit_name__ = 'any'

    def __init__(self, left, right, operator=operators.eq):
        self.type = sqltypes.Boolean()
        self.left = expression._literal_as_binds(left)
        self.right = right
        self.operator = operator


class All(expression.ColumnElement):
    """Represent the clause ``left operator ALL (right)``.  ``right`` must be
    an array expression.

    .. seealso::

        :class:`.postgresql.ARRAY`

        :meth:`.postgresql.ARRAY.Comparator.all` - ARRAY-bound method

    """
    __visit_name__ = 'all'

    def __init__(self, left, right, operator=operators.eq):
        self.type = sqltypes.Boolean()
        self.left = expression._literal_as_binds(left)
        self.right = right
        self.operator = operator


class array(expression.Tuple):
    """A Postgresql ARRAY literal.

    This is used to produce ARRAY literals in SQL expressions, e.g.::

        from sqlalchemy.dialects.postgresql import array
        from sqlalchemy.dialects import postgresql
        from sqlalchemy import select, func

        stmt = select([
                        array([1,2]) + array([3,4,5])
                    ])

        print stmt.compile(dialect=postgresql.dialect())

    Produces the SQL::

        SELECT ARRAY[%(param_1)s, %(param_2)s] ||
            ARRAY[%(param_3)s, %(param_4)s, %(param_5)s]) AS anon_1

    An instance of :class:`.array` will always have the datatype
    :class:`.ARRAY`.  The "inner" type of the array is inferred from
    the values present, unless the ``type_`` keyword argument is passed::

        array(['foo', 'bar'], type_=CHAR)

    .. versionadded:: 0.8 Added the :class:`~.postgresql.array` literal type.

    See also:

    :class:`.postgresql.ARRAY`

    """
    __visit_name__ = 'array'

    def __init__(self, clauses, **kw):
        super(array, self).__init__(*clauses, **kw)
        self.type = ARRAY(self.type)

    def _bind_param(self, operator, obj):
        return array(*[
            expression.BindParameter(None, o, _compared_to_operator=operator,
                             _compared_to_type=self.type, unique=True)
            for o in obj
        ])

    def self_group(self, against=None):
        return self


class ARRAY(sqltypes.Concatenable, sqltypes.TypeEngine):
    """Postgresql ARRAY type.

    Represents values as Python lists.

    An :class:`.ARRAY` type is constructed given the "type"
    of element::

        mytable = Table("mytable", metadata,
                Column("data", ARRAY(Integer))
            )

    The above type represents an N-dimensional array,
    meaning Postgresql will interpret values with any number
    of dimensions automatically.   To produce an INSERT
    construct that passes in a 1-dimensional array of integers::

        connection.execute(
                mytable.insert(),
                data=[1,2,3]
        )

    The :class:`.ARRAY` type can be constructed given a fixed number
    of dimensions::

        mytable = Table("mytable", metadata,
                Column("data", ARRAY(Integer, dimensions=2))
            )

    This has the effect of the :class:`.ARRAY` type
    specifying that number of bracketed blocks when a :class:`.Table`
    is used in a CREATE TABLE statement, or when the type is used
    within a :func:`.expression.cast` construct; it also causes
    the bind parameter and result set processing of the type
    to optimize itself to expect exactly that number of dimensions.
    Note that Postgresql itself still allows N dimensions with such a type.

    SQL expressions of type :class:`.ARRAY` have support for "index" and
    "slice" behavior.  The Python ``[]`` operator works normally here, given
    integer indexes or slices.  Note that Postgresql arrays default
    to 1-based indexing.  The operator produces binary expression
    constructs which will produce the appropriate SQL, both for
    SELECT statements::

        select([mytable.c.data[5], mytable.c.data[2:7]])

    as well as UPDATE statements when the :meth:`.Update.values` method
    is used::

        mytable.update().values({
            mytable.c.data[5]: 7,
            mytable.c.data[2:7]: [1, 2, 3]
        })

    :class:`.ARRAY` provides special methods for containment operations,
    e.g.::

        mytable.c.data.contains([1, 2])

    For a full list of special methods see :class:`.ARRAY.Comparator`.

    .. versionadded:: 0.8 Added support for index and slice operations
       to the :class:`.ARRAY` type, including support for UPDATE
       statements, and special array containment operations.

    The :class:`.ARRAY` type may not be supported on all DBAPIs.
    It is known to work on psycopg2 and not pg8000.

    See also:

    :class:`.postgresql.array` - produce a literal array value.

    """
    __visit_name__ = 'ARRAY'

    class Comparator(sqltypes.Concatenable.Comparator):
        """Define comparison operations for :class:`.ARRAY`."""

        def __getitem__(self, index):
            if isinstance(index, slice):
                index = _Slice(index, self)
                return_type = self.type
            else:
                return_type = self.type.item_type
            return self._binary_operate(self.expr, operators.getitem, index,
                            result_type=return_type)

        def any(self, other, operator=operators.eq):
            """Return ``other operator ANY (array)`` clause.

            Argument places are switched, because ANY requires array
            expression to be on the right hand-side.

            E.g.::

                from sqlalchemy.sql import operators

                conn.execute(
                    select([table.c.data]).where(
                            table.c.data.any(7, operator=operators.lt)
                        )
                )

            :param other: expression to be compared
            :param operator: an operator object from the
             :mod:`sqlalchemy.sql.operators`
             package, defaults to :func:`.operators.eq`.

            .. seealso::

                :class:`.postgresql.Any`

                :meth:`.postgresql.ARRAY.Comparator.all`

            """
            return Any(other, self.expr, operator=operator)

        def all(self, other, operator=operators.eq):
            """Return ``other operator ALL (array)`` clause.

            Argument places are switched, because ALL requires array
            expression to be on the right hand-side.

            E.g.::

                from sqlalchemy.sql import operators

                conn.execute(
                    select([table.c.data]).where(
                            table.c.data.all(7, operator=operators.lt)
                        )
                )

            :param other: expression to be compared
            :param operator: an operator object from the
             :mod:`sqlalchemy.sql.operators`
             package, defaults to :func:`.operators.eq`.

            .. seealso::

                :class:`.postgresql.All`

                :meth:`.postgresql.ARRAY.Comparator.any`

            """
            return All(other, self.expr, operator=operator)

        def contains(self, other, **kwargs):
            """Boolean expression.  Test if elements are a superset of the
            elements of the argument array expression.
            """
            return self.expr.op('@>')(other)

        def contained_by(self, other):
            """Boolean expression.  Test if elements are a proper subset of the
            elements of the argument array expression.
            """
            return self.expr.op('<@')(other)

        def overlap(self, other):
            """Boolean expression.  Test if array has elements in common with
            an argument array expression.
            """
            return self.expr.op('&&')(other)

        def _adapt_expression(self, op, other_comparator):
            if isinstance(op, operators.custom_op):
                if op.opstring in ['@>', '<@', '&&']:
                    return op, sqltypes.Boolean
            return sqltypes.Concatenable.Comparator.\
                _adapt_expression(self, op, other_comparator)

    comparator_factory = Comparator

    def __init__(self, item_type, as_tuple=False, dimensions=None):
        """Construct an ARRAY.

        E.g.::

          Column('myarray', ARRAY(Integer))

        Arguments are:

        :param item_type: The data type of items of this array. Note that
          dimensionality is irrelevant here, so multi-dimensional arrays like
          ``INTEGER[][]``, are constructed as ``ARRAY(Integer)``, not as
          ``ARRAY(ARRAY(Integer))`` or such.

        :param as_tuple=False: Specify whether return results
          should be converted to tuples from lists. DBAPIs such
          as psycopg2 return lists by default. When tuples are
          returned, the results are hashable.

        :param dimensions: if non-None, the ARRAY will assume a fixed
         number of dimensions.  This will cause the DDL emitted for this
         ARRAY to include the exact number of bracket clauses ``[]``,
         and will also optimize the performance of the type overall.
         Note that PG arrays are always implicitly "non-dimensioned",
         meaning they can store any number of dimensions no matter how
         they were declared.

        """
        if isinstance(item_type, ARRAY):
            raise ValueError("Do not nest ARRAY types; ARRAY(basetype) "
                            "handles multi-dimensional arrays of basetype")
        if isinstance(item_type, type):
            item_type = item_type()
        self.item_type = item_type
        self.as_tuple = as_tuple
        self.dimensions = dimensions

    def compare_values(self, x, y):
        return x == y

    def _proc_array(self, arr, itemproc, dim, collection):
        if dim is None:
            arr = list(arr)
        if dim == 1 or dim is None and (
                        # this has to be (list, tuple), or at least
                        # not hasattr('__iter__'), since Py3K strings
                        # etc. have __iter__
                        not arr or not isinstance(arr[0], (list, tuple))):
            if itemproc:
                return collection(itemproc(x) for x in arr)
            else:
                return collection(arr)
        else:
            return collection(
                    self._proc_array(
                            x, itemproc,
                            dim - 1 if dim is not None else None,
                            collection)
                    for x in arr
                )

    def bind_processor(self, dialect):
        item_proc = self.item_type.\
                        dialect_impl(dialect).\
                        bind_processor(dialect)

        def process(value):
            if value is None:
                return value
            else:
                return self._proc_array(
                            value,
                            item_proc,
                            self.dimensions,
                            list)
        return process

    def result_processor(self, dialect, coltype):
        item_proc = self.item_type.\
                        dialect_impl(dialect).\
                        result_processor(dialect, coltype)

        def process(value):
            if value is None:
                return value
            else:
                return self._proc_array(
                            value,
                            item_proc,
                            self.dimensions,
                            tuple if self.as_tuple else list)
        return process

PGArray = ARRAY


class ENUM(sqltypes.Enum):
    """Postgresql ENUM type.

    This is a subclass of :class:`.types.Enum` which includes
    support for PG's ``CREATE TYPE``.

    :class:`~.postgresql.ENUM` is used automatically when
    using the :class:`.types.Enum` type on PG assuming
    the ``native_enum`` is left as ``True``.   However, the
    :class:`~.postgresql.ENUM` class can also be instantiated
    directly in order to access some additional Postgresql-specific
    options, namely finer control over whether or not
    ``CREATE TYPE`` should be emitted.

    Note that both :class:`.types.Enum` as well as
    :class:`~.postgresql.ENUM` feature create/drop
    methods; the base :class:`.types.Enum` type ultimately
    delegates to the :meth:`~.postgresql.ENUM.create` and
    :meth:`~.postgresql.ENUM.drop` methods present here.

    """

    def __init__(self, *enums, **kw):
        """Construct an :class:`~.postgresql.ENUM`.

        Arguments are the same as that of
        :class:`.types.Enum`, but also including
        the following parameters.

        :param create_type: Defaults to True.
         Indicates that ``CREATE TYPE`` should be
         emitted, after optionally checking for the
         presence of the type, when the parent
         table is being created; and additionally
         that ``DROP TYPE`` is called when the table
         is dropped.    When ``False``, no check
         will be performed and no ``CREATE TYPE``
         or ``DROP TYPE`` is emitted, unless
         :meth:`~.postgresql.ENUM.create`
         or :meth:`~.postgresql.ENUM.drop`
         are called directly.
         Setting to ``False`` is helpful
         when invoking a creation scheme to a SQL file
         without access to the actual database -
         the :meth:`~.postgresql.ENUM.create` and
         :meth:`~.postgresql.ENUM.drop` methods can
         be used to emit SQL to a target bind.

         .. versionadded:: 0.7.4

        """
        self.create_type = kw.pop("create_type", True)
        super(ENUM, self).__init__(*enums, **kw)

    def create(self, bind=None, checkfirst=True):
        """Emit ``CREATE TYPE`` for this
        :class:`~.postgresql.ENUM`.

        If the underlying dialect does not support
        Postgresql CREATE TYPE, no action is taken.

        :param bind: a connectable :class:`.Engine`,
         :class:`.Connection`, or similar object to emit
         SQL.
        :param checkfirst: if ``True``, a query against
         the PG catalog will be first performed to see
         if the type does not exist already before
         creating.

        """
        if not bind.dialect.supports_native_enum:
            return

        if not checkfirst or \
            not bind.dialect.has_type(bind, self.name, schema=self.schema):
            bind.execute(CreateEnumType(self))

    def drop(self, bind=None, checkfirst=True):
        """Emit ``DROP TYPE`` for this
        :class:`~.postgresql.ENUM`.

        If the underlying dialect does not support
        Postgresql DROP TYPE, no action is taken.

        :param bind: a connectable :class:`.Engine`,
         :class:`.Connection`, or similar object to emit
         SQL.
        :param checkfirst: if ``True``, a query against
         the PG catalog will be first performed to see
         if the type actually exists before dropping.

        """
        if not bind.dialect.supports_native_enum:
            return

        if not checkfirst or \
            bind.dialect.has_type(bind, self.name, schema=self.schema):
            bind.execute(DropEnumType(self))

    def _check_for_name_in_memos(self, checkfirst, kw):
        """Look in the 'ddl runner' for 'memos', then
        note our name in that collection.

        This to ensure a particular named enum is operated
        upon only once within any kind of create/drop
        sequence without relying upon "checkfirst".

        """
        if not self.create_type:
            return True
        if '_ddl_runner' in kw:
            ddl_runner = kw['_ddl_runner']
            if '_pg_enums' in ddl_runner.memo:
                pg_enums = ddl_runner.memo['_pg_enums']
            else:
                pg_enums = ddl_runner.memo['_pg_enums'] = set()
            present = self.name in pg_enums
            pg_enums.add(self.name)
            return present
        else:
            return False

    def _on_table_create(self, target, bind, checkfirst, **kw):
        if not self._check_for_name_in_memos(checkfirst, kw):
            self.create(bind=bind, checkfirst=checkfirst)

    def _on_metadata_create(self, target, bind, checkfirst, **kw):
        if self.metadata is not None and \
            not self._check_for_name_in_memos(checkfirst, kw):
            self.create(bind=bind, checkfirst=checkfirst)

    def _on_metadata_drop(self, target, bind, checkfirst, **kw):
        if not self._check_for_name_in_memos(checkfirst, kw):
            self.drop(bind=bind, checkfirst=checkfirst)

colspecs = {
    sqltypes.Interval: INTERVAL,
    sqltypes.Enum: ENUM,
}

ischema_names = {
    'integer': INTEGER,
    'bigint': BIGINT,
    'smallint': SMALLINT,
    'character varying': VARCHAR,
    'character': CHAR,
    '"char"': sqltypes.String,
    'name': sqltypes.String,
    'text': TEXT,
    'numeric': NUMERIC,
    'float': FLOAT,
    'real': REAL,
    'inet': INET,
    'cidr': CIDR,
    'uuid': UUID,
    'bit': BIT,
    'bit varying': BIT,
    'macaddr': MACADDR,
    'double precision': DOUBLE_PRECISION,
    'timestamp': TIMESTAMP,
    'timestamp with time zone': TIMESTAMP,
    'timestamp without time zone': TIMESTAMP,
    'time with time zone': TIME,
    'time without time zone': TIME,
    'date': DATE,
    'time': TIME,
    'bytea': BYTEA,
    'boolean': BOOLEAN,
    'interval': INTERVAL,
    'interval year to month': INTERVAL,
    'interval day to second': INTERVAL,
}


class PGCompiler(compiler.SQLCompiler):

    def visit_array(self, element, **kw):
        return "ARRAY[%s]" % self.visit_clauselist(element, **kw)

    def visit_slice(self, element, **kw):
        return "%s:%s" % (
                    self.process(element.start, **kw),
                    self.process(element.stop, **kw),
                )

    def visit_any(self, element, **kw):
        return "%s%sANY (%s)" % (
            self.process(element.left, **kw),
            compiler.OPERATORS[element.operator],
            self.process(element.right, **kw)
        )

    def visit_all(self, element, **kw):
        return "%s%sALL (%s)" % (
            self.process(element.left, **kw),
            compiler.OPERATORS[element.operator],
            self.process(element.right, **kw)
        )

    def visit_getitem_binary(self, binary, operator, **kw):
        return "%s[%s]" % (
                self.process(binary.left, **kw),
                self.process(binary.right, **kw)
            )

    def visit_match_op_binary(self, binary, operator, **kw):
        return "%s @@ to_tsquery(%s)" % (
                        self.process(binary.left, **kw),
                        self.process(binary.right, **kw))

    def visit_ilike_op_binary(self, binary, operator, **kw):
        escape = binary.modifiers.get("escape", None)
        return '%s ILIKE %s' % \
                (self.process(binary.left, **kw),
                    self.process(binary.right, **kw)) \
                + (escape and
                        (' ESCAPE ' + self.render_literal_value(escape, None))
                        or '')

    def visit_notilike_op_binary(self, binary, operator, **kw):
        escape = binary.modifiers.get("escape", None)
        return '%s NOT ILIKE %s' % \
                (self.process(binary.left, **kw),
                    self.process(binary.right, **kw)) \
                + (escape and
                        (' ESCAPE ' + self.render_literal_value(escape, None))
                        or '')

    def render_literal_value(self, value, type_):
        value = super(PGCompiler, self).render_literal_value(value, type_)
        # TODO: need to inspect "standard_conforming_strings"
        if self.dialect._backslash_escapes:
            value = value.replace('\\', '\\\\')
        return value

    def visit_sequence(self, seq):
        return "nextval('%s')" % self.preparer.format_sequence(seq)

    def limit_clause(self, select):
        text = ""
        if select._limit is not None:
            text += " \n LIMIT " + self.process(sql.literal(select._limit))
        if select._offset is not None:
            if select._limit is None:
                text += " \n LIMIT ALL"
            text += " OFFSET " + self.process(sql.literal(select._offset))
        return text

    def format_from_hint_text(self, sqltext, table, hint, iscrud):
        if hint.upper() != 'ONLY':
            raise exc.CompileError("Unrecognized hint: %r" % hint)
        return "ONLY " + sqltext

    def get_select_precolumns(self, select):
        if select._distinct is not False:
            if select._distinct is True:
                return "DISTINCT "
            elif isinstance(select._distinct, (list, tuple)):
                return "DISTINCT ON (" + ', '.join(
                    [self.process(col) for col in select._distinct]
                ) + ") "
            else:
                return "DISTINCT ON (" + self.process(select._distinct) + ") "
        else:
            return ""

    def for_update_clause(self, select):
        if select.for_update == 'nowait':
            return " FOR UPDATE NOWAIT"
        elif select.for_update == 'read':
            return " FOR SHARE"
        elif select.for_update == 'read_nowait':
            return " FOR SHARE NOWAIT"
        else:
            return super(PGCompiler, self).for_update_clause(select)

    def returning_clause(self, stmt, returning_cols):

        columns = [
                self._label_select_column(None, c, True, False, {})
                for c in expression._select_iterables(returning_cols)
            ]

        return 'RETURNING ' + ', '.join(columns)


    def visit_substring_func(self, func, **kw):
        s = self.process(func.clauses.clauses[0], **kw)
        start = self.process(func.clauses.clauses[1], **kw)
        if len(func.clauses.clauses) > 2:
            length = self.process(func.clauses.clauses[2], **kw)
            return "SUBSTRING(%s FROM %s FOR %s)" % (s, start, length)
        else:
            return "SUBSTRING(%s FROM %s)" % (s, start)

class PGDDLCompiler(compiler.DDLCompiler):
    def get_column_specification(self, column, **kwargs):
        colspec = self.preparer.format_column(column)
        impl_type = column.type.dialect_impl(self.dialect)
        if column.primary_key and \
            column is column.table._autoincrement_column and \
            not isinstance(impl_type, sqltypes.SmallInteger) and \
            (
                column.default is None or
                (
                    isinstance(column.default, schema.Sequence) and
                    column.default.optional
                )):
            if isinstance(impl_type, sqltypes.BigInteger):
                colspec += " BIGSERIAL"
            else:
                colspec += " SERIAL"
        else:
            colspec += " " + self.dialect.type_compiler.process(column.type)
            default = self.get_column_default_string(column)
            if default is not None:
                colspec += " DEFAULT " + default

        if not column.nullable:
            colspec += " NOT NULL"
        return colspec

    def visit_create_enum_type(self, create):
        type_ = create.element

        return "CREATE TYPE %s AS ENUM (%s)" % (
            self.preparer.format_type(type_),
            ",".join("'%s'" % e for e in type_.enums)
        )

    def visit_drop_enum_type(self, drop):
        type_ = drop.element

        return "DROP TYPE %s" % (
            self.preparer.format_type(type_)
        )

    def visit_create_index(self, create):
        preparer = self.preparer
        index = create.element
        self._verify_index_table(index)
        text = "CREATE "
        if index.unique:
            text += "UNIQUE "
        text += "INDEX %s ON %s " % (
                        self._prepared_index_name(index,
                                include_schema=False),
                    preparer.format_table(index.table)
                )

        if 'postgresql_using' in index.kwargs:
            using = index.kwargs['postgresql_using']
            text += "USING %s " % preparer.quote(using, index.quote)

        ops = index.kwargs.get('postgresql_ops', {})
        text += "(%s)" \
                % (
                    ', '.join([
                        self.sql_compiler.process(
                                expr.self_group()
                                if not isinstance(expr, expression.ColumnClause)
                                    else expr,
                                include_table=False, literal_binds=True) +
                        (c.key in ops and (' ' + ops[c.key]) or '')
                        for expr, c in zip(index.expressions, index.columns)])
                    )

        if 'postgresql_where' in index.kwargs:
            whereclause = index.kwargs['postgresql_where']
        else:
            whereclause = None

        if whereclause is not None:
            where_compiled = self.sql_compiler.process(
                                    whereclause, include_table=False,
                                    literal_binds=True)
            text += " WHERE " + where_compiled
        return text

    def visit_exclude_constraint(self, constraint):
        text = ""
        if constraint.name is not None:
            text += "CONSTRAINT %s " % \
                    self.preparer.format_constraint(constraint)
        elements = []
        for c in constraint.columns:
            op = constraint.operators[c.name]
            elements.append(self.preparer.quote(c.name, c.quote)+' WITH '+op)
        text += "EXCLUDE USING %s (%s)" % (constraint.using, ', '.join(elements))
        if constraint.where is not None:
            text += ' WHERE (%s)' % self.sql_compiler.process(
                                            constraint.where,
                                            literal_binds=True)
        text += self.define_constraint_deferrability(constraint)
        return text


class PGTypeCompiler(compiler.GenericTypeCompiler):
    def visit_INET(self, type_):
        return "INET"

    def visit_CIDR(self, type_):
        return "CIDR"

    def visit_MACADDR(self, type_):
        return "MACADDR"

    def visit_FLOAT(self, type_):
        if not type_.precision:
            return "FLOAT"
        else:
            return "FLOAT(%(precision)s)" % {'precision': type_.precision}

    def visit_DOUBLE_PRECISION(self, type_):
        return "DOUBLE PRECISION"

    def visit_BIGINT(self, type_):
        return "BIGINT"

    def visit_HSTORE(self, type_):
        return "HSTORE"

    def visit_INT4RANGE(self, type_):
        return "INT4RANGE"

    def visit_INT8RANGE(self, type_):
        return "INT8RANGE"

    def visit_NUMRANGE(self, type_):
        return "NUMRANGE"

    def visit_DATERANGE(self, type_):
        return "DATERANGE"

    def visit_TSRANGE(self, type_):
        return "TSRANGE"

    def visit_TSTZRANGE(self, type_):
        return "TSTZRANGE"

    def visit_datetime(self, type_):
        return self.visit_TIMESTAMP(type_)

    def visit_enum(self, type_):
        if not type_.native_enum or not self.dialect.supports_native_enum:
            return super(PGTypeCompiler, self).visit_enum(type_)
        else:
            return self.visit_ENUM(type_)

    def visit_ENUM(self, type_):
        return self.dialect.identifier_preparer.format_type(type_)

    def visit_TIMESTAMP(self, type_):
        return "TIMESTAMP%s %s" % (
            getattr(type_, 'precision', None) and "(%d)" %
            type_.precision or "",
            (type_.timezone and "WITH" or "WITHOUT") + " TIME ZONE"
        )

    def visit_TIME(self, type_):
        return "TIME%s %s" % (
            getattr(type_, 'precision', None) and "(%d)" %
            type_.precision or "",
            (type_.timezone and "WITH" or "WITHOUT") + " TIME ZONE"
        )

    def visit_INTERVAL(self, type_):
        if type_.precision is not None:
            return "INTERVAL(%d)" % type_.precision
        else:
            return "INTERVAL"

    def visit_BIT(self, type_):
        if type_.varying:
            compiled = "BIT VARYING"
            if type_.length is not None:
                compiled += "(%d)" % type_.length
        else:
            compiled = "BIT(%d)" % type_.length
        return compiled

    def visit_UUID(self, type_):
        return "UUID"

    def visit_large_binary(self, type_):
        return self.visit_BYTEA(type_)

    def visit_BYTEA(self, type_):
        return "BYTEA"

    def visit_ARRAY(self, type_):
        return self.process(type_.item_type) + ('[]' * (type_.dimensions
                                                if type_.dimensions
                                                is not None else 1))


class PGIdentifierPreparer(compiler.IdentifierPreparer):

    reserved_words = RESERVED_WORDS

    def _unquote_identifier(self, value):
        if value[0] == self.initial_quote:
            value = value[1:-1].\
                        replace(self.escape_to_quote, self.escape_quote)
        return value

    def format_type(self, type_, use_schema=True):
        if not type_.name:
            raise exc.CompileError("Postgresql ENUM type requires a name.")

        name = self.quote(type_.name, type_.quote)
        if not self.omit_schema and use_schema and type_.schema is not None:
            name = self.quote_schema(type_.schema, type_.quote) + "." + name
        return name


class PGInspector(reflection.Inspector):

    def __init__(self, conn):
        reflection.Inspector.__init__(self, conn)

    def get_table_oid(self, table_name, schema=None):
        """Return the oid from `table_name` and `schema`."""

        return self.dialect.get_table_oid(self.bind, table_name, schema,
                                          info_cache=self.info_cache)


class CreateEnumType(schema._CreateDropBase):
    __visit_name__ = "create_enum_type"


class DropEnumType(schema._CreateDropBase):
    __visit_name__ = "drop_enum_type"


class PGExecutionContext(default.DefaultExecutionContext):
    def fire_sequence(self, seq, type_):
        return self._execute_scalar(("select nextval('%s')" % \
                self.dialect.identifier_preparer.format_sequence(seq)), type_)

    def get_insert_default(self, column):
        if column.primary_key and column is column.table._autoincrement_column:
            if column.server_default and column.server_default.has_argument:

                # pre-execute passive defaults on primary key columns
                return self._execute_scalar("select %s" %
                                    column.server_default.arg, column.type)

            elif (column.default is None or
                        (column.default.is_sequence and
                        column.default.optional)):

                # execute the sequence associated with a SERIAL primary
                # key column. for non-primary-key SERIAL, the ID just
                # generates server side.

                try:
                    seq_name = column._postgresql_seq_name
                except AttributeError:
                    tab = column.table.name
                    col = column.name
                    tab = tab[0:29 + max(0, (29 - len(col)))]
                    col = col[0:29 + max(0, (29 - len(tab)))]
                    name = "%s_%s_seq" % (tab, col)
                    column._postgresql_seq_name = seq_name = name

                sch = column.table.schema
                if sch is not None:
                    exc = "select nextval('\"%s\".\"%s\"')" % \
                            (sch, seq_name)
                else:
                    exc = "select nextval('\"%s\"')" % \
                            (seq_name, )

                return self._execute_scalar(exc, column.type)

        return super(PGExecutionContext, self).get_insert_default(column)


class PGDialect(default.DefaultDialect):
    name = 'postgresql'
    supports_alter = True
    max_identifier_length = 63
    supports_sane_rowcount = True

    supports_native_enum = True
    supports_native_boolean = True

    supports_sequences = True
    sequences_optional = True
    preexecute_autoincrement_sequences = True
    postfetch_lastrowid = False

    supports_default_values = True
    supports_empty_insert = False
    supports_multivalues_insert = True
    default_paramstyle = 'pyformat'
    ischema_names = ischema_names
    colspecs = colspecs

    statement_compiler = PGCompiler
    ddl_compiler = PGDDLCompiler
    type_compiler = PGTypeCompiler
    preparer = PGIdentifierPreparer
    execution_ctx_cls = PGExecutionContext
    inspector = PGInspector
    isolation_level = None

    # TODO: need to inspect "standard_conforming_strings"
    _backslash_escapes = True

    def __init__(self, isolation_level=None, **kwargs):
        default.DefaultDialect.__init__(self, **kwargs)
        self.isolation_level = isolation_level

    def initialize(self, connection):
        super(PGDialect, self).initialize(connection)
        self.implicit_returning = self.server_version_info > (8, 2) and \
                            self.__dict__.get('implicit_returning', True)
        self.supports_native_enum = self.server_version_info >= (8, 3)
        if not self.supports_native_enum:
            self.colspecs = self.colspecs.copy()
            # pop base Enum type
            self.colspecs.pop(sqltypes.Enum, None)
            # psycopg2, others may have placed ENUM here as well
            self.colspecs.pop(ENUM, None)

    def on_connect(self):
        if self.isolation_level is not None:
            def connect(conn):
                self.set_isolation_level(conn, self.isolation_level)
            return connect
        else:
            return None

    _isolation_lookup = set(['SERIALIZABLE',
                'READ UNCOMMITTED', 'READ COMMITTED', 'REPEATABLE READ'])

    def set_isolation_level(self, connection, level):
        level = level.replace('_', ' ')
        if level not in self._isolation_lookup:
            raise exc.ArgumentError(
                "Invalid value '%s' for isolation_level. "
                "Valid isolation levels for %s are %s" %
                (level, self.name, ", ".join(self._isolation_lookup))
                )
        cursor = connection.cursor()
        cursor.execute(
            "SET SESSION CHARACTERISTICS AS TRANSACTION "
            "ISOLATION LEVEL %s" % level)
        cursor.execute("COMMIT")
        cursor.close()

    def get_isolation_level(self, connection):
        cursor = connection.cursor()
        cursor.execute('show transaction isolation level')
        val = cursor.fetchone()[0]
        cursor.close()
        return val.upper()

    def do_begin_twophase(self, connection, xid):
        self.do_begin(connection.connection)

    def do_prepare_twophase(self, connection, xid):
        connection.execute("PREPARE TRANSACTION '%s'" % xid)

    def do_rollback_twophase(self, connection, xid,
                                is_prepared=True, recover=False):
        if is_prepared:
            if recover:
                #FIXME: ugly hack to get out of transaction
                # context when committing recoverable transactions
                # Must find out a way how to make the dbapi not
                # open a transaction.
                connection.execute("ROLLBACK")
            connection.execute("ROLLBACK PREPARED '%s'" % xid)
            connection.execute("BEGIN")
            self.do_rollback(connection.connection)
        else:
            self.do_rollback(connection.connection)

    def do_commit_twophase(self, connection, xid,
                                is_prepared=True, recover=False):
        if is_prepared:
            if recover:
                connection.execute("ROLLBACK")
            connection.execute("COMMIT PREPARED '%s'" % xid)
            connection.execute("BEGIN")
            self.do_rollback(connection.connection)
        else:
            self.do_commit(connection.connection)

    def do_recover_twophase(self, connection):
        resultset = connection.execute(
                    sql.text("SELECT gid FROM pg_prepared_xacts"))
        return [row[0] for row in resultset]

    def _get_default_schema_name(self, connection):
        return connection.scalar("select current_schema()")

    def has_schema(self, connection, schema):
        query = "select nspname from pg_namespace where lower(nspname)=:schema"
        cursor = connection.execute(
            sql.text(
                query,
                bindparams=[
                    sql.bindparam(
                        'schema', unicode(schema.lower()),
                        type_=sqltypes.Unicode)]
            )
        )

        return bool(cursor.first())

    def has_table(self, connection, table_name, schema=None):
        # seems like case gets folded in pg_class...
        if schema is None:
            cursor = connection.execute(
                sql.text(
                "select relname from pg_class c join pg_namespace n on "
                "n.oid=c.relnamespace where n.nspname=current_schema() and "
                "relname=:name",
                bindparams=[
                        sql.bindparam('name', unicode(table_name),
                        type_=sqltypes.Unicode)]
                )
            )
        else:
            cursor = connection.execute(
                sql.text(
                "select relname from pg_class c join pg_namespace n on "
                "n.oid=c.relnamespace where n.nspname=:schema and "
                "relname=:name",
                    bindparams=[
                        sql.bindparam('name',
                        unicode(table_name), type_=sqltypes.Unicode),
                        sql.bindparam('schema',
                        unicode(schema), type_=sqltypes.Unicode)]
                )
            )
        return bool(cursor.first())

    def has_sequence(self, connection, sequence_name, schema=None):
        if schema is None:
            cursor = connection.execute(
                sql.text(
                    "SELECT relname FROM pg_class c join pg_namespace n on "
                    "n.oid=c.relnamespace where relkind='S' and "
                    "n.nspname=current_schema() "
                    "and relname=:name",
                    bindparams=[
                        sql.bindparam('name', unicode(sequence_name),
                        type_=sqltypes.Unicode)
                    ]
                )
            )
        else:
            cursor = connection.execute(
                sql.text(
                "SELECT relname FROM pg_class c join pg_namespace n on "
                "n.oid=c.relnamespace where relkind='S' and "
                "n.nspname=:schema and relname=:name",
                bindparams=[
                    sql.bindparam('name', unicode(sequence_name),
                     type_=sqltypes.Unicode),
                    sql.bindparam('schema',
                                unicode(schema), type_=sqltypes.Unicode)
                ]
            )
            )

        return bool(cursor.first())

    def has_type(self, connection, type_name, schema=None):
        bindparams = [
            sql.bindparam('typname',
                unicode(type_name), type_=sqltypes.Unicode),
            sql.bindparam('nspname',
                unicode(schema), type_=sqltypes.Unicode),
            ]
        if schema is not None:
            query = """
            SELECT EXISTS (
                SELECT * FROM pg_catalog.pg_type t, pg_catalog.pg_namespace n
                WHERE t.typnamespace = n.oid
                AND t.typname = :typname
                AND n.nspname = :nspname
                )
                """
        else:
            query = """
            SELECT EXISTS (
                SELECT * FROM pg_catalog.pg_type t
                WHERE t.typname = :typname
                AND pg_type_is_visible(t.oid)
                )
                """
        cursor = connection.execute(sql.text(query, bindparams=bindparams))
        return bool(cursor.scalar())

    def _get_server_version_info(self, connection):
        v = connection.execute("select version()").scalar()
        m = re.match(
            '.*(?:PostgreSQL|EnterpriseDB) '
            '(\d+)\.(\d+)(?:\.(\d+))?(?:\.\d+)?(?:devel)?',
            v)
        if not m:
            raise AssertionError(
                    "Could not determine version from string '%s'" % v)
        return tuple([int(x) for x in m.group(1, 2, 3) if x is not None])

    @reflection.cache
    def get_table_oid(self, connection, table_name, schema=None, **kw):
        """Fetch the oid for schema.table_name.

        Several reflection methods require the table oid.  The idea for using
        this method is that it can be fetched one time and cached for
        subsequent calls.

        """
        table_oid = None
        if schema is not None:
            schema_where_clause = "n.nspname = :schema"
        else:
            schema_where_clause = "pg_catalog.pg_table_is_visible(c.oid)"
        query = """
            SELECT c.oid
            FROM pg_catalog.pg_class c
            LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            WHERE (%s)
            AND c.relname = :table_name AND c.relkind in ('r','v')
        """ % schema_where_clause
        # Since we're binding to unicode, table_name and schema_name must be
        # unicode.
        table_name = unicode(table_name)
        if schema is not None:
            schema = unicode(schema)
        s = sql.text(query, bindparams=[
            sql.bindparam('table_name', type_=sqltypes.Unicode),
            sql.bindparam('schema', type_=sqltypes.Unicode)
            ],
            typemap={'oid': sqltypes.Integer}
        )
        c = connection.execute(s, table_name=table_name, schema=schema)
        table_oid = c.scalar()
        if table_oid is None:
            raise exc.NoSuchTableError(table_name)
        return table_oid

    @reflection.cache
    def get_schema_names(self, connection, **kw):
        s = """
        SELECT nspname
        FROM pg_namespace
        ORDER BY nspname
        """
        rp = connection.execute(s)
        # what about system tables?
        # Py3K
        #schema_names = [row[0] for row in rp \
        #                if not row[0].startswith('pg_')]
        # Py2K
        schema_names = [row[0].decode(self.encoding) for row in rp \
                        if not row[0].startswith('pg_')]
        # end Py2K
        return schema_names

    @reflection.cache
    def get_table_names(self, connection, schema=None, **kw):
        if schema is not None:
            current_schema = schema
        else:
            current_schema = self.default_schema_name

        result = connection.execute(
            sql.text(u"SELECT relname FROM pg_class c "
                "WHERE relkind = 'r' "
                "AND '%s' = (select nspname from pg_namespace n "
                "where n.oid = c.relnamespace) " %
                current_schema,
                typemap={'relname': sqltypes.Unicode}
            )
        )
        return [row[0] for row in result]

    @reflection.cache
    def get_view_names(self, connection, schema=None, **kw):
        if schema is not None:
            current_schema = schema
        else:
            current_schema = self.default_schema_name
        s = """
        SELECT relname
        FROM pg_class c
        WHERE relkind = 'v'
          AND '%(schema)s' = (select nspname from pg_namespace n
          where n.oid = c.relnamespace)
        """ % dict(schema=current_schema)
        # Py3K
        #view_names = [row[0] for row in connection.execute(s)]
        # Py2K
        view_names = [row[0].decode(self.encoding)
                            for row in connection.execute(s)]
        # end Py2K
        return view_names

    @reflection.cache
    def get_view_definition(self, connection, view_name, schema=None, **kw):
        if schema is not None:
            current_schema = schema
        else:
            current_schema = self.default_schema_name
        s = """
        SELECT definition FROM pg_views
        WHERE schemaname = :schema
        AND viewname = :view_name
        """
        rp = connection.execute(sql.text(s),
                                view_name=view_name, schema=current_schema)
        if rp:
            # Py3K
            #view_def = rp.scalar()
            # Py2K
            view_def = rp.scalar().decode(self.encoding)
            # end Py2K
            return view_def

    @reflection.cache
    def get_columns(self, connection, table_name, schema=None, **kw):

        table_oid = self.get_table_oid(connection, table_name, schema,
                                       info_cache=kw.get('info_cache'))
        SQL_COLS = """
            SELECT a.attname,
              pg_catalog.format_type(a.atttypid, a.atttypmod),
              (SELECT pg_catalog.pg_get_expr(d.adbin, d.adrelid)
                FROM pg_catalog.pg_attrdef d
               WHERE d.adrelid = a.attrelid AND d.adnum = a.attnum
               AND a.atthasdef)
              AS DEFAULT,
              a.attnotnull, a.attnum, a.attrelid as table_oid
            FROM pg_catalog.pg_attribute a
            WHERE a.attrelid = :table_oid
            AND a.attnum > 0 AND NOT a.attisdropped
            ORDER BY a.attnum
        """
        s = sql.text(SQL_COLS,
            bindparams=[sql.bindparam('table_oid', type_=sqltypes.Integer)],
            typemap={'attname': sqltypes.Unicode, 'default': sqltypes.Unicode}
        )
        c = connection.execute(s, table_oid=table_oid)
        rows = c.fetchall()
        domains = self._load_domains(connection)
        enums = self._load_enums(connection)

        # format columns
        columns = []
        for name, format_type, default, notnull, attnum, table_oid in rows:
            column_info = self._get_column_info(
                name, format_type, default, notnull, domains, enums, schema)
            columns.append(column_info)
        return columns

    def _get_column_info(self, name, format_type, default,
                         notnull, domains, enums, schema):
        ## strip (*) from character varying(5), timestamp(5)
        # with time zone, geometry(POLYGON), etc.
        attype = re.sub(r'\(.*\)', '', format_type)

        # strip '[]' from integer[], etc.
        attype = re.sub(r'\[\]', '', attype)

        nullable = not notnull
        is_array = format_type.endswith('[]')
        charlen = re.search('\(([\d,]+)\)', format_type)
        if charlen:
            charlen = charlen.group(1)
        args = re.search('\((.*)\)', format_type)
        if args and args.group(1):
            args = tuple(re.split('\s*,\s*', args.group(1)))
        else:
            args = ()
        kwargs = {}

        if attype == 'numeric':
            if charlen:
                prec, scale = charlen.split(',')
                args = (int(prec), int(scale))
            else:
                args = ()
        elif attype == 'double precision':
            args = (53, )
        elif attype == 'integer':
            args = ()
        elif attype in ('timestamp with time zone',
                        'time with time zone'):
            kwargs['timezone'] = True
            if charlen:
                kwargs['precision'] = int(charlen)
            args = ()
        elif attype in ('timestamp without time zone',
                        'time without time zone', 'time'):
            kwargs['timezone'] = False
            if charlen:
                kwargs['precision'] = int(charlen)
            args = ()
        elif attype == 'bit varying':
            kwargs['varying'] = True
            if charlen:
                args = (int(charlen),)
            else:
                args = ()
        elif attype in ('interval', 'interval year to month',
                            'interval day to second'):
            if charlen:
                kwargs['precision'] = int(charlen)
            args = ()
        elif charlen:
            args = (int(charlen),)

        while True:
            if attype in self.ischema_names:
                coltype = self.ischema_names[attype]
                break
            elif attype in enums:
                enum = enums[attype]
                coltype = ENUM
                if "." in attype:
                    kwargs['schema'], kwargs['name'] = attype.split('.')
                else:
                    kwargs['name'] = attype
                args = tuple(enum['labels'])
                break
            elif attype in domains:
                domain = domains[attype]
                attype = domain['attype']
                # A table can't override whether the domain is nullable.
                nullable = domain['nullable']
                if domain['default'] and not default:
                    # It can, however, override the default
                    # value, but can't set it to null.
                    default = domain['default']
                continue
            else:
                coltype = None
                break

        if coltype:
            coltype = coltype(*args, **kwargs)
            if is_array:
                coltype = ARRAY(coltype)
        else:
            util.warn("Did not recognize type '%s' of column '%s'" %
                      (attype, name))
            coltype = sqltypes.NULLTYPE
        # adjust the default value
        autoincrement = False
        if default is not None:
            match = re.search(r"""(nextval\(')([^']+)('.*$)""", default)
            if match is not None:
                autoincrement = True
                # the default is related to a Sequence
                sch = schema
                if '.' not in match.group(2) and sch is not None:
                    # unconditionally quote the schema name.  this could
                    # later be enhanced to obey quoting rules /
                    # "quote schema"
                    default = match.group(1) + \
                                ('"%s"' % sch) + '.' + \
                                match.group(2) + match.group(3)

        column_info = dict(name=name, type=coltype, nullable=nullable,
                           default=default, autoincrement=autoincrement)
        return column_info

    @reflection.cache
    def get_pk_constraint(self, connection, table_name, schema=None, **kw):
        table_oid = self.get_table_oid(connection, table_name, schema,
                                       info_cache=kw.get('info_cache'))

        if self.server_version_info < (8, 4):
            # unnest() and generate_subscripts() both introduced in
            # version 8.4
            PK_SQL = """
                SELECT a.attname
                FROM
                    pg_class t
                    join pg_index ix on t.oid = ix.indrelid
                    join pg_attribute a
                        on t.oid=a.attrelid and a.attnum=ANY(ix.indkey)
                 WHERE
                  t.oid = :table_oid and ix.indisprimary = 't'
                ORDER BY a.attnum
            """
        else:
            PK_SQL = """
                SELECT a.attname
                FROM pg_attribute a JOIN (
                    SELECT unnest(ix.indkey) attnum,
                           generate_subscripts(ix.indkey, 1) ord
                    FROM pg_index ix
                    WHERE ix.indrelid = :table_oid AND ix.indisprimary
                    ) k ON a.attnum=k.attnum
                WHERE a.attrelid = :table_oid
                ORDER BY k.ord
            """
        t = sql.text(PK_SQL, typemap={'attname': sqltypes.Unicode})
        c = connection.execute(t, table_oid=table_oid)
        cols = [r[0] for r in c.fetchall()]

        PK_CONS_SQL = """
        SELECT conname
           FROM  pg_catalog.pg_constraint r
           WHERE r.conrelid = :table_oid AND r.contype = 'p'
           ORDER BY 1
        """
        t = sql.text(PK_CONS_SQL, typemap={'conname': sqltypes.Unicode})
        c = connection.execute(t, table_oid=table_oid)
        name = c.scalar()

        return {'constrained_columns': cols, 'name': name}

    @reflection.cache
    def get_foreign_keys(self, connection, table_name, schema=None, **kw):
        preparer = self.identifier_preparer
        table_oid = self.get_table_oid(connection, table_name, schema,
                                       info_cache=kw.get('info_cache'))

        FK_SQL = """
          SELECT r.conname,
                pg_catalog.pg_get_constraintdef(r.oid, true) as condef,
                n.nspname as conschema
          FROM  pg_catalog.pg_constraint r,
                pg_namespace n,
                pg_class c

          WHERE r.conrelid = :table AND
                r.contype = 'f' AND
                c.oid = confrelid AND
                n.oid = c.relnamespace
          ORDER BY 1
        """

        t = sql.text(FK_SQL, typemap={
                                'conname': sqltypes.Unicode,
                                'condef': sqltypes.Unicode})
        c = connection.execute(t, table=table_oid)
        fkeys = []
        for conname, condef, conschema in c.fetchall():
            m = re.search('FOREIGN KEY \((.*?)\) REFERENCES '
                            '(?:(.*?)\.)?(.*?)\((.*?)\)', condef).groups()
            constrained_columns, referred_schema, \
                    referred_table, referred_columns = m
            constrained_columns = [preparer._unquote_identifier(x)
                        for x in re.split(r'\s*,\s*', constrained_columns)]

            if referred_schema:
                referred_schema =\
                                preparer._unquote_identifier(referred_schema)
            elif schema is not None and schema == conschema:
                # no schema was returned by pg_get_constraintdef().  This
                # means the schema is in the search path.   We will leave
                # it as None, unless the actual schema, which we pull out
                # from pg_namespace even though pg_get_constraintdef() doesn't
                # want to give it to us, matches that of the referencing table,
                # and an explicit schema was given for the referencing table.
                referred_schema = schema
            referred_table = preparer._unquote_identifier(referred_table)
            referred_columns = [preparer._unquote_identifier(x)
                        for x in re.split(r'\s*,\s', referred_columns)]
            fkey_d = {
                'name': conname,
                'constrained_columns': constrained_columns,
                'referred_schema': referred_schema,
                'referred_table': referred_table,
                'referred_columns': referred_columns
            }
            fkeys.append(fkey_d)
        return fkeys

    @reflection.cache
    def get_indexes(self, connection, table_name, schema, **kw):
        table_oid = self.get_table_oid(connection, table_name, schema,
                                       info_cache=kw.get('info_cache'))

        IDX_SQL = """
          SELECT
              i.relname as relname,
              ix.indisunique, ix.indexprs, ix.indpred,
              a.attname, a.attnum, ix.indkey
          FROM
              pg_class t
                    join pg_index ix on t.oid = ix.indrelid
                    join pg_class i on i.oid=ix.indexrelid
                    left outer join
                        pg_attribute a
                        on t.oid=a.attrelid and a.attnum=ANY(ix.indkey)
          WHERE
              t.relkind = 'r'
              and t.oid = :table_oid
              and ix.indisprimary = 'f'
          ORDER BY
              t.relname,
              i.relname
        """

        t = sql.text(IDX_SQL, typemap={'attname': sqltypes.Unicode})
        c = connection.execute(t, table_oid=table_oid)

        indexes = defaultdict(lambda: defaultdict(dict))

        sv_idx_name = None
        for row in c.fetchall():
            idx_name, unique, expr, prd, col, col_num, idx_key = row

            if expr:
                if idx_name != sv_idx_name:
                    util.warn(
                      "Skipped unsupported reflection of "
                      "expression-based index %s"
                      % idx_name)
                sv_idx_name = idx_name
                continue

            if prd and not idx_name == sv_idx_name:
                util.warn(
                   "Predicate of partial index %s ignored during reflection"
                   % idx_name)
                sv_idx_name = idx_name

            index = indexes[idx_name]
            if col is not None:
                index['cols'][col_num] = col
            index['key'] = [int(k.strip()) for k in idx_key.split()]
            index['unique'] = unique

        return [
            {'name': name,
             'unique': idx['unique'],
             'column_names': [idx['cols'][i] for i in idx['key']]}
            for name, idx in indexes.items()
        ]

    def _load_enums(self, connection):
        if not self.supports_native_enum:
            return {}

        ## Load data types for enums:
        SQL_ENUMS = """
            SELECT t.typname as "name",
               -- no enum defaults in 8.4 at least
               -- t.typdefault as "default",
               pg_catalog.pg_type_is_visible(t.oid) as "visible",
               n.nspname as "schema",
               e.enumlabel as "label"
            FROM pg_catalog.pg_type t
                 LEFT JOIN pg_catalog.pg_namespace n ON n.oid = t.typnamespace
                 LEFT JOIN pg_catalog.pg_enum e ON t.oid = e.enumtypid
            WHERE t.typtype = 'e'
            ORDER BY "name", e.oid -- e.oid gives us label order
        """

        s = sql.text(SQL_ENUMS, typemap={
                                'attname': sqltypes.Unicode,
                                'label': sqltypes.Unicode})
        c = connection.execute(s)

        enums = {}
        for enum in c.fetchall():
            if enum['visible']:
                # 'visible' just means whether or not the enum is in a
                # schema that's on the search path -- or not overridden by
                # a schema with higher precedence. If it's not visible,
                # it will be prefixed with the schema-name when it's used.
                name = enum['name']
            else:
                name = "%s.%s" % (enum['schema'], enum['name'])

            if name in enums:
                enums[name]['labels'].append(enum['label'])
            else:
                enums[name] = {
                        'labels': [enum['label']],
                        }

        return enums

    def _load_domains(self, connection):
        ## Load data types for domains:
        SQL_DOMAINS = """
            SELECT t.typname as "name",
               pg_catalog.format_type(t.typbasetype, t.typtypmod) as "attype",
               not t.typnotnull as "nullable",
               t.typdefault as "default",
               pg_catalog.pg_type_is_visible(t.oid) as "visible",
               n.nspname as "schema"
            FROM pg_catalog.pg_type t
               LEFT JOIN pg_catalog.pg_namespace n ON n.oid = t.typnamespace
            WHERE t.typtype = 'd'
        """

        s = sql.text(SQL_DOMAINS, typemap={'attname': sqltypes.Unicode})
        c = connection.execute(s)

        domains = {}
        for domain in c.fetchall():
            ## strip (30) from character varying(30)
            attype = re.search('([^\(]+)', domain['attype']).group(1)
            if domain['visible']:
                # 'visible' just means whether or not the domain is in a
                # schema that's on the search path -- or not overridden by
                # a schema with higher precedence. If it's not visible,
                # it will be prefixed with the schema-name when it's used.
                name = domain['name']
            else:
                name = "%s.%s" % (domain['schema'], domain['name'])

            domains[name] = {
                    'attype': attype,
                    'nullable': domain['nullable'],
                    'default': domain['default']
                }

        return domains
