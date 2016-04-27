# orm/util.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php


from .. import sql, util, event, exc as sa_exc, inspection
from ..sql import expression, util as sql_util, operators
from .interfaces import PropComparator, MapperProperty, _InspectionAttr
from itertools import chain
from . import attributes, exc
import re

mapperlib = util.importlater("sqlalchemy.orm", "mapperlib")

all_cascades = frozenset(("delete", "delete-orphan", "all", "merge",
                          "expunge", "save-update", "refresh-expire",
                          "none"))

_INSTRUMENTOR = ('mapper', 'instrumentor')

_none_set = frozenset([None])


class CascadeOptions(frozenset):
    """Keeps track of the options sent to relationship().cascade"""

    _add_w_all_cascades = all_cascades.difference([
                            'all', 'none', 'delete-orphan'])
    _allowed_cascades = all_cascades

    def __new__(cls, arg):
        values = set([
                    c for c
                    in re.split('\s*,\s*', arg or "")
                    if c
                ])

        if values.difference(cls._allowed_cascades):
            raise sa_exc.ArgumentError(
                    "Invalid cascade option(s): %s" %
                    ", ".join([repr(x) for x in
                        sorted(
                            values.difference(cls._allowed_cascades)
                    )])
            )

        if "all" in values:
            values.update(cls._add_w_all_cascades)
        if "none" in values:
            values.clear()
        values.discard('all')

        self = frozenset.__new__(CascadeOptions, values)
        self.save_update = 'save-update' in values
        self.delete = 'delete' in values
        self.refresh_expire = 'refresh-expire' in values
        self.merge = 'merge' in values
        self.expunge = 'expunge' in values
        self.delete_orphan = "delete-orphan" in values

        if self.delete_orphan and not self.delete:
            util.warn("The 'delete-orphan' cascade "
                        "option requires 'delete'.")
        return self

    def __repr__(self):
        return "CascadeOptions(%r)" % (
            ",".join([x for x in sorted(self)])
        )


def _validator_events(desc, key, validator, include_removes):
    """Runs a validation method on an attribute value to be set or appended."""

    if include_removes:
        def append(state, value, initiator):
            return validator(state.obj(), key, value, False)

        def set_(state, value, oldvalue, initiator):
            return validator(state.obj(), key, value, False)

        def remove(state, value, initiator):
            validator(state.obj(), key, value, True)
    else:
        def append(state, value, initiator):
            return validator(state.obj(), key, value)

        def set_(state, value, oldvalue, initiator):
            return validator(state.obj(), key, value)

    event.listen(desc, 'append', append, raw=True, retval=True)
    event.listen(desc, 'set', set_, raw=True, retval=True)
    if include_removes:
        event.listen(desc, "remove", remove, raw=True, retval=True)


def polymorphic_union(table_map, typecolname,
                        aliasname='p_union', cast_nulls=True):
    """Create a ``UNION`` statement used by a polymorphic mapper.

    See  :ref:`concrete_inheritance` for an example of how
    this is used.

    :param table_map: mapping of polymorphic identities to
     :class:`.Table` objects.
    :param typecolname: string name of a "discriminator" column, which will be
     derived from the query, producing the polymorphic identity for
     each row.  If ``None``, no polymorphic discriminator is generated.
    :param aliasname: name of the :func:`~sqlalchemy.sql.expression.alias()`
     construct generated.
    :param cast_nulls: if True, non-existent columns, which are represented
     as labeled NULLs, will be passed into CAST.   This is a legacy behavior
     that is problematic on some backends such as Oracle - in which case it
     can be set to False.

    """

    colnames = util.OrderedSet()
    colnamemaps = {}
    types = {}
    for key in table_map.keys():
        table = table_map[key]

        # mysql doesnt like selecting from a select;
        # make it an alias of the select
        if isinstance(table, sql.Select):
            table = table.alias()
            table_map[key] = table

        m = {}
        for c in table.c:
            colnames.add(c.key)
            m[c.key] = c
            types[c.key] = c.type
        colnamemaps[table] = m

    def col(name, table):
        try:
            return colnamemaps[table][name]
        except KeyError:
            if cast_nulls:
                return sql.cast(sql.null(), types[name]).label(name)
            else:
                return sql.type_coerce(sql.null(), types[name]).label(name)

    result = []
    for type, table in table_map.iteritems():
        if typecolname is not None:
            result.append(
                    sql.select([col(name, table) for name in colnames] +
                    [sql.literal_column(sql_util._quote_ddl_expr(type)).
                            label(typecolname)],
                             from_obj=[table]))
        else:
            result.append(sql.select([col(name, table) for name in colnames],
                                     from_obj=[table]))
    return sql.union_all(*result).alias(aliasname)


