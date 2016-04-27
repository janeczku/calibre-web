""":mod:`wand.font` --- Fonts
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. versionadded:: 0.3.0

:class:`Font` is an object which takes the :attr:`~Font.path` of font file,
:attr:`~Font.size`, :attr:`~Font.color`, and whether to use
:attr:`~Font.antialias`\ ing.  If you want to use font by its name rather
than the file path, use TTFQuery_ package.  The font path resolution by its
name is a very complicated problem to achieve.

.. seealso::

   TTFQuery_ --- Find and Extract Information from TTF Files
      TTFQuery builds on the `FontTools-TTX`_ package to allow the Python
      programmer to accomplish a number of tasks:

      - query the system to find installed fonts

      - retrieve metadata about any TTF font file

        - this includes the glyph outlines (shape) of individual code-points,
          which allows for rendering the glyphs in 3D (such as is done in
          OpenGLContext)

      - lookup/find fonts by:

        - abstract family type
        - proper font name

      - build simple metadata registries for run-time font matching

.. _TTFQuery: http://ttfquery.sourceforge.net/
.. _FontTools-TTX: http://sourceforge.net/projects/fonttools/

"""
import numbers

from .color import Color
from .compat import string_type, text

__all__ = 'Font',


class Font(tuple):
    """Font struct which is a subtype of :class:`tuple`.

    :param path: the path of the font file
    :type path: :class:`str`, :class:`basestring`
    :param size: the size of typeface.  0 by default which means *autosized*
    :type size: :class:`numbers.Real`
    :param color: the color of typeface.  black by default
    :type color: :class:`~wand.color.Color`
    :param antialias: whether to use antialiasing.  :const:`True` by default
    :type antialias: :class:`bool`

    .. versionchanged:: 0.3.9
       The ``size`` parameter becomes optional.  Its default value is
       0, which means *autosized*.

    """

    def __new__(cls, path, size=0, color=None, antialias=True):
        if not isinstance(path, string_type):
            raise TypeError('path must be a string, not ' + repr(path))
        if not isinstance(size, numbers.Real):
            raise TypeError('size must be a real number, not ' + repr(size))
        if color is None:
            color = Color('black')
        elif not isinstance(color, Color):
            raise TypeError('color must be an instance of wand.color.Color, '
                            'not ' + repr(color))
        path = text(path)
        return tuple.__new__(cls, (path, size, color, bool(antialias)))

    @property
    def path(self):
        """(:class:`basestring`) The path of font file."""
        return self[0]

    @property
    def size(self):
        """(:class:`numbers.Real`) The font size in pixels."""
        return self[1]

    @property
    def color(self):
        """(:class:`wand.color.Color`) The font color."""
        return self[2]

    @property
    def antialias(self):
        """(:class:`bool`) Whether to apply antialiasing (``True``)
        or not (``False``).

        """
        return self[3]

    def __repr__(self):
        return '{0.__module__}.{0.__name__}({1})'.format(
            type(self),
            tuple.__repr__(self)
        )
