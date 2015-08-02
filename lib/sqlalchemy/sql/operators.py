# sql/operators.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Defines operators used in SQL expressions."""

from operator import (
    and_, or_, inv, add, mul, sub, mod, truediv, lt, le, ne, gt, ge, eq, neg,
    getitem, lshift, rshift
    )

# Py2K
from operator import (div,)
# end Py2K

from ..util import symbol


class Operators(object):
    """Base of comparison and logical operators.

    Implements base methods :meth:`operate` and :meth:`reverse_operate`,
    as well as :meth:`__and__`, :meth:`__or__`, :meth:`__invert__`.

    Usually is used via its most common subclass
    :class:`.ColumnOperators`.

    """
    def __and__(self, other):
        """Implement the ``&`` operator.

        When used with SQL expressions, results in an
        AND operation, equivalent to
        :func:`~.expression.and_`, that is::

            a & b

        is equivalent to::

            from sqlalchemy import and_
            and_(a, b)

        Care should be taken when using ``&`` regarding
        operator precedence; the ``&`` operator has the highest precedence.
        The operands should be enclosed in parenthesis if they contain
        further sub expressions::

            (a == 2) & (b == 4)

        """
        return self.operate(and_, other)

    def __or__(self, other):
        """Implement the ``|`` operator.

        When used with SQL expressions, results in an
        OR operation, equivalent to
        :func:`~.expression.or_`, that is::

            a | b

        is equivalent to::

            from sqlalchemy import or_
            or_(a, b)

        Care should be taken when using ``|`` regarding
        operator precedence; the ``|`` operator has the highest precedence.
        The operands should be enclosed in parenthesis if they contain
        further sub expressions::

            (a == 2) | (b == 4)

        """
        return self.operate(or_, other)

    def __invert__(self):
        """Implement the ``~`` operator.

        When used with SQL expressions, results in a
        NOT operation, equivalent to
        :func:`~.expression.not_`, that is::

            ~a

        is equivalent to::

            from sqlalchemy import not_
            not_(a)

        """
        return self.operate(inv)

    def op(self, opstring, precedence=0):
        """produce a generic operator function.

        e.g.::

          somecolumn.op("*")(5)

        produces::

          somecolumn * 5

        This function can also be used to make bitwise operators explicit. For
        example::

          somecolumn.op('&')(0xff)

        is a bitwise AND of the value in ``somecolumn``.

        :param operator: a string which will be output as the infix operator
          between this element and the expression passed to the
          generated function.

        :param precedence: precedence to apply to the operator, when
         parenthesizing expressions.  A lower number will cause the expression
         to be parenthesized when applied against another operator with
         higher precedence.  The default value of ``0`` is lower than all
         operators except for the comma (``,``) and ``AS`` operators.
         A value of 100 will be higher or equal to all operators, and -100
         will be lower than or equal to all operators.

         .. versionadded:: 0.8 - added the 'precedence' argument.

        .. seealso::

            :ref:`types_operators`

        """
        operator = custom_op(opstring, precedence)

        def against(other):
            return operator(self, other)
        return against

    def operate(self, op, *other, **kwargs):
        """Operate on an argument.

        This is the lowest level of operation, raises
        :class:`NotImplementedError` by default.

        Overriding this on a subclass can allow common
        behavior to be applied to all operations.
        For example, overriding :class:`.ColumnOperators`
        to apply ``func.lower()`` to the left and right
        side::

            class MyComparator(ColumnOperators):
                def operate(self, op, other):
                    return op(func.lower(self), func.lower(other))

        :param op:  Operator callable.
        :param \*other: the 'other' side of the operation. Will
         be a single scalar for most operations.
        :param \**kwargs: modifiers.  These may be passed by special
         operators such as :meth:`ColumnOperators.contains`.


        """
        raise NotImplementedError(str(op))

    def reverse_operate(self, op, other, **kwargs):
        """Reverse operate on an argument.

        Usage is the same as :meth:`operate`.

        """
        raise NotImplementedError(str(op))


class custom_op(object):
    """Represent a 'custom' operator.

    :class:`.custom_op` is normally instantitated when the
    :meth:`.ColumnOperators.op` method is used to create a
    custom operator callable.  The class can also be used directly
    when programmatically constructing expressions.   E.g.
    to represent the "factorial" operation::

        from sqlalchemy.sql import UnaryExpression
        from sqlalchemy.sql import operators
        from sqlalchemy import Numeric

        unary = UnaryExpression(table.c.somecolumn,
                modifier=operators.custom_op("!"),
                type_=Numeric)

    """
    __name__ = 'custom_op'

    def __init__(self, opstring, precedence=0):
        self.opstring = opstring
        self.precedence = precedence

    def __eq__(self, other):
        return isinstance(other, custom_op) and \
            other.opstring == self.opstring

    def __hash__(self):
        return id(self)

    def __call__(self, left, right, **kw):
        return left.operate(self, right, **kw)


