# ext/declarative/__init__.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""
Synopsis
========

SQLAlchemy object-relational configuration involves the
combination of :class:`.Table`, :func:`.mapper`, and class
objects to define a mapped class.
:mod:`~sqlalchemy.ext.declarative` allows all three to be
expressed at once within the class declaration. As much as
possible, regular SQLAlchemy schema and ORM constructs are
used directly, so that configuration between "classical" ORM
usage and declarative remain highly similar.

As a simple example::

    from sqlalchemy.ext.declarative import declarative_base

    Base = declarative_base()

    class SomeClass(Base):
        __tablename__ = 'some_table'
        id = Column(Integer, primary_key=True)
        name =  Column(String(50))

Above, the :func:`declarative_base` callable returns a new base class from
which all mapped classes should inherit. When the class definition is
completed, a new :class:`.Table` and :func:`.mapper` will have been generated.

The resulting table and mapper are accessible via
``__table__`` and ``__mapper__`` attributes on the
``SomeClass`` class::

    # access the mapped Table
    SomeClass.__table__

    # access the Mapper
    SomeClass.__mapper__

Defining Attributes
===================

In the previous example, the :class:`.Column` objects are
automatically named with the name of the attribute to which they are
assigned.

To name columns explicitly with a name distinct from their mapped attribute,
just give the column a name.  Below, column "some_table_id" is mapped to the
"id" attribute of `SomeClass`, but in SQL will be represented as
"some_table_id"::

    class SomeClass(Base):
        __tablename__ = 'some_table'
        id = Column("some_table_id", Integer, primary_key=True)

Attributes may be added to the class after its construction, and they will be
added to the underlying :class:`.Table` and
:func:`.mapper` definitions as appropriate::

    SomeClass.data = Column('data', Unicode)
    SomeClass.related = relationship(RelatedInfo)

Classes which are constructed using declarative can interact freely
with classes that are mapped explicitly with :func:`.mapper`.

It is recommended, though not required, that all tables
share the same underlying :class:`~sqlalchemy.schema.MetaData` object,
so that string-configured :class:`~sqlalchemy.schema.ForeignKey`
references can be resolved without issue.

Accessing the MetaData
=======================

The :func:`declarative_base` base class contains a
:class:`.MetaData` object where newly defined
:class:`.Table` objects are collected. This object is
intended to be accessed directly for
:class:`.MetaData`-specific operations. Such as, to issue
CREATE statements for all tables::

    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)

:func:`declarative_base` can also receive a pre-existing
:class:`.MetaData` object, which allows a
declarative setup to be associated with an already
existing traditional collection of :class:`~sqlalchemy.schema.Table`
objects::

    mymetadata = MetaData()
    Base = declarative_base(metadata=mymetadata)

Configuring Relationships
=========================

Relationships to other classes are done in the usual way, with the added
feature that the class specified to :func:`~sqlalchemy.orm.relationship`
may be a string name.  The "class registry" associated with ``Base``
is used at mapper compilation time to resolve the name into the actual
class object, which is expected to have been defined once the mapper
configuration is used::

    class User(Base):
        __tablename__ = 'users'

        id = Column(Integer, primary_key=True)
        name = Column(String(50))
        addresses = relationship("Address", backref="user")

    class Address(Base):
        __tablename__ = 'addresses'

        id = Column(Integer, primary_key=True)
        email = Column(String(50))
        user_id = Column(Integer, ForeignKey('users.id'))

Column constructs, since they are just that, are immediately usable,
as below where we define a primary join condition on the ``Address``
class using them::

    class Address(Base):
        __tablename__ = 'addresses'

        id = Column(Integer, primary_key=True)
        email = Column(String(50))
        user_id = Column(Integer, ForeignKey('users.id'))
        user = relationship(User, primaryjoin=user_id == User.id)

In addition to the main argument for :func:`~sqlalchemy.orm.relationship`,
other arguments which depend upon the columns present on an as-yet
undefined class may also be specified as strings.  These strings are
evaluated as Python expressions.  The full namespace available within
this evaluation includes all classes mapped for this declarative base,
as well as the contents of the ``sqlalchemy`` package, including
expression functions like :func:`~sqlalchemy.sql.expression.desc` and
:attr:`~sqlalchemy.sql.expression.func`::

    class User(Base):
        # ....
        addresses = relationship("Address",
                             order_by="desc(Address.email)",
                             primaryjoin="Address.user_id==User.id")

For the case where more than one module contains a class of the same name,
string class names can also be specified as module-qualified paths
within any of these string expressions::

    class User(Base):
        # ....
        addresses = relationship("myapp.model.address.Address",
                             order_by="desc(myapp.model.address.Address.email)",
                             primaryjoin="myapp.model.address.Address.user_id=="
                                            "myapp.model.user.User.id")

The qualified path can be any partial path that removes ambiguity between
the names.  For example, to disambiguate between
``myapp.model.address.Address`` and ``myapp.model.lookup.Address``,
we can specify ``address.Address`` or ``lookup.Address``::

    class User(Base):
        # ....
        addresses = relationship("address.Address",
                             order_by="desc(address.Address.email)",
                             primaryjoin="address.Address.user_id=="
                                            "User.id")

