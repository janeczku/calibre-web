# Copyright (C) 2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

from .base import ischema_names
from ... import types as sqltypes

__all__ = ('INT4RANGE', 'INT8RANGE', 'NUMRANGE')

class RangeOperators(object):
    """
    This mixin provides functionality for the Range Operators
    listed in Table 9-44 of the `postgres documentation`__ for Range
    Functions and Operators. It is used by all the range types
    provided in the ``postgres`` dialect and can likely be used for
    any range types you create yourself.

    __ http://www.postgresql.org/docs/devel/static/functions-range.html

    No extra support is provided for the Range Functions listed in
    Table 9-45 of the postgres documentation. For these, the normal
    :func:`~sqlalchemy.sql.expression.func` object should be used.

    .. versionadded:: 0.8.2  Support for Postgresql RANGE operations.

    """

    class comparator_factory(sqltypes.Concatenable.Comparator):
        """Define comparison operations for range types."""

        def __ne__(self, other):
            "Boolean expression. Returns true if two ranges are not equal"
            return self.expr.op('<>')(other)

        def contains(self, other, **kw):
            """Boolean expression. Returns true if the right hand operand,
            which can be an element or a range, is contained within the
            column.
            """
            return self.expr.op('@>')(other)

        def contained_by(self, other):
            """Boolean expression. Returns true if the column is contained
            within the right hand operand.
            """
            return self.expr.op('<@')(other)

        def overlaps(self, other):
            """Boolean expression. Returns true if the column overlaps
            (has points in common with) the right hand operand.
            """
            return self.expr.op('&&')(other)

        def strictly_left_of(self, other):
            """Boolean expression. Returns true if the column is strictly
            left of the right hand operand.
            """
            return self.expr.op('<<')(other)

        __lshift__ = strictly_left_of

        def strictly_right_of(self, other):
            """Boolean expression. Returns true if the column is strictly
            right of the right hand operand.
            """
            return self.expr.op('>>')(other)

        __rshift__ = strictly_right_of

        def not_extend_right_of(self, other):
            """Boolean expression. Returns true if the range in the column
            does not extend right of the range in the operand.
            """
            return self.expr.op('&<')(other)

        def not_extend_left_of(self, other):
            """Boolean expression. Returns true if the range in the column
            does not extend left of the range in the operand.
            """
            return self.expr.op('&>')(other)

        def adjacent_to(self, other):
            """Boolean expression. Returns true if the range in the column
            is adjacent to the range in the operand.
            """
            return self.expr.op('-|-')(other)

        def __add__(self, other):
            """Range expression. Returns the union of the two ranges.
            Will raise an exception if the resulting range is not
            contigous.
            """
            return self.expr.op('+')(other)

class INT4RANGE(RangeOperators, sqltypes.TypeEngine):
    """Represent the Postgresql INT4RANGE type.

    .. versionadded:: 0.8.2

    """

    __visit_name__ = 'INT4RANGE'

ischema_names['int4range'] = INT4RANGE

class INT8RANGE(RangeOperators, sqltypes.TypeEngine):
    """Represent the Postgresql INT8RANGE type.

    .. versionadded:: 0.8.2

    """

    __visit_name__ = 'INT8RANGE'

ischema_names['int8range'] = INT8RANGE

class NUMRANGE(RangeOperators, sqltypes.TypeEngine):
    """Represent the Postgresql NUMRANGE type.

    .. versionadded:: 0.8.2

    """

    __visit_name__ = 'NUMRANGE'

ischema_names['numrange'] = NUMRANGE

class DATERANGE(RangeOperators, sqltypes.TypeEngine):
    """Represent the Postgresql DATERANGE type.

    .. versionadded:: 0.8.2

    """

    __visit_name__ = 'DATERANGE'

ischema_names['daterange'] = DATERANGE

class TSRANGE(RangeOperators, sqltypes.TypeEngine):
    """Represent the Postgresql TSRANGE type.

    .. versionadded:: 0.8.2

    """

    __visit_name__ = 'TSRANGE'

ischema_names['tsrange'] = TSRANGE

class TSTZRANGE(RangeOperators, sqltypes.TypeEngine):
    """Represent the Postgresql TSTZRANGE type.

    .. versionadded:: 0.8.2

    """

    __visit_name__ = 'TSTZRANGE'

ischema_names['tstzrange'] = TSTZRANGE
