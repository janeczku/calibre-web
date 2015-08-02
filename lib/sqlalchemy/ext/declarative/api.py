# ext/declarative/api.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
"""Public API functions and helpers for declarative."""


from ...schema import Table, MetaData
from ...orm import synonym as _orm_synonym, mapper,\
                                comparable_property,\
                                interfaces
from ...orm.util import polymorphic_union, _mapper_or_none
from ... import exc
import weakref

from .base import _as_declarative, \
                _declarative_constructor,\
                _MapperConfig, _add_attribute


def instrument_declarative(cls, registry, metadata):
    """Given a class, configure the class declaratively,
    using the given registry, which can be any dictionary, and
    MetaData object.

    """
    if '_decl_class_registry' in cls.__dict__:
        raise exc.InvalidRequestError(
                            "Class %r already has been "
                            "instrumented declaratively" % cls)
    cls._decl_class_registry = registry
    cls.metadata = metadata
    _as_declarative(cls, cls.__name__, cls.__dict__)


def has_inherited_table(cls):
    """Given a class, return True if any of the classes it inherits from has a
    mapped table, otherwise return False.
    """
    for class_ in cls.__mro__[1:]:
        if getattr(class_, '__table__', None) is not None:
            return True
    return False


class DeclarativeMeta(type):
    def __init__(cls, classname, bases, dict_):
        if '_decl_class_registry' not in cls.__dict__:
            _as_declarative(cls, classname, cls.__dict__)
        type.__init__(cls, classname, bases, dict_)

    def __setattr__(cls, key, value):
        _add_attribute(cls, key, value)


def synonym_for(name, map_column=False):
    """Decorator, make a Python @property a query synonym for a column.

    A decorator version of :func:`~sqlalchemy.orm.synonym`. The function being
    decorated is the 'descriptor', otherwise passes its arguments through to
    synonym()::

      @synonym_for('col')
      @property
      def prop(self):
          return 'special sauce'

    The regular ``synonym()`` is also usable directly in a declarative setting
    and may be convenient for read/write properties::

      prop = synonym('col', descriptor=property(_read_prop, _write_prop))

    """
    def decorate(fn):
        return _orm_synonym(name, map_column=map_column, descriptor=fn)
    return decorate


def comparable_using(comparator_factory):
    """Decorator, allow a Python @property to be used in query criteria.

    This is a  decorator front end to
    :func:`~sqlalchemy.orm.comparable_property` that passes
    through the comparator_factory and the function being decorated::

      @comparable_using(MyComparatorType)
      @property
      def prop(self):
          return 'special sauce'

    The regular ``comparable_property()`` is also usable directly in a
    declarative setting and may be convenient for read/write properties::

      prop = comparable_property(MyComparatorType)

    """
    def decorate(fn):
        return comparable_property(comparator_factory, fn)
    return decorate


class declared_attr(interfaces._MappedAttribute, property):
    """Mark a class-level method as representing the definition of
    a mapped property or special declarative member name.

    @declared_attr turns the attribute into a scalar-like
    property that can be invoked from the uninstantiated class.
    Declarative treats attributes specifically marked with
    @declared_attr as returning a construct that is specific
    to mapping or declarative table configuration.  The name
    of the attribute is that of what the non-dynamic version
    of the attribute would be.

    @declared_attr is more often than not applicable to mixins,
    to define relationships that are to be applied to different
    implementors of the class::

        class ProvidesUser(object):
            "A mixin that adds a 'user' relationship to classes."

            @declared_attr
            def user(self):
                return relationship("User")

    It also can be applied to mapped classes, such as to provide
    a "polymorphic" scheme for inheritance::

        class Employee(Base):
            id = Column(Integer, primary_key=True)
            type = Column(String(50), nullable=False)

            @declared_attr
            def __tablename__(cls):
                return cls.__name__.lower()

            @declared_attr
            def __mapper_args__(cls):
                if cls.__name__ == 'Employee':
                    return {
                            "polymorphic_on":cls.type,
                            "polymorphic_identity":"Employee"
                    }
                else:
                    return {"polymorphic_identity":cls.__name__}

    .. versionchanged:: 0.8 :class:`.declared_attr` can be used with
       non-ORM or extension attributes, such as user-defined attributes
       or :func:`.association_proxy` objects, which will be assigned
       to the class at class construction time.


    """

    def __init__(self, fget, *arg, **kw):
        super(declared_attr, self).__init__(fget, *arg, **kw)
        self.__doc__ = fget.__doc__

    def __get__(desc, self, cls):
        return desc.fget(cls)


