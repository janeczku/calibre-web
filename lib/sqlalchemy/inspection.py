# sqlalchemy/inspect.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""The inspection module provides the :func:`.inspect` function,
which delivers runtime information about a wide variety
of SQLAlchemy objects, both within the Core as well as the
ORM.

The :func:`.inspect` function is the entry point to SQLAlchemy's
public API for viewing the configuration and construction
of in-memory objects.   Depending on the type of object
passed to :func:`.inspect`, the return value will either be
a related object which provides a known interface, or in many
cases it will return the object itself.

The rationale for :func:`.inspect` is twofold.  One is that
it replaces the need to be aware of a large variety of "information
getting" functions in SQLAlchemy, such as :meth:`.Inspector.from_engine`,
:func:`.orm.attributes.instance_state`, :func:`.orm.class_mapper`,
and others.    The other is that the return value of :func:`.inspect`
is guaranteed to obey a documented API, thus allowing third party
tools which build on top of SQLAlchemy configurations to be constructed
in a forwards-compatible way.

.. versionadded:: 0.8 The :func:`.inspect` system is introduced
   as of version 0.8.

"""

from . import util, exc
_registrars = util.defaultdict(list)


def inspect(subject, raiseerr=True):
    """Produce an inspection object for the given target.

    The returned value in some cases may be the
    same object as the one given, such as if a
    :class:`.orm.Mapper` object is passed.   In other
    cases, it will be an instance of the registered
    inspection type for the given object, such as
    if a :class:`.engine.Engine` is passed, an
    :class:`.engine.Inspector` object is returned.

    :param subject: the subject to be inspected.
    :param raiseerr: When ``True``, if the given subject
     does not
     correspond to a known SQLAlchemy inspected type,
     :class:`sqlalchemy.exc.NoInspectionAvailable`
     is raised.  If ``False``, ``None`` is returned.

     """
    type_ = type(subject)
    for cls in type_.__mro__:
        if cls in _registrars:
            reg = _registrars[cls]
            if reg is True:
                return subject
            ret = reg(subject)
            if ret is not None:
                break
    else:
        reg = ret = None

    if raiseerr and (
            reg is None or ret is None
        ):
        raise exc.NoInspectionAvailable(
            "No inspection system is "
            "available for object of type %s" %
            type_)
    return ret


def _inspects(*types):
    def decorate(fn_or_cls):
        for type_ in types:
            if type_ in _registrars:
                raise AssertionError(
                            "Type %s is already "
                            "registered" % type_)
            _registrars[type_] = fn_or_cls
        return fn_or_cls
    return decorate


def _self_inspects(*types):
    _inspects(*types)(True)
