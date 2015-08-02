# Copyright (C) 2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
from sqlalchemy.schema import ColumnCollectionConstraint
from sqlalchemy.sql import expression

class ExcludeConstraint(ColumnCollectionConstraint):
    """A table-level EXCLUDE constraint.

    Defines an EXCLUDE constraint as described in the `postgres
    documentation`__.

    __ http://www.postgresql.org/docs/9.0/static/sql-createtable.html#SQL-CREATETABLE-EXCLUDE
    """

    __visit_name__ = 'exclude_constraint'

    where = None

    def __init__(self, *elements, **kw):
        """
        :param \*elements:
          A sequence of two tuples of the form ``(column, operator)`` where
          column must be a column name or Column object and operator must
          be a string containing the operator to use.

        :param name:
          Optional, the in-database name of this constraint.

        :param deferrable:
          Optional bool.  If set, emit DEFERRABLE or NOT DEFERRABLE when
          issuing DDL for this constraint.

        :param initially:
          Optional string.  If set, emit INITIALLY <value> when issuing DDL
          for this constraint.

        :param using:
          Optional string.  If set, emit USING <index_method> when issuing DDL
          for this constraint. Defaults to 'gist'.

        :param where:
          Optional string.  If set, emit WHERE <predicate> when issuing DDL
          for this constraint.

        """
        ColumnCollectionConstraint.__init__(
            self,
            name=kw.get('name'),
            deferrable=kw.get('deferrable'),
            initially=kw.get('initially'),
            *[col for col, op in elements]
            )
        self.operators = {}
        for col_or_string, op in elements:
            name = getattr(col_or_string, 'name', col_or_string)
            self.operators[name] = op
        self.using = kw.get('using', 'gist')
        where = kw.get('where')
        if where:
            self.where =  expression._literal_as_text(where)

    def copy(self, **kw):
        elements = [(col, self.operators[col])
                    for col in self.columns.keys()]
        c = self.__class__(name=self.name,
                            deferrable=self.deferrable,
                            initially=self.initially,
                            *elements)
        c.dispatch._update(self.dispatch)
        return c

