"""Profiling support for unit and performance tests.

These are special purpose profiling methods which operate
in a more fine-grained way than nose's profiling plugin.

"""

import os
import sys
from .util import gc_collect, decorator
from . import config
from nose import SkipTest
import pstats
import time
import collections
from .. import util

try:
    import cProfile
except ImportError:
    cProfile = None
from ..util import jython, pypy, win32, update_wrapper

_current_test = None


def profiled(target=None, **target_opts):
    """Function profiling.

    @profiled()
    or
    @profiled(report=True, sort=('calls',), limit=20)

    Outputs profiling info for a decorated function.

    """

    profile_config = {'targets': set(),
                       'report': True,
                       'print_callers': False,
                       'print_callees': False,
                       'graphic': False,
                       'sort': ('time', 'calls'),
                       'limit': None}
    if target is None:
        target = 'anonymous_target'

    filename = "%s.prof" % target

    @decorator
    def decorate(fn, *args, **kw):
        elapsed, load_stats, result = _profile(
            filename, fn, *args, **kw)

        graphic = target_opts.get('graphic', profile_config['graphic'])
        if graphic:
            os.system("runsnake %s" % filename)
        else:
            report = target_opts.get('report', profile_config['report'])
            if report:
                sort_ = target_opts.get('sort', profile_config['sort'])
                limit = target_opts.get('limit', profile_config['limit'])
                print ("Profile report for target '%s' (%s)" % (
                    target, filename)
                    )

                stats = load_stats()
                stats.sort_stats(*sort_)
                if limit:
                    stats.print_stats(limit)
                else:
                    stats.print_stats()

                print_callers = target_opts.get(
                    'print_callers', profile_config['print_callers'])
                if print_callers:
                    stats.print_callers()

                print_callees = target_opts.get(
                    'print_callees', profile_config['print_callees'])
                if print_callees:
                    stats.print_callees()

        os.unlink(filename)
        return result
    return decorate


class ProfileStatsFile(object):
    """"Store per-platform/fn profiling results in a file.

    We're still targeting Py2.5, 2.4 on 0.7 with no dependencies,
    so no json lib :(  need to roll something silly

    """
    def __init__(self, filename):
        self.write = (
            config.options is not None and
            config.options.write_profiles
        )
        self.fname = os.path.abspath(filename)
        self.short_fname = os.path.split(self.fname)[-1]
        self.data = collections.defaultdict(
            lambda: collections.defaultdict(dict))
        self._read()
        if self.write:
            # rewrite for the case where features changed,
            # etc.
            self._write()

    @util.memoized_property
    def platform_key(self):

        dbapi_key = config.db.name + "_" + config.db.driver

        # keep it at 2.7, 3.1, 3.2, etc. for now.
        py_version = '.'.join([str(v) for v in sys.version_info[0:2]])

        platform_tokens = [py_version]
        platform_tokens.append(dbapi_key)
        if jython:
            platform_tokens.append("jython")
        if pypy:
            platform_tokens.append("pypy")
        if win32:
            platform_tokens.append("win")
        _has_cext = config.requirements._has_cextensions()
        platform_tokens.append(_has_cext and "cextensions" or "nocextensions")
        return "_".join(platform_tokens)

    def has_stats(self):
        test_key = _current_test
        return (
            test_key in self.data and
            self.platform_key in self.data[test_key]
        )

    def result(self, callcount):
        test_key = _current_test
        per_fn = self.data[test_key]
        per_platform = per_fn[self.platform_key]

        if 'counts' not in per_platform:
            per_platform['counts'] = counts = []
        else:
            counts = per_platform['counts']

        if 'current_count' not in per_platform:
            per_platform['current_count'] = current_count = 0
        else:
            current_count = per_platform['current_count']

        has_count = len(counts) > current_count

        if not has_count:
            counts.append(callcount)
            if self.write:
                self._write()
            result = None
        else:
            result = per_platform['lineno'], counts[current_count]
        per_platform['current_count'] += 1
        return result

    def _header(self):
        return \
        "# %s\n"\
        "# This file is written out on a per-environment basis.\n"\
        "# For each test in aaa_profiling, the corresponding function and \n"\
        "# environment is located within this file.  If it doesn't exist,\n"\
        "# the test is skipped.\n"\
        "# If a callcount does exist, it is compared to what we received. \n"\
        "# assertions are raised if the counts do not match.\n"\
        "# \n"\
        "# To add a new callcount test, apply the function_call_count \n"\
        "# decorator and re-run the tests using the --write-profiles \n"\
        "# option - this file will be rewritten including the new count.\n"\
        "# \n"\
        "" % (self.fname)

    def _read(self):
        try:
            profile_f = open(self.fname)
        except IOError:
            return
        for lineno, line in enumerate(profile_f):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            test_key, platform_key, counts = line.split()
            per_fn = self.data[test_key]
            per_platform = per_fn[platform_key]
            c = [int(count) for count in counts.split(",")]
            per_platform['counts'] = c
            per_platform['lineno'] = lineno + 1
            per_platform['current_count'] = 0
        profile_f.close()

    def _write(self):
        print("Writing profile file %s" % self.fname)
        profile_f = open(self.fname, "w")
        profile_f.write(self._header())
        for test_key in sorted(self.data):

            per_fn = self.data[test_key]
            profile_f.write("\n# TEST: %s\n\n" % test_key)
            for platform_key in sorted(per_fn):
                per_platform = per_fn[platform_key]
                c = ",".join(str(count) for count in per_platform['counts'])
                profile_f.write("%s %s %s\n" % (test_key, platform_key, c))
        profile_f.close()