def identity_key(*args, **kwargs):
    """Get an identity key.

    Valid call signatures:

    * ``identity_key(class, ident)``

      class
          mapped class (must be a positional argument)

      ident
          primary key, if the key is composite this is a tuple


    * ``identity_key(instance=instance)``

      instance
          object instance (must be given as a keyword arg)

    * ``identity_key(class, row=row)``

      class
          mapped class (must be a positional argument)

      row
          result proxy row (must be given as a keyword arg)

    """
    if args:
        if len(args) == 1:
            class_ = args[0]
            try:
                row = kwargs.pop("row")
            except KeyError:
                ident = kwargs.pop("ident")
        elif len(args) == 2:
            class_, ident = args
        elif len(args) == 3:
            class_, ident = args
        else:
            raise sa_exc.ArgumentError("expected up to three "
                "positional arguments, got %s" % len(args))
        if kwargs:
            raise sa_exc.ArgumentError("unknown keyword arguments: %s"
                % ", ".join(kwargs.keys()))
        mapper = class_mapper(class_)
        if "ident" in locals():
            return mapper.identity_key_from_primary_key(util.to_list(ident))
        return mapper.identity_key_from_row(row)
    instance = kwargs.pop("instance")
    if kwargs:
        raise sa_exc.ArgumentError("unknown keyword arguments: %s"
            % ", ".join(kwargs.keys()))
    mapper = object_mapper(instance)
    return mapper.identity_key_from_instance(instance)


class ORMAdapter(sql_util.ColumnAdapter):
    """Extends ColumnAdapter to accept ORM entities.

    The selectable is extracted from the given entity,
    and the AliasedClass if any is referenced.

    """
    def __init__(self, entity, equivalents=None,
                            chain_to=None, adapt_required=False):
        info = inspection.inspect(entity)

        self.mapper = info.mapper
        selectable = info.selectable
        is_aliased_class = info.is_aliased_class
        if is_aliased_class:
            self.aliased_class = entity
        else:
            self.aliased_class = None
        sql_util.ColumnAdapter.__init__(self, selectable,
                                        equivalents, chain_to,
                                        adapt_required=adapt_required)

    def replace(self, elem):
        entity = elem._annotations.get('parentmapper', None)
        if not entity or entity.isa(self.mapper):
            return sql_util.ColumnAdapter.replace(self, elem)
        else:
            return None

def _unreduce_path(path):
    return PathRegistry.deserialize(path)

class PathRegistry(object):
    """Represent query load paths and registry functions.

    Basically represents structures like:

    (<User mapper>, "orders", <Order mapper>, "items", <Item mapper>)

    These structures are generated by things like
    query options (joinedload(), subqueryload(), etc.) and are
    used to compose keys stored in the query._attributes dictionary
    for various options.

    They are then re-composed at query compile/result row time as
    the query is formed and as rows are fetched, where they again
    serve to compose keys to look up options in the context.attributes
    dictionary, which is copied from query._attributes.

    The path structure has a limited amount of caching, where each
    "root" ultimately pulls from a fixed registry associated with
    the first mapper, that also contains elements for each of its
    property keys.  However paths longer than two elements, which
    are the exception rather than the rule, are generated on an
    as-needed basis.

    """

    def __eq__(self, other):
        return other is not None and \
            self.path == other.path

    def set(self, reg, key, value):
        reg._attributes[(key, self.path)] = value

    def setdefault(self, reg, key, value):
        reg._attributes.setdefault((key, self.path), value)

    def get(self, reg, key, value=None):
        key = (key, self.path)
        if key in reg._attributes:
            return reg._attributes[key]
        else:
            return value

    def __len__(self):
        return len(self.path)

    @property
    def length(self):
        return len(self.path)

    def pairs(self):
        path = self.path
        for i in xrange(0, len(path), 2):
            yield path[i], path[i + 1]

    def contains_mapper(self, mapper):
        for path_mapper in [
            self.path[i] for i in range(0, len(self.path), 2)
        ]:
            if isinstance(path_mapper, mapperlib.Mapper) and \
                path_mapper.isa(mapper):
                return True
        else:
            return False

    def contains(self, reg, key):
        return (key, self.path) in reg._attributes

    def __reduce__(self):
        return _unreduce_path, (self.serialize(), )

    def serialize(self):
        path = self.path
        return zip(
            [m.class_ for m in [path[i] for i in range(0, len(path), 2)]],
            [path[i].key for i in range(1, len(path), 2)] + [None]
        )

    @classmethod
    def deserialize(cls, path):
        if path is None:
            return None

        p = tuple(chain(*[(class_mapper(mcls),
                            class_mapper(mcls).attrs[key]
                                if key is not None else None)
                            for mcls, key in path]))
        if p and p[-1] is None:
            p = p[0:-1]
        return cls.coerce(p)

    @classmethod
    def per_mapper(cls, mapper):
        return EntityRegistry(
                cls.root, mapper
            )

    @classmethod
    def coerce(cls, raw):
        return util.reduce(lambda prev, next: prev[next], raw, cls.root)

    @classmethod
    def token(cls, token):
        return TokenRegistry(cls.root, token)

    def __add__(self, other):
        return util.reduce(
                    lambda prev, next: prev[next],
                    other.path, self)

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.path, )


