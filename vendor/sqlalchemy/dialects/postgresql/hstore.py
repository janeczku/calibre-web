# postgresql/hstore.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

import re

from .base import ARRAY, ischema_names
from ... import types as sqltypes
from ...sql import functions as sqlfunc
from ...sql.operators import custom_op
from ... import util

__all__ = ('HSTORE', 'hstore')

# My best guess at the parsing rules of hstore literals, since no formal
# grammar is given.  This is mostly reverse engineered from PG's input parser
# behavior.
HSTORE_PAIR_RE = re.compile(r"""
(
  "(?P<key> (\\ . | [^"])* )"       # Quoted key
)
[ ]* => [ ]*    # Pair operator, optional adjoining whitespace
(
    (?P<value_null> NULL )          # NULL value
  | "(?P<value> (\\ . | [^"])* )"   # Quoted value
)
""", re.VERBOSE)

HSTORE_DELIMITER_RE = re.compile(r"""
[ ]* , [ ]*
""", re.VERBOSE)


def _parse_error(hstore_str, pos):
    """format an unmarshalling error."""

    ctx = 20
    hslen = len(hstore_str)

    parsed_tail = hstore_str[max(pos - ctx - 1, 0):min(pos, hslen)]
    residual = hstore_str[min(pos, hslen):min(pos + ctx + 1, hslen)]

    if len(parsed_tail) > ctx:
        parsed_tail = '[...]' + parsed_tail[1:]
    if len(residual) > ctx:
        residual = residual[:-1] + '[...]'

    return "After %r, could not parse residual at position %d: %r" % (
        parsed_tail, pos, residual)


def _parse_hstore(hstore_str):
    """Parse an hstore from it's literal string representation.

    Attempts to approximate PG's hstore input parsing rules as closely as
    possible. Although currently this is not strictly necessary, since the
    current implementation of hstore's output syntax is stricter than what it
    accepts as input, the documentation makes no guarantees that will always
    be the case.



    """
    result = {}
    pos = 0
    pair_match = HSTORE_PAIR_RE.match(hstore_str)

    while pair_match is not None:
        key = pair_match.group('key').replace(r'\"', '"').replace("\\\\", "\\")
        if pair_match.group('value_null'):
            value = None
        else:
            value = pair_match.group('value').replace(r'\"', '"').replace("\\\\", "\\")
        result[key] = value

        pos += pair_match.end()

        delim_match = HSTORE_DELIMITER_RE.match(hstore_str[pos:])
        if delim_match is not None:
            pos += delim_match.end()

        pair_match = HSTORE_PAIR_RE.match(hstore_str[pos:])

    if pos != len(hstore_str):
        raise ValueError(_parse_error(hstore_str, pos))

    return result


def _serialize_hstore(val):
    """Serialize a dictionary into an hstore literal.  Keys and values must
    both be strings (except None for values).

    """
    def esc(s, position):
        if position == 'value' and s is None:
            return 'NULL'
        elif isinstance(s, basestring):
            return '"%s"' % s.replace("\\", "\\\\").replace('"', r'\"')
        else:
            raise ValueError("%r in %s position is not a string." %
                             (s, position))

    return ', '.join('%s=>%s' % (esc(k, 'key'), esc(v, 'value'))
                     for k, v in val.iteritems())