.. versionadded:: 0.8
   module-qualified paths can be used when specifying string arguments
   with Declarative, in order to specify specific modules.

Two alternatives also exist to using string-based attributes.  A lambda
can also be used, which will be evaluated after all mappers have been
configured::

    class User(Base):
        # ...
        addresses = relationship(lambda: Address,
                             order_by=lambda: desc(Address.email),
                             primaryjoin=lambda: Address.user_id==User.id)

Or, the relationship can be added to the class explicitly after the classes
are available::

    User.addresses = relationship(Address,
                              primaryjoin=Address.user_id==User.id)




Configuring Many-to-Many Relationships
======================================

Many-to-many relationships are also declared in the same way
with declarative as with traditional mappings. The
``secondary`` argument to
:func:`.relationship` is as usual passed a
:class:`.Table` object, which is typically declared in the
traditional way.  The :class:`.Table` usually shares
the :class:`.MetaData` object used by the declarative base::

    keywords = Table(
        'keywords', Base.metadata,
        Column('author_id', Integer, ForeignKey('authors.id')),
        Column('keyword_id', Integer, ForeignKey('keywords.id'))
        )

    class Author(Base):
        __tablename__ = 'authors'
        id = Column(Integer, primary_key=True)
        keywords = relationship("Keyword", secondary=keywords)

Like other :func:`~sqlalchemy.orm.relationship` arguments, a string is accepted
as well, passing the string name of the table as defined in the
``Base.metadata.tables`` collection::

    class Author(Base):
        __tablename__ = 'authors'
        id = Column(Integer, primary_key=True)
        keywords = relationship("Keyword", secondary="keywords")

As with traditional mapping, its generally not a good idea to use
a :class:`.Table` as the "secondary" argument which is also mapped to
a class, unless the :func:`.relationship` is declared with ``viewonly=True``.
Otherwise, the unit-of-work system may attempt duplicate INSERT and
DELETE statements against the underlying table.

.. _declarative_sql_expressions:

Defining SQL Expressions
========================

See :ref:`mapper_sql_expressions` for examples on declaratively
mapping attributes to SQL expressions.

.. _declarative_table_args:

Table Configuration
===================

Table arguments other than the name, metadata, and mapped Column
arguments are specified using the ``__table_args__`` class attribute.
This attribute accommodates both positional as well as keyword
arguments that are normally sent to the
:class:`~sqlalchemy.schema.Table` constructor.
The attribute can be specified in one of two forms. One is as a
dictionary::

    class MyClass(Base):
        __tablename__ = 'sometable'
        __table_args__ = {'mysql_engine':'InnoDB'}

The other, a tuple, where each argument is positional
(usually constraints)::

    class MyClass(Base):
        __tablename__ = 'sometable'
        __table_args__ = (
                ForeignKeyConstraint(['id'], ['remote_table.id']),
                UniqueConstraint('foo'),
                )

Keyword arguments can be specified with the above form by
specifying the last argument as a dictionary::

    class MyClass(Base):
        __tablename__ = 'sometable'
        __table_args__ = (
                ForeignKeyConstraint(['id'], ['remote_table.id']),
                UniqueConstraint('foo'),
                {'autoload':True}
                )

Using a Hybrid Approach with __table__
=======================================

As an alternative to ``__tablename__``, a direct
:class:`~sqlalchemy.schema.Table` construct may be used.  The
:class:`~sqlalchemy.schema.Column` objects, which in this case require
their names, will be added to the mapping just like a regular mapping
to a table::

    class MyClass(Base):
        __table__ = Table('my_table', Base.metadata,
            Column('id', Integer, primary_key=True),
            Column('name', String(50))
        )

``__table__`` provides a more focused point of control for establishing
table metadata, while still getting most of the benefits of using declarative.
An application that uses reflection might want to load table metadata elsewhere
and pass it to declarative classes::

    from sqlalchemy.ext.declarative import declarative_base

    Base = declarative_base()
    Base.metadata.reflect(some_engine)

    class User(Base):
        __table__ = metadata.tables['user']

    class Address(Base):
        __table__ = metadata.tables['address']

Some configuration schemes may find it more appropriate to use ``__table__``,
such as those which already take advantage of the data-driven nature of
:class:`.Table` to customize and/or automate schema definition.

Note that when the ``__table__`` approach is used, the object is immediately
usable as a plain :class:`.Table` within the class declaration body itself,
as a Python class is only another syntactical block.  Below this is illustrated
by using the ``id`` column in the ``primaryjoin`` condition of a
:func:`.relationship`::

    class MyClass(Base):
        __table__ = Table('my_table', Base.metadata,
            Column('id', Integer, primary_key=True),
            Column('name', String(50))
        )

        widgets = relationship(Widget,
                    primaryjoin=Widget.myclass_id==__table__.c.id)

Similarly, mapped attributes which refer to ``__table__`` can be placed inline,
as below where we assign the ``name`` column to the attribute ``_name``,
generating a synonym for ``name``::

    from sqlalchemy.ext.declarative import synonym_for

    class MyClass(Base):
        __table__ = Table('my_table', Base.metadata,
            Column('id', Integer, primary_key=True),
            Column('name', String(50))
        )

        _name = __table__.c.name

        @synonym_for("_name")
        def name(self):
            return "Name: %s" % _name

