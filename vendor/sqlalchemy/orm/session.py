# orm/session.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
"""Provides the Session class and related utilities."""

from __future__ import with_statement

import weakref
from .. import util, sql, engine, exc as sa_exc, event
from ..sql import util as sql_util, expression
from . import (
    SessionExtension, attributes, exc, query, util as orm_util,
    loading, identity
    )
from .util import (
    object_mapper, class_mapper,
    _class_to_mapper, _state_mapper, object_state,
    _none_set
    )
from .unitofwork import UOWTransaction
from .mapper import Mapper
from .events import SessionEvents
statelib = util.importlater("sqlalchemy.orm", "state")
import sys

__all__ = ['Session', 'SessionTransaction', 'SessionExtension', 'sessionmaker']


class _SessionClassMethods(object):
    """Class-level methods for :class:`.Session`, :class:`.sessionmaker`."""

    @classmethod
    def close_all(cls):
        """Close *all* sessions in memory."""

        for sess in _sessions.values():
            sess.close()

    @classmethod
    def identity_key(cls, *args, **kwargs):
        """Return an identity key.

        This is an alias of :func:`.util.identity_key`.

        """
        return orm_util.identity_key(*args, **kwargs)

    @classmethod
    def object_session(cls, instance):
        """Return the :class:`.Session` to which an object belongs.

        This is an alias of :func:`.object_session`.

        """

        return object_session(instance)


ACTIVE = util.symbol('ACTIVE')
PREPARED = util.symbol('PREPARED')
COMMITTED = util.symbol('COMMITTED')
DEACTIVE = util.symbol('DEACTIVE')
CLOSED = util.symbol('CLOSED')

class SessionTransaction(object):
    """A :class:`.Session`-level transaction.

    :class:`.SessionTransaction` is a mostly behind-the-scenes object
    not normally referenced directly by application code.   It coordinates
    among multiple :class:`.Connection` objects, maintaining a database
    transaction for each one individually, committing or rolling them
    back all at once.   It also provides optional two-phase commit behavior
    which can augment this coordination operation.

    The :attr:`.Session.transaction` attribute of :class:`.Session`
    refers to the current :class:`.SessionTransaction` object in use, if any.


    A :class:`.SessionTransaction` is associated with a :class:`.Session`
    in its default mode of ``autocommit=False`` immediately, associated
    with no database connections.  As the :class:`.Session` is called upon
    to emit SQL on behalf of various :class:`.Engine` or :class:`.Connection`
    objects, a corresponding :class:`.Connection` and associated
    :class:`.Transaction` is added to a collection within the
    :class:`.SessionTransaction` object, becoming one of the
    connection/transaction pairs maintained by the
    :class:`.SessionTransaction`.

    The lifespan of the :class:`.SessionTransaction` ends when the
    :meth:`.Session.commit`, :meth:`.Session.rollback` or
    :meth:`.Session.close` methods are called.  At this point, the
    :class:`.SessionTransaction` removes its association with its parent
    :class:`.Session`.   A :class:`.Session` that is in ``autocommit=False``
    mode will create a new :class:`.SessionTransaction` to replace it
    immediately, whereas a :class:`.Session` that's in ``autocommit=True``
    mode will remain without a :class:`.SessionTransaction` until the
    :meth:`.Session.begin` method is called.

    Another detail of :class:`.SessionTransaction` behavior is that it is
    capable of "nesting".  This means that the :meth:`.Session.begin` method
    can be called while an existing :class:`.SessionTransaction` is already
    present, producing a new :class:`.SessionTransaction` that temporarily
    replaces the parent :class:`.SessionTransaction`.   When a
    :class:`.SessionTransaction` is produced as nested, it assigns itself to
    the :attr:`.Session.transaction` attribute.  When it is ended via
    :meth:`.Session.commit` or :meth:`.Session.rollback`, it restores its
    parent :class:`.SessionTransaction` back onto the
    :attr:`.Session.transaction` attribute.  The behavior is effectively a
    stack, where :attr:`.Session.transaction` refers to the current head of
    the stack.

    The purpose of this stack is to allow nesting of
    :meth:`.Session.rollback` or :meth:`.Session.commit` calls in context
    with various flavors of :meth:`.Session.begin`. This nesting behavior
    applies to when :meth:`.Session.begin_nested` is used to emit a
    SAVEPOINT transaction, and is also used to produce a so-called
    "subtransaction" which allows a block of code to use a
    begin/rollback/commit sequence regardless of whether or not its enclosing
    code block has begun a transaction.  The :meth:`.flush` method, whether
    called explicitly or via autoflush, is the primary consumer of the
    "subtransaction" feature, in that it wishes to guarantee that it works
    within in a transaction block regardless of whether or not the
    :class:`.Session` is in transactional mode when the method is called.

    See also:

    :meth:`.Session.rollback`

    :meth:`.Session.commit`

    :meth:`.Session.begin`

    :meth:`.Session.begin_nested`

    :attr:`.Session.is_active`

    :meth:`.SessionEvents.after_commit`

    :meth:`.SessionEvents.after_rollback`

    :meth:`.SessionEvents.after_soft_rollback`

    """

    _rollback_exception = None

    def __init__(self, session, parent=None, nested=False):
        self.session = session
        self._connections = {}
        self._parent = parent
        self.nested = nested
        self._state = ACTIVE
        if not parent and nested:
            raise sa_exc.InvalidRequestError(
                "Can't start a SAVEPOINT transaction when no existing "
                "transaction is in progress")

        if self.session._enable_transaction_accounting:
            self._take_snapshot()

        if self.session.dispatch.after_transaction_create:
            self.session.dispatch.after_transaction_create(self.session, self)

    @property
    def is_active(self):
        return self.session is not None and self._state is ACTIVE

    def _assert_active(self, prepared_ok=False,
                        rollback_ok=False,
                        deactive_ok=False,
                        closed_msg="This transaction is closed"):
        if self._state is COMMITTED:
            raise sa_exc.InvalidRequestError(
                    "This session is in 'committed' state; no further "
                    "SQL can be emitted within this transaction."
                )
        elif self._state is PREPARED:
            if not prepared_ok:
                raise sa_exc.InvalidRequestError(
                        "This session is in 'prepared' state; no further "
                        "SQL can be emitted within this transaction."
                    )
        elif self._state is DEACTIVE:
            if not deactive_ok and not rollback_ok:
                if self._rollback_exception:
                    raise sa_exc.InvalidRequestError(
                        "This Session's transaction has been rolled back "
                        "due to a previous exception during flush."
                        " To begin a new transaction with this Session, "
                        "first issue Session.rollback()."
                        " Original exception was: %s"
                        % self._rollback_exception
                    )
                elif not deactive_ok:
                    raise sa_exc.InvalidRequestError(
                        "This Session's transaction has been rolled back "
                        "by a nested rollback() call.  To begin a new "
                        "transaction, issue Session.rollback() first."
                        )
        elif self._state is CLOSED:
            raise sa_exc.ResourceClosedError(closed_msg)

    @property
    def _is_transaction_boundary(self):
        return self.nested or not self._parent

    def connection(self, bindkey, **kwargs):
        self._assert_active()
        bind = self.session.get_bind(bindkey, **kwargs)
        return self._connection_for_bind(bind)

    def _begin(self, nested=False):
        self._assert_active()
        return SessionTransaction(
            self.session, self, nested=nested)

    def _iterate_parents(self, upto=None):
        if self._parent is upto:
            return (self,)
        else:
            if self._parent is None:
                raise sa_exc.InvalidRequestError(
                    "Transaction %s is not on the active transaction list" % (
                    upto))
            return (self,) + self._parent._iterate_parents(upto)

    def _take_snapshot(self):
        if not self._is_transaction_boundary:
            self._new = self._parent._new
            self._deleted = self._parent._deleted
            self._dirty = self._parent._dirty
            self._key_switches = self._parent._key_switches
            return

        if not self.session._flushing:
            self.session.flush()

        self._new = weakref.WeakKeyDictionary()
        self._deleted = weakref.WeakKeyDictionary()
        self._dirty = weakref.WeakKeyDictionary()
        self._key_switches = weakref.WeakKeyDictionary()

    def _restore_snapshot(self, dirty_only=False):
        assert self._is_transaction_boundary

        for s in set(self._new).union(self.session._new):
            self.session._expunge_state(s)
            if s.key:
                del s.key

        for s, (oldkey, newkey) in self._key_switches.items():
            self.session.identity_map.discard(s)
            s.key = oldkey
            self.session.identity_map.replace(s)

        for s in set(self._deleted).union(self.session._deleted):
            if s.deleted:
                #assert s in self._deleted
                del s.deleted
            self.session._update_impl(s, discard_existing=True)

        assert not self.session._deleted

        for s in self.session.identity_map.all_states():
            if not dirty_only or s.modified or s in self._dirty:
                s._expire(s.dict, self.session.identity_map._modified)

    def _remove_snapshot(self):
        assert self._is_transaction_boundary

        if not self.nested and self.session.expire_on_commit:
            for s in self.session.identity_map.all_states():
                s._expire(s.dict, self.session.identity_map._modified)
            for s in self._deleted:
                s.session_id = None
            self._deleted.clear()


    def _connection_for_bind(self, bind):
        self._assert_active()

        if bind in self._connections:
            return self._connections[bind][0]

        if self._parent:
            conn = self._parent._connection_for_bind(bind)
            if not self.nested:
                return conn
        else:
            if isinstance(bind, engine.Connection):
                conn = bind
                if conn.engine in self._connections:
                    raise sa_exc.InvalidRequestError(
                        "Session already has a Connection associated for the "
                        "given Connection's Engine")
            else:
                conn = bind.contextual_connect()

        if self.session.twophase and self._parent is None:
            transaction = conn.begin_twophase()
        elif self.nested:
            transaction = conn.begin_nested()
        else:
            transaction = conn.begin()

        self._connections[conn] = self._connections[conn.engine] = \
          (conn, transaction, conn is not bind)
        self.session.dispatch.after_begin(self.session, self, conn)
        return conn

    def prepare(self):
        if self._parent is not None or not self.session.twophase:
            raise sa_exc.InvalidRequestError(
                "'twophase' mode not enabled, or not root transaction; "
                "can't prepare.")
        self._prepare_impl()

    def _prepare_impl(self):
        self._assert_active()
        if self._parent is None or self.nested:
            self.session.dispatch.before_commit(self.session)

        stx = self.session.transaction
        if stx is not self:
            for subtransaction in stx._iterate_parents(upto=self):
                subtransaction.commit()

        if not self.session._flushing:
            for _flush_guard in xrange(100):
                if self.session._is_clean():
                    break
                self.session.flush()
            else:
                raise exc.FlushError(
                        "Over 100 subsequent flushes have occurred within "
                        "session.commit() - is an after_flush() hook "
                        "creating new objects?")

        if self._parent is None and self.session.twophase:
            try:
                for t in set(self._connections.values()):
                    t[1].prepare()
            except:
                with util.safe_reraise():
                    self.rollback()

        self._state = PREPARED

    def commit(self):
        self._assert_active(prepared_ok=True)
        if self._state is not PREPARED:
            self._prepare_impl()

        if self._parent is None or self.nested:
            for t in set(self._connections.values()):
                t[1].commit()

            self._state = COMMITTED
            self.session.dispatch.after_commit(self.session)

            if self.session._enable_transaction_accounting:
                self._remove_snapshot()

        self.close()
        return self._parent

    def rollback(self, _capture_exception=False):
        self._assert_active(prepared_ok=True, rollback_ok=True)

        stx = self.session.transaction
        if stx is not self:
            for subtransaction in stx._iterate_parents(upto=self):
                subtransaction.close()

        if self._state in (ACTIVE, PREPARED):
            for transaction in self._iterate_parents():
                if transaction._parent is None or transaction.nested:
                    transaction._rollback_impl()
                    transaction._state = DEACTIVE
                    break
                else:
                    transaction._state = DEACTIVE

        sess = self.session

        if self.session._enable_transaction_accounting and \
                not sess._is_clean():
            # if items were added, deleted, or mutated
            # here, we need to re-restore the snapshot
            util.warn(
                    "Session's state has been changed on "
                    "a non-active transaction - this state "
                    "will be discarded.")
            self._restore_snapshot(dirty_only=self.nested)

        self.close()
        if self._parent and _capture_exception:
            self._parent._rollback_exception = sys.exc_info()[1]

        sess.dispatch.after_soft_rollback(sess, self)

        return self._parent

    def _rollback_impl(self):
        for t in set(self._connections.values()):
            t[1].rollback()

        if self.session._enable_transaction_accounting:
            self._restore_snapshot(dirty_only=self.nested)

        self.session.dispatch.after_rollback(self.session)

    def close(self):
        self.session.transaction = self._parent
        if self._parent is None:
            for connection, transaction, autoclose in \
                    set(self._connections.values()):
                if autoclose:
                    connection.close()
                else:
                    transaction.close()

        self._state = CLOSED
        if self.session.dispatch.after_transaction_end:
            self.session.dispatch.after_transaction_end(self.session, self)

        if self._parent is None:
            if not self.session.autocommit:
                self.session.begin()
        self.session = None
        self._connections = None

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self._assert_active(deactive_ok=True, prepared_ok=True)
        if self.session.transaction is None:
            return
        if type is None:
            try:
                self.commit()
            except:
                with util.safe_reraise():
                    self.rollback()
        else:
            self.rollback()


