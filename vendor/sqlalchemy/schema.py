# sqlalchemy/schema.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""The schema module provides the building blocks for database metadata.

Each element within this module describes a database entity which can be
created and dropped, or is otherwise part of such an entity.  Examples include
tables, columns, sequences, and indexes.

All entities are subclasses of :class:`~sqlalchemy.schema.SchemaItem`, and as
defined in this module they are intended to be agnostic of any vendor-specific
constructs.

A collection of entities are grouped into a unit called
:class:`~sqlalchemy.schema.MetaData`. MetaData serves as a logical grouping of
schema elements, and can also be associated with an actual database connection
such that operations involving the contained elements can contact the database
as needed.

Two of the elements here also build upon their "syntactic" counterparts, which
are defined in :class:`~sqlalchemy.sql.expression.`, specifically
:class:`~sqlalchemy.schema.Table` and :class:`~sqlalchemy.schema.Column`.
Since these objects are part of the SQL expression language, they are usable
as components in SQL expressions.

"""
from __future__ import with_statement
import re
import inspect
from . import exc, util, dialects, event, events, inspection
from .sql import expression, visitors

ddl = util.importlater("sqlalchemy.engine", "ddl")
sqlutil = util.importlater("sqlalchemy.sql", "util")
url = util.importlater("sqlalchemy.engine", "url")
sqltypes = util.importlater("sqlalchemy", "types")

__all__ = ['SchemaItem', 'Table', 'Column', 'ForeignKey', 'Sequence', 'Index',
           'ForeignKeyConstraint', 'PrimaryKeyConstraint', 'CheckConstraint',
           'UniqueConstraint', 'DefaultGenerator', 'Constraint', 'MetaData',
           'ThreadLocalMetaData', 'SchemaVisitor', 'PassiveDefault',
           'DefaultClause', 'FetchedValue', 'ColumnDefault', 'DDL',
           'CreateTable', 'DropTable', 'CreateSequence', 'DropSequence',
           'AddConstraint', 'DropConstraint',
           ]
__all__.sort()

RETAIN_SCHEMA = util.symbol('retain_schema')


class SchemaItem(events.SchemaEventTarget, visitors.Visitable):
    """Base class for items that define a database schema."""

    __visit_name__ = 'schema_item'
    quote = None

    def _init_items(self, *args):
        """Initialize the list of child items for this SchemaItem."""

        for item in args:
            if item is not None:
                item._set_parent_with_dispatch(self)

    def get_children(self, **kwargs):
        """used to allow SchemaVisitor access"""
        return []

    def __repr__(self):
        return util.generic_repr(self)

    @util.memoized_property
    def info(self):
        """Info dictionary associated with the object, allowing user-defined
        data to be associated with this :class:`.SchemaItem`.

        The dictionary is automatically generated when first accessed.
        It can also be specified in the constructor of some objects,
        such as :class:`.Table` and :class:`.Column`.

        """
        return {}


def _get_table_key(name, schema):
    if schema is None:
        return name
    else:
        return schema + "." + name


def _validate_dialect_kwargs(kwargs, name):
    # validate remaining kwargs that they all specify DB prefixes

    for k in kwargs:
        m = re.match('^(.+?)_.*', k)
        if m is None:
            raise TypeError("Additional arguments should be "
                    "named <dialectname>_<argument>, got '%s'" % k)


inspection._self_inspects(SchemaItem)


class Table(SchemaItem, expression.TableClause):
    """Represent a table in a database.

    e.g.::

        mytable = Table("mytable", metadata,
                        Column('mytable_id', Integer, primary_key=True),
                        Column('value', String(50))
                   )

    The :class:`.Table` object constructs a unique instance of itself based
    on its name and optional schema name within the given
    :class:`.MetaData` object. Calling the :class:`.Table`
    constructor with the same name and same :class:`.MetaData` argument
    a second time will return the *same* :class:`.Table` object - in this way
    the :class:`.Table` constructor acts as a registry function.

    .. seealso::

        :ref:`metadata_describing` - Introduction to database metadata

    Constructor arguments are as follows:

    :param name: The name of this table as represented in the database.

        This property, along with the *schema*, indicates the *singleton
        identity* of this table in relation to its parent :class:`.MetaData`.
        Additional calls to :class:`.Table` with the same name, metadata,
        and schema name will return the same :class:`.Table` object.

        Names which contain no upper case characters
        will be treated as case insensitive names, and will not be quoted
        unless they are a reserved word.  Names with any number of upper
        case characters will be quoted and sent exactly.  Note that this
        behavior applies even for databases which standardize upper
        case names as case insensitive such as Oracle.

    :param metadata: a :class:`.MetaData` object which will contain this
        table.  The metadata is used as a point of association of this table
        with other tables which are referenced via foreign key.  It also
        may be used to associate this table with a particular
        :class:`.Connectable`.

    :param \*args: Additional positional arguments are used primarily
        to add the list of :class:`.Column` objects contained within this
        table. Similar to the style of a CREATE TABLE statement, other
        :class:`.SchemaItem` constructs may be added here, including
        :class:`.PrimaryKeyConstraint`, and :class:`.ForeignKeyConstraint`.

    :param autoload: Defaults to False: the Columns for this table should
        be reflected from the database. Usually there will be no Column
        objects in the constructor if this property is set.

    :param autoload_replace: If ``True``, when using ``autoload=True``
        and ``extend_existing=True``,
        replace ``Column`` objects already present in the ``Table`` that's
        in the ``MetaData`` registry with
        what's reflected.  Otherwise, all existing columns will be
        excluded from the reflection process.    Note that this does
        not impact ``Column`` objects specified in the same call to ``Table``
        which includes ``autoload``, those always take precedence.
        Defaults to ``True``.

        .. versionadded:: 0.7.5

    :param autoload_with: If autoload==True, this is an optional Engine
        or Connection instance to be used for the table reflection. If
        ``None``, the underlying MetaData's bound connectable will be used.

    :param extend_existing: When ``True``, indicates that if this
        :class:`.Table` is already present in the given :class:`.MetaData`,
        apply further arguments within the constructor to the existing
        :class:`.Table`.

        If ``extend_existing`` or ``keep_existing`` are not set, an error is
        raised if additional table modifiers are specified when
        the given :class:`.Table` is already present in the :class:`.MetaData`.

        .. versionchanged:: 0.7.4
            ``extend_existing`` will work in conjunction
            with ``autoload=True`` to run a new reflection operation against
            the database; new :class:`.Column` objects will be produced
            from database metadata to replace those existing with the same
            name, and additional :class:`.Column` objects not present
            in the :class:`.Table` will be added.

        As is always the case with ``autoload=True``, :class:`.Column`
        objects can be specified in the same :class:`.Table` constructor,
        which will take precedence.  I.e.::

            Table("mytable", metadata,
                        Column('y', Integer),
                        extend_existing=True,
                        autoload=True,
                        autoload_with=engine
                    )

        The above will overwrite all columns within ``mytable`` which
        are present in the database, except for ``y`` which will be used as is
        from the above definition.   If the ``autoload_replace`` flag
        is set to False, no existing columns will be replaced.

    :param implicit_returning: True by default - indicates that
        RETURNING can be used by default to fetch newly inserted primary key
        values, for backends which support this.  Note that
        create_engine() also provides an implicit_returning flag.

    :param include_columns: A list of strings indicating a subset of
        columns to be loaded via the ``autoload`` operation; table columns who
        aren't present in this list will not be represented on the resulting
        ``Table`` object. Defaults to ``None`` which indicates all columns
        should be reflected.

    :param info: Optional data dictionary which will be populated into the
        :attr:`.SchemaItem.info` attribute of this object.

    :param keep_existing: When ``True``, indicates that if this Table
        is already present in the given :class:`.MetaData`, ignore
        further arguments within the constructor to the existing
        :class:`.Table`, and return the :class:`.Table` object as
        originally created. This is to allow a function that wishes
        to define a new :class:`.Table` on first call, but on
        subsequent calls will return the same :class:`.Table`,
        without any of the declarations (particularly constraints)
        being applied a second time. Also see extend_existing.

        If extend_existing or keep_existing are not set, an error is
        raised if additional table modifiers are specified when
        the given :class:`.Table` is already present in the :class:`.MetaData`.

    :param listeners: A list of tuples of the form ``(<eventname>, <fn>)``
        which will be passed to :func:`.event.listen` upon construction.
        This alternate hook to :func:`.event.listen` allows the establishment
        of a listener function specific to this :class:`.Table` before
        the "autoload" process begins.  Particularly useful for
        the :meth:`.DDLEvents.column_reflect` event::

            def listen_for_reflect(table, column_info):
                "handle the column reflection event"
                # ...

            t = Table(
                'sometable',
                autoload=True,
                listeners=[
                    ('column_reflect', listen_for_reflect)
                ])

    :param mustexist: When ``True``, indicates that this Table must already
        be present in the given :class:`.MetaData` collection, else
        an exception is raised.

    :param prefixes:
        A list of strings to insert after CREATE in the CREATE TABLE
        statement.  They will be separated by spaces.

    :param quote: Force quoting of this table's name on or off, corresponding
        to ``True`` or ``False``.  When left at its default of ``None``,
        the column identifier will be quoted according to whether the name is
        case sensitive (identifiers with at least one upper case character are
        treated as case sensitive), or if it's a reserved word.  This flag
        is only needed to force quoting of a reserved word which is not known
        by the SQLAlchemy dialect.

    :param quote_schema: same as 'quote' but applies to the schema identifier.

    :param schema: The *schema name* for this table, which is required if
        the table resides in a schema other than the default selected schema
        for the engine's database connection. Defaults to ``None``.

    :param useexisting: Deprecated.  Use extend_existing.

    """

    __visit_name__ = 'table'

    def __new__(cls, *args, **kw):
        if not args:
            # python3k pickle seems to call this
            return object.__new__(cls)

        try:
            name, metadata, args = args[0], args[1], args[2:]
        except IndexError:
            raise TypeError("Table() takes at least two arguments")

        schema = kw.get('schema', None)
        if schema is None:
            schema = metadata.schema
        keep_existing = kw.pop('keep_existing', False)
        extend_existing = kw.pop('extend_existing', False)
        if 'useexisting' in kw:
            msg = "useexisting is deprecated.  Use extend_existing."
            util.warn_deprecated(msg)
            if extend_existing:
                msg = "useexisting is synonymous with extend_existing."
                raise exc.ArgumentError(msg)
            extend_existing = kw.pop('useexisting', False)

        if keep_existing and extend_existing:
            msg = "keep_existing and extend_existing are mutually exclusive."
            raise exc.ArgumentError(msg)

        mustexist = kw.pop('mustexist', False)
        key = _get_table_key(name, schema)
        if key in metadata.tables:
            if not keep_existing and not extend_existing and bool(args):
                raise exc.InvalidRequestError(
                    "Table '%s' is already defined for this MetaData "
                    "instance.  Specify 'extend_existing=True' "
                    "to redefine "
                    "options and columns on an "
                    "existing Table object." % key)
            table = metadata.tables[key]
            if extend_existing:
                table._init_existing(*args, **kw)
            return table
        else:
            if mustexist:
                raise exc.InvalidRequestError(
                    "Table '%s' not defined" % (key))
            table = object.__new__(cls)
            table.dispatch.before_parent_attach(table, metadata)
            metadata._add_table(name, schema, table)
            try:
                table._init(name, metadata, *args, **kw)
                table.dispatch.after_parent_attach(table, metadata)
                return table
            except:
                metadata._remove_table(name, schema)
                raise

    def __init__(self, *args, **kw):
        """Constructor for :class:`~.schema.Table`.

        This method is a no-op.   See the top-level
        documentation for :class:`~.schema.Table`
        for constructor arguments.

        """
        # __init__ is overridden to prevent __new__ from
        # calling the superclass constructor.

    def _init(self, name, metadata, *args, **kwargs):
        super(Table, self).__init__(name)
        self.metadata = metadata
        self.schema = kwargs.pop('schema', None)
        if self.schema is None:
            self.schema = metadata.schema
            self.quote_schema = kwargs.pop(
                'quote_schema', metadata.quote_schema)
        else:
            self.quote_schema = kwargs.pop('quote_schema', None)

        self.indexes = set()
        self.constraints = set()
        self._columns = expression.ColumnCollection()
        PrimaryKeyConstraint()._set_parent_with_dispatch(self)
        self.foreign_keys = set()
        self._extra_dependencies = set()
        self.kwargs = {}
        if self.schema is not None:
            self.fullname = "%s.%s" % (self.schema, self.name)
        else:
            self.fullname = self.name

        autoload = kwargs.pop('autoload', False)
        autoload_with = kwargs.pop('autoload_with', None)
        # this argument is only used with _init_existing()
        kwargs.pop('autoload_replace', True)
        include_columns = kwargs.pop('include_columns', None)

        self.implicit_returning = kwargs.pop('implicit_returning', True)
        self.quote = kwargs.pop('quote', None)
        if 'info' in kwargs:
            self.info = kwargs.pop('info')
        if 'listeners' in kwargs:
            listeners = kwargs.pop('listeners')
            for evt, fn in listeners:
                event.listen(self, evt, fn)

        self._prefixes = kwargs.pop('prefixes', [])

        self._extra_kwargs(**kwargs)

        # load column definitions from the database if 'autoload' is defined
        # we do it after the table is in the singleton dictionary to support
        # circular foreign keys
        if autoload:
            self._autoload(metadata, autoload_with, include_columns)

        # initialize all the column, etc. objects.  done after reflection to
        # allow user-overrides
        self._init_items(*args)

    def _autoload(self, metadata, autoload_with, include_columns,
                  exclude_columns=()):
        if self.primary_key.columns:
            PrimaryKeyConstraint(*[
                c for c in self.primary_key.columns
                if c.key in exclude_columns
            ])._set_parent_with_dispatch(self)

        if autoload_with:
            autoload_with.run_callable(
                autoload_with.dialect.reflecttable,
                self, include_columns, exclude_columns
            )
        else:
            bind = _bind_or_error(metadata,
                    msg="No engine is bound to this Table's MetaData. "
                    "Pass an engine to the Table via "
                    "autoload_with=<someengine>, "
                    "or associate the MetaData with an engine via "
                    "metadata.bind=<someengine>")
            bind.run_callable(
                    bind.dialect.reflecttable,
                    self, include_columns, exclude_columns
                )

    @property
    def _sorted_constraints(self):
        """Return the set of constraints as a list, sorted by creation
        order.

        """
        return sorted(self.constraints, key=lambda c: c._creation_order)

    def _init_existing(self, *args, **kwargs):
        autoload = kwargs.pop('autoload', False)
        autoload_with = kwargs.pop('autoload_with', None)
        autoload_replace = kwargs.pop('autoload_replace', True)
        schema = kwargs.pop('schema', None)
        if schema and schema != self.schema:
            raise exc.ArgumentError(
                "Can't change schema of existing table from '%s' to '%s'",
                (self.schema, schema))

        include_columns = kwargs.pop('include_columns', None)

        if include_columns is not None:
            for c in self.c:
                if c.name not in include_columns:
                    self._columns.remove(c)

        for key in ('quote', 'quote_schema'):
            if key in kwargs:
                setattr(self, key, kwargs.pop(key))

        if 'info' in kwargs:
            self.info = kwargs.pop('info')

        if autoload:
            if not autoload_replace:
                exclude_columns = [c.name for c in self.c]
            else:
                exclude_columns = ()
            self._autoload(
                self.metadata, autoload_with, include_columns, exclude_columns)

        self._extra_kwargs(**kwargs)
        self._init_items(*args)

    def _extra_kwargs(self, **kwargs):
        # validate remaining kwargs that they all specify DB prefixes
        _validate_dialect_kwargs(kwargs, "Table")
        self.kwargs.update(kwargs)

    def _init_collections(self):
        pass

    @util.memoized_property
    def _autoincrement_column(self):
        for col in self.primary_key:
            if col.autoincrement and \
                col.type._type_affinity is not None and \
                issubclass(col.type._type_affinity, sqltypes.Integer) and \
                (not col.foreign_keys or col.autoincrement == 'ignore_fk') and \
                isinstance(col.default, (type(None), Sequence)) and \
                (col.server_default is None or col.server_default.reflected):
                return col

    @property
    def key(self):
        return _get_table_key(self.name, self.schema)

    def __repr__(self):
        return "Table(%s)" % ', '.join(
            [repr(self.name)] + [repr(self.metadata)] +
            [repr(x) for x in self.columns] +
            ["%s=%s" % (k, repr(getattr(self, k))) for k in ['schema']])

    def __str__(self):
        return _get_table_key(self.description, self.schema)

    @property
    def bind(self):
        """Return the connectable associated with this Table."""

        return self.metadata and self.metadata.bind or None

    def add_is_dependent_on(self, table):
        """Add a 'dependency' for this Table.

        This is another Table object which must be created
        first before this one can, or dropped after this one.

        Usually, dependencies between tables are determined via
        ForeignKey objects.   However, for other situations that
        create dependencies outside of foreign keys (rules, inheriting),
        this method can manually establish such a link.

        """
        self._extra_dependencies.add(table)

    def append_column(self, column):
        """Append a :class:`~.schema.Column` to this :class:`~.schema.Table`.

        The "key" of the newly added :class:`~.schema.Column`, i.e. the
        value of its ``.key`` attribute, will then be available
        in the ``.c`` collection of this :class:`~.schema.Table`, and the
        column definition will be included in any CREATE TABLE, SELECT,
        UPDATE, etc. statements generated from this :class:`~.schema.Table`
        construct.

        Note that this does **not** change the definition of the table
        as it exists within any underlying database, assuming that
        table has already been created in the database.   Relational
        databases support the addition of columns to existing tables
        using the SQL ALTER command, which would need to be
        emitted for an already-existing table that doesn't contain
        the newly added column.

        """

        column._set_parent_with_dispatch(self)

    def append_constraint(self, constraint):
        """Append a :class:`~.schema.Constraint` to this
        :class:`~.schema.Table`.

        This has the effect of the constraint being included in any
        future CREATE TABLE statement, assuming specific DDL creation
        events have not been associated with the given
        :class:`~.schema.Constraint` object.

        Note that this does **not** produce the constraint within the
        relational database automatically, for a table that already exists
        in the database.   To add a constraint to an
        existing relational database table, the SQL ALTER command must
        be used.  SQLAlchemy also provides the
        :class:`.AddConstraint` construct which can produce this SQL when
        invoked as an executable clause.

        """

        constraint._set_parent_with_dispatch(self)

    def append_ddl_listener(self, event_name, listener):
        """Append a DDL event listener to this ``Table``.

        Deprecated.  See :class:`.DDLEvents`.

        """

        def adapt_listener(target, connection, **kw):
            listener(event_name, target, connection)

        event.listen(self, "" + event_name.replace('-', '_'), adapt_listener)

    def _set_parent(self, metadata):
        metadata._add_table(self.name, self.schema, self)
        self.metadata = metadata

    def get_children(self, column_collections=True,
                                schema_visitor=False, **kw):
        if not schema_visitor:
            return expression.TableClause.get_children(
                self, column_collections=column_collections, **kw)
        else:
            if column_collections:
                return list(self.columns)
            else:
                return []

    def exists(self, bind=None):
        """Return True if this table exists."""

        if bind is None:
            bind = _bind_or_error(self)

        return bind.run_callable(bind.dialect.has_table,
                                self.name, schema=self.schema)

    def create(self, bind=None, checkfirst=False):
        """Issue a ``CREATE`` statement for this
        :class:`.Table`, using the given :class:`.Connectable`
        for connectivity.

        .. seealso::

             :meth:`.MetaData.create_all`.

        """

        if bind is None:
            bind = _bind_or_error(self)
        bind._run_visitor(ddl.SchemaGenerator,
                            self,
                            checkfirst=checkfirst)

    def drop(self, bind=None, checkfirst=False):
        """Issue a ``DROP`` statement for this
        :class:`.Table`, using the given :class:`.Connectable`
        for connectivity.

        .. seealso::

            :meth:`.MetaData.drop_all`.

        """
        if bind is None:
            bind = _bind_or_error(self)
        bind._run_visitor(ddl.SchemaDropper,
                            self,
                            checkfirst=checkfirst)

    def tometadata(self, metadata, schema=RETAIN_SCHEMA):
        """Return a copy of this :class:`.Table` associated with a different
        :class:`.MetaData`.

        E.g.::

            some_engine = create_engine("sqlite:///some.db")

            # create two metadata
            meta1 = MetaData()
            meta2 = MetaData()

            # load 'users' from the sqlite engine
            users_table = Table('users', meta1, autoload=True,
                                    autoload_with=some_engine)

            # create the same Table object for the plain metadata
            users_table_2 = users_table.tometadata(meta2)

        :param metadata: Target :class:`.MetaData` object.
        :param schema: Optional string name of a target schema, or
         ``None`` for no schema.  The :class:`.Table` object will be
         given this schema name upon copy.   Defaults to the special
         symbol :attr:`.RETAIN_SCHEMA` which indicates no change should be
         made to the schema name of the resulting :class:`.Table`.

        """

        if schema is RETAIN_SCHEMA:
            schema = self.schema
        elif schema is None:
            schema = metadata.schema
        key = _get_table_key(self.name, schema)
        if key in metadata.tables:
            util.warn("Table '%s' already exists within the given "
                      "MetaData - not copying." % self.description)
            return metadata.tables[key]

        args = []
        for c in self.columns:
            args.append(c.copy(schema=schema))
        table = Table(
            self.name, metadata, schema=schema,
            *args, **self.kwargs
            )
        for c in self.constraints:
            table.append_constraint(c.copy(schema=schema, target_table=table))

        for index in self.indexes:
            # skip indexes that would be generated
            # by the 'index' flag on Column
            if len(index.columns) == 1 and \
                list(index.columns)[0].index:
                continue
            Index(index.name,
                  unique=index.unique,
                  *[table.c[col] for col in index.columns.keys()],
                  **index.kwargs)
        table.dispatch._update(self.dispatch)
        return table


class Column(SchemaItem, expression.ColumnClause):
    """Represents a column in a database table."""

    __visit_name__ = 'column'

    def __init__(self, *args, **kwargs):
        """
        Construct a new ``Column`` object.

        :param name: The name of this column as represented in the database.
          This argument may be the first positional argument, or specified
          via keyword.

          Names which contain no upper case characters
          will be treated as case insensitive names, and will not be quoted
          unless they are a reserved word.  Names with any number of upper
          case characters will be quoted and sent exactly.  Note that this
          behavior applies even for databases which standardize upper
          case names as case insensitive such as Oracle.

          The name field may be omitted at construction time and applied
          later, at any time before the Column is associated with a
          :class:`.Table`.  This is to support convenient
          usage within the :mod:`~sqlalchemy.ext.declarative` extension.

        :param type\_: The column's type, indicated using an instance which
          subclasses :class:`~sqlalchemy.types.TypeEngine`.  If no arguments
          are required for the type, the class of the type can be sent
          as well, e.g.::

            # use a type with arguments
            Column('data', String(50))

            # use no arguments
            Column('level', Integer)

          The ``type`` argument may be the second positional argument
          or specified by keyword.

          There is partial support for automatic detection of the
          type based on that of a :class:`.ForeignKey` associated
          with this column, if the type is specified as ``None``.
          However, this feature is not fully implemented and
          may not function in all cases.

        :param \*args: Additional positional arguments include various
          :class:`.SchemaItem` derived constructs which will be applied
          as options to the column.  These include instances of
          :class:`.Constraint`, :class:`.ForeignKey`, :class:`.ColumnDefault`,
          and :class:`.Sequence`.  In some cases an equivalent keyword
          argument is available such as ``server_default``, ``default``
          and ``unique``.

        :param autoincrement: This flag may be set to ``False`` to
          indicate an integer primary key column that should not be
          considered to be the "autoincrement" column, that is
          the integer primary key column which generates values
          implicitly upon INSERT and whose value is usually returned
          via the DBAPI cursor.lastrowid attribute.   It defaults
          to ``True`` to satisfy the common use case of a table
          with a single integer primary key column.  If the table
          has a composite primary key consisting of more than one
          integer column, set this flag to True only on the
          column that should be considered "autoincrement".

          The setting *only* has an effect for columns which are:

          * Integer derived (i.e. INT, SMALLINT, BIGINT).

          * Part of the primary key

          * Are not referenced by any foreign keys, unless
            the value is specified as ``'ignore_fk'``

            .. versionadded:: 0.7.4

          * have no server side or client side defaults (with the exception
            of Postgresql SERIAL).

          The setting has these two effects on columns that meet the
          above criteria:

          * DDL issued for the column will include database-specific
            keywords intended to signify this column as an
            "autoincrement" column, such as AUTO INCREMENT on MySQL,
            SERIAL on Postgresql, and IDENTITY on MS-SQL.  It does
            *not* issue AUTOINCREMENT for SQLite since this is a
            special SQLite flag that is not required for autoincrementing
            behavior.  See the SQLite dialect documentation for
            information on SQLite's AUTOINCREMENT.

          * The column will be considered to be available as
            cursor.lastrowid or equivalent, for those dialects which
            "post fetch" newly inserted identifiers after a row has
            been inserted (SQLite, MySQL, MS-SQL).  It does not have
            any effect in this regard for databases that use sequences
            to generate primary key identifiers (i.e. Firebird, Postgresql,
            Oracle).

          .. versionchanged:: 0.7.4
              ``autoincrement`` accepts a special value ``'ignore_fk'``
              to indicate that autoincrementing status regardless of foreign
              key references.  This applies to certain composite foreign key
              setups, such as the one demonstrated in the ORM documentation
              at :ref:`post_update`.

        :param default: A scalar, Python callable, or
            :class:`.ColumnElement` expression representing the
            *default value* for this column, which will be invoked upon insert
            if this column is otherwise not specified in the VALUES clause of
            the insert. This is a shortcut to using :class:`.ColumnDefault` as
            a positional argument; see that class for full detail on the
            structure of the argument.

            Contrast this argument to ``server_default`` which creates a
            default generator on the database side.

        :param doc: optional String that can be used by the ORM or similar
            to document attributes.   This attribute does not render SQL
            comments (a future attribute 'comment' will achieve that).

        :param key: An optional string identifier which will identify this
            ``Column`` object on the :class:`.Table`. When a key is provided,
            this is the only identifier referencing the ``Column`` within the
            application, including ORM attribute mapping; the ``name`` field
            is used only when rendering SQL.

        :param index: When ``True``, indicates that the column is indexed.
            This is a shortcut for using a :class:`.Index` construct on the
            table. To specify indexes with explicit names or indexes that
            contain multiple columns, use the :class:`.Index` construct
            instead.

        :param info: Optional data dictionary which will be populated into the
            :attr:`.SchemaItem.info` attribute of this object.

        :param nullable: If set to the default of ``True``, indicates the
            column will be rendered as allowing NULL, else it's rendered as
            NOT NULL. This parameter is only used when issuing CREATE TABLE
            statements.

        :param onupdate: A scalar, Python callable, or
            :class:`~sqlalchemy.sql.expression.ClauseElement` representing a
            default value to be applied to the column within UPDATE
            statements, which wil be invoked upon update if this column is not
            present in the SET clause of the update. This is a shortcut to
            using :class:`.ColumnDefault` as a positional argument with
            ``for_update=True``.

        :param primary_key: If ``True``, marks this column as a primary key
            column. Multiple columns can have this flag set to specify
            composite primary keys. As an alternative, the primary key of a
            :class:`.Table` can be specified via an explicit
            :class:`.PrimaryKeyConstraint` object.

        :param server_default: A :class:`.FetchedValue` instance, str, Unicode
            or :func:`~sqlalchemy.sql.expression.text` construct representing
            the DDL DEFAULT value for the column.

            String types will be emitted as-is, surrounded by single quotes::

                Column('x', Text, server_default="val")

                x TEXT DEFAULT 'val'

            A :func:`~sqlalchemy.sql.expression.text` expression will be
            rendered as-is, without quotes::

                Column('y', DateTime, server_default=text('NOW()'))0

                y DATETIME DEFAULT NOW()

            Strings and text() will be converted into a :class:`.DefaultClause`
            object upon initialization.

            Use :class:`.FetchedValue` to indicate that an already-existing
            column will generate a default value on the database side which
            will be available to SQLAlchemy for post-fetch after inserts. This
            construct does not specify any DDL and the implementation is left
            to the database, such as via a trigger.

        :param server_onupdate:   A :class:`.FetchedValue` instance
             representing a database-side default generation function. This
             indicates to SQLAlchemy that a newly generated value will be
             available after updates. This construct does not specify any DDL
             and the implementation is left to the database, such as via a
             trigger.

        :param quote: Force quoting of this column's name on or off,
             corresponding to ``True`` or ``False``. When left at its default
             of ``None``, the column identifier will be quoted according to
             whether the name is case sensitive (identifiers with at least one
             upper case character are treated as case sensitive), or if it's a
             reserved word. This flag is only needed to force quoting of a
             reserved word which is not known by the SQLAlchemy dialect.

        :param unique: When ``True``, indicates that this column contains a
             unique constraint, or if ``index`` is ``True`` as well, indicates
             that the :class:`.Index` should be created with the unique flag.
             To specify multiple columns in the constraint/index or to specify
             an explicit name, use the :class:`.UniqueConstraint` or
             :class:`.Index` constructs explicitly.

        :param system: When ``True``, indicates this is a "system" column,
             that is a column which is automatically made available by the
             database, and should not be included in the columns list for a
             ``CREATE TABLE`` statement.

             For more elaborate scenarios where columns should be conditionally
             rendered differently on different backends, consider custom
             compilation rules for :class:`.CreateColumn`.

             ..versionadded:: 0.8.3 Added the ``system=True`` parameter to
               :class:`.Column`.

        """

        name = kwargs.pop('name', None)
        type_ = kwargs.pop('type_', None)
        args = list(args)
        if args:
            if isinstance(args[0], basestring):
                if name is not None:
                    raise exc.ArgumentError(
                        "May not pass name positionally and as a keyword.")
                name = args.pop(0)
        if args:
            coltype = args[0]

            if (isinstance(coltype, sqltypes.TypeEngine) or
                (isinstance(coltype, type) and
                 issubclass(coltype, sqltypes.TypeEngine))):
                if type_ is not None:
                    raise exc.ArgumentError(
                        "May not pass type_ positionally and as a keyword.")
                type_ = args.pop(0)

        no_type = type_ is None

        super(Column, self).__init__(name, None, type_)
        self.key = kwargs.pop('key', name)
        self.primary_key = kwargs.pop('primary_key', False)
        self.nullable = kwargs.pop('nullable', not self.primary_key)
        self.default = kwargs.pop('default', None)
        self.server_default = kwargs.pop('server_default', None)
        self.server_onupdate = kwargs.pop('server_onupdate', None)

        # these default to None because .index and .unique is *not*
        # an informational flag about Column - there can still be an
        # Index or UniqueConstraint referring to this Column.
        self.index = kwargs.pop('index', None)
        self.unique = kwargs.pop('unique', None)

        self.system = kwargs.pop('system', False)
        self.quote = kwargs.pop('quote', None)
        self.doc = kwargs.pop('doc', None)
        self.onupdate = kwargs.pop('onupdate', None)
        self.autoincrement = kwargs.pop('autoincrement', True)
        self.constraints = set()
        self.foreign_keys = set()

        # check if this Column is proxying another column
        if '_proxies' in kwargs:
            self._proxies = kwargs.pop('_proxies')
        # otherwise, add DDL-related events
        elif isinstance(self.type, sqltypes.SchemaType):
            self.type._set_parent_with_dispatch(self)

        if self.default is not None:
            if isinstance(self.default, (ColumnDefault, Sequence)):
                args.append(self.default)
            else:
                if getattr(self.type, '_warn_on_bytestring', False):
                    # Py3K
                    #if isinstance(self.default, bytes):
                    # Py2K
                    if isinstance(self.default, str):
                    # end Py2K
                        util.warn("Unicode column received non-unicode "
                                  "default value.")
                args.append(ColumnDefault(self.default))

        if self.server_default is not None:
            if isinstance(self.server_default, FetchedValue):
                args.append(self.server_default._as_for_update(False))
            else:
                args.append(DefaultClause(self.server_default))

        if self.onupdate is not None:
            if isinstance(self.onupdate, (ColumnDefault, Sequence)):
                args.append(self.onupdate)
            else:
                args.append(ColumnDefault(self.onupdate, for_update=True))

        if self.server_onupdate is not None:
            if isinstance(self.server_onupdate, FetchedValue):
                args.append(self.server_onupdate._as_for_update(True))
            else:
                args.append(DefaultClause(self.server_onupdate,
                                            for_update=True))
        self._init_items(*args)

        if not self.foreign_keys and no_type:
            raise exc.ArgumentError("'type' is required on Column objects "
                                        "which have no foreign keys.")
        util.set_creation_order(self)

        if 'info' in kwargs:
            self.info = kwargs.pop('info')

        if kwargs:
            raise exc.ArgumentError(
                "Unknown arguments passed to Column: " + repr(kwargs.keys()))

    def __str__(self):
        if self.name is None:
            return "(no name)"
        elif self.table is not None:
            if self.table.named_with_column:
                return (self.table.description + "." + self.description)
            else:
                return self.description
        else:
            return self.description

    def references(self, column):
        """Return True if this Column references the given column via foreign
        key."""

        for fk in self.foreign_keys:
            if fk.column.proxy_set.intersection(column.proxy_set):
                return True
        else:
            return False

    def append_foreign_key(self, fk):
        fk._set_parent_with_dispatch(self)

    def __repr__(self):
        kwarg = []
        if self.key != self.name:
            kwarg.append('key')
        if self.primary_key:
            kwarg.append('primary_key')
        if not self.nullable:
            kwarg.append('nullable')
        if self.onupdate:
            kwarg.append('onupdate')
        if self.default:
            kwarg.append('default')
        if self.server_default:
            kwarg.append('server_default')
        return "Column(%s)" % ', '.join(
            [repr(self.name)] + [repr(self.type)] +
            [repr(x) for x in self.foreign_keys if x is not None] +
            [repr(x) for x in self.constraints] +
            [(self.table is not None and "table=<%s>" %
                    self.table.description or "table=None")] +
            ["%s=%s" % (k, repr(getattr(self, k))) for k in kwarg])

    def _set_parent(self, table):
        if not self.name:
            raise exc.ArgumentError(
                "Column must be constructed with a non-blank name or "
                "assign a non-blank .name before adding to a Table.")
        if self.key is None:
            self.key = self.name

        existing = getattr(self, 'table', None)
        if existing is not None and existing is not table:
            raise exc.ArgumentError(
                    "Column object already assigned to Table '%s'" %
                    existing.description)

        if self.key in table._columns:
            col = table._columns.get(self.key)
            if col is not self:
                for fk in list(col.foreign_keys):
                    table.foreign_keys.remove(fk)
                    if fk.constraint in table.constraints:
                        # this might have been removed
                        # already, if it's a composite constraint
                        # and more than one col being replaced
                        table.constraints.remove(fk.constraint)

        table._columns.replace(self)

        if self.primary_key:
            table.primary_key._replace(self)
            Table._autoincrement_column._reset(table)
        elif self.key in table.primary_key:
            raise exc.ArgumentError(
                "Trying to redefine primary-key column '%s' as a "
                "non-primary-key column on table '%s'" % (
                self.key, table.fullname))
        self.table = table

        if self.index:
            if isinstance(self.index, basestring):
                raise exc.ArgumentError(
                    "The 'index' keyword argument on Column is boolean only. "
                    "To create indexes with a specific name, create an "
                    "explicit Index object external to the Table.")
            Index(expression._truncated_label('ix_%s' % self._label),
                                    self, unique=bool(self.unique))
        elif self.unique:
            if isinstance(self.unique, basestring):
                raise exc.ArgumentError(
                    "The 'unique' keyword argument on Column is boolean "
                    "only. To create unique constraints or indexes with a "
                    "specific name, append an explicit UniqueConstraint to "
                    "the Table's list of elements, or create an explicit "
                    "Index object external to the Table.")
            table.append_constraint(UniqueConstraint(self.key))

    def _on_table_attach(self, fn):
        if self.table is not None:
            fn(self, self.table)
        event.listen(self, 'after_parent_attach', fn)

    def copy(self, **kw):
        """Create a copy of this ``Column``, unitialized.

        This is used in ``Table.tometadata``.

        """

        # Constraint objects plus non-constraint-bound ForeignKey objects
        args = \
            [c.copy(**kw) for c in self.constraints] + \
            [c.copy(**kw) for c in self.foreign_keys if not c.constraint]

        type_ = self.type
        if isinstance(type_, sqltypes.SchemaType):
            type_ = type_.copy(**kw)

        c = self._constructor(
                name=self.name,
                type_=type_,
                key=self.key,
                primary_key=self.primary_key,
                nullable=self.nullable,
                unique=self.unique,
                system=self.system,
                quote=self.quote,
                index=self.index,
                autoincrement=self.autoincrement,
                default=self.default,
                server_default=self.server_default,
                onupdate=self.onupdate,
                server_onupdate=self.server_onupdate,
                info=self.info,
                doc=self.doc,
                *args
                )
        c.dispatch._update(self.dispatch)
        return c

    def _make_proxy(self, selectable, name=None, key=None,
                            name_is_truncatable=False, **kw):
        """Create a *proxy* for this column.

        This is a copy of this ``Column`` referenced by a different parent
        (such as an alias or select statement).  The column should
        be used only in select scenarios, as its full DDL/default
        information is not transferred.

        """
        fk = [ForeignKey(f.column, _constraint=f.constraint)
                for f in self.foreign_keys]
        if name is None and self.name is None:
            raise exc.InvalidRequestError("Cannot initialize a sub-selectable"
                    " with this Column object until it's 'name' has "
                    "been assigned.")
        try:
            c = self._constructor(
                expression._as_truncated(name or self.name) if \
                                name_is_truncatable else (name or self.name),
                self.type,
                key=key if key else name if name else self.key,
                primary_key=self.primary_key,
                nullable=self.nullable,
                quote=self.quote,
                _proxies=[self], *fk)
        except TypeError, e:
            # Py3K
            #raise TypeError(
            #    "Could not create a copy of this %r object.  "
            #    "Ensure the class includes a _constructor() "
            #    "attribute or method which accepts the "
            #    "standard Column constructor arguments, or "
            #    "references the Column class itself." % self.__class__) from e
            # Py2K
            raise TypeError(
                "Could not create a copy of this %r object.  "
                "Ensure the class includes a _constructor() "
                "attribute or method which accepts the "
                "standard Column constructor arguments, or "
                "references the Column class itself. "
                "Original error: %s" % (self.__class__, e))
            # end Py2K

        c.table = selectable
        selectable._columns.add(c)
        if selectable._is_clone_of is not None:
            c._is_clone_of = selectable._is_clone_of.columns[c.key]
        if self.primary_key:
            selectable.primary_key.add(c)
        c.dispatch.after_parent_attach(c, selectable)
        return c

    def get_children(self, schema_visitor=False, **kwargs):
        if schema_visitor:
            return [x for x in (self.default, self.onupdate)
                    if x is not None] + \
                list(self.foreign_keys) + list(self.constraints)
        else:
            return expression.ColumnClause.get_children(self, **kwargs)


class ForeignKey(SchemaItem):
    """Defines a dependency between two columns.

    ``ForeignKey`` is specified as an argument to a :class:`.Column` object,
    e.g.::

        t = Table("remote_table", metadata,
            Column("remote_id", ForeignKey("main_table.id"))
        )

    Note that ``ForeignKey`` is only a marker object that defines
    a dependency between two columns.   The actual constraint
    is in all cases represented by the :class:`.ForeignKeyConstraint`
    object.   This object will be generated automatically when
    a ``ForeignKey`` is associated with a :class:`.Column` which
    in turn is associated with a :class:`.Table`.   Conversely,
    when :class:`.ForeignKeyConstraint` is applied to a :class:`.Table`,
    ``ForeignKey`` markers are automatically generated to be
    present on each associated :class:`.Column`, which are also
    associated with the constraint object.

    Note that you cannot define a "composite" foreign key constraint,
    that is a constraint between a grouping of multiple parent/child
    columns, using ``ForeignKey`` objects.   To define this grouping,
    the :class:`.ForeignKeyConstraint` object must be used, and applied
    to the :class:`.Table`.   The associated ``ForeignKey`` objects
    are created automatically.

    The ``ForeignKey`` objects associated with an individual
    :class:`.Column` object are available in the `foreign_keys` collection
    of that column.

    Further examples of foreign key configuration are in
    :ref:`metadata_foreignkeys`.

    """

    __visit_name__ = 'foreign_key'

    def __init__(self, column, _constraint=None, use_alter=False, name=None,
                    onupdate=None, ondelete=None, deferrable=None,
                    schema=None,
                    initially=None, link_to_name=False, match=None):
        """
        Construct a column-level FOREIGN KEY.

        The :class:`.ForeignKey` object when constructed generates a
        :class:`.ForeignKeyConstraint` which is associated with the parent
        :class:`.Table` object's collection of constraints.

        :param column: A single target column for the key relationship. A
            :class:`.Column` object or a column name as a string:
            ``tablename.columnkey`` or ``schema.tablename.columnkey``.
            ``columnkey`` is the ``key`` which has been assigned to the column
            (defaults to the column name itself), unless ``link_to_name`` is
            ``True`` in which case the rendered name of the column is used.

            .. versionadded:: 0.7.4
                Note that if the schema name is not included, and the
                underlying :class:`.MetaData` has a "schema", that value will
                be used.

        :param name: Optional string. An in-database name for the key if
            `constraint` is not provided.

        :param onupdate: Optional string. If set, emit ON UPDATE <value> when
            issuing DDL for this constraint. Typical values include CASCADE,
            DELETE and RESTRICT.

        :param ondelete: Optional string. If set, emit ON DELETE <value> when
            issuing DDL for this constraint. Typical values include CASCADE,
            DELETE and RESTRICT.

        :param deferrable: Optional bool. If set, emit DEFERRABLE or NOT
            DEFERRABLE when issuing DDL for this constraint.

        :param initially: Optional string. If set, emit INITIALLY <value> when
            issuing DDL for this constraint.

        :param link_to_name: if True, the string name given in ``column`` is
            the rendered name of the referenced column, not its locally
            assigned ``key``.

        :param use_alter: passed to the underlying
            :class:`.ForeignKeyConstraint` to indicate the constraint should be
            generated/dropped externally from the CREATE TABLE/ DROP TABLE
            statement. See that classes' constructor for details.

        :param match: Optional string. If set, emit MATCH <value> when issuing
            DDL for this constraint. Typical values include SIMPLE, PARTIAL
            and FULL.

        :param schema: Deprecated; this flag does nothing and will be removed
            in 0.9.
        """

        self._colspec = column

        # the linked ForeignKeyConstraint.
        # ForeignKey will create this when parent Column
        # is attached to a Table, *or* ForeignKeyConstraint
        # object passes itself in when creating ForeignKey
        # markers.
        self.constraint = _constraint

        self.use_alter = use_alter
        self.name = name
        self.onupdate = onupdate
        self.ondelete = ondelete
        self.deferrable = deferrable
        self.initially = initially
        self.link_to_name = link_to_name
        self.match = match

        if schema:
            util.warn_deprecated(
                "'schema' argument on ForeignKey has no effect - "
                "please specify the target as "
                "<schemaname>.<tablename>.<colname>.")

    def __repr__(self):
        return "ForeignKey(%r)" % self._get_colspec()

    def copy(self, schema=None):
        """Produce a copy of this :class:`.ForeignKey` object.

        The new :class:`.ForeignKey` will not be bound
        to any :class:`.Column`.

        This method is usually used by the internal
        copy procedures of :class:`.Column`, :class:`.Table`,
        and :class:`.MetaData`.

        :param schema: The returned :class:`.ForeignKey` will
          reference the original table and column name, qualified
          by the given string schema name.

        """

        fk = ForeignKey(
                self._get_colspec(schema=schema),
                use_alter=self.use_alter,
                name=self.name,
                onupdate=self.onupdate,
                ondelete=self.ondelete,
                deferrable=self.deferrable,
                initially=self.initially,
                link_to_name=self.link_to_name,
                match=self.match
                )
        fk.dispatch._update(self.dispatch)
        return fk

    def _get_colspec(self, schema=None):
        """Return a string based 'column specification' for this
        :class:`.ForeignKey`.

        This is usually the equivalent of the string-based "tablename.colname"
        argument first passed to the object's constructor.

        """
        if schema:
            return schema + "." + self.column.table.name + \
                                    "." + self.column.key
        elif isinstance(self._colspec, basestring):
            return self._colspec
        elif hasattr(self._colspec, '__clause_element__'):
            _column = self._colspec.__clause_element__()
        else:
            _column = self._colspec

        return "%s.%s" % (_column.table.fullname, _column.key)

    target_fullname = property(_get_colspec)

    def references(self, table):
        """Return True if the given :class:`.Table` is referenced by this
        :class:`.ForeignKey`."""

        return table.corresponding_column(self.column) is not None

    def get_referent(self, table):
        """Return the :class:`.Column` in the given :class:`.Table`
        referenced by this :class:`.ForeignKey`.

        Returns None if this :class:`.ForeignKey` does not reference the given
        :class:`.Table`.

        """

        return table.corresponding_column(self.column)

    @util.memoized_property
    def column(self):
        """Return the target :class:`.Column` referenced by this
        :class:`.ForeignKey`.

        If this :class:`.ForeignKey` was created using a
        string-based target column specification, this
        attribute will on first access initiate a resolution
        process to locate the referenced remote
        :class:`.Column`.  The resolution process traverses
        to the parent :class:`.Column`, :class:`.Table`, and
        :class:`.MetaData` to proceed - if any of these aren't
        yet present, an error is raised.

        """
        # ForeignKey inits its remote column as late as possible, so tables
        # can be defined without dependencies
        if isinstance(self._colspec, basestring):
            # locate the parent table this foreign key is attached to.  we
            # use the "original" column which our parent column represents
            # (its a list of columns/other ColumnElements if the parent
            # table is a UNION)
            for c in self.parent.base_columns:
                if isinstance(c, Column):
                    parenttable = c.table
                    break
            else:
                raise exc.ArgumentError(
                    "Parent column '%s' does not descend from a "
                    "table-attached Column" % str(self.parent))

            m = self._colspec.split('.')

            if m is None:
                raise exc.ArgumentError(
                    "Invalid foreign key column specification: %s" %
                    self._colspec)

            # A FK between column 'bar' and table 'foo' can be
            # specified as 'foo', 'foo.bar', 'dbo.foo.bar',
            # 'otherdb.dbo.foo.bar'. Once we have the column name and
            # the table name, treat everything else as the schema
            # name. Some databases (e.g. Sybase) support
            # inter-database foreign keys. See tickets#1341 and --
            # indirectly related -- Ticket #594. This assumes that '.'
            # will never appear *within* any component of the FK.

            (schema, tname, colname) = (None, None, None)
            if schema is None and parenttable.metadata.schema is not None:
                schema = parenttable.metadata.schema

            if (len(m) == 1):
                tname = m.pop()
            else:
                colname = m.pop()
                tname = m.pop()

            if (len(m) > 0):
                schema = '.'.join(m)

            if _get_table_key(tname, schema) not in parenttable.metadata:
                raise exc.NoReferencedTableError(
                    "Foreign key associated with column '%s' could not find "
                    "table '%s' with which to generate a "
                    "foreign key to target column '%s'" %
                    (self.parent, tname, colname),
                    tname)
            table = Table(tname, parenttable.metadata,
                          mustexist=True, schema=schema)

            if not hasattr(self.constraint, '_referred_table'):
                self.constraint._referred_table = table
            elif self.constraint._referred_table is not table:
                raise exc.ArgumentError(
                    'ForeignKeyConstraint on %s(%s) refers to '
                    'multiple remote tables: %s and %s' % (
                    parenttable,
                    self.constraint._col_description,
                    self.constraint._referred_table,
                    table
                ))

            _column = None
            if colname is None:
                # colname is None in the case that ForeignKey argument
                # was specified as table name only, in which case we
                # match the column name to the same column on the
                # parent.
                key = self.parent
                _column = table.c.get(self.parent.key, None)
            elif self.link_to_name:
                key = colname
                for c in table.c:
                    if c.name == colname:
                        _column = c
            else:
                key = colname
                _column = table.c.get(colname, None)

            if _column is None:
                raise exc.NoReferencedColumnError(
                    "Could not create ForeignKey '%s' on table '%s': "
                    "table '%s' has no column named '%s'" % (
                    self._colspec, parenttable.name, table.name, key),
                    table.name, key)

        elif hasattr(self._colspec, '__clause_element__'):
            _column = self._colspec.__clause_element__()
        else:
            _column = self._colspec

        # propagate TypeEngine to parent if it didn't have one
        if isinstance(self.parent.type, sqltypes.NullType):
            self.parent.type = _column.type
        return _column

    def _set_parent(self, column):
        if hasattr(self, 'parent'):
            if self.parent is column:
                return
            raise exc.InvalidRequestError(
                    "This ForeignKey already has a parent !")
        self.parent = column
        self.parent.foreign_keys.add(self)
        self.parent._on_table_attach(self._set_table)

    def _set_table(self, column, table):
        # standalone ForeignKey - create ForeignKeyConstraint
        # on the hosting Table when attached to the Table.
        if self.constraint is None and isinstance(table, Table):
            self.constraint = ForeignKeyConstraint(
                [], [], use_alter=self.use_alter, name=self.name,
                onupdate=self.onupdate, ondelete=self.ondelete,
                deferrable=self.deferrable, initially=self.initially,
                match=self.match,
                )
            self.constraint._elements[self.parent] = self
            self.constraint._set_parent_with_dispatch(table)
        table.foreign_keys.add(self)


class _NotAColumnExpr(object):
    def _not_a_column_expr(self):
        raise exc.InvalidRequestError(
                "This %s cannot be used directly "
                "as a column expression." % self.__class__.__name__)

    __clause_element__ = self_group = lambda self: self._not_a_column_expr()
    _from_objects = property(lambda self: self._not_a_column_expr())


class DefaultGenerator(_NotAColumnExpr, SchemaItem):
    """Base class for column *default* values."""

    __visit_name__ = 'default_generator'

    is_sequence = False
    is_server_default = False
    column = None

    def __init__(self, for_update=False):
        self.for_update = for_update

    def _set_parent(self, column):
        self.column = column
        if self.for_update:
            self.column.onupdate = self
        else:
            self.column.default = self

    def execute(self, bind=None, **kwargs):
        if bind is None:
            bind = _bind_or_error(self)
        return bind._execute_default(self, **kwargs)

    @property
    def bind(self):
        """Return the connectable associated with this default."""
        if getattr(self, 'column', None) is not None:
            return self.column.table.bind
        else:
            return None


class ColumnDefault(DefaultGenerator):
    """A plain default value on a column.

    This could correspond to a constant, a callable function,
    or a SQL clause.

    :class:`.ColumnDefault` is generated automatically
    whenever the ``default``, ``onupdate`` arguments of
    :class:`.Column` are used.  A :class:`.ColumnDefault`
    can be passed positionally as well.

    For example, the following::

        Column('foo', Integer, default=50)

    Is equivalent to::

        Column('foo', Integer, ColumnDefault(50))


    """

    def __init__(self, arg, **kwargs):
        """"Construct a new :class:`.ColumnDefault`.


        :param arg: argument representing the default value.
         May be one of the following:

         * a plain non-callable Python value, such as a
           string, integer, boolean, or other simple type.
           The default value will be used as is each time.
         * a SQL expression, that is one which derives from
           :class:`.ColumnElement`.  The SQL expression will
           be rendered into the INSERT or UPDATE statement,
           or in the case of a primary key column when
           RETURNING is not used may be
           pre-executed before an INSERT within a SELECT.
         * A Python callable.  The function will be invoked for each
           new row subject to an INSERT or UPDATE.
           The callable must accept exactly
           zero or one positional arguments.  The one-argument form
           will receive an instance of the :class:`.ExecutionContext`,
           which provides contextual information as to the current
           :class:`.Connection` in use as well as the current
           statement and parameters.

        """
        super(ColumnDefault, self).__init__(**kwargs)
        if isinstance(arg, FetchedValue):
            raise exc.ArgumentError(
                "ColumnDefault may not be a server-side default type.")
        if util.callable(arg):
            arg = self._maybe_wrap_callable(arg)
        self.arg = arg

    @util.memoized_property
    def is_callable(self):
        return util.callable(self.arg)

    @util.memoized_property
    def is_clause_element(self):
        return isinstance(self.arg, expression.ClauseElement)

    @util.memoized_property
    def is_scalar(self):
        return not self.is_callable and \
                    not self.is_clause_element and \
                    not self.is_sequence

    def _maybe_wrap_callable(self, fn):
        """Wrap callables that don't accept a context.

        The alternative here is to require that
        a simple callable passed to "default" would need
        to be of the form "default=lambda ctx: datetime.now".
        That is the more "correct" way to go, but the case
        of using a zero-arg callable for "default" is so
        much more prominent than the context-specific one
        I'm having trouble justifying putting that inconvenience
        on everyone.

        """
        if inspect.isfunction(fn):
            inspectable = fn
        elif inspect.isclass(fn):
            inspectable = fn.__init__
        elif hasattr(fn, '__call__'):
            inspectable = fn.__call__
        else:
            # probably not inspectable, try anyways.
            inspectable = fn
        try:
            argspec = inspect.getargspec(inspectable)
        except TypeError:
            return lambda ctx: fn()

        defaulted = argspec[3] is not None and len(argspec[3]) or 0
        positionals = len(argspec[0]) - defaulted

        # Py3K compat - no unbound methods
        if inspect.ismethod(inspectable) or inspect.isclass(fn):
            positionals -= 1

        if positionals == 0:
            return lambda ctx: fn()
        elif positionals == 1:
            return fn
        else:
            raise exc.ArgumentError(
                "ColumnDefault Python function takes zero or one "
                "positional arguments")

    def _visit_name(self):
        if self.for_update:
            return "column_onupdate"
        else:
            return "column_default"
    __visit_name__ = property(_visit_name)

    def __repr__(self):
        return "ColumnDefault(%r)" % self.arg


class Sequence(DefaultGenerator):
    """Represents a named database sequence.

    The :class:`.Sequence` object represents the name and configurational
    parameters of a database sequence.   It also represents
    a construct that can be "executed" by a SQLAlchemy :class:`.Engine`
    or :class:`.Connection`, rendering the appropriate "next value" function
    for the target database and returning a result.

    The :class:`.Sequence` is typically associated with a primary key column::

        some_table = Table('some_table', metadata,
            Column('id', Integer, Sequence('some_table_seq'), primary_key=True)
        )

    When CREATE TABLE is emitted for the above :class:`.Table`, if the
    target platform supports sequences, a CREATE SEQUENCE statement will
    be emitted as well.   For platforms that don't support sequences,
    the :class:`.Sequence` construct is ignored.

    .. seealso::

        :class:`.CreateSequence`

        :class:`.DropSequence`

    """

    __visit_name__ = 'sequence'

    is_sequence = True

    def __init__(self, name, start=None, increment=None, schema=None,
                 optional=False, quote=None, metadata=None,
                 quote_schema=None,
                 for_update=False):
        """Construct a :class:`.Sequence` object.

        :param name: The name of the sequence.
        :param start: the starting index of the sequence.  This value is
         used when the CREATE SEQUENCE command is emitted to the database
         as the value of the "START WITH" clause.   If ``None``, the
         clause is omitted, which on most platforms indicates a starting
         value of 1.
        :param increment: the increment value of the sequence.  This
         value is used when the CREATE SEQUENCE command is emitted to
         the database as the value of the "INCREMENT BY" clause.  If ``None``,
         the clause is omitted, which on most platforms indicates an
         increment of 1.
        :param schema: Optional schema name for the sequence, if located
         in a schema other than the default.
        :param optional: boolean value, when ``True``, indicates that this
         :class:`.Sequence` object only needs to be explicitly generated
         on backends that don't provide another way to generate primary
         key identifiers.  Currently, it essentially means, "don't create
         this sequence on the Postgresql backend, where the SERIAL keyword
         creates a sequence for us automatically".
        :param quote: boolean value, when ``True`` or ``False``, explicitly
         forces quoting of the schema name on or off.  When left at its
         default of ``None``, normal quoting rules based on casing and reserved
         words take place.
        :param metadata: optional :class:`.MetaData` object which will be
         associated with this :class:`.Sequence`.  A :class:`.Sequence`
         that is associated with a :class:`.MetaData` gains access to the
         ``bind`` of that :class:`.MetaData`, meaning the
         :meth:`.Sequence.create` and :meth:`.Sequence.drop` methods will
         make usage of that engine automatically.

         .. versionchanged:: 0.7
             Additionally, the appropriate CREATE SEQUENCE/
             DROP SEQUENCE DDL commands will be emitted corresponding to this
             :class:`.Sequence` when :meth:`.MetaData.create_all` and
             :meth:`.MetaData.drop_all` are invoked.

         Note that when a :class:`.Sequence` is applied to a :class:`.Column`,
         the :class:`.Sequence` is automatically associated with the
         :class:`.MetaData` object of that column's parent :class:`.Table`,
         when that association is made.   The :class:`.Sequence` will then
         be subject to automatic CREATE SEQUENCE/DROP SEQUENCE corresponding
         to when the :class:`.Table` object itself is created or dropped,
         rather than that of the :class:`.MetaData` object overall.
        :param for_update: Indicates this :class:`.Sequence`, when associated
         with a :class:`.Column`, should be invoked for UPDATE statements
         on that column's table, rather than for INSERT statements, when
         no value is otherwise present for that column in the statement.

        """
        super(Sequence, self).__init__(for_update=for_update)
        self.name = name
        self.start = start
        self.increment = increment
        self.optional = optional
        self.quote = quote
        if metadata is not None and schema is None and metadata.schema:
            self.schema = schema = metadata.schema
            self.quote_schema = metadata.quote_schema
        else:
            self.schema = schema
            self.quote_schema = quote_schema
        self.metadata = metadata
        self._key = _get_table_key(name, schema)
        if metadata:
            self._set_metadata(metadata)

    @util.memoized_property
    def is_callable(self):
        return False

    @util.memoized_property
    def is_clause_element(self):
        return False

    def next_value(self):
        """Return a :class:`.next_value` function element
        which will render the appropriate increment function
        for this :class:`.Sequence` within any SQL expression.

        """
        return expression.func.next_value(self, bind=self.bind)

    def _set_parent(self, column):
        super(Sequence, self)._set_parent(column)
        column._on_table_attach(self._set_table)

    def _set_table(self, column, table):
        self._set_metadata(table.metadata)

    def _set_metadata(self, metadata):
        self.metadata = metadata
        self.metadata._sequences[self._key] = self

    @property
    def bind(self):
        if self.metadata:
            return self.metadata.bind
        else:
            return None

    def create(self, bind=None, checkfirst=True):
        """Creates this sequence in the database."""

        if bind is None:
            bind = _bind_or_error(self)
        bind._run_visitor(ddl.SchemaGenerator,
                            self,
                            checkfirst=checkfirst)

    def drop(self, bind=None, checkfirst=True):
        """Drops this sequence from the database."""

        if bind is None:
            bind = _bind_or_error(self)
        bind._run_visitor(ddl.SchemaDropper,
                            self,
                            checkfirst=checkfirst)

    def _not_a_column_expr(self):
        raise exc.InvalidRequestError(
                "This %s cannot be used directly "
                "as a column expression.  Use func.next_value(sequence) "
                "to produce a 'next value' function that's usable "
                "as a column element."
                % self.__class__.__name__)


class FetchedValue(_NotAColumnExpr, events.SchemaEventTarget):
    """A marker for a transparent database-side default.

    Use :class:`.FetchedValue` when the database is configured
    to provide some automatic default for a column.

    E.g.::

        Column('foo', Integer, FetchedValue())

    Would indicate that some trigger or default generator
    will create a new value for the ``foo`` column during an
    INSERT.

    .. seealso::

        :ref:`triggered_columns`

    """
    is_server_default = True
    reflected = False
    has_argument = False

    def __init__(self, for_update=False):
        self.for_update = for_update

    def _as_for_update(self, for_update):
        if for_update == self.for_update:
            return self
        else:
            return self._clone(for_update)

    def _clone(self, for_update):
        n = self.__class__.__new__(self.__class__)
        n.__dict__.update(self.__dict__)
        n.__dict__.pop('column', None)
        n.for_update = for_update
        return n

    def _set_parent(self, column):
        self.column = column
        if self.for_update:
            self.column.server_onupdate = self
        else:
            self.column.server_default = self

    def __repr__(self):
        return util.generic_repr(self)

inspection._self_inspects(FetchedValue)


class DefaultClause(FetchedValue):
    """A DDL-specified DEFAULT column value.

    :class:`.DefaultClause` is a :class:`.FetchedValue`
    that also generates a "DEFAULT" clause when
    "CREATE TABLE" is emitted.

    :class:`.DefaultClause` is generated automatically
    whenever the ``server_default``, ``server_onupdate`` arguments of
    :class:`.Column` are used.  A :class:`.DefaultClause`
    can be passed positionally as well.

    For example, the following::

        Column('foo', Integer, server_default="50")

    Is equivalent to::

        Column('foo', Integer, DefaultClause("50"))

    """

    has_argument = True

    def __init__(self, arg, for_update=False, _reflected=False):
        util.assert_arg_type(arg, (basestring,
                                   expression.ClauseElement,
                                   expression.TextClause), 'arg')
        super(DefaultClause, self).__init__(for_update)
        self.arg = arg
        self.reflected = _reflected

    def __repr__(self):
        return "DefaultClause(%r, for_update=%r)" % \
                        (self.arg, self.for_update)


class PassiveDefault(DefaultClause):
    """A DDL-specified DEFAULT column value.

    .. deprecated:: 0.6
        :class:`.PassiveDefault` is deprecated.
        Use :class:`.DefaultClause`.
    """
    @util.deprecated("0.6",
                ":class:`.PassiveDefault` is deprecated.  "
                "Use :class:`.DefaultClause`.",
                False)
    def __init__(self, *arg, **kw):
        DefaultClause.__init__(self, *arg, **kw)


class Constraint(SchemaItem):
    """A table-level SQL constraint."""

    __visit_name__ = 'constraint'

    def __init__(self, name=None, deferrable=None, initially=None,
                            _create_rule=None,
                            **kw):
        """Create a SQL constraint.

        :param name:
          Optional, the in-database name of this ``Constraint``.

        :param deferrable:
          Optional bool.  If set, emit DEFERRABLE or NOT DEFERRABLE when
          issuing DDL for this constraint.

        :param initially:
          Optional string.  If set, emit INITIALLY <value> when issuing DDL
          for this constraint.

        :param _create_rule:
          a callable which is passed the DDLCompiler object during
          compilation. Returns True or False to signal inline generation of
          this Constraint.

          The AddConstraint and DropConstraint DDL constructs provide
          DDLElement's more comprehensive "conditional DDL" approach that is
          passed a database connection when DDL is being issued. _create_rule
          is instead called during any CREATE TABLE compilation, where there
          may not be any transaction/connection in progress. However, it
          allows conditional compilation of the constraint even for backends
          which do not support addition of constraints through ALTER TABLE,
          which currently includes SQLite.

          _create_rule is used by some types to create constraints.
          Currently, its call signature is subject to change at any time.

        :param \**kwargs:
          Dialect-specific keyword parameters, see the documentation
          for various dialects and constraints regarding options here.

        """

        self.name = name
        self.deferrable = deferrable
        self.initially = initially
        self._create_rule = _create_rule
        util.set_creation_order(self)
        _validate_dialect_kwargs(kw, self.__class__.__name__)
        self.kwargs = kw

    @property
    def table(self):
        try:
            if isinstance(self.parent, Table):
                return self.parent
        except AttributeError:
            pass
        raise exc.InvalidRequestError(
                    "This constraint is not bound to a table.  Did you "
                    "mean to call table.append_constraint(constraint) ?")

    def _set_parent(self, parent):
        self.parent = parent
        parent.constraints.add(self)

    def copy(self, **kw):
        raise NotImplementedError()


class ColumnCollectionMixin(object):
    def __init__(self, *columns):
        self.columns = expression.ColumnCollection()
        self._pending_colargs = [_to_schema_column_or_string(c)
                                    for c in columns]
        if self._pending_colargs and \
                isinstance(self._pending_colargs[0], Column) and \
                isinstance(self._pending_colargs[0].table, Table):
            self._set_parent_with_dispatch(self._pending_colargs[0].table)

    def _set_parent(self, table):
        for col in self._pending_colargs:
            if isinstance(col, basestring):
                col = table.c[col]
            self.columns.add(col)


class ColumnCollectionConstraint(ColumnCollectionMixin, Constraint):
    """A constraint that proxies a ColumnCollection."""

    def __init__(self, *columns, **kw):
        """
        :param \*columns:
          A sequence of column names or Column objects.

        :param name:
          Optional, the in-database name of this constraint.

        :param deferrable:
          Optional bool.  If set, emit DEFERRABLE or NOT DEFERRABLE when
          issuing DDL for this constraint.

        :param initially:
          Optional string.  If set, emit INITIALLY <value> when issuing DDL
          for this constraint.

        """
        ColumnCollectionMixin.__init__(self, *columns)
        Constraint.__init__(self, **kw)

    def _set_parent(self, table):
        ColumnCollectionMixin._set_parent(self, table)
        Constraint._set_parent(self, table)

    def __contains__(self, x):
        return x in self.columns

    def copy(self, **kw):
        c = self.__class__(name=self.name, deferrable=self.deferrable,
                              initially=self.initially, *self.columns.keys())
        c.dispatch._update(self.dispatch)
        return c

    def contains_column(self, col):
        return self.columns.contains_column(col)

    def __iter__(self):
        # inlining of
        # return iter(self.columns)
        # ColumnCollection->OrderedProperties->OrderedDict
        ordered_dict = self.columns._data
        return (ordered_dict[key] for key in ordered_dict._list)

    def __len__(self):
        return len(self.columns._data)


class CheckConstraint(Constraint):
    """A table- or column-level CHECK constraint.

    Can be included in the definition of a Table or Column.
    """

    def __init__(self, sqltext, name=None, deferrable=None,
                    initially=None, table=None, _create_rule=None,
                    _autoattach=True):
        """Construct a CHECK constraint.

        :param sqltext:
          A string containing the constraint definition, which will be used
          verbatim, or a SQL expression construct.

        :param name:
          Optional, the in-database name of the constraint.

        :param deferrable:
          Optional bool.  If set, emit DEFERRABLE or NOT DEFERRABLE when
          issuing DDL for this constraint.

        :param initially:
          Optional string.  If set, emit INITIALLY <value> when issuing DDL
          for this constraint.

        """

        super(CheckConstraint, self).\
                        __init__(name, deferrable, initially, _create_rule)
        self.sqltext = expression._literal_as_text(sqltext)
        if table is not None:
            self._set_parent_with_dispatch(table)
        elif _autoattach:
            cols = sqlutil.find_columns(self.sqltext)
            tables = set([c.table for c in cols
                        if isinstance(c.table, Table)])
            if len(tables) == 1:
                self._set_parent_with_dispatch(
                        tables.pop())

    def __visit_name__(self):
        if isinstance(self.parent, Table):
            return "check_constraint"
        else:
            return "column_check_constraint"
    __visit_name__ = property(__visit_name__)

    def copy(self, target_table=None, **kw):
        if target_table is not None:
            def replace(col):
                if self.table.c.contains_column(col):
                    return target_table.c[col.key]
                else:
                    return None
            sqltext = visitors.replacement_traverse(self.sqltext, {}, replace)
        else:
            sqltext = self.sqltext
        c = CheckConstraint(sqltext,
                                name=self.name,
                                initially=self.initially,
                                deferrable=self.deferrable,
                                _create_rule=self._create_rule,
                                table=target_table,
                                _autoattach=False)
        c.dispatch._update(self.dispatch)
        return c


class ForeignKeyConstraint(Constraint):
    """A table-level FOREIGN KEY constraint.

    Defines a single column or composite FOREIGN KEY ... REFERENCES
    constraint. For a no-frills, single column foreign key, adding a
    :class:`.ForeignKey` to the definition of a :class:`.Column` is a shorthand
    equivalent for an unnamed, single column :class:`.ForeignKeyConstraint`.

    Examples of foreign key configuration are in :ref:`metadata_foreignkeys`.

    """
    __visit_name__ = 'foreign_key_constraint'

    def __init__(self, columns, refcolumns, name=None, onupdate=None,
            ondelete=None, deferrable=None, initially=None, use_alter=False,
            link_to_name=False, match=None, table=None):
        """Construct a composite-capable FOREIGN KEY.

        :param columns: A sequence of local column names. The named columns
          must be defined and present in the parent Table. The names should
          match the ``key`` given to each column (defaults to the name) unless
          ``link_to_name`` is True.

        :param refcolumns: A sequence of foreign column names or Column
          objects. The columns must all be located within the same Table.

        :param name: Optional, the in-database name of the key.

        :param onupdate: Optional string. If set, emit ON UPDATE <value> when
          issuing DDL for this constraint. Typical values include CASCADE,
          DELETE and RESTRICT.

        :param ondelete: Optional string. If set, emit ON DELETE <value> when
          issuing DDL for this constraint. Typical values include CASCADE,
          DELETE and RESTRICT.

        :param deferrable: Optional bool. If set, emit DEFERRABLE or NOT
          DEFERRABLE when issuing DDL for this constraint.

        :param initially: Optional string. If set, emit INITIALLY <value> when
          issuing DDL for this constraint.

        :param link_to_name: if True, the string name given in ``column`` is
          the rendered name of the referenced column, not its locally assigned
          ``key``.

        :param use_alter: If True, do not emit the DDL for this constraint as
          part of the CREATE TABLE definition. Instead, generate it via an
          ALTER TABLE statement issued after the full collection of tables
          have been created, and drop it via an ALTER TABLE statement before
          the full collection of tables are dropped. This is shorthand for the
          usage of :class:`.AddConstraint` and :class:`.DropConstraint` applied
          as "after-create" and "before-drop" events on the MetaData object.
          This is normally used to generate/drop constraints on objects that
          are mutually dependent on each other.

        :param match: Optional string. If set, emit MATCH <value> when issuing
            DDL for this constraint. Typical values include SIMPLE, PARTIAL
            and FULL.

        """
        super(ForeignKeyConstraint, self).\
                        __init__(name, deferrable, initially)

        self.onupdate = onupdate
        self.ondelete = ondelete
        self.link_to_name = link_to_name
        if self.name is None and use_alter:
            raise exc.ArgumentError("Alterable Constraint requires a name")
        self.use_alter = use_alter
        self.match = match

        self._elements = util.OrderedDict()

        # standalone ForeignKeyConstraint - create
        # associated ForeignKey objects which will be applied to hosted
        # Column objects (in col.foreign_keys), either now or when attached
        # to the Table for string-specified names
        for col, refcol in zip(columns, refcolumns):
            self._elements[col] = ForeignKey(
                    refcol,
                    _constraint=self,
                    name=self.name,
                    onupdate=self.onupdate,
                    ondelete=self.ondelete,
                    use_alter=self.use_alter,
                    link_to_name=self.link_to_name,
                    match=self.match
                )

        if table is not None:
            self._set_parent_with_dispatch(table)
        elif columns and \
            isinstance(columns[0], Column) and \
            columns[0].table is not None:
            self._set_parent_with_dispatch(columns[0].table)

    @property
    def _col_description(self):
        return ", ".join(self._elements)

    @property
    def columns(self):
        return self._elements.keys()

    @property
    def elements(self):
        return self._elements.values()

    def _set_parent(self, table):
        super(ForeignKeyConstraint, self)._set_parent(table)

        for col, fk in self._elements.iteritems():
            # string-specified column names now get
            # resolved to Column objects
            if isinstance(col, basestring):
                try:
                    col = table.c[col]
                except KeyError:
                    raise exc.ArgumentError(
                        "Can't create ForeignKeyConstraint "
                        "on table '%s': no column "
                        "named '%s' is present." % (table.description, col))

            if not hasattr(fk, 'parent') or \
                fk.parent is not col:
                fk._set_parent_with_dispatch(col)

        if self.use_alter:
            def supports_alter(ddl, event, schema_item, bind, **kw):
                return table in set(kw['tables']) and \
                            bind.dialect.supports_alter

            event.listen(table.metadata, "after_create",
                         AddConstraint(self, on=supports_alter))
            event.listen(table.metadata, "before_drop",
                         DropConstraint(self, on=supports_alter))

    def copy(self, schema=None, **kw):
        fkc = ForeignKeyConstraint(
                    [x.parent.key for x in self._elements.values()],
                    [x._get_colspec(schema=schema) for x in self._elements.values()],
                    name=self.name,
                    onupdate=self.onupdate,
                    ondelete=self.ondelete,
                    use_alter=self.use_alter,
                    deferrable=self.deferrable,
                    initially=self.initially,
                    link_to_name=self.link_to_name,
                    match=self.match
                )
        fkc.dispatch._update(self.dispatch)
        return fkc


class PrimaryKeyConstraint(ColumnCollectionConstraint):
    """A table-level PRIMARY KEY constraint.

    Defines a single column or composite PRIMARY KEY constraint. For a
    no-frills primary key, adding ``primary_key=True`` to one or more
    ``Column`` definitions is a shorthand equivalent for an unnamed single- or
    multiple-column PrimaryKeyConstraint.
    """

    __visit_name__ = 'primary_key_constraint'

    def _set_parent(self, table):
        super(PrimaryKeyConstraint, self)._set_parent(table)

        if table.primary_key in table.constraints:
            table.constraints.remove(table.primary_key)
        table.primary_key = self
        table.constraints.add(self)

        for c in self.columns:
            c.primary_key = True

    def _replace(self, col):
        self.columns.replace(col)


class UniqueConstraint(ColumnCollectionConstraint):
    """A table-level UNIQUE constraint.

    Defines a single column or composite UNIQUE constraint. For a no-frills,
    single column constraint, adding ``unique=True`` to the ``Column``
    definition is a shorthand equivalent for an unnamed, single column
    UniqueConstraint.
    """

    __visit_name__ = 'unique_constraint'


class Index(ColumnCollectionMixin, SchemaItem):
    """A table-level INDEX.

    Defines a composite (one or more column) INDEX.

    E.g.::

        sometable = Table("sometable", metadata,
                        Column("name", String(50)),
                        Column("address", String(100))
                    )

        Index("some_index", sometable.c.name)

    For a no-frills, single column index, adding
    :class:`.Column` also supports ``index=True``::

        sometable = Table("sometable", metadata,
                        Column("name", String(50), index=True)
                    )

    For a composite index, multiple columns can be specified::

        Index("some_index", sometable.c.name, sometable.c.address)

    Functional indexes are supported as well, keeping in mind that at least
    one :class:`.Column` must be present::

        Index("some_index", func.lower(sometable.c.name))

    .. versionadded:: 0.8 support for functional and expression-based indexes.

    .. seealso::

        :ref:`schema_indexes` - General information on :class:`.Index`.

        :ref:`postgresql_indexes` - PostgreSQL-specific options available for the
        :class:`.Index` construct.

        :ref:`mysql_indexes` - MySQL-specific options available for the
        :class:`.Index` construct.

        :ref:`mssql_indexes` - MSSQL-specific options available for the
        :class:`.Index` construct.

    """

    __visit_name__ = 'index'

    def __init__(self, name, *expressions, **kw):
        """Construct an index object.

        :param name:
          The name of the index

        :param \*expressions:
          Column or SQL expressions.

        :param unique:
            Defaults to False: create a unique index.

        :param \**kw:
            Other keyword arguments may be interpreted by specific dialects.

        """
        self.table = None

        columns = []
        for expr in expressions:
            if not isinstance(expr, expression.ClauseElement):
                columns.append(expr)
            else:
                cols = []
                visitors.traverse(expr, {}, {'column': cols.append})
                if cols:
                    columns.append(cols[0])
                else:
                    columns.append(expr)

        self.expressions = expressions

        # will call _set_parent() if table-bound column
        # objects are present
        ColumnCollectionMixin.__init__(self, *columns)

        self.name = name
        self.unique = kw.pop('unique', False)
        self.kwargs = kw

    def _set_parent(self, table):
        ColumnCollectionMixin._set_parent(self, table)

        if self.table is not None and table is not self.table:
            raise exc.ArgumentError(
                "Index '%s' is against table '%s', and "
                "cannot be associated with table '%s'." % (
                    self.name,
                    self.table.description,
                    table.description
                )
            )
        self.table = table
        for c in self.columns:
            if c.table != self.table:
                raise exc.ArgumentError(
                    "Column '%s' is not part of table '%s'." %
                    (c, self.table.description)
                )
        table.indexes.add(self)

        self.expressions = [
            expr if isinstance(expr, expression.ClauseElement)
            else colexpr
            for expr, colexpr in zip(self.expressions, self.columns)
        ]

    @property
    def bind(self):
        """Return the connectable associated with this Index."""

        return self.table.bind

    def create(self, bind=None):
        """Issue a ``CREATE`` statement for this
        :class:`.Index`, using the given :class:`.Connectable`
        for connectivity.

        .. seealso::

            :meth:`.MetaData.create_all`.

        """
        if bind is None:
            bind = _bind_or_error(self)
        bind._run_visitor(ddl.SchemaGenerator, self)
        return self

    def drop(self, bind=None):
        """Issue a ``DROP`` statement for this
        :class:`.Index`, using the given :class:`.Connectable`
        for connectivity.

        .. seealso::

            :meth:`.MetaData.drop_all`.

        """
        if bind is None:
            bind = _bind_or_error(self)
        bind._run_visitor(ddl.SchemaDropper, self)

    def __repr__(self):
        return 'Index(%s)' % (
                    ", ".join(
                        [repr(self.name)] +
                        [repr(c) for c in self.columns] +
                        (self.unique and ["unique=True"] or [])
                    ))


class MetaData(SchemaItem):
    """A collection of :class:`.Table` objects and their associated schema
    constructs.

    Holds a collection of :class:`.Table` objects as well as
    an optional binding to an :class:`.Engine` or
    :class:`.Connection`.  If bound, the :class:`.Table` objects
    in the collection and their columns may participate in implicit SQL
    execution.

    The :class:`.Table` objects themselves are stored in the
    ``metadata.tables`` dictionary.

    The ``bind`` property may be assigned to dynamically.  A common pattern is
    to start unbound and then bind later when an engine is available::

      metadata = MetaData()
      # define tables
      Table('mytable', metadata, ...)
      # connect to an engine later, perhaps after loading a URL from a
      # configuration file
      metadata.bind = an_engine

    MetaData is a thread-safe object after tables have been explicitly defined
    or loaded via reflection.

    .. seealso::

        :ref:`metadata_describing` - Introduction to database metadata

    """

    __visit_name__ = 'metadata'

    def __init__(self, bind=None, reflect=False, schema=None,
                 quote_schema=None):
        """Create a new MetaData object.

        :param bind:
          An Engine or Connection to bind to.  May also be a string or URL
          instance, these are passed to create_engine() and this MetaData will
          be bound to the resulting engine.

        :param reflect:
          Optional, automatically load all tables from the bound database.
          Defaults to False. ``bind`` is required when this option is set.

          .. deprecated:: 0.8
                Please use the :meth:`.MetaData.reflect` method.

        :param schema:
           The default schema to use for the :class:`.Table`,
           :class:`.Sequence`, and other objects associated with this
           :class:`.MetaData`. Defaults to ``None``.

        :param quote_schema:
            Sets the ``quote_schema`` flag for those :class:`.Table`,
            :class:`.Sequence`, and other objects which make usage of the
            local ``schema`` name.

        .. versionadded:: 0.7.4
            ``schema`` and ``quote_schema`` parameters.

        """
        self.tables = util.immutabledict()
        self.schema = schema
        self.quote_schema = quote_schema
        self._schemas = set()
        self._sequences = {}
        self.bind = bind
        if reflect:
            util.warn("reflect=True is deprecate; please "
                            "use the reflect() method.")
            if not bind:
                raise exc.ArgumentError(
                    "A bind must be supplied in conjunction "
                    "with reflect=True")
            self.reflect()

    def __repr__(self):
        return 'MetaData(bind=%r)' % self.bind

    def __contains__(self, table_or_key):
        if not isinstance(table_or_key, basestring):
            table_or_key = table_or_key.key
        return table_or_key in self.tables

    def _add_table(self, name, schema, table):
        key = _get_table_key(name, schema)
        dict.__setitem__(self.tables, key, table)
        if schema:
            self._schemas.add(schema)

    def _remove_table(self, name, schema):
        key = _get_table_key(name, schema)
        dict.pop(self.tables, key, None)
        if self._schemas:
            self._schemas = set([t.schema
                                for t in self.tables.values()
                                if t.schema is not None])

    def __getstate__(self):
        return {'tables': self.tables,
                'schema': self.schema,
                'quote_schema': self.quote_schema,
                'schemas': self._schemas,
                'sequences': self._sequences}

    def __setstate__(self, state):
        self.tables = state['tables']
        self.schema = state['schema']
        self.quote_schema = state['quote_schema']
        self._bind = None
        self._sequences = state['sequences']
        self._schemas = state['schemas']

    def is_bound(self):
        """True if this MetaData is bound to an Engine or Connection."""

        return self._bind is not None

    def bind(self):
        """An :class:`.Engine` or :class:`.Connection` to which this
        :class:`.MetaData` is bound.

        Typically, a :class:`.Engine` is assigned to this attribute
        so that "implicit execution" may be used, or alternatively
        as a means of providing engine binding information to an
        ORM :class:`.Session` object::

            engine = create_engine("someurl://")
            metadata.bind = engine

        .. seealso::

           :ref:`dbengine_implicit` - background on "bound metadata"

        """
        return self._bind

    def _bind_to(self, bind):
        """Bind this MetaData to an Engine, Connection, string or URL."""

        if isinstance(bind, (basestring, url.URL)):
            from sqlalchemy import create_engine
            self._bind = create_engine(bind)
        else:
            self._bind = bind
    bind = property(bind, _bind_to)

    def clear(self):
        """Clear all Table objects from this MetaData."""

        dict.clear(self.tables)
        self._schemas.clear()

    def remove(self, table):
        """Remove the given Table object from this MetaData."""

        self._remove_table(table.name, table.schema)

    @property
    def sorted_tables(self):
        """Returns a list of :class:`.Table` objects sorted in order of
        foreign key dependency.

        The sorting will place :class:`.Table` objects that have dependencies
        first, before the dependencies themselves, representing the
        order in which they can be created.   To get the order in which
        the tables would be dropped, use the ``reversed()`` Python built-in.

        .. seealso::

            :meth:`.Inspector.sorted_tables`

        """
        return sqlutil.sort_tables(self.tables.itervalues())

    def reflect(self, bind=None, schema=None, views=False, only=None):
        """Load all available table definitions from the database.

        Automatically creates ``Table`` entries in this ``MetaData`` for any
        table available in the database but not yet present in the
        ``MetaData``.  May be called multiple times to pick up tables recently
        added to the database, however no special action is taken if a table
        in this ``MetaData`` no longer exists in the database.

        :param bind:
          A :class:`.Connectable` used to access the database; if None, uses
          the existing bind on this ``MetaData``, if any.

        :param schema:
          Optional, query and reflect tables from an alterate schema.
          If None, the schema associated with this :class:`.MetaData`
          is used, if any.

        :param views:
          If True, also reflect views.

        :param only:
          Optional.  Load only a sub-set of available named tables.  May be
          specified as a sequence of names or a callable.

          If a sequence of names is provided, only those tables will be
          reflected.  An error is raised if a table is requested but not
          available.  Named tables already present in this ``MetaData`` are
          ignored.

          If a callable is provided, it will be used as a boolean predicate to
          filter the list of potential table names.  The callable is called
          with a table name and this ``MetaData`` instance as positional
          arguments and should return a true value for any table to reflect.

        """
        if bind is None:
            bind = _bind_or_error(self)

        with bind.connect() as conn:

            reflect_opts = {
                'autoload': True,
                'autoload_with': conn
            }

            if schema is None:
                schema = self.schema

            if schema is not None:
                reflect_opts['schema'] = schema

            available = util.OrderedSet(bind.engine.table_names(schema,
                                                            connection=conn))
            if views:
                available.update(
                    bind.dialect.get_view_names(conn, schema)
                )

            if schema is not None:
                available_w_schema = util.OrderedSet(["%s.%s" % (schema, name)
                                        for name in available])
            else:
                available_w_schema = available

            current = set(self.tables)

            if only is None:
                load = [name for name, schname in
                            zip(available, available_w_schema)
                            if schname not in current]
            elif util.callable(only):
                load = [name for name, schname in
                            zip(available, available_w_schema)
                            if schname not in current and only(name, self)]
            else:
                missing = [name for name in only if name not in available]
                if missing:
                    s = schema and (" schema '%s'" % schema) or ''
                    raise exc.InvalidRequestError(
                        'Could not reflect: requested table(s) not available '
                        'in %s%s: (%s)' %
                        (bind.engine.url, s, ', '.join(missing)))
                load = [name for name in only if name not in current]

            for name in load:
                Table(name, self, **reflect_opts)

    def append_ddl_listener(self, event_name, listener):
        """Append a DDL event listener to this ``MetaData``.

        Deprecated.  See :class:`.DDLEvents`.

        """
        def adapt_listener(target, connection, **kw):
            tables = kw['tables']
            listener(event, target, connection, tables=tables)

        event.listen(self, "" + event_name.replace('-', '_'), adapt_listener)

    def create_all(self, bind=None, tables=None, checkfirst=True):
        """Create all tables stored in this metadata.

        Conditional by default, will not attempt to recreate tables already
        present in the target database.

        :param bind:
          A :class:`.Connectable` used to access the
          database; if None, uses the existing bind on this ``MetaData``, if
          any.

        :param tables:
          Optional list of ``Table`` objects, which is a subset of the total
          tables in the ``MetaData`` (others are ignored).

        :param checkfirst:
          Defaults to True, don't issue CREATEs for tables already present
          in the target database.

        """
        if bind is None:
            bind = _bind_or_error(self)
        bind._run_visitor(ddl.SchemaGenerator,
                            self,
                            checkfirst=checkfirst,
                            tables=tables)

    def drop_all(self, bind=None, tables=None, checkfirst=True):
        """Drop all tables stored in this metadata.

        Conditional by default, will not attempt to drop tables not present in
        the target database.

        :param bind:
          A :class:`.Connectable` used to access the
          database; if None, uses the existing bind on this ``MetaData``, if
          any.

        :param tables:
          Optional list of ``Table`` objects, which is a subset of the
          total tables in the ``MetaData`` (others are ignored).

        :param checkfirst:
          Defaults to True, only issue DROPs for tables confirmed to be
          present in the target database.

        """
        if bind is None:
            bind = _bind_or_error(self)
        bind._run_visitor(ddl.SchemaDropper,
                            self,
                            checkfirst=checkfirst,
                            tables=tables)


class ThreadLocalMetaData(MetaData):
    """A MetaData variant that presents a different ``bind`` in every thread.

    Makes the ``bind`` property of the MetaData a thread-local value, allowing
    this collection of tables to be bound to different ``Engine``
    implementations or connections in each thread.

    The ThreadLocalMetaData starts off bound to None in each thread.  Binds
    must be made explicitly by assigning to the ``bind`` property or using
    ``connect()``.  You can also re-bind dynamically multiple times per
    thread, just like a regular ``MetaData``.

    """

    __visit_name__ = 'metadata'

    def __init__(self):
        """Construct a ThreadLocalMetaData."""

        self.context = util.threading.local()
        self.__engines = {}
        super(ThreadLocalMetaData, self).__init__()

    def bind(self):
        """The bound Engine or Connection for this thread.

        This property may be assigned an Engine or Connection, or assigned a
        string or URL to automatically create a basic Engine for this bind
        with ``create_engine()``."""

        return getattr(self.context, '_engine', None)

    def _bind_to(self, bind):
        """Bind to a Connectable in the caller's thread."""

        if isinstance(bind, (basestring, url.URL)):
            try:
                self.context._engine = self.__engines[bind]
            except KeyError:
                from sqlalchemy import create_engine
                e = create_engine(bind)
                self.__engines[bind] = e
                self.context._engine = e
        else:
            # TODO: this is squirrely.  we shouldnt have to hold onto engines
            # in a case like this
            if bind not in self.__engines:
                self.__engines[bind] = bind
            self.context._engine = bind

    bind = property(bind, _bind_to)

    def is_bound(self):
        """True if there is a bind for this thread."""
        return (hasattr(self.context, '_engine') and
                self.context._engine is not None)

    def dispose(self):
        """Dispose all bound engines, in all thread contexts."""

        for e in self.__engines.itervalues():
            if hasattr(e, 'dispose'):
                e.dispose()


