# sql/util.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

from .. import exc, schema, util, sql
from ..util import topological
from . import expression, operators, visitors
from itertools import chain
from collections import deque

"""Utility functions that build upon SQL and Schema constructs."""


def sort_tables(tables, skip_fn=None, extra_dependencies=None):
    """sort a collection of Table objects in order of
                their foreign-key dependency."""

    tables = list(tables)
    tuples = []
    if extra_dependencies is not None:
        tuples.extend(extra_dependencies)

    def visit_foreign_key(fkey):
        if fkey.use_alter:
            return
        elif skip_fn and skip_fn(fkey):
            return
        parent_table = fkey.column.table
        if parent_table in tables:
            child_table = fkey.parent.table
            if parent_table is not child_table:
                tuples.append((parent_table, child_table))

    for table in tables:
        visitors.traverse(table,
                            {'schema_visitor': True},
                            {'foreign_key': visit_foreign_key})

        tuples.extend(
            [parent, table] for parent in table._extra_dependencies
        )

    return list(topological.sort(tuples, tables))


def find_join_source(clauses, join_to):
    """Given a list of FROM clauses and a selectable,
    return the first index and element from the list of
    clauses which can be joined against the selectable.  returns
    None, None if no match is found.

    e.g.::

        clause1 = table1.join(table2)
        clause2 = table4.join(table5)

        join_to = table2.join(table3)

        find_join_source([clause1, clause2], join_to) == clause1

    """

    selectables = list(expression._from_objects(join_to))
    for i, f in enumerate(clauses):
        for s in selectables:
            if f.is_derived_from(s):
                return i, f
    else:
        return None, None


def visit_binary_product(fn, expr):
    """Produce a traversal of the given expression, delivering
    column comparisons to the given function.

    The function is of the form::

        def my_fn(binary, left, right)

    For each binary expression located which has a
    comparison operator, the product of "left" and
    "right" will be delivered to that function,
    in terms of that binary.

    Hence an expression like::

        and_(
            (a + b) == q + func.sum(e + f),
            j == r
        )

    would have the traversal::

        a <eq> q
        a <eq> e
        a <eq> f
        b <eq> q
        b <eq> e
        b <eq> f
        j <eq> r

    That is, every combination of "left" and
    "right" that doesn't further contain
    a binary comparison is passed as pairs.

    """
    stack = []

    def visit(element):
        if isinstance(element, (expression.ScalarSelect)):
            # we dont want to dig into correlated subqueries,
            # those are just column elements by themselves
            yield element
        elif element.__visit_name__ == 'binary' and \
            operators.is_comparison(element.operator):
            stack.insert(0, element)
            for l in visit(element.left):
                for r in visit(element.right):
                    fn(stack[0], l, r)
            stack.pop(0)
            for elem in element.get_children():
                visit(elem)
        else:
            if isinstance(element, expression.ColumnClause):
                yield element
            for elem in element.get_children():
                for e in visit(elem):
                    yield e
    list(visit(expr))


def find_tables(clause, check_columns=False,
                include_aliases=False, include_joins=False,
                include_selects=False, include_crud=False):
    """locate Table objects within the given expression."""

    tables = []
    _visitors = {}

    if include_selects:
        _visitors['select'] = _visitors['compound_select'] = tables.append

    if include_joins:
        _visitors['join'] = tables.append

    if include_aliases:
        _visitors['alias'] = tables.append

    if include_crud:
        _visitors['insert'] = _visitors['update'] = \
                    _visitors['delete'] = lambda ent: tables.append(ent.table)

    if check_columns:
        def visit_column(column):
            tables.append(column.table)
        _visitors['column'] = visit_column

    _visitors['table'] = tables.append

    visitors.traverse(clause, {'column_collections': False}, _visitors)
    return tables


def find_columns(clause):
    """locate Column objects within the given expression."""

    cols = util.column_set()
    visitors.traverse(clause, {}, {'column': cols.add})
    return cols


def unwrap_order_by(clause):
    """Break up an 'order by' expression into individual column-expressions,
    without DESC/ASC/NULLS FIRST/NULLS LAST"""

    cols = util.column_set()
    stack = deque([clause])
    while stack:
        t = stack.popleft()
        if isinstance(t, expression.ColumnElement) and \
            (
                not isinstance(t, expression.UnaryExpression) or \
                not operators.is_ordering_modifier(t.modifier)
            ):
            cols.add(t)
        else:
            for c in t.get_children():
                stack.append(c)
    return cols