class Session(_SessionClassMethods):
    """Manages persistence operations for ORM-mapped objects.

    The Session's usage paradigm is described at :doc:`/orm/session`.


    """

    public_methods = (
        '__contains__', '__iter__', 'add', 'add_all', 'begin', 'begin_nested',
        'close', 'commit', 'connection', 'delete', 'execute', 'expire',
        'expire_all', 'expunge', 'expunge_all', 'flush', 'get_bind',
        'is_modified',
        'merge', 'query', 'refresh', 'rollback',
        'scalar')

    def __init__(self, bind=None, autoflush=True, expire_on_commit=True,
                _enable_transaction_accounting=True,
                 autocommit=False, twophase=False,
                 weak_identity_map=True, binds=None, extension=None,
                 query_cls=query.Query):
        """Construct a new Session.

        See also the :class:`.sessionmaker` function which is used to
        generate a :class:`.Session`-producing callable with a given
        set of arguments.

        :param autocommit:

          .. warning::

             The autocommit flag is **not for general use**, and if it is used,
             queries should only be invoked within the span of a
             :meth:`.Session.begin` / :meth:`.Session.commit` pair.   Executing
             queries outside of a demarcated transaction is a legacy mode
             of usage, and can in some cases lead to concurrent connection
             checkouts.

          Defaults to ``False``. When ``True``, the
          :class:`.Session` does not keep a persistent transaction running, and
          will acquire connections from the engine on an as-needed basis,
          returning them immediately after their use. Flushes will begin and
          commit (or possibly rollback) their own transaction if no
          transaction is present. When using this mode, the
          :meth:`.Session.begin` method is used to explicitly start
          transactions.

          .. seealso::

            :ref:`session_autocommit`

        :param autoflush: When ``True``, all query operations will issue a
           ``flush()`` call to this ``Session`` before proceeding. This is a
           convenience feature so that ``flush()`` need not be called
           repeatedly in order for database queries to retrieve results. It's
           typical that ``autoflush`` is used in conjunction with
           ``autocommit=False``. In this scenario, explicit calls to
           ``flush()`` are rarely needed; you usually only need to call
           ``commit()`` (which flushes) to finalize changes.

        :param bind: An optional ``Engine`` or ``Connection`` to which this
           ``Session`` should be bound. When specified, all SQL operations
           performed by this session will execute via this connectable.

        :param binds: An optional dictionary which contains more granular
           "bind" information than the ``bind`` parameter provides. This
           dictionary can map individual ``Table`` instances as well as
           ``Mapper`` instances to individual ``Engine`` or ``Connection``
           objects. Operations which proceed relative to a particular
           ``Mapper`` will consult this dictionary for the direct ``Mapper``
           instance as well as the mapper's ``mapped_table`` attribute in
           order to locate an connectable to use. The full resolution is
           described in the ``get_bind()`` method of ``Session``.
           Usage looks like::

            Session = sessionmaker(binds={
                SomeMappedClass: create_engine('postgresql://engine1'),
                somemapper: create_engine('postgresql://engine2'),
                some_table: create_engine('postgresql://engine3'),
                })

          Also see the :meth:`.Session.bind_mapper`
          and :meth:`.Session.bind_table` methods.

        :param \class_: Specify an alternate class other than
           ``sqlalchemy.orm.session.Session`` which should be used by the
           returned class. This is the only argument that is local to the
           ``sessionmaker()`` function, and is not sent directly to the
           constructor for ``Session``.

        :param _enable_transaction_accounting:  Defaults to ``True``.  A
           legacy-only flag which when ``False`` disables *all* 0.5-style
           object accounting on transaction boundaries, including auto-expiry
           of instances on rollback and commit, maintenance of the "new" and
           "deleted" lists upon rollback, and autoflush of pending changes upon
           begin(), all of which are interdependent.

        :param expire_on_commit:  Defaults to ``True``. When ``True``, all
           instances will be fully expired after each ``commit()``, so that
           all attribute/object access subsequent to a completed transaction
           will load from the most recent database state.

        :param extension: An optional
           :class:`~.SessionExtension` instance, or a list
           of such instances, which will receive pre- and post- commit and
           flush events, as well as a post-rollback event. **Deprecated.**
           Please see :class:`.SessionEvents`.

        :param query_cls:  Class which should be used to create new Query
           objects, as returned by the ``query()`` method. Defaults to
           :class:`~sqlalchemy.orm.query.Query`.

        :param twophase:  When ``True``, all transactions will be started as
            a "two phase" transaction, i.e. using the "two phase" semantics
            of the database in use along with an XID.  During a ``commit()``,
            after ``flush()`` has been issued for all attached databases, the
            ``prepare()`` method on each database's ``TwoPhaseTransaction``
            will be called. This allows each database to roll back the entire
            transaction, before each transaction is committed.

        :param weak_identity_map:  Defaults to ``True`` - when set to
           ``False``, objects placed in the :class:`.Session` will be
           strongly referenced until explicitly removed or the
           :class:`.Session` is closed.  **Deprecated** - this option
           is obsolete.

        """

        if weak_identity_map:
            self._identity_cls = identity.WeakInstanceDict
        else:
            util.warn_deprecated("weak_identity_map=False is deprecated.  "
                                    "This feature is not needed.")
            self._identity_cls = identity.StrongInstanceDict
        self.identity_map = self._identity_cls()

        self._new = {}   # InstanceState->object, strong refs object
        self._deleted = {}  # same
        self.bind = bind
        self.__binds = {}
        self._flushing = False
        self._warn_on_events = False
        self.transaction = None
        self.hash_key = _new_sessionid()
        self.autoflush = autoflush
        self.autocommit = autocommit
        self.expire_on_commit = expire_on_commit
        self._enable_transaction_accounting = _enable_transaction_accounting
        self.twophase = twophase
        self._query_cls = query_cls

        if extension:
            for ext in util.to_list(extension):
                SessionExtension._adapt_listener(self, ext)

        if binds is not None:
            for mapperortable, bind in binds.iteritems():
                if isinstance(mapperortable, (type, Mapper)):
                    self.bind_mapper(mapperortable, bind)
                else:
                    self.bind_table(mapperortable, bind)

        if not self.autocommit:
            self.begin()
        _sessions[self.hash_key] = self

    dispatch = event.dispatcher(SessionEvents)

    connection_callable = None

    transaction = None
    """The current active or inactive :class:`.SessionTransaction`."""

    def begin(self, subtransactions=False, nested=False):
        """Begin a transaction on this Session.

        If this Session is already within a transaction, either a plain
        transaction or nested transaction, an error is raised, unless
        ``subtransactions=True`` or ``nested=True`` is specified.

        The ``subtransactions=True`` flag indicates that this
        :meth:`~.Session.begin` can create a subtransaction if a transaction
        is already in progress. For documentation on subtransactions, please
        see :ref:`session_subtransactions`.

        The ``nested`` flag begins a SAVEPOINT transaction and is equivalent
        to calling :meth:`~.Session.begin_nested`. For documentation on
        SAVEPOINT transactions, please see :ref:`session_begin_nested`.

        """
        if self.transaction is not None:
            if subtransactions or nested:
                self.transaction = self.transaction._begin(
                                        nested=nested)
            else:
                raise sa_exc.InvalidRequestError(
                    "A transaction is already begun.  Use "
                    "subtransactions=True to allow subtransactions.")
        else:
            self.transaction = SessionTransaction(
                self, nested=nested)
        return self.transaction  # needed for __enter__/__exit__ hook

    def begin_nested(self):
        """Begin a `nested` transaction on this Session.

        The target database(s) must support SQL SAVEPOINTs or a
        SQLAlchemy-supported vendor implementation of the idea.

        For documentation on SAVEPOINT
        transactions, please see :ref:`session_begin_nested`.

        """
        return self.begin(nested=True)

    def rollback(self):
        """Rollback the current transaction in progress.

        If no transaction is in progress, this method is a pass-through.

        This method rolls back the current transaction or nested transaction
        regardless of subtransactions being in effect.  All subtransactions up
        to the first real transaction are closed.  Subtransactions occur when
        begin() is called multiple times.

        .. seealso::

            :ref:`session_rollback`

        """
        if self.transaction is None:
            pass
        else:
            self.transaction.rollback()

    def commit(self):
        """Flush pending changes and commit the current transaction.

        If no transaction is in progress, this method raises an
        :exc:`~sqlalchemy.exc.InvalidRequestError`.

        By default, the :class:`.Session` also expires all database
        loaded state on all ORM-managed attributes after transaction commit.
        This so that subsequent operations load the most recent
        data from the database.   This behavior can be disabled using
        the ``expire_on_commit=False`` option to :class:`.sessionmaker` or
        the :class:`.Session` constructor.

        If a subtransaction is in effect (which occurs when begin() is called
        multiple times), the subtransaction will be closed, and the next call
        to ``commit()`` will operate on the enclosing transaction.

        When using the :class:`.Session` in its default mode of
        ``autocommit=False``, a new transaction will
        be begun immediately after the commit, but note that the newly begun
        transaction does *not* use any connection resources until the first
        SQL is actually emitted.

        .. seealso::

            :ref:`session_committing`

        """
        if self.transaction is None:
            if not self.autocommit:
                self.begin()
            else:
                raise sa_exc.InvalidRequestError("No transaction is begun.")

        self.transaction.commit()

    def prepare(self):
        """Prepare the current transaction in progress for two phase commit.

        If no transaction is in progress, this method raises an
        :exc:`~sqlalchemy.exc.InvalidRequestError`.

        Only root transactions of two phase sessions can be prepared. If the
        current transaction is not such, an
        :exc:`~sqlalchemy.exc.InvalidRequestError` is raised.

        """
        if self.transaction is None:
            if not self.autocommit:
                self.begin()
            else:
                raise sa_exc.InvalidRequestError("No transaction is begun.")

        self.transaction.prepare()

    def connection(self, mapper=None, clause=None,
                        bind=None,
                        close_with_result=False,
                        **kw):
        """Return a :class:`.Connection` object corresponding to this
        :class:`.Session` object's transactional state.

        If this :class:`.Session` is configured with ``autocommit=False``,
        either the :class:`.Connection` corresponding to the current
        transaction is returned, or if no transaction is in progress, a new
        one is begun and the :class:`.Connection` returned (note that no
        transactional state is established with the DBAPI until the first
        SQL statement is emitted).

        Alternatively, if this :class:`.Session` is configured with
        ``autocommit=True``, an ad-hoc :class:`.Connection` is returned
        using :meth:`.Engine.contextual_connect` on the underlying
        :class:`.Engine`.

        Ambiguity in multi-bind or unbound :class:`.Session` objects can be
        resolved through any of the optional keyword arguments.   This
        ultimately makes usage of the :meth:`.get_bind` method for resolution.

        :param bind:
          Optional :class:`.Engine` to be used as the bind.  If
          this engine is already involved in an ongoing transaction,
          that connection will be used.  This argument takes precedence
          over ``mapper``, ``clause``.

        :param mapper:
          Optional :func:`.mapper` mapped class, used to identify
          the appropriate bind.  This argument takes precedence over
          ``clause``.

        :param clause:
            A :class:`.ClauseElement` (i.e. :func:`~.sql.expression.select`,
            :func:`~.sql.expression.text`,
            etc.) which will be used to locate a bind, if a bind
            cannot otherwise be identified.

        :param close_with_result: Passed to :meth:`Engine.connect`, indicating
          the :class:`.Connection` should be considered "single use",
          automatically closing when the first result set is closed.  This
          flag only has an effect if this :class:`.Session` is configured with
          ``autocommit=True`` and does not already have a  transaction
          in progress.

        :param \**kw:
          Additional keyword arguments are sent to :meth:`get_bind()`,
          allowing additional arguments to be passed to custom
          implementations of :meth:`get_bind`.

        """
        if bind is None:
            bind = self.get_bind(mapper, clause=clause, **kw)

        return self._connection_for_bind(bind,
                                        close_with_result=close_with_result)

    def _connection_for_bind(self, engine, **kwargs):
        if self.transaction is not None:
            return self.transaction._connection_for_bind(engine)
        else:
            return engine.contextual_connect(**kwargs)

    def execute(self, clause, params=None, mapper=None, bind=None, **kw):
        """Execute a SQL expression construct or string statement within
        the current transaction.

        Returns a :class:`.ResultProxy` representing
        results of the statement execution, in the same manner as that of an
        :class:`.Engine` or
        :class:`.Connection`.

        E.g.::

            result = session.execute(
                        user_table.select().where(user_table.c.id == 5)
                    )

        :meth:`~.Session.execute` accepts any executable clause construct, such
        as :func:`~.sql.expression.select`,
        :func:`~.sql.expression.insert`,
        :func:`~.sql.expression.update`,
        :func:`~.sql.expression.delete`, and
        :func:`~.sql.expression.text`.  Plain SQL strings can be passed
        as well, which in the case of :meth:`.Session.execute` only
        will be interpreted the same as if it were passed via a
        :func:`~.expression.text` construct.  That is, the following usage::

            result = session.execute(
                        "SELECT * FROM user WHERE id=:param",
                        {"param":5}
                    )

        is equivalent to::

            from sqlalchemy import text
            result = session.execute(
                        text("SELECT * FROM user WHERE id=:param"),
                        {"param":5}
                    )

        The second positional argument to :meth:`.Session.execute` is an
        optional parameter set.  Similar to that of
        :meth:`.Connection.execute`, whether this is passed as a single
        dictionary, or a list of dictionaries, determines whether the DBAPI
        cursor's ``execute()`` or ``executemany()`` is used to execute the
        statement.   An INSERT construct may be invoked for a single row::

            result = session.execute(users.insert(), {"id": 7, "name": "somename"})

        or for multiple rows::

            result = session.execute(users.insert(), [
                                    {"id": 7, "name": "somename7"},
                                    {"id": 8, "name": "somename8"},
                                    {"id": 9, "name": "somename9"}
                                ])

        The statement is executed within the current transactional context of
        this :class:`.Session`.   The :class:`.Connection` which is used
        to execute the statement can also be acquired directly by
        calling the :meth:`.Session.connection` method.  Both methods use
        a rule-based resolution scheme in order to determine the
        :class:`.Connection`, which in the average case is derived directly
        from the "bind" of the :class:`.Session` itself, and in other cases
        can be based on the :func:`.mapper`
        and :class:`.Table` objects passed to the method; see the documentation
        for :meth:`.Session.get_bind` for a full description of this scheme.

        The :meth:`.Session.execute` method does *not* invoke autoflush.

        The :class:`.ResultProxy` returned by the :meth:`.Session.execute`
        method is returned with the "close_with_result" flag set to true;
        the significance of this flag is that if this :class:`.Session` is
        autocommitting and does not have a transaction-dedicated
        :class:`.Connection` available, a temporary :class:`.Connection` is
        established for the statement execution, which is closed (meaning,
        returned to the connection pool) when the :class:`.ResultProxy` has
        consumed all available data. This applies *only* when the
        :class:`.Session` is configured with autocommit=True and no
        transaction has been started.

        :param clause:
            An executable statement (i.e. an :class:`.Executable` expression
            such as :func:`.expression.select`) or string SQL statement
            to be executed.

        :param params:
            Optional dictionary, or list of dictionaries, containing
            bound parameter values.   If a single dictionary, single-row
            execution occurs; if a list of dictionaries, an
            "executemany" will be invoked.  The keys in each dictionary
            must correspond to parameter names present in the statement.

        :param mapper:
          Optional :func:`.mapper` or mapped class, used to identify
          the appropriate bind.  This argument takes precedence over
          ``clause`` when locating a bind.   See :meth:`.Session.get_bind`
          for more details.

        :param bind:
          Optional :class:`.Engine` to be used as the bind.  If
          this engine is already involved in an ongoing transaction,
          that connection will be used.  This argument takes
          precedence over ``mapper`` and ``clause`` when locating
          a bind.

        :param \**kw:
          Additional keyword arguments are sent to :meth:`.Session.get_bind()`
          to allow extensibility of "bind" schemes.

        .. seealso::

            :ref:`sqlexpression_toplevel` - Tutorial on using Core SQL
            constructs.

            :ref:`connections_toplevel` - Further information on direct
            statement execution.

            :meth:`.Connection.execute` - core level statement execution
            method, which is :meth:`.Session.execute` ultimately uses
            in order to execute the statement.

        """
        clause = expression._literal_as_text(clause)

        if bind is None:
            bind = self.get_bind(mapper, clause=clause, **kw)

        return self._connection_for_bind(bind, close_with_result=True).execute(
            clause, params or {})

    def scalar(self, clause, params=None, mapper=None, bind=None, **kw):
        """Like :meth:`~.Session.execute` but return a scalar result."""

        return self.execute(
            clause, params=params, mapper=mapper, bind=bind, **kw).scalar()

    def close(self):
        """Close this Session.

        This clears all items and ends any transaction in progress.

        If this session were created with ``autocommit=False``, a new
        transaction is immediately begun.  Note that this new transaction does
        not use any connection resources until they are first needed.

        """
        self.expunge_all()
        if self.transaction is not None:
            for transaction in self.transaction._iterate_parents():
                transaction.close()

    def expunge_all(self):
        """Remove all object instances from this ``Session``.

        This is equivalent to calling ``expunge(obj)`` on all objects in this
        ``Session``.

        """
        for state in self.identity_map.all_states() + list(self._new):
            state._detach()

        self.identity_map = self._identity_cls()
        self._new = {}
        self._deleted = {}

    # TODO: need much more test coverage for bind_mapper() and similar !
    # TODO: + crystalize + document resolution order
    #       vis. bind_mapper/bind_table

    def bind_mapper(self, mapper, bind):
        """Bind operations for a mapper to a Connectable.

        mapper
          A mapper instance or mapped class

        bind
          Any Connectable: a ``Engine`` or ``Connection``.

        All subsequent operations involving this mapper will use the given
        `bind`.

        """
        if isinstance(mapper, type):
            mapper = class_mapper(mapper)

        self.__binds[mapper.base_mapper] = bind
        for t in mapper._all_tables:
            self.__binds[t] = bind

    def bind_table(self, table, bind):
        """Bind operations on a Table to a Connectable.

        table
          A ``Table`` instance

        bind
          Any Connectable: a ``Engine`` or ``Connection``.

        All subsequent operations involving this ``Table`` will use the
        given `bind`.

        """
        self.__binds[table] = bind

    def get_bind(self, mapper=None, clause=None):
        """Return a "bind" to which this :class:`.Session` is bound.

        The "bind" is usually an instance of :class:`.Engine`,
        except in the case where the :class:`.Session` has been
        explicitly bound directly to a :class:`.Connection`.

        For a multiply-bound or unbound :class:`.Session`, the
        ``mapper`` or ``clause`` arguments are used to determine the
        appropriate bind to return.

        Note that the "mapper" argument is usually present
        when :meth:`.Session.get_bind` is called via an ORM
        operation such as a :meth:`.Session.query`, each
        individual INSERT/UPDATE/DELETE operation within a
        :meth:`.Session.flush`, call, etc.

        The order of resolution is:

        1. if mapper given and session.binds is present,
           locate a bind based on mapper.
        2. if clause given and session.binds is present,
           locate a bind based on :class:`.Table` objects
           found in the given clause present in session.binds.
        3. if session.bind is present, return that.
        4. if clause given, attempt to return a bind
           linked to the :class:`.MetaData` ultimately
           associated with the clause.
        5. if mapper given, attempt to return a bind
           linked to the :class:`.MetaData` ultimately
           associated with the :class:`.Table` or other
           selectable to which the mapper is mapped.
        6. No bind can be found, :exc:`~sqlalchemy.exc.UnboundExecutionError`
           is raised.

        :param mapper:
          Optional :func:`.mapper` mapped class or instance of
          :class:`.Mapper`.   The bind can be derived from a :class:`.Mapper`
          first by consulting the "binds" map associated with this
          :class:`.Session`, and secondly by consulting the :class:`.MetaData`
          associated with the :class:`.Table` to which the :class:`.Mapper`
          is mapped for a bind.

        :param clause:
            A :class:`.ClauseElement` (i.e. :func:`~.sql.expression.select`,
            :func:`~.sql.expression.text`,
            etc.).  If the ``mapper`` argument is not present or could not
            produce a bind, the given expression construct will be searched
            for a bound element, typically a :class:`.Table` associated with
            bound :class:`.MetaData`.

        """
        if mapper is clause is None:
            if self.bind:
                return self.bind
            else:
                raise sa_exc.UnboundExecutionError(
                    "This session is not bound to a single Engine or "
                    "Connection, and no context was provided to locate "
                    "a binding.")

        c_mapper = mapper is not None and _class_to_mapper(mapper) or None

        # manually bound?
        if self.__binds:
            if c_mapper:
                if c_mapper.base_mapper in self.__binds:
                    return self.__binds[c_mapper.base_mapper]
                elif c_mapper.mapped_table in self.__binds:
                    return self.__binds[c_mapper.mapped_table]
            if clause is not None:
                for t in sql_util.find_tables(clause, include_crud=True):
                    if t in self.__binds:
                        return self.__binds[t]

        if self.bind:
            return self.bind

        if isinstance(clause, sql.expression.ClauseElement) and clause.bind:
            return clause.bind

        if c_mapper and c_mapper.mapped_table.bind:
            return c_mapper.mapped_table.bind

        context = []
        if mapper is not None:
            context.append('mapper %s' % c_mapper)
        if clause is not None:
            context.append('SQL expression')

        raise sa_exc.UnboundExecutionError(
            "Could not locate a bind configured on %s or this Session" % (
            ', '.join(context)))

    def query(self, *entities, **kwargs):
        """Return a new ``Query`` object corresponding to this ``Session``."""

        return self._query_cls(entities, self, **kwargs)

    @property
    @util.contextmanager
    def no_autoflush(self):
        """Return a context manager that disables autoflush.

        e.g.::

            with session.no_autoflush:

                some_object = SomeClass()
                session.add(some_object)
                # won't autoflush
                some_object.related_thing = session.query(SomeRelated).first()

        Operations that proceed within the ``with:`` block
        will not be subject to flushes occurring upon query
        access.  This is useful when initializing a series
        of objects which involve existing database queries,
        where the uncompleted object should not yet be flushed.

        .. versionadded:: 0.7.6

        """
        autoflush = self.autoflush
        self.autoflush = False
        yield self
        self.autoflush = autoflush

    def _autoflush(self):
        if self.autoflush and not self._flushing:
            self.flush()

    def refresh(self, instance, attribute_names=None, lockmode=None):
        """Expire and refresh the attributes on the given instance.

        A query will be issued to the database and all attributes will be
        refreshed with their current database value.

        Lazy-loaded relational attributes will remain lazily loaded, so that
        the instance-wide refresh operation will be followed immediately by
        the lazy load of that attribute.

        Eagerly-loaded relational attributes will eagerly load within the
        single refresh operation.

        Note that a highly isolated transaction will return the same values as
        were previously read in that same transaction, regardless of changes
        in database state outside of that transaction - usage of
        :meth:`~Session.refresh` usually only makes sense if non-ORM SQL
        statement were emitted in the ongoing transaction, or if autocommit
        mode is turned on.

        :param attribute_names: optional.  An iterable collection of
          string attribute names indicating a subset of attributes to
          be refreshed.

        :param lockmode: Passed to the :class:`~sqlalchemy.orm.query.Query`
          as used by :meth:`~sqlalchemy.orm.query.Query.with_lockmode`.

        """
        try:
            state = attributes.instance_state(instance)
        except exc.NO_STATE:
            raise exc.UnmappedInstanceError(instance)

        self._expire_state(state, attribute_names)

        if loading.load_on_ident(
                self.query(object_mapper(instance)),
                state.key, refresh_state=state,
                lockmode=lockmode,
                only_load_props=attribute_names) is None:
            raise sa_exc.InvalidRequestError(
                "Could not refresh instance '%s'" %
                orm_util.instance_str(instance))

    def expire_all(self):
        """Expires all persistent instances within this Session.

        When any attributes on a persistent instance is next accessed,
        a query will be issued using the
        :class:`.Session` object's current transactional context in order to
        load all expired attributes for the given instance.   Note that
        a highly isolated transaction will return the same values as were
        previously read in that same transaction, regardless of changes
        in database state outside of that transaction.

        To expire individual objects and individual attributes
        on those objects, use :meth:`Session.expire`.

        The :class:`.Session` object's default behavior is to
        expire all state whenever the :meth:`Session.rollback`
        or :meth:`Session.commit` methods are called, so that new
        state can be loaded for the new transaction.   For this reason,
        calling :meth:`Session.expire_all` should not be needed when
        autocommit is ``False``, assuming the transaction is isolated.

        """
        for state in self.identity_map.all_states():
            state._expire(state.dict, self.identity_map._modified)

    def expire(self, instance, attribute_names=None):
        """Expire the attributes on an instance.

        Marks the attributes of an instance as out of date. When an expired
        attribute is next accessed, a query will be issued to the
        :class:`.Session` object's current transactional context in order to
        load all expired attributes for the given instance.   Note that
        a highly isolated transaction will return the same values as were
        previously read in that same transaction, regardless of changes
        in database state outside of that transaction.

        To expire all objects in the :class:`.Session` simultaneously,
        use :meth:`Session.expire_all`.

        The :class:`.Session` object's default behavior is to
        expire all state whenever the :meth:`Session.rollback`
        or :meth:`Session.commit` methods are called, so that new
        state can be loaded for the new transaction.   For this reason,
        calling :meth:`Session.expire` only makes sense for the specific
        case that a non-ORM SQL statement was emitted in the current
        transaction.

        :param instance: The instance to be refreshed.
        :param attribute_names: optional list of string attribute names
          indicating a subset of attributes to be expired.

        """
        try:
            state = attributes.instance_state(instance)
        except exc.NO_STATE:
            raise exc.UnmappedInstanceError(instance)
        self._expire_state(state, attribute_names)

    def _expire_state(self, state, attribute_names):
        self._validate_persistent(state)
        if attribute_names:
            state._expire_attributes(state.dict, attribute_names)
        else:
            # pre-fetch the full cascade since the expire is going to
            # remove associations
            cascaded = list(state.manager.mapper.cascade_iterator(
                                            'refresh-expire', state))
            self._conditional_expire(state)
            for o, m, st_, dct_ in cascaded:
                self._conditional_expire(st_)

    def _conditional_expire(self, state):
        """Expire a state if persistent, else expunge if pending"""

        if state.key:
            state._expire(state.dict, self.identity_map._modified)
        elif state in self._new:
            self._new.pop(state)
            state._detach()

    @util.deprecated("0.7", "The non-weak-referencing identity map "
                        "feature is no longer needed.")
    def prune(self):
        """Remove unreferenced instances cached in the identity map.

        Note that this method is only meaningful if "weak_identity_map" is set
        to False.  The default weak identity map is self-pruning.

        Removes any object in this Session's identity map that is not
        referenced in user code, modified, new or scheduled for deletion.
        Returns the number of objects pruned.

        """
        return self.identity_map.prune()

    def expunge(self, instance):
        """Remove the `instance` from this ``Session``.

        This will free all internal references to the instance.  Cascading
        will be applied according to the *expunge* cascade rule.

        """
        try:
            state = attributes.instance_state(instance)
        except exc.NO_STATE:
            raise exc.UnmappedInstanceError(instance)
        if state.session_id is not self.hash_key:
            raise sa_exc.InvalidRequestError(
                "Instance %s is not present in this Session" %
                orm_util.state_str(state))

        cascaded = list(state.manager.mapper.cascade_iterator(
                                    'expunge', state))
        self._expunge_state(state)
        for o, m, st_, dct_ in cascaded:
            self._expunge_state(st_)

    def _expunge_state(self, state):
        if state in self._new:
            self._new.pop(state)
            state._detach()
        elif self.identity_map.contains_state(state):
            self.identity_map.discard(state)
            self._deleted.pop(state, None)
            state._detach()
        elif self.transaction:
            self.transaction._deleted.pop(state, None)

    def _register_newly_persistent(self, states):
        for state in states:
            mapper = _state_mapper(state)

            # prevent against last minute dereferences of the object
            obj = state.obj()
            if obj is not None:

                instance_key = mapper._identity_key_from_state(state)

                if _none_set.issubset(instance_key[1]) and \
                    not mapper.allow_partial_pks or \
                    _none_set.issuperset(instance_key[1]):
                    raise exc.FlushError(
                        "Instance %s has a NULL identity key.  If this is an "
                        "auto-generated value, check that the database table "
                        "allows generation of new primary key values, and "
                        "that the mapped Column object is configured to "
                        "expect these generated values.  Ensure also that "
                        "this flush() is not occurring at an inappropriate "
                        "time, such aswithin a load() event."
                        % orm_util.state_str(state)
                    )

                if state.key is None:
                    state.key = instance_key
                elif state.key != instance_key:
                    # primary key switch. use discard() in case another
                    # state has already replaced this one in the identity
                    # map (see test/orm/test_naturalpks.py ReversePKsTest)
                    self.identity_map.discard(state)
                    if state in self.transaction._key_switches:
                        orig_key = self.transaction._key_switches[state][0]
                    else:
                        orig_key = state.key
                    self.transaction._key_switches[state] = (
                        orig_key, instance_key)
                    state.key = instance_key

                self.identity_map.replace(state)

        statelib.InstanceState._commit_all_states(
            ((state, state.dict) for state in states),
            self.identity_map
        )

        self._register_altered(states)
        # remove from new last, might be the last strong ref
        for state in set(states).intersection(self._new):
            self._new.pop(state)

    def _register_altered(self, states):
        if self._enable_transaction_accounting and self.transaction:
            for state in states:
                if state in self._new:
                    self.transaction._new[state] = True
                else:
                    self.transaction._dirty[state] = True

    def _remove_newly_deleted(self, states):
        for state in states:
            if self._enable_transaction_accounting and self.transaction:
                self.transaction._deleted[state] = True

            self.identity_map.discard(state)
            self._deleted.pop(state, None)
            state.deleted = True

    def add(self, instance, _warn=True):
        """Place an object in the ``Session``.

        Its state will be persisted to the database on the next flush
        operation.

        Repeated calls to ``add()`` will be ignored. The opposite of ``add()``
        is ``expunge()``.

        """
        if _warn and self._warn_on_events:
            self._flush_warning("Session.add()")

        try:
            state = attributes.instance_state(instance)
        except exc.NO_STATE:
            raise exc.UnmappedInstanceError(instance)

        self._save_or_update_state(state)

    def add_all(self, instances):
        """Add the given collection of instances to this ``Session``."""

        if self._warn_on_events:
            self._flush_warning("Session.add_all()")

        for instance in instances:
            self.add(instance, _warn=False)

    def _save_or_update_state(self, state):
        self._save_or_update_impl(state)

        mapper = _state_mapper(state)
        for o, m, st_, dct_ in mapper.cascade_iterator(
                                    'save-update',
                                    state,
                                    halt_on=self._contains_state):
            self._save_or_update_impl(st_)

    def delete(self, instance):
        """Mark an instance as deleted.

        The database delete operation occurs upon ``flush()``.

        """
        if self._warn_on_events:
            self._flush_warning("Session.delete()")

        try:
            state = attributes.instance_state(instance)
        except exc.NO_STATE:
            raise exc.UnmappedInstanceError(instance)

        if state.key is None:
            raise sa_exc.InvalidRequestError(
                "Instance '%s' is not persisted" %
                orm_util.state_str(state))

        if state in self._deleted:
            return

        # ensure object is attached to allow the
        # cascade operation to load deferred attributes
        # and collections
        self._attach(state, include_before=True)

        # grab the cascades before adding the item to the deleted list
        # so that autoflush does not delete the item
        # the strong reference to the instance itself is significant here
        cascade_states = list(state.manager.mapper.cascade_iterator(
                                            'delete', state))

        self._deleted[state] = state.obj()
        self.identity_map.add(state)

        for o, m, st_, dct_ in cascade_states:
            self._delete_impl(st_)

    def merge(self, instance, load=True):
        """Copy the state of a given instance into a corresponding instance
        within this :class:`.Session`.

        :meth:`.Session.merge` examines the primary key attributes of the
        source instance, and attempts to reconcile it with an instance of the
        same primary key in the session.   If not found locally, it attempts
        to load the object from the database based on primary key, and if
        none can be located, creates a new instance.  The state of each
        attribute on the source instance is then copied to the target instance.
        The resulting target instance is then returned by the method; the
        original source instance is left unmodified, and un-associated with the
        :class:`.Session` if not already.

        This operation cascades to associated instances if the association is
        mapped with ``cascade="merge"``.

        See :ref:`unitofwork_merging` for a detailed discussion of merging.

        :param instance: Instance to be merged.
        :param load: Boolean, when False, :meth:`.merge` switches into
         a "high performance" mode which causes it to forego emitting history
         events as well as all database access.  This flag is used for
         cases such as transferring graphs of objects into a :class:`.Session`
         from a second level cache, or to transfer just-loaded objects
         into the :class:`.Session` owned by a worker thread or process
         without re-querying the database.

         The ``load=False`` use case adds the caveat that the given
         object has to be in a "clean" state, that is, has no pending changes
         to be flushed - even if the incoming object is detached from any
         :class:`.Session`.   This is so that when
         the merge operation populates local attributes and
         cascades to related objects and
         collections, the values can be "stamped" onto the
         target object as is, without generating any history or attribute
         events, and without the need to reconcile the incoming data with
         any existing related objects or collections that might not
         be loaded.  The resulting objects from ``load=False`` are always
         produced as "clean", so it is only appropriate that the given objects
         should be "clean" as well, else this suggests a mis-use of the method.

        """

        if self._warn_on_events:
            self._flush_warning("Session.merge()")

        _recursive = {}

        if load:
            # flush current contents if we expect to load data
            self._autoflush()

        object_mapper(instance)  # verify mapped
        autoflush = self.autoflush
        try:
            self.autoflush = False
            return self._merge(
                            attributes.instance_state(instance),
                            attributes.instance_dict(instance),
                            load=load, _recursive=_recursive)
        finally:
            self.autoflush = autoflush

    def _merge(self, state, state_dict, load=True, _recursive=None):
        mapper = _state_mapper(state)
        if state in _recursive:
            return _recursive[state]

        new_instance = False
        key = state.key

        if key is None:
            if not load:
                raise sa_exc.InvalidRequestError(
                    "merge() with load=False option does not support "
                    "objects transient (i.e. unpersisted) objects.  flush() "
                    "all changes on mapped instances before merging with "
                    "load=False.")
            key = mapper._identity_key_from_state(state)

        if key in self.identity_map:
            merged = self.identity_map[key]

        elif not load:
            if state.modified:
                raise sa_exc.InvalidRequestError(
                    "merge() with load=False option does not support "
                    "objects marked as 'dirty'.  flush() all changes on "
                    "mapped instances before merging with load=False.")
            merged = mapper.class_manager.new_instance()
            merged_state = attributes.instance_state(merged)
            merged_state.key = key
            self._update_impl(merged_state)
            new_instance = True

        elif not _none_set.issubset(key[1]) or \
                    (mapper.allow_partial_pks and
                    not _none_set.issuperset(key[1])):
            merged = self.query(mapper.class_).get(key[1])
        else:
            merged = None

        if merged is None:
            merged = mapper.class_manager.new_instance()
            merged_state = attributes.instance_state(merged)
            merged_dict = attributes.instance_dict(merged)
            new_instance = True
            self._save_or_update_state(merged_state)
        else:
            merged_state = attributes.instance_state(merged)
            merged_dict = attributes.instance_dict(merged)

        _recursive[state] = merged

        # check that we didn't just pull the exact same
        # state out.
        if state is not merged_state:
            # version check if applicable
            if mapper.version_id_col is not None:
                existing_version = mapper._get_state_attr_by_column(
                            state,
                            state_dict,
                            mapper.version_id_col,
                            passive=attributes.PASSIVE_NO_INITIALIZE)

                merged_version = mapper._get_state_attr_by_column(
                            merged_state,
                            merged_dict,
                            mapper.version_id_col,
                            passive=attributes.PASSIVE_NO_INITIALIZE)

                if existing_version is not attributes.PASSIVE_NO_RESULT and \
                    merged_version is not attributes.PASSIVE_NO_RESULT and \
                    existing_version != merged_version:
                    raise exc.StaleDataError(
                            "Version id '%s' on merged state %s "
                            "does not match existing version '%s'. "
                            "Leave the version attribute unset when "
                            "merging to update the most recent version."
                            % (
                                existing_version,
                                orm_util.state_str(merged_state),
                                merged_version
                            ))

            merged_state.load_path = state.load_path
            merged_state.load_options = state.load_options

            for prop in mapper.iterate_properties:
                prop.merge(self, state, state_dict,
                                merged_state, merged_dict,
                                load, _recursive)

        if not load:
            # remove any history
            merged_state._commit_all(merged_dict, self.identity_map)

        if new_instance:
            merged_state.manager.dispatch.load(merged_state, None)
        return merged

    def _validate_persistent(self, state):
        if not self.identity_map.contains_state(state):
            raise sa_exc.InvalidRequestError(
                "Instance '%s' is not persistent within this Session" %
                orm_util.state_str(state))

    def _save_impl(self, state):
        if state.key is not None:
            raise sa_exc.InvalidRequestError(
                "Object '%s' already has an identity - it can't be registered "
                "as pending" % orm_util.state_str(state))

        self._before_attach(state)
        if state not in self._new:
            self._new[state] = state.obj()
            state.insert_order = len(self._new)
        self._attach(state)

    def _update_impl(self, state, discard_existing=False):
        if (self.identity_map.contains_state(state) and
            state not in self._deleted):
            return

        if state.key is None:
            raise sa_exc.InvalidRequestError(
                "Instance '%s' is not persisted" %
                orm_util.state_str(state))

        if state.deleted:
            raise sa_exc.InvalidRequestError(
                "Instance '%s' has been deleted.  Use the make_transient() "
                "function to send this object back to the transient state." %
                orm_util.state_str(state)
            )
        self._before_attach(state)
        self._deleted.pop(state, None)
        if discard_existing:
            self.identity_map.replace(state)
        else:
            self.identity_map.add(state)
        self._attach(state)

    def _save_or_update_impl(self, state):
        if state.key is None:
            self._save_impl(state)
        else:
            self._update_impl(state)

    def _delete_impl(self, state):
        if state in self._deleted:
            return

        if state.key is None:
            return

        self._attach(state, include_before=True)
        self._deleted[state] = state.obj()
        self.identity_map.add(state)

    def enable_relationship_loading(self, obj):
        """Associate an object with this :class:`.Session` for related
        object loading.

        .. warning::

            :meth:`.enable_relationship_loading` exists to serve special
            use cases and is not recommended for general use.

        Accesses of attributes mapped with :func:`.relationship`
        will attempt to load a value from the database using this
        :class:`.Session` as the source of connectivity.  The values
        will be loaded based on foreign key values present on this
        object - it follows that this functionality
        generally only works for many-to-one-relationships.

        The object will be attached to this session, but will
        **not** participate in any persistence operations; its state
        for almost all purposes will remain either "transient" or
        "detached", except for the case of relationship loading.

        Also note that backrefs will often not work as expected.
        Altering a relationship-bound attribute on the target object
        may not fire off a backref event, if the effective value
        is what was already loaded from a foreign-key-holding value.

        The :meth:`.Session.enable_relationship_loading` method supersedes
        the ``load_on_pending`` flag on :func:`.relationship`.   Unlike
        that flag, :meth:`.Session.enable_relationship_loading` allows
        an object to remain transient while still being able to load
        related items.

        To make a transient object associated with a :class:`.Session`
        via :meth:`.Session.enable_relationship_loading` pending, add
        it to the :class:`.Session` using :meth:`.Session.add` normally.

        :meth:`.Session.enable_relationship_loading` does not improve
        behavior when the ORM is used normally - object references should be
        constructed at the object level, not at the foreign key level, so
        that they are present in an ordinary way before flush()
        proceeds.  This method is not intended for general use.

        .. versionadded:: 0.8

        """
        state = attributes.instance_state(obj)
        self._attach(state, include_before=True)
        state._load_pending = True

    def _before_attach(self, state):
        if state.session_id != self.hash_key and \
                self.dispatch.before_attach:
            self.dispatch.before_attach(self, state.obj())

    def _attach(self, state, include_before=False):
        if state.key and \
            state.key in self.identity_map and \
                not self.identity_map.contains_state(state):
            raise sa_exc.InvalidRequestError("Can't attach instance "
                    "%s; another instance with key %s is already "
                    "present in this session."
                    % (orm_util.state_str(state), state.key))

        if state.session_id and \
                state.session_id is not self.hash_key and \
                state.session_id in _sessions:
            raise sa_exc.InvalidRequestError(
                "Object '%s' is already attached to session '%s' "
                "(this is '%s')" % (orm_util.state_str(state),
                                    state.session_id, self.hash_key))

        if state.session_id != self.hash_key:
            if include_before and \
                    self.dispatch.before_attach:
                self.dispatch.before_attach(self, state.obj())
            state.session_id = self.hash_key
            if state.modified and state._strong_obj is None:
                state._strong_obj = state.obj()
            if self.dispatch.after_attach:
                self.dispatch.after_attach(self, state.obj())

    def __contains__(self, instance):
        """Return True if the instance is associated with this session.

        The instance may be pending or persistent within the Session for a
        result of True.

        """
        try:
            state = attributes.instance_state(instance)
        except exc.NO_STATE:
            raise exc.UnmappedInstanceError(instance)
        return self._contains_state(state)

    def __iter__(self):
        """Iterate over all pending or persistent instances within this
        Session.

        """
        return iter(list(self._new.values()) + self.identity_map.values())

    def _contains_state(self, state):
        return state in self._new or self.identity_map.contains_state(state)

    def flush(self, objects=None):
        """Flush all the object changes to the database.

        Writes out all pending object creations, deletions and modifications
        to the database as INSERTs, DELETEs, UPDATEs, etc.  Operations are
        automatically ordered by the Session's unit of work dependency
        solver.

        Database operations will be issued in the current transactional
        context and do not affect the state of the transaction, unless an
        error occurs, in which case the entire transaction is rolled back.
        You may flush() as often as you like within a transaction to move
        changes from Python to the database's transaction buffer.

        For ``autocommit`` Sessions with no active manual transaction, flush()
        will create a transaction on the fly that surrounds the entire set of
        operations int the flush.

        :param objects: Optional; restricts the flush operation to operate
          only on elements that are in the given collection.

          This feature is for an extremely narrow set of use cases where
          particular objects may need to be operated upon before the
          full flush() occurs.  It is not intended for general use.

        """

        if self._flushing:
            raise sa_exc.InvalidRequestError("Session is already flushing")

        if self._is_clean():
            return
        try:
            self._flushing = True
            self._flush(objects)
        finally:
            self._flushing = False

    def _flush_warning(self, method):
        util.warn(
            "Usage of the '%s' operation is not currently supported "
            "within the execution stage of the flush process. "
            "Results may not be consistent.  Consider using alternative "
            "event listeners or connection-level operations instead."
            % method)

    def _is_clean(self):
        return not self.identity_map.check_modified() and \
                not self._deleted and \
                not self._new

    def _flush(self, objects=None):

        dirty = self._dirty_states
        if not dirty and not self._deleted and not self._new:
            self.identity_map._modified.clear()
            return

        flush_context = UOWTransaction(self)

        if self.dispatch.before_flush:
            self.dispatch.before_flush(self, flush_context, objects)
            # re-establish "dirty states" in case the listeners
            # added
            dirty = self._dirty_states

        deleted = set(self._deleted)
        new = set(self._new)

        dirty = set(dirty).difference(deleted)

        # create the set of all objects we want to operate upon
        if objects:
            # specific list passed in
            objset = set()
            for o in objects:
                try:
                    state = attributes.instance_state(o)
                except exc.NO_STATE:
                    raise exc.UnmappedInstanceError(o)
                objset.add(state)
        else:
            objset = None

        # store objects whose fate has been decided
        processed = set()

        # put all saves/updates into the flush context.  detect top-level
        # orphans and throw them into deleted.
        if objset:
            proc = new.union(dirty).intersection(objset).difference(deleted)
        else:
            proc = new.union(dirty).difference(deleted)

        for state in proc:
            is_orphan = (
                _state_mapper(state)._is_orphan(state) and state.has_identity)
            flush_context.register_object(state, isdelete=is_orphan)
            processed.add(state)

        # put all remaining deletes into the flush context.
        if objset:
            proc = deleted.intersection(objset).difference(processed)
        else:
            proc = deleted.difference(processed)
        for state in proc:
            flush_context.register_object(state, isdelete=True)

        if not flush_context.has_work:
            return

        flush_context.transaction = transaction = self.begin(
            subtransactions=True)
        try:
            self._warn_on_events = True
            try:
                flush_context.execute()
            finally:
                self._warn_on_events = False

            self.dispatch.after_flush(self, flush_context)

            flush_context.finalize_flush_changes()

            if not objects and self.identity_map._modified:
                len_ = len(self.identity_map._modified)

                statelib.InstanceState._commit_all_states(
                                [(state, state.dict) for state in
                                        self.identity_map._modified],
                                instance_dict=self.identity_map)
                util.warn("Attribute history events accumulated on %d "
                        "previously clean instances "
                        "within inner-flush event handlers have been reset, "
                        "and will not result in database updates. "
                        "Consider using set_committed_value() within "
                        "inner-flush event handlers to avoid this warning."
                                    % len_)

            # useful assertions:
            #if not objects:
            #    assert not self.identity_map._modified
            #else:
            #    assert self.identity_map._modified == \
            #            self.identity_map._modified.difference(objects)

            self.dispatch.after_flush_postexec(self, flush_context)

            transaction.commit()

        except:
            with util.safe_reraise():
                transaction.rollback(_capture_exception=True)

    def is_modified(self, instance, include_collections=True,
                            passive=True):
        """Return ``True`` if the given instance has locally
        modified attributes.

        This method retrieves the history for each instrumented
        attribute on the instance and performs a comparison of the current
        value to its previously committed value, if any.

        It is in effect a more expensive and accurate
        version of checking for the given instance in the
        :attr:`.Session.dirty` collection; a full test for
        each attribute's net "dirty" status is performed.

        E.g.::

            return session.is_modified(someobject)

        .. versionchanged:: 0.8
            When using SQLAlchemy 0.7 and earlier, the ``passive``
            flag should **always** be explicitly set to ``True``,
            else SQL loads/autoflushes may proceed which can affect
            the modified state itself:
            ``session.is_modified(someobject, passive=True)``\ .
            In 0.8 and above, the behavior is corrected and
            this flag is ignored.

        A few caveats to this method apply:

        * Instances present in the :attr:`.Session.dirty` collection may report
          ``False`` when tested with this method.  This is because
          the object may have received change events via attribute
          mutation, thus placing it in :attr:`.Session.dirty`,
          but ultimately the state is the same as that loaded from
          the database, resulting in no net change here.
        * Scalar attributes may not have recorded the previously set
          value when a new value was applied, if the attribute was not loaded,
          or was expired, at the time the new value was received - in these
          cases, the attribute is assumed to have a change, even if there is
          ultimately no net change against its database value. SQLAlchemy in
          most cases does not need the "old" value when a set event occurs, so
          it skips the expense of a SQL call if the old value isn't present,
          based on the assumption that an UPDATE of the scalar value is
          usually needed, and in those few cases where it isn't, is less
          expensive on average than issuing a defensive SELECT.

          The "old" value is fetched unconditionally upon set only if the
          attribute container has the ``active_history`` flag set to ``True``.
          This flag is set typically for primary key attributes and scalar
          object references that are not a simple many-to-one.  To set this
          flag for any arbitrary mapped column, use the ``active_history``
          argument with :func:`.column_property`.

        :param instance: mapped instance to be tested for pending changes.
        :param include_collections: Indicates if multivalued collections
         should be included in the operation.  Setting this to ``False`` is a
         way to detect only local-column based properties (i.e. scalar columns
         or many-to-one foreign keys) that would result in an UPDATE for this
         instance upon flush.
        :param passive:
         .. versionchanged:: 0.8
             Ignored for backwards compatibility.
             When using SQLAlchemy 0.7 and earlier, this flag should always
             be set to ``True``.

        """
        state = object_state(instance)

        if not state.modified:
            return False

        dict_ = state.dict

        for attr in state.manager.attributes:
            if \
                (
                    not include_collections and
                    hasattr(attr.impl, 'get_collection')
                ) or not hasattr(attr.impl, 'get_history'):
                continue

            (added, unchanged, deleted) = \
                    attr.impl.get_history(state, dict_,
                            passive=attributes.NO_CHANGE)

            if added or deleted:
                return True
        else:
            return False

    @property
    def is_active(self):
        """True if this :class:`.Session` is in "transaction mode" and
        is not in "partial rollback" state.

        The :class:`.Session` in its default mode of ``autocommit=False``
        is essentially always in "transaction mode", in that a
        :class:`.SessionTransaction` is associated with it as soon as
        it is instantiated.  This :class:`.SessionTransaction` is immediately
        replaced with a new one as soon as it is ended, due to a rollback,
        commit, or close operation.

        "Transaction mode" does *not* indicate whether
        or not actual database connection resources are in use;  the
        :class:`.SessionTransaction` object coordinates among zero or more
        actual database transactions, and starts out with none, accumulating
        individual DBAPI connections as different data sources are used
        within its scope.   The best way to track when a particular
        :class:`.Session` has actually begun to use DBAPI resources is to
        implement a listener using the :meth:`.SessionEvents.after_begin`
        method, which will deliver both the :class:`.Session` as well as the
        target :class:`.Connection` to a user-defined event listener.

        The "partial rollback" state refers to when an "inner" transaction,
        typically used during a flush, encounters an error and emits a
        rollback of the DBAPI connection.  At this point, the
        :class:`.Session` is in "partial rollback" and awaits for the user to
        call :meth:`.Session.rollback`, in order to close out the
        transaction stack.  It is in this "partial rollback" period that the
        :attr:`.is_active` flag returns False.  After the call to
        :meth:`.Session.rollback`, the :class:`.SessionTransaction` is replaced
        with a new one and :attr:`.is_active` returns ``True`` again.

        When a :class:`.Session` is used in ``autocommit=True`` mode, the
        :class:`.SessionTransaction` is only instantiated within the scope
        of a flush call, or when :meth:`.Session.begin` is called.  So
        :attr:`.is_active` will always be ``False`` outside of a flush or
        :meth:`.Session.begin` block in this mode, and will be ``True``
        within the :meth:`.Session.begin` block as long as it doesn't enter
        "partial rollback" state.

        From all the above, it follows that the only purpose to this flag is
        for application frameworks that wish to detect is a "rollback" is
        necessary within a generic error handling routine, for
        :class:`.Session` objects that would otherwise be in
        "partial rollback" mode.  In a typical integration case, this is also
        not necessary as it is standard practice to emit
        :meth:`.Session.rollback` unconditionally within the outermost
        exception catch.

        To track the transactional state of a :class:`.Session` fully,
        use event listeners, primarily the :meth:`.SessionEvents.after_begin`,
        :meth:`.SessionEvents.after_commit`,
        :meth:`.SessionEvents.after_rollback` and related events.

        """
        return self.transaction and self.transaction.is_active

    identity_map = None
    """A mapping of object identities to objects themselves.

    Iterating through ``Session.identity_map.values()`` provides
    access to the full set of persistent objects (i.e., those
    that have row identity) currently in the session.

    See also:

    :func:`.identity_key` - operations involving identity keys.

    """

    @property
    def _dirty_states(self):
        """The set of all persistent states considered dirty.

        This method returns all states that were modified including
        those that were possibly deleted.

        """
        return self.identity_map._dirty_states()

    @property
    def dirty(self):
        """The set of all persistent instances considered dirty.

        E.g.::

            some_mapped_object in session.dirty

        Instances are considered dirty when they were modified but not
        deleted.

        Note that this 'dirty' calculation is 'optimistic'; most
        attribute-setting or collection modification operations will
        mark an instance as 'dirty' and place it in this set, even if
        there is no net change to the attribute's value.  At flush
        time, the value of each attribute is compared to its
        previously saved value, and if there's no net change, no SQL
        operation will occur (this is a more expensive operation so
        it's only done at flush time).

        To check if an instance has actionable net changes to its
        attributes, use the :meth:`.Session.is_modified` method.

        """
        return util.IdentitySet(
            [state.obj()
             for state in self._dirty_states
             if state not in self._deleted])

    @property
    def deleted(self):
        "The set of all instances marked as 'deleted' within this ``Session``"

        return util.IdentitySet(self._deleted.values())

    @property
    def new(self):
        "The set of all instances marked as 'new' within this ``Session``."

        return util.IdentitySet(self._new.values())


