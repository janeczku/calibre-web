from __future__ import with_statement

import operator
from nose import SkipTest
from ..util import decorator
from . import config
from .. import util
import contextlib


class skip_if(object):
    def __init__(self, predicate, reason=None):
        self.predicate = _as_predicate(predicate)
        self.reason = reason

    _fails_on = None

    @property
    def enabled(self):
        return not self.predicate()

    @contextlib.contextmanager
    def fail_if(self, name='block'):
        try:
            yield
        except Exception, ex:
            if self.predicate():
                print ("%s failed as expected (%s): %s " % (
                    name, self.predicate, str(ex)))
            else:
                raise
        else:
            if self.predicate():
                raise AssertionError(
                    "Unexpected success for '%s' (%s)" %
                    (name, self.predicate))

    def __call__(self, fn):
        @decorator
        def decorate(fn, *args, **kw):
            if self.predicate():
                if self.reason:
                    msg = "'%s' : %s" % (
                            fn.__name__,
                            self.reason
                        )
                else:
                    msg = "'%s': %s" % (
                            fn.__name__, self.predicate
                        )
                raise SkipTest(msg)
            else:
                if self._fails_on:
                    with self._fails_on.fail_if(name=fn.__name__):
                        return fn(*args, **kw)
                else:
                    return fn(*args, **kw)
        return decorate(fn)

    def fails_on(self, other, reason=None):
        self._fails_on = skip_if(other, reason)
        return self


class fails_if(skip_if):
    def __call__(self, fn):
        @decorator
        def decorate(fn, *args, **kw):
            with self.fail_if(name=fn.__name__):
                return fn(*args, **kw)
        return decorate(fn)


def only_if(predicate, reason=None):
    predicate = _as_predicate(predicate)
    return skip_if(NotPredicate(predicate), reason)


def succeeds_if(predicate, reason=None):
    predicate = _as_predicate(predicate)
    return fails_if(NotPredicate(predicate), reason)


class Predicate(object):
    @classmethod
    def as_predicate(cls, predicate):
        if isinstance(predicate, skip_if):
            return predicate.predicate
        elif isinstance(predicate, Predicate):
            return predicate
        elif isinstance(predicate, list):
            return OrPredicate([cls.as_predicate(pred) for pred in predicate])
        elif isinstance(predicate, tuple):
            return SpecPredicate(*predicate)
        elif isinstance(predicate, basestring):
            return SpecPredicate(predicate, None, None)
        elif util.callable(predicate):
            return LambdaPredicate(predicate)
        else:
            assert False, "unknown predicate type: %s" % predicate


class BooleanPredicate(Predicate):
    def __init__(self, value, description=None):
        self.value = value
        self.description = description or "boolean %s" % value

    def __call__(self):
        return self.value

    def _as_string(self, negate=False):
        if negate:
            return "not " + self.description
        else:
            return self.description

    def __str__(self):
        return self._as_string()


class SpecPredicate(Predicate):
    def __init__(self, db, op=None, spec=None, description=None):
        self.db = db
        self.op = op
        self.spec = spec
        self.description = description

    _ops = {
            '<': operator.lt,
             '>': operator.gt,
             '==': operator.eq,
             '!=': operator.ne,
             '<=': operator.le,
             '>=': operator.ge,
             'in': operator.contains,
             'between': lambda val, pair: val >= pair[0] and val <= pair[1],
             }

    def __call__(self, engine=None):
        if engine is None:
            engine = config.db

        if "+" in self.db:
            dialect, driver = self.db.split('+')
        else:
            dialect, driver = self.db, None

        if dialect and engine.name != dialect:
            return False
        if driver is not None and engine.driver != driver:
            return False

        if self.op is not None:
            assert driver is None, "DBAPI version specs not supported yet"

            version = _server_version(engine)
            oper = hasattr(self.op, '__call__') and self.op \
                        or self._ops[self.op]
            return oper(version, self.spec)
        else:
            return True

    def _as_string(self, negate=False):
        if self.description is not None:
            return self.description
        elif self.op is None:
            if negate:
                return "not %s" % self.db
            else:
                return "%s" % self.db
        else:
            if negate:
                return "not %s %s %s" % (
                        self.db,
                        self.op,
                        self.spec
                    )
            else:
                return "%s %s %s" % (
                        self.db,
                        self.op,
                        self.spec
                    )

    def __str__(self):
        return self._as_string()


class LambdaPredicate(Predicate):
    def __init__(self, lambda_, description=None, args=None, kw=None):
        self.lambda_ = lambda_
        self.args = args or ()
        self.kw = kw or {}
        if description:
            self.description = description
        elif lambda_.__doc__:
            self.description = lambda_.__doc__
        else:
            self.description = "custom function"

    def __call__(self):
        return self.lambda_(*self.args, **self.kw)

    def _as_string(self, negate=False):
        if negate:
            return "not " + self.description
        else:
            return self.description

    def __str__(self):
        return self._as_string()


class NotPredicate(Predicate):
    def __init__(self, predicate):
        self.predicate = predicate

    def __call__(self, *arg, **kw):
        return not self.predicate(*arg, **kw)

    def __str__(self):
        return self.predicate._as_string(True)


class OrPredicate(Predicate):
    def __init__(self, predicates, description=None):
        self.predicates = predicates
        self.description = description

    def __call__(self, *arg, **kw):
        for pred in self.predicates:
            if pred(*arg, **kw):
                self._str = pred
                return True
        return False

    _str = None

    def _eval_str(self, negate=False):
        if self._str is None:
            if negate:
                conjunction = " and "
            else:
                conjunction = " or "
            return conjunction.join(p._as_string(negate=negate)
                            for p in self.predicates)
        else:
            return self._str._as_string(negate=negate)

    def _negation_str(self):
        if self.description is not None:
            return "Not " + (self.description % {"spec": self._str})
        else:
            return self._eval_str(negate=True)

    def _as_string(self, negate=False):
        if negate:
            return self._negation_str()
        else:
            if self.description is not None:
                return self.description % {"spec": self._str}
            else:
                return self._eval_str()

    def __str__(self):
        return self._as_string()

_as_predicate = Predicate.as_predicate


def _is_excluded(db, op, spec):
    return SpecPredicate(db, op, spec)()


def _server_version(engine):
    """Return a server_version_info tuple."""

    # force metadata to be retrieved
    conn = engine.connect()
    version = getattr(engine.dialect, 'server_version_info', ())
    conn.close()
    return version


def db_spec(*dbs):
    return OrPredicate(
            Predicate.as_predicate(db) for db in dbs
        )


def open():
    return skip_if(BooleanPredicate(False, "mark as execute"))


def closed():
    return skip_if(BooleanPredicate(True, "marked as skip"))


@decorator
def future(fn, *args, **kw):
    return fails_if(LambdaPredicate(fn, *args, **kw), "Future feature")


def fails_on(db, reason=None):
    return fails_if(SpecPredicate(db), reason)


def fails_on_everything_except(*dbs):
    return succeeds_if(
                OrPredicate([
                    SpecPredicate(db) for db in dbs
                    ])
            )


def skip(db, reason=None):
    return skip_if(SpecPredicate(db), reason)


def only_on(dbs, reason=None):
    return only_if(
            OrPredicate([SpecPredicate(db) for db in util.to_list(dbs)])
    )


def exclude(db, op, spec, reason=None):
    return skip_if(SpecPredicate(db, op, spec), reason)


def against(*queries):
    return OrPredicate([
                Predicate.as_predicate(query)
                for query in queries
            ])()
