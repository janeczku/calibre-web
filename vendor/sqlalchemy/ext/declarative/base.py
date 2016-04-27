# ext/declarative/base.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
"""Internal implementation for declarative."""

from ...schema import Table, Column
from ...orm import mapper, class_mapper
from ...orm.interfaces import MapperProperty
from ...orm.properties import ColumnProperty, CompositeProperty
from ...orm.util import _is_mapped_class
from ... import util, exc
from ...sql import expression
from ... import event
from . import clsregistry


def _declared_mapping_info(cls):
    # deferred mapping
    if cls in _MapperConfig.configs:
        return _MapperConfig.configs[cls]
    # regular mapping
    elif _is_mapped_class(cls):
        return class_mapper(cls, configure=False)
    else:
        return None


def _as_declarative(cls, classname, dict_):
    from .api import declared_attr

    # dict_ will be a dictproxy, which we can't write to, and we need to!
    dict_ = dict(dict_)

    column_copies = {}
    potential_columns = {}

    mapper_args_fn = None
    table_args = inherited_table_args = None
    tablename = None

    declarative_props = (declared_attr, util.classproperty)

    for base in cls.__mro__:
        _is_declarative_inherits = hasattr(base, '_decl_class_registry')

        if '__declare_last__' in base.__dict__:
            @event.listens_for(mapper, "after_configured")
            def go():
                cls.__declare_last__()
        if '__abstract__' in base.__dict__:
            if (base is cls or
                (base in cls.__bases__ and not _is_declarative_inherits)
            ):
                return

        class_mapped = _declared_mapping_info(base) is not None

        for name, obj in vars(base).items():
            if name == '__mapper_args__':
                if not mapper_args_fn and (
                                        not class_mapped or
                                        isinstance(obj, declarative_props)
                                    ):
                    # don't even invoke __mapper_args__ until
                    # after we've determined everything about the
                    # mapped table.
                    mapper_args_fn = lambda: cls.__mapper_args__
            elif name == '__tablename__':
                if not tablename and (
                                        not class_mapped or
                                        isinstance(obj, declarative_props)
                                    ):
                    tablename = cls.__tablename__
            elif name == '__table_args__':
                if not table_args and (
                                        not class_mapped or
                                        isinstance(obj, declarative_props)
                                    ):
                    table_args = cls.__table_args__
                    if not isinstance(table_args, (tuple, dict, type(None))):
                        raise exc.ArgumentError(
                                "__table_args__ value must be a tuple, "
                                "dict, or None")
                    if base is not cls:
                        inherited_table_args = True
            elif class_mapped:
                if isinstance(obj, declarative_props):
                    util.warn("Regular (i.e. not __special__) "
                            "attribute '%s.%s' uses @declared_attr, "
                            "but owning class %s is mapped - "
                            "not applying to subclass %s."
                            % (base.__name__, name, base, cls))
                continue
            elif base is not cls:
                # we're a mixin.
                if isinstance(obj, Column):
                    if getattr(cls, name) is not obj:
                        # if column has been overridden
                        # (like by the InstrumentedAttribute of the
                        # superclass), skip
                        continue
                    if obj.foreign_keys:
                        raise exc.InvalidRequestError(
                        "Columns with foreign keys to other columns "
                        "must be declared as @declared_attr callables "
                        "on declarative mixin classes. ")
                    if name not in dict_ and not (
                            '__table__' in dict_ and
                            (obj.name or name) in dict_['__table__'].c
                            ) and name not in potential_columns:
                        potential_columns[name] = \
                                column_copies[obj] = \
                                obj.copy()
                        column_copies[obj]._creation_order = \
                                obj._creation_order
                elif isinstance(obj, MapperProperty):
                    raise exc.InvalidRequestError(
                        "Mapper properties (i.e. deferred,"
                        "column_property(), relationship(), etc.) must "
                        "be declared as @declared_attr callables "
                        "on declarative mixin classes.")
                elif isinstance(obj, declarative_props):
                    dict_[name] = ret = \
                            column_copies[obj] = getattr(cls, name)
                    if isinstance(ret, (Column, MapperProperty)) and \
                        ret.doc is None:
                        ret.doc = obj.__doc__

    # apply inherited columns as we should
    for k, v in potential_columns.items():
        dict_[k] = v

    if inherited_table_args and not tablename:
        table_args = None

    clsregistry.add_class(classname, cls)
    our_stuff = util.OrderedDict()

    for k in list(dict_):

        # TODO: improve this ?  all dunders ?
        if k in ('__table__', '__tablename__', '__mapper_args__'):
            continue

        value = dict_[k]
        if isinstance(value, declarative_props):
            value = getattr(cls, k)

        if (isinstance(value, tuple) and len(value) == 1 and
            isinstance(value[0], (Column, MapperProperty))):
            util.warn("Ignoring declarative-like tuple value of attribute "
                      "%s: possibly a copy-and-paste error with a comma "
                      "left at the end of the line?" % k)
            continue
        if not isinstance(value, (Column, MapperProperty)):
            if not k.startswith('__'):
                dict_.pop(k)
                setattr(cls, k, value)
            continue
        if k == 'metadata':
            raise exc.InvalidRequestError(
                "Attribute name 'metadata' is reserved "
                "for the MetaData instance when using a "
                "declarative base class."
            )
        prop = clsregistry._deferred_relationship(cls, value)
        our_stuff[k] = prop

    # set up attributes in the order they were created
    our_stuff.sort(key=lambda key: our_stuff[key]._creation_order)

    # extract columns from the class dict
    declared_columns = set()
    for key, c in our_stuff.iteritems():
        if isinstance(c, (ColumnProperty, CompositeProperty)):
            for col in c.columns:
                if isinstance(col, Column) and \
                    col.table is None:
                    _undefer_column_name(key, col)
                    declared_columns.add(col)
        elif isinstance(c, Column):
            _undefer_column_name(key, c)
            declared_columns.add(c)
            # if the column is the same name as the key,
            # remove it from the explicit properties dict.
            # the normal rules for assigning column-based properties
            # will take over, including precedence of columns
            # in multi-column ColumnProperties.
            if key == c.key:
                del our_stuff[key]
    declared_columns = sorted(
        declared_columns, key=lambda c: c._creation_order)
    table = None

    if hasattr(cls, '__table_cls__'):
        table_cls = util.unbound_method_to_callable(cls.__table_cls__)
    else:
        table_cls = Table

    if '__table__' not in dict_:
        if tablename is not None:

            args, table_kw = (), {}
            if table_args:
                if isinstance(table_args, dict):
                    table_kw = table_args
                elif isinstance(table_args, tuple):
                    if isinstance(table_args[-1], dict):
                        args, table_kw = table_args[0:-1], table_args[-1]
                    else:
                        args = table_args

            autoload = dict_.get('__autoload__')
            if autoload:
                table_kw['autoload'] = True

            cls.__table__ = table = table_cls(
                tablename, cls.metadata,
                *(tuple(declared_columns) + tuple(args)),
                **table_kw)
    else:
        table = cls.__table__
        if declared_columns:
            for c in declared_columns:
                if not table.c.contains_column(c):
                    raise exc.ArgumentError(
                        "Can't add additional column %r when "
                        "specifying __table__" % c.key
                    )

    if hasattr(cls, '__mapper_cls__'):
        mapper_cls = util.unbound_method_to_callable(cls.__mapper_cls__)
    else:
        mapper_cls = mapper

    for c in cls.__bases__:
        if _declared_mapping_info(c) is not None:
            inherits = c
            break
    else:
        inherits = None

    if table is None and inherits is None:
        raise exc.InvalidRequestError(
            "Class %r does not have a __table__ or __tablename__ "
            "specified and does not inherit from an existing "
            "table-mapped class." % cls
            )
    elif inherits:
        inherited_mapper = _declared_mapping_info(inherits)
        inherited_table = inherited_mapper.local_table
        inherited_mapped_table = inherited_mapper.mapped_table

        if table is None:
            # single table inheritance.
            # ensure no table args
            if table_args:
                raise exc.ArgumentError(
                    "Can't place __table_args__ on an inherited class "
                    "with no table."
                    )
            # add any columns declared here to the inherited table.
            for c in declared_columns:
                if c.primary_key:
                    raise exc.ArgumentError(
                        "Can't place primary key columns on an inherited "
                        "class with no table."
                        )
                if c.name in inherited_table.c:
                    if inherited_table.c[c.name] is c:
                        continue
                    raise exc.ArgumentError(
                        "Column '%s' on class %s conflicts with "
                        "existing column '%s'" %
                        (c, cls, inherited_table.c[c.name])
                    )
                inherited_table.append_column(c)
                if inherited_mapped_table is not None and \
                    inherited_mapped_table is not inherited_table:
                    inherited_mapped_table._refresh_for_new_column(c)

    mt = _MapperConfig(mapper_cls,
                       cls, table,
                       inherits,
                       declared_columns,
                       column_copies,
                       our_stuff,
                       mapper_args_fn)
    if not hasattr(cls, '_sa_decl_prepare'):
        mt.map()


