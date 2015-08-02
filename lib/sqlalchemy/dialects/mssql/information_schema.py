# mssql/information_schema.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

# TODO: should be using the sys. catalog with SQL Server, not information schema

from ... import Table, MetaData, Column
from ...types import String, Unicode, Integer, TypeDecorator
from ... import cast
from ... import util
from ...sql import expression
from ...ext.compiler import compiles

ischema = MetaData()

class CoerceUnicode(TypeDecorator):
    impl = Unicode

    def process_bind_param(self, value, dialect):
        # Py2K
        if isinstance(value, str):
            value = value.decode(dialect.encoding)
        # end Py2K
        return value

    def bind_expression(self, bindvalue):
        return _cast_on_2005(bindvalue)

class _cast_on_2005(expression.ColumnElement):
    def __init__(self, bindvalue):
        self.bindvalue = bindvalue

@compiles(_cast_on_2005)
def _compile(element, compiler, **kw):
    from . import base
    if compiler.dialect.server_version_info < base.MS_2005_VERSION:
        return compiler.process(element.bindvalue, **kw)
    else:
        return compiler.process(cast(element.bindvalue, Unicode), **kw)

schemata = Table("SCHEMATA", ischema,
    Column("CATALOG_NAME", CoerceUnicode, key="catalog_name"),
    Column("SCHEMA_NAME", CoerceUnicode, key="schema_name"),
    Column("SCHEMA_OWNER", CoerceUnicode, key="schema_owner"),
    schema="INFORMATION_SCHEMA")

tables = Table("TABLES", ischema,
    Column("TABLE_CATALOG", CoerceUnicode, key="table_catalog"),
    Column("TABLE_SCHEMA", CoerceUnicode, key="table_schema"),
    Column("TABLE_NAME", CoerceUnicode, key="table_name"),
    Column("TABLE_TYPE", String(convert_unicode=True), key="table_type"),
    schema="INFORMATION_SCHEMA")

columns = Table("COLUMNS", ischema,
    Column("TABLE_SCHEMA", CoerceUnicode, key="table_schema"),
    Column("TABLE_NAME", CoerceUnicode, key="table_name"),
    Column("COLUMN_NAME", CoerceUnicode, key="column_name"),
    Column("IS_NULLABLE", Integer, key="is_nullable"),
    Column("DATA_TYPE", String, key="data_type"),
    Column("ORDINAL_POSITION", Integer, key="ordinal_position"),
    Column("CHARACTER_MAXIMUM_LENGTH", Integer, key="character_maximum_length"),
    Column("NUMERIC_PRECISION", Integer, key="numeric_precision"),
    Column("NUMERIC_SCALE", Integer, key="numeric_scale"),
    Column("COLUMN_DEFAULT", Integer, key="column_default"),
    Column("COLLATION_NAME", String, key="collation_name"),
    schema="INFORMATION_SCHEMA")

constraints = Table("TABLE_CONSTRAINTS", ischema,
    Column("TABLE_SCHEMA", CoerceUnicode, key="table_schema"),
    Column("TABLE_NAME", CoerceUnicode, key="table_name"),
    Column("CONSTRAINT_NAME", CoerceUnicode, key="constraint_name"),
    Column("CONSTRAINT_TYPE", String(convert_unicode=True), key="constraint_type"),
    schema="INFORMATION_SCHEMA")

column_constraints = Table("CONSTRAINT_COLUMN_USAGE", ischema,
    Column("TABLE_SCHEMA", CoerceUnicode, key="table_schema"),
    Column("TABLE_NAME", CoerceUnicode, key="table_name"),
    Column("COLUMN_NAME", CoerceUnicode, key="column_name"),
    Column("CONSTRAINT_NAME", CoerceUnicode, key="constraint_name"),
    schema="INFORMATION_SCHEMA")

key_constraints = Table("KEY_COLUMN_USAGE", ischema,
    Column("TABLE_SCHEMA", CoerceUnicode, key="table_schema"),
    Column("TABLE_NAME", CoerceUnicode, key="table_name"),
    Column("COLUMN_NAME", CoerceUnicode, key="column_name"),
    Column("CONSTRAINT_NAME", CoerceUnicode, key="constraint_name"),
    Column("ORDINAL_POSITION", Integer, key="ordinal_position"),
    schema="INFORMATION_SCHEMA")

ref_constraints = Table("REFERENTIAL_CONSTRAINTS", ischema,
    Column("CONSTRAINT_CATALOG", CoerceUnicode, key="constraint_catalog"),
    Column("CONSTRAINT_SCHEMA", CoerceUnicode, key="constraint_schema"),
    Column("CONSTRAINT_NAME", CoerceUnicode, key="constraint_name"),
    # TODO: is CATLOG misspelled ?
    Column("UNIQUE_CONSTRAINT_CATLOG", CoerceUnicode,
                                        key="unique_constraint_catalog"),

    Column("UNIQUE_CONSTRAINT_SCHEMA", CoerceUnicode,
                                        key="unique_constraint_schema"),
    Column("UNIQUE_CONSTRAINT_NAME", CoerceUnicode,
                                        key="unique_constraint_name"),
    Column("MATCH_OPTION", String, key="match_option"),
    Column("UPDATE_RULE", String, key="update_rule"),
    Column("DELETE_RULE", String, key="delete_rule"),
    schema="INFORMATION_SCHEMA")

views = Table("VIEWS", ischema,
    Column("TABLE_CATALOG", CoerceUnicode, key="table_catalog"),
    Column("TABLE_SCHEMA", CoerceUnicode, key="table_schema"),
    Column("TABLE_NAME", CoerceUnicode, key="table_name"),
    Column("VIEW_DEFINITION", CoerceUnicode, key="view_definition"),
    Column("CHECK_OPTION", String, key="check_option"),
    Column("IS_UPDATABLE", String, key="is_updatable"),
    schema="INFORMATION_SCHEMA")