class HSTORE(sqltypes.Concatenable, sqltypes.TypeEngine):
    """Represent the Postgresql HSTORE type.

    The :class:`.HSTORE` type stores dictionaries containing strings, e.g.::

        data_table = Table('data_table', metadata,
            Column('id', Integer, primary_key=True),
            Column('data', HSTORE)
        )

        with engine.connect() as conn:
            conn.execute(
                data_table.insert(),
                data = {"key1": "value1", "key2": "value2"}
            )

    :class:`.HSTORE` provides for a wide range of operations, including:

    * Index operations::

        data_table.c.data['some key'] == 'some value'

    * Containment operations::

        data_table.c.data.has_key('some key')

        data_table.c.data.has_all(['one', 'two', 'three'])

    * Concatenation::

        data_table.c.data + {"k1": "v1"}

    For a full list of special methods see :class:`.HSTORE.comparator_factory`.

    For usage with the SQLAlchemy ORM, it may be desirable to combine
    the usage of :class:`.HSTORE` with :class:`.MutableDict` dictionary
    now part of the :mod:`sqlalchemy.ext.mutable`
    extension.  This extension will allow "in-place" changes to the
    dictionary, e.g. addition of new keys or replacement/removal of existing
    keys to/from the current dictionary, to produce events which will be detected
    by the unit of work::

        from sqlalchemy.ext.mutable import MutableDict

        class MyClass(Base):
            __tablename__ = 'data_table'

            id = Column(Integer, primary_key=True)
            data = Column(MutableDict.as_mutable(HSTORE))

        my_object = session.query(MyClass).one()

        # in-place mutation, requires Mutable extension
        # in order for the ORM to detect
        my_object.data['some_key'] = 'some value'

        session.commit()

    When the :mod:`sqlalchemy.ext.mutable` extension is not used, the ORM
    will not be alerted to any changes to the contents of an existing dictionary,
    unless that dictionary value is re-assigned to the HSTORE-attribute itself,
    thus generating a change event.

    .. versionadded:: 0.8

    .. seealso::

        :class:`.hstore` - render the Postgresql ``hstore()`` function.


    """

    __visit_name__ = 'HSTORE'

    class comparator_factory(sqltypes.Concatenable.Comparator):
        """Define comparison operations for :class:`.HSTORE`."""

        def has_key(self, other):
            """Boolean expression.  Test for presence of a key.  Note that the
            key may be a SQLA expression.
            """
            return self.expr.op('?')(other)

        def has_all(self, other):
            """Boolean expression.  Test for presence of all keys in the PG
            array.
            """
            return self.expr.op('?&')(other)

        def has_any(self, other):
            """Boolean expression.  Test for presence of any key in the PG
            array.
            """
            return self.expr.op('?|')(other)

        def defined(self, key):
            """Boolean expression.  Test for presence of a non-NULL value for
            the key.  Note that the key may be a SQLA expression.
            """
            return _HStoreDefinedFunction(self.expr, key)

        def contains(self, other, **kwargs):
            """Boolean expression.  Test if keys are a superset of the keys of
            the argument hstore expression.
            """
            return self.expr.op('@>')(other)

        def contained_by(self, other):
            """Boolean expression.  Test if keys are a proper subset of the
            keys of the argument hstore expression.
            """
            return self.expr.op('<@')(other)

        def __getitem__(self, other):
            """Text expression.  Get the value at a given key.  Note that the
            key may be a SQLA expression.
            """
            return self.expr.op('->', precedence=5)(other)

        def delete(self, key):
            """HStore expression.  Returns the contents of this hstore with the
            given key deleted.  Note that the key may be a SQLA expression.
            """
            if isinstance(key, dict):
                key = _serialize_hstore(key)
            return _HStoreDeleteFunction(self.expr, key)

        def slice(self, array):
            """HStore expression.  Returns a subset of an hstore defined by
            array of keys.
            """
            return _HStoreSliceFunction(self.expr, array)

        def keys(self):
            """Text array expression.  Returns array of keys."""
            return _HStoreKeysFunction(self.expr)

        def vals(self):
            """Text array expression.  Returns array of values."""
            return _HStoreValsFunction(self.expr)

        def array(self):
            """Text array expression.  Returns array of alternating keys and
            values.
            """
            return _HStoreArrayFunction(self.expr)

        def matrix(self):
            """Text array expression.  Returns array of [key, value] pairs."""
            return _HStoreMatrixFunction(self.expr)

        def _adapt_expression(self, op, other_comparator):
            if isinstance(op, custom_op):
                if op.opstring in ['?', '?&', '?|', '@>', '<@']:
                    return op, sqltypes.Boolean
                elif op.opstring == '->':
                    return op, sqltypes.Text
            return sqltypes.Concatenable.Comparator.\
                _adapt_expression(self, op, other_comparator)

    def bind_processor(self, dialect):
        if util.py2k:
            encoding = dialect.encoding
            def process(value):
                if isinstance(value, dict):
                    return _serialize_hstore(value).encode(encoding)
                else:
                    return value
        else:
            def process(value):
                if isinstance(value, dict):
                    return _serialize_hstore(value)
                else:
                    return value
        return process

    def result_processor(self, dialect, coltype):
        if util.py2k:
            encoding = dialect.encoding
            def process(value):
                if value is not None:
                    return _parse_hstore(value.decode(encoding))
                else:
                    return value
        else:
            def process(value):
                if value is not None:
                    return _parse_hstore(value)
                else:
                    return value
        return process


ischema_names['hstore'] = HSTORE


class hstore(sqlfunc.GenericFunction):
    """Construct an hstore value within a SQL expression using the
    Postgresql ``hstore()`` function.

    The :class:`.hstore` function accepts one or two arguments as described
    in the Postgresql documentation.

    E.g.::

        from sqlalchemy.dialects.postgresql import array, hstore

        select([hstore('key1', 'value1')])

        select([
                hstore(
                    array(['key1', 'key2', 'key3']),
                    array(['value1', 'value2', 'value3'])
                )
            ])

    .. versionadded:: 0.8

    .. seealso::

        :class:`.HSTORE` - the Postgresql ``HSTORE`` datatype.

    """
    type = HSTORE
    name = 'hstore'


class _HStoreDefinedFunction(sqlfunc.GenericFunction):
    type = sqltypes.Boolean
    name = 'defined'


class _HStoreDeleteFunction(sqlfunc.GenericFunction):
    type = HSTORE
    name = 'delete'


class _HStoreSliceFunction(sqlfunc.GenericFunction):
    type = HSTORE
    name = 'slice'


class _HStoreKeysFunction(sqlfunc.GenericFunction):
    type = ARRAY(sqltypes.Text)
    name = 'akeys'


class _HStoreValsFunction(sqlfunc.GenericFunction):
    type = ARRAY(sqltypes.Text)
    name = 'avals'


class _HStoreArrayFunction(sqlfunc.GenericFunction):
    type = ARRAY(sqltypes.Text)
    name = 'hstore_to_array'


class _HStoreMatrixFunction(sqlfunc.GenericFunction):
    type = ARRAY(sqltypes.Text)
    name = 'hstore_to_matrix'