class _MapperConfig(object):
    configs = util.OrderedDict()
    mapped_table = None

    def __init__(self, mapper_cls,
                        cls,
                        table,
                        inherits,
                        declared_columns,
                        column_copies,
                        properties, mapper_args_fn):
        self.mapper_cls = mapper_cls
        self.cls = cls
        self.local_table = table
        self.inherits = inherits
        self.properties = properties
        self.mapper_args_fn = mapper_args_fn
        self.declared_columns = declared_columns
        self.column_copies = column_copies
        self.configs[cls] = self

    def _prepare_mapper_arguments(self):
        properties = self.properties
        if self.mapper_args_fn:
            mapper_args = self.mapper_args_fn()
        else:
            mapper_args = {}

        # make sure that column copies are used rather
        # than the original columns from any mixins
        for k in ('version_id_col', 'polymorphic_on',):
            if k in mapper_args:
                v = mapper_args[k]
                mapper_args[k] = self.column_copies.get(v, v)

        assert 'inherits' not in mapper_args, \
            "Can't specify 'inherits' explicitly with declarative mappings"

        if self.inherits:
            mapper_args['inherits'] = self.inherits

        if self.inherits and not mapper_args.get('concrete', False):
            # single or joined inheritance
            # exclude any cols on the inherited table which are
            # not mapped on the parent class, to avoid
            # mapping columns specific to sibling/nephew classes
            inherited_mapper = _declared_mapping_info(self.inherits)
            inherited_table = inherited_mapper.local_table

            if 'exclude_properties' not in mapper_args:
                mapper_args['exclude_properties'] = exclude_properties = \
                    set([c.key for c in inherited_table.c
                         if c not in inherited_mapper._columntoproperty])
                exclude_properties.difference_update(
                        [c.key for c in self.declared_columns])

            # look through columns in the current mapper that
            # are keyed to a propname different than the colname
            # (if names were the same, we'd have popped it out above,
            # in which case the mapper makes this combination).
            # See if the superclass has a similar column property.
            # If so, join them together.
            for k, col in properties.items():
                if not isinstance(col, expression.ColumnElement):
                    continue
                if k in inherited_mapper._props:
                    p = inherited_mapper._props[k]
                    if isinstance(p, ColumnProperty):
                        # note here we place the subclass column
                        # first.  See [ticket:1892] for background.
                        properties[k] = [col] + p.columns
        result_mapper_args = mapper_args.copy()
        result_mapper_args['properties'] = properties
        return result_mapper_args

    def map(self):
        self.configs.pop(self.cls, None)
        mapper_args = self._prepare_mapper_arguments()
        self.cls.__mapper__ = self.mapper_cls(
            self.cls,
            self.local_table,
            **mapper_args
        )


