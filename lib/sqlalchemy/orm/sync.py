# orm/sync.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""private module containing functions used for copying data
between instances based on join conditions.

"""

from . import exc, util as orm_util, attributes


def populate(source, source_mapper, dest, dest_mapper,
                        synchronize_pairs, uowcommit, flag_cascaded_pks):
    source_dict = source.dict
    dest_dict = dest.dict

    for l, r in synchronize_pairs:
        try:
            # inline of source_mapper._get_state_attr_by_column
            prop = source_mapper._columntoproperty[l]
            value = source.manager[prop.key].impl.get(source, source_dict,
                                                    attributes.PASSIVE_OFF)
        except exc.UnmappedColumnError:
            _raise_col_to_prop(False, source_mapper, l, dest_mapper, r)

        try:
            # inline of dest_mapper._set_state_attr_by_column
            prop = dest_mapper._columntoproperty[r]
            dest.manager[prop.key].impl.set(dest, dest_dict, value, None)
        except exc.UnmappedColumnError:
            _raise_col_to_prop(True, source_mapper, l, dest_mapper, r)

        # technically the "r.primary_key" check isn't
        # needed here, but we check for this condition to limit
        # how often this logic is invoked for memory/performance
        # reasons, since we only need this info for a primary key
        # destination.
        if flag_cascaded_pks and l.primary_key and \
                    r.primary_key and \
                    r.references(l):
            uowcommit.attributes[("pk_cascaded", dest, r)] = True


def clear(dest, dest_mapper, synchronize_pairs):
    for l, r in synchronize_pairs:
        if r.primary_key:
            raise AssertionError(
                "Dependency rule tried to blank-out primary key "
                "column '%s' on instance '%s'" %
                (r, orm_util.state_str(dest))
            )
        try:
            dest_mapper._set_state_attr_by_column(dest, dest.dict, r, None)
        except exc.UnmappedColumnError:
            _raise_col_to_prop(True, None, l, dest_mapper, r)


def update(source, source_mapper, dest, old_prefix, synchronize_pairs):
    for l, r in synchronize_pairs:
        try:
            oldvalue = source_mapper._get_committed_attr_by_column(
                source.obj(), l)
            value = source_mapper._get_state_attr_by_column(
                source, source.dict, l)
        except exc.UnmappedColumnError:
            _raise_col_to_prop(False, source_mapper, l, None, r)
        dest[r.key] = value
        dest[old_prefix + r.key] = oldvalue


def populate_dict(source, source_mapper, dict_, synchronize_pairs):
    for l, r in synchronize_pairs:
        try:
            value = source_mapper._get_state_attr_by_column(
                source, source.dict, l)
        except exc.UnmappedColumnError:
            _raise_col_to_prop(False, source_mapper, l, None, r)

        dict_[r.key] = value


def source_modified(uowcommit, source, source_mapper, synchronize_pairs):
    """return true if the source object has changes from an old to a
    new value on the given synchronize pairs

    """
    for l, r in synchronize_pairs:
        try:
            prop = source_mapper._columntoproperty[l]
        except exc.UnmappedColumnError:
            _raise_col_to_prop(False, source_mapper, l, None, r)
        history = uowcommit.get_attribute_history(source, prop.key,
                                        attributes.PASSIVE_NO_INITIALIZE)
        if bool(history.deleted):
            return True
    else:
        return False


def _raise_col_to_prop(isdest, source_mapper, source_column,
                       dest_mapper, dest_column):
    if isdest:
        raise exc.UnmappedColumnError("Can't execute sync rule for "
                "destination column '%s'; mapper '%s' does not map "
                "this column.  Try using an explicit `foreign_keys` "
                "collection which does not include this column (or use "
                "a viewonly=True relation)." % (dest_column,
                dest_mapper))
    else:
        raise exc.UnmappedColumnError("Can't execute sync rule for "
                "source column '%s'; mapper '%s' does not map this "
                "column.  Try using an explicit `foreign_keys` "
                "collection which does not include destination column "
                "'%s' (or use a viewonly=True relation)."
                % (source_column, source_mapper, dest_column))
