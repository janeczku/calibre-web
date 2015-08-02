# orm/instrumentation.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Defines SQLAlchemy's system of class instrumentation.

This module is usually not directly visible to user applications, but
defines a large part of the ORM's interactivity.

instrumentation.py deals with registration of end-user classes
for state tracking.   It interacts closely with state.py
and attributes.py which establish per-instance and per-class-attribute
instrumentation, respectively.

The class instrumentation system can be customized on a per-class
or global basis using the :mod:`sqlalchemy.ext.instrumentation`
module, which provides the means to build and specify
alternate instrumentation forms.

.. versionchanged: 0.8
   The instrumentation extension system was moved out of the
   ORM and into the external :mod:`sqlalchemy.ext.instrumentation`
   package.  When that package is imported, it installs
   itself within sqlalchemy.orm so that its more comprehensive
   resolution mechanics take effect.

"""


from . import exc, collections, events, interfaces
from operator import attrgetter
from .. import event, util
state = util.importlater("sqlalchemy.orm", "state")


class ClassManager(dict):
    """tracks state information at the class level."""

    MANAGER_ATTR = '_sa_class_manager'
    STATE_ATTR = '_sa_instance_state'

    deferred_scalar_loader = None

    original_init = object.__init__

    factory = None

    def __init__(self, class_):
        self.class_ = class_
        self.info = {}
        self.new_init = None
        self.local_attrs = {}
        self.originals = {}

        self._bases = [mgr for mgr in [
                        manager_of_class(base)
                        for base in self.class_.__bases__
                        if isinstance(base, type)
                 ] if mgr is not None]

        for base in self._bases:
            self.update(base)

        events._InstanceEventsHold.populate(class_, self)

        for basecls in class_.__mro__:
            mgr = manager_of_class(basecls)
            if mgr is not None:
                self.dispatch._update(mgr.dispatch)
        self.manage()
        self._instrument_init()

        if '__del__' in class_.__dict__:
            util.warn("__del__() method on class %s will "
                        "cause unreachable cycles and memory leaks, "
                        "as SQLAlchemy instrumentation often creates "
                        "reference cycles.  Please remove this method." %
                        class_)

    dispatch = event.dispatcher(events.InstanceEvents)

    @property
    def is_mapped(self):
        return 'mapper' in self.__dict__

    @util.memoized_property
    def mapper(self):
        # raises unless self.mapper has been assigned
        raise exc.UnmappedClassError(self.class_)

    def _all_sqla_attributes(self, exclude=None):
        """return an iterator of all classbound attributes that are
        implement :class:`._InspectionAttr`.

        This includes :class:`.QueryableAttribute` as well as extension
        types such as :class:`.hybrid_property` and :class:`.AssociationProxy`.

        """
        if exclude is None:
            exclude = set()
        for supercls in self.class_.__mro__:
            for key in set(supercls.__dict__).difference(exclude):
                exclude.add(key)
                val = supercls.__dict__[key]
                if isinstance(val, interfaces._InspectionAttr):
                    yield key, val


    def _attr_has_impl(self, key):
        """Return True if the given attribute is fully initialized.

        i.e. has an impl.
        """

        return key in self and self[key].impl is not None

    def _subclass_manager(self, cls):
        """Create a new ClassManager for a subclass of this ClassManager's
        class.

        This is called automatically when attributes are instrumented so that
        the attributes can be propagated to subclasses against their own
        class-local manager, without the need for mappers etc. to have already
        pre-configured managers for the full class hierarchy.   Mappers
        can post-configure the auto-generated ClassManager when needed.

        """
        manager = manager_of_class(cls)
        if manager is None:
            manager = _instrumentation_factory.create_manager_for_cls(cls)
        return manager

    def _instrument_init(self):
        # TODO: self.class_.__init__ is often the already-instrumented
        # __init__ from an instrumented superclass.  We still need to make
        # our own wrapper, but it would
        # be nice to wrap the original __init__ and not our existing wrapper
        # of such, since this adds method overhead.
        self.original_init = self.class_.__init__
        self.new_init = _generate_init(self.class_, self)
        self.install_member('__init__', self.new_init)

    def _uninstrument_init(self):
        if self.new_init:
            self.uninstall_member('__init__')
            self.new_init = None

    @util.memoized_property
    def _state_constructor(self):
        self.dispatch.first_init(self, self.class_)
        return state.InstanceState

    def manage(self):
        """Mark this instance as the manager for its class."""

        setattr(self.class_, self.MANAGER_ATTR, self)

    def dispose(self):
        """Dissasociate this manager from its class."""

        delattr(self.class_, self.MANAGER_ATTR)

    @util.hybridmethod
    def manager_getter(self):
        def manager_of_class(cls):
            return cls.__dict__.get(ClassManager.MANAGER_ATTR, None)
        return manager_of_class

    @util.hybridmethod
    def state_getter(self):
        """Return a (instance) -> InstanceState callable.

        "state getter" callables should raise either KeyError or
        AttributeError if no InstanceState could be found for the
        instance.
        """

        return attrgetter(self.STATE_ATTR)

    @util.hybridmethod
    def dict_getter(self):
        return attrgetter('__dict__')

    def instrument_attribute(self, key, inst, propagated=False):
        if propagated:
            if key in self.local_attrs:
                return  # don't override local attr with inherited attr
        else:
            self.local_attrs[key] = inst
            self.install_descriptor(key, inst)
        self[key] = inst

        for cls in self.class_.__subclasses__():
            manager = self._subclass_manager(cls)
            manager.instrument_attribute(key, inst, True)

    def subclass_managers(self, recursive):
        for cls in self.class_.__subclasses__():
            mgr = manager_of_class(cls)
            if mgr is not None and mgr is not self:
                yield mgr
                if recursive:
                    for m in mgr.subclass_managers(True):
                        yield m

    def post_configure_attribute(self, key):
        _instrumentation_factory.dispatch.\
                attribute_instrument(self.class_, key, self[key])

    def uninstrument_attribute(self, key, propagated=False):
        if key not in self:
            return
        if propagated:
            if key in self.local_attrs:
                return  # don't get rid of local attr
        else:
            del self.local_attrs[key]
            self.uninstall_descriptor(key)
        del self[key]
        for cls in self.class_.__subclasses__():
            manager = manager_of_class(cls)
            if manager:
                manager.uninstrument_attribute(key, True)

    def unregister(self):
        """remove all instrumentation established by this ClassManager."""

        self._uninstrument_init()

        self.mapper = self.dispatch = None
        self.info.clear()

        for key in list(self):
            if key in self.local_attrs:
                self.uninstrument_attribute(key)

    def install_descriptor(self, key, inst):
        if key in (self.STATE_ATTR, self.MANAGER_ATTR):
            raise KeyError("%r: requested attribute name conflicts with "
                           "instrumentation attribute of the same name." %
                           key)
        setattr(self.class_, key, inst)

    def uninstall_descriptor(self, key):
        delattr(self.class_, key)

    def install_member(self, key, implementation):
        if key in (self.STATE_ATTR, self.MANAGER_ATTR):
            raise KeyError("%r: requested attribute name conflicts with "
                           "instrumentation attribute of the same name." %
                           key)
        self.originals.setdefault(key, getattr(self.class_, key, None))
        setattr(self.class_, key, implementation)

    def uninstall_member(self, key):
        original = self.originals.pop(key, None)
        if original is not None:
            setattr(self.class_, key, original)

    def instrument_collection_class(self, key, collection_class):
        return collections.prepare_instrumentation(collection_class)

    def initialize_collection(self, key, state, factory):
        user_data = factory()
        adapter = collections.CollectionAdapter(
            self.get_impl(key), state, user_data)
        return adapter, user_data

    def is_instrumented(self, key, search=False):
        if search:
            return key in self
        else:
            return key in self.local_attrs

    def get_impl(self, key):
        return self[key].impl

    @property
    def attributes(self):
        return self.itervalues()

    ## InstanceState management

    def new_instance(self, state=None):
        instance = self.class_.__new__(self.class_)
        setattr(instance, self.STATE_ATTR,
                    state or self._state_constructor(instance, self))
        return instance

    def setup_instance(self, instance, state=None):
        setattr(instance, self.STATE_ATTR,
                    state or self._state_constructor(instance, self))

    def teardown_instance(self, instance):
        delattr(instance, self.STATE_ATTR)

    def _new_state_if_none(self, instance):
        """Install a default InstanceState if none is present.

        A private convenience method used by the __init__ decorator.

        """
        if hasattr(instance, self.STATE_ATTR):
            return False
        elif self.class_ is not instance.__class__ and \
                self.is_mapped:
            # this will create a new ClassManager for the
            # subclass, without a mapper.  This is likely a
            # user error situation but allow the object
            # to be constructed, so that it is usable
            # in a non-ORM context at least.
            return self._subclass_manager(instance.__class__).\
                        _new_state_if_none(instance)
        else:
            state = self._state_constructor(instance, self)
            setattr(instance, self.STATE_ATTR, state)
            return state

    def has_state(self, instance):
        return hasattr(instance, self.STATE_ATTR)

    def has_parent(self, state, key, optimistic=False):
        """TODO"""
        return self.get_impl(key).hasparent(state, optimistic=optimistic)

    def __nonzero__(self):
        """All ClassManagers are non-zero regardless of attribute state."""
        return True

    def __repr__(self):
        return '<%s of %r at %x>' % (
            self.__class__.__name__, self.class_, id(self))


class InstrumentationFactory(object):
    """Factory for new ClassManager instances."""

    dispatch = event.dispatcher(events.InstrumentationEvents)

    def create_manager_for_cls(self, class_):
        assert class_ is not None
        assert manager_of_class(class_) is None

        # give a more complicated subclass
        # a chance to do what it wants here
        manager, factory = self._locate_extended_factory(class_)

        if factory is None:
            factory = ClassManager
            manager = factory(class_)

        self._check_conflicts(class_, factory)

        manager.factory = factory

        self.dispatch.class_instrument(class_)
        return manager

    def _locate_extended_factory(self, class_):
        """Overridden by a subclass to do an extended lookup."""
        return None, None

    def _check_conflicts(self, class_, factory):
        """Overridden by a subclass to test for conflicting factories."""
        return

    def unregister(self, class_):
        manager = manager_of_class(class_)
        manager.unregister()
        manager.dispose()
        self.dispatch.class_uninstrument(class_)
        if ClassManager.MANAGER_ATTR in class_.__dict__:
            delattr(class_, ClassManager.MANAGER_ATTR)

# this attribute is replaced by sqlalchemy.ext.instrumentation
# when importred.
_instrumentation_factory = InstrumentationFactory()


def register_class(class_):
    """Register class instrumentation.

    Returns the existing or newly created class manager.

    """

    manager = manager_of_class(class_)
    if manager is None:
        manager = _instrumentation_factory.create_manager_for_cls(class_)
    return manager


def unregister_class(class_):
    """Unregister class instrumentation."""

    _instrumentation_factory.unregister(class_)


def is_instrumented(instance, key):
    """Return True if the given attribute on the given instance is
    instrumented by the attributes package.

    This function may be used regardless of instrumentation
    applied directly to the class, i.e. no descriptors are required.

    """
    return manager_of_class(instance.__class__).\
                        is_instrumented(key, search=True)

# these attributes are replaced by sqlalchemy.ext.instrumentation
# when a non-standard InstrumentationManager class is first
# used to instrument a class.
instance_state = _default_state_getter = ClassManager.state_getter()

instance_dict = _default_dict_getter = ClassManager.dict_getter()

manager_of_class = _default_manager_getter = ClassManager.manager_getter()


def _generate_init(class_, class_manager):
    """Build an __init__ decorator that triggers ClassManager events."""

    # TODO: we should use the ClassManager's notion of the
    # original '__init__' method, once ClassManager is fixed
    # to always reference that.
    original__init__ = class_.__init__
    assert original__init__

    # Go through some effort here and don't change the user's __init__
    # calling signature, including the unlikely case that it has
    # a return value.
    # FIXME: need to juggle local names to avoid constructor argument
    # clashes.
    func_body = """\
def __init__(%(apply_pos)s):
    new_state = class_manager._new_state_if_none(%(self_arg)s)
    if new_state:
        return new_state._initialize_instance(%(apply_kw)s)
    else:
        return original__init__(%(apply_kw)s)
"""
    func_vars = util.format_argspec_init(original__init__, grouped=False)
    func_text = func_body % func_vars

    # Py3K
    #func_defaults = getattr(original__init__, '__defaults__', None)
    #func_kw_defaults = getattr(original__init__, '__kwdefaults__', None)
    # Py2K
    func = getattr(original__init__, 'im_func', original__init__)
    func_defaults = getattr(func, 'func_defaults', None)
    # end Py2K

    env = locals().copy()
    exec func_text in env
    __init__ = env['__init__']
    __init__.__doc__ = original__init__.__doc__
    if func_defaults:
        __init__.func_defaults = func_defaults
    # Py3K
    #if func_kw_defaults:
    #    __init__.__kwdefaults__ = func_kw_defaults
    return __init__
