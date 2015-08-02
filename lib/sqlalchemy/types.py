# sqlalchemy/types.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""defines genericized SQL types, each represented by a subclass of
:class:`~sqlalchemy.types.AbstractType`.  Dialects define further subclasses
of these types.

For more information see the SQLAlchemy documentation on types.

"""
__all__ = ['TypeEngine', 'TypeDecorator', 'AbstractType', 'UserDefinedType',
            'INT', 'CHAR', 'VARCHAR', 'NCHAR', 'NVARCHAR', 'TEXT', 'Text',
            'FLOAT', 'NUMERIC', 'REAL', 'DECIMAL', 'TIMESTAMP', 'DATETIME',
            'CLOB', 'BLOB', 'BINARY', 'VARBINARY', 'BOOLEAN', 'BIGINT',
            'SMALLINT', 'INTEGER', 'DATE', 'TIME', 'String', 'Integer',
            'SmallInteger', 'BigInteger', 'Numeric', 'Float', 'DateTime',
            'Date', 'Time', 'LargeBinary', 'Binary', 'Boolean', 'Unicode',
            'Concatenable', 'UnicodeText', 'PickleType', 'Interval', 'Enum']

import datetime as dt
import codecs

from . import exc, schema, util, processors, events, event
from .sql import operators, type_coerce
from .sql.expression import _DefaultColumnComparator
from .util import pickle
from .sql.visitors import Visitable
import decimal
default = util.importlater("sqlalchemy.engine", "default")

NoneType = type(None)
if util.jython:
    import array


class AbstractType(Visitable):
    """Base for all types - not needed except for backwards
    compatibility."""


class TypeEngine(AbstractType):
    """Base for built-in types."""

    class Comparator(_DefaultColumnComparator):
        """Base class for custom comparison operations defined at the
        type level.  See :attr:`.TypeEngine.comparator_factory`.

        The public base class for :class:`.TypeEngine.Comparator`
        is :class:`.ColumnOperators`.

        """

        def __init__(self, expr):
            self.expr = expr

        def __reduce__(self):
            return _reconstitute_comparator, (self.expr, )

    hashable = True
    """Flag, if False, means values from this type aren't hashable.

    Used by the ORM when uniquing result lists.

    """

    comparator_factory = Comparator
    """A :class:`.TypeEngine.Comparator` class which will apply
    to operations performed by owning :class:`.ColumnElement` objects.

    The :attr:`.comparator_factory` attribute is a hook consulted by
    the core expression system when column and SQL expression operations
    are performed.   When a :class:`.TypeEngine.Comparator` class is
    associated with this attribute, it allows custom re-definition of
    all existing operators, as well as definition of new operators.
    Existing operators include those provided by Python operator overloading
    such as :meth:`.operators.ColumnOperators.__add__` and
    :meth:`.operators.ColumnOperators.__eq__`,
    those provided as standard
    attributes of :class:`.operators.ColumnOperators` such as
    :meth:`.operators.ColumnOperators.like`
    and :meth:`.operators.ColumnOperators.in_`.

    Rudimentary usage of this hook is allowed through simple subclassing
    of existing types, or alternatively by using :class:`.TypeDecorator`.
    See the documentation section :ref:`types_operators` for examples.

    .. versionadded:: 0.8  The expression system was enhanced to support
      customization of operators on a per-type level.

    """

    def copy_value(self, value):
        return value

    def bind_processor(self, dialect):
        """Return a conversion function for processing bind values.

        Returns a callable which will receive a bind parameter value
        as the sole positional argument and will return a value to
        send to the DB-API.

        If processing is not necessary, the method should return ``None``.

        :param dialect: Dialect instance in use.

        """
        return None

    def result_processor(self, dialect, coltype):
        """Return a conversion function for processing result row values.

        Returns a callable which will receive a result row column
        value as the sole positional argument and will return a value
        to return to the user.

        If processing is not necessary, the method should return ``None``.

        :param dialect: Dialect instance in use.

        :param coltype: DBAPI coltype argument received in cursor.description.

        """
        return None

    def column_expression(self, colexpr):
        """Given a SELECT column expression, return a wrapping SQL expression.

        This is typically a SQL function that wraps a column expression
        as rendered in the columns clause of a SELECT statement.
        It is used for special data types that require
        columns to be wrapped in some special database function in order
        to coerce the value before being sent back to the application.
        It is the SQL analogue of the :meth:`.TypeEngine.result_processor`
        method.

        The method is evaluated at statement compile time, as opposed
        to statement construction time.

        See also:

        :ref:`types_sql_value_processing`

        """

        return None

    @util.memoized_property
    def _has_column_expression(self):
        """memoized boolean, check if column_expression is implemented.

        Allows the method to be skipped for the vast majority of expression
        types that don't use this feature.

        """

        return self.__class__.column_expression.func_code \
            is not TypeEngine.column_expression.func_code

    def bind_expression(self, bindvalue):
        """"Given a bind value (i.e. a :class:`.BindParameter` instance),
        return a SQL expression in its place.

        This is typically a SQL function that wraps the existing bound
        parameter within the statement.  It is used for special data types
        that require literals being wrapped in some special database function
        in order to coerce an application-level value into a database-specific
        format.  It is the SQL analogue of the
        :meth:`.TypeEngine.bind_processor` method.

        The method is evaluated at statement compile time, as opposed
        to statement construction time.

        Note that this method, when implemented, should always return
        the exact same structure, without any conditional logic, as it
        may be used in an executemany() call against an arbitrary number
        of bound parameter sets.

        See also:

        :ref:`types_sql_value_processing`

        """
        return None

    @util.memoized_property
    def _has_bind_expression(self):
        """memoized boolean, check if bind_expression is implemented.

        Allows the method to be skipped for the vast majority of expression
        types that don't use this feature.

        """

        return self.__class__.bind_expression.func_code \
            is not TypeEngine.bind_expression.func_code

    def compare_values(self, x, y):
        """Compare two values for equality."""

        return x == y

    def get_dbapi_type(self, dbapi):
        """Return the corresponding type object from the underlying DB-API, if
        any.

         This can be useful for calling ``setinputsizes()``, for example.

        """
        return None

    @property
    def python_type(self):
        """Return the Python type object expected to be returned
        by instances of this type, if known.

        Basically, for those types which enforce a return type,
        or are known across the board to do such for all common
        DBAPIs (like ``int`` for example), will return that type.

        If a return type is not defined, raises
        ``NotImplementedError``.

        Note that any type also accommodates NULL in SQL which
        means you can also get back ``None`` from any type
        in practice.

        """
        raise NotImplementedError()

    def with_variant(self, type_, dialect_name):
        """Produce a new type object that will utilize the given
        type when applied to the dialect of the given name.

        e.g.::

            from sqlalchemy.types import String
            from sqlalchemy.dialects import mysql

            s = String()

            s = s.with_variant(mysql.VARCHAR(collation='foo'), 'mysql')

        The construction of :meth:`.TypeEngine.with_variant` is always
        from the "fallback" type to that which is dialect specific.
        The returned type is an instance of :class:`.Variant`, which
        itself provides a :meth:`~sqlalchemy.types.Variant.with_variant`
        that can be called repeatedly.

        :param type_: a :class:`.TypeEngine` that will be selected
         as a variant from the originating type, when a dialect
         of the given name is in use.
        :param dialect_name: base name of the dialect which uses
         this type. (i.e. ``'postgresql'``, ``'mysql'``, etc.)

        .. versionadded:: 0.7.2

        """
        return Variant(self, {dialect_name: type_})

    @util.memoized_property
    def _type_affinity(self):
        """Return a rudimental 'affinity' value expressing the general class
        of type."""

        typ = None
        for t in self.__class__.__mro__:
            if t is TypeEngine or t is UserDefinedType:
                return typ
            elif issubclass(t, TypeEngine):
                typ = t
        else:
            return self.__class__

    def dialect_impl(self, dialect):
        """Return a dialect-specific implementation for this
        :class:`.TypeEngine`.

        """
        try:
            return dialect._type_memos[self]['impl']
        except KeyError:
            return self._dialect_info(dialect)['impl']

    def _cached_bind_processor(self, dialect):
        """Return a dialect-specific bind processor for this type."""

        try:
            return dialect._type_memos[self]['bind']
        except KeyError:
            d = self._dialect_info(dialect)
            d['bind'] = bp = d['impl'].bind_processor(dialect)
            return bp

    def _cached_result_processor(self, dialect, coltype):
        """Return a dialect-specific result processor for this type."""

        try:
            return dialect._type_memos[self][coltype]
        except KeyError:
            d = self._dialect_info(dialect)
            # key assumption: DBAPI type codes are
            # constants.  Else this dictionary would
            # grow unbounded.
            d[coltype] = rp = d['impl'].result_processor(dialect, coltype)
            return rp

    def _dialect_info(self, dialect):
        """Return a dialect-specific registry which
        caches a dialect-specific implementation, bind processing
        function, and one or more result processing functions."""

        if self in dialect._type_memos:
            return dialect._type_memos[self]
        else:
            impl = self._gen_dialect_impl(dialect)
            if impl is self:
                impl = self.adapt(type(self))
            # this can't be self, else we create a cycle
            assert impl is not self
            dialect._type_memos[self] = d = {'impl': impl}
            return d

    def _gen_dialect_impl(self, dialect):
        return dialect.type_descriptor(self)

    def adapt(self, cls, **kw):
        """Produce an "adapted" form of this type, given an "impl" class
        to work with.

        This method is used internally to associate generic
        types with "implementation" types that are specific to a particular
        dialect.
        """
        return util.constructor_copy(self, cls, **kw)

    def coerce_compared_value(self, op, value):
        """Suggest a type for a 'coerced' Python value in an expression.

        Given an operator and value, gives the type a chance
        to return a type which the value should be coerced into.

        The default behavior here is conservative; if the right-hand
        side is already coerced into a SQL type based on its
        Python type, it is usually left alone.

        End-user functionality extension here should generally be via
        :class:`.TypeDecorator`, which provides more liberal behavior in that
        it defaults to coercing the other side of the expression into this
        type, thus applying special Python conversions above and beyond those
        needed by the DBAPI to both ides. It also provides the public method
        :meth:`.TypeDecorator.coerce_compared_value` which is intended for
        end-user customization of this behavior.

        """
        _coerced_type = _type_map.get(type(value), NULLTYPE)
        if _coerced_type is NULLTYPE or _coerced_type._type_affinity \
            is self._type_affinity:
            return self
        else:
            return _coerced_type

    def _compare_type_affinity(self, other):
        return self._type_affinity is other._type_affinity

    def compile(self, dialect=None):
        """Produce a string-compiled form of this :class:`.TypeEngine`.

        When called with no arguments, uses a "default" dialect
        to produce a string result.

        :param dialect: a :class:`.Dialect` instance.

        """
        # arg, return value is inconsistent with
        # ClauseElement.compile()....this is a mistake.

        if not dialect:
            dialect = self._default_dialect

        return dialect.type_compiler.process(self)

    @property
    def _default_dialect(self):
        if self.__class__.__module__.startswith("sqlalchemy.dialects"):
            tokens = self.__class__.__module__.split(".")[0:3]
            mod = ".".join(tokens)
            return getattr(__import__(mod).dialects, tokens[-1]).dialect()
        else:
            return default.DefaultDialect()

    def __str__(self):
        # Py3K
        #return unicode(self.compile())
        # Py2K
        return unicode(self.compile()).\
                        encode('ascii', 'backslashreplace')
        # end Py2K

    def __init__(self, *args, **kwargs):
        """Support implementations that were passing arguments"""
        if args or kwargs:
            util.warn_deprecated("Passing arguments to type object "
                    "constructor %s is deprecated" % self.__class__)

    def __repr__(self):
        return util.generic_repr(self)


def _reconstitute_comparator(expression):
    return expression.comparator


class UserDefinedType(TypeEngine):
    """Base for user defined types.

    This should be the base of new types.  Note that
    for most cases, :class:`.TypeDecorator` is probably
    more appropriate::

      import sqlalchemy.types as types

      class MyType(types.UserDefinedType):
          def __init__(self, precision = 8):
              self.precision = precision

          def get_col_spec(self):
              return "MYTYPE(%s)" % self.precision

          def bind_processor(self, dialect):
              def process(value):
                  return value
              return process

          def result_processor(self, dialect, coltype):
              def process(value):
                  return value
              return process

    Once the type is made, it's immediately usable::

      table = Table('foo', meta,
          Column('id', Integer, primary_key=True),
          Column('data', MyType(16))
          )

    """
    __visit_name__ = "user_defined"

    class Comparator(TypeEngine.Comparator):
        def _adapt_expression(self, op, other_comparator):
            if hasattr(self.type, 'adapt_operator'):
                util.warn_deprecated(
                    "UserDefinedType.adapt_operator is deprecated.  Create "
                     "a UserDefinedType.Comparator subclass instead which "
                     "generates the desired expression constructs, given a "
                     "particular operator."
                    )
                return self.type.adapt_operator(op), self.type
            else:
                return op, self.type

    comparator_factory = Comparator

    def coerce_compared_value(self, op, value):
        """Suggest a type for a 'coerced' Python value in an expression.

        Default behavior for :class:`.UserDefinedType` is the
        same as that of :class:`.TypeDecorator`; by default it returns
        ``self``, assuming the compared value should be coerced into
        the same type as this one.  See
        :meth:`.TypeDecorator.coerce_compared_value` for more detail.

        .. versionchanged:: 0.8 :meth:`.UserDefinedType.coerce_compared_value`
           now returns ``self`` by default, rather than falling onto the
           more fundamental behavior of
           :meth:`.TypeEngine.coerce_compared_value`.

        """

        return self


class TypeDecorator(TypeEngine):
    """Allows the creation of types which add additional functionality
    to an existing type.

    This method is preferred to direct subclassing of SQLAlchemy's
    built-in types as it ensures that all required functionality of
    the underlying type is kept in place.

    Typical usage::

      import sqlalchemy.types as types

      class MyType(types.TypeDecorator):
          '''Prefixes Unicode values with "PREFIX:" on the way in and
          strips it off on the way out.
          '''

          impl = types.Unicode

          def process_bind_param(self, value, dialect):
              return "PREFIX:" + value

          def process_result_value(self, value, dialect):
              return value[7:]

          def copy(self):
              return MyType(self.impl.length)

    The class-level "impl" attribute is required, and can reference any
    TypeEngine class.  Alternatively, the load_dialect_impl() method
    can be used to provide different type classes based on the dialect
    given; in this case, the "impl" variable can reference
    ``TypeEngine`` as a placeholder.

    Types that receive a Python type that isn't similar to the ultimate type
    used may want to define the :meth:`TypeDecorator.coerce_compared_value`
    method. This is used to give the expression system a hint when coercing
    Python objects into bind parameters within expressions. Consider this
    expression::

        mytable.c.somecol + datetime.date(2009, 5, 15)

    Above, if "somecol" is an ``Integer`` variant, it makes sense that
    we're doing date arithmetic, where above is usually interpreted
    by databases as adding a number of days to the given date.
    The expression system does the right thing by not attempting to
    coerce the "date()" value into an integer-oriented bind parameter.

    However, in the case of ``TypeDecorator``, we are usually changing an
    incoming Python type to something new - ``TypeDecorator`` by default will
    "coerce" the non-typed side to be the same type as itself. Such as below,
    we define an "epoch" type that stores a date value as an integer::

        class MyEpochType(types.TypeDecorator):
            impl = types.Integer

            epoch = datetime.date(1970, 1, 1)

            def process_bind_param(self, value, dialect):
                return (value - self.epoch).days

            def process_result_value(self, value, dialect):
                return self.epoch + timedelta(days=value)

    Our expression of ``somecol + date`` with the above type will coerce the
    "date" on the right side to also be treated as ``MyEpochType``.

    This behavior can be overridden via the
    :meth:`~TypeDecorator.coerce_compared_value` method, which returns a type
    that should be used for the value of the expression. Below we set it such
    that an integer value will be treated as an ``Integer``, and any other
    value is assumed to be a date and will be treated as a ``MyEpochType``::

        def coerce_compared_value(self, op, value):
            if isinstance(value, int):
                return Integer()
            else:
                return self

    """

    __visit_name__ = "type_decorator"

    def __init__(self, *args, **kwargs):
        """Construct a :class:`.TypeDecorator`.

        Arguments sent here are passed to the constructor
        of the class assigned to the ``impl`` class level attribute,
        assuming the ``impl`` is a callable, and the resulting
        object is assigned to the ``self.impl`` instance attribute
        (thus overriding the class attribute of the same name).

        If the class level ``impl`` is not a callable (the unusual case),
        it will be assigned to the same instance attribute 'as-is',
        ignoring those arguments passed to the constructor.

        Subclasses can override this to customize the generation
        of ``self.impl`` entirely.

        """

        if not hasattr(self.__class__, 'impl'):
            raise AssertionError("TypeDecorator implementations "
                                 "require a class-level variable "
                                 "'impl' which refers to the class of "
                                 "type being decorated")
        self.impl = to_instance(self.__class__.impl, *args, **kwargs)

    coerce_to_is_types = (util.NoneType, )
    """Specify those Python types which should be coerced at the expression
    level to "IS <constant>" when compared using ``==`` (and same for
        ``IS NOT`` in conjunction with ``!=``.

    For most SQLAlchemy types, this includes ``NoneType``, as well as ``bool``.

    :class:`.TypeDecorator` modifies this list to only include ``NoneType``,
    as typedecorator implementations that deal with boolean types are common.

    Custom :class:`.TypeDecorator` classes can override this attribute to
    return an empty tuple, in which case no values will be coerced to
    constants.

    ..versionadded:: 0.8.2
        Added :attr:`.TypeDecorator.coerce_to_is_types` to allow for easier
        control of ``__eq__()`` ``__ne__()`` operations.

    """

    class Comparator(TypeEngine.Comparator):
        def operate(self, op, *other, **kwargs):
            kwargs['_python_is_types'] = self.expr.type.coerce_to_is_types
            return super(TypeDecorator.Comparator, self).operate(
                                                        op, *other, **kwargs)

        def reverse_operate(self, op, other, **kwargs):
            kwargs['_python_is_types'] = self.expr.type.coerce_to_is_types
            return super(TypeDecorator.Comparator, self).reverse_operate(
                                                        op, other, **kwargs)

    @property
    def comparator_factory(self):
        return type("TDComparator",
                    (TypeDecorator.Comparator, self.impl.comparator_factory),
                    {})

    def _gen_dialect_impl(self, dialect):
        """
        #todo
        """
        adapted = dialect.type_descriptor(self)
        if adapted is not self:
            return adapted

        # otherwise adapt the impl type, link
        # to a copy of this TypeDecorator and return
        # that.
        typedesc = self.load_dialect_impl(dialect).dialect_impl(dialect)
        tt = self.copy()
        if not isinstance(tt, self.__class__):
            raise AssertionError('Type object %s does not properly '
                                 'implement the copy() method, it must '
                                 'return an object of type %s' % (self,
                                 self.__class__))
        tt.impl = typedesc
        return tt

    @property
    def _type_affinity(self):
        """
        #todo
        """
        return self.impl._type_affinity

    def type_engine(self, dialect):
        """Return a dialect-specific :class:`.TypeEngine` instance
        for this :class:`.TypeDecorator`.

        In most cases this returns a dialect-adapted form of
        the :class:`.TypeEngine` type represented by ``self.impl``.
        Makes usage of :meth:`dialect_impl` but also traverses
        into wrapped :class:`.TypeDecorator` instances.
        Behavior can be customized here by overriding
        :meth:`load_dialect_impl`.

        """
        adapted = dialect.type_descriptor(self)
        if type(adapted) is not type(self):
            return adapted
        elif isinstance(self.impl, TypeDecorator):
            return self.impl.type_engine(dialect)
        else:
            return self.load_dialect_impl(dialect)

    def load_dialect_impl(self, dialect):
        """Return a :class:`.TypeEngine` object corresponding to a dialect.

        This is an end-user override hook that can be used to provide
        differing types depending on the given dialect.  It is used
        by the :class:`.TypeDecorator` implementation of :meth:`type_engine`
        to help determine what type should ultimately be returned
        for a given :class:`.TypeDecorator`.

        By default returns ``self.impl``.

        """
        return self.impl

    def __getattr__(self, key):
        """Proxy all other undefined accessors to the underlying
        implementation."""
        return getattr(self.impl, key)

    def process_bind_param(self, value, dialect):
        """Receive a bound parameter value to be converted.

        Subclasses override this method to return the
        value that should be passed along to the underlying
        :class:`.TypeEngine` object, and from there to the
        DBAPI ``execute()`` method.

        The operation could be anything desired to perform custom
        behavior, such as transforming or serializing data.
        This could also be used as a hook for validating logic.

        This operation should be designed with the reverse operation
        in mind, which would be the process_result_value method of
        this class.

        :param value: Data to operate upon, of any type expected by
         this method in the subclass.  Can be ``None``.
        :param dialect: the :class:`.Dialect` in use.

        """

        raise NotImplementedError()

    def process_result_value(self, value, dialect):
        """Receive a result-row column value to be converted.

        Subclasses should implement this method to operate on data
        fetched from the database.

        Subclasses override this method to return the
        value that should be passed back to the application,
        given a value that is already processed by
        the underlying :class:`.TypeEngine` object, originally
        from the DBAPI cursor method ``fetchone()`` or similar.

        The operation could be anything desired to perform custom
        behavior, such as transforming or serializing data.
        This could also be used as a hook for validating logic.

        :param value: Data to operate upon, of any type expected by
         this method in the subclass.  Can be ``None``.
        :param dialect: the :class:`.Dialect` in use.

        This operation should be designed to be reversible by
        the "process_bind_param" method of this class.

        """

        raise NotImplementedError()

    @util.memoized_property
    def _has_bind_processor(self):
        """memoized boolean, check if process_bind_param is implemented.

        Allows the base process_bind_param to raise
        NotImplementedError without needing to test an expensive
        exception throw.

        """

        return self.__class__.process_bind_param.func_code \
            is not TypeDecorator.process_bind_param.func_code

    def bind_processor(self, dialect):
        """Provide a bound value processing function for the
        given :class:`.Dialect`.

        This is the method that fulfills the :class:`.TypeEngine`
        contract for bound value conversion.   :class:`.TypeDecorator`
        will wrap a user-defined implementation of
        :meth:`process_bind_param` here.

        User-defined code can override this method directly,
        though its likely best to use :meth:`process_bind_param` so that
        the processing provided by ``self.impl`` is maintained.

        :param dialect: Dialect instance in use.

        This method is the reverse counterpart to the
        :meth:`result_processor` method of this class.

        """
        if self._has_bind_processor:
            process_param = self.process_bind_param
            impl_processor = self.impl.bind_processor(dialect)
            if impl_processor:
                def process(value):
                    return impl_processor(process_param(value, dialect))

            else:
                def process(value):
                    return process_param(value, dialect)

            return process
        else:
            return self.impl.bind_processor(dialect)

    @util.memoized_property
    def _has_result_processor(self):
        """memoized boolean, check if process_result_value is implemented.

        Allows the base process_result_value to raise
        NotImplementedError without needing to test an expensive
        exception throw.

        """
        return self.__class__.process_result_value.func_code \
            is not TypeDecorator.process_result_value.func_code

    def result_processor(self, dialect, coltype):
        """Provide a result value processing function for the given
        :class:`.Dialect`.

        This is the method that fulfills the :class:`.TypeEngine`
        contract for result value conversion.   :class:`.TypeDecorator`
        will wrap a user-defined implementation of
        :meth:`process_result_value` here.

        User-defined code can override this method directly,
        though its likely best to use :meth:`process_result_value` so that
        the processing provided by ``self.impl`` is maintained.

        :param dialect: Dialect instance in use.
        :param coltype: An SQLAlchemy data type

        This method is the reverse counterpart to the
        :meth:`bind_processor` method of this class.

        """
        if self._has_result_processor:
            process_value = self.process_result_value
            impl_processor = self.impl.result_processor(dialect,
                    coltype)
            if impl_processor:
                def process(value):
                    return process_value(impl_processor(value), dialect)

            else:
                def process(value):
                    return process_value(value, dialect)

            return process
        else:
            return self.impl.result_processor(dialect, coltype)

    def coerce_compared_value(self, op, value):
        """Suggest a type for a 'coerced' Python value in an expression.

        By default, returns self.   This method is called by
        the expression system when an object using this type is
        on the left or right side of an expression against a plain Python
        object which does not yet have a SQLAlchemy type assigned::

            expr = table.c.somecolumn + 35

        Where above, if ``somecolumn`` uses this type, this method will
        be called with the value ``operator.add``
        and ``35``.  The return value is whatever SQLAlchemy type should
        be used for ``35`` for this particular operation.

        """
        return self

    def copy(self):
        """Produce a copy of this :class:`.TypeDecorator` instance.

        This is a shallow copy and is provided to fulfill part of
        the :class:`.TypeEngine` contract.  It usually does not
        need to be overridden unless the user-defined :class:`.TypeDecorator`
        has local state that should be deep-copied.

        """

        instance = self.__class__.__new__(self.__class__)
        instance.__dict__.update(self.__dict__)
        return instance

    def get_dbapi_type(self, dbapi):
        """Return the DBAPI type object represented by this
        :class:`.TypeDecorator`.

        By default this calls upon :meth:`.TypeEngine.get_dbapi_type` of the
        underlying "impl".
        """
        return self.impl.get_dbapi_type(dbapi)

    def compare_values(self, x, y):
        """Given two values, compare them for equality.

        By default this calls upon :meth:`.TypeEngine.compare_values`
        of the underlying "impl", which in turn usually
        uses the Python equals operator ``==``.

        This function is used by the ORM to compare
        an original-loaded value with an intercepted
        "changed" value, to determine if a net change
        has occurred.

        """
        return self.impl.compare_values(x, y)

    def __repr__(self):
        return util.generic_repr(self, to_inspect=self.impl)


class Variant(TypeDecorator):
    """A wrapping type that selects among a variety of
    implementations based on dialect in use.

    The :class:`.Variant` type is typically constructed
    using the :meth:`.TypeEngine.with_variant` method.

    .. versionadded:: 0.7.2

    """

    def __init__(self, base, mapping):
        """Construct a new :class:`.Variant`.

        :param base: the base 'fallback' type
        :param mapping: dictionary of string dialect names to
          :class:`.TypeEngine` instances.

        """
        self.impl = base
        self.mapping = mapping

    def load_dialect_impl(self, dialect):
        if dialect.name in self.mapping:
            return self.mapping[dialect.name]
        else:
            return self.impl

    def with_variant(self, type_, dialect_name):
        """Return a new :class:`.Variant` which adds the given
        type + dialect name to the mapping, in addition to the
        mapping present in this :class:`.Variant`.

        :param type_: a :class:`.TypeEngine` that will be selected
         as a variant from the originating type, when a dialect
         of the given name is in use.
        :param dialect_name: base name of the dialect which uses
         this type. (i.e. ``'postgresql'``, ``'mysql'``, etc.)

        """

        if dialect_name in self.mapping:
            raise exc.ArgumentError(
                "Dialect '%s' is already present in "
                "the mapping for this Variant" % dialect_name)
        mapping = self.mapping.copy()
        mapping[dialect_name] = type_
        return Variant(self.impl, mapping)


def to_instance(typeobj, *arg, **kw):
    if typeobj is None:
        return NULLTYPE

    if util.callable(typeobj):
        return typeobj(*arg, **kw)
    else:
        return typeobj


def adapt_type(typeobj, colspecs):
    if isinstance(typeobj, type):
        typeobj = typeobj()
    for t in typeobj.__class__.__mro__[0:-1]:
        try:
            impltype = colspecs[t]
            break
        except KeyError:
            pass
    else:
        # couldnt adapt - so just return the type itself
        # (it may be a user-defined type)
        return typeobj
    # if we adapted the given generic type to a database-specific type,
    # but it turns out the originally given "generic" type
    # is actually a subclass of our resulting type, then we were already
    # given a more specific type than that required; so use that.
    if (issubclass(typeobj.__class__, impltype)):
        return typeobj
    return typeobj.adapt(impltype)


class NullType(TypeEngine):
    """An unknown type.

    NullTypes will stand in if :class:`~sqlalchemy.Table` reflection
    encounters a column data type unknown to SQLAlchemy.  The
    resulting columns are nearly fully usable: the DB-API adapter will
    handle all translation to and from the database data type.

    NullType does not have sufficient information to particpate in a
    ``CREATE TABLE`` statement and will raise an exception if
    encountered during a :meth:`~sqlalchemy.Table.create` operation.

    """
    __visit_name__ = 'null'

    class Comparator(TypeEngine.Comparator):
        def _adapt_expression(self, op, other_comparator):
            if isinstance(other_comparator, NullType.Comparator) or \
                not operators.is_commutative(op):
                return op, self.expr.type
            else:
                return other_comparator._adapt_expression(op, self)
    comparator_factory = Comparator

NullTypeEngine = NullType


class Concatenable(object):
    """A mixin that marks a type as supporting 'concatenation',
    typically strings."""

    class Comparator(TypeEngine.Comparator):
        def _adapt_expression(self, op, other_comparator):
            if op is operators.add and isinstance(other_comparator,
                    (Concatenable.Comparator, NullType.Comparator)):
                return operators.concat_op, self.expr.type
            else:
                return op, self.expr.type

    comparator_factory = Comparator


class _DateAffinity(object):
    """Mixin date/time specific expression adaptations.

    Rules are implemented within Date,Time,Interval,DateTime, Numeric,
    Integer. Based on http://www.postgresql.org/docs/current/static
    /functions-datetime.html.

    """

    @property
    def _expression_adaptations(self):
        raise NotImplementedError()

    class Comparator(TypeEngine.Comparator):
        _blank_dict = util.immutabledict()

        def _adapt_expression(self, op, other_comparator):
            othertype = other_comparator.type._type_affinity
            return op, \
                    self.type._expression_adaptations.get(op, self._blank_dict).\
                    get(othertype, NULLTYPE)
    comparator_factory = Comparator


class String(Concatenable, TypeEngine):
    """The base for all string and character types.

    In SQL, corresponds to VARCHAR.  Can also take Python unicode objects
    and encode to the database's encoding in bind params (and the reverse for
    result sets.)

    The `length` field is usually required when the `String` type is
    used within a CREATE TABLE statement, as VARCHAR requires a length
    on most databases.

    """

    __visit_name__ = 'string'

    def __init__(self, length=None, collation=None,
                        convert_unicode=False,
                        unicode_error=None,
                        _warn_on_bytestring=False
                        ):
        """
        Create a string-holding type.

        :param length: optional, a length for the column for use in
          DDL and CAST expressions.  May be safely omitted if no ``CREATE
          TABLE`` will be issued.  Certain databases may require a
          ``length`` for use in DDL, and will raise an exception when
          the ``CREATE TABLE`` DDL is issued if a ``VARCHAR``
          with no length is included.  Whether the value is
          interpreted as bytes or characters is database specific.

        :param collation: Optional, a column-level collation for
          use in DDL and CAST expressions.  Renders using the
          COLLATE keyword supported by SQLite, MySQL, and Postgresql.
          E.g.::

            >>> from sqlalchemy import cast, select, String
            >>> print select([cast('some string', String(collation='utf8'))])
            SELECT CAST(:param_1 AS VARCHAR COLLATE utf8) AS anon_1

          .. versionadded:: 0.8 Added support for COLLATE to all
             string types.

        :param convert_unicode: When set to ``True``, the
          :class:`.String` type will assume that
          input is to be passed as Python ``unicode`` objects,
          and results returned as Python ``unicode`` objects.
          If the DBAPI in use does not support Python unicode
          (which is fewer and fewer these days), SQLAlchemy
          will encode/decode the value, using the
          value of the ``encoding`` parameter passed to
          :func:`.create_engine` as the encoding.

          When using a DBAPI that natively supports Python
          unicode objects, this flag generally does not
          need to be set.  For columns that are explicitly
          intended to store non-ASCII data, the :class:`.Unicode`
          or :class:`UnicodeText`
          types should be used regardless, which feature
          the same behavior of ``convert_unicode`` but
          also indicate an underlying column type that
          directly supports unicode, such as ``NVARCHAR``.

          For the extremely rare case that Python ``unicode``
          is to be encoded/decoded by SQLAlchemy on a backend
          that does natively support Python ``unicode``,
          the value ``force`` can be passed here which will
          cause SQLAlchemy's encode/decode services to be
          used unconditionally.

        :param unicode_error: Optional, a method to use to handle Unicode
          conversion errors. Behaves like the ``errors`` keyword argument to
          the standard library's ``string.decode()`` functions.   This flag
          requires that ``convert_unicode`` is set to ``force`` - otherwise,
          SQLAlchemy is not guaranteed to handle the task of unicode
          conversion.   Note that this flag adds significant performance
          overhead to row-fetching operations for backends that already
          return unicode objects natively (which most DBAPIs do).  This
          flag should only be used as a last resort for reading
          strings from a column with varied or corrupted encodings.

        """
        if unicode_error is not None and convert_unicode != 'force':
            raise exc.ArgumentError("convert_unicode must be 'force' "
                                        "when unicode_error is set.")

        self.length = length
        self.collation = collation
        self.convert_unicode = convert_unicode
        self.unicode_error = unicode_error
        self._warn_on_bytestring = _warn_on_bytestring

    def bind_processor(self, dialect):
        if self.convert_unicode or dialect.convert_unicode:
            if dialect.supports_unicode_binds and \
                self.convert_unicode != 'force':
                if self._warn_on_bytestring:
                    def process(value):
                        # Py3K
                        #if isinstance(value, bytes):
                        # Py2K
                        if isinstance(value, str):
                        # end Py2K
                            util.warn("Unicode type received non-unicode bind "
                                      "param value.")
                        return value
                    return process
                else:
                    return None
            else:
                encoder = codecs.getencoder(dialect.encoding)
                warn_on_bytestring = self._warn_on_bytestring

                def process(value):
                    if isinstance(value, unicode):
                        return encoder(value, self.unicode_error)[0]
                    elif warn_on_bytestring and value is not None:
                        util.warn("Unicode type received non-unicode bind "
                                  "param value")
                    return value
            return process
        else:
            return None

    def result_processor(self, dialect, coltype):
        wants_unicode = self.convert_unicode or dialect.convert_unicode
        needs_convert = wants_unicode and \
                        (dialect.returns_unicode_strings is not True or
                        self.convert_unicode == 'force')

        if needs_convert:
            to_unicode = processors.to_unicode_processor_factory(
                                    dialect.encoding, self.unicode_error)

            if dialect.returns_unicode_strings:
                # we wouldn't be here unless convert_unicode='force'
                # was specified, or the driver has erratic unicode-returning
                # habits.  since we will be getting back unicode
                # in most cases, we check for it (decode will fail).
                def process(value):
                    if isinstance(value, unicode):
                        return value
                    else:
                        return to_unicode(value)
                return process
            else:
                # here, we assume that the object is not unicode,
                # avoiding expensive isinstance() check.
                return to_unicode
        else:
            return None

    @property
    def python_type(self):
        if self.convert_unicode:
            return unicode
        else:
            return str

    def get_dbapi_type(self, dbapi):
        return dbapi.STRING


class Text(String):
    """A variably sized string type.

    In SQL, usually corresponds to CLOB or TEXT. Can also take Python
    unicode objects and encode to the database's encoding in bind
    params (and the reverse for result sets.)  In general, TEXT objects
    do not have a length; while some databases will accept a length
    argument here, it will be rejected by others.

    """
    __visit_name__ = 'text'


class Unicode(String):
    """A variable length Unicode string type.

    The :class:`.Unicode` type is a :class:`.String` subclass
    that assumes input and output as Python ``unicode`` data,
    and in that regard is equivalent to the usage of the
    ``convert_unicode`` flag with the :class:`.String` type.
    However, unlike plain :class:`.String`, it also implies an
    underlying column type that is explicitly supporting of non-ASCII
    data, such as ``NVARCHAR`` on Oracle and SQL Server.
    This can impact the output of ``CREATE TABLE`` statements
    and ``CAST`` functions at the dialect level, and can
    also affect the handling of bound parameters in some
    specific DBAPI scenarios.

    The encoding used by the :class:`.Unicode` type is usually
    determined by the DBAPI itself; most modern DBAPIs
    feature support for Python ``unicode`` objects as bound
    values and result set values, and the encoding should
    be configured as detailed in the notes for the target
    DBAPI in the :ref:`dialect_toplevel` section.

    For those DBAPIs which do not support, or are not configured
    to accommodate Python ``unicode`` objects
    directly, SQLAlchemy does the encoding and decoding
    outside of the DBAPI.   The encoding in this scenario
    is determined by the ``encoding`` flag passed to
    :func:`.create_engine`.

    When using the :class:`.Unicode` type, it is only appropriate
    to pass Python ``unicode`` objects, and not plain ``str``.
    If a plain ``str`` is passed under Python 2, a warning
    is emitted.  If you notice your application emitting these warnings but
    you're not sure of the source of them, the Python
    ``warnings`` filter, documented at
    http://docs.python.org/library/warnings.html,
    can be used to turn these warnings into exceptions
    which will illustrate a stack trace::

      import warnings
      warnings.simplefilter('error')

    For an application that wishes to pass plain bytestrings
    and Python ``unicode`` objects to the ``Unicode`` type
    equally, the bytestrings must first be decoded into
    unicode.  The recipe at :ref:`coerce_to_unicode` illustrates
    how this is done.

    See also:

        :class:`.UnicodeText` - unlengthed textual counterpart
        to :class:`.Unicode`.

    """

    __visit_name__ = 'unicode'

    def __init__(self, length=None, **kwargs):
        """
        Create a :class:`.Unicode` object.

        Parameters are the same as that of :class:`.String`,
        with the exception that ``convert_unicode``
        defaults to ``True``.

        """
        kwargs.setdefault('convert_unicode', True)
        kwargs.setdefault('_warn_on_bytestring', True)
        super(Unicode, self).__init__(length=length, **kwargs)


class UnicodeText(Text):
    """An unbounded-length Unicode string type.

    See :class:`.Unicode` for details on the unicode
    behavior of this object.

    Like :class:`.Unicode`, usage the :class:`.UnicodeText` type implies a
    unicode-capable type being used on the backend, such as
    ``NCLOB``, ``NTEXT``.

    """

    __visit_name__ = 'unicode_text'

    def __init__(self, length=None, **kwargs):
        """
        Create a Unicode-converting Text type.

        Parameters are the same as that of :class:`.Text`,
        with the exception that ``convert_unicode``
        defaults to ``True``.

        """
        kwargs.setdefault('convert_unicode', True)
        kwargs.setdefault('_warn_on_bytestring', True)
        super(UnicodeText, self).__init__(length=length, **kwargs)


class Integer(_DateAffinity, TypeEngine):
    """A type for ``int`` integers."""

    __visit_name__ = 'integer'

    def get_dbapi_type(self, dbapi):
        return dbapi.NUMBER

    @property
    def python_type(self):
        return int

    @util.memoized_property
    def _expression_adaptations(self):
        # TODO: need a dictionary object that will
        # handle operators generically here, this is incomplete
        return {
            operators.add: {
                Date: Date,
                Integer: self.__class__,
                Numeric: Numeric,
            },
            operators.mul: {
                Interval: Interval,
                Integer: self.__class__,
                Numeric: Numeric,
            },
            # Py2K
            operators.div: {
                Integer: self.__class__,
                Numeric: Numeric,
            },
            # end Py2K
            operators.truediv: {
                Integer: self.__class__,
                Numeric: Numeric,
            },
            operators.sub: {
                Integer: self.__class__,
                Numeric: Numeric,
            },
        }


class SmallInteger(Integer):
    """A type for smaller ``int`` integers.

    Typically generates a ``SMALLINT`` in DDL, and otherwise acts like
    a normal :class:`.Integer` on the Python side.

    """

    __visit_name__ = 'small_integer'


class BigInteger(Integer):
    """A type for bigger ``int`` integers.

    Typically generates a ``BIGINT`` in DDL, and otherwise acts like
    a normal :class:`.Integer` on the Python side.

    """

    __visit_name__ = 'big_integer'


class Numeric(_DateAffinity, TypeEngine):
    """A type for fixed precision numbers.

    Typically generates DECIMAL or NUMERIC.  Returns
    ``decimal.Decimal`` objects by default, applying
    conversion as needed.

    .. note::

       The `cdecimal <http://pypi.python.org/pypi/cdecimal/>`_ library
       is a high performing alternative to Python's built-in
       ``decimal.Decimal`` type, which performs very poorly in high volume
       situations. SQLAlchemy 0.7 is tested against ``cdecimal`` and supports
       it fully. The type is not necessarily supported by DBAPI
       implementations however, most of which contain an import for plain
       ``decimal`` in their source code, even though some such as psycopg2
       provide hooks for alternate adapters. SQLAlchemy imports ``decimal``
       globally as well.  The most straightforward and
       foolproof way to use "cdecimal" given current DBAPI and Python support
       is to patch it directly into sys.modules before anything else is
       imported::

           import sys
           import cdecimal
           sys.modules["decimal"] = cdecimal

       While the global patch is a little ugly, it's particularly
       important to use just one decimal library at a time since
       Python Decimal and cdecimal Decimal objects
       are not currently compatible *with each other*::

           >>> import cdecimal
           >>> import decimal
           >>> decimal.Decimal("10") == cdecimal.Decimal("10")
           False

       SQLAlchemy will provide more natural support of
       cdecimal if and when it becomes a standard part of Python
       installations and is supported by all DBAPIs.

    """

    __visit_name__ = 'numeric'

    def __init__(self, precision=None, scale=None, asdecimal=True):
        """
        Construct a Numeric.

        :param precision: the numeric precision for use in DDL ``CREATE
          TABLE``.

        :param scale: the numeric scale for use in DDL ``CREATE TABLE``.

        :param asdecimal: default True.  Return whether or not
          values should be sent as Python Decimal objects, or
          as floats.   Different DBAPIs send one or the other based on
          datatypes - the Numeric type will ensure that return values
          are one or the other across DBAPIs consistently.

        When using the ``Numeric`` type, care should be taken to ensure
        that the asdecimal setting is apppropriate for the DBAPI in use -
        when Numeric applies a conversion from Decimal->float or float->
        Decimal, this conversion incurs an additional performance overhead
        for all result columns received.

        DBAPIs that return Decimal natively (e.g. psycopg2) will have
        better accuracy and higher performance with a setting of ``True``,
        as the native translation to Decimal reduces the amount of floating-
        point issues at play, and the Numeric type itself doesn't need
        to apply any further conversions.  However, another DBAPI which
        returns floats natively *will* incur an additional conversion
        overhead, and is still subject to floating point data loss - in
        which case ``asdecimal=False`` will at least remove the extra
        conversion overhead.

        """
        self.precision = precision
        self.scale = scale
        self.asdecimal = asdecimal

    def get_dbapi_type(self, dbapi):
        return dbapi.NUMBER

    @property
    def python_type(self):
        if self.asdecimal:
            return decimal.Decimal
        else:
            return float

    def bind_processor(self, dialect):
        if dialect.supports_native_decimal:
            return None
        else:
            return processors.to_float

    def result_processor(self, dialect, coltype):
        if self.asdecimal:
            if dialect.supports_native_decimal:
                # we're a "numeric", DBAPI will give us Decimal directly
                return None
            else:
                util.warn('Dialect %s+%s does *not* support Decimal '
                          'objects natively, and SQLAlchemy must '
                          'convert from floating point - rounding '
                          'errors and other issues may occur. Please '
                          'consider storing Decimal numbers as strings '
                          'or integers on this platform for lossless '
                          'storage.' % (dialect.name, dialect.driver))

                # we're a "numeric", DBAPI returns floats, convert.
                if self.scale is not None:
                    return processors.to_decimal_processor_factory(
                                decimal.Decimal, self.scale)
                else:
                    return processors.to_decimal_processor_factory(
                                decimal.Decimal)
        else:
            if dialect.supports_native_decimal:
                return processors.to_float
            else:
                return None

    @util.memoized_property
    def _expression_adaptations(self):
        return {
            operators.mul: {
                Interval: Interval,
                Numeric: self.__class__,
                Integer: self.__class__,
            },
            # Py2K
            operators.div: {
                Numeric: self.__class__,
                Integer: self.__class__,
            },
            # end Py2K
            operators.truediv: {
                Numeric: self.__class__,
                Integer: self.__class__,
            },
            operators.add: {
                Numeric: self.__class__,
                Integer: self.__class__,
            },
            operators.sub: {
                Numeric: self.__class__,
                Integer: self.__class__,
            }
        }


class Float(Numeric):
    """A type for ``float`` numbers.

    Returns Python ``float`` objects by default, applying
    conversion as needed.

    """

    __visit_name__ = 'float'

    scale = None

    def __init__(self, precision=None, asdecimal=False, **kwargs):
        """
        Construct a Float.

        :param precision: the numeric precision for use in DDL ``CREATE
           TABLE``.

        :param asdecimal: the same flag as that of :class:`.Numeric`, but
          defaults to ``False``.   Note that setting this flag to ``True``
          results in floating point conversion.

        :param \**kwargs: deprecated.  Additional arguments here are ignored
         by the default :class:`.Float` type.  For database specific
         floats that support additional arguments, see that dialect's
         documentation for details, such as
         :class:`sqlalchemy.dialects.mysql.FLOAT`.

        """
        self.precision = precision
        self.asdecimal = asdecimal
        if kwargs:
            util.warn_deprecated("Additional keyword arguments "
                                "passed to Float ignored.")

    def result_processor(self, dialect, coltype):
        if self.asdecimal:
            return processors.to_decimal_processor_factory(decimal.Decimal)
        else:
            return None

    @util.memoized_property
    def _expression_adaptations(self):
        return {
            operators.mul: {
                Interval: Interval,
                Numeric: self.__class__,
            },
            # Py2K
            operators.div: {
                Numeric: self.__class__,
            },
            # end Py2K
            operators.truediv: {
                Numeric: self.__class__,
            },
            operators.add: {
                Numeric: self.__class__,
            },
            operators.sub: {
                Numeric: self.__class__,
            }
        }


class DateTime(_DateAffinity, TypeEngine):
    """A type for ``datetime.datetime()`` objects.

    Date and time types return objects from the Python ``datetime``
    module.  Most DBAPIs have built in support for the datetime
    module, with the noted exception of SQLite.  In the case of
    SQLite, date and time types are stored as strings which are then
    converted back to datetime objects when rows are returned.

    """

    __visit_name__ = 'datetime'

    def __init__(self, timezone=False):
        """Construct a new :class:`.DateTime`.

        :param timezone: boolean.  If True, and supported by the
        backend, will produce 'TIMESTAMP WITH TIMEZONE'. For backends
        that don't support timezone aware timestamps, has no
        effect.

        """
        self.timezone = timezone

    def get_dbapi_type(self, dbapi):
        return dbapi.DATETIME

    @property
    def python_type(self):
        return dt.datetime

    @util.memoized_property
    def _expression_adaptations(self):
        return {
            operators.add: {
                Interval: self.__class__,
            },
            operators.sub: {
                Interval: self.__class__,
                DateTime: Interval,
            },
        }


class Date(_DateAffinity, TypeEngine):
    """A type for ``datetime.date()`` objects."""

    __visit_name__ = 'date'

    def get_dbapi_type(self, dbapi):
        return dbapi.DATETIME

    @property
    def python_type(self):
        return dt.date

    @util.memoized_property
    def _expression_adaptations(self):
        return {
            operators.add: {
                Integer: self.__class__,
                Interval: DateTime,
                Time: DateTime,
            },
            operators.sub: {
                # date - integer = date
                Integer: self.__class__,

                # date - date = integer.
                Date: Integer,

                Interval: DateTime,

                # date - datetime = interval,
                # this one is not in the PG docs
                # but works
                DateTime: Interval,
            },
        }


class Time(_DateAffinity, TypeEngine):
    """A type for ``datetime.time()`` objects."""

    __visit_name__ = 'time'

    def __init__(self, timezone=False):
        self.timezone = timezone

    def get_dbapi_type(self, dbapi):
        return dbapi.DATETIME

    @property
    def python_type(self):
        return dt.time

    @util.memoized_property
    def _expression_adaptations(self):
        return {
            operators.add: {
                Date: DateTime,
                Interval: self.__class__
            },
            operators.sub: {
                Time: Interval,
                Interval: self.__class__,
            },
        }


class _Binary(TypeEngine):
    """Define base behavior for binary types."""

    def __init__(self, length=None):
        self.length = length

    @property
    def python_type(self):
        # Py3K
        #return bytes
        # Py2K
        return str
        # end Py2K

    # Python 3 - sqlite3 doesn't need the `Binary` conversion
    # here, though pg8000 does to indicate "bytea"
    def bind_processor(self, dialect):
        DBAPIBinary = dialect.dbapi.Binary

        def process(value):
            x = self
            if value is not None:
                return DBAPIBinary(value)
            else:
                return None
        return process

    # Python 3 has native bytes() type
    # both sqlite3 and pg8000 seem to return it,
    # psycopg2 as of 2.5 returns 'memoryview'
    # Py3K
    #def result_processor(self, dialect, coltype):
    #    def process(value):
    #        if value is not None:
    #            value = bytes(value)
    #        return value
    #    return process
    # Py2K
    def result_processor(self, dialect, coltype):
        if util.jython:
            def process(value):
                if value is not None:
                    if isinstance(value, array.array):
                        return value.tostring()
                    return str(value)
                else:
                    return None
        else:
            process = processors.to_str
        return process
    # end Py2K

    def coerce_compared_value(self, op, value):
        """See :meth:`.TypeEngine.coerce_compared_value` for a description."""

        if isinstance(value, basestring):
            return self
        else:
            return super(_Binary, self).coerce_compared_value(op, value)

    def get_dbapi_type(self, dbapi):
        return dbapi.BINARY


class LargeBinary(_Binary):
    """A type for large binary byte data.

    The Binary type generates BLOB or BYTEA when tables are created,
    and also converts incoming values using the ``Binary`` callable
    provided by each DB-API.

    """

    __visit_name__ = 'large_binary'

    def __init__(self, length=None):
        """
        Construct a LargeBinary type.

        :param length: optional, a length for the column for use in
          DDL statements, for those BLOB types that accept a length
          (i.e. MySQL).  It does *not* produce a small BINARY/VARBINARY
          type - use the BINARY/VARBINARY types specifically for those.
          May be safely omitted if no ``CREATE
          TABLE`` will be issued.  Certain databases may require a
          *length* for use in DDL, and will raise an exception when
          the ``CREATE TABLE`` DDL is issued.

        """
        _Binary.__init__(self, length=length)


class Binary(LargeBinary):
    """Deprecated.  Renamed to LargeBinary."""

    def __init__(self, *arg, **kw):
        util.warn_deprecated('The Binary type has been renamed to '
                             'LargeBinary.')
        LargeBinary.__init__(self, *arg, **kw)


class SchemaType(events.SchemaEventTarget):
    """Mark a type as possibly requiring schema-level DDL for usage.

    Supports types that must be explicitly created/dropped (i.e. PG ENUM type)
    as well as types that are complimented by table or schema level
    constraints, triggers, and other rules.

    :class:`.SchemaType` classes can also be targets for the
    :meth:`.DDLEvents.before_parent_attach` and
    :meth:`.DDLEvents.after_parent_attach` events, where the events fire off
    surrounding the association of the type object with a parent
    :class:`.Column`.

    .. seealso::

        :class:`.Enum`

        :class:`.Boolean`


    """

    def __init__(self, **kw):
        self.name = kw.pop('name', None)
        self.quote = kw.pop('quote', None)
        self.schema = kw.pop('schema', None)
        self.metadata = kw.pop('metadata', None)
        self.inherit_schema = kw.pop('inherit_schema', False)
        if self.metadata:
            event.listen(
                self.metadata,
                "before_create",
                util.portable_instancemethod(self._on_metadata_create)
            )
            event.listen(
                self.metadata,
                "after_drop",
                util.portable_instancemethod(self._on_metadata_drop)
            )

    def _set_parent(self, column):
        column._on_table_attach(util.portable_instancemethod(self._set_table))

    def _set_table(self, column, table):
        if self.inherit_schema:
            self.schema = table.schema

        event.listen(
            table,
            "before_create",
              util.portable_instancemethod(
                    self._on_table_create)
        )
        event.listen(
            table,
            "after_drop",
            util.portable_instancemethod(self._on_table_drop)
        )
        if self.metadata is None:
            # TODO: what's the difference between self.metadata
            # and table.metadata here ?
            event.listen(
                table.metadata,
                "before_create",
                util.portable_instancemethod(self._on_metadata_create)
            )
            event.listen(
                table.metadata,
                "after_drop",
                util.portable_instancemethod(self._on_metadata_drop)
            )

    def copy(self, **kw):
        return self.adapt(self.__class__)

    def adapt(self, impltype, **kw):
        schema = kw.pop('schema', self.schema)
        metadata = kw.pop('metadata', self.metadata)
        return impltype(name=self.name,
                    quote=self.quote,
                    schema=schema,
                    metadata=metadata,
                    inherit_schema=self.inherit_schema,
                    **kw
                    )

    @property
    def bind(self):
        return self.metadata and self.metadata.bind or None

    def create(self, bind=None, checkfirst=False):
        """Issue CREATE ddl for this type, if applicable."""

        if bind is None:
            bind = schema._bind_or_error(self)
        t = self.dialect_impl(bind.dialect)
        if t.__class__ is not self.__class__ and isinstance(t, SchemaType):
            t.create(bind=bind, checkfirst=checkfirst)

    def drop(self, bind=None, checkfirst=False):
        """Issue DROP ddl for this type, if applicable."""

        if bind is None:
            bind = schema._bind_or_error(self)
        t = self.dialect_impl(bind.dialect)
        if t.__class__ is not self.__class__ and isinstance(t, SchemaType):
            t.drop(bind=bind, checkfirst=checkfirst)

    def _on_table_create(self, target, bind, **kw):
        t = self.dialect_impl(bind.dialect)
        if t.__class__ is not self.__class__ and isinstance(t, SchemaType):
            t._on_table_create(target, bind, **kw)

    def _on_table_drop(self, target, bind, **kw):
        t = self.dialect_impl(bind.dialect)
        if t.__class__ is not self.__class__ and isinstance(t, SchemaType):
            t._on_table_drop(target, bind, **kw)

    def _on_metadata_create(self, target, bind, **kw):
        t = self.dialect_impl(bind.dialect)
        if t.__class__ is not self.__class__ and isinstance(t, SchemaType):
            t._on_metadata_create(target, bind, **kw)

    def _on_metadata_drop(self, target, bind, **kw):
        t = self.dialect_impl(bind.dialect)
        if t.__class__ is not self.__class__ and isinstance(t, SchemaType):
            t._on_metadata_drop(target, bind, **kw)


class Enum(String, SchemaType):
    """Generic Enum Type.

    The Enum type provides a set of possible string values which the
    column is constrained towards.

    By default, uses the backend's native ENUM type if available,
    else uses VARCHAR + a CHECK constraint.

    .. seealso::

        :class:`~.postgresql.ENUM` - PostgreSQL-specific type,
        which has additional functionality.

    """

    __visit_name__ = 'enum'

    def __init__(self, *enums, **kw):
        """Construct an enum.

        Keyword arguments which don't apply to a specific backend are ignored
        by that backend.

        :param \*enums: string or unicode enumeration labels. If unicode
           labels are present, the `convert_unicode` flag is auto-enabled.

        :param convert_unicode: Enable unicode-aware bind parameter and
           result-set processing for this Enum's data. This is set
           automatically based on the presence of unicode label strings.

        :param metadata: Associate this type directly with a ``MetaData``
           object. For types that exist on the target database as an
           independent schema construct (Postgresql), this type will be
           created and dropped within ``create_all()`` and ``drop_all()``
           operations. If the type is not associated with any ``MetaData``
           object, it will associate itself with each ``Table`` in which it is
           used, and will be created when any of those individual tables are
           created, after a check is performed for it's existence. The type is
           only dropped when ``drop_all()`` is called for that ``Table``
           object's metadata, however.

        :param name: The name of this type. This is required for Postgresql
           and any future supported database which requires an explicitly
           named type, or an explicitly named constraint in order to generate
           the type and/or a table that uses it.

        :param native_enum: Use the database's native ENUM type when
           available. Defaults to True. When False, uses VARCHAR + check
           constraint for all backends.

        :param schema: Schema name of this type. For types that exist on the
           target database as an independent schema construct (Postgresql),
           this parameter specifies the named schema in which the type is
           present.

           .. note::

                The ``schema`` of the :class:`.Enum` type does not
                by default make use of the ``schema`` established on the
                owning :class:`.Table`.  If this behavior is desired,
                set the ``inherit_schema`` flag to ``True``.

        :param quote: Force quoting to be on or off on the type's name. If
           left as the default of `None`, the usual schema-level "case
           sensitive"/"reserved name" rules are used to determine if this
           type's name should be quoted.

        :param inherit_schema: When ``True``, the "schema" from the owning
           :class:`.Table` will be copied to the "schema" attribute of this
           :class:`.Enum`, replacing whatever value was passed for the
           ``schema`` attribute.   This also takes effect when using the
           :meth:`.Table.tometadata` operation.

           .. versionadded:: 0.8

        """
        self.enums = enums
        self.native_enum = kw.pop('native_enum', True)
        convert_unicode = kw.pop('convert_unicode', None)
        if convert_unicode is None:
            for e in enums:
                if isinstance(e, unicode):
                    convert_unicode = True
                    break
            else:
                convert_unicode = False

        if self.enums:
            length = max(len(x) for x in self.enums)
        else:
            length = 0
        String.__init__(self,
                        length=length,
                        convert_unicode=convert_unicode,
                        )
        SchemaType.__init__(self, **kw)

    def __repr__(self):
        return util.generic_repr(self, [
                        ("native_enum", True),
                        ("name", None)
                    ])

    def _should_create_constraint(self, compiler):
        return not self.native_enum or \
                    not compiler.dialect.supports_native_enum

    def _set_table(self, column, table):
        if self.native_enum:
            SchemaType._set_table(self, column, table)

        e = schema.CheckConstraint(
                        type_coerce(column, self).in_(self.enums),
                        name=self.name,
                        _create_rule=util.portable_instancemethod(
                                        self._should_create_constraint)
                    )
        table.append_constraint(e)

    def adapt(self, impltype, **kw):
        schema = kw.pop('schema', self.schema)
        metadata = kw.pop('metadata', self.metadata)
        if issubclass(impltype, Enum):
            return impltype(name=self.name,
                        quote=self.quote,
                        schema=schema,
                        metadata=metadata,
                        convert_unicode=self.convert_unicode,
                        native_enum=self.native_enum,
                        inherit_schema=self.inherit_schema,
                        *self.enums,
                        **kw
                        )
        else:
            return super(Enum, self).adapt(impltype, **kw)


class PickleType(TypeDecorator):
    """Holds Python objects, which are serialized using pickle.

    PickleType builds upon the Binary type to apply Python's
    ``pickle.dumps()`` to incoming objects, and ``pickle.loads()`` on
    the way out, allowing any pickleable Python object to be stored as
    a serialized binary field.

    To allow ORM change events to propagate for elements associated
    with :class:`.PickleType`, see :ref:`mutable_toplevel`.

    """

    impl = LargeBinary

    def __init__(self, protocol=pickle.HIGHEST_PROTOCOL,
                    pickler=None, comparator=None):
        """
        Construct a PickleType.

        :param protocol: defaults to ``pickle.HIGHEST_PROTOCOL``.

        :param pickler: defaults to cPickle.pickle or pickle.pickle if
          cPickle is not available.  May be any object with
          pickle-compatible ``dumps` and ``loads`` methods.

        :param comparator: a 2-arg callable predicate used
          to compare values of this type.  If left as ``None``,
          the Python "equals" operator is used to compare values.

        """
        self.protocol = protocol
        self.pickler = pickler or pickle
        self.comparator = comparator
        super(PickleType, self).__init__()

    def __reduce__(self):
        return PickleType, (self.protocol,
                            None,
                            self.comparator)

    def bind_processor(self, dialect):
        impl_processor = self.impl.bind_processor(dialect)
        dumps = self.pickler.dumps
        protocol = self.protocol
        if impl_processor:
            def process(value):
                if value is not None:
                    value = dumps(value, protocol)
                return impl_processor(value)
        else:
            def process(value):
                if value is not None:
                    value = dumps(value, protocol)
                return value
        return process

    def result_processor(self, dialect, coltype):
        impl_processor = self.impl.result_processor(dialect, coltype)
        loads = self.pickler.loads
        if impl_processor:
            def process(value):
                value = impl_processor(value)
                if value is None:
                    return None
                return loads(value)
        else:
            def process(value):
                if value is None:
                    return None
                return loads(value)
        return process

    def compare_values(self, x, y):
        if self.comparator:
            return self.comparator(x, y)
        else:
            return x == y


class Boolean(TypeEngine, SchemaType):
    """A bool datatype.

    Boolean typically uses BOOLEAN or SMALLINT on the DDL side, and on
    the Python side deals in ``True`` or ``False``.

    """

    __visit_name__ = 'boolean'

    def __init__(self, create_constraint=True, name=None):
        """Construct a Boolean.

        :param create_constraint: defaults to True.  If the boolean
          is generated as an int/smallint, also create a CHECK constraint
          on the table that ensures 1 or 0 as a value.

        :param name: if a CHECK constraint is generated, specify
          the name of the constraint.

        """
        self.create_constraint = create_constraint
        self.name = name

    def _should_create_constraint(self, compiler):
        return not compiler.dialect.supports_native_boolean

    def _set_table(self, column, table):
        if not self.create_constraint:
            return

        e = schema.CheckConstraint(
                        type_coerce(column, self).in_([0, 1]),
                        name=self.name,
                        _create_rule=util.portable_instancemethod(
                                    self._should_create_constraint)
                    )
        table.append_constraint(e)

    @property
    def python_type(self):
        return bool

    def bind_processor(self, dialect):
        if dialect.supports_native_boolean:
            return None
        else:
            return processors.boolean_to_int

    def result_processor(self, dialect, coltype):
        if dialect.supports_native_boolean:
            return None
        else:
            return processors.int_to_boolean


class Interval(_DateAffinity, TypeDecorator):
    """A type for ``datetime.timedelta()`` objects.

    The Interval type deals with ``datetime.timedelta`` objects.  In
    PostgreSQL, the native ``INTERVAL`` type is used; for others, the
    value is stored as a date which is relative to the "epoch"
    (Jan. 1, 1970).

    Note that the ``Interval`` type does not currently provide date arithmetic
    operations on platforms which do not support interval types natively. Such
    operations usually require transformation of both sides of the expression
    (such as, conversion of both sides into integer epoch values first) which
    currently is a manual procedure (such as via
    :attr:`~sqlalchemy.sql.expression.func`).

    """

    impl = DateTime
    epoch = dt.datetime.utcfromtimestamp(0)

    def __init__(self, native=True,
                        second_precision=None,
                        day_precision=None):
        """Construct an Interval object.

        :param native: when True, use the actual
          INTERVAL type provided by the database, if
          supported (currently Postgresql, Oracle).
          Otherwise, represent the interval data as
          an epoch value regardless.

        :param second_precision: For native interval types
          which support a "fractional seconds precision" parameter,
          i.e. Oracle and Postgresql

        :param day_precision: for native interval types which
          support a "day precision" parameter, i.e. Oracle.

        """
        super(Interval, self).__init__()
        self.native = native
        self.second_precision = second_precision
        self.day_precision = day_precision

    def adapt(self, cls, **kw):
        if self.native and hasattr(cls, '_adapt_from_generic_interval'):
            return cls._adapt_from_generic_interval(self, **kw)
        else:
            return self.__class__(
                        native=self.native,
                        second_precision=self.second_precision,
                        day_precision=self.day_precision,
                        **kw)

    @property
    def python_type(self):
        return dt.timedelta

    def bind_processor(self, dialect):
        impl_processor = self.impl.bind_processor(dialect)
        epoch = self.epoch
        if impl_processor:
            def process(value):
                if value is not None:
                    value = epoch + value
                return impl_processor(value)
        else:
            def process(value):
                if value is not None:
                    value = epoch + value
                return value
        return process

    def result_processor(self, dialect, coltype):
        impl_processor = self.impl.result_processor(dialect, coltype)
        epoch = self.epoch
        if impl_processor:
            def process(value):
                value = impl_processor(value)
                if value is None:
                    return None
                return value - epoch
        else:
            def process(value):
                if value is None:
                    return None
                return value - epoch
        return process

    @util.memoized_property
    def _expression_adaptations(self):
        return {
            operators.add: {
                Date: DateTime,
                Interval: self.__class__,
                DateTime: DateTime,
                Time: Time,
            },
            operators.sub: {
                Interval: self.__class__
            },
            operators.mul: {
                Numeric: self.__class__
            },
            operators.truediv: {
                Numeric: self.__class__
            },
            # Py2K
            operators.div: {
                Numeric: self.__class__
            }
            # end Py2K
        }

    @property
    def _type_affinity(self):
        return Interval

    def coerce_compared_value(self, op, value):
        """See :meth:`.TypeEngine.coerce_compared_value` for a description."""

        return self.impl.coerce_compared_value(op, value)


class REAL(Float):
    """The SQL REAL type."""

    __visit_name__ = 'REAL'


class FLOAT(Float):
    """The SQL FLOAT type."""

    __visit_name__ = 'FLOAT'


class NUMERIC(Numeric):
    """The SQL NUMERIC type."""

    __visit_name__ = 'NUMERIC'


class DECIMAL(Numeric):
    """The SQL DECIMAL type."""

    __visit_name__ = 'DECIMAL'


class INTEGER(Integer):
    """The SQL INT or INTEGER type."""

    __visit_name__ = 'INTEGER'
INT = INTEGER


class SMALLINT(SmallInteger):
    """The SQL SMALLINT type."""

    __visit_name__ = 'SMALLINT'


class BIGINT(BigInteger):
    """The SQL BIGINT type."""

    __visit_name__ = 'BIGINT'


class TIMESTAMP(DateTime):
    """The SQL TIMESTAMP type."""

    __visit_name__ = 'TIMESTAMP'

    def get_dbapi_type(self, dbapi):
        return dbapi.TIMESTAMP


class DATETIME(DateTime):
    """The SQL DATETIME type."""

    __visit_name__ = 'DATETIME'


class DATE(Date):
    """The SQL DATE type."""

    __visit_name__ = 'DATE'


class TIME(Time):
    """The SQL TIME type."""

    __visit_name__ = 'TIME'


class TEXT(Text):
    """The SQL TEXT type."""

    __visit_name__ = 'TEXT'


class CLOB(Text):
    """The CLOB type.

    This type is found in Oracle and Informix.
    """

    __visit_name__ = 'CLOB'


class VARCHAR(String):
    """The SQL VARCHAR type."""

    __visit_name__ = 'VARCHAR'


class NVARCHAR(Unicode):
    """The SQL NVARCHAR type."""

    __visit_name__ = 'NVARCHAR'


class CHAR(String):
    """The SQL CHAR type."""

    __visit_name__ = 'CHAR'


class NCHAR(Unicode):
    """The SQL NCHAR type."""

    __visit_name__ = 'NCHAR'


class BLOB(LargeBinary):
    """The SQL BLOB type."""

    __visit_name__ = 'BLOB'


class BINARY(_Binary):
    """The SQL BINARY type."""

    __visit_name__ = 'BINARY'


class VARBINARY(_Binary):
    """The SQL VARBINARY type."""

    __visit_name__ = 'VARBINARY'


class BOOLEAN(Boolean):
    """The SQL BOOLEAN type."""

    __visit_name__ = 'BOOLEAN'

NULLTYPE = NullType()
BOOLEANTYPE = Boolean()
STRINGTYPE = String()

_type_map = {
    str: String(),
    # Py3K
    #bytes: LargeBinary(),
    # Py2K
    unicode: Unicode(),
    # end Py2K
    int: Integer(),
    float: Numeric(),
    bool: BOOLEANTYPE,
    decimal.Decimal: Numeric(),
    dt.date: Date(),
    dt.datetime: DateTime(),
    dt.time: Time(),
    dt.timedelta: Interval(),
    NoneType: NULLTYPE
}