Using Reflection with Declarative
=================================

It's easy to set up a :class:`.Table` that uses ``autoload=True``
in conjunction with a mapped class::

    class MyClass(Base):
        __table__ = Table('mytable', Base.metadata,
                        autoload=True, autoload_with=some_engine)

However, one improvement that can be made here is to not
require the :class:`.Engine` to be available when classes are
being first declared.   To achieve this, use the
:class:`.DeferredReflection` mixin, which sets up mappings
only after a special ``prepare(engine)`` step is called::

    from sqlalchemy.ext.declarative import declarative_base, DeferredReflection

    Base = declarative_base(cls=DeferredReflection)

    class Foo(Base):
        __tablename__ = 'foo'
        bars = relationship("Bar")

    class Bar(Base):
        __tablename__ = 'bar'

        # illustrate overriding of "bar.foo_id" to have
        # a foreign key constraint otherwise not
        # reflected, such as when using MySQL
        foo_id = Column(Integer, ForeignKey('foo.id'))

    Base.prepare(e)

.. versionadded:: 0.8
   Added :class:`.DeferredReflection`.

Mapper Configuration
====================

Declarative makes use of the :func:`~.orm.mapper` function internally
when it creates the mapping to the declared table.   The options
for :func:`~.orm.mapper` are passed directly through via the
``__mapper_args__`` class attribute.  As always, arguments which reference
locally mapped columns can reference them directly from within the
class declaration::

    from datetime import datetime

    class Widget(Base):
        __tablename__ = 'widgets'

        id = Column(Integer, primary_key=True)
        timestamp = Column(DateTime, nullable=False)

        __mapper_args__ = {
                        'version_id_col': timestamp,
                        'version_id_generator': lambda v:datetime.now()
                    }

.. _declarative_inheritance:

Inheritance Configuration
=========================

Declarative supports all three forms of inheritance as intuitively
as possible.  The ``inherits`` mapper keyword argument is not needed
as declarative will determine this from the class itself.   The various
"polymorphic" keyword arguments are specified using ``__mapper_args__``.

Joined Table Inheritance
~~~~~~~~~~~~~~~~~~~~~~~~

Joined table inheritance is defined as a subclass that defines its own
table::

    class Person(Base):
        __tablename__ = 'people'
        id = Column(Integer, primary_key=True)
        discriminator = Column('type', String(50))
        __mapper_args__ = {'polymorphic_on': discriminator}

    class Engineer(Person):
        __tablename__ = 'engineers'
        __mapper_args__ = {'polymorphic_identity': 'engineer'}
        id = Column(Integer, ForeignKey('people.id'), primary_key=True)
        primary_language = Column(String(50))

Note that above, the ``Engineer.id`` attribute, since it shares the
same attribute name as the ``Person.id`` attribute, will in fact
represent the ``people.id`` and ``engineers.id`` columns together,
with the "Engineer.id" column taking precedence if queried directly.
To provide the ``Engineer`` class with an attribute that represents
only the ``engineers.id`` column, give it a different attribute name::

    class Engineer(Person):
        __tablename__ = 'engineers'
        __mapper_args__ = {'polymorphic_identity': 'engineer'}
        engineer_id = Column('id', Integer, ForeignKey('people.id'),
                                                    primary_key=True)
        primary_language = Column(String(50))


.. versionchanged:: 0.7 joined table inheritance favors the subclass
   column over that of the superclass, such as querying above
   for ``Engineer.id``.  Prior to 0.7 this was the reverse.

.. _declarative_single_table:

Single Table Inheritance
~~~~~~~~~~~~~~~~~~~~~~~~

Single table inheritance is defined as a subclass that does not have
its own table; you just leave out the ``__table__`` and ``__tablename__``
attributes::

    class Person(Base):
        __tablename__ = 'people'
        id = Column(Integer, primary_key=True)
        discriminator = Column('type', String(50))
        __mapper_args__ = {'polymorphic_on': discriminator}

    class Engineer(Person):
        __mapper_args__ = {'polymorphic_identity': 'engineer'}
        primary_language = Column(String(50))

When the above mappers are configured, the ``Person`` class is mapped
to the ``people`` table *before* the ``primary_language`` column is
defined, and this column will not be included in its own mapping.
When ``Engineer`` then defines the ``primary_language`` column, the
column is added to the ``people`` table so that it is included in the
mapping for ``Engineer`` and is also part of the table's full set of
columns.  Columns which are not mapped to ``Person`` are also excluded
from any other single or joined inheriting classes using the
``exclude_properties`` mapper argument.  Below, ``Manager`` will have
all the attributes of ``Person`` and ``Manager`` but *not* the
``primary_language`` attribute of ``Engineer``::

    class Manager(Person):
        __mapper_args__ = {'polymorphic_identity': 'manager'}
        golf_swing = Column(String(50))