class RootRegistry(PathRegistry):
    """Root registry, defers to mappers so that
    paths are maintained per-root-mapper.

    """
    path = ()

    def __getitem__(self, entity):
        return entity._path_registry
PathRegistry.root = RootRegistry()

class TokenRegistry(PathRegistry):
    def __init__(self, parent, token):
        self.token = token
        self.parent = parent
        self.path = parent.path + (token,)

    def __getitem__(self, entity):
        raise NotImplementedError()

class PropRegistry(PathRegistry):
    def __init__(self, parent, prop):
        # restate this path in terms of the
        # given MapperProperty's parent.
        insp = inspection.inspect(parent[-1])
        if not insp.is_aliased_class or insp._use_mapper_path:
            parent = parent.parent[prop.parent]
        elif insp.is_aliased_class and insp.with_polymorphic_mappers:
            if prop.parent is not insp.mapper and \
                prop.parent in insp.with_polymorphic_mappers:
                subclass_entity = parent[-1]._entity_for_mapper(prop.parent)
                parent = parent.parent[subclass_entity]

        self.prop = prop
        self.parent = parent
        self.path = parent.path + (prop,)

    def __getitem__(self, entity):
        if isinstance(entity, (int, slice)):
            return self.path[entity]
        else:
            return EntityRegistry(
                self, entity
            )


class EntityRegistry(PathRegistry, dict):
    is_aliased_class = False

    def __init__(self, parent, entity):
        self.key = entity
        self.parent = parent
        self.is_aliased_class = entity.is_aliased_class

        self.path = parent.path + (entity,)

    def __nonzero__(self):
        return True

    def __getitem__(self, entity):
        if isinstance(entity, (int, slice)):
            return self.path[entity]
        else:
            return dict.__getitem__(self, entity)

    def _inlined_get_for(self, prop, context, key):
        """an inlined version of:

        cls = path[mapperproperty].get(context, key)

        Skips the isinstance() check in __getitem__
        and the extra method call for get().
        Used by StrategizedProperty for its
        very frequent lookup.

        """
        path = dict.__getitem__(self, prop)
        path_key = (key, path.path)
        if path_key in context._attributes:
            return context._attributes[path_key]
        else:
            return None

    def __missing__(self, key):
        self[key] = item = PropRegistry(self, key)
        return item


