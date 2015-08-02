# util/deprecations.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Helpers related to deprecation of functions, methods, classes, other
functionality."""

from .. import exc
import warnings
import re
from langhelpers import decorator


def warn_deprecated(msg, stacklevel=3):
    warnings.warn(msg, exc.SADeprecationWarning, stacklevel=stacklevel)


def warn_pending_deprecation(msg, stacklevel=3):
    warnings.warn(msg, exc.SAPendingDeprecationWarning, stacklevel=stacklevel)


def deprecated(version, message=None, add_deprecation_to_docstring=True):
    """Decorates a function and issues a deprecation warning on use.

    :param message:
      If provided, issue message in the warning.  A sensible default
      is used if not provided.

    :param add_deprecation_to_docstring:
      Default True.  If False, the wrapped function's __doc__ is left
      as-is.  If True, the 'message' is prepended to the docs if
      provided, or sensible default if message is omitted.

    """

    if add_deprecation_to_docstring:
        header = ".. deprecated:: %s %s" % \
                    (version, (message or ''))
    else:
        header = None

    if message is None:
        message = "Call to deprecated function %(func)s"

    def decorate(fn):
        return _decorate_with_warning(
            fn, exc.SADeprecationWarning,
            message % dict(func=fn.__name__), header)
    return decorate


def pending_deprecation(version, message=None,
                        add_deprecation_to_docstring=True):
    """Decorates a function and issues a pending deprecation warning on use.

    :param version:
      An approximate future version at which point the pending deprecation
      will become deprecated.  Not used in messaging.

    :param message:
      If provided, issue message in the warning.  A sensible default
      is used if not provided.

    :param add_deprecation_to_docstring:
      Default True.  If False, the wrapped function's __doc__ is left
      as-is.  If True, the 'message' is prepended to the docs if
      provided, or sensible default if message is omitted.
    """

    if add_deprecation_to_docstring:
        header = ".. deprecated:: %s (pending) %s" % \
                        (version, (message or ''))
    else:
        header = None

    if message is None:
        message = "Call to deprecated function %(func)s"

    def decorate(fn):
        return _decorate_with_warning(
            fn, exc.SAPendingDeprecationWarning,
            message % dict(func=fn.__name__), header)
    return decorate


def _sanitize_restructured_text(text):
    def repl(m):
        type_, name = m.group(1, 2)
        if type_ in ("func", "meth"):
            name += "()"
        return name
    return re.sub(r'\:(\w+)\:`~?\.?(.+?)`', repl, text)


def _decorate_with_warning(func, wtype, message, docstring_header=None):
    """Wrap a function with a warnings.warn and augmented docstring."""

    message = _sanitize_restructured_text(message)

    @decorator
    def warned(fn, *args, **kwargs):
        warnings.warn(wtype(message), stacklevel=3)
        return fn(*args, **kwargs)

    doc = func.__doc__ is not None and func.__doc__ or ''
    if docstring_header is not None:
        docstring_header %= dict(func=func.__name__)
        docs = doc and doc.expandtabs().split('\n') or []
        indent = ''
        for line in docs[1:]:
            text = line.lstrip()
            if text:
                indent = line[0:len(line) - len(text)]
                break
        point = min(len(docs), 1)
        docs.insert(point, '\n' + indent + docstring_header.rstrip())
        doc = '\n'.join(docs)

    decorated = warned(func)
    decorated.__doc__ = doc
    return decorated