The attribute exclusion logic is provided by the
``exclude_properties`` mapper argument, and declarative's default
behavior can be disabled by passing an explicit ``exclude_properties``
collection (empty or otherwise) to the ``__mapper_args__``.

Resolving Column Conflicts
^^^^^^^^^^^^^^^^^^^^^^^^^^

Note above that the ``primary_language`` and ``golf_swing`` columns
are "moved up" to be applied to ``Person.__table__``, as a result of their
declaration on a subclass that has no table of its own.   A tricky case
comes up when two subclasses want to specify *the same* column, as below::

    class Person(Base):
        __tablename__ = 'people'
        id = Column(Integer, primary_key=True)
        discriminator = Column('type', String(50))
        __mapper_args__ = {'polymorphic_on': discriminator}

    class Engineer(Person):
        __mapper_args__ = {'polymorphic_identity': 'engineer'}
        start_date = Column(DateTime)

    class Manager(Person):
        __mapper_args__ = {'polymorphic_identity': 'manager'}
        start_date = Column(DateTime)

Above, the ``start_date`` column declared on both ``Engineer`` and ``Manager``
will result in an error::

    sqlalchemy.exc.ArgumentError: Column 'start_date' on class
    <class '__main__.Manager'> conflicts with existing
    column 'people.start_date'

In a situation like this, Declarative can't be sure
of the intent, especially if the ``start_date`` columns had, for example,
different types.   A situation like this can be resolved by using
:class:`.declared_attr` to define the :class:`.Column` conditionally, taking
care to return the **existing column** via the parent ``__table__`` if it
already exists::

    from sqlalchemy.ext.declarative import declared_attr

    class Person(Base):
        __tablename__ = 'people'
        id = Column(Integer, primary_key=True)
        discriminator = Column('type', String(50))
        __mapper_args__ = {'polymorphic_on': discriminator}

    class Engineer(Person):
        __mapper_args__ = {'polymorphic_identity': 'engineer'}

        @declared_attr
        def start_date(cls):
            "Start date column, if not present already."
            return Person.__table__.c.get('start_date', Column(DateTime))

    class Manager(Person):
        __mapper_args__ = {'polymorphic_identity': 'manager'}

        @declared_attr
        def start_date(cls):
            "Start date column, if not present already."
            return Person.__table__.c.get('start_date', Column(DateTime))

Above, when ``Manager`` is mapped, the ``start_date`` column is
already present on the ``Person`` class.  Declarative lets us return
that :class:`.Column` as a result in this case, where it knows to skip
re-assigning the same column. If the mapping is mis-configured such
that the ``start_date`` column is accidentally re-assigned to a
different table (such as, if we changed ``Manager`` to be joined
inheritance without fixing ``start_date``), an error is raised which
indicates an existing :class:`.Column` is trying to be re-assigned to
a different owning :class:`.Table`.

.. versionadded:: 0.8 :class:`.declared_attr` can be used on a non-mixin
   class, and the returned :class:`.Column` or other mapped attribute
   will be applied to the mapping as any other attribute.  Previously,
   the resulting attribute would be ignored, and also result in a warning
   being emitted when a subclass was created.

.. versionadded:: 0.8 :class:`.declared_attr`, when used either with a
   mixin or non-mixin declarative class, can return an existing
   :class:`.Column` already assigned to the parent :class:`.Table`,
   to indicate that the re-assignment of the :class:`.Column` should be
   skipped, however should still be mapped on the target class,
   in order to resolve duplicate column conflicts.

The same concept can be used with mixin classes (see
:ref:`declarative_mixins`)::

    class Person(Base):
        __tablename__ = 'people'
        id = Column(Integer, primary_key=True)
        discriminator = Column('type', String(50))
        __mapper_args__ = {'polymorphic_on': discriminator}

    class HasStartDate(object):
        @declared_attr
        def start_date(cls):
            return cls.__table__.c.get('start_date', Column(DateTime))

    class Engineer(HasStartDate, Person):
        __mapper_args__ = {'polymorphic_identity': 'engineer'}

    class Manager(HasStartDate, Person):
        __mapper_args__ = {'polymorphic_identity': 'manager'}

The above mixin checks the local ``__table__`` attribute for the column.
Because we're using single table inheritance, we're sure that in this case,
``cls.__table__`` refers to ``People.__table__``.  If we were mixing joined-
and single-table inheritance, we might want our mixin to check more carefully
if ``cls.__table__`` is really the :class:`.Table` we're looking for.

Concrete Table Inheritance
~~~~~~~~~~~~~~~~~~~~~~~~~~

Concrete is defined as a subclass which has its own table and sets the
``concrete`` keyword argument to ``True``::

    class Person(Base):
        __tablename__ = 'people'
        id = Column(Integer, primary_key=True)
        name = Column(String(50))

    class Engineer(Person):
        __tablename__ = 'engineers'
        __mapper_args__ = {'concrete':True}
        id = Column(Integer, primary_key=True)
        primary_language = Column(String(50))
        name = Column(String(50))

