from ..util import jython, pypy, defaultdict, decorator
import decimal
import gc
import time
import random
import sys
import types

if jython:
    def jython_gc_collect(*args):
        """aggressive gc.collect for tests."""
        gc.collect()
        time.sleep(0.1)
        gc.collect()
        gc.collect()
        return 0

    # "lazy" gc, for VM's that don't GC on refcount == 0
    gc_collect = lazy_gc = jython_gc_collect
elif pypy:
    def pypy_gc_collect(*args):
        gc.collect()
        gc.collect()
    gc_collect = lazy_gc = pypy_gc_collect
else:
    # assume CPython - straight gc.collect, lazy_gc() is a pass
    gc_collect = gc.collect

    def lazy_gc():
        pass


def picklers():
    picklers = set()
    # Py2K
    try:
        import cPickle
        picklers.add(cPickle)
    except ImportError:
        pass
    # end Py2K
    import pickle
    picklers.add(pickle)

    # yes, this thing needs this much testing
    for pickle_ in picklers:
        for protocol in -1, 0, 1, 2:
            yield pickle_.loads, lambda d: pickle_.dumps(d, protocol)


def round_decimal(value, prec):
    if isinstance(value, float):
        return round(value, prec)

    # can also use shift() here but that is 2.6 only
    return (value * decimal.Decimal("1" + "0" * prec)
                    ).to_integral(decimal.ROUND_FLOOR) / \
                        pow(10, prec)


class RandomSet(set):
    def __iter__(self):
        l = list(set.__iter__(self))
        random.shuffle(l)
        return iter(l)

    def pop(self):
        index = random.randint(0, len(self) - 1)
        item = list(set.__iter__(self))[index]
        self.remove(item)
        return item

    def union(self, other):
        return RandomSet(set.union(self, other))

    def difference(self, other):
        return RandomSet(set.difference(self, other))

    def intersection(self, other):
        return RandomSet(set.intersection(self, other))

    def copy(self):
        return RandomSet(self)


def conforms_partial_ordering(tuples, sorted_elements):
    """True if the given sorting conforms to the given partial ordering."""

    deps = defaultdict(set)
    for parent, child in tuples:
        deps[parent].add(child)
    for i, node in enumerate(sorted_elements):
        for n in sorted_elements[i:]:
            if node in deps[n]:
                return False
    else:
        return True


def all_partial_orderings(tuples, elements):
    edges = defaultdict(set)
    for parent, child in tuples:
        edges[child].add(parent)

    def _all_orderings(elements):

        if len(elements) == 1:
            yield list(elements)
        else:
            for elem in elements:
                subset = set(elements).difference([elem])
                if not subset.intersection(edges[elem]):
                    for sub_ordering in _all_orderings(subset):
                        yield [elem] + sub_ordering

    return iter(_all_orderings(elements))


def function_named(fn, name):
    """Return a function with a given __name__.

    Will assign to __name__ and return the original function if possible on
    the Python implementation, otherwise a new function will be constructed.

    This function should be phased out as much as possible
    in favor of @decorator.   Tests that "generate" many named tests
    should be modernized.

    """
    try:
        fn.__name__ = name
    except TypeError:
        fn = types.FunctionType(fn.func_code, fn.func_globals, name,
                          fn.func_defaults, fn.func_closure)
    return fn


def run_as_contextmanager(ctx, fn, *arg, **kw):
    """Run the given function under the given contextmanager,
    simulating the behavior of 'with' to support older
    Python versions.

    """

    obj = ctx.__enter__()
    try:
        result = fn(obj, *arg, **kw)
        ctx.__exit__(None, None, None)
        return result
    except:
        exc_info = sys.exc_info()
        raise_ = ctx.__exit__(*exc_info)
        if raise_ is None:
            raise
        else:
            return raise_


def rowset(results):
    """Converts the results of sql execution into a plain set of column tuples.

    Useful for asserting the results of an unordered query.
    """

    return set([tuple(row) for row in results])


def fail(msg):
    assert False, msg


@decorator
def provide_metadata(fn, *args, **kw):
    """Provide bound MetaData for a single test, dropping afterwards."""

    from . import config
    from sqlalchemy import schema

    metadata = schema.MetaData(config.db)
    self = args[0]
    prev_meta = getattr(self, 'metadata', None)
    self.metadata = metadata
    try:
        return fn(*args, **kw)
    finally:
        metadata.drop_all()
        self.metadata = prev_meta


class adict(dict):
    """Dict keys available as attributes.  Shadows."""
    def __getattribute__(self, key):
        try:
            return self[key]
        except KeyError:
            return dict.__getattribute__(self, key)

    def get_all(self, *keys):
        return tuple([self[key] for key in keys])