class sessionmaker(_SessionClassMethods):
    """A configurable :class:`.Session` factory.

    The :class:`.sessionmaker` factory generates new
    :class:`.Session` objects when called, creating them given
    the configurational arguments established here.

    e.g.::

        # global scope
        Session = sessionmaker(autoflush=False)

        # later, in a local scope, create and use a session:
        sess = Session()

    Any keyword arguments sent to the constructor itself will override the
    "configured" keywords::

        Session = sessionmaker()

        # bind an individual session to a connection
        sess = Session(bind=connection)

    The class also includes a method :meth:`.configure`, which can
    be used to specify additional keyword arguments to the factory, which
    will take effect for subsequent :class:`.Session` objects generated.
    This is usually used to associate one or more :class:`.Engine` objects
    with an existing :class:`.sessionmaker` factory before it is first
    used::

        # application starts
        Session = sessionmaker()

        # ... later
        engine = create_engine('sqlite:///foo.db')
        Session.configure(bind=engine)

        sess = Session()

    .. seealso:

        :ref:`session_getting` - introductory text on creating
        sessions using :class:`.sessionmaker`.

    """

    def __init__(self, bind=None, class_=Session, autoflush=True,
                        autocommit=False,
                        expire_on_commit=True, **kw):
        """Construct a new :class:`.sessionmaker`.

        All arguments here except for ``class_`` correspond to arguments
        accepted by :class:`.Session` directly.  See the
        :meth:`.Session.__init__` docstring for more details on parameters.

        :param bind: a :class:`.Engine` or other :class:`.Connectable` with
         which newly created :class:`.Session` objects will be associated.
        :param class_: class to use in order to create new :class:`.Session`
         objects.  Defaults to :class:`.Session`.
        :param autoflush: The autoflush setting to use with newly created
         :class:`.Session` objects.
        :param autocommit: The autocommit setting to use with newly created
         :class:`.Session` objects.
        :param expire_on_commit=True: the expire_on_commit setting to use
         with newly created :class:`.Session` objects.
        :param \**kw: all other keyword arguments are passed to the constructor
         of newly created :class:`.Session` objects.

        """
        kw['bind'] = bind
        kw['autoflush'] = autoflush
        kw['autocommit'] = autocommit
        kw['expire_on_commit'] = expire_on_commit
        self.kw = kw
        # make our own subclass of the given class, so that
        # events can be associated with it specifically.
        self.class_ = type(class_.__name__, (class_,), {})

    def __call__(self, **local_kw):
        """Produce a new :class:`.Session` object using the configuration
        established in this :class:`.sessionmaker`.

        In Python, the ``__call__`` method is invoked on an object when
        it is "called" in the same way as a function::

            Session = sessionmaker()
            session = Session()  # invokes sessionmaker.__call__()

        """
        for k, v in self.kw.items():
            local_kw.setdefault(k, v)
        return self.class_(**local_kw)

    def configure(self, **new_kw):
        """(Re)configure the arguments for this sessionmaker.

        e.g.::

            Session = sessionmaker()

            Session.configure(bind=create_engine('sqlite://'))
        """
        self.kw.update(new_kw)

    def __repr__(self):
        return "%s(class_=%r%s)" % (
                    self.__class__.__name__,
                    self.class_.__name__,
                    ", ".join("%s=%r" % (k, v) for k, v in self.kw.items())
                )

_sessions = weakref.WeakValueDictionary()


def make_transient(instance):
    """Make the given instance 'transient'.

    This will remove its association with any
    session and additionally will remove its "identity key",
    such that it's as though the object were newly constructed,
    except retaining its values.   It also resets the
    "deleted" flag on the state if this object
    had been explicitly deleted by its session.

    Attributes which were "expired" or deferred at the
    instance level are reverted to undefined, and
    will not trigger any loads.

    """
    state = attributes.instance_state(instance)
    s = _state_session(state)
    if s:
        s._expunge_state(state)

    # remove expired state and
    # deferred callables
    state.callables.clear()
    if state.key:
        del state.key
    if state.deleted:
        del state.deleted


def object_session(instance):
    """Return the ``Session`` to which instance belongs.

    If the instance is not a mapped instance, an error is raised.

    """

    try:
        return _state_session(attributes.instance_state(instance))
    except exc.NO_STATE:
        raise exc.UnmappedInstanceError(instance)


def _state_session(state):
    if state.session_id:
        try:
            return _sessions[state.session_id]
        except KeyError:
            pass
    return None

_new_sessionid = util.counter()