class ColumnOperators(Operators):
    """Defines boolean, comparison, and other operators for
    :class:`.ColumnElement` expressions.

    By default, all methods call down to
    :meth:`.operate` or :meth:`.reverse_operate`,
    passing in the appropriate operator function from the
    Python builtin ``operator`` module or
    a SQLAlchemy-specific operator function from
    :mod:`sqlalchemy.expression.operators`.   For example
    the ``__eq__`` function::

        def __eq__(self, other):
            return self.operate(operators.eq, other)

    Where ``operators.eq`` is essentially::

        def eq(a, b):
            return a == b

    The core column expression unit :class:`.ColumnElement`
    overrides :meth:`.Operators.operate` and others
    to return further :class:`.ColumnElement` constructs,
    so that the ``==`` operation above is replaced by a clause
    construct.

    See also:

    :ref:`types_operators`

    :attr:`.TypeEngine.comparator_factory`

    :class:`.ColumnOperators`

    :class:`.PropComparator`

    """

    timetuple = None
    """Hack, allows datetime objects to be compared on the LHS."""

    def __lt__(self, other):
        """Implement the ``<`` operator.

        In a column context, produces the clause ``a < b``.

        """
        return self.operate(lt, other)

    def __le__(self, other):
        """Implement the ``<=`` operator.

        In a column context, produces the clause ``a <= b``.

        """
        return self.operate(le, other)

    __hash__ = Operators.__hash__

    def __eq__(self, other):
        """Implement the ``==`` operator.

        In a column context, produces the clause ``a = b``.
        If the target is ``None``, produces ``a IS NULL``.

        """
        return self.operate(eq, other)

    def __ne__(self, other):
        """Implement the ``!=`` operator.

        In a column context, produces the clause ``a != b``.
        If the target is ``None``, produces ``a IS NOT NULL``.

        """
        return self.operate(ne, other)

    def __gt__(self, other):
        """Implement the ``>`` operator.

        In a column context, produces the clause ``a > b``.

        """
        return self.operate(gt, other)

    def __ge__(self, other):
        """Implement the ``>=`` operator.

        In a column context, produces the clause ``a >= b``.

        """
        return self.operate(ge, other)

    def __neg__(self):
        """Implement the ``-`` operator.

        In a column context, produces the clause ``-a``.

        """
        return self.operate(neg)

    def __getitem__(self, index):
        """Implement the [] operator.

        This can be used by some database-specific types
        such as Postgresql ARRAY and HSTORE.

        """
        return self.operate(getitem, index)

    def __lshift__(self, other):
        """implement the << operator.

        Not used by SQLAlchemy core, this is provided
        for custom operator systems which want to use
        << as an extension point.
        """
        return self.operate(lshift, other)

    def __rshift__(self, other):
        """implement the >> operator.

        Not used by SQLAlchemy core, this is provided
        for custom operator systems which want to use
        >> as an extension point.
        """
        return self.operate(rshift, other)

    def concat(self, other):
        """Implement the 'concat' operator.

        In a column context, produces the clause ``a || b``,
        or uses the ``concat()`` operator on MySQL.

        """
        return self.operate(concat_op, other)

    def like(self, other, escape=None):
        """Implement the ``like`` operator.

        In a column context, produces the clause ``a LIKE other``.

        E.g.::

            select([sometable]).where(sometable.c.column.like("%foobar%"))

        :param other: expression to be compared
        :param escape: optional escape character, renders the ``ESCAPE``
          keyword, e.g.::

            somecolumn.like("foo/%bar", escape="/")

        .. seealso::

            :meth:`.ColumnOperators.ilike`

        """
        return self.operate(like_op, other, escape=escape)

    def ilike(self, other, escape=None):
        """Implement the ``ilike`` operator.

        In a column context, produces the clause ``a ILIKE other``.

        E.g.::

            select([sometable]).where(sometable.c.column.ilike("%foobar%"))

        :param other: expression to be compared
        :param escape: optional escape character, renders the ``ESCAPE``
          keyword, e.g.::

            somecolumn.ilike("foo/%bar", escape="/")

        .. seealso::

            :meth:`.ColumnOperators.like`

        """
        return self.operate(ilike_op, other, escape=escape)

    def in_(self, other):
        """Implement the ``in`` operator.

        In a column context, produces the clause ``a IN other``.
        "other" may be a tuple/list of column expressions,
        or a :func:`~.expression.select` construct.

        """
        return self.operate(in_op, other)

    def notin_(self, other):
        """implement the ``NOT IN`` operator.

        This is equivalent to using negation with :meth:`.ColumnOperators.in_`,
        i.e. ``~x.in_(y)``.

        .. versionadded:: 0.8

        .. seealso::

            :meth:`.ColumnOperators.in_`

        """
        return self.operate(notin_op, other)

    def notlike(self, other, escape=None):
        """implement the ``NOT LIKE`` operator.

        This is equivalent to using negation with
        :meth:`.ColumnOperators.like`, i.e. ``~x.like(y)``.

        .. versionadded:: 0.8

        .. seealso::

            :meth:`.ColumnOperators.like`

        """
        return self.operate(notlike_op, other, escape=escape)

    def notilike(self, other, escape=None):
        """implement the ``NOT ILIKE`` operator.

        This is equivalent to using negation with
        :meth:`.ColumnOperators.ilike`, i.e. ``~x.ilike(y)``.

        .. versionadded:: 0.8

        .. seealso::

            :meth:`.ColumnOperators.ilike`

        """
        return self.operate(notilike_op, other, escape=escape)

    def is_(self, other):
        """Implement the ``IS`` operator.

        Normally, ``IS`` is generated automatically when comparing to a
        value of ``None``, which resolves to ``NULL``.  However, explicit
        usage of ``IS`` may be desirable if comparing to boolean values
        on certain platforms.

        .. versionadded:: 0.7.9

        .. seealso:: :meth:`.ColumnOperators.isnot`

        """
        return self.operate(is_, other)

    def isnot(self, other):
        """Implement the ``IS NOT`` operator.

        Normally, ``IS NOT`` is generated automatically when comparing to a
        value of ``None``, which resolves to ``NULL``.  However, explicit
        usage of ``IS NOT`` may be desirable if comparing to boolean values
        on certain platforms.

        .. versionadded:: 0.7.9

        .. seealso:: :meth:`.ColumnOperators.is_`

        """
        return self.operate(isnot, other)

    def startswith(self, other, **kwargs):
        """Implement the ``startwith`` operator.

        In a column context, produces the clause ``LIKE '<other>%'``

        """
        return self.operate(startswith_op, other, **kwargs)

    def endswith(self, other, **kwargs):
        """Implement the 'endswith' operator.

        In a column context, produces the clause ``LIKE '%<other>'``

        """
        return self.operate(endswith_op, other, **kwargs)

    def contains(self, other, **kwargs):
        """Implement the 'contains' operator.

        In a column context, produces the clause ``LIKE '%<other>%'``

        """
        return self.operate(contains_op, other, **kwargs)

    def match(self, other, **kwargs):
        """Implements the 'match' operator.

        In a column context, this produces a MATCH clause, i.e.
        ``MATCH '<other>'``.  The allowed contents of ``other``
        are database backend specific.

        """
        return self.operate(match_op, other, **kwargs)

    def desc(self):
        """Produce a :func:`~.expression.desc` clause against the
        parent object."""
        return self.operate(desc_op)

    def asc(self):
        """Produce a :func:`~.expression.asc` clause against the
        parent object."""
        return self.operate(asc_op)

    def nullsfirst(self):
        """Produce a :func:`~.expression.nullsfirst` clause against the
        parent object."""
        return self.operate(nullsfirst_op)

    def nullslast(self):
        """Produce a :func:`~.expression.nullslast` clause against the
        parent object."""
        return self.operate(nullslast_op)

    def collate(self, collation):
        """Produce a :func:`~.expression.collate` clause against
        the parent object, given the collation string."""
        return self.operate(collate, collation)

    def __radd__(self, other):
        """Implement the ``+`` operator in reverse.

        See :meth:`.ColumnOperators.__add__`.

        """
        return self.reverse_operate(add, other)

    def __rsub__(self, other):
        """Implement the ``-`` operator in reverse.

        See :meth:`.ColumnOperators.__sub__`.

        """
        return self.reverse_operate(sub, other)

    def __rmul__(self, other):
        """Implement the ``*`` operator in reverse.

        See :meth:`.ColumnOperators.__mul__`.

        """
        return self.reverse_operate(mul, other)

    def __rdiv__(self, other):
        """Implement the ``/`` operator in reverse.

        See :meth:`.ColumnOperators.__div__`.

        """
        return self.reverse_operate(div, other)

    def between(self, cleft, cright):
        """Produce a :func:`~.expression.between` clause against
        the parent object, given the lower and upper range."""
        return self.operate(between_op, cleft, cright)

    def distinct(self):
        """Produce a :func:`~.expression.distinct` clause against the
        parent object.

        """
        return self.operate(distinct_op)

    def __add__(self, other):
        """Implement the ``+`` operator.

        In a column context, produces the clause ``a + b``
        if the parent object has non-string affinity.
        If the parent object has a string affinity,
        produces the concatenation operator, ``a || b`` -
        see :meth:`.ColumnOperators.concat`.

        """
        return self.operate(add, other)

    def __sub__(self, other):
        """Implement the ``-`` operator.

        In a column context, produces the clause ``a - b``.

        """
        return self.operate(sub, other)

    def __mul__(self, other):
        """Implement the ``*`` operator.

        In a column context, produces the clause ``a * b``.

        """
        return self.operate(mul, other)

    def __div__(self, other):
        """Implement the ``/`` operator.

        In a column context, produces the clause ``a / b``.

        """
        return self.operate(div, other)

    def __mod__(self, other):
        """Implement the ``%`` operator.

        In a column context, produces the clause ``a % b``.

        """
        return self.operate(mod, other)

    def __truediv__(self, other):
        """Implement the ``//`` operator.

        In a column context, produces the clause ``a / b``.

        """
        return self.operate(truediv, other)

    def __rtruediv__(self, other):
        """Implement the ``//`` operator in reverse.

        See :meth:`.ColumnOperators.__truediv__`.

        """
        return self.reverse_operate(truediv, other)


