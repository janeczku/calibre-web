# engine/util.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

from .. import util


def _coerce_config(configuration, prefix):
    """Convert configuration values to expected types."""

    options = dict((key[len(prefix):], configuration[key])
                   for key in configuration
                   if key.startswith(prefix))
    for option, type_ in (
        ('convert_unicode', util.bool_or_str('force')),
        ('pool_timeout', int),
        ('echo', util.bool_or_str('debug')),
        ('echo_pool', util.bool_or_str('debug')),
        ('pool_recycle', int),
        ('pool_size', int),
        ('max_overflow', int),
        ('pool_threadlocal', bool),
        ('use_native_unicode', bool),
    ):
        util.coerce_kw_type(options, option, type_)
    return options


def connection_memoize(key):
    """Decorator, memoize a function in a connection.info stash.

    Only applicable to functions which take no arguments other than a
    connection.  The memo will be stored in ``connection.info[key]``.
    """

    @util.decorator
    def decorated(fn, self, connection):
        connection = connection.connect()
        try:
            return connection.info[key]
        except KeyError:
            connection.info[key] = val = fn(self, connection)
            return val

    return decorated


def py_fallback():
    def _distill_params(multiparams, params):
        """Given arguments from the calling form *multiparams, **params,
        return a list of bind parameter structures, usually a list of
        dictionaries.

        In the case of 'raw' execution which accepts positional parameters,
        it may be a list of tuples or lists.

        """

        if not multiparams:
            if params:
                return [params]
            else:
                return []
        elif len(multiparams) == 1:
            zero = multiparams[0]
            if isinstance(zero, (list, tuple)):
                if not zero or hasattr(zero[0], '__iter__') and \
                        not hasattr(zero[0], 'strip'):
                    # execute(stmt, [{}, {}, {}, ...])
                    # execute(stmt, [(), (), (), ...])
                    return zero
                else:
                    # execute(stmt, ("value", "value"))
                    return [zero]
            elif hasattr(zero, 'keys'):
                # execute(stmt, {"key":"value"})
                return [zero]
            else:
                # execute(stmt, "value")
                return [[zero]]
        else:
            if hasattr(multiparams[0], '__iter__') and \
                not hasattr(multiparams[0], 'strip'):
                return multiparams
            else:
                return [multiparams]

    return locals()
try:
    from sqlalchemy.cutils import _distill_params
except ImportError:
    globals().update(py_fallback())
