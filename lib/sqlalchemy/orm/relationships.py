# orm/relationships.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Heuristics related to join conditions as used in
:func:`.relationship`.

Provides the :class:`.JoinCondition` object, which encapsulates
SQL annotation and aliasing behavior focused on the `primaryjoin`
and `secondaryjoin` aspects of :func:`.relationship`.

"""

from .. import sql, util, exc as sa_exc, schema
from ..sql.util import (
    ClauseAdapter,
    join_condition, _shallow_annotate, visit_binary_product,
    _deep_deannotate, find_tables
    )
from ..sql import operators, expression, visitors
from .interfaces import MANYTOMANY, MANYTOONE, ONETOMANY


def remote(expr):
    """Annotate a portion of a primaryjoin expression
    with a 'remote' annotation.

    See the section :ref:`relationship_custom_foreign` for a
    description of use.

    .. versionadded:: 0.8

    .. seealso::

        :ref:`relationship_custom_foreign`

        :func:`.foreign`

    """
    return _annotate_columns(expression._clause_element_as_expr(expr),
                    {"remote": True})


def foreign(expr):
    """Annotate a portion of a primaryjoin expression
    with a 'foreign' annotation.

    See the section :ref:`relationship_custom_foreign` for a
    description of use.

    .. versionadded:: 0.8

    .. seealso::

        :ref:`relationship_custom_foreign`

        :func:`.remote`

    """

    return _annotate_columns(expression._clause_element_as_expr(expr),
                        {"foreign": True})


def _annotate_columns(element, annotations):
    def clone(elem):
        if isinstance(elem, expression.ColumnClause):
            elem = elem._annotate(annotations.copy())
        elem._copy_internals(clone=clone)
        return elem

    if element is not None:
        element = clone(element)
    return element


class JoinCondition(object):
    def __init__(self,
                    parent_selectable,
                    child_selectable,
                    parent_local_selectable,
                    child_local_selectable,
                    primaryjoin=None,
                    secondary=None,
                    secondaryjoin=None,
                    parent_equivalents=None,
                    child_equivalents=None,
                    consider_as_foreign_keys=None,
                    local_remote_pairs=None,
                    remote_side=None,
                    self_referential=False,
                    prop=None,
                    support_sync=True,
                    can_be_synced_fn=lambda *c: True
                    ):
        self.parent_selectable = parent_selectable
        self.parent_local_selectable = parent_local_selectable
        self.child_selectable = child_selectable
        self.child_local_selectable = child_local_selectable
        self.parent_equivalents = parent_equivalents
        self.child_equivalents = child_equivalents
        self.primaryjoin = primaryjoin
        self.secondaryjoin = secondaryjoin
        self.secondary = secondary
        self.consider_as_foreign_keys = consider_as_foreign_keys
        self._local_remote_pairs = local_remote_pairs
        self._remote_side = remote_side
        self.prop = prop
        self.self_referential = self_referential
        self.support_sync = support_sync
        self.can_be_synced_fn = can_be_synced_fn
        self._determine_joins()
        self._annotate_fks()
        self._annotate_remote()
        self._annotate_local()
        self._setup_pairs()
        self._check_foreign_cols(self.primaryjoin, True)
        if self.secondaryjoin is not None:
            self._check_foreign_cols(self.secondaryjoin, False)
        self._determine_direction()
        self._check_remote_side()
        self._log_joins()

    def _log_joins(self):
        if self.prop is None:
            return
        log = self.prop.logger
        log.info('%s setup primary join %s', self.prop,
                         self.primaryjoin)
        log.info('%s setup secondary join %s', self.prop,
                         self.secondaryjoin)
        log.info('%s synchronize pairs [%s]', self.prop,
                         ','.join('(%s => %s)' % (l, r) for (l, r) in
                         self.synchronize_pairs))
        log.info('%s secondary synchronize pairs [%s]', self.prop,
                         ','.join('(%s => %s)' % (l, r) for (l, r) in
                         self.secondary_synchronize_pairs or []))
        log.info('%s local/remote pairs [%s]', self.prop,
                         ','.join('(%s / %s)' % (l, r) for (l, r) in
                         self.local_remote_pairs))
        log.info('%s remote columns [%s]', self.prop,
                        ','.join('%s' % col for col in self.remote_columns)
            )
        log.info('%s local columns [%s]', self.prop,
                        ','.join('%s' % col for col in self.local_columns)
            )
        log.info('%s relationship direction %s', self.prop,
                         self.direction)

    def _determine_joins(self):
        """Determine the 'primaryjoin' and 'secondaryjoin' attributes,
        if not passed to the constructor already.

        This is based on analysis of the foreign key relationships
        between the parent and target mapped selectables.

        """
        if self.secondaryjoin is not None and self.secondary is None:
            raise sa_exc.ArgumentError(
                    "Property %s specified with secondary "
                    "join condition but "
                    "no secondary argument" % self.prop)

        # find a join between the given mapper's mapped table and
        # the given table. will try the mapper's local table first
        # for more specificity, then if not found will try the more
        # general mapped table, which in the case of inheritance is
        # a join.
        try:
            consider_as_foreign_keys = self.consider_as_foreign_keys or None
            if self.secondary is not None:
                if self.secondaryjoin is None:
                    self.secondaryjoin = \
                        join_condition(
                            self.child_selectable,
                            self.secondary,
                            a_subset=self.child_local_selectable,
                            consider_as_foreign_keys=consider_as_foreign_keys
                        )
                if self.primaryjoin is None:
                    self.primaryjoin = \
                        join_condition(
                            self.parent_selectable,
                            self.secondary,
                            a_subset=self.parent_local_selectable,
                            consider_as_foreign_keys=consider_as_foreign_keys
                        )
            else:
                if self.primaryjoin is None:
                    self.primaryjoin = \
                        join_condition(
                            self.parent_selectable,
                            self.child_selectable,
                            a_subset=self.parent_local_selectable,
                            consider_as_foreign_keys=consider_as_foreign_keys
                        )
        except sa_exc.NoForeignKeysError:
            if self.secondary is not None:
                raise sa_exc.NoForeignKeysError("Could not determine join "
                        "condition between parent/child tables on "
                        "relationship %s - there are no foreign keys "
                        "linking these tables via secondary table '%s'.  "
                        "Ensure that referencing columns are associated "
                        "with a ForeignKey or ForeignKeyConstraint, or "
                        "specify 'primaryjoin' and 'secondaryjoin' "
                        "expressions."
                        % (self.prop, self.secondary))
            else:
                raise sa_exc.NoForeignKeysError("Could not determine join "
                        "condition between parent/child tables on "
                        "relationship %s - there are no foreign keys "
                        "linking these tables.  "
                        "Ensure that referencing columns are associated "
                        "with a ForeignKey or ForeignKeyConstraint, or "
                        "specify a 'primaryjoin' expression."
                        % self.prop)
        except sa_exc.AmbiguousForeignKeysError:
            if self.secondary is not None:
                raise sa_exc.AmbiguousForeignKeysError(
                        "Could not determine join "
                        "condition between parent/child tables on "
                        "relationship %s - there are multiple foreign key "
                        "paths linking the tables via secondary table '%s'.  "
                        "Specify the 'foreign_keys' "
                        "argument, providing a list of those columns which "
                        "should be counted as containing a foreign key "
                        "reference from the secondary table to each of the "
                        "parent and child tables."
                        % (self.prop, self.secondary))
            else:
                raise sa_exc.AmbiguousForeignKeysError(
                        "Could not determine join "
                        "condition between parent/child tables on "
                        "relationship %s - there are multiple foreign key "
                        "paths linking the tables.  Specify the "
                        "'foreign_keys' argument, providing a list of those "
                        "columns which should be counted as containing a "
                        "foreign key reference to the parent table."
                        % self.prop)

    @property
    def primaryjoin_minus_local(self):
        return _deep_deannotate(self.primaryjoin, values=("local", "remote"))

    @property
    def secondaryjoin_minus_local(self):
        return _deep_deannotate(self.secondaryjoin, values=("local", "remote"))

    @util.memoized_property
    def primaryjoin_reverse_remote(self):
        """Return the primaryjoin condition suitable for the
        "reverse" direction.

        If the primaryjoin was delivered here with pre-existing
        "remote" annotations, the local/remote annotations
        are reversed.  Otherwise, the local/remote annotations
        are removed.

        """
        if self._has_remote_annotations:
            def replace(element):
                if "remote" in element._annotations:
                    v = element._annotations.copy()
                    del v['remote']
                    v['local'] = True
                    return element._with_annotations(v)
                elif "local" in element._annotations:
                    v = element._annotations.copy()
                    del v['local']
                    v['remote'] = True
                    return element._with_annotations(v)
            return visitors.replacement_traverse(
                                self.primaryjoin, {}, replace)
        else:
            if self._has_foreign_annotations:
                # TODO: coverage
                return _deep_deannotate(self.primaryjoin,
                                values=("local", "remote"))
            else:
                return _deep_deannotate(self.primaryjoin)

    def _has_annotation(self, clause, annotation):
        for col in visitors.iterate(clause, {}):
            if annotation in col._annotations:
                return True
        else:
            return False

    @util.memoized_property
    def _has_foreign_annotations(self):
        return self._has_annotation(self.primaryjoin, "foreign")

    @util.memoized_property
    def _has_remote_annotations(self):
        return self._has_annotation(self.primaryjoin, "remote")

    def _annotate_fks(self):
        """Annotate the primaryjoin and secondaryjoin
        structures with 'foreign' annotations marking columns
        considered as foreign.

        """
        if self._has_foreign_annotations:
            return

        if self.consider_as_foreign_keys:
            self._annotate_from_fk_list()
        else:
            self._annotate_present_fks()

    def _annotate_from_fk_list(self):
        def check_fk(col):
            if col in self.consider_as_foreign_keys:
                return col._annotate({"foreign": True})
        self.primaryjoin = visitors.replacement_traverse(
            self.primaryjoin,
            {},
            check_fk
        )
        if self.secondaryjoin is not None:
            self.secondaryjoin = visitors.replacement_traverse(
                self.secondaryjoin,
                {},
                check_fk
            )

    def _annotate_present_fks(self):
        if self.secondary is not None:
            secondarycols = util.column_set(self.secondary.c)
        else:
            secondarycols = set()

        def is_foreign(a, b):
            if isinstance(a, schema.Column) and \
                        isinstance(b, schema.Column):
                if a.references(b):
                    return a
                elif b.references(a):
                    return b

            if secondarycols:
                if a in secondarycols and b not in secondarycols:
                    return a
                elif b in secondarycols and a not in secondarycols:
                    return b

        def visit_binary(binary):
            if not isinstance(binary.left, sql.ColumnElement) or \
                        not isinstance(binary.right, sql.ColumnElement):
                return

            if "foreign" not in binary.left._annotations and \
                    "foreign" not in binary.right._annotations:
                col = is_foreign(binary.left, binary.right)
                if col is not None:
                    if col.compare(binary.left):
                        binary.left = binary.left._annotate(
                                            {"foreign": True})
                    elif col.compare(binary.right):
                        binary.right = binary.right._annotate(
                                            {"foreign": True})

        self.primaryjoin = visitors.cloned_traverse(
            self.primaryjoin,
            {},
            {"binary": visit_binary}
        )
        if self.secondaryjoin is not None:
            self.secondaryjoin = visitors.cloned_traverse(
                self.secondaryjoin,
                {},
                {"binary": visit_binary}
            )

    def _refers_to_parent_table(self):
        """Return True if the join condition contains column
        comparisons where both columns are in both tables.

        """
        pt = self.parent_selectable
        mt = self.child_selectable
        result = [False]

        def visit_binary(binary):
            c, f = binary.left, binary.right
            if (
                isinstance(c, expression.ColumnClause) and \
                isinstance(f, expression.ColumnClause) and \
                pt.is_derived_from(c.table) and \
                pt.is_derived_from(f.table) and \
                mt.is_derived_from(c.table) and \
                mt.is_derived_from(f.table)
            ):
                result[0] = True
        visitors.traverse(
                    self.primaryjoin,
                    {},
                    {"binary": visit_binary}
                )
        return result[0]

    def _tables_overlap(self):
        """Return True if parent/child tables have some overlap."""

        return  bool(
            set(find_tables(self.parent_selectable)).intersection(
                find_tables(self.child_selectable)
            )
        )

    def _annotate_remote(self):
        """Annotate the primaryjoin and secondaryjoin
        structures with 'remote' annotations marking columns
        considered as part of the 'remote' side.

        """
        if self._has_remote_annotations:
            return

        if self.secondary is not None:
            self._annotate_remote_secondary()
        elif self._local_remote_pairs or self._remote_side:
            self._annotate_remote_from_args()
        elif self._refers_to_parent_table():
            self._annotate_selfref(lambda col: "foreign" in col._annotations)
        elif self._tables_overlap():
            self._annotate_remote_with_overlap()
        else:
            self._annotate_remote_distinct_selectables()

    def _annotate_remote_secondary(self):
        """annotate 'remote' in primaryjoin, secondaryjoin
        when 'secondary' is present.

        """
        def repl(element):
            if self.secondary.c.contains_column(element):
                return element._annotate({"remote": True})
        self.primaryjoin = visitors.replacement_traverse(
                                    self.primaryjoin, {},  repl)
        self.secondaryjoin = visitors.replacement_traverse(
                                    self.secondaryjoin, {}, repl)

    def _annotate_selfref(self, fn):
        """annotate 'remote' in primaryjoin, secondaryjoin
        when the relationship is detected as self-referential.

        """
        def visit_binary(binary):
            equated = binary.left.compare(binary.right)
            if isinstance(binary.left, expression.ColumnClause) and \
                    isinstance(binary.right, expression.ColumnClause):
                # assume one to many - FKs are "remote"
                if fn(binary.left):
                    binary.left = binary.left._annotate({"remote": True})
                if fn(binary.right) and not equated:
                    binary.right = binary.right._annotate(
                                        {"remote": True})
            else:
                self._warn_non_column_elements()

        self.primaryjoin = visitors.cloned_traverse(
                                self.primaryjoin, {},
                                {"binary": visit_binary})

    def _annotate_remote_from_args(self):
        """annotate 'remote' in primaryjoin, secondaryjoin
        when the 'remote_side' or '_local_remote_pairs'
        arguments are used.

        """
        if self._local_remote_pairs:
            if self._remote_side:
                raise sa_exc.ArgumentError(
                        "remote_side argument is redundant "
                        "against more detailed _local_remote_side "
                        "argument.")

            remote_side = [r for (l, r) in self._local_remote_pairs]
        else:
            remote_side = self._remote_side

        if self._refers_to_parent_table():
            self._annotate_selfref(lambda col: col in remote_side)
        else:
            def repl(element):
                if element in remote_side:
                    return element._annotate({"remote": True})
            self.primaryjoin = visitors.replacement_traverse(
                                        self.primaryjoin, {},  repl)

    def _annotate_remote_with_overlap(self):
        """annotate 'remote' in primaryjoin, secondaryjoin
        when the parent/child tables have some set of
        tables in common, though is not a fully self-referential
        relationship.

        """
        def visit_binary(binary):
            binary.left, binary.right = proc_left_right(binary.left,
                                            binary.right)
            binary.right, binary.left = proc_left_right(binary.right,
                                            binary.left)

        def proc_left_right(left, right):
            if isinstance(left, expression.ColumnClause) and \
                    isinstance(right, expression.ColumnClause):
                if self.child_selectable.c.contains_column(right) and \
                        self.parent_selectable.c.contains_column(left):
                    right = right._annotate({"remote": True})
            else:
                self._warn_non_column_elements()

            return left, right

        self.primaryjoin = visitors.cloned_traverse(
                                    self.primaryjoin, {},
                                    {"binary": visit_binary})

    def _annotate_remote_distinct_selectables(self):
        """annotate 'remote' in primaryjoin, secondaryjoin
        when the parent/child tables are entirely
        separate.

        """
        def repl(element):
            if self.child_selectable.c.contains_column(element) and \
                (
                    not self.parent_local_selectable.c.\
                            contains_column(element)
                    or self.child_local_selectable.c.\
                            contains_column(element)):
                return element._annotate({"remote": True})
        self.primaryjoin = visitors.replacement_traverse(
                                    self.primaryjoin, {},  repl)

    def _warn_non_column_elements(self):
        util.warn(
            "Non-simple column elements in primary "
            "join condition for property %s - consider using "
            "remote() annotations to mark the remote side."
            % self.prop
        )

    def _annotate_local(self):
        """Annotate the primaryjoin and secondaryjoin
        structures with 'local' annotations.

        This annotates all column elements found
        simultaneously in the parent table
        and the join condition that don't have a
        'remote' annotation set up from
        _annotate_remote() or user-defined.

        """
        if self._has_annotation(self.primaryjoin, "local"):
            return

        if self._local_remote_pairs:
            local_side = util.column_set([l for (l, r)
                                in self._local_remote_pairs])
        else:
            local_side = util.column_set(self.parent_selectable.c)

        def locals_(elem):
            if "remote" not in elem._annotations and \
                    elem in local_side:
                return elem._annotate({"local": True})
        self.primaryjoin = visitors.replacement_traverse(
                self.primaryjoin, {}, locals_
            )

    def _check_remote_side(self):
        if not self.local_remote_pairs:
            raise sa_exc.ArgumentError('Relationship %s could '
                    'not determine any unambiguous local/remote column '
                    'pairs based on join condition and remote_side '
                    'arguments.  '
                    'Consider using the remote() annotation to '
                    'accurately mark those elements of the join '
                    'condition that are on the remote side of '
                    'the relationship.'
                    % (self.prop, ))

    def _check_foreign_cols(self, join_condition, primary):
        """Check the foreign key columns collected and emit error
        messages."""

        can_sync = False

        foreign_cols = self._gather_columns_with_annotation(
                                join_condition, "foreign")

        has_foreign = bool(foreign_cols)

        if primary:
            can_sync = bool(self.synchronize_pairs)
        else:
            can_sync = bool(self.secondary_synchronize_pairs)

        if self.support_sync and can_sync or \
                (not self.support_sync and has_foreign):
            return

        # from here below is just determining the best error message
        # to report.  Check for a join condition using any operator
        # (not just ==), perhaps they need to turn on "viewonly=True".
        if self.support_sync and has_foreign and not can_sync:
            err = "Could not locate any simple equality expressions "\
                    "involving locally mapped foreign key columns for "\
                    "%s join condition "\
                    "'%s' on relationship %s." % (
                        primary and 'primary' or 'secondary',
                        join_condition,
                        self.prop
                    )
            err += \
                "  Ensure that referencing columns are associated "\
                "with a ForeignKey or ForeignKeyConstraint, or are "\
                "annotated in the join condition with the foreign() "\
                "annotation. To allow comparison operators other than "\
                "'==', the relationship can be marked as viewonly=True."

            raise sa_exc.ArgumentError(err)
        else:
            err = "Could not locate any relevant foreign key columns "\
                    "for %s join condition '%s' on relationship %s." % (
                        primary and 'primary' or 'secondary',
                        join_condition,
                        self.prop
                    )
            err += \
                '  Ensure that referencing columns are associated '\
                'with a ForeignKey or ForeignKeyConstraint, or are '\
                'annotated in the join condition with the foreign() '\
                'annotation.'
            raise sa_exc.ArgumentError(err)

    def _determine_direction(self):
        """Determine if this relationship is one to many, many to one,
        many to many.

        """
        if self.secondaryjoin is not None:
            self.direction = MANYTOMANY
        else:
            parentcols = util.column_set(self.parent_selectable.c)
            targetcols = util.column_set(self.child_selectable.c)

            # fk collection which suggests ONETOMANY.
            onetomany_fk = targetcols.intersection(
                            self.foreign_key_columns)

            # fk collection which suggests MANYTOONE.

            manytoone_fk = parentcols.intersection(
                            self.foreign_key_columns)

            if onetomany_fk and manytoone_fk:
                # fks on both sides.  test for overlap of local/remote
                # with foreign key
                self_equated = self.remote_columns.intersection(
                                        self.local_columns
                                    )
                onetomany_local = self.remote_columns.\
                                    intersection(self.foreign_key_columns).\
                                    difference(self_equated)
                manytoone_local = self.local_columns.\
                                    intersection(self.foreign_key_columns).\
                                    difference(self_equated)
                if onetomany_local and not manytoone_local:
                    self.direction = ONETOMANY
                elif manytoone_local and not onetomany_local:
                    self.direction = MANYTOONE
                else:
                    raise sa_exc.ArgumentError(
                        "Can't determine relationship"
                        " direction for relationship '%s' - foreign "
                        "key columns within the join condition are present "
                        "in both the parent and the child's mapped tables.  "
                        "Ensure that only those columns referring "
                        "to a parent column are marked as foreign, "
                        "either via the foreign() annotation or "
                        "via the foreign_keys argument." % self.prop)
            elif onetomany_fk:
                self.direction = ONETOMANY
            elif manytoone_fk:
                self.direction = MANYTOONE
            else:
                raise sa_exc.ArgumentError("Can't determine relationship "
                        "direction for relationship '%s' - foreign "
                        "key columns are present in neither the parent "
                        "nor the child's mapped tables" % self.prop)

    def _deannotate_pairs(self, collection):
        """provide deannotation for the various lists of
        pairs, so that using them in hashes doesn't incur
        high-overhead __eq__() comparisons against
        original columns mapped.

        """
        return [(x._deannotate(), y._deannotate())
            for x, y in collection]

    def _setup_pairs(self):
        sync_pairs = []
        lrp = util.OrderedSet([])
        secondary_sync_pairs = []

        def go(joincond, collection):
            def visit_binary(binary, left, right):
                if "remote" in right._annotations and \
                    "remote" not in left._annotations and \
                        self.can_be_synced_fn(left):
                    lrp.add((left, right))
                elif "remote" in left._annotations and \
                    "remote" not in right._annotations and \
                        self.can_be_synced_fn(right):
                    lrp.add((right, left))
                if binary.operator is operators.eq and \
                        self.can_be_synced_fn(left, right):
                    if "foreign" in right._annotations:
                        collection.append((left, right))
                    elif "foreign" in left._annotations:
                        collection.append((right, left))
            visit_binary_product(visit_binary, joincond)

        for joincond, collection in [
            (self.primaryjoin, sync_pairs),
            (self.secondaryjoin, secondary_sync_pairs)
        ]:
            if joincond is None:
                continue
            go(joincond, collection)

        self.local_remote_pairs = self._deannotate_pairs(lrp)
        self.synchronize_pairs = self._deannotate_pairs(sync_pairs)
        self.secondary_synchronize_pairs = \
            self._deannotate_pairs(secondary_sync_pairs)

    @util.memoized_property
    def remote_columns(self):
        return self._gather_join_annotations("remote")

    @util.memoized_property
    def local_columns(self):
        return self._gather_join_annotations("local")

    @util.memoized_property
    def foreign_key_columns(self):
        return self._gather_join_annotations("foreign")

    @util.memoized_property
    def deannotated_primaryjoin(self):
        return _deep_deannotate(self.primaryjoin)

    @util.memoized_property
    def deannotated_secondaryjoin(self):
        if self.secondaryjoin is not None:
            return _deep_deannotate(self.secondaryjoin)
        else:
            return None

    def _gather_join_annotations(self, annotation):
        s = set(
            self._gather_columns_with_annotation(
                        self.primaryjoin, annotation)
        )
        if self.secondaryjoin is not None:
            s.update(
                self._gather_columns_with_annotation(
                        self.secondaryjoin, annotation)
            )
        return set([x._deannotate() for x in s])

    def _gather_columns_with_annotation(self, clause, *annotation):
        annotation = set(annotation)
        return set([
            col for col in visitors.iterate(clause, {})
            if annotation.issubset(col._annotations)
        ])

    def join_targets(self, source_selectable,
                            dest_selectable,
                            aliased,
                            single_crit=None):
        """Given a source and destination selectable, create a
        join between them.

        This takes into account aliasing the join clause
        to reference the appropriate corresponding columns
        in the target objects, as well as the extra child
        criterion, equivalent column sets, etc.

        """

        # place a barrier on the destination such that
        # replacement traversals won't ever dig into it.
        # its internal structure remains fixed
        # regardless of context.
        dest_selectable = _shallow_annotate(
                                dest_selectable,
                                {'no_replacement_traverse': True})

        primaryjoin, secondaryjoin, secondary = self.primaryjoin, \
            self.secondaryjoin, self.secondary

        # adjust the join condition for single table inheritance,
        # in the case that the join is to a subclass
        # this is analogous to the
        # "_adjust_for_single_table_inheritance()" method in Query.

        if single_crit is not None:
            if secondaryjoin is not None:
                secondaryjoin = secondaryjoin & single_crit
            else:
                primaryjoin = primaryjoin & single_crit

        if aliased:
            if secondary is not None:
                secondary = secondary.alias()
                primary_aliasizer = ClauseAdapter(secondary)
                secondary_aliasizer = \
                    ClauseAdapter(dest_selectable,
                        equivalents=self.child_equivalents).\
                        chain(primary_aliasizer)
                if source_selectable is not None:
                    primary_aliasizer = \
                        ClauseAdapter(secondary).\
                            chain(ClauseAdapter(source_selectable,
                            equivalents=self.parent_equivalents))
                secondaryjoin = \
                    secondary_aliasizer.traverse(secondaryjoin)
            else:
                primary_aliasizer = ClauseAdapter(dest_selectable,
                        exclude_fn=_ColInAnnotations("local"),
                        equivalents=self.child_equivalents)
                if source_selectable is not None:
                    primary_aliasizer.chain(
                        ClauseAdapter(source_selectable,
                            exclude_fn=_ColInAnnotations("remote"),
                            equivalents=self.parent_equivalents))
                secondary_aliasizer = None

            primaryjoin = primary_aliasizer.traverse(primaryjoin)
            target_adapter = secondary_aliasizer or primary_aliasizer
            target_adapter.exclude_fn = None
        else:
            target_adapter = None
        return primaryjoin, secondaryjoin, secondary, \
                        target_adapter, dest_selectable

    def create_lazy_clause(self, reverse_direction=False):
        binds = util.column_dict()
        lookup = util.column_dict()
        equated_columns = util.column_dict()

        if reverse_direction and self.secondaryjoin is None:
            for l, r in self.local_remote_pairs:
                _list = lookup.setdefault(r, [])
                _list.append((r, l))
                equated_columns[l] = r
        else:
            for l, r in self.local_remote_pairs:
                _list = lookup.setdefault(l, [])
                _list.append((l, r))
                equated_columns[r] = l

        def col_to_bind(col):
            if col in lookup:
                for tobind, equated in lookup[col]:
                    if equated in binds:
                        return None
                if col not in binds:
                    binds[col] = sql.bindparam(
                        None, None, type_=col.type, unique=True)
                return binds[col]
            return None

        lazywhere = self.deannotated_primaryjoin

        if self.deannotated_secondaryjoin is None or not reverse_direction:
            lazywhere = visitors.replacement_traverse(
                                            lazywhere, {}, col_to_bind)

        if self.deannotated_secondaryjoin is not None:
            secondaryjoin = self.deannotated_secondaryjoin
            if reverse_direction:
                secondaryjoin = visitors.replacement_traverse(
                                            secondaryjoin, {}, col_to_bind)
            lazywhere = sql.and_(lazywhere, secondaryjoin)

        bind_to_col = dict((binds[col].key, col) for col in binds)

        return lazywhere, bind_to_col, equated_columns

class _ColInAnnotations(object):
    """Seralizable equivalent to:

        lambda c: "name" in c._annotations
    """
    def __init__(self, name):
        self.name = name

    def __call__(self, c):
        return self.name in c._annotations