def from_():
    raise NotImplementedError()


def as_():
    raise NotImplementedError()


def exists():
    raise NotImplementedError()


def is_(a, b):
    return a.is_(b)


def isnot(a, b):
    return a.isnot(b)


def collate(a, b):
    return a.collate(b)


def op(a, opstring, b):
    return a.op(opstring)(b)


def like_op(a, b, escape=None):
    return a.like(b, escape=escape)


def notlike_op(a, b, escape=None):
    return a.notlike(b, escape=escape)


def ilike_op(a, b, escape=None):
    return a.ilike(b, escape=escape)


def notilike_op(a, b, escape=None):
    return a.notilike(b, escape=escape)


def between_op(a, b, c):
    return a.between(b, c)


def in_op(a, b):
    return a.in_(b)


def notin_op(a, b):
    return a.notin_(b)


def distinct_op(a):
    return a.distinct()


def startswith_op(a, b, escape=None):
    return a.startswith(b, escape=escape)


def notstartswith_op(a, b, escape=None):
    return ~a.startswith(b, escape=escape)


def endswith_op(a, b, escape=None):
    return a.endswith(b, escape=escape)


def notendswith_op(a, b, escape=None):
    return ~a.endswith(b, escape=escape)


def contains_op(a, b, escape=None):
    return a.contains(b, escape=escape)