def clause_is_present(clause, search):
    """Given a target clause and a second to search within, return True
    if the target is plainly present in the search without any
    subqueries or aliases involved.

    Basically descends through Joins.

    """

    stack = [search]
    while stack:
        elem = stack.pop()
        if clause == elem:  # use == here so that Annotated's compare
            return True
        elif isinstance(elem, expression.Join):
            stack.extend((elem.left, elem.right))
    return False


def bind_values(clause):
    """Return an ordered list of "bound" values in the given clause.

    E.g.::

        >>> expr = and_(
        ...    table.c.foo==5, table.c.foo==7
        ... )
        >>> bind_values(expr)
        [5, 7]
    """

    v = []

    def visit_bindparam(bind):
        v.append(bind.effective_value)

    visitors.traverse(clause, {}, {'bindparam': visit_bindparam})
    return v


def _quote_ddl_expr(element):
    if isinstance(element, basestring):
        element = element.replace("'", "''")
        return "'%s'" % element
    else:
        return repr(element)


class _repr_params(object):
    """A string view of bound parameters, truncating
    display to the given number of 'multi' parameter sets.

    """
    def __init__(self, params, batches):
        self.params = params
        self.batches = batches

    def __repr__(self):
        if isinstance(self.params, (list, tuple)) and \
            len(self.params) > self.batches and \
            isinstance(self.params[0], (list, dict, tuple)):
            msg = " ... displaying %i of %i total bound parameter sets ... "
            return ' '.join((
                        repr(self.params[:self.batches - 2])[0:-1],
                        msg % (self.batches, len(self.params)),
                        repr(self.params[-2:])[1:]
                    ))
        else:
            return repr(self.params)


def expression_as_ddl(clause):
    """Given a SQL expression, convert for usage in DDL, such as
     CREATE INDEX and CHECK CONSTRAINT.

     Converts bind params into quoted literals, column identifiers
     into detached column constructs so that the parent table
     identifier is not included.

     .. deprecated:: this function is removed in 0.9.0.

    """
    def repl(element):
        if isinstance(element, expression.BindParameter):
            return expression.literal_column(_quote_ddl_expr(element.value))
        elif isinstance(element, expression.ColumnClause) and \
                element.table is not None:
            col = expression.column(element.name)
            col.quote = element.quote
            return col
        else:
            return None

    return visitors.replacement_traverse(clause, {}, repl)


def adapt_criterion_to_null(crit, nulls):
    """given criterion containing bind params, convert selected elements
    to IS NULL.

    """

    def visit_binary(binary):
        if isinstance(binary.left, expression.BindParameter) \
            and binary.left._identifying_key in nulls:
            # reverse order if the NULL is on the left side
            binary.left = binary.right
            binary.right = expression.null()
            binary.operator = operators.is_
            binary.negate = operators.isnot
        elif isinstance(binary.right, expression.BindParameter) \
            and binary.right._identifying_key in nulls:
            binary.right = expression.null()
            binary.operator = operators.is_
            binary.negate = operators.isnot

    return visitors.cloned_traverse(crit, {}, {'binary': visit_binary})