class SchemaVisitor(visitors.ClauseVisitor):
    """Define the visiting for ``SchemaItem`` objects."""

    __traverse_options__ = {'schema_visitor': True}


class _DDLCompiles(expression.ClauseElement):
    def _compiler(self, dialect, **kw):
        """Return a compiler appropriate for this ClauseElement, given a
        Dialect."""

        return dialect.ddl_compiler(dialect, self, **kw)


class DDLElement(expression.Executable, _DDLCompiles):
    """Base class for DDL expression constructs.

    This class is the base for the general purpose :class:`.DDL` class,
    as well as the various create/drop clause constructs such as
    :class:`.CreateTable`, :class:`.DropTable`, :class:`.AddConstraint`,
    etc.

    :class:`.DDLElement` integrates closely with SQLAlchemy events,
    introduced in :ref:`event_toplevel`.  An instance of one is
    itself an event receiving callable::

        event.listen(
            users,
            'after_create',
            AddConstraint(constraint).execute_if(dialect='postgresql')
        )

    .. seealso::

        :class:`.DDL`

        :class:`.DDLEvents`

        :ref:`event_toplevel`

        :ref:`schema_ddl_sequences`

    """

    _execution_options = expression.Executable.\
                            _execution_options.union({'autocommit': True})

    target = None
    on = None
    dialect = None
    callable_ = None

    def execute(self, bind=None, target=None):
        """Execute this DDL immediately.

        Executes the DDL statement in isolation using the supplied
        :class:`.Connectable` or
        :class:`.Connectable` assigned to the ``.bind``
        property, if not supplied. If the DDL has a conditional ``on``
        criteria, it will be invoked with None as the event.

        :param bind:
          Optional, an ``Engine`` or ``Connection``. If not supplied, a valid
          :class:`.Connectable` must be present in the
          ``.bind`` property.

        :param target:
          Optional, defaults to None.  The target SchemaItem for the
          execute call.  Will be passed to the ``on`` callable if any,
          and may also provide string expansion data for the
          statement. See ``execute_at`` for more information.

        """

        if bind is None:
            bind = _bind_or_error(self)

        if self._should_execute(target, bind):
            return bind.execute(self.against(target))
        else:
            bind.engine.logger.info(
                        "DDL execution skipped, criteria not met.")

    @util.deprecated("0.7", "See :class:`.DDLEvents`, as well as "
        ":meth:`.DDLElement.execute_if`.")
    def execute_at(self, event_name, target):
        """Link execution of this DDL to the DDL lifecycle of a SchemaItem.

        Links this ``DDLElement`` to a ``Table`` or ``MetaData`` instance,
        executing it when that schema item is created or dropped. The DDL
        statement will be executed using the same Connection and transactional
        context as the Table create/drop itself. The ``.bind`` property of
        this statement is ignored.

        :param event:
          One of the events defined in the schema item's ``.ddl_events``;
          e.g. 'before-create', 'after-create', 'before-drop' or 'after-drop'

        :param target:
          The Table or MetaData instance for which this DDLElement will
          be associated with.

        A DDLElement instance can be linked to any number of schema items.

        ``execute_at`` builds on the ``append_ddl_listener`` interface of
        :class:`.MetaData` and :class:`.Table` objects.

        Caveat: Creating or dropping a Table in isolation will also trigger
        any DDL set to ``execute_at`` that Table's MetaData.  This may change
        in a future release.

        """

        def call_event(target, connection, **kw):
            if self._should_execute_deprecated(event_name,
                                    target, connection, **kw):
                return connection.execute(self.against(target))

        event.listen(target, "" + event_name.replace('-', '_'), call_event)

    @expression._generative
    def against(self, target):
        """Return a copy of this DDL against a specific schema item."""

        self.target = target

    @expression._generative
    def execute_if(self, dialect=None, callable_=None, state=None):
        """Return a callable that will execute this
        DDLElement conditionally.

        Used to provide a wrapper for event listening::

            event.listen(
                        metadata,
                        'before_create',
                        DDL("my_ddl").execute_if(dialect='postgresql')
                    )

        :param dialect: May be a string, tuple or a callable
          predicate.  If a string, it will be compared to the name of the
          executing database dialect::

            DDL('something').execute_if(dialect='postgresql')

          If a tuple, specifies multiple dialect names::

            DDL('something').execute_if(dialect=('postgresql', 'mysql'))

        :param callable_: A callable, which will be invoked with
          four positional arguments as well as optional keyword
          arguments:

            :ddl:
              This DDL element.

            :target:
              The :class:`.Table` or :class:`.MetaData` object which is the
              target of this event. May be None if the DDL is executed
              explicitly.

            :bind:
              The :class:`.Connection` being used for DDL execution

            :tables:
              Optional keyword argument - a list of Table objects which are to
              be created/ dropped within a MetaData.create_all() or drop_all()
              method call.

            :state:
              Optional keyword argument - will be the ``state`` argument
              passed to this function.

            :checkfirst:
             Keyword argument, will be True if the 'checkfirst' flag was
             set during the call to ``create()``, ``create_all()``,
             ``drop()``, ``drop_all()``.

          If the callable returns a true value, the DDL statement will be
          executed.

        :param state: any value which will be passed to the callable_
          as the ``state`` keyword argument.

        .. seealso::

            :class:`.DDLEvents`

            :ref:`event_toplevel`

        """
        self.dialect = dialect
        self.callable_ = callable_
        self.state = state

    def _should_execute(self, target, bind, **kw):
        if self.on is not None and \
            not self._should_execute_deprecated(None, target, bind, **kw):
            return False

        if isinstance(self.dialect, basestring):
            if self.dialect != bind.engine.name:
                return False
        elif isinstance(self.dialect, (tuple, list, set)):
            if bind.engine.name not in self.dialect:
                return False
        if self.callable_ is not None and \
            not self.callable_(self, target, bind, state=self.state, **kw):
            return False

        return True

    def _should_execute_deprecated(self, event, target, bind, **kw):
        if self.on is None:
            return True
        elif isinstance(self.on, basestring):
            return self.on == bind.engine.name
        elif isinstance(self.on, (tuple, list, set)):
            return bind.engine.name in self.on
        else:
            return self.on(self, event, target, bind, **kw)

    def __call__(self, target, bind, **kw):
        """Execute the DDL as a ddl_listener."""

        if self._should_execute(target, bind, **kw):
            return bind.execute(self.against(target))

    def _check_ddl_on(self, on):
        if (on is not None and
            (not isinstance(on, (basestring, tuple, list, set)) and
                    not util.callable(on))):
            raise exc.ArgumentError(
                "Expected the name of a database dialect, a tuple "
                "of names, or a callable for "
                "'on' criteria, got type '%s'." % type(on).__name__)

    def bind(self):
        if self._bind:
            return self._bind

    def _set_bind(self, bind):
        self._bind = bind
    bind = property(bind, _set_bind)

    def _generate(self):
        s = self.__class__.__new__(self.__class__)
        s.__dict__ = self.__dict__.copy()
        return s