class AliasedClass(object):
    """Represents an "aliased" form of a mapped class for usage with Query.

    The ORM equivalent of a :func:`sqlalchemy.sql.expression.alias`
    construct, this object mimics the mapped class using a
    __getattr__ scheme and maintains a reference to a
    real :class:`~sqlalchemy.sql.expression.Alias` object.

    Usage is via the :func:`.orm.aliased` function, or alternatively
    via the :func:`.orm.with_polymorphic` function.

    Usage example::

        # find all pairs of users with the same name
        user_alias = aliased(User)
        session.query(User, user_alias).\\
                        join((user_alias, User.id > user_alias.id)).\\
                        filter(User.name==user_alias.name)

    The resulting object is an instance of :class:`.AliasedClass`.
    This object implements an attribute scheme which produces the
    same attribute and method interface as the original mapped
    class, allowing :class:`.AliasedClass` to be compatible
    with any attribute technique which works on the original class,
    including hybrid attributes (see :ref:`hybrids_toplevel`).

    The :class:`.AliasedClass` can be inspected for its underlying
    :class:`.Mapper`, aliased selectable, and other information
    using :func:`.inspect`::

        from sqlalchemy import inspect
        my_alias = aliased(MyClass)
        insp = inspect(my_alias)

    The resulting inspection object is an instance of :class:`.AliasedInsp`.

    See :func:`.aliased` and :func:`.with_polymorphic` for construction
    argument descriptions.

    """
    def __init__(self, cls, alias=None,
                            name=None,
                            adapt_on_names=False,
                            #  TODO: None for default here?
                            with_polymorphic_mappers=(),
                            with_polymorphic_discriminator=None,
                            base_alias=None,
                            use_mapper_path=False):
        mapper = _class_to_mapper(cls)
        if alias is None:
            alias = mapper._with_polymorphic_selectable.alias(name=name)
        self._aliased_insp = AliasedInsp(
            self,
            mapper,
            alias,
            name,
            with_polymorphic_mappers
                if with_polymorphic_mappers
                else mapper.with_polymorphic_mappers,
            with_polymorphic_discriminator
                if with_polymorphic_discriminator is not None
                else mapper.polymorphic_on,
            base_alias,
            use_mapper_path
        )

        self._setup(self._aliased_insp, adapt_on_names)


    def _setup(self, aliased_insp, adapt_on_names):
        self.__adapt_on_names = adapt_on_names
        mapper = aliased_insp.mapper
        alias = aliased_insp.selectable
        self.__target = mapper.class_
        self.__adapt_on_names = adapt_on_names
        self.__adapter = sql_util.ClauseAdapter(alias,
                            equivalents=mapper._equivalent_columns,
                            adapt_on_names=self.__adapt_on_names)
        for poly in aliased_insp.with_polymorphic_mappers:
            if poly is not mapper:
                setattr(self, poly.class_.__name__,
                    AliasedClass(poly.class_, alias, base_alias=self,
                            use_mapper_path=self._aliased_insp._use_mapper_path))

        self.__name__ = 'AliasedClass_%s' % self.__target.__name__

    def __getstate__(self):
        return {
            'mapper': self._aliased_insp.mapper,
            'alias': self._aliased_insp.selectable,
            'name': self._aliased_insp.name,
            'adapt_on_names': self.__adapt_on_names,
            'with_polymorphic_mappers':
                self._aliased_insp.with_polymorphic_mappers,
            'with_polymorphic_discriminator':
                self._aliased_insp.polymorphic_on,
            'base_alias': self._aliased_insp._base_alias.entity,
            'use_mapper_path': self._aliased_insp._use_mapper_path
        }

    def __setstate__(self, state):
        self._aliased_insp = AliasedInsp(
            self,
            state['mapper'],
            state['alias'],
            state['name'],
            state['with_polymorphic_mappers'],
            state['with_polymorphic_discriminator'],
            state['base_alias'],
            state['use_mapper_path']
        )
        self._setup(self._aliased_insp, state['adapt_on_names'])

    def __adapt_element(self, elem):
        return self.__adapter.traverse(elem).\
                    _annotate({
                        'parententity': self,
                        'parentmapper': self._aliased_insp.mapper}
                    )

    def __adapt_prop(self, existing, key):
        comparator = existing.comparator.adapted(self.__adapt_element)
        queryattr = attributes.QueryableAttribute(
                                self, key,
                                impl=existing.impl,
                                parententity=self._aliased_insp,
                                comparator=comparator)
        setattr(self, key, queryattr)
        return queryattr

    def __getattr__(self, key):
        for base in self.__target.__mro__:
            try:
                attr = object.__getattribute__(base, key)
            except AttributeError:
                continue
            else:
                break
        else:
            raise AttributeError(key)

        if isinstance(attr, attributes.QueryableAttribute):
            return self.__adapt_prop(attr, key)
        elif hasattr(attr, 'func_code'):
            is_method = getattr(self.__target, key, None)
            if is_method and is_method.im_self is not None:
                return util.types.MethodType(attr.im_func, self, self)
            else:
                return None
        elif hasattr(attr, '__get__'):
            ret = attr.__get__(None, self)
            if isinstance(ret, PropComparator):
                return ret.adapted(self.__adapt_element)
            return ret
        else:
            return attr

    def __repr__(self):
        return '<AliasedClass at 0x%x; %s>' % (
            id(self), self.__target.__name__)


class AliasedInsp(_InspectionAttr):
    """Provide an inspection interface for an
    :class:`.AliasedClass` object.

    The :class:`.AliasedInsp` object is returned
    given an :class:`.AliasedClass` using the
    :func:`.inspect` function::

        from sqlalchemy import inspect
        from sqlalchemy.orm import aliased

        my_alias = aliased(MyMappedClass)
        insp = inspect(my_alias)

    Attributes on :class:`.AliasedInsp`
    include:

    * ``entity`` - the :class:`.AliasedClass` represented.
    * ``mapper`` - the :class:`.Mapper` mapping the underlying class.
    * ``selectable`` - the :class:`.Alias` construct which ultimately
      represents an aliased :class:`.Table` or :class:`.Select`
      construct.
    * ``name`` - the name of the alias.  Also is used as the attribute
      name when returned in a result tuple from :class:`.Query`.
    * ``with_polymorphic_mappers`` - collection of :class:`.Mapper` objects
      indicating all those mappers expressed in the select construct
      for the :class:`.AliasedClass`.
    * ``polymorphic_on`` - an alternate column or SQL expression which
      will be used as the "discriminator" for a polymorphic load.

    .. seealso::

        :ref:`inspection_toplevel`

    """

    def __init__(self, entity, mapper, selectable, name,
                    with_polymorphic_mappers, polymorphic_on,
                    _base_alias, _use_mapper_path):
        self.entity = entity
        self.mapper = mapper
        self.selectable = selectable
        self.name = name
        self.with_polymorphic_mappers = with_polymorphic_mappers
        self.polymorphic_on = polymorphic_on

        # a little dance to get serialization to work
        self._base_alias = _base_alias._aliased_insp if _base_alias \
                            and _base_alias is not entity else self
        self._use_mapper_path = _use_mapper_path


    is_aliased_class = True
    "always returns True"

    @property
    def class_(self):
        """Return the mapped class ultimately represented by this
        :class:`.AliasedInsp`."""
        return self.mapper.class_

    @util.memoized_property
    def _path_registry(self):
        if self._use_mapper_path:
            return self.mapper._path_registry
        else:
            return PathRegistry.per_mapper(self)

    def _entity_for_mapper(self, mapper):
        self_poly = self.with_polymorphic_mappers
        if mapper in self_poly:
            return getattr(self.entity, mapper.class_.__name__)._aliased_insp
        elif mapper.isa(self.mapper):
            return self
        else:
            assert False, "mapper %s doesn't correspond to %s" % (mapper, self)

    def __repr__(self):
        return '<AliasedInsp at 0x%x; %s>' % (
            id(self), self.class_.__name__)