def declarative_base(bind=None, metadata=None, mapper=None, cls=object,
                     name='Base', constructor=_declarative_constructor,
                     class_registry=None,
                     metaclass=DeclarativeMeta):
    """Construct a base class for declarative class definitions.

    The new base class will be given a metaclass that produces
    appropriate :class:`~sqlalchemy.schema.Table` objects and makes
    the appropriate :func:`~sqlalchemy.orm.mapper` calls based on the
    information provided declaratively in the class and any subclasses
    of the class.

    :param bind: An optional
      :class:`~sqlalchemy.engine.base.Connectable`, will be assigned
      the ``bind`` attribute on the :class:`~sqlalchemy.MetaData`
      instance.

    :param metadata:
      An optional :class:`~sqlalchemy.MetaData` instance.  All
      :class:`~sqlalchemy.schema.Table` objects implicitly declared by
      subclasses of the base will share this MetaData.  A MetaData instance
      will be created if none is provided.  The
      :class:`~sqlalchemy.MetaData` instance will be available via the
      `metadata` attribute of the generated declarative base class.

    :param mapper:
      An optional callable, defaults to :func:`~sqlalchemy.orm.mapper`. Will
      be used to map subclasses to their Tables.

    :param cls:
      Defaults to :class:`object`. A type to use as the base for the generated
      declarative base class. May be a class or tuple of classes.

    :param name:
      Defaults to ``Base``.  The display name for the generated
      class.  Customizing this is not required, but can improve clarity in
      tracebacks and debugging.

    :param constructor:
      Defaults to
      :func:`~sqlalchemy.ext.declarative._declarative_constructor`, an
      __init__ implementation that assigns \**kwargs for declared
      fields and relationships to an instance.  If ``None`` is supplied,
      no __init__ will be provided and construction will fall back to
      cls.__init__ by way of the normal Python semantics.

    :param class_registry: optional dictionary that will serve as the
      registry of class names-> mapped classes when string names
      are used to identify classes inside of :func:`.relationship`
      and others.  Allows two or more declarative base classes
      to share the same registry of class names for simplified
      inter-base relationships.

    :param metaclass:
      Defaults to :class:`.DeclarativeMeta`.  A metaclass or __metaclass__
      compatible callable to use as the meta type of the generated
      declarative base class.

    .. seealso::

        :func:`.as_declarative`

    """
    lcl_metadata = metadata or MetaData()
    if bind:
        lcl_metadata.bind = bind

    if class_registry is None:
        class_registry = weakref.WeakValueDictionary()

    bases = not isinstance(cls, tuple) and (cls,) or cls
    class_dict = dict(_decl_class_registry=class_registry,
                      metadata=lcl_metadata)

    if constructor:
        class_dict['__init__'] = constructor
    if mapper:
        class_dict['__mapper_cls__'] = mapper

    return metaclass(name, bases, class_dict)

def as_declarative(**kw):
    """
    Class decorator for :func:`.declarative_base`.

    Provides a syntactical shortcut to the ``cls`` argument
    sent to :func:`.declarative_base`, allowing the base class
    to be converted in-place to a "declarative" base::

        from sqlalchemy.ext.declarative import as_declarative

        @as_declarative()
        class Base(object)
            @declared_attr
            def __tablename__(cls):
                return cls.__name__.lower()
            id = Column(Integer, primary_key=True)

        class MyMappedClass(Base):
            # ...

    All keyword arguments passed to :func:`.as_declarative` are passed
    along to :func:`.declarative_base`.

    .. versionadded:: 0.8.3

    .. seealso::

        :func:`.declarative_base`

    """
    def decorate(cls):
        kw['cls'] = cls
        kw['name'] = cls.__name__
        return declarative_base(**kw)

    return decorate

class ConcreteBase(object):
    """A helper class for 'concrete' declarative mappings.

    :class:`.ConcreteBase` will use the :func:`.polymorphic_union`
    function automatically, against all tables mapped as a subclass
    to this class.   The function is called via the
    ``__declare_last__()`` function, which is essentially
    a hook for the :func:`.MapperEvents.after_configured` event.

    :class:`.ConcreteBase` produces a mapped
    table for the class itself.  Compare to :class:`.AbstractConcreteBase`,
    which does not.

    Example::

        from sqlalchemy.ext.declarative import ConcreteBase

        class Employee(ConcreteBase, Base):
            __tablename__ = 'employee'
            employee_id = Column(Integer, primary_key=True)
            name = Column(String(50))
            __mapper_args__ = {
                            'polymorphic_identity':'employee',
                            'concrete':True}

        class Manager(Employee):
            __tablename__ = 'manager'
            employee_id = Column(Integer, primary_key=True)
            name = Column(String(50))
            manager_data = Column(String(40))
            __mapper_args__ = {
                            'polymorphic_identity':'manager',
                            'concrete':True}

    """

    @classmethod
    def _create_polymorphic_union(cls, mappers):
        return polymorphic_union(dict(
            (mp.polymorphic_identity, mp.local_table)
            for mp in mappers
         ), 'type', 'pjoin')

    @classmethod
    def __declare_last__(cls):
        m = cls.__mapper__
        if m.with_polymorphic:
            return

        mappers = list(m.self_and_descendants)
        pjoin = cls._create_polymorphic_union(mappers)
        m._set_with_polymorphic(("*", pjoin))
        m._set_polymorphic_on(pjoin.c.type)


