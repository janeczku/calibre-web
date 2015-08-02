from .. import fixtures, config
from ..config import requirements
from .. import exclusions
from ..assertions import eq_
from .. import engines

from sqlalchemy import Integer, String, select, util

from ..schema import Table, Column


class RowFetchTest(fixtures.TablesTest):

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

    def test_via_string(self):
        row = config.db.execute(
                self.tables.plain_pk.select().\
                    order_by(self.tables.plain_pk.c.id)
            ).first()

        eq_(
            row['id'], 1
        )
        eq_(
            row['data'], "d1"
        )

    def test_via_int(self):
        row = config.db.execute(
                self.tables.plain_pk.select().\
                    order_by(self.tables.plain_pk.c.id)
            ).first()

        eq_(
            row[0], 1
        )
        eq_(
            row[1], "d1"
        )

    def test_via_col_object(self):
        row = config.db.execute(
                self.tables.plain_pk.select().\
                    order_by(self.tables.plain_pk.c.id)
            ).first()

        eq_(
            row[self.tables.plain_pk.c.id], 1
        )
        eq_(
            row[self.tables.plain_pk.c.data], "d1"
        )