inspection._inspects(AliasedClass)(lambda target: target._aliased_insp)
inspection._inspects(AliasedInsp)(lambda target: target)


def aliased(element, alias=None, name=None, adapt_on_names=False):
    """Produce an alias of the given element, usually an :class:`.AliasedClass`
    instance.

    E.g.::

        my_alias = aliased(MyClass)

        session.query(MyClass, my_alias).filter(MyClass.id > my_alias.id)

    The :func:`.aliased` function is used to create an ad-hoc mapping
    of a mapped class to a new selectable.  By default, a selectable
    is generated from the normally mapped selectable (typically a
    :class:`.Table`) using the :meth:`.FromClause.alias` method.
    However, :func:`.aliased` can also be used to link the class to
    a new :func:`.select` statement.   Also, the :func:`.with_polymorphic`
    function is a variant of :func:`.aliased` that is intended to specify
    a so-called "polymorphic selectable", that corresponds to the union
    of several joined-inheritance subclasses at once.

    For convenience, the :func:`.aliased` function also accepts plain
    :class:`.FromClause` constructs, such as a :class:`.Table` or
    :func:`.select` construct.   In those cases, the :meth:`.FromClause.alias`
    method is called on the object and the new :class:`.Alias` object
    returned.  The returned :class:`.Alias` is not ORM-mapped in this case.

    :param element: element to be aliased.  Is normally a mapped class,
     but for convenience can also be a :class:`.FromClause` element.
    :param alias: Optional selectable unit to map the element to.  This should
     normally be a :class:`.Alias` object corresponding to the :class:`.Table`
     to which the class is mapped, or to a :func:`.select` construct that
     is compatible with the mapping.   By default, a simple anonymous
     alias of the mapped table is generated.
    :param name: optional string name to use for the alias, if not specified
     by the ``alias`` parameter.  The name, among other things, forms the
     attribute name that will be accessible via tuples returned by a
     :class:`.Query` object.
    :param adapt_on_names: if True, more liberal "matching" will be used when
     mapping the mapped columns of the ORM entity to those of the
     given selectable - a name-based match will be performed if the
     given selectable doesn't otherwise have a column that corresponds
     to one on the entity.  The use case for this is when associating
     an entity with some derived selectable such as one that uses
     aggregate functions::

        class UnitPrice(Base):
            __tablename__ = 'unit_price'
            ...
            unit_id = Column(Integer)
            price = Column(Numeric)

        aggregated_unit_price = Session.query(
                                    func.sum(UnitPrice.price).label('price')
                                ).group_by(UnitPrice.unit_id).subquery()

        aggregated_unit_price = aliased(UnitPrice,
                    alias=aggregated_unit_price, adapt_on_names=True)

     Above, functions on ``aggregated_unit_price`` which refer to
     ``.price`` will return the
     ``fund.sum(UnitPrice.price).label('price')`` column, as it is
     matched on the name "price".  Ordinarily, the "price" function
     wouldn't have any "column correspondence" to the actual
     ``UnitPrice.price`` column as it is not a proxy of the original.

     .. versionadded:: 0.7.3


    """
    if isinstance(element, expression.FromClause):
        if adapt_on_names:
            raise sa_exc.ArgumentError(
                "adapt_on_names only applies to ORM elements"
            )
        return element.alias(name)
    else:
        return AliasedClass(element, alias=alias,
                    name=name, adapt_on_names=adapt_on_names)


