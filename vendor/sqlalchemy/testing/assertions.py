from __future__ import absolute_import

from . import util as testutil
from sqlalchemy import pool, orm, util
from sqlalchemy.engine import default, create_engine
from sqlalchemy import exc as sa_exc
from sqlalchemy.util import decorator
from sqlalchemy import types as sqltypes, schema
import warnings
import re
from .warnings import resetwarnings
from .exclusions import db_spec, _is_excluded
from . import assertsql
from . import config
import itertools
from .util import fail
import contextlib


def emits_warning(*messages):
    """Mark a test as emitting a warning.

    With no arguments, squelches all SAWarning failures.  Or pass one or more
    strings; these will be matched to the root of the warning description by
    warnings.filterwarnings().
    """
    # TODO: it would be nice to assert that a named warning was
    # emitted. should work with some monkeypatching of warnings,
    # and may work on non-CPython if they keep to the spirit of
    # warnings.showwarning's docstring.
    # - update: jython looks ok, it uses cpython's module

    @decorator
    def decorate(fn, *args, **kw):
        # todo: should probably be strict about this, too
        filters = [dict(action='ignore',
                        category=sa_exc.SAPendingDeprecationWarning)]
        if not messages:
            filters.append(dict(action='ignore',
                                 category=sa_exc.SAWarning))
        else:
            filters.extend(dict(action='ignore',
                                 message=message,
                                 category=sa_exc.SAWarning)
                            for message in messages)
        for f in filters:
            warnings.filterwarnings(**f)
        try:
            return fn(*args, **kw)
        finally:
            resetwarnings()
    return decorate


def emits_warning_on(db, *warnings):
    """Mark a test as emitting a warning on a specific dialect.

    With no arguments, squelches all SAWarning failures.  Or pass one or more
    strings; these will be matched to the root of the warning description by
    warnings.filterwarnings().
    """
    spec = db_spec(db)

    @decorator
    def decorate(fn, *args, **kw):
        if isinstance(db, basestring):
            if not spec(config.db):
                return fn(*args, **kw)
            else:
                wrapped = emits_warning(*warnings)(fn)
                return wrapped(*args, **kw)
        else:
            if not _is_excluded(*db):
                return fn(*args, **kw)
            else:
                wrapped = emits_warning(*warnings)(fn)
                return wrapped(*args, **kw)
    return decorate


def uses_deprecated(*messages):
    """Mark a test as immune from fatal deprecation warnings.

    With no arguments, squelches all SADeprecationWarning failures.
    Or pass one or more strings; these will be matched to the root
    of the warning description by warnings.filterwarnings().

    As a special case, you may pass a function name prefixed with //
    and it will be re-written as needed to match the standard warning
    verbiage emitted by the sqlalchemy.util.deprecated decorator.
    """

    @decorator
    def decorate(fn, *args, **kw):
        # todo: should probably be strict about this, too
        filters = [dict(action='ignore',
                        category=sa_exc.SAPendingDeprecationWarning)]
        if not messages:
            filters.append(dict(action='ignore',
                                category=sa_exc.SADeprecationWarning))
        else:
            filters.extend(
                [dict(action='ignore',
                      message=message,
                      category=sa_exc.SADeprecationWarning)
                 for message in
                 [(m.startswith('//') and
                    ('Call to deprecated function ' + m[2:]) or m)
                   for m in messages]])

        for f in filters:
            warnings.filterwarnings(**f)
        try:
            return fn(*args, **kw)
        finally:
            resetwarnings()
    return decorate


def global_cleanup_assertions():
    """Check things that have to be finalized at the end of a test suite.

    Hardcoded at the moment, a modular system can be built here
    to support things like PG prepared transactions, tables all
    dropped, etc.

    """

    testutil.lazy_gc()
    assert not pool._refs, str(pool._refs)


def eq_(a, b, msg=None):
    """Assert a == b, with repr messaging on failure."""
    assert a == b, msg or "%r != %r" % (a, b)