Usage of an abstract base class is a little less straightforward as it
requires usage of :func:`~sqlalchemy.orm.util.polymorphic_union`,
which needs to be created with the :class:`.Table` objects
before the class is built::

    engineers = Table('engineers', Base.metadata,
                    Column('id', Integer, primary_key=True),
                    Column('name', String(50)),
                    Column('primary_language', String(50))
                )
    managers = Table('managers', Base.metadata,
                    Column('id', Integer, primary_key=True),
                    Column('name', String(50)),
                    Column('golf_swing', String(50))
                )

    punion = polymorphic_union({
        'engineer':engineers,
        'manager':managers
    }, 'type', 'punion')

    class Person(Base):
        __table__ = punion
        __mapper_args__ = {'polymorphic_on':punion.c.type}

    class Engineer(Person):
        __table__ = engineers
        __mapper_args__ = {'polymorphic_identity':'engineer', 'concrete':True}

    class Manager(Person):
        __table__ = managers
        __mapper_args__ = {'polymorphic_identity':'manager', 'concrete':True}

.. _declarative_concrete_helpers:

Using the Concrete Helpers
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Helper classes provides a simpler pattern for concrete inheritance.
With these objects, the ``__declare_last__`` helper is used to configure the
"polymorphic" loader for the mapper after all subclasses have been declared.

.. versionadded:: 0.7.3

An abstract base can be declared using the
:class:`.AbstractConcreteBase` class::

    from sqlalchemy.ext.declarative import AbstractConcreteBase

    class Employee(AbstractConcreteBase, Base):
        pass

To have a concrete ``employee`` table, use :class:`.ConcreteBase` instead::

    from sqlalchemy.ext.declarative import ConcreteBase

    class Employee(ConcreteBase, Base):
        __tablename__ = 'employee'
        employee_id = Column(Integer, primary_key=True)
        name = Column(String(50))
        __mapper_args__ = {
                        'polymorphic_identity':'employee',
                        'concrete':True}


Either ``Employee`` base can be used in the normal fashion::

    class Manager(Employee):
        __tablename__ = 'manager'
        employee_id = Column(Integer, primary_key=True)
        name = Column(String(50))
        manager_data = Column(String(40))
        __mapper_args__ = {
                        'polymorphic_identity':'manager',
                        'concrete':True}

    class Engineer(Employee):
        __tablename__ = 'engineer'
        employee_id = Column(Integer, primary_key=True)
        name = Column(String(50))
        engineer_info = Column(String(40))
        __mapper_args__ = {'polymorphic_identity':'engineer',
                        'concrete':True}


.. _declarative_mixins:

Mixin and Custom Base Classes
==============================

A common need when using :mod:`~sqlalchemy.ext.declarative` is to
share some functionality, such as a set of common columns, some common
table options, or other mapped properties, across many
classes.  The standard Python idioms for this is to have the classes
inherit from a base which includes these common features.

When using :mod:`~sqlalchemy.ext.declarative`, this idiom is allowed
via the usage of a custom declarative base class, as well as a "mixin" class
which is inherited from in addition to the primary base.  Declarative
includes several helper features to make this work in terms of how
mappings are declared.   An example of some commonly mixed-in
idioms is below::

    from sqlalchemy.ext.declarative import declared_attr

    class MyMixin(object):

        @declared_attr
        def __tablename__(cls):
            return cls.__name__.lower()

        __table_args__ = {'mysql_engine': 'InnoDB'}
        __mapper_args__= {'always_refresh': True}

        id =  Column(Integer, primary_key=True)

    class MyModel(MyMixin, Base):
        name = Column(String(1000))

Where above, the class ``MyModel`` will contain an "id" column
as the primary key, a ``__tablename__`` attribute that derives
from the name of the class itself, as well as ``__table_args__``
and ``__mapper_args__`` defined by the ``MyMixin`` mixin class.

There's no fixed convention over whether ``MyMixin`` precedes
``Base`` or not.  Normal Python method resolution rules apply, and
the above example would work just as well with::

    class MyModel(Base, MyMixin):
        name = Column(String(1000))

This works because ``Base`` here doesn't define any of the
variables that ``MyMixin`` defines, i.e. ``__tablename__``,
``__table_args__``, ``id``, etc.   If the ``Base`` did define
an attribute of the same name, the class placed first in the
inherits list would determine which attribute is used on the
newly defined class.

Augmenting the Base
~~~~~~~~~~~~~~~~~~~

In addition to using a pure mixin, most of the techniques in this
section can also be applied to the base class itself, for patterns that
should apply to all classes derived from a particular base.  This is achieved
using the ``cls`` argument of the :func:`.declarative_base` function::

    from sqlalchemy.ext.declarative import declared_attr

    class Base(object):
        @declared_attr
        def __tablename__(cls):
            return cls.__name__.lower()

        __table_args__ = {'mysql_engine': 'InnoDB'}

        id =  Column(Integer, primary_key=True)

    from sqlalchemy.ext.declarative import declarative_base

    Base = declarative_base(cls=Base)

    class MyModel(Base):
        name = Column(String(1000))

Where above, ``MyModel`` and all other classes that derive from ``Base`` will
have a table name derived from the class name, an ``id`` primary key column,
as well as the "InnoDB" engine for MySQL.

Mixing in Columns
~~~~~~~~~~~~~~~~~