def join_condition(a, b, ignore_nonexistent_tables=False,
                            a_subset=None,
                            consider_as_foreign_keys=None):
    """create a join condition between two tables or selectables.

    e.g.::

        join_condition(tablea, tableb)

    would produce an expression along the lines of::

        tablea.c.id==tableb.c.tablea_id

    The join is determined based on the foreign key relationships
    between the two selectables.   If there are multiple ways
    to join, or no way to join, an error is raised.

    :param ignore_nonexistent_tables:  Deprecated - this
    flag is no longer used.  Only resolution errors regarding
    the two given tables are propagated.

    :param a_subset: An optional expression that is a sub-component
    of ``a``.  An attempt will be made to join to just this sub-component
    first before looking at the full ``a`` construct, and if found
    will be successful even if there are other ways to join to ``a``.
    This allows the "right side" of a join to be passed thereby
    providing a "natural join".

    """
    crit = []
    constraints = set()

    for left in (a_subset, a):
        if left is None:
            continue
        for fk in sorted(
                    b.foreign_keys,
                    key=lambda fk: fk.parent._creation_order):
            if consider_as_foreign_keys is not None and \
                fk.parent not in consider_as_foreign_keys:
                continue
            try:
                col = fk.get_referent(left)
            except exc.NoReferenceError, nrte:
                if nrte.table_name == left.name:
                    raise
                else:
                    continue

            if col is not None:
                crit.append(col == fk.parent)
                constraints.add(fk.constraint)
        if left is not b:
            for fk in sorted(
                        left.foreign_keys,
                        key=lambda fk: fk.parent._creation_order):
                if consider_as_foreign_keys is not None and \
                    fk.parent not in consider_as_foreign_keys:
                    continue
                try:
                    col = fk.get_referent(b)
                except exc.NoReferenceError, nrte:
                    if nrte.table_name == b.name:
                        raise
                    else:
                        # this is totally covered.  can't get
                        # coverage to mark it.
                        continue

                if col is not None:
                    crit.append(col == fk.parent)
                    constraints.add(fk.constraint)
        if crit:
            break

    if len(crit) == 0:
        if isinstance(b, expression.FromGrouping):
            hint = " Perhaps you meant to convert the right side to a "\
                                "subquery using alias()?"
        else:
            hint = ""
        raise exc.NoForeignKeysError(
            "Can't find any foreign key relationships "
            "between '%s' and '%s'.%s" % (a.description, b.description, hint))
    elif len(constraints) > 1:
        raise exc.AmbiguousForeignKeysError(
            "Can't determine join between '%s' and '%s'; "
            "tables have more than one foreign key "
            "constraint relationship between them. "
            "Please specify the 'onclause' of this "
            "join explicitly." % (a.description, b.description))
    elif len(crit) == 1:
        return (crit[0])
    else:
        return sql.and_(*crit)


class Annotated(object):
    """clones a ClauseElement and applies an 'annotations' dictionary.

    Unlike regular clones, this clone also mimics __hash__() and
    __cmp__() of the original element so that it takes its place
    in hashed collections.

    A reference to the original element is maintained, for the important
    reason of keeping its hash value current.  When GC'ed, the
    hash value may be reused, causing conflicts.

    """

    def __new__(cls, *args):
        if not args:
            # clone constructor
            return object.__new__(cls)
        else:
            element, values = args
            # pull appropriate subclass from registry of annotated
            # classes
            try:
                cls = annotated_classes[element.__class__]
            except KeyError:
                cls = annotated_classes[element.__class__] = type.__new__(type,
                        "Annotated%s" % element.__class__.__name__,
                        (cls, element.__class__), {})
            return object.__new__(cls)

    def __init__(self, element, values):
        # force FromClause to generate their internal
        # collections into __dict__
        if isinstance(element, expression.FromClause):
            element.c

        self.__dict__ = element.__dict__.copy()
        expression.ColumnElement.comparator._reset(self)
        self.__element = element
        self._annotations = values

    def _annotate(self, values):
        _values = self._annotations.copy()
        _values.update(values)
        return self._with_annotations(_values)

    def _with_annotations(self, values):
        clone = self.__class__.__new__(self.__class__)
        clone.__dict__ = self.__dict__.copy()
        expression.ColumnElement.comparator._reset(clone)
        clone._annotations = values
        return clone

    def _deannotate(self, values=None, clone=True):
        if values is None:
            return self.__element
        else:
            _values = self._annotations.copy()
            for v in values:
                _values.pop(v, None)
            return self._with_annotations(_values)

    def _compiler_dispatch(self, visitor, **kw):
        return self.__element.__class__._compiler_dispatch(self, visitor, **kw)

    @property
    def _constructor(self):
        return self.__element._constructor

    def _clone(self):
        clone = self.__element._clone()
        if clone is self.__element:
            # detect immutable, don't change anything
            return self
        else:
            # update the clone with any changes that have occurred
            # to this object's __dict__.
            clone.__dict__.update(self.__dict__)
            return self.__class__(clone, self._annotations)

    def __hash__(self):
        return hash(self.__element)

    def __eq__(self, other):
        if isinstance(self.__element, expression.ColumnOperators):
            return self.__element.__class__.__eq__(self, other)
        else:
            return hash(other) == hash(self)