def with_polymorphic(base, classes, selectable=False,
                        polymorphic_on=None, aliased=False,
                        innerjoin=False, _use_mapper_path=False):
    """Produce an :class:`.AliasedClass` construct which specifies
    columns for descendant mappers of the given base.

    .. versionadded:: 0.8
        :func:`.orm.with_polymorphic` is in addition to the existing
        :class:`.Query` method :meth:`.Query.with_polymorphic`,
        which has the same purpose but is not as flexible in its usage.

    Using this method will ensure that each descendant mapper's
    tables are included in the FROM clause, and will allow filter()
    criterion to be used against those tables.  The resulting
    instances will also have those columns already loaded so that
    no "post fetch" of those columns will be required.

    See the examples at :ref:`with_polymorphic`.

    :param base: Base class to be aliased.

    :param classes: a single class or mapper, or list of
        class/mappers, which inherit from the base class.
        Alternatively, it may also be the string ``'*'``, in which case
        all descending mapped classes will be added to the FROM clause.

    :param aliased: when True, the selectable will be wrapped in an
        alias, that is ``(SELECT * FROM <fromclauses>) AS anon_1``.
        This can be important when using the with_polymorphic()
        to create the target of a JOIN on a backend that does not
        support parenthesized joins, such as SQLite and older
        versions of MySQL.

    :param selectable: a table or select() statement that will
        be used in place of the generated FROM clause. This argument is
        required if any of the desired classes use concrete table
        inheritance, since SQLAlchemy currently cannot generate UNIONs
        among tables automatically. If used, the ``selectable`` argument
        must represent the full set of tables and columns mapped by every
        mapped class. Otherwise, the unaccounted mapped columns will
        result in their table being appended directly to the FROM clause
        which will usually lead to incorrect results.

    :param polymorphic_on: a column to be used as the "discriminator"
        column for the given selectable. If not given, the polymorphic_on
        attribute of the base classes' mapper will be used, if any. This
        is useful for mappings that don't have polymorphic loading
        behavior by default.

    :param innerjoin: if True, an INNER JOIN will be used.  This should
       only be specified if querying for one specific subtype only
    """
    primary_mapper = _class_to_mapper(base)
    mappers, selectable = primary_mapper.\
                    _with_polymorphic_args(classes, selectable,
                                innerjoin=innerjoin)
    if aliased:
        selectable = selectable.alias()
    return AliasedClass(base,
                selectable,
                with_polymorphic_mappers=mappers,
                with_polymorphic_discriminator=polymorphic_on,
                use_mapper_path=_use_mapper_path)


def _orm_annotate(element, exclude=None):
    """Deep copy the given ClauseElement, annotating each element with the
    "_orm_adapt" flag.

    Elements within the exclude collection will be cloned but not annotated.

    """
    return sql_util._deep_annotate(element, {'_orm_adapt': True}, exclude)


def _orm_deannotate(element):
    """Remove annotations that link a column to a particular mapping.

    Note this doesn't affect "remote" and "foreign" annotations
    passed by the :func:`.orm.foreign` and :func:`.orm.remote`
    annotators.

    """

    return sql_util._deep_deannotate(element,
                values=("_orm_adapt", "parententity")
            )


def _orm_full_deannotate(element):
    return sql_util._deep_deannotate(element)


class _ORMJoin(expression.Join):
    """Extend Join to support ORM constructs as input."""

    __visit_name__ = expression.Join.__visit_name__

    def __init__(self, left, right, onclause=None, isouter=False):

        left_info = inspection.inspect(left)
        left_orm_info = getattr(left, '_joined_from_info', left_info)

        right_info = inspection.inspect(right)
        adapt_to = right_info.selectable

        self._joined_from_info = right_info

        if isinstance(onclause, basestring):
            onclause = getattr(left_orm_info.entity, onclause)

        if isinstance(onclause, attributes.QueryableAttribute):
            on_selectable = onclause.comparator._source_selectable()
            prop = onclause.property
        elif isinstance(onclause, MapperProperty):
            prop = onclause
            on_selectable = prop.parent.selectable
        else:
            prop = None

        if prop:
            if sql_util.clause_is_present(on_selectable, left_info.selectable):
                adapt_from = on_selectable
            else:
                adapt_from = left_info.selectable

            pj, sj, source, dest, \
                secondary, target_adapter = prop._create_joins(
                            source_selectable=adapt_from,
                            dest_selectable=adapt_to,
                            source_polymorphic=True,
                            dest_polymorphic=True,
                            of_type=right_info.mapper)

            if sj is not None:
                left = sql.join(left, secondary, pj, isouter)
                onclause = sj
            else:
                onclause = pj
            self._target_adapter = target_adapter

        expression.Join.__init__(self, left, right, onclause, isouter)

    def join(self, right, onclause=None, isouter=False, join_to_left=None):
        return _ORMJoin(self, right, onclause, isouter)

    def outerjoin(self, right, onclause=None, join_to_left=None):
        return _ORMJoin(self, right, onclause, True)