def _add_attribute(cls, key, value):
    """add an attribute to an existing declarative class.

    This runs through the logic to determine MapperProperty,
    adds it to the Mapper, adds a column to the mapped Table, etc.

    """
    if '__mapper__' in cls.__dict__:
        if isinstance(value, Column):
            _undefer_column_name(key, value)
            cls.__table__.append_column(value)
            cls.__mapper__.add_property(key, value)
        elif isinstance(value, ColumnProperty):
            for col in value.columns:
                if isinstance(col, Column) and col.table is None:
                    _undefer_column_name(key, col)
                    cls.__table__.append_column(col)
            cls.__mapper__.add_property(key, value)
        elif isinstance(value, MapperProperty):
            cls.__mapper__.add_property(
                key,
                clsregistry._deferred_relationship(cls, value)
            )
        else:
            type.__setattr__(cls, key, value)
    else:
        type.__setattr__(cls, key, value)


def _declarative_constructor(self, **kwargs):
    """A simple constructor that allows initialization from kwargs.

    Sets attributes on the constructed instance using the names and
    values in ``kwargs``.

    Only keys that are present as
    attributes of the instance's class are allowed. These could be,
    for example, any mapped columns or relationships.
    """
    cls_ = type(self)
    for k in kwargs:
        if not hasattr(cls_, k):
            raise TypeError(
                "%r is an invalid keyword argument for %s" %
                (k, cls_.__name__))
        setattr(self, k, kwargs[k])
_declarative_constructor.__name__ = '__init__'


def _undefer_column_name(key, column):
    if column.key is None:
        column.key = key
    if column.name is None:
        column.name = key
