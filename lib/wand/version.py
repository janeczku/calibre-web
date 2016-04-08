""":mod:`wand.version` --- Version data
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can find the current version in the command line interface:

.. sourcecode:: console

   $ python -m wand.version
   0.0.0
   $ python -m wand.version --verbose
   Wand 0.0.0
   ImageMagick 6.7.7-6 2012-06-03 Q16 http://www.imagemagick.org
   $ python -m wand.version --config | grep CC | cut -d : -f 2
   gcc -std=gnu99 -std=gnu99
   $ python -m wand.version --fonts | grep Helvetica
   Helvetica
   Helvetica-Bold
   Helvetica-Light
   Helvetica-Narrow
   Helvetica-Oblique
   $ python -m wand.version --formats | grep CMYK
   CMYK
   CMYKA

.. versionadded:: 0.2.0
   The command line interface.

.. versionadded:: 0.2.2
   The ``--verbose``/``-v`` option which also prints ImageMagick library
   version for CLI.

.. versionadded:: 0.4.1
   The ``--fonts``, ``--formats``, & ``--config`` option allows printing
   additional information about ImageMagick library.

"""
from __future__ import print_function

import ctypes
import datetime
import re
import sys

try:
    from .api import libmagick, library
except ImportError:
    libmagick = None
from .compat import binary, string_type, text


__all__ = ('VERSION', 'VERSION_INFO', 'MAGICK_VERSION',
           'MAGICK_VERSION_INFO', 'MAGICK_VERSION_NUMBER',
           'MAGICK_RELEASE_DATE', 'MAGICK_RELEASE_DATE_STRING',
           'QUANTUM_DEPTH', 'configure_options', 'fonts', 'formats')

#: (:class:`tuple`) The version tuple e.g. ``(0, 1, 2)``.
#:
#: .. versionchanged:: 0.1.9
#:    Becomes :class:`tuple`.  (It was string before.)
VERSION_INFO = (0, 4, 2)

#: (:class:`basestring`) The version string e.g. ``'0.1.2'``.
#:
#: .. versionchanged:: 0.1.9
#:    Becomes string.  (It was :class:`tuple` before.)
VERSION = '{0}.{1}.{2}'.format(*VERSION_INFO)

if libmagick:
    c_magick_version = ctypes.c_size_t()
    #: (:class:`basestring`) The version string of the linked ImageMagick
    #: library.  The exactly same string to the result of
    #: :c:func:`GetMagickVersion` function.
    #:
    #: Example::
    #:
    #:    'ImageMagick 6.7.7-6 2012-06-03 Q16 http://www.imagemagick.org'
    #:
    #: .. versionadded:: 0.2.1
    MAGICK_VERSION = text(
        libmagick.GetMagickVersion(ctypes.byref(c_magick_version))
    )

    #: (:class:`numbers.Integral`) The version number of the linked
    #: ImageMagick library.
    #:
    #: .. versionadded:: 0.2.1
    MAGICK_VERSION_NUMBER = c_magick_version.value

    _match = re.match(r'^ImageMagick\s+(\d+)\.(\d+)\.(\d+)(?:-(\d+))?',
                      MAGICK_VERSION)
    #: (:class:`tuple`) The version tuple e.g. ``(6, 7, 7, 6)`` of
    #: :const:`MAGICK_VERSION`.
    #:
    #: .. versionadded:: 0.2.1
    MAGICK_VERSION_INFO = tuple(int(v or 0) for v in _match.groups())

    #: (:class:`datetime.date`) The release date of the linked ImageMagick
    #: library.  The same to the result of :c:func:`GetMagickReleaseDate`
    #: function.
    #:
    #: .. versionadded:: 0.2.1
    MAGICK_RELEASE_DATE_STRING = text(libmagick.GetMagickReleaseDate())

    #: (:class:`basestring`) The date string e.g. ``'2012-06-03'`` of
    #: :const:`MAGICK_RELEASE_DATE_STRING`.  This value is the exactly same
    #: string to the result of :c:func:`GetMagickReleaseDate` function.
    #:
    #: .. versionadded:: 0.2.1
    MAGICK_RELEASE_DATE = datetime.date(
        *map(int, MAGICK_RELEASE_DATE_STRING.split('-')))

    c_quantum_depth = ctypes.c_size_t()
    libmagick.GetMagickQuantumDepth(ctypes.byref(c_quantum_depth))
    #: (:class:`numbers.Integral`) The quantum depth configuration of
    #: the linked ImageMagick library.  One of 8, 16, 32, or 64.
    #:
    #: .. versionadded:: 0.3.0
    QUANTUM_DEPTH = c_quantum_depth.value

    del c_magick_version, _match, c_quantum_depth