The most basic way to specify a column on a mixin is by simple
declaration::

    class TimestampMixin(object):
        created_at = Column(DateTime, default=func.now())

    class MyModel(TimestampMixin, Base):
        __tablename__ = 'test'

        id =  Column(Integer, primary_key=True)
        name = Column(String(1000))

Where above, all declarative classes that include ``TimestampMixin``
will also have a column ``created_at`` that applies a timestamp to
all row insertions.

Those familiar with the SQLAlchemy expression language know that
the object identity of clause elements defines their role in a schema.
Two ``Table`` objects ``a`` and ``b`` may both have a column called
``id``, but the way these are differentiated is that ``a.c.id``
and ``b.c.id`` are two distinct Python objects, referencing their
parent tables ``a`` and ``b`` respectively.

In the case of the mixin column, it seems that only one
:class:`.Column` object is explicitly created, yet the ultimate
``created_at`` column above must exist as a distinct Python object
for each separate destination class.  To accomplish this, the declarative
extension creates a **copy** of each :class:`.Column` object encountered on
a class that is detected as a mixin.

This copy mechanism is limited to simple columns that have no foreign
keys, as a :class:`.ForeignKey` itself contains references to columns
which can't be properly recreated at this level.  For columns that
have foreign keys, as well as for the variety of mapper-level constructs
that require destination-explicit context, the
:class:`~.declared_attr` decorator is provided so that
patterns common to many classes can be defined as callables::

    from sqlalchemy.ext.declarative import declared_attr

    class ReferenceAddressMixin(object):
        @declared_attr
        def address_id(cls):
            return Column(Integer, ForeignKey('address.id'))

    class User(ReferenceAddressMixin, Base):
        __tablename__ = 'user'
        id = Column(Integer, primary_key=True)

Where above, the ``address_id`` class-level callable is executed at the
point at which the ``User`` class is constructed, and the declarative
extension can use the resulting :class:`.Column` object as returned by
the method without the need to copy it.

.. versionchanged:: > 0.6.5
    Rename 0.6.5 ``sqlalchemy.util.classproperty``
    into :class:`~.declared_attr`.

Columns generated by :class:`~.declared_attr` can also be
referenced by ``__mapper_args__`` to a limited degree, currently
by ``polymorphic_on`` and ``version_id_col``, by specifying the
classdecorator itself into the dictionary - the declarative extension
will resolve them at class construction time::

    class MyMixin:
        @declared_attr
        def type_(cls):
            return Column(String(50))

        __mapper_args__= {'polymorphic_on':type_}

    class MyModel(MyMixin, Base):
        __tablename__='test'
        id =  Column(Integer, primary_key=True)



Mixing in Relationships
~~~~~~~~~~~~~~~~~~~~~~~

Relationships created by :func:`~sqlalchemy.orm.relationship` are provided
with declarative mixin classes exclusively using the
:class:`.declared_attr` approach, eliminating any ambiguity
which could arise when copying a relationship and its possibly column-bound
contents. Below is an example which combines a foreign key column and a
relationship so that two classes ``Foo`` and ``Bar`` can both be configured to
reference a common target class via many-to-one::

    class RefTargetMixin(object):
        @declared_attr
        def target_id(cls):
            return Column('target_id', ForeignKey('target.id'))

        @declared_attr
        def target(cls):
            return relationship("Target")

    class Foo(RefTargetMixin, Base):
        __tablename__ = 'foo'
        id = Column(Integer, primary_key=True)

    class Bar(RefTargetMixin, Base):
        __tablename__ = 'bar'
        id = Column(Integer, primary_key=True)

    class Target(Base):
        __tablename__ = 'target'
        id = Column(Integer, primary_key=True)

:func:`~sqlalchemy.orm.relationship` definitions which require explicit
primaryjoin, order_by etc. expressions should use the string forms
for these arguments, so that they are evaluated as late as possible.
To reference the mixin class in these expressions, use the given ``cls``
to get its name::

    class RefTargetMixin(object):
        @declared_attr
        def target_id(cls):
            return Column('target_id', ForeignKey('target.id'))

        @declared_attr
        def target(cls):
            return relationship("Target",
                primaryjoin="Target.id==%s.target_id" % cls.__name__
            )

Mixing in deferred(), column_property(), and other MapperProperty classes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Like :func:`~sqlalchemy.orm.relationship`, all
:class:`~sqlalchemy.orm.interfaces.MapperProperty` subclasses such as
:func:`~sqlalchemy.orm.deferred`, :func:`~sqlalchemy.orm.column_property`,
etc. ultimately involve references to columns, and therefore, when
used with declarative mixins, have the :class:`.declared_attr`
requirement so that no reliance on copying is needed::

    class SomethingMixin(object):

        @declared_attr
        def dprop(cls):
            return deferred(Column(Integer))

    class Something(SomethingMixin, Base):
        __tablename__ = "something"

