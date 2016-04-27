""":mod:`wand.compat` --- Compatibility layer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This module provides several subtle things to support
multiple Python versions (2.6, 2.7, 3.2--3.5) and VM implementations
(CPython, PyPy).

"""
import contextlib
import io
import sys
import types

__all__ = ('PY3', 'binary', 'binary_type', 'encode_filename', 'file_types',
           'nested', 'string_type', 'text', 'text_type', 'xrange')


#: (:class:`bool`) Whether it is Python 3.x or not.
PY3 = sys.version_info >= (3,)

#: (:class:`type`) Type for representing binary data.  :class:`str` in Python 2
#: and :class:`bytes` in Python 3.
binary_type = bytes if PY3 else str

#: (:class:`type`) Type for text data.  :class:`basestring` in Python 2
#: and :class:`str` in Python 3.
string_type = str if PY3 else basestring  # noqa

#: (:class:`type`) Type for representing Unicode textual data.
#: :class:`unicode` in Python 2 and :class:`str` in Python 3.
text_type = str if PY3 else unicode  # noqa


def binary(string, var=None):
    """Makes ``string`` to :class:`str` in Python 2.
    Makes ``string`` to :class:`bytes` in Python 3.

    :param string: a string to cast it to :data:`binary_type`
    :type string: :class:`bytes`, :class:`str`, :class:`unicode`
    :param var: an optional variable name to be used for error message
    :type var: :class:`str`

    """
    if isinstance(string, text_type):
        return string.encode()
    elif isinstance(string, binary_type):
        return string
    if var:
        raise TypeError('{0} must be a string, not {1!r}'.format(var, string))
    raise TypeError('expected a string, not ' + repr(string))


if PY3:
    def text(string):
        if isinstance(string, bytes):
            return string.decode('utf-8')
        return string
else:
    def text(string):
        """Makes ``string`` to :class:`str` in Python 3.
        Does nothing in Python 2.

        :param string: a string to cast it to :data:`text_type`
        :type string: :class:`bytes`, :class:`str`, :class:`unicode`

        """
        return string


#: The :func:`xrange()` function.  Alias for :func:`range()` in Python 3.
xrange = range if PY3 else xrange  # noqa


#: (:class:`type`, :class:`tuple`) Types for file objects that have
#: ``fileno()``.
file_types = io.RawIOBase if PY3 else (io.RawIOBase, types.FileType)


def encode_filename(filename):
    """If ``filename`` is a :data:`text_type`, encode it to
    :data:`binary_type` according to filesystem's default encoding.

    """
    if isinstance(filename, text_type):
        return filename.encode(sys.getfilesystemencoding())
    return filename


try:
    nested = contextlib.nested
except AttributeError:
    # http://hg.python.org/cpython/file/v2.7.6/Lib/contextlib.py#l88
    @contextlib.contextmanager
    def nested(*managers):
        exits = []
        vars = []
        exc = (None, None, None)
        try:
            for mgr in managers:
                exit = mgr.__exit__
                enter = mgr.__enter__
                vars.append(enter())
                exits.append(exit)
            yield vars
        except:
            exc = sys.exc_info()
        finally:
            while exits:
                exit = exits.pop()
                try:
                    if exit(*exc):
                        exc = (None, None, None)
                except:
                    exc = sys.exc_info()
            if exc != (None, None, None):
                # PEP 3109
                e = exc[0](exc[1])
                e.__traceback__ = e[2]
                raise e