def join(left, right, onclause=None, isouter=False, join_to_left=None):
    """Produce an inner join between left and right clauses.

    :func:`.orm.join` is an extension to the core join interface
    provided by :func:`.sql.expression.join()`, where the
    left and right selectables may be not only core selectable
    objects such as :class:`.Table`, but also mapped classes or
    :class:`.AliasedClass` instances.   The "on" clause can
    be a SQL expression, or an attribute or string name
    referencing a configured :func:`.relationship`.

    :func:`.orm.join` is not commonly needed in modern usage,
    as its functionality is encapsulated within that of the
    :meth:`.Query.join` method, which features a
    significant amount of automation beyond :func:`.orm.join`
    by itself.  Explicit usage of :func:`.orm.join`
    with :class:`.Query` involves usage of the
    :meth:`.Query.select_from` method, as in::

        from sqlalchemy.orm import join
        session.query(User).\\
            select_from(join(User, Address, User.addresses)).\\
            filter(Address.email_address=='foo@bar.com')

    In modern SQLAlchemy the above join can be written more
    succinctly as::

        session.query(User).\\
                join(User.addresses).\\
                filter(Address.email_address=='foo@bar.com')

    See :meth:`.Query.join` for information on modern usage
    of ORM level joins.

    .. versionchanged:: 0.8.1 - the ``join_to_left`` parameter
       is no longer used, and is deprecated.

    """
    return _ORMJoin(left, right, onclause, isouter)


def outerjoin(left, right, onclause=None, join_to_left=None):
    """Produce a left outer join between left and right clauses.

    This is the "outer join" version of the :func:`.orm.join` function,
    featuring the same behavior except that an OUTER JOIN is generated.
    See that function's documentation for other usage details.

    """
    return _ORMJoin(left, right, onclause, True)


def with_parent(instance, prop):
    """Create filtering criterion that relates this query's primary entity
    to the given related instance, using established :func:`.relationship()`
    configuration.

    The SQL rendered is the same as that rendered when a lazy loader
    would fire off from the given parent on that attribute, meaning
    that the appropriate state is taken from the parent object in
    Python without the need to render joins to the parent table
    in the rendered statement.

    .. versionchanged:: 0.6.4
        This method accepts parent instances in all
        persistence states, including transient, persistent, and detached.
        Only the requisite primary key/foreign key attributes need to
        be populated.  Previous versions didn't work with transient
        instances.

    :param instance:
      An instance which has some :func:`.relationship`.

    :param property:
      String property name, or class-bound attribute, which indicates
      what relationship from the instance should be used to reconcile the
      parent/child relationship.

    """
    if isinstance(prop, basestring):
        mapper = object_mapper(instance)
        prop = getattr(mapper.class_, prop).property
    elif isinstance(prop, attributes.QueryableAttribute):
        prop = prop.property

    return prop.compare(operators.eq,
                        instance,
                        value_is_parent=True)


def _attr_as_key(attr):
    if hasattr(attr, 'key'):
        return attr.key
    else:
        return expression._column_as_key(attr)


_state_mapper = util.dottedgetter('manager.mapper')


@inspection._inspects(object)
def _inspect_mapped_object(instance):
    try:
        return attributes.instance_state(instance)
        # TODO: whats the py-2/3 syntax to catch two
        # different kinds of exceptions at once ?
    except exc.UnmappedClassError:
        return None
    except exc.NO_STATE:
        return None


@inspection._inspects(type)
def _inspect_mapped_class(class_, configure=False):
    try:
        class_manager = attributes.manager_of_class(class_)
        if not class_manager.is_mapped:
            return None
        mapper = class_manager.mapper
        if configure and mapperlib.module._new_mappers:
            mapperlib.configure_mappers()
        return mapper

    except exc.NO_STATE:
        return None


def object_mapper(instance):
    """Given an object, return the primary Mapper associated with the object
    instance.

    Raises :class:`sqlalchemy.orm.exc.UnmappedInstanceError`
    if no mapping is configured.

    This function is available via the inspection system as::

        inspect(instance).mapper

    Using the inspection system will raise
    :class:`sqlalchemy.exc.NoInspectionAvailable` if the instance is
    not part of a mapping.

    """
    return object_state(instance).mapper


def object_state(instance):
    """Given an object, return the :class:`.InstanceState`
    associated with the object.

    Raises :class:`sqlalchemy.orm.exc.UnmappedInstanceError`
    if no mapping is configured.

    Equivalent functionality is available via the :func:`.inspect`
    function as::

        inspect(instance)

    Using the inspection system will raise
    :class:`sqlalchemy.exc.NoInspectionAvailable` if the instance is
    not part of a mapping.

    """
    state = _inspect_mapped_object(instance)
    if state is None:
        raise exc.UnmappedInstanceError(instance)
    else:
        return state