Mixing in Association Proxy and Other Attributes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Mixins can specify user-defined attributes as well as other extension
units such as :func:`.association_proxy`.   The usage of
:class:`.declared_attr` is required in those cases where the attribute must
be tailored specifically to the target subclass.   An example is when
constructing multiple :func:`.association_proxy` attributes which each
target a different type of child object.  Below is an
:func:`.association_proxy` / mixin example which provides a scalar list of
string values to an implementing class::

    from sqlalchemy import Column, Integer, ForeignKey, String
    from sqlalchemy.orm import relationship
    from sqlalchemy.ext.associationproxy import association_proxy
    from sqlalchemy.ext.declarative import declarative_base, declared_attr

    Base = declarative_base()

    class HasStringCollection(object):
        @declared_attr
        def _strings(cls):
            class StringAttribute(Base):
                __tablename__ = cls.string_table_name
                id = Column(Integer, primary_key=True)
                value = Column(String(50), nullable=False)
                parent_id = Column(Integer,
                                ForeignKey('%s.id' % cls.__tablename__),
                                nullable=False)
                def __init__(self, value):
                    self.value = value

            return relationship(StringAttribute)

        @declared_attr
        def strings(cls):
            return association_proxy('_strings', 'value')

    class TypeA(HasStringCollection, Base):
        __tablename__ = 'type_a'
        string_table_name = 'type_a_strings'
        id = Column(Integer(), primary_key=True)

    class TypeB(HasStringCollection, Base):
        __tablename__ = 'type_b'
        string_table_name = 'type_b_strings'
        id = Column(Integer(), primary_key=True)

Above, the ``HasStringCollection`` mixin produces a :func:`.relationship`
which refers to a newly generated class called ``StringAttribute``.  The
``StringAttribute`` class is generated with it's own :class:`.Table`
definition which is local to the parent class making usage of the
``HasStringCollection`` mixin.  It also produces an :func:`.association_proxy`
object which proxies references to the ``strings`` attribute onto the ``value``
attribute of each ``StringAttribute`` instance.

``TypeA`` or ``TypeB`` can be instantiated given the constructor
argument ``strings``, a list of strings::

    ta = TypeA(strings=['foo', 'bar'])
    tb = TypeA(strings=['bat', 'bar'])

This list will generate a collection
of ``StringAttribute`` objects, which are persisted into a table that's
local to either the ``type_a_strings`` or ``type_b_strings`` table::

    >>> print ta._strings
    [<__main__.StringAttribute object at 0x10151cd90>,
        <__main__.StringAttribute object at 0x10151ce10>]

When constructing the :func:`.association_proxy`, the
:class:`.declared_attr` decorator must be used so that a distinct
:func:`.association_proxy` object is created for each of the ``TypeA``
and ``TypeB`` classes.

.. versionadded:: 0.8 :class:`.declared_attr` is usable with non-mapped
   attributes, including user-defined attributes as well as
   :func:`.association_proxy`.


Controlling table inheritance with mixins
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``__tablename__`` attribute in conjunction with the hierarchy of
classes involved in a declarative mixin scenario controls what type of
table inheritance, if any,
is configured by the declarative extension.

If the ``__tablename__`` is computed by a mixin, you may need to
control which classes get the computed attribute in order to get the
type of table inheritance you require.

For example, if you had a mixin that computes ``__tablename__`` but
where you wanted to use that mixin in a single table inheritance
hierarchy, you can explicitly specify ``__tablename__`` as ``None`` to
indicate that the class should not have a table mapped::

    from sqlalchemy.ext.declarative import declared_attr

    class Tablename:
        @declared_attr
        def __tablename__(cls):
            return cls.__name__.lower()

    class Person(Tablename, Base):
        id = Column(Integer, primary_key=True)
        discriminator = Column('type', String(50))
        __mapper_args__ = {'polymorphic_on': discriminator}

    class Engineer(Person):
        __tablename__ = None
        __mapper_args__ = {'polymorphic_identity': 'engineer'}
        primary_language = Column(String(50))

Alternatively, you can make the mixin intelligent enough to only
return a ``__tablename__`` in the event that no table is already
mapped in the inheritance hierarchy. To help with this, a
:func:`~sqlalchemy.ext.declarative.has_inherited_table` helper
function is provided that returns ``True`` if a parent class already
has a mapped table.

As an example, here's a mixin that will only allow single table
inheritance::

    from sqlalchemy.ext.declarative import declared_attr
    from sqlalchemy.ext.declarative import has_inherited_table

    class Tablename(object):
        @declared_attr
        def __tablename__(cls):
            if has_inherited_table(cls):
                return None
            return cls.__name__.lower()

    class Person(Tablename, Base):
        id = Column(Integer, primary_key=True)
        discriminator = Column('type', String(50))
        __mapper_args__ = {'polymorphic_on': discriminator}

    class Engineer(Person):
        primary_language = Column(String(50))
        __mapper_args__ = {'polymorphic_identity': 'engineer'}

