""":mod:`wand.exceptions` --- Errors and warnings
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This module maps MagickWand API's errors and warnings to Python's native
exceptions and warnings. You can catch all MagickWand errors using Python's
natural way to catch errors.

.. seealso::

   `ImageMagick Exceptions <http://www.imagemagick.org/script/exception.php>`_

.. versionadded:: 0.1.1

"""


class WandException(Exception):
    """All Wand-related exceptions are derived from this class."""


class WandWarning(WandException, Warning):
    """Base class for Wand-related warnings."""


class WandError(WandException):
    """Base class for Wand-related errors."""


class WandFatalError(WandException):
    """Base class for Wand-related fatal errors."""


class WandLibraryVersionError(WandException):
    """Base class for Wand-related ImageMagick version errors.

    .. versionadded:: 0.3.2

    """


#: (:class:`list`) A list of error/warning domains, these descriptions and
#: codes. The form of elements is like: (domain name, description, codes).
DOMAIN_MAP = [
    ('ResourceLimit',
     'A program resource is exhausted e.g. not enough memory.',
     (MemoryError,),
     [300, 400, 700]),
    ('Type', 'A font is unavailable; a substitution may have occurred.', (),
     [305, 405, 705]),
    ('Option', 'A command-line option was malformed.', (), [310, 410, 710]),
    ('Delegate', 'An ImageMagick delegate failed to complete.', (),
     [315, 415, 715]),
    ('MissingDelegate',
     'The image type can not be read or written because the appropriate; '
     'delegate is missing.',
     (ImportError,),
     [320, 420, 720]),
    ('CorruptImage', 'The image file may be corrupt.',
     (ValueError,), [325, 425, 725]),
    ('FileOpen', 'The image file could not be opened for reading or writing.',
     (IOError,), [330, 430, 730]),
    ('Blob', 'A binary large object could not be allocated, read, or written.',
     (IOError,), [335, 435, 735]),
    ('Stream', 'There was a problem reading or writing from a stream.',
     (IOError,), [340, 440, 740]),
    ('Cache', 'Pixels could not be read or written to the pixel cache.',
     (), [345, 445, 745]),
    ('Coder', 'There was a problem with an image coder.', (), [350, 450, 750]),
    ('Module', 'There was a problem with an image module.', (),
     [355, 455, 755]),
    ('Draw', 'A drawing operation failed.', (), [360, 460, 760]),
    ('Image', 'The operation could not complete due to an incompatible image.',
     (), [365, 465, 765]),
    ('Wand', 'There was a problem specific to the MagickWand API.', (),
     [370, 470, 770]),
    ('Random', 'There is a problem generating a true or pseudo-random number.',
     (), [375, 475, 775]),
    ('XServer', 'An X resource is unavailable.', (), [380, 480, 780]),
    ('Monitor', 'There was a problem activating the progress monitor.', (),
     [385, 485, 785]),
    ('Registry', 'There was a problem getting or setting the registry.', (),
     [390, 490, 790]),
    ('Configure', 'There was a problem getting a configuration file.', (),
     [395, 495, 795]),
    ('Policy',
     'A policy denies access to a delegate, coder, filter, path, or resource.',
     (), [399, 499, 799])
]


#: (:class:`list`) The list of (base_class, suffix) pairs (for each code).
#: It would be zipped with :const:`DOMAIN_MAP` pairs' last element.
CODE_MAP = [
    (WandWarning, 'Warning'),
    (WandError, 'Error'),
    (WandFatalError, 'FatalError')
]


#: (:class:`dict`) The dictionary of (code, exc_type).
TYPE_MAP = {}


for domain, description, bases, codes in DOMAIN_MAP:
    for code, (base, suffix) in zip(codes, CODE_MAP):
        name = domain + suffix
        locals()[name] = TYPE_MAP[code] = type(name, (base,) + bases, {
            '__doc__': description,
            'wand_error_code': code
        })
del name, base, suffix