class AbstractConcreteBase(ConcreteBase):
    """A helper class for 'concrete' declarative mappings.

    :class:`.AbstractConcreteBase` will use the :func:`.polymorphic_union`
    function automatically, against all tables mapped as a subclass
    to this class.   The function is called via the
    ``__declare_last__()`` function, which is essentially
    a hook for the :func:`.MapperEvents.after_configured` event.

    :class:`.AbstractConcreteBase` does not produce a mapped
    table for the class itself.  Compare to :class:`.ConcreteBase`,
    which does.

    Example::

        from sqlalchemy.ext.declarative import AbstractConcreteBase

        class Employee(AbstractConcreteBase, Base):
            pass

        class Manager(Employee):
            __tablename__ = 'manager'
            employee_id = Column(Integer, primary_key=True)
            name = Column(String(50))
            manager_data = Column(String(40))
            __mapper_args__ = {
                            'polymorphic_identity':'manager',
                            'concrete':True}

    """

    __abstract__ = True

    @classmethod
    def __declare_last__(cls):
        if hasattr(cls, '__mapper__'):
            return

        # can't rely on 'self_and_descendants' here
        # since technically an immediate subclass
        # might not be mapped, but a subclass
        # may be.
        mappers = []
        stack = list(cls.__subclasses__())
        while stack:
            klass = stack.pop()
            stack.extend(klass.__subclasses__())
            mn = _mapper_or_none(klass)
            if mn is not None:
                mappers.append(mn)
        pjoin = cls._create_polymorphic_union(mappers)
        cls.__mapper__ = m = mapper(cls, pjoin, polymorphic_on=pjoin.c.type)

        for scls in cls.__subclasses__():
            sm = _mapper_or_none(scls)
            if sm.concrete and cls in scls.__bases__:
                sm._set_concrete_base(m)


class DeferredReflection(object):
    """A helper class for construction of mappings based on
    a deferred reflection step.

    Normally, declarative can be used with reflection by
    setting a :class:`.Table` object using autoload=True
    as the ``__table__`` attribute on a declarative class.
    The caveat is that the :class:`.Table` must be fully
    reflected, or at the very least have a primary key column,
    at the point at which a normal declarative mapping is
    constructed, meaning the :class:`.Engine` must be available
    at class declaration time.

    The :class:`.DeferredReflection` mixin moves the construction
    of mappers to be at a later point, after a specific
    method is called which first reflects all :class:`.Table`
    objects created so far.   Classes can define it as such::

        from sqlalchemy.ext.declarative import declarative_base
        from sqlalchemy.ext.declarative import DeferredReflection
        Base = declarative_base()

        class MyClass(DeferredReflection, Base):
            __tablename__ = 'mytable'

    Above, ``MyClass`` is not yet mapped.   After a series of
    classes have been defined in the above fashion, all tables
    can be reflected and mappings created using
    :meth:`.DeferredReflection.prepare`::

        engine = create_engine("someengine://...")
        DeferredReflection.prepare(engine)

    The :class:`.DeferredReflection` mixin can be applied to individual
    classes, used as the base for the declarative base itself,
    or used in a custom abstract class.   Using an abstract base
    allows that only a subset of classes to be prepared for a
    particular prepare step, which is necessary for applications
    that use more than one engine.  For example, if an application
    has two engines, you might use two bases, and prepare each
    separately, e.g.::

        class ReflectedOne(DeferredReflection, Base):
            __abstract__ = True

        class ReflectedTwo(DeferredReflection, Base):
            __abstract__ = True

        class MyClass(ReflectedOne):
            __tablename__ = 'mytable'

        class MyOtherClass(ReflectedOne):
            __tablename__ = 'myothertable'

        class YetAnotherClass(ReflectedTwo):
            __tablename__ = 'yetanothertable'

        # ... etc.

    Above, the class hierarchies for ``ReflectedOne`` and
    ``ReflectedTwo`` can be configured separately::

        ReflectedOne.prepare(engine_one)
        ReflectedTwo.prepare(engine_two)

    .. versionadded:: 0.8

    """
    @classmethod
    def prepare(cls, engine):
        """Reflect all :class:`.Table` objects for all current
        :class:`.DeferredReflection` subclasses"""
        to_map = [m for m in _MapperConfig.configs.values()
                    if issubclass(m.cls, cls)]
        for thingy in to_map:
            cls._sa_decl_prepare(thingy.local_table, engine)
            thingy.map()

    @classmethod
    def _sa_decl_prepare(cls, local_table, engine):
        # autoload Table, which is already
        # present in the metadata.  This
        # will fill in db-loaded columns
        # into the existing Table object.
        if local_table is not None:
            Table(local_table.name,
                local_table.metadata,
                extend_existing=True,
                autoload_replace=False,
                autoload=True,
                autoload_with=engine,
                schema=local_table.schema)
