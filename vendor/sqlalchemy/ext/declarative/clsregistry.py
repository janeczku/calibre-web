# ext/declarative/clsregistry.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
"""Routines to handle the string class registry used by declarative.

This system allows specification of classes and expressions used in
:func:`.relationship` using strings.

"""
from ...orm.properties import ColumnProperty, RelationshipProperty, \
                            SynonymProperty
from ...schema import _get_table_key
from ...orm import class_mapper, interfaces
from ... import util
from ... import exc
import weakref

# strong references to registries which we place in
# the _decl_class_registry, which is usually weak referencing.
# the internal registries here link to classes with weakrefs and remove
# themselves when all references to contained classes are removed.
_registries = set()


def add_class(classname, cls):
    """Add a class to the _decl_class_registry associated with the
    given declarative class.

    """
    if classname in cls._decl_class_registry:
        # class already exists.
        existing = cls._decl_class_registry[classname]
        if not isinstance(existing, _MultipleClassMarker):
            existing = \
                cls._decl_class_registry[classname] = \
                _MultipleClassMarker([cls, existing])
    else:
        cls._decl_class_registry[classname] = cls

    try:
        root_module = cls._decl_class_registry['_sa_module_registry']
    except KeyError:
        cls._decl_class_registry['_sa_module_registry'] = \
            root_module = _ModuleMarker('_sa_module_registry', None)

    tokens = cls.__module__.split(".")

    # build up a tree like this:
    # modulename:  myapp.snacks.nuts
    #
    # myapp->snack->nuts->(classes)
    # snack->nuts->(classes)
    # nuts->(classes)
    #
    # this allows partial token paths to be used.
    while tokens:
        token = tokens.pop(0)
        module = root_module.get_module(token)
        for token in tokens:
            module = module.get_module(token)
        module.add_class(classname, cls)


class _MultipleClassMarker(object):
    """refers to multiple classes of the same name
    within _decl_class_registry.

    """

    def __init__(self, classes, on_remove=None):
        self.on_remove = on_remove
        self.contents = set([
                weakref.ref(item, self._remove_item) for item in classes])
        _registries.add(self)

    def __iter__(self):
        return (ref() for ref in self.contents)

    def attempt_get(self, path, key):
        if len(self.contents) > 1:
            raise exc.InvalidRequestError(
                "Multiple classes found for path \"%s\" "
                "in the registry of this declarative "
                "base. Please use a fully module-qualified path." %
                (".".join(path + [key]))
            )
        else:
            ref = list(self.contents)[0]
            cls = ref()
            if cls is None:
                raise NameError(key)
            return cls

    def _remove_item(self, ref):
        self.contents.remove(ref)
        if not self.contents:
            _registries.discard(self)
            if self.on_remove:
                self.on_remove()

    def add_item(self, item):
        modules = set([cls().__module__ for cls in self.contents])
        if item.__module__ in modules:
            util.warn(
                "This declarative base already contains a class with the "
                "same class name and module name as %s.%s, and will "
                "be replaced in the string-lookup table." % (
                    item.__module__,
                    item.__name__
                )
            )
        self.contents.add(weakref.ref(item, self._remove_item))


class _ModuleMarker(object):
    """"refers to a module name within
    _decl_class_registry.

    """
    def __init__(self, name, parent):
        self.parent = parent
        self.name = name
        self.contents = {}
        self.mod_ns = _ModNS(self)
        if self.parent:
            self.path = self.parent.path + [self.name]
        else:
            self.path = []
        _registries.add(self)

    def __contains__(self, name):
        return name in self.contents

    def __getitem__(self, name):
        return self.contents[name]

    def _remove_item(self, name):
        self.contents.pop(name, None)
        if not self.contents and self.parent is not None:
            self.parent._remove_item(self.name)
            _registries.discard(self)

    def resolve_attr(self, key):
        return getattr(self.mod_ns, key)

    def get_module(self, name):
        if name not in self.contents:
            marker = _ModuleMarker(name, self)
            self.contents[name] = marker
        else:
            marker = self.contents[name]
        return marker

    def add_class(self, name, cls):
        if name in self.contents:
            existing = self.contents[name]
            existing.add_item(cls)
        else:
            existing = self.contents[name] = \
                    _MultipleClassMarker([cls],
                        on_remove=lambda: self._remove_item(name))


