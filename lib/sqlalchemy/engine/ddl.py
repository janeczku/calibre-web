# engine/ddl.py
# Copyright (C) 2009-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Routines to handle CREATE/DROP workflow."""

from .. import schema
from ..sql import util as sql_util


class DDLBase(schema.SchemaVisitor):
    def __init__(self, connection):
        self.connection = connection


class SchemaGenerator(DDLBase):

    def __init__(self, dialect, connection, checkfirst=False,
                 tables=None, **kwargs):
        super(SchemaGenerator, self).__init__(connection, **kwargs)
        self.checkfirst = checkfirst
        self.tables = tables
        self.preparer = dialect.identifier_preparer
        self.dialect = dialect
        self.memo = {}

    def _can_create_table(self, table):
        self.dialect.validate_identifier(table.name)
        if table.schema:
            self.dialect.validate_identifier(table.schema)
        return not self.checkfirst or \
                not self.dialect.has_table(self.connection,
                                    table.name, schema=table.schema)

    def _can_create_sequence(self, sequence):
        return self.dialect.supports_sequences and \
            (
                (not self.dialect.sequences_optional or
                 not sequence.optional) and
                    (
                        not self.checkfirst or
                        not self.dialect.has_sequence(
                                self.connection,
                                sequence.name,
                                schema=sequence.schema)
                     )
            )

    def visit_metadata(self, metadata):
        if self.tables is not None:
            tables = self.tables
        else:
            tables = metadata.tables.values()
        collection = [t for t in sql_util.sort_tables(tables)
                        if self._can_create_table(t)]
        seq_coll = [s for s in metadata._sequences.values()
                        if s.column is None and self._can_create_sequence(s)]

        metadata.dispatch.before_create(metadata, self.connection,
                                    tables=collection,
                                    checkfirst=self.checkfirst,
                                            _ddl_runner=self)

        for seq in seq_coll:
            self.traverse_single(seq, create_ok=True)

        for table in collection:
            self.traverse_single(table, create_ok=True)

        metadata.dispatch.after_create(metadata, self.connection,
                                    tables=collection,
                                    checkfirst=self.checkfirst,
                                            _ddl_runner=self)

    def visit_table(self, table, create_ok=False):
        if not create_ok and not self._can_create_table(table):
            return

        table.dispatch.before_create(table, self.connection,
                                        checkfirst=self.checkfirst,
                                            _ddl_runner=self)

        for column in table.columns:
            if column.default is not None:
                self.traverse_single(column.default)

        self.connection.execute(schema.CreateTable(table))

        if hasattr(table, 'indexes'):
            for index in table.indexes:
                self.traverse_single(index)

        table.dispatch.after_create(table, self.connection,
                                        checkfirst=self.checkfirst,
                                            _ddl_runner=self)

    def visit_sequence(self, sequence, create_ok=False):
        if not create_ok and not self._can_create_sequence(sequence):
            return
        self.connection.execute(schema.CreateSequence(sequence))

    def visit_index(self, index):
        self.connection.execute(schema.CreateIndex(index))


class SchemaDropper(DDLBase):

    def __init__(self, dialect, connection, checkfirst=False,
                 tables=None, **kwargs):
        super(SchemaDropper, self).__init__(connection, **kwargs)
        self.checkfirst = checkfirst
        self.tables = tables
        self.preparer = dialect.identifier_preparer
        self.dialect = dialect
        self.memo = {}

    def visit_metadata(self, metadata):
        if self.tables is not None:
            tables = self.tables
        else:
            tables = metadata.tables.values()

        collection = [
            t
            for t in reversed(sql_util.sort_tables(tables))
            if self._can_drop_table(t)
        ]

        seq_coll = [
            s
            for s in metadata._sequences.values()
            if s.column is None and self._can_drop_sequence(s)
        ]

        metadata.dispatch.before_drop(
            metadata, self.connection, tables=collection,
            checkfirst=self.checkfirst, _ddl_runner=self)

        for table in collection:
            self.traverse_single(table, drop_ok=True)

        for seq in seq_coll:
            self.traverse_single(seq, drop_ok=True)

        metadata.dispatch.after_drop(
            metadata, self.connection, tables=collection,
            checkfirst=self.checkfirst, _ddl_runner=self)

    def _can_drop_table(self, table):
        self.dialect.validate_identifier(table.name)
        if table.schema:
            self.dialect.validate_identifier(table.schema)
        return not self.checkfirst or self.dialect.has_table(self.connection,
                                            table.name, schema=table.schema)

    def _can_drop_sequence(self, sequence):
        return self.dialect.supports_sequences and \
            ((not self.dialect.sequences_optional or
                 not sequence.optional) and
                (not self.checkfirst or
                self.dialect.has_sequence(
                                self.connection,
                                sequence.name,
                                schema=sequence.schema))
            )

    def visit_index(self, index):
        self.connection.execute(schema.DropIndex(index))

    def visit_table(self, table, drop_ok=False):
        if not drop_ok and not self._can_drop_table(table):
            return

        table.dispatch.before_drop(table, self.connection,
                                    checkfirst=self.checkfirst,
                                            _ddl_runner=self)

        for column in table.columns:
            if column.default is not None:
                self.traverse_single(column.default)

        self.connection.execute(schema.DropTable(table))

        table.dispatch.after_drop(table, self.connection,
                                        checkfirst=self.checkfirst,
                                            _ddl_runner=self)

    def visit_sequence(self, sequence, drop_ok=False):
        if not drop_ok and not self._can_drop_sequence(sequence):
            return
        self.connection.execute(schema.DropSequence(sequence))
