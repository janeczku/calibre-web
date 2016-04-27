# sql/functions.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

from .. import types as sqltypes, schema
from .expression import (
    ClauseList, Function, _literal_as_binds, literal_column, _type_from_args,
    cast, extract
    )
from . import operators
from .visitors import VisitableType
from .. import util

_registry = util.defaultdict(dict)


def register_function(identifier, fn, package="_default"):
    """Associate a callable with a particular func. name.

    This is normally called by _GenericMeta, but is also
    available by itself so that a non-Function construct
    can be associated with the :data:`.func` accessor (i.e.
    CAST, EXTRACT).

    """
    reg = _registry[package]
    reg[identifier] = fn


class _GenericMeta(VisitableType):
    def __init__(cls, clsname, bases, clsdict):
        cls.name = name = clsdict.get('name', clsname)
        cls.identifier = identifier = clsdict.get('identifier', name)
        package = clsdict.pop('package', '_default')
        # legacy
        if '__return_type__' in clsdict:
            cls.type = clsdict['__return_type__']
        register_function(identifier, cls, package)
        super(_GenericMeta, cls).__init__(clsname, bases, clsdict)


class GenericFunction(Function):
    """Define a 'generic' function.

    A generic function is a pre-established :class:`.Function`
    class that is instantiated automatically when called
    by name from the :data:`.func` attribute.    Note that
    calling any name from :data:`.func` has the effect that
    a new :class:`.Function` instance is created automatically,
    given that name.  The primary use case for defining
    a :class:`.GenericFunction` class is so that a function
    of a particular name may be given a fixed return type.
    It can also include custom argument parsing schemes as well
    as additional methods.

    Subclasses of :class:`.GenericFunction` are automatically
    registered under the name of the class.  For
    example, a user-defined function ``as_utc()`` would
    be available immediately::

        from sqlalchemy.sql.functions import GenericFunction
        from sqlalchemy.types import DateTime

        class as_utc(GenericFunction):
            type = DateTime

        print select([func.as_utc()])

    User-defined generic functions can be organized into
    packages by specifying the "package" attribute when defining
    :class:`.GenericFunction`.   Third party libraries
    containing many functions may want to use this in order
    to avoid name conflicts with other systems.   For example,
    if our ``as_utc()`` function were part of a package
    "time"::

        class as_utc(GenericFunction):
            type = DateTime
            package = "time"

    The above function would be available from :data:`.func`
    using the package name ``time``::

        print select([func.time.as_utc()])

    A final option is to allow the function to be accessed
    from one name in :data:`.func` but to render as a different name.
    The ``identifier`` attribute will override the name used to
    access the function as loaded from :data:`.func`, but will retain
    the usage of ``name`` as the rendered name::

        class GeoBuffer(GenericFunction):
            type = Geometry
            package = "geo"
            name = "ST_Buffer"
            identifier = "buffer"

    The above function will render as follows::

        >>> print func.geo.buffer()
        ST_Buffer()

    .. versionadded:: 0.8 :class:`.GenericFunction` now supports
       automatic registration of new functions as well as package
       and custom naming support.

    .. versionchanged:: 0.8 The attribute name ``type`` is used
       to specify the function's return type at the class level.
       Previously, the name ``__return_type__`` was used.  This
       name is still recognized for backwards-compatibility.

    """
    __metaclass__ = _GenericMeta

    coerce_arguments = True

    def __init__(self, *args, **kwargs):
        parsed_args = kwargs.pop('_parsed_args', None)
        if parsed_args is None:
            parsed_args = [_literal_as_binds(c) for c in args]
        self.packagenames = []
        self._bind = kwargs.get('bind', None)
        self.clause_expr = ClauseList(
                operator=operators.comma_op,
                group_contents=True, *parsed_args).self_group()
        self.type = sqltypes.to_instance(
            kwargs.pop("type_", None) or getattr(self, 'type', None))


register_function("cast", cast)
register_function("extract", extract)


class next_value(GenericFunction):
    """Represent the 'next value', given a :class:`.Sequence`
    as it's single argument.

    Compiles into the appropriate function on each backend,
    or will raise NotImplementedError if used on a backend
    that does not provide support for sequences.

    """
    type = sqltypes.Integer()
    name = "next_value"

    def __init__(self, seq, **kw):
        assert isinstance(seq, schema.Sequence), \
                "next_value() accepts a Sequence object as input."
        self._bind = kw.get('bind', None)
        self.sequence = seq

    @property
    def _from_objects(self):
        return []


class AnsiFunction(GenericFunction):
    def __init__(self, **kwargs):
        GenericFunction.__init__(self, **kwargs)


class ReturnTypeFromArgs(GenericFunction):
    """Define a function whose return type is the same as its arguments."""

    def __init__(self, *args, **kwargs):
        args = [_literal_as_binds(c) for c in args]
        kwargs.setdefault('type_', _type_from_args(args))
        kwargs['_parsed_args'] = args
        GenericFunction.__init__(self, *args, **kwargs)


class coalesce(ReturnTypeFromArgs):
    pass


class max(ReturnTypeFromArgs):
    pass


class min(ReturnTypeFromArgs):
    pass


class sum(ReturnTypeFromArgs):
    pass


class now(GenericFunction):
    type = sqltypes.DateTime


class concat(GenericFunction):
    type = sqltypes.String


class char_length(GenericFunction):
    type = sqltypes.Integer

    def __init__(self, arg, **kwargs):
        GenericFunction.__init__(self, arg, **kwargs)


class random(GenericFunction):
    pass


class count(GenericFunction):
    """The ANSI COUNT aggregate function.  With no arguments,
    emits COUNT \*.

    """
    type = sqltypes.Integer

    def __init__(self, expression=None, **kwargs):
        if expression is None:
            expression = literal_column('*')
        GenericFunction.__init__(self, expression, **kwargs)


class current_date(AnsiFunction):
    type = sqltypes.Date


class current_time(AnsiFunction):
    type = sqltypes.Time


class current_timestamp(AnsiFunction):
    type = sqltypes.DateTime


class current_user(AnsiFunction):
    type = sqltypes.String


class localtime(AnsiFunction):
    type = sqltypes.DateTime


class localtimestamp(AnsiFunction):
    type = sqltypes.DateTime


class session_user(AnsiFunction):
    type = sqltypes.String


class sysdate(AnsiFunction):
    type = sqltypes.DateTime


class user(AnsiFunction):
    type = sqltypes.String