class _ModNS(object):
    def __init__(self, parent):
        self.__parent = parent

    def __getattr__(self, key):
        try:
            value = self.__parent.contents[key]
        except KeyError:
            pass
        else:
            if value is not None:
                if isinstance(value, _ModuleMarker):
                    return value.mod_ns
                else:
                    assert isinstance(value, _MultipleClassMarker)
                    return value.attempt_get(self.__parent.path, key)
        raise AttributeError("Module %r has no mapped classes "
                    "registered under the name %r" % (self.__parent.name, key))


class _GetColumns(object):
    def __init__(self, cls):
        self.cls = cls

    def __getattr__(self, key):
        mp = class_mapper(self.cls, configure=False)
        if mp:
            if key not in mp.all_orm_descriptors:
                raise exc.InvalidRequestError(
                            "Class %r does not have a mapped column named %r"
                            % (self.cls, key))

            desc = mp.all_orm_descriptors[key]
            if desc.extension_type is interfaces.NOT_EXTENSION:
                prop = desc.property
                if isinstance(prop, SynonymProperty):
                    key = prop.name
                elif not isinstance(prop, ColumnProperty):
                    raise exc.InvalidRequestError(
                                "Property %r is not an instance of"
                                " ColumnProperty (i.e. does not correspond"
                                " directly to a Column)." % key)
        return getattr(self.cls, key)


class _GetTable(object):
    def __init__(self, key, metadata):
        self.key = key
        self.metadata = metadata

    def __getattr__(self, key):
        return self.metadata.tables[
                _get_table_key(key, self.key)
            ]


def _determine_container(key, value):
    if isinstance(value, _MultipleClassMarker):
        value = value.attempt_get([], key)
    return _GetColumns(value)


def _resolver(cls, prop):
    def resolve_arg(arg):
        import sqlalchemy
        from sqlalchemy.orm import foreign, remote

        fallback = sqlalchemy.__dict__.copy()
        fallback.update({'foreign': foreign, 'remote': remote})

        def access_cls(key):
            if key in cls._decl_class_registry:
                return _determine_container(key, cls._decl_class_registry[key])
            elif key in cls.metadata.tables:
                return cls.metadata.tables[key]
            elif key in cls.metadata._schemas:
                return _GetTable(key, cls.metadata)
            elif '_sa_module_registry' in cls._decl_class_registry and \
                key in cls._decl_class_registry['_sa_module_registry']:
                registry = cls._decl_class_registry['_sa_module_registry']
                return registry.resolve_attr(key)
            else:
                return fallback[key]

        d = util.PopulateDict(access_cls)

        def return_cls():
            try:
                x = eval(arg, globals(), d)

                if isinstance(x, _GetColumns):
                    return x.cls
                else:
                    return x
            except NameError, n:
                raise exc.InvalidRequestError(
                    "When initializing mapper %s, expression %r failed to "
                    "locate a name (%r). If this is a class name, consider "
                    "adding this relationship() to the %r class after "
                    "both dependent classes have been defined." %
                    (prop.parent, arg, n.args[0], cls)
                )
        return return_cls
    return resolve_arg


def _deferred_relationship(cls, prop):

    if isinstance(prop, RelationshipProperty):
        resolve_arg = _resolver(cls, prop)

        for attr in ('argument', 'order_by', 'primaryjoin', 'secondaryjoin',
                     'secondary', '_user_defined_foreign_keys', 'remote_side'):
            v = getattr(prop, attr)
            if isinstance(v, basestring):
                setattr(prop, attr, resolve_arg(v))

        if prop.backref and isinstance(prop.backref, tuple):
            key, kwargs = prop.backref
            for attr in ('primaryjoin', 'secondaryjoin', 'secondary',
                         'foreign_keys', 'remote_side', 'order_by'):
                if attr in kwargs and isinstance(kwargs[attr], basestring):
                    kwargs[attr] = resolve_arg(kwargs[attr])

    return prop