If you want to use a similar pattern with a mix of single and joined
table inheritance, you would need a slightly different mixin and use
it on any joined table child classes in addition to their parent
classes::

    from sqlalchemy.ext.declarative import declared_attr
    from sqlalchemy.ext.declarative import has_inherited_table

    class Tablename(object):
        @declared_attr
        def __tablename__(cls):
            if (has_inherited_table(cls) and
                Tablename not in cls.__bases__):
                return None
            return cls.__name__.lower()

    class Person(Tablename, Base):
        id = Column(Integer, primary_key=True)
        discriminator = Column('type', String(50))
        __mapper_args__ = {'polymorphic_on': discriminator}

    # This is single table inheritance
    class Engineer(Person):
        primary_language = Column(String(50))
        __mapper_args__ = {'polymorphic_identity': 'engineer'}

    # This is joined table inheritance
    class Manager(Tablename, Person):
        id = Column(Integer, ForeignKey('person.id'), primary_key=True)
        preferred_recreation = Column(String(50))
        __mapper_args__ = {'polymorphic_identity': 'engineer'}

Combining Table/Mapper Arguments from Multiple Mixins
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In the case of ``__table_args__`` or ``__mapper_args__``
specified with declarative mixins, you may want to combine
some parameters from several mixins with those you wish to
define on the class iteself. The
:class:`.declared_attr` decorator can be used
here to create user-defined collation routines that pull
from multiple collections::

    from sqlalchemy.ext.declarative import declared_attr

    class MySQLSettings(object):
        __table_args__ = {'mysql_engine':'InnoDB'}

    class MyOtherMixin(object):
        __table_args__ = {'info':'foo'}

    class MyModel(MySQLSettings, MyOtherMixin, Base):
        __tablename__='my_model'

        @declared_attr
        def __table_args__(cls):
            args = dict()
            args.update(MySQLSettings.__table_args__)
            args.update(MyOtherMixin.__table_args__)
            return args

        id =  Column(Integer, primary_key=True)

Creating Indexes with Mixins
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To define a named, potentially multicolumn :class:`.Index` that applies to all
tables derived from a mixin, use the "inline" form of :class:`.Index` and
establish it as part of ``__table_args__``::

    class MyMixin(object):
        a =  Column(Integer)
        b =  Column(Integer)

        @declared_attr
        def __table_args__(cls):
            return (Index('test_idx_%s' % cls.__tablename__, 'a', 'b'),)

    class MyModel(MyMixin, Base):
        __tablename__ = 'atable'
        c =  Column(Integer,primary_key=True)

Special Directives
==================

``__declare_last__()``
~~~~~~~~~~~~~~~~~~~~~~

The ``__declare_last__()`` hook allows definition of
a class level function that is automatically called by the
:meth:`.MapperEvents.after_configured` event, which occurs after mappings are
assumed to be completed and the 'configure' step has finished::

    class MyClass(Base):
        @classmethod
        def __declare_last__(cls):
            ""
            # do something with mappings

.. versionadded:: 0.7.3

.. _declarative_abstract:

``__abstract__``
~~~~~~~~~~~~~~~~~~~

``__abstract__`` causes declarative to skip the production
of a table or mapper for the class entirely.  A class can be added within a
hierarchy in the same way as mixin (see :ref:`declarative_mixins`), allowing
subclasses to extend just from the special class::

    class SomeAbstractBase(Base):
        __abstract__ = True

        def some_helpful_method(self):
            ""

        @declared_attr
        def __mapper_args__(cls):
            return {"helpful mapper arguments":True}

    class MyMappedClass(SomeAbstractBase):
        ""

One possible use of ``__abstract__`` is to use a distinct
:class:`.MetaData` for different bases::

    Base = declarative_base()

    class DefaultBase(Base):
        __abstract__ = True
        metadata = MetaData()

    class OtherBase(Base):
        __abstract__ = True
        metadata = MetaData()

Above, classes which inherit from ``DefaultBase`` will use one
:class:`.MetaData` as the registry of tables, and those which inherit from
``OtherBase`` will use a different one. The tables themselves can then be
created perhaps within distinct databases::

    DefaultBase.metadata.create_all(some_engine)
    OtherBase.metadata_create_all(some_other_engine)

.. versionadded:: 0.7.3

Class Constructor
=================

As a convenience feature, the :func:`declarative_base` sets a default
constructor on classes which takes keyword arguments, and assigns them
to the named attributes::

    e = Engineer(primary_language='python')

Sessions
========

Note that ``declarative`` does nothing special with sessions, and is
only intended as an easier way to configure mappers and
:class:`~sqlalchemy.schema.Table` objects.  A typical application
setup using :class:`~sqlalchemy.orm.scoped_session` might look like::

    engine = create_engine('postgresql://scott:tiger@localhost/test')
    Session = scoped_session(sessionmaker(autocommit=False,
                                          autoflush=False,
                                          bind=engine))
    Base = declarative_base()

Mapped instances then make usage of
:class:`~sqlalchemy.orm.session.Session` in the usual way.

"""

from .api import declarative_base, synonym_for, comparable_using, \
    instrument_declarative, ConcreteBase, AbstractConcreteBase, \
    DeclarativeMeta, DeferredReflection, has_inherited_table,\
    declared_attr, as_declarative


__all__ = ['declarative_base', 'synonym_for', 'has_inherited_table',
            'comparable_using', 'instrument_declarative', 'declared_attr',
            'ConcreteBase', 'AbstractConcreteBase', 'DeclarativeMeta',
            'DeferredReflection']