def class_mapper(class_, configure=True):
    """Given a class, return the primary :class:`.Mapper` associated
    with the key.

    Raises :class:`.UnmappedClassError` if no mapping is configured
    on the given class, or :class:`.ArgumentError` if a non-class
    object is passed.

    Equivalent functionality is available via the :func:`.inspect`
    function as::

        inspect(some_mapped_class)

    Using the inspection system will raise
    :class:`sqlalchemy.exc.NoInspectionAvailable` if the class is not mapped.

    """
    mapper = _inspect_mapped_class(class_, configure=configure)
    if mapper is None:
        if not isinstance(class_, type):
            raise sa_exc.ArgumentError(
                    "Class object expected, got '%r'." % class_)
        raise exc.UnmappedClassError(class_)
    else:
        return mapper


def _class_to_mapper(class_or_mapper):
    insp = inspection.inspect(class_or_mapper, False)
    if insp is not None:
        return insp.mapper
    else:
        raise exc.UnmappedClassError(class_or_mapper)


def _mapper_or_none(entity):
    """Return the :class:`.Mapper` for the given class or None if the
    class is not mapped."""

    insp = inspection.inspect(entity, False)
    if insp is not None:
        return insp.mapper
    else:
        return None


def _is_mapped_class(entity):
    """Return True if the given object is a mapped class,
    :class:`.Mapper`, or :class:`.AliasedClass`."""

    insp = inspection.inspect(entity, False)
    return insp is not None and \
        hasattr(insp, "mapper") and \
        (
            insp.is_mapper
            or insp.is_aliased_class
        )


def _is_aliased_class(entity):
    insp = inspection.inspect(entity, False)
    return insp is not None and \
        getattr(insp, "is_aliased_class", False)


def _entity_descriptor(entity, key):
    """Return a class attribute given an entity and string name.

    May return :class:`.InstrumentedAttribute` or user-defined
    attribute.

    """
    insp = inspection.inspect(entity)
    if insp.is_selectable:
        description = entity
        entity = insp.c
    elif insp.is_aliased_class:
        entity = insp.entity
        description = entity
    elif hasattr(insp, "mapper"):
        description = entity = insp.mapper.class_
    else:
        description = entity

    try:
        return getattr(entity, key)
    except AttributeError:
        raise sa_exc.InvalidRequestError(
                    "Entity '%s' has no property '%s'" %
                    (description, key)
                )


def _orm_columns(entity):
    insp = inspection.inspect(entity, False)
    if hasattr(insp, 'selectable'):
        return [c for c in insp.selectable.c]
    else:
        return [entity]


def has_identity(object):
    """Return True if the given object has a database
    identity.

    This typically corresponds to the object being
    in either the persistent or detached state.

    .. seealso::

        :func:`.was_deleted`

    """
    state = attributes.instance_state(object)
    return state.has_identity

def was_deleted(object):
    """Return True if the given object was deleted
    within a session flush.

    .. versionadded:: 0.8.0

    """

    state = attributes.instance_state(object)
    return state.deleted

def instance_str(instance):
    """Return a string describing an instance."""

    return state_str(attributes.instance_state(instance))


def state_str(state):
    """Return a string describing an instance via its InstanceState."""

    if state is None:
        return "None"
    else:
        return '<%s at 0x%x>' % (state.class_.__name__, id(state.obj()))


def state_class_str(state):
    """Return a string describing an instance's class via its InstanceState."""

    if state is None:
        return "None"
    else:
        return '<%s>' % (state.class_.__name__, )


def attribute_str(instance, attribute):
    return instance_str(instance) + "." + attribute


def state_attribute_str(state, attribute):
    return state_str(state) + "." + attribute


def randomize_unitofwork():
    """Use random-ordering sets within the unit of work in order
    to detect unit of work sorting issues.

    This is a utility function that can be used to help reproduce
    inconsistent unit of work sorting issues.   For example,
    if two kinds of objects A and B are being inserted, and
    B has a foreign key reference to A - the A must be inserted first.
    However, if there is no relationship between A and B, the unit of work
    won't know to perform this sorting, and an operation may or may not
    fail, depending on how the ordering works out.   Since Python sets
    and dictionaries have non-deterministic ordering, such an issue may
    occur on some runs and not on others, and in practice it tends to
    have a great dependence on the state of the interpreter.  This leads
    to so-called "heisenbugs" where changing entirely irrelevant aspects
    of the test program still cause the failure behavior to change.

    By calling ``randomize_unitofwork()`` when a script first runs, the
    ordering of a key series of sets within the unit of work implementation
    are randomized, so that the script can be minimized down to the fundamental
    mapping and operation that's failing, while still reproducing the issue
    on at least some runs.

    This utility is also available when running the test suite via the
    ``--reversetop`` flag.

    .. versionadded:: 0.8.1 created a standalone version of the
       ``--reversetop`` feature.

    """
    from sqlalchemy.orm import unitofwork, session, mapper, dependency
    from sqlalchemy.util import topological
    from sqlalchemy.testing.util import RandomSet
    topological.set = unitofwork.set = session.set = mapper.set = \
            dependency.set = RandomSet

