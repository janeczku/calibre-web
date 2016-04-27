from .. import fixtures, config
from ..assertions import eq_

from sqlalchemy import Integer, String
from ..schema import Table, Column


class SimpleUpdateDeleteTest(fixtures.TablesTest):
    run_deletes = 'each'

    @classmethod
    def define_tables(cls, metadata):
        Table('plain_pk', metadata,
                Column('id', Integer, primary_key=True),
                Column('data', String(50))
            )

    @classmethod
    def insert_data(cls):
        config.db.execute(
            cls.tables.plain_pk.insert(),
            [
                {"id":1, "data":"d1"},
                {"id":2, "data":"d2"},
                {"id":3, "data":"d3"},
            ]
        )

    def test_update(self):
        t = self.tables.plain_pk
        r = config.db.execute(
            t.update().where(t.c.id == 2),
            data="d2_new"
        )
        assert not r.is_insert
        assert not r.returns_rows

        eq_(
            config.db.execute(t.select().order_by(t.c.id)).fetchall(),
            [
                (1, "d1"),
                (2, "d2_new"),
                (3, "d3")
            ]
        )

    def test_delete(self):
        t = self.tables.plain_pk
        r = config.db.execute(
            t.delete().where(t.c.id == 2)
        )
        assert not r.is_insert
        assert not r.returns_rows
        eq_(
            config.db.execute(t.select().order_by(t.c.id)).fetchall(),
            [
                (1, "d1"),
                (3, "d3")
            ]
        )

__all__ = ('SimpleUpdateDeleteTest', )
