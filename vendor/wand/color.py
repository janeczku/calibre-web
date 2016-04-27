""":mod:`wand.color` --- Colors
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. versionadded:: 0.1.2

"""
import ctypes

from .api import MagickPixelPacket, library
from .compat import binary, text
from .resource import Resource
from .version import QUANTUM_DEPTH

__all__ = 'Color', 'scale_quantum_to_int8'


class Color(Resource):
    """Color value.

    Unlike any other objects in Wand, its resource management can be
    implicit when it used outside of :keyword:`with` block. In these case,
    its resource are allocated for every operation which requires a resource
    and destroyed immediately. Of course it is inefficient when the
    operations are much, so to avoid it, you should use color objects
    inside of :keyword:`with` block explicitly e.g.::

        red_count = 0
        with Color('#f00') as red:
            with Image(filename='image.png') as img:
                for row in img:
                    for col in row:
                        if col == red:
                            red_count += 1

    :param string: a color namel string e.g. ``'rgb(255, 255, 255)'``,
                   ``'#fff'``, ``'white'``. see `ImageMagick Color Names`_
                   doc also
    :type string: :class:`basestring`

    .. versionchanged:: 0.3.0
       :class:`Color` objects become hashable.

    .. seealso::

       `ImageMagick Color Names`_
          The color can then be given as a color name (there is a limited
          but large set of these; see below) or it can be given as a set
          of numbers (in decimal or hexadecimal), each corresponding to
          a channel in an RGB or RGBA color model. HSL, HSLA, HSB, HSBA,
          CMYK, or CMYKA color models may also be specified. These topics
          are briefly described in the sections below.

    .. _ImageMagick Color Names: http://www.imagemagick.org/script/color.php

    .. describe:: == (other)

       Equality operator.

       :param other: a color another one
       :type color: :class:`Color`
       :returns: ``True`` only if two images equal.
       :rtype: :class:`bool`

    """

    c_is_resource = library.IsPixelWand
    c_destroy_resource = library.DestroyPixelWand
    c_get_exception = library.PixelGetException
    c_clear_exception = library.PixelClearException

    __slots__ = 'raw', 'c_resource', 'allocated'

    def __init__(self, string=None, raw=None):
        if (string is None and raw is None or
                string is not None and raw is not None):
            raise TypeError('expected one argument')

        self.allocated = 0
        if raw is None:
            self.raw = ctypes.create_string_buffer(
                ctypes.sizeof(MagickPixelPacket)
            )
            with self:
                library.PixelSetColor(self.resource, binary(string))
                library.PixelGetMagickColor(self.resource, self.raw)
        else:
            self.raw = raw

    def __getinitargs__(self):
        return self.string, None

    def __enter__(self):
        if not self.allocated:
            with self.allocate():
                self.resource = library.NewPixelWand()
                library.PixelSetMagickColor(self.resource, self.raw)
        self.allocated += 1
        return Resource.__enter__(self)

    def __exit__(self, type, value, traceback):
        self.allocated -= 1
        if not self.allocated:
            Resource.__exit__(self, type, value, traceback)

    @property
    def string(self):
        """(:class:`basestring`) The string representation of the color."""
        with self:
            color_string = library.PixelGetColorAsString(self.resource)
            return text(color_string.value)

    @property
    def normalized_string(self):
        """(:class:`basestring`) The normalized string representation of
        the color.  The same color is always represented to the same
        string.

        .. versionadded:: 0.3.0

        """
        with self:
            string = library.PixelGetColorAsNormalizedString(self.resource)
            return text(string.value)

    @staticmethod
    def c_equals(a, b):
        """Raw level version of equality test function for two pixels.

        :param a: a pointer to PixelWand to compare
        :type a: :class:`ctypes.c_void_p`
        :param b: a pointer to PixelWand to compare
        :type b: :class:`ctypes.c_void_p`
        :returns: ``True`` only if two pixels equal
        :rtype: :class:`bool`

        .. note::

           It's only for internal use. Don't use it directly.
           Use ``==`` operator of :class:`Color` instead.

        """
        alpha = library.PixelGetAlpha
        return bool(library.IsPixelWandSimilar(a, b, 0) and
                    alpha(a) == alpha(b))

    def __eq__(self, other):
        if not isinstance(other, Color):
            return False
        with self as this:
            with other:
                return self.c_equals(this.resource, other.resource)

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        if self.alpha:
            return hash(self.normalized_string)
        return hash(None)

    @property
    def red(self):
        """(:class:`numbers.Real`) Red, from 0.0 to 1.0."""
        with self:
            return library.PixelGetRed(self.resource)

    @property
    def green(self):
        """(:class:`numbers.Real`) Green, from 0.0 to 1.0."""
        with self:
            return library.PixelGetGreen(self.resource)

    @property
    def blue(self):
        """(:class:`numbers.Real`) Blue, from 0.0 to 1.0."""
        with self:
            return library.PixelGetBlue(self.resource)

    @property
    def alpha(self):
        """(:class:`numbers.Real`) Alpha value, from 0.0 to 1.0."""
        with self:
            return library.PixelGetAlpha(self.resource)

    @property
    def red_quantum(self):
        """(:class:`numbers.Integral`) Red.
        Scale depends on :const:`~wand.version.QUANTUM_DEPTH`.

        .. versionadded:: 0.3.0

        """
        with self:
            return library.PixelGetRedQuantum(self.resource)

    @property
    def green_quantum(self):
        """(:class:`numbers.Integral`) Green.
        Scale depends on :const:`~wand.version.QUANTUM_DEPTH`.

        .. versionadded:: 0.3.0

        """
        with self:
            return library.PixelGetGreenQuantum(self.resource)

    @property
    def blue_quantum(self):
        """(:class:`numbers.Integral`) Blue.
        Scale depends on :const:`~wand.version.QUANTUM_DEPTH`.

        .. versionadded:: 0.3.0

        """
        with self:
            return library.PixelGetBlueQuantum(self.resource)

    @property
    def alpha_quantum(self):
        """(:class:`numbers.Integral`) Alpha value.
        Scale depends on :const:`~wand.version.QUANTUM_DEPTH`.

        .. versionadded:: 0.3.0

        """
        with self:
            return library.PixelGetAlphaQuantum(self.resource)

    @property
    def red_int8(self):
        """(:class:`numbers.Integral`) Red as 8bit integer which is a common
        style.  From 0 to 255.

        .. versionadded:: 0.3.0

        """
        return scale_quantum_to_int8(self.red_quantum)

    @property
    def green_int8(self):
        """(:class:`numbers.Integral`) Green as 8bit integer which is
        a common style.  From 0 to 255.

        .. versionadded:: 0.3.0

        """
        return scale_quantum_to_int8(self.green_quantum)

    @property
    def blue_int8(self):
        """(:class:`numbers.Integral`) Blue as 8bit integer which is
        a common style.  From 0 to 255.

        .. versionadded:: 0.3.0

        """
        return scale_quantum_to_int8(self.blue_quantum)

    @property
    def alpha_int8(self):
        """(:class:`numbers.Integral`) Alpha value as 8bit integer which is
        a common style.  From 0 to 255.

        .. versionadded:: 0.3.0

        """
        return scale_quantum_to_int8(self.alpha_quantum)

    def __str__(self):
        return self.string

    def __repr__(self):
        c = type(self)
        return '{0}.{1}({2!r})'.format(c.__module__, c.__name__, self.string)

    def _repr_html_(self):
        html = """
        <span style="background-color:#{red:02X}{green:02X}{blue:02X};
                     display:inline-block;
                     line-height:1em;
                     width:1em;">&nbsp;</span>
        <strong>#{red:02X}{green:02X}{blue:02X}</strong>
        """
        return html.format(red=self.red_int8,
                           green=self.green_int8,
                           blue=self.blue_int8)


def scale_quantum_to_int8(quantum):
    """Straightforward port of :c:func:`ScaleQuantumToChar()` inline
    function.

    :param quantum: quantum value
    :type quantum: :class:`numbers.Integral`
    :returns: 8bit integer of the given ``quantum`` value
    :rtype: :class:`numbers.Integral`

    .. versionadded:: 0.3.0

    """
    if quantum <= 0:
        return 0
    table = {8: 1, 16: 257.0, 32: 16843009.0, 64: 72340172838076673.0}
    v = quantum / table[QUANTUM_DEPTH]
    if v >= 255:
        return 255
    return int(v + 0.5)