class AnnotatedColumnElement(Annotated):
    def __init__(self, element, values):
        Annotated.__init__(self, element, values)
        for attr in ('name', 'key', 'table'):
            if self.__dict__.get(attr, False) is None:
                self.__dict__.pop(attr)

    @util.memoized_property
    def name(self):
        """pull 'name' from parent, if not present"""
        return self._Annotated__element.name

    @util.memoized_property
    def table(self):
        """pull 'table' from parent, if not present"""
        return self._Annotated__element.table

    @util.memoized_property
    def key(self):
        """pull 'key' from parent, if not present"""
        return self._Annotated__element.key

    @util.memoized_property
    def info(self):
        return self._Annotated__element.info

# hard-generate Annotated subclasses.  this technique
# is used instead of on-the-fly types (i.e. type.__new__())
# so that the resulting objects are pickleable.
annotated_classes = {}

for cls in expression.__dict__.values() + [schema.Column, schema.Table]:
    if isinstance(cls, type) and issubclass(cls, expression.ClauseElement):
        if issubclass(cls, expression.ColumnElement):
            annotation_cls = "AnnotatedColumnElement"
        else:
            annotation_cls = "Annotated"
        exec "class Annotated%s(%s, cls):\n" \
             "    pass" % (cls.__name__, annotation_cls) in locals()
        exec "annotated_classes[cls] = Annotated%s" % (cls.__name__,)


def _deep_annotate(element, annotations, exclude=None):
    """Deep copy the given ClauseElement, annotating each element
    with the given annotations dictionary.

    Elements within the exclude collection will be cloned but not annotated.

    """
    def clone(elem):
        if exclude and \
                    hasattr(elem, 'proxy_set') and \
                    elem.proxy_set.intersection(exclude):
            newelem = elem._clone()
        elif annotations != elem._annotations:
            newelem = elem._annotate(annotations)
        else:
            newelem = elem
        newelem._copy_internals(clone=clone)
        return newelem

    if element is not None:
        element = clone(element)
    return element


def _deep_deannotate(element, values=None):
    """Deep copy the given element, removing annotations."""

    cloned = util.column_dict()

    def clone(elem):
        # if a values dict is given,
        # the elem must be cloned each time it appears,
        # as there may be different annotations in source
        # elements that are remaining.  if totally
        # removing all annotations, can assume the same
        # slate...
        if values or elem not in cloned:
            newelem = elem._deannotate(values=values, clone=True)
            newelem._copy_internals(clone=clone)
            if not values:
                cloned[elem] = newelem
            return newelem
        else:
            return cloned[elem]

    if element is not None:
        element = clone(element)
    return element


def _shallow_annotate(element, annotations):
    """Annotate the given ClauseElement and copy its internals so that
    internal objects refer to the new annotated object.

    Basically used to apply a "dont traverse" annotation to a
    selectable, without digging throughout the whole
    structure wasting time.
    """
    element = element._annotate(annotations)
    element._copy_internals()
    return element


def splice_joins(left, right, stop_on=None):
    if left is None:
        return right

    stack = [(right, None)]

    adapter = ClauseAdapter(left)
    ret = None
    while stack:
        (right, prevright) = stack.pop()
        if isinstance(right, expression.Join) and right is not stop_on:
            right = right._clone()
            right._reset_exported()
            right.onclause = adapter.traverse(right.onclause)
            stack.append((right.left, right))
        else:
            right = adapter.traverse(right)
        if prevright is not None:
            prevright.left = right
        if ret is None:
            ret = right

    return ret


