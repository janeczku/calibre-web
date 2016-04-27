""":mod:`wand.resource` --- Global resource management
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

There is the global resource to manage in MagickWand API. This module
implements automatic global resource management through reference counting.

"""
import contextlib
import ctypes
import warnings

from .api import library
from .compat import string_type
from .exceptions import TYPE_MAP, WandException


__all__ = ('genesis', 'terminus', 'increment_refcount', 'decrement_refcount',
           'Resource', 'DestroyedResourceError')


def genesis():
    """Instantiates the MagickWand API.

    .. warning::

       Don't call this function directly. Use :func:`increment_refcount()` and
       :func:`decrement_refcount()` functions instead.

    """
    library.MagickWandGenesis()


def terminus():
    """Cleans up the MagickWand API.

    .. warning::

       Don't call this function directly. Use :func:`increment_refcount()` and
       :func:`decrement_refcount()` functions instead.

    """
    library.MagickWandTerminus()


#: (:class:`numbers.Integral`) The internal integer value that maintains
#: the number of referenced objects.
#:
#: .. warning::
#:
#:    Don't touch this global variable. Use :func:`increment_refcount()` and
#:    :func:`decrement_refcount()` functions instead.
#:
reference_count = 0


def increment_refcount():
    """Increments the :data:`reference_count` and instantiates the MagickWand
    API if it is the first use.

    """
    global reference_count
    if reference_count:
        reference_count += 1
    else:
        genesis()
        reference_count = 1


def decrement_refcount():
    """Decrements the :data:`reference_count` and cleans up the MagickWand
    API if it will be no more used.

    """
    global reference_count
    if not reference_count:
        raise RuntimeError('wand.resource.reference_count is already zero')
    reference_count -= 1
    if not reference_count:
        terminus()


class Resource(object):
    """Abstract base class for MagickWand object that requires resource
    management. Its all subclasses manage the resource semiautomatically
    and support :keyword:`with` statement as well::

        with Resource() as resource:
            # use the resource...
            pass

    It doesn't implement constructor by itself, so subclasses should
    implement it. Every constructor should assign the pointer of its
    resource data into :attr:`resource` attribute inside of :keyword:`with`
    :meth:`allocate()` context.  For example::

        class Pizza(Resource):
            '''My pizza yummy.'''

            def __init__(self):
                with self.allocate():
                    self.resource = library.NewPizza()

    .. versionadded:: 0.1.2

    """

    #: (:class:`ctypes.CFUNCTYPE`) The :mod:`ctypes` predicate function
    #: that returns whether the given pointer (that contains a resource data
    #: usuaully) is a valid resource.
    #:
    #: .. note::
    #:
    #:    It is an abstract attribute that has to be implemented
    #:    in the subclass.
    c_is_resource = NotImplemented

    #: (:class:`ctypes.CFUNCTYPE`) The :mod:`ctypes` function that destroys
    #: the :attr:`resource`.
    #:
    #: .. note::
    #:
    #:    It is an abstract attribute that has to be implemented
    #:    in the subclass.
    c_destroy_resource = NotImplemented

    #: (:class:`ctypes.CFUNCTYPE`) The :mod:`ctypes` function that gets
    #: an exception from the :attr:`resource`.
    #:
    #: .. note::
    #:
    #:    It is an abstract attribute that has to be implemented
    #:    in the subclass.
    c_get_exception = NotImplemented

    #: (:class:`ctypes.CFUNCTYPE`) The :mod:`ctypes` function that clears
    #: an exception of the :attr:`resource`.
    #:
    #: .. note::
    #:
    #:    It is an abstract attribute that has to be implemented
    #:    in the subclass.
    c_clear_exception = NotImplemented

    @property
    def resource(self):
        """Internal pointer to the resource instance. It may raise
        :exc:`DestroyedResourceError` when the resource has destroyed already.

        """
        if getattr(self, 'c_resource', None) is None:
            raise DestroyedResourceError(repr(self) + ' is destroyed already')
        return self.c_resource

    @resource.setter
    def resource(self, resource):
        # Delete the existing resource if there is one
        if getattr(self, 'c_resource', None):
            self.destroy()

        if self.c_is_resource(resource):
            self.c_resource = resource
        else:
            raise TypeError(repr(resource) + ' is an invalid resource')
        increment_refcount()

    @resource.deleter
    def resource(self):
        self.c_destroy_resource(self.resource)
        self.c_resource = None

    @contextlib.contextmanager
    def allocate(self):
        """Allocates the memory for the resource explicitly. Its subclasses
        should assign the created resource into :attr:`resource` attribute
        inside of this context. For example::

            with resource.allocate():
                resource.resource = library.NewResource()

        """
        increment_refcount()
        try:
            yield self
        except:
            decrement_refcount()
            raise

    def destroy(self):
        """Cleans up the resource explicitly. If you use the resource in
        :keyword:`with` statement, it was called implicitly so have not to
        call it.

        """
        del self.resource
        decrement_refcount()

    def get_exception(self):
        """Gets a current exception instance.

        :returns: a current exception. it can be ``None`` as well if any
                  errors aren't occurred
        :rtype: :class:`wand.exceptions.WandException`

        """
        severity = ctypes.c_int()
        desc = self.c_get_exception(self.resource, ctypes.byref(severity))
        if severity.value == 0:
            return
        self.c_clear_exception(self.wand)
        exc_cls = TYPE_MAP[severity.value]
        message = desc.value
        if not isinstance(message, string_type):
            message = message.decode(errors='replace')
        return exc_cls(message)

    def raise_exception(self, stacklevel=1):
        """Raises an exception or warning if it has occurred."""
        e = self.get_exception()
        if isinstance(e, Warning):
            warnings.warn(e, stacklevel=stacklevel + 1)
        elif isinstance(e, Exception):
            raise e

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.destroy()

    def __del__(self):
        try:
            self.destroy()
        except DestroyedResourceError:
            pass


class DestroyedResourceError(WandException, ReferenceError, AttributeError):
    """An error that rises when some code tries access to an already
    destroyed resource.

    .. versionchanged:: 0.3.0
       It becomes a subtype of :exc:`wand.exceptions.WandException`.

    """
