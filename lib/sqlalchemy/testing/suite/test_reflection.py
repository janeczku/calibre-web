from __future__ import with_statement

import sqlalchemy as sa
from sqlalchemy import exc as sa_exc
from sqlalchemy import types as sql_types
from sqlalchemy import inspect
from sqlalchemy import MetaData, Integer, String
from sqlalchemy.engine.reflection import Inspector
from sqlalchemy.testing import engines, fixtures
from sqlalchemy.testing.schema import Table, Column
from sqlalchemy.testing import eq_, assert_raises_message
from sqlalchemy import testing
from .. import config

from sqlalchemy.schema import DDL, Index
from sqlalchemy import event

metadata, users = None, None


class HasTableTest(fixtures.TablesTest):
    @classmethod
    def define_tables(cls, metadata):
        Table('test_table', metadata,
                Column('id', Integer, primary_key=True),
                Column('data', String(50))
            )

    def test_has_table(self):
        with config.db.begin() as conn:
            assert config.db.dialect.has_table(conn, "test_table")
            assert not config.db.dialect.has_table(conn, "nonexistent_table")



class ComponentReflectionTest(fixtures.TablesTest):
    run_inserts = run_deletes = None

    @classmethod
    def define_tables(cls, metadata):
        cls.define_reflected_tables(metadata, None)
        if testing.requires.schemas.enabled:
            cls.define_reflected_tables(metadata, "test_schema")

    @classmethod
    def define_reflected_tables(cls, metadata, schema):
        if schema:
            schema_prefix = schema + "."
        else:
            schema_prefix = ""

        if testing.requires.self_referential_foreign_keys.enabled:
            users = Table('users', metadata,
                Column('user_id', sa.INT, primary_key=True),
                Column('test1', sa.CHAR(5), nullable=False),
                Column('test2', sa.Float(5), nullable=False),
                Column('parent_user_id', sa.Integer,
                            sa.ForeignKey('%susers.user_id' % schema_prefix)),
                schema=schema,
                test_needs_fk=True,
            )
        else:
            users = Table('users', metadata,
                Column('user_id', sa.INT, primary_key=True),
                Column('test1', sa.CHAR(5), nullable=False),
                Column('test2', sa.Float(5), nullable=False),
                schema=schema,
                test_needs_fk=True,
            )

        Table("dingalings", metadata,
                  Column('dingaling_id', sa.Integer, primary_key=True),
                  Column('address_id', sa.Integer,
                    sa.ForeignKey('%semail_addresses.address_id' %
                                    schema_prefix)),
                  Column('data', sa.String(30)),
                  schema=schema,
                  test_needs_fk=True,
            )
        Table('email_addresses', metadata,
            Column('address_id', sa.Integer),
            Column('remote_user_id', sa.Integer,
                   sa.ForeignKey(users.c.user_id)),
            Column('email_address', sa.String(20)),
            sa.PrimaryKeyConstraint('address_id', name='email_ad_pk'),
            schema=schema,
            test_needs_fk=True,
        )

        if testing.requires.index_reflection.enabled:
            cls.define_index(metadata, users)
        if testing.requires.view_reflection.enabled:
            cls.define_views(metadata, schema)

    @classmethod
    def define_index(cls, metadata, users):
        Index("users_t_idx", users.c.test1, users.c.test2)
        Index("users_all_idx", users.c.user_id, users.c.test2, users.c.test1)

    @classmethod
    def define_views(cls, metadata, schema):
        for table_name in ('users', 'email_addresses'):
            fullname = table_name
            if schema:
                fullname = "%s.%s" % (schema, table_name)
            view_name = fullname + '_v'
            query = "CREATE VIEW %s AS SELECT * FROM %s" % (
                                view_name, fullname)

            event.listen(
                metadata,
                "after_create",
                DDL(query)
            )
            event.listen(
                metadata,
                "before_drop",
                DDL("DROP VIEW %s" % view_name)
            )

    @testing.requires.schema_reflection
    def test_get_schema_names(self):
        insp = inspect(testing.db)

        self.assert_('test_schema' in insp.get_schema_names())

    @testing.requires.schema_reflection
    def test_dialect_initialize(self):
        engine = engines.testing_engine()
        assert not hasattr(engine.dialect, 'default_schema_name')
        inspect(engine)
        assert hasattr(engine.dialect, 'default_schema_name')

    @testing.requires.schema_reflection
    def test_get_default_schema_name(self):
        insp = inspect(testing.db)
        eq_(insp.default_schema_name, testing.db.dialect.default_schema_name)

    @testing.provide_metadata
    def _test_get_table_names(self, schema=None, table_type='table',
                              order_by=None):
        meta = self.metadata
        users, addresses, dingalings = self.tables.users, \
                self.tables.email_addresses, self.tables.dingalings
        insp = inspect(meta.bind)
        if table_type == 'view':
            table_names = insp.get_view_names(schema)
            table_names.sort()
            answer = ['email_addresses_v', 'users_v']
        else:
            table_names = insp.get_table_names(schema,
                                               order_by=order_by)
            if order_by == 'foreign_key':
                answer = ['users', 'email_addresses', 'dingalings']
                eq_(table_names, answer)
            else:
                answer = ['dingalings', 'email_addresses', 'users']
                eq_(sorted(table_names), answer)

    @testing.requires.table_reflection
    def test_get_table_names(self):
        self._test_get_table_names()

    @testing.requires.table_reflection
    @testing.requires.foreign_key_constraint_reflection
    def test_get_table_names_fks(self):
        self._test_get_table_names(order_by='foreign_key')

    @testing.requires.table_reflection
    @testing.requires.schemas
    def test_get_table_names_with_schema(self):
        self._test_get_table_names('test_schema')

    @testing.requires.view_reflection
    def test_get_view_names(self):
        self._test_get_table_names(table_type='view')

    @testing.requires.view_reflection
    @testing.requires.schemas
    def test_get_view_names_with_schema(self):
        self._test_get_table_names('test_schema', table_type='view')

    def _test_get_columns(self, schema=None, table_type='table'):
        meta = MetaData(testing.db)
        users, addresses, dingalings = self.tables.users, \
                self.tables.email_addresses, self.tables.dingalings
        table_names = ['users', 'email_addresses']
        if table_type == 'view':
            table_names = ['users_v', 'email_addresses_v']
        insp = inspect(meta.bind)
        for table_name, table in zip(table_names, (users,
                addresses)):
            schema_name = schema
            cols = insp.get_columns(table_name, schema=schema_name)
            self.assert_(len(cols) > 0, len(cols))

            # should be in order

            for i, col in enumerate(table.columns):
                eq_(col.name, cols[i]['name'])
                ctype = cols[i]['type'].__class__
                ctype_def = col.type
                if isinstance(ctype_def, sa.types.TypeEngine):
                    ctype_def = ctype_def.__class__

                # Oracle returns Date for DateTime.

                if testing.against('oracle') and ctype_def \
                    in (sql_types.Date, sql_types.DateTime):
                    ctype_def = sql_types.Date

                # assert that the desired type and return type share
                # a base within one of the generic types.

                self.assert_(len(set(ctype.__mro__).
                    intersection(ctype_def.__mro__).intersection([
                    sql_types.Integer,
                    sql_types.Numeric,
                    sql_types.DateTime,
                    sql_types.Date,
                    sql_types.Time,
                    sql_types.String,
                    sql_types._Binary,
                    ])) > 0, '%s(%s), %s(%s)' % (col.name,
                            col.type, cols[i]['name'], ctype))

                if not col.primary_key:
                    assert cols[i]['default'] is None

    @testing.requires.table_reflection
    def test_get_columns(self):
        self._test_get_columns()

    @testing.requires.table_reflection
    @testing.requires.schemas
    def test_get_columns_with_schema(self):
        self._test_get_columns(schema='test_schema')

    @testing.requires.view_reflection
    def test_get_view_columns(self):
        self._test_get_columns(table_type='view')

    @testing.requires.view_reflection
    @testing.requires.schemas
    def test_get_view_columns_with_schema(self):
        self._test_get_columns(schema='test_schema', table_type='view')

    @testing.provide_metadata
    def _test_get_pk_constraint(self, schema=None):
        meta = self.metadata
        users, addresses = self.tables.users, self.tables.email_addresses
        insp = inspect(meta.bind)

        users_cons = insp.get_pk_constraint(users.name, schema=schema)
        users_pkeys = users_cons['constrained_columns']
        eq_(users_pkeys,  ['user_id'])

        addr_cons = insp.get_pk_constraint(addresses.name, schema=schema)
        addr_pkeys = addr_cons['constrained_columns']
        eq_(addr_pkeys,  ['address_id'])

        with testing.requires.reflects_pk_names.fail_if():
            eq_(addr_cons['name'], 'email_ad_pk')

    @testing.requires.primary_key_constraint_reflection
    def test_get_pk_constraint(self):
        self._test_get_pk_constraint()

    @testing.requires.table_reflection
    @testing.requires.primary_key_constraint_reflection
    @testing.requires.schemas
    def test_get_pk_constraint_with_schema(self):
        self._test_get_pk_constraint(schema='test_schema')

    @testing.requires.table_reflection
    @testing.provide_metadata
    def test_deprecated_get_primary_keys(self):
        meta = self.metadata
        users = self.tables.users
        insp = Inspector(meta.bind)
        assert_raises_message(
            sa_exc.SADeprecationWarning,
            "Call to deprecated method get_primary_keys."
            "  Use get_pk_constraint instead.",
            insp.get_primary_keys, users.name
        )

    @testing.provide_metadata
    def _test_get_foreign_keys(self, schema=None):
        meta = self.metadata
        users, addresses, dingalings = self.tables.users, \
                    self.tables.email_addresses, self.tables.dingalings
        insp = inspect(meta.bind)
        expected_schema = schema
        # users
        users_fkeys = insp.get_foreign_keys(users.name,
                                            schema=schema)
        fkey1 = users_fkeys[0]

        with testing.requires.named_constraints.fail_if():
            self.assert_(fkey1['name'] is not None)

        eq_(fkey1['referred_schema'], expected_schema)
        eq_(fkey1['referred_table'], users.name)
        eq_(fkey1['referred_columns'], ['user_id', ])
        if testing.requires.self_referential_foreign_keys.enabled:
            eq_(fkey1['constrained_columns'], ['parent_user_id'])

        #addresses
        addr_fkeys = insp.get_foreign_keys(addresses.name,
                                           schema=schema)
        fkey1 = addr_fkeys[0]

        with testing.requires.named_constraints.fail_if():
            self.assert_(fkey1['name'] is not None)

        eq_(fkey1['referred_schema'], expected_schema)
        eq_(fkey1['referred_table'], users.name)
        eq_(fkey1['referred_columns'], ['user_id', ])
        eq_(fkey1['constrained_columns'], ['remote_user_id'])

    @testing.requires.foreign_key_constraint_reflection
    def test_get_foreign_keys(self):
        self._test_get_foreign_keys()

    @testing.requires.foreign_key_constraint_reflection
    @testing.requires.schemas
    def test_get_foreign_keys_with_schema(self):
        self._test_get_foreign_keys(schema='test_schema')

    @testing.provide_metadata
    def _test_get_indexes(self, schema=None):
        meta = self.metadata
        users, addresses, dingalings = self.tables.users, \
                    self.tables.email_addresses, self.tables.dingalings
        # The database may decide to create indexes for foreign keys, etc.
        # so there may be more indexes than expected.
        insp = inspect(meta.bind)
        indexes = insp.get_indexes('users', schema=schema)
        expected_indexes = [
            {'unique': False,
             'column_names': ['test1', 'test2'],
             'name': 'users_t_idx'},
            {'unique': False,
             'column_names': ['user_id', 'test2', 'test1'],
             'name': 'users_all_idx'}
        ]
        index_names = [d['name'] for d in indexes]
        for e_index in expected_indexes:
            assert e_index['name'] in index_names
            index = indexes[index_names.index(e_index['name'])]
            for key in e_index:
                eq_(e_index[key], index[key])

    @testing.requires.index_reflection
    def test_get_indexes(self):
        self._test_get_indexes()

    @testing.requires.index_reflection
    @testing.requires.schemas
    def test_get_indexes_with_schema(self):
        self._test_get_indexes(schema='test_schema')

    @testing.provide_metadata
    def _test_get_view_definition(self, schema=None):
        meta = self.metadata
        users, addresses, dingalings = self.tables.users, \
                    self.tables.email_addresses, self.tables.dingalings
        view_name1 = 'users_v'
        view_name2 = 'email_addresses_v'
        insp = inspect(meta.bind)
        v1 = insp.get_view_definition(view_name1, schema=schema)
        self.assert_(v1)
        v2 = insp.get_view_definition(view_name2, schema=schema)
        self.assert_(v2)

    @testing.requires.view_reflection
    def test_get_view_definition(self):
        self._test_get_view_definition()

    @testing.requires.view_reflection
    @testing.requires.schemas
    def test_get_view_definition_with_schema(self):
        self._test_get_view_definition(schema='test_schema')

    @testing.only_on("postgresql", "PG specific feature")
    @testing.provide_metadata
    def _test_get_table_oid(self, table_name, schema=None):
        meta = self.metadata
        users, addresses, dingalings = self.tables.users, \
                    self.tables.email_addresses, self.tables.dingalings
        insp = inspect(meta.bind)
        oid = insp.get_table_oid(table_name, schema)
        self.assert_(isinstance(oid, (int, long)))

    def test_get_table_oid(self):
        self._test_get_table_oid('users')

    @testing.requires.schemas
    def test_get_table_oid_with_schema(self):
        self._test_get_table_oid('users', schema='test_schema')

    @testing.provide_metadata
    def test_autoincrement_col(self):
        """test that 'autoincrement' is reflected according to sqla's policy.

        Don't mark this test as unsupported for any backend !

        (technically it fails with MySQL InnoDB since "id" comes before "id2")

        A backend is better off not returning "autoincrement" at all,
        instead of potentially returning "False" for an auto-incrementing
        primary key column.

        """

        meta = self.metadata
        insp = inspect(meta.bind)

        for tname, cname in [
                ('users', 'user_id'),
                ('email_addresses', 'address_id'),
                ('dingalings', 'dingaling_id'),
            ]:
            cols = insp.get_columns(tname)
            id_ = dict((c['name'], c) for c in cols)[cname]
            assert id_.get('autoincrement', True)



__all__ = ('ComponentReflectionTest', 'HasTableTest')