class DDL(DDLElement):
    """A literal DDL statement.

    Specifies literal SQL DDL to be executed by the database.  DDL objects
    function as DDL event listeners, and can be subscribed to those events
    listed in :class:`.DDLEvents`, using either :class:`.Table` or
    :class:`.MetaData` objects as targets.   Basic templating support allows
    a single DDL instance to handle repetitive tasks for multiple tables.

    Examples::

      from sqlalchemy import event, DDL

      tbl = Table('users', metadata, Column('uid', Integer))
      event.listen(tbl, 'before_create', DDL('DROP TRIGGER users_trigger'))

      spow = DDL('ALTER TABLE %(table)s SET secretpowers TRUE')
      event.listen(tbl, 'after_create', spow.execute_if(dialect='somedb'))

      drop_spow = DDL('ALTER TABLE users SET secretpowers FALSE')
      connection.execute(drop_spow)

    When operating on Table events, the following ``statement``
    string substitions are available::

      %(table)s  - the Table name, with any required quoting applied
      %(schema)s - the schema name, with any required quoting applied
      %(fullname)s - the Table name including schema, quoted if needed

    The DDL's "context", if any, will be combined with the standard
    substutions noted above.  Keys present in the context will override
    the standard substitutions.

    """

    __visit_name__ = "ddl"

    def __init__(self, statement, on=None, context=None, bind=None):
        """Create a DDL statement.

        :param statement:
          A string or unicode string to be executed.  Statements will be
          processed with Python's string formatting operator.  See the
          ``context`` argument and the ``execute_at`` method.

          A literal '%' in a statement must be escaped as '%%'.

          SQL bind parameters are not available in DDL statements.

        :param on:
          Deprecated.  See :meth:`.DDLElement.execute_if`.

          Optional filtering criteria.  May be a string, tuple or a callable
          predicate.  If a string, it will be compared to the name of the
          executing database dialect::

            DDL('something', on='postgresql')

          If a tuple, specifies multiple dialect names::

            DDL('something', on=('postgresql', 'mysql'))

          If a callable, it will be invoked with four positional arguments
          as well as optional keyword arguments:

            :ddl:
              This DDL element.

            :event:
              The name of the event that has triggered this DDL, such as
              'after-create' Will be None if the DDL is executed explicitly.

            :target:
              The ``Table`` or ``MetaData`` object which is the target of
              this event. May be None if the DDL is executed explicitly.

            :connection:
              The ``Connection`` being used for DDL execution

            :tables:
              Optional keyword argument - a list of Table objects which are to
              be created/ dropped within a MetaData.create_all() or drop_all()
              method call.


          If the callable returns a true value, the DDL statement will be
          executed.

        :param context:
          Optional dictionary, defaults to None.  These values will be
          available for use in string substitutions on the DDL statement.

        :param bind:
          Optional. A :class:`.Connectable`, used by
          default when ``execute()`` is invoked without a bind argument.


        .. seealso::

            :class:`.DDLEvents`

            :mod:`sqlalchemy.event`

        """

        if not isinstance(statement, basestring):
            raise exc.ArgumentError(
                "Expected a string or unicode SQL statement, got '%r'" %
                statement)

        self.statement = statement
        self.context = context or {}

        self._check_ddl_on(on)
        self.on = on
        self._bind = bind

    def __repr__(self):
        return '<%s@%s; %s>' % (
            type(self).__name__, id(self),
            ', '.join([repr(self.statement)] +
                      ['%s=%r' % (key, getattr(self, key))
                       for key in ('on', 'context')
                       if getattr(self, key)]))


