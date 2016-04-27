from .. import fixtures, config
from ..config import requirements
from ..assertions import eq_
from ... import testing

from ... import Integer, String, Sequence, schema

from ..schema import Table, Column

class SequenceTest(fixtures.TablesTest):
    __requires__ = ('sequences',)

    run_create_tables = 'each'

    @classmethod
    def define_tables(cls, metadata):
        Table('seq_pk', metadata,
                Column('id', Integer, Sequence('tab_id_seq'), primary_key=True),
                Column('data', String(50))
            )

        Table('seq_opt_pk', metadata,
                Column('id', Integer, Sequence('tab_id_seq', optional=True),
                                                primary_key=True),
                Column('data', String(50))
            )

    def test_insert_roundtrip(self):
        config.db.execute(
            self.tables.seq_pk.insert(),
            data="some data"
        )
        self._assert_round_trip(self.tables.seq_pk, config.db)

    def test_insert_lastrowid(self):
        r = config.db.execute(
            self.tables.seq_pk.insert(),
            data="some data"
        )
        eq_(
            r.inserted_primary_key,
            [1]
        )

    def test_nextval_direct(self):
        r = config.db.execute(
            self.tables.seq_pk.c.id.default
        )
        eq_(
            r, 1
        )

    @requirements.sequences_optional
    def test_optional_seq(self):
        r = config.db.execute(
            self.tables.seq_opt_pk.insert(),
            data="some data"
        )
        eq_(
            r.inserted_primary_key,
            [1]
        )


    def _assert_round_trip(self, table, conn):
        row = conn.execute(table.select()).first()
        eq_(
            row,
            (1, "some data")
        )


class HasSequenceTest(fixtures.TestBase):
    __requires__ = 'sequences',

    def test_has_sequence(self):
        s1 = Sequence('user_id_seq')
        testing.db.execute(schema.CreateSequence(s1))
        try:
            eq_(testing.db.dialect.has_sequence(testing.db,
                'user_id_seq'), True)
        finally:
            testing.db.execute(schema.DropSequence(s1))

    @testing.requires.schemas
    def test_has_sequence_schema(self):
        s1 = Sequence('user_id_seq', schema="test_schema")
        testing.db.execute(schema.CreateSequence(s1))
        try:
            eq_(testing.db.dialect.has_sequence(testing.db,
                'user_id_seq', schema="test_schema"), True)
        finally:
            testing.db.execute(schema.DropSequence(s1))

    def test_has_sequence_neg(self):
        eq_(testing.db.dialect.has_sequence(testing.db, 'user_id_seq'),
            False)

    @testing.requires.schemas
    def test_has_sequence_schemas_neg(self):
        eq_(testing.db.dialect.has_sequence(testing.db, 'user_id_seq',
                            schema="test_schema"),
            False)

    @testing.requires.schemas
    def test_has_sequence_default_not_in_remote(self):
        s1 = Sequence('user_id_seq')
        testing.db.execute(schema.CreateSequence(s1))
        try:
            eq_(testing.db.dialect.has_sequence(testing.db, 'user_id_seq',
                            schema="test_schema"),
                False)
        finally:
            testing.db.execute(schema.DropSequence(s1))

    @testing.requires.schemas
    def test_has_sequence_remote_not_in_default(self):
        s1 = Sequence('user_id_seq', schema="test_schema")
        testing.db.execute(schema.CreateSequence(s1))
        try:
            eq_(testing.db.dialect.has_sequence(testing.db, 'user_id_seq'),
                False)
        finally:
            testing.db.execute(schema.DropSequence(s1))


