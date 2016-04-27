from __future__ import absolute_import

import warnings
from .. import exc as sa_exc
from .. import util


def testing_warn(msg, stacklevel=3):
    """Replaces sqlalchemy.util.warn during tests."""

    filename = "sqlalchemy.testing.warnings"
    lineno = 1
    if isinstance(msg, basestring):
        warnings.warn_explicit(msg, sa_exc.SAWarning, filename, lineno)
    else:
        warnings.warn_explicit(msg, filename, lineno)


def resetwarnings():
    """Reset warning behavior to testing defaults."""

    util.warn = util.langhelpers.warn = testing_warn

    warnings.filterwarnings('ignore',
                            category=sa_exc.SAPendingDeprecationWarning)
    warnings.filterwarnings('error', category=sa_exc.SADeprecationWarning)
    warnings.filterwarnings('error', category=sa_exc.SAWarning)


def assert_warnings(fn, warnings):
    """Assert that each of the given warnings are emitted by fn."""

    from .assertions import eq_, emits_warning

    canary = []
    orig_warn = util.warn

    def capture_warnings(*args, **kw):
        orig_warn(*args, **kw)
        popwarn = warnings.pop(0)
        canary.append(popwarn)
        eq_(args[0], popwarn)
    util.warn = util.langhelpers.warn = capture_warnings

    result = emits_warning()(fn)()
    assert canary, "No warning was emitted"
    return result