def reduce_columns(columns, *clauses, **kw):
    """given a list of columns, return a 'reduced' set based on natural
    equivalents.

    the set is reduced to the smallest list of columns which have no natural
    equivalent present in the list.  A "natural equivalent" means that two
    columns will ultimately represent the same value because they are related
    by a foreign key.

    \*clauses is an optional list of join clauses which will be traversed
    to further identify columns that are "equivalent".

    \**kw may specify 'ignore_nonexistent_tables' to ignore foreign keys
    whose tables are not yet configured, or columns that aren't yet present.

    This function is primarily used to determine the most minimal "primary key"
    from a selectable, by reducing the set of primary key columns present
    in the the selectable to just those that are not repeated.

    """
    ignore_nonexistent_tables = kw.pop('ignore_nonexistent_tables', False)
    only_synonyms = kw.pop('only_synonyms', False)

    columns = util.ordered_column_set(columns)

    omit = util.column_set()
    for col in columns:
        for fk in chain(*[c.foreign_keys for c in col.proxy_set]):
            for c in columns:
                if c is col:
                    continue
                try:
                    fk_col = fk.column
                except exc.NoReferencedColumnError:
                    # TODO: add specific coverage here
                    # to test/sql/test_selectable ReduceTest
                    if ignore_nonexistent_tables:
                        continue
                    else:
                        raise
                except exc.NoReferencedTableError:
                    # TODO: add specific coverage here
                    # to test/sql/test_selectable ReduceTest
                    if ignore_nonexistent_tables:
                        continue
                    else:
                        raise
                if fk_col.shares_lineage(c) and \
                    (not only_synonyms or \
                    c.name == col.name):
                    omit.add(col)
                    break

    if clauses:
        def visit_binary(binary):
            if binary.operator == operators.eq:
                cols = util.column_set(chain(*[c.proxy_set
                            for c in columns.difference(omit)]))
                if binary.left in cols and binary.right in cols:
                    for c in reversed(columns):
                        if c.shares_lineage(binary.right) and \
                            (not only_synonyms or \
                            c.name == binary.left.name):
                            omit.add(c)
                            break
        for clause in clauses:
            if clause is not None:
                visitors.traverse(clause, {}, {'binary': visit_binary})

    return expression.ColumnSet(columns.difference(omit))


def criterion_as_pairs(expression, consider_as_foreign_keys=None,
                        consider_as_referenced_keys=None, any_operator=False):
    """traverse an expression and locate binary criterion pairs."""

    if consider_as_foreign_keys and consider_as_referenced_keys:
        raise exc.ArgumentError("Can only specify one of "
                                "'consider_as_foreign_keys' or "
                                "'consider_as_referenced_keys'")

    def col_is(a, b):
        #return a is b
        return a.compare(b)

    def visit_binary(binary):
        if not any_operator and binary.operator is not operators.eq:
            return
        if not isinstance(binary.left, sql.ColumnElement) or \
                    not isinstance(binary.right, sql.ColumnElement):
            return

        if consider_as_foreign_keys:
            if binary.left in consider_as_foreign_keys and \
                        (col_is(binary.right, binary.left) or
                        binary.right not in consider_as_foreign_keys):
                pairs.append((binary.right, binary.left))
            elif binary.right in consider_as_foreign_keys and \
                        (col_is(binary.left, binary.right) or
                        binary.left not in consider_as_foreign_keys):
                pairs.append((binary.left, binary.right))
        elif consider_as_referenced_keys:
            if binary.left in consider_as_referenced_keys and \
                        (col_is(binary.right, binary.left) or
                        binary.right not in consider_as_referenced_keys):
                pairs.append((binary.left, binary.right))
            elif binary.right in consider_as_referenced_keys and \
                        (col_is(binary.left, binary.right) or
                        binary.left not in consider_as_referenced_keys):
                pairs.append((binary.right, binary.left))
        else:
            if isinstance(binary.left, schema.Column) and \
                        isinstance(binary.right, schema.Column):
                if binary.left.references(binary.right):
                    pairs.append((binary.right, binary.left))
                elif binary.right.references(binary.left):
                    pairs.append((binary.left, binary.right))
    pairs = []
    visitors.traverse(expression, {}, {'binary': visit_binary})
    return pairs


class AliasedRow(object):
    """Wrap a RowProxy with a translation map.

    This object allows a set of keys to be translated
    to those present in a RowProxy.

    """
    def __init__(self, row, map):
        # AliasedRow objects don't nest, so un-nest
        # if another AliasedRow was passed
        if isinstance(row, AliasedRow):
            self.row = row.row
        else:
            self.row = row
        self.map = map

    def __contains__(self, key):
        return self.map[key] in self.row

    def has_key(self, key):
        return key in self

    def __getitem__(self, key):
        return self.row[self.map[key]]

    def keys(self):
        return self.row.keys()