def configure_options(pattern='*'):
    """
    Queries ImageMagick library for configurations options given at
    compile-time.

    Example: Find where the ImageMagick documents are installed::

        >>> from wand.version import configure_options
        >>> configure_options('DOC*')
        {'DOCUMENTATION_PATH': '/usr/local/share/doc/ImageMagick-6'}

    :param pattern: A term to filter queries against. Supports wildcard '*'
                    characters. Default patterns '*' for all options.
    :type pattern: :class:`basestring`
    :returns: Directory of configuration options matching given pattern
    :rtype: :class:`collections.defaultdict`
    """
    if not isinstance(pattern, string_type):
        raise TypeError('pattern must be a string, not ' + repr(pattern))
    pattern_p = ctypes.create_string_buffer(binary(pattern))
    config_count = ctypes.c_size_t(0)
    configs = {}
    configs_p = library.MagickQueryConfigureOptions(pattern_p,
                                                    ctypes.byref(config_count))
    cursor = 0
    while cursor < config_count.value:
        config = configs_p[cursor].value
        value = library.MagickQueryConfigureOption(config)
        configs[text(config)] = text(value.value)
        cursor += 1
    return configs


def fonts(pattern='*'):
    """
    Queries ImageMagick library for available fonts.

    Available fonts can be configured by defining `types.xml`,
    `type-ghostscript.xml`, or `type-windows.xml`.
    Use :func:`wand.version.configure_options` to locate system search path,
    and `resources <http://www.imagemagick.org/script/resources.php>`_
    article for defining xml file.

    Example: List all bold Helvetica fonts::

        >>> from wand.version import fonts
        >>> fonts('*Helvetica*Bold*')
        ['Helvetica-Bold', 'Helvetica-Bold-Oblique', 'Helvetica-BoldOblique',
         'Helvetica-Narrow-Bold', 'Helvetica-Narrow-BoldOblique']


    :param pattern: A term to filter queries against. Supports wildcard '*'
                    characters. Default patterns '*' for all options.
    :type pattern: :class:`basestring`
    :returns: Sequence of matching fonts
    :rtype: :class:`collections.Sequence`
    """
    if not isinstance(pattern, string_type):
        raise TypeError('pattern must be a string, not ' + repr(pattern))
    pattern_p = ctypes.create_string_buffer(binary(pattern))
    number_fonts = ctypes.c_size_t(0)
    fonts = []
    fonts_p = library.MagickQueryFonts(pattern_p,
                                       ctypes.byref(number_fonts))
    cursor = 0
    while cursor < number_fonts.value:
        font = fonts_p[cursor].value
        fonts.append(text(font))
        cursor += 1
    return fonts


def formats(pattern='*'):
    """
    Queries ImageMagick library for supported formats.

    Example: List supported PNG formats::

        >>> from wand.version import formats
        >>> formats('PNG*')
        ['PNG', 'PNG00', 'PNG8', 'PNG24', 'PNG32', 'PNG48', 'PNG64']


    :param pattern: A term to filter formats against. Supports wildcards '*'
                    characters. Default pattern '*' for all formats.
    :type pattern: :class:`basestring`
    :returns: Sequence of matching formats
    :rtype: :class:`collections.Sequence`
    """
    if not isinstance(pattern, string_type):
        raise TypeError('pattern must be a string, not ' + repr(pattern))
    pattern_p = ctypes.create_string_buffer(binary(pattern))
    number_formats = ctypes.c_size_t(0)
    formats = []
    formats_p = library.MagickQueryFormats(pattern_p,
                                           ctypes.byref(number_formats))
    cursor = 0
    while cursor < number_formats.value:
        value = formats_p[cursor].value
        formats.append(text(value))
        cursor += 1
    return formats

if __doc__ is not None:
    __doc__ = __doc__.replace('0.0.0', VERSION)

del libmagick


if __name__ == '__main__':
    options = frozenset(sys.argv[1:])
    if '-v' in options or '--verbose' in options:
        print('Wand', VERSION)
        try:
            print(MAGICK_VERSION)
        except NameError:
            pass
    elif '--fonts' in options:
        for font in fonts():
            print(font)
    elif '--formats' in options:
        for supported_format in formats():
            print(supported_format)
    elif '--config' in options:
        config_options = configure_options()
        for key in config_options:
            print('{:24s}: {}'.format(key, config_options[key]))
    else:
        print(VERSION)