def _to_schema_column(element):
    if hasattr(element, '__clause_element__'):
        element = element.__clause_element__()
    if not isinstance(element, Column):
        raise exc.ArgumentError("schema.Column object expected")
    return element


def _to_schema_column_or_string(element):
    if hasattr(element, '__clause_element__'):
        element = element.__clause_element__()
    if not isinstance(element, (basestring, expression.ColumnElement)):
        msg = "Element %r is not a string name or column element"
        raise exc.ArgumentError(msg % element)
    return element


class _CreateDropBase(DDLElement):
    """Base class for DDL constucts that represent CREATE and DROP or
    equivalents.

    The common theme of _CreateDropBase is a single
    ``element`` attribute which refers to the element
    to be created or dropped.

    """

    def __init__(self, element, on=None, bind=None):
        self.element = element
        self._check_ddl_on(on)
        self.on = on
        self.bind = bind

    def _create_rule_disable(self, compiler):
        """Allow disable of _create_rule using a callable.

        Pass to _create_rule using
        util.portable_instancemethod(self._create_rule_disable)
        to retain serializability.

        """
        return False


class CreateSchema(_CreateDropBase):
    """Represent a CREATE SCHEMA statement.

    .. versionadded:: 0.7.4

    The argument here is the string name of the schema.

    """

    __visit_name__ = "create_schema"

    def __init__(self, name, quote=None, **kw):
        """Create a new :class:`.CreateSchema` construct."""

        self.quote = quote
        super(CreateSchema, self).__init__(name, **kw)