def ne_(a, b, msg=None):
    """Assert a != b, with repr messaging on failure."""
    assert a != b, msg or "%r == %r" % (a, b)


def is_(a, b, msg=None):
    """Assert a is b, with repr messaging on failure."""
    assert a is b, msg or "%r is not %r" % (a, b)


def is_not_(a, b, msg=None):
    """Assert a is not b, with repr messaging on failure."""
    assert a is not b, msg or "%r is %r" % (a, b)


def startswith_(a, fragment, msg=None):
    """Assert a.startswith(fragment), with repr messaging on failure."""
    assert a.startswith(fragment), msg or "%r does not start with %r" % (
        a, fragment)


def assert_raises(except_cls, callable_, *args, **kw):
    try:
        callable_(*args, **kw)
        success = False
    except except_cls:
        success = True

    # assert outside the block so it works for AssertionError too !
    assert success, "Callable did not raise an exception"


def assert_raises_message(except_cls, msg, callable_, *args, **kwargs):
    try:
        callable_(*args, **kwargs)
        assert False, "Callable did not raise an exception"
    except except_cls, e:
        assert re.search(msg, unicode(e), re.UNICODE), u"%r !~ %s" % (msg, e)
        print unicode(e).encode('utf-8')


class AssertsCompiledSQL(object):
    def assert_compile(self, clause, result, params=None,
                        checkparams=None, dialect=None,
                        checkpositional=None,
                        use_default_dialect=False,
                        allow_dialect_select=False):
        if use_default_dialect:
            dialect = default.DefaultDialect()
        elif dialect == None and not allow_dialect_select:
            dialect = getattr(self, '__dialect__', None)
            if dialect == 'default':
                dialect = default.DefaultDialect()
            elif dialect is None:
                dialect = config.db.dialect
            elif isinstance(dialect, basestring):
                dialect = create_engine("%s://" % dialect).dialect

        kw = {}
        if params is not None:
            kw['column_keys'] = params.keys()

        if isinstance(clause, orm.Query):
            context = clause._compile_context()
            context.statement.use_labels = True
            clause = context.statement

        c = clause.compile(dialect=dialect, **kw)

        param_str = repr(getattr(c, 'params', {}))
        # Py3K
        #param_str = param_str.encode('utf-8').decode('ascii', 'ignore')

        print "\nSQL String:\n" + str(c) + param_str

        cc = re.sub(r'[\n\t]', '', str(c))

        eq_(cc, result, "%r != %r on dialect %r" % (cc, result, dialect))

        if checkparams is not None:
            eq_(c.construct_params(params), checkparams)
        if checkpositional is not None:
            p = c.construct_params(params)
            eq_(tuple([p[x] for x in c.positiontup]), checkpositional)


class ComparesTables(object):

    def assert_tables_equal(self, table, reflected_table, strict_types=False):
        assert len(table.c) == len(reflected_table.c)
        for c, reflected_c in zip(table.c, reflected_table.c):
            eq_(c.name, reflected_c.name)
            assert reflected_c is reflected_table.c[c.name]
            eq_(c.primary_key, reflected_c.primary_key)
            eq_(c.nullable, reflected_c.nullable)

            if strict_types:
                msg = "Type '%s' doesn't correspond to type '%s'"
                assert type(reflected_c.type) is type(c.type), \
                    msg % (reflected_c.type, c.type)
            else:
                self.assert_types_base(reflected_c, c)

            if isinstance(c.type, sqltypes.String):
                eq_(c.type.length, reflected_c.type.length)

            eq_(
                set([f.column.name for f in c.foreign_keys]),
                set([f.column.name for f in reflected_c.foreign_keys])
            )
            if c.server_default:
                assert isinstance(reflected_c.server_default,
                                  schema.FetchedValue)

        assert len(table.primary_key) == len(reflected_table.primary_key)
        for c in table.primary_key:
            assert reflected_table.primary_key.columns[c.name] is not None

    def assert_types_base(self, c1, c2):
        assert c1.type._compare_type_affinity(c2.type),\
                "On column %r, type '%s' doesn't correspond to type '%s'" % \
                (c1.name, c1.type, c2.type)


