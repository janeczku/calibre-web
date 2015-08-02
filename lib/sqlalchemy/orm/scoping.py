# orm/scoping.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

from .. import exc as sa_exc
from ..util import ScopedRegistry, ThreadLocalRegistry, warn
from . import class_mapper, exc as orm_exc
from .session import Session


__all__ = ['scoped_session']


class scoped_session(object):
    """Provides scoped management of :class:`.Session` objects.

    See :ref:`unitofwork_contextual` for a tutorial.

    """

    def __init__(self, session_factory, scopefunc=None):
        """Construct a new :class:`.scoped_session`.

        :param session_factory: a factory to create new :class:`.Session`
         instances. This is usually, but not necessarily, an instance
         of :class:`.sessionmaker`.
        :param scopefunc: optional function which defines
         the current scope.   If not passed, the :class:`.scoped_session`
         object assumes "thread-local" scope, and will use
         a Python ``threading.local()`` in order to maintain the current
         :class:`.Session`.  If passed, the function should return
         a hashable token; this token will be used as the key in a
         dictionary in order to store and retrieve the current
         :class:`.Session`.

        """
        self.session_factory = session_factory
        if scopefunc:
            self.registry = ScopedRegistry(session_factory, scopefunc)
        else:
            self.registry = ThreadLocalRegistry(session_factory)

    def __call__(self, **kw):
        """Return the current :class:`.Session`, creating it
        using the session factory if not present.

        :param \**kw: Keyword arguments will be passed to the
         session factory callable, if an existing :class:`.Session`
         is not present.  If the :class:`.Session` is present and
         keyword arguments have been passed,
         :exc:`~sqlalchemy.exc.InvalidRequestError` is raised.

        """
        if kw:
            scope = kw.pop('scope', False)
            if scope is not None:
                if self.registry.has():
                    raise sa_exc.InvalidRequestError(
                            "Scoped session is already present; "
                            "no new arguments may be specified.")
                else:
                    sess = self.session_factory(**kw)
                    self.registry.set(sess)
                    return sess
            else:
                return self.session_factory(**kw)
        else:
            return self.registry()

    def remove(self):
        """Dispose of the current :class:`.Session`, if present.

        This will first call :meth:`.Session.close` method
        on the current :class:`.Session`, which releases any existing
        transactional/connection resources still being held; transactions
        specifically are rolled back.  The :class:`.Session` is then
        discarded.   Upon next usage within the same scope,
        the :class:`.scoped_session` will produce a new
        :class:`.Session` object.

        """

        if self.registry.has():
            self.registry().close()
        self.registry.clear()

    def configure(self, **kwargs):
        """reconfigure the :class:`.sessionmaker` used by this
        :class:`.scoped_session`.

        See :meth:`.sessionmaker.configure`.

        """

        if self.registry.has():
            warn('At least one scoped session is already present. '
                      ' configure() can not affect sessions that have '
                      'already been created.')

        self.session_factory.configure(**kwargs)

    def query_property(self, query_cls=None):
        """return a class property which produces a :class:`.Query` object
        against the class and the current :class:`.Session` when called.

        e.g.::

            Session = scoped_session(sessionmaker())

            class MyClass(object):
                query = Session.query_property()

            # after mappers are defined
            result = MyClass.query.filter(MyClass.name=='foo').all()

        Produces instances of the session's configured query class by
        default.  To override and use a custom implementation, provide
        a ``query_cls`` callable.  The callable will be invoked with
        the class's mapper as a positional argument and a session
        keyword argument.

        There is no limit to the number of query properties placed on
        a class.

        """
        class query(object):
            def __get__(s, instance, owner):
                try:
                    mapper = class_mapper(owner)
                    if mapper:
                        if query_cls:
                            # custom query class
                            return query_cls(mapper, session=self.registry())
                        else:
                            # session's configured query class
                            return self.registry().query(mapper)
                except orm_exc.UnmappedClassError:
                    return None
        return query()

ScopedSession = scoped_session
"""Old name for backwards compatibility."""


def instrument(name):
    def do(self, *args, **kwargs):
        return getattr(self.registry(), name)(*args, **kwargs)
    return do

for meth in Session.public_methods:
    setattr(scoped_session, meth, instrument(meth))


def makeprop(name):
    def set(self, attr):
        setattr(self.registry(), name, attr)

    def get(self):
        return getattr(self.registry(), name)

    return property(get, set)

for prop in ('bind', 'dirty', 'deleted', 'new', 'identity_map',
             'is_active', 'autoflush', 'no_autoflush'):
    setattr(scoped_session, prop, makeprop(prop))


def clslevel(name):
    def do(cls, *args, **kwargs):
        return getattr(Session, name)(*args, **kwargs)
    return classmethod(do)

for prop in ('close_all', 'object_session', 'identity_key'):
    setattr(scoped_session, prop, clslevel(prop))