class DropSchema(_CreateDropBase):
    """Represent a DROP SCHEMA statement.

    The argument here is the string name of the schema.

    .. versionadded:: 0.7.4

    """

    __visit_name__ = "drop_schema"

    def __init__(self, name, quote=None, cascade=False, **kw):
        """Create a new :class:`.DropSchema` construct."""

        self.quote = quote
        self.cascade = cascade
        super(DropSchema, self).__init__(name, **kw)


class CreateTable(_CreateDropBase):
    """Represent a CREATE TABLE statement."""

    __visit_name__ = "create_table"

    def __init__(self, element, on=None, bind=None):
        """Create a :class:`.CreateTable` construct.

        :param element: a :class:`.Table` that's the subject
         of the CREATE
        :param on: See the description for 'on' in :class:`.DDL`.
        :param bind: See the description for 'bind' in :class:`.DDL`.

        """
        super(CreateTable, self).__init__(element, on=on, bind=bind)
        self.columns = [CreateColumn(column)
            for column in element.columns
        ]


class _DropView(_CreateDropBase):
    """Semi-public 'DROP VIEW' construct.

    Used by the test suite for dialect-agnostic drops of views.
    This object will eventually be part of a public "view" API.

    """
    __visit_name__ = "drop_view"


class CreateColumn(_DDLCompiles):
    """Represent a :class:`.Column` as rendered in a CREATE TABLE statement,
    via the :class:`.CreateTable` construct.

    This is provided to support custom column DDL within the generation
    of CREATE TABLE statements, by using the
    compiler extension documented in :ref:`sqlalchemy.ext.compiler_toplevel`
    to extend :class:`.CreateColumn`.

    Typical integration is to examine the incoming :class:`.Column`
    object, and to redirect compilation if a particular flag or condition
    is found::

        from sqlalchemy import schema
        from sqlalchemy.ext.compiler import compiles

        @compiles(schema.CreateColumn)
        def compile(element, compiler, **kw):
            column = element.element

            if "special" not in column.info:
                return compiler.visit_create_column(element, **kw)

            text = "%s SPECIAL DIRECTIVE %s" % (
                    column.name,
                    compiler.type_compiler.process(column.type)
                )
            default = compiler.get_column_default_string(column)
            if default is not None:
                text += " DEFAULT " + default

            if not column.nullable:
                text += " NOT NULL"

            if column.constraints:
                text += " ".join(
                            compiler.process(const)
                            for const in column.constraints)
            return text

    The above construct can be applied to a :class:`.Table` as follows::

        from sqlalchemy import Table, Metadata, Column, Integer, String
        from sqlalchemy import schema

        metadata = MetaData()

        table = Table('mytable', MetaData(),
                Column('x', Integer, info={"special":True}, primary_key=True),
                Column('y', String(50)),
                Column('z', String(20), info={"special":True})
            )

        metadata.create_all(conn)

    Above, the directives we've added to the :attr:`.Column.info` collection
    will be detected by our custom compilation scheme::

        CREATE TABLE mytable (
                x SPECIAL DIRECTIVE INTEGER NOT NULL,
                y VARCHAR(50),
                z SPECIAL DIRECTIVE VARCHAR(20),
            PRIMARY KEY (x)
        )

    The :class:`.CreateColumn` construct can also be used to skip certain
    columns when producing a ``CREATE TABLE``.  This is accomplished by
    creating a compilation rule that conditionally returns ``None``.
    This is essentially how to produce the same effect as using the
    ``system=True`` argument on :class:`.Column`, which marks a column
    as an implicitly-present "system" column.

    For example, suppose we wish to produce a :class:`.Table` which skips
    rendering of the Postgresql ``xmin`` column against the Postgresql backend,
    but on other backends does render it, in anticipation of a triggered rule.
    A conditional compilation rule could skip this name only on Postgresql::

        from sqlalchemy.schema import CreateColumn

        @compiles(CreateColumn, "postgresql")
        def skip_xmin(element, compiler, **kw):
            if element.element.name == 'xmin':
                return None
            else:
                return compiler.visit_create_column(element, **kw)


        my_table = Table('mytable', metadata,
                    Column('id', Integer, primary_key=True),
                    Column('xmin', Integer)
                )

    Above, a :class:`.CreateTable` construct will generate a ``CREATE TABLE``
    which only includes the ``id`` column in the string; the ``xmin`` column
    will be omitted, but only against the Postgresql backend.

    .. versionadded:: 0.8.3 The :class:`.CreateColumn` construct supports
       skipping of columns by returning ``None`` from a custom compilation rule.

    .. versionadded:: 0.8 The :class:`.CreateColumn` construct was added
       to support custom column creation styles.

    """
    __visit_name__ = 'create_column'

    def __init__(self, element):
        self.element = element