def notcontains_op(a, b, escape=None):
    return ~a.contains(b, escape=escape)


def match_op(a, b):
    return a.match(b)


def comma_op(a, b):
    raise NotImplementedError()


def concat_op(a, b):
    return a.concat(b)


def desc_op(a):
    return a.desc()


def asc_op(a):
    return a.asc()


def nullsfirst_op(a):
    return a.nullsfirst()


def nullslast_op(a):
    return a.nullslast()


_commutative = set([eq, ne, add, mul])

_comparison = set([eq, ne, lt, gt, ge, le, between_op])


def is_comparison(op):
    return op in _comparison


def is_commutative(op):
    return op in _commutative


def is_ordering_modifier(op):
    return op in (asc_op, desc_op,
                    nullsfirst_op, nullslast_op)

_associative = _commutative.union([concat_op, and_, or_])

_natural_self_precedent = _associative.union([getitem])
"""Operators where if we have (a op b) op c, we don't want to
parenthesize (a op b).

"""

_smallest = symbol('_smallest', canonical=-100)
_largest = symbol('_largest', canonical=100)

_PRECEDENCE = {
    from_: 15,
    getitem: 15,
    mul: 8,
    truediv: 8,
    # Py2K
    div: 8,
    # end Py2K
    mod: 8,
    neg: 8,
    add: 7,
    sub: 7,

    concat_op: 6,
    match_op: 6,

    ilike_op: 6,
    notilike_op: 6,
    like_op: 6,
    notlike_op: 6,
    in_op: 6,
    notin_op: 6,

    is_: 6,
    isnot: 6,

    eq: 5,
    ne: 5,
    gt: 5,
    lt: 5,
    ge: 5,
    le: 5,

    between_op: 5,
    distinct_op: 5,
    inv: 5,
    and_: 3,
    or_: 2,
    comma_op: -1,
    collate: 7,
    as_: -1,
    exists: 0,
    _smallest: _smallest,
    _largest: _largest
}


def is_precedent(operator, against):
    if operator is against and operator in _natural_self_precedent:
        return False
    else:
        return (_PRECEDENCE.get(operator,
                getattr(operator, 'precedence', _smallest)) <=
            _PRECEDENCE.get(against,
                getattr(against, 'precedence', _largest)))