def function_call_count(variance=0.05):
    """Assert a target for a test case's function call count.

    The main purpose of this assertion is to detect changes in
    callcounts for various functions - the actual number is not as important.
    Callcounts are stored in a file keyed to Python version and OS platform
    information.  This file is generated automatically for new tests,
    and versioned so that unexpected changes in callcounts will be detected.

    """

    def decorate(fn):
        def wrap(*args, **kw):

            if cProfile is None:
                raise SkipTest("cProfile is not installed")

            if not _profile_stats.has_stats() and not _profile_stats.write:
                # run the function anyway, to support dependent tests
                # (not a great idea but we have these in test_zoomark)
                fn(*args, **kw)
                raise SkipTest("No profiling stats available on this "
                            "platform for this function.  Run tests with "
                            "--write-profiles to add statistics to %s for "
                            "this platform." % _profile_stats.short_fname)

            gc_collect()

            timespent, load_stats, fn_result = _profile(
                fn, *args, **kw
            )
            stats = load_stats()
            callcount = stats.total_calls

            expected = _profile_stats.result(callcount)
            if expected is None:
                expected_count = None
            else:
                line_no, expected_count = expected

            print("Pstats calls: %d Expected %s" % (
                    callcount,
                    expected_count
                )
            )
            stats.print_stats()
            #stats.print_callers()

            if expected_count:
                deviance = int(callcount * variance)
                if abs(callcount - expected_count) > deviance:
                    raise AssertionError(
                        "Adjusted function call count %s not within %s%% "
                        "of expected %s. (Delete line %d of file %s to "
                        "regenerate this callcount, when tests are run "
                        "with --write-profiles.)"
                        % (
                        callcount, (variance * 100),
                        expected_count, line_no,
                        _profile_stats.fname))
            return fn_result
        return update_wrapper(wrap, fn)
    return decorate


def _profile(fn, *args, **kw):
    filename = "%s.prof" % fn.__name__

    def load_stats():
        st = pstats.Stats(filename)
        os.unlink(filename)
        return st

    began = time.time()
    cProfile.runctx('result = fn(*args, **kw)', globals(), locals(),
                    filename=filename)
    ended = time.time()

    return ended - began, load_stats, locals()['result']