class DropTable(_CreateDropBase):
    """Represent a DROP TABLE statement."""

    __visit_name__ = "drop_table"


class CreateSequence(_CreateDropBase):
    """Represent a CREATE SEQUENCE statement."""

    __visit_name__ = "create_sequence"


class DropSequence(_CreateDropBase):
    """Represent a DROP SEQUENCE statement."""

    __visit_name__ = "drop_sequence"


class CreateIndex(_CreateDropBase):
    """Represent a CREATE INDEX statement."""

    __visit_name__ = "create_index"


class DropIndex(_CreateDropBase):
    """Represent a DROP INDEX statement."""

    __visit_name__ = "drop_index"


class AddConstraint(_CreateDropBase):
    """Represent an ALTER TABLE ADD CONSTRAINT statement."""

    __visit_name__ = "add_constraint"

    def __init__(self, element, *args, **kw):
        super(AddConstraint, self).__init__(element, *args, **kw)
        element._create_rule = util.portable_instancemethod(
                                            self._create_rule_disable)


class DropConstraint(_CreateDropBase):
    """Represent an ALTER TABLE DROP CONSTRAINT statement."""

    __visit_name__ = "drop_constraint"

    def __init__(self, element, cascade=False, **kw):
        self.cascade = cascade
        super(DropConstraint, self).__init__(element, **kw)
        element._create_rule = util.portable_instancemethod(
                                            self._create_rule_disable)


def _bind_or_error(schemaitem, msg=None):
    bind = schemaitem.bind
    if not bind:
        name = schemaitem.__class__.__name__
        label = getattr(schemaitem, 'fullname',
                        getattr(schemaitem, 'name', None))
        if label:
            item = '%s %r' % (name, label)
        else:
            item = name
        if isinstance(schemaitem, (MetaData, DDL)):
            bindable = "the %s's .bind" % name
        else:
            bindable = "this %s's .metadata.bind" % name

        if msg is None:
            msg = "The %s is not bound to an Engine or Connection.  "\
                   "Execution can not proceed without a database to execute "\
                   "against.  Either execute with an explicit connection or "\
                   "assign %s to enable implicit execution." % \
                   (item, bindable)
        raise exc.UnboundExecutionError(msg)
    return bind