class ClauseAdapter(visitors.ReplacingCloningVisitor):
    """Clones and modifies clauses based on column correspondence.

    E.g.::

      table1 = Table('sometable', metadata,
          Column('col1', Integer),
          Column('col2', Integer)
          )
      table2 = Table('someothertable', metadata,
          Column('col1', Integer),
          Column('col2', Integer)
          )

      condition = table1.c.col1 == table2.c.col1

    make an alias of table1::

      s = table1.alias('foo')

    calling ``ClauseAdapter(s).traverse(condition)`` converts
    condition to read::

      s.c.col1 == table2.c.col1

    """
    def __init__(self, selectable, equivalents=None,
                        include=None, exclude=None,
                        include_fn=None, exclude_fn=None,
                        adapt_on_names=False):
        self.__traverse_options__ = {'stop_on': [selectable]}
        self.selectable = selectable
        if include:
            assert not include_fn
            self.include_fn = lambda e: e in include
        else:
            self.include_fn = include_fn
        if exclude:
            assert not exclude_fn
            self.exclude_fn = lambda e: e in exclude
        else:
            self.exclude_fn = exclude_fn
        self.equivalents = util.column_dict(equivalents or {})
        self.adapt_on_names = adapt_on_names

    def _corresponding_column(self, col, require_embedded,
                              _seen=util.EMPTY_SET):
        newcol = self.selectable.corresponding_column(
                                    col,
                                    require_embedded=require_embedded)
        if newcol is None and col in self.equivalents and col not in _seen:
            for equiv in self.equivalents[col]:
                newcol = self._corresponding_column(equiv,
                                require_embedded=require_embedded,
                                _seen=_seen.union([col]))
                if newcol is not None:
                    return newcol
        if self.adapt_on_names and newcol is None:
            newcol = self.selectable.c.get(col.name)
        return newcol

    def replace(self, col):
        if isinstance(col, expression.FromClause) and \
            self.selectable.is_derived_from(col):
                return self.selectable
        elif not isinstance(col, expression.ColumnElement):
            return None
        elif self.include_fn and not self.include_fn(col):
            return None
        elif self.exclude_fn and self.exclude_fn(col):
            return None
        else:
            return self._corresponding_column(col, True)


class ColumnAdapter(ClauseAdapter):
    """Extends ClauseAdapter with extra utility functions.

    Provides the ability to "wrap" this ClauseAdapter
    around another, a columns dictionary which returns
    adapted elements given an original, and an
    adapted_row() factory.

    """
    def __init__(self, selectable, equivalents=None,
                        chain_to=None, include=None,
                        exclude=None, adapt_required=False):
        ClauseAdapter.__init__(self, selectable, equivalents, include, exclude)
        if chain_to:
            self.chain(chain_to)
        self.columns = util.populate_column_dict(self._locate_col)
        self.adapt_required = adapt_required

    def wrap(self, adapter):
        ac = self.__class__.__new__(self.__class__)
        ac.__dict__ = self.__dict__.copy()
        ac._locate_col = ac._wrap(ac._locate_col, adapter._locate_col)
        ac.adapt_clause = ac._wrap(ac.adapt_clause, adapter.adapt_clause)
        ac.adapt_list = ac._wrap(ac.adapt_list, adapter.adapt_list)
        ac.columns = util.populate_column_dict(ac._locate_col)
        return ac

    adapt_clause = ClauseAdapter.traverse
    adapt_list = ClauseAdapter.copy_and_process

    def _wrap(self, local, wrapped):
        def locate(col):
            col = local(col)
            return wrapped(col)
        return locate

    def _locate_col(self, col):
        c = self._corresponding_column(col, True)
        if c is None:
            c = self.adapt_clause(col)

            # anonymize labels in case they have a hardcoded name
            if isinstance(c, expression.Label):
                c = c.label(None)

        # adapt_required indicates that if we got the same column
        # back which we put in (i.e. it passed through),
        # it's not correct.  this is used by eagerloading which
        # knows that all columns and expressions need to be adapted
        # to a result row, and a "passthrough" is definitely targeting
        # the wrong column.
        if self.adapt_required and c is col:
            return None

        return c

    def adapted_row(self, row):
        return AliasedRow(row, self.columns)

    def __getstate__(self):
        d = self.__dict__.copy()
        del d['columns']
        return d

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.columns = util.PopulateDict(self._locate_col)
