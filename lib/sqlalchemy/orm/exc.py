# orm/exc.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""SQLAlchemy ORM exceptions."""
from .. import exc as sa_exc, util
orm_util = util.importlater('sqlalchemy.orm', 'util')
attributes = util.importlater('sqlalchemy.orm', 'attributes')

NO_STATE = (AttributeError, KeyError)
"""Exception types that may be raised by instrumentation implementations."""


class StaleDataError(sa_exc.SQLAlchemyError):
    """An operation encountered database state that is unaccounted for.

    Conditions which cause this to happen include:

    * A flush may have attempted to update or delete rows
      and an unexpected number of rows were matched during
      the UPDATE or DELETE statement.   Note that when
      version_id_col is used, rows in UPDATE or DELETE statements
      are also matched against the current known version
      identifier.

    * A mapped object with version_id_col was refreshed,
      and the version number coming back from the database does
      not match that of the object itself.

    * A object is detached from its parent object, however
      the object was previously attached to a different parent
      identity which was garbage collected, and a decision
      cannot be made if the new parent was really the most
      recent "parent".

      .. versionadded:: 0.7.4

    """

ConcurrentModificationError = StaleDataError


class FlushError(sa_exc.SQLAlchemyError):
    """A invalid condition was detected during flush()."""


class UnmappedError(sa_exc.InvalidRequestError):
    """Base for exceptions that involve expected mappings not present."""


class ObjectDereferencedError(sa_exc.SQLAlchemyError):
    """An operation cannot complete due to an object being garbage
    collected.

    """


class DetachedInstanceError(sa_exc.SQLAlchemyError):
    """An attempt to access unloaded attributes on a
    mapped instance that is detached."""


class UnmappedInstanceError(UnmappedError):
    """An mapping operation was requested for an unknown instance."""

    def __init__(self, obj, msg=None):
        if not msg:
            try:
                mapper = orm_util.class_mapper(type(obj))
                name = _safe_cls_name(type(obj))
                msg = ("Class %r is mapped, but this instance lacks "
                       "instrumentation.  This occurs when the instance"
                       "is created before sqlalchemy.orm.mapper(%s) "
                       "was called." % (name, name))
            except UnmappedClassError:
                msg = _default_unmapped(type(obj))
                if isinstance(obj, type):
                    msg += (
                        '; was a class (%s) supplied where an instance was '
                        'required?' % _safe_cls_name(obj))
        UnmappedError.__init__(self, msg)

    def __reduce__(self):
        return self.__class__, (None, self.args[0])


class UnmappedClassError(UnmappedError):
    """An mapping operation was requested for an unknown class."""

    def __init__(self, cls, msg=None):
        if not msg:
            msg = _default_unmapped(cls)
        UnmappedError.__init__(self, msg)

    def __reduce__(self):
        return self.__class__, (None, self.args[0])


class ObjectDeletedError(sa_exc.InvalidRequestError):
    """A refresh operation failed to retrieve the database
    row corresponding to an object's known primary key identity.

    A refresh operation proceeds when an expired attribute is
    accessed on an object, or when :meth:`.Query.get` is
    used to retrieve an object which is, upon retrieval, detected
    as expired.   A SELECT is emitted for the target row
    based on primary key; if no row is returned, this
    exception is raised.

    The true meaning of this exception is simply that
    no row exists for the primary key identifier associated
    with a persistent object.   The row may have been
    deleted, or in some cases the primary key updated
    to a new value, outside of the ORM's management of the target
    object.

    """
    def __init__(self, state, msg=None):
        if not msg:
            msg = "Instance '%s' has been deleted, or its "\
             "row is otherwise not present." % orm_util.state_str(state)

        sa_exc.InvalidRequestError.__init__(self, msg)

    def __reduce__(self):
        return self.__class__, (None, self.args[0])


class UnmappedColumnError(sa_exc.InvalidRequestError):
    """Mapping operation was requested on an unknown column."""


class NoResultFound(sa_exc.InvalidRequestError):
    """A database result was required but none was found."""


class MultipleResultsFound(sa_exc.InvalidRequestError):
    """A single database result was required but more than one were found."""


def _safe_cls_name(cls):
    try:
        cls_name = '.'.join((cls.__module__, cls.__name__))
    except AttributeError:
        cls_name = getattr(cls, '__name__', None)
        if cls_name is None:
            cls_name = repr(cls)
    return cls_name


def _default_unmapped(cls):
    try:
        mappers = attributes.manager_of_class(cls).mappers
    except NO_STATE:
        mappers = {}
    except TypeError:
        mappers = {}
    name = _safe_cls_name(cls)

    if not mappers:
        return "Class '%s' is not mapped" % name