class AssertsExecutionResults(object):
    def assert_result(self, result, class_, *objects):
        result = list(result)
        print repr(result)
        self.assert_list(result, class_, objects)

    def assert_list(self, result, class_, list):
        self.assert_(len(result) == len(list),
                     "result list is not the same size as test list, " +
                     "for class " + class_.__name__)
        for i in range(0, len(list)):
            self.assert_row(class_, result[i], list[i])

    def assert_row(self, class_, rowobj, desc):
        self.assert_(rowobj.__class__ is class_,
                     "item class is not " + repr(class_))
        for key, value in desc.iteritems():
            if isinstance(value, tuple):
                if isinstance(value[1], list):
                    self.assert_list(getattr(rowobj, key), value[0], value[1])
                else:
                    self.assert_row(value[0], getattr(rowobj, key), value[1])
            else:
                self.assert_(getattr(rowobj, key) == value,
                             "attribute %s value %s does not match %s" % (
                             key, getattr(rowobj, key), value))

    def assert_unordered_result(self, result, cls, *expected):
        """As assert_result, but the order of objects is not considered.

        The algorithm is very expensive but not a big deal for the small
        numbers of rows that the test suite manipulates.
        """

        class immutabledict(dict):
            def __hash__(self):
                return id(self)

        found = util.IdentitySet(result)
        expected = set([immutabledict(e) for e in expected])

        for wrong in itertools.ifilterfalse(lambda o: type(o) == cls, found):
            fail('Unexpected type "%s", expected "%s"' % (
                type(wrong).__name__, cls.__name__))

        if len(found) != len(expected):
            fail('Unexpected object count "%s", expected "%s"' % (
                len(found), len(expected)))

        NOVALUE = object()

        def _compare_item(obj, spec):
            for key, value in spec.iteritems():
                if isinstance(value, tuple):
                    try:
                        self.assert_unordered_result(
                            getattr(obj, key), value[0], *value[1])
                    except AssertionError:
                        return False
                else:
                    if getattr(obj, key, NOVALUE) != value:
                        return False
            return True

        for expected_item in expected:
            for found_item in found:
                if _compare_item(found_item, expected_item):
                    found.remove(found_item)
                    break
            else:
                fail(
                    "Expected %s instance with attributes %s not found." % (
                    cls.__name__, repr(expected_item)))
        return True

    def assert_sql_execution(self, db, callable_, *rules):
        assertsql.asserter.add_rules(rules)
        try:
            callable_()
            assertsql.asserter.statement_complete()
        finally:
            assertsql.asserter.clear_rules()

    def assert_sql(self, db, callable_, list_, with_sequences=None):
        if with_sequences is not None and config.db.dialect.supports_sequences:
            rules = with_sequences
        else:
            rules = list_

        newrules = []
        for rule in rules:
            if isinstance(rule, dict):
                newrule = assertsql.AllOf(*[
                    assertsql.ExactSQL(k, v) for k, v in rule.iteritems()
                ])
            else:
                newrule = assertsql.ExactSQL(*rule)
            newrules.append(newrule)

        self.assert_sql_execution(db, callable_, *newrules)

    def assert_sql_count(self, db, callable_, count):
        self.assert_sql_execution(
            db, callable_, assertsql.CountStatements(count))

    @contextlib.contextmanager
    def assert_execution(self, *rules):
        assertsql.asserter.add_rules(rules)
        try:
            yield
            assertsql.asserter.statement_complete()
        finally:
            assertsql.asserter.clear_rules()

    def assert_statement_count(self, count):
        return self.assert_execution(assertsql.CountStatements(count))
