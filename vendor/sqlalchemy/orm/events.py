# orm/events.py
# Copyright (C) 2005-2013 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""ORM event interfaces.

"""
from .. import event, exc, util
orm = util.importlater("sqlalchemy", "orm")
import inspect
import weakref


class InstrumentationEvents(event.Events):
    """Events related to class instrumentation events.

    The listeners here support being established against
    any new style class, that is any object that is a subclass
    of 'type'.  Events will then be fired off for events
    against that class.  If the "propagate=True" flag is passed
    to event.listen(), the event will fire off for subclasses
    of that class as well.

    The Python ``type`` builtin is also accepted as a target,
    which when used has the effect of events being emitted
    for all classes.

    Note the "propagate" flag here is defaulted to ``True``,
    unlike the other class level events where it defaults
    to ``False``.  This means that new subclasses will also
    be the subject of these events, when a listener
    is established on a superclass.

    .. versionchanged:: 0.8 - events here will emit based
       on comparing the incoming class to the type of class
       passed to :func:`.event.listen`.  Previously, the
       event would fire for any class unconditionally regardless
       of what class was sent for listening, despite
       documentation which stated the contrary.

    """

    @classmethod
    def _accept_with(cls, target):
        # TODO: there's no coverage for this
        if isinstance(target, type):
            return _InstrumentationEventsHold(target)
        else:
            return None

    @classmethod
    def _listen(cls, target, identifier, fn, propagate=True):

        def listen(target_cls, *arg):
            listen_cls = target()
            if propagate and issubclass(target_cls, listen_cls):
                return fn(target_cls, *arg)
            elif not propagate and target_cls is listen_cls:
                return fn(target_cls, *arg)

        def remove(ref):
            event.Events._remove(orm.instrumentation._instrumentation_factory,
                                            identifier, listen)

        target = weakref.ref(target.class_, remove)
        event.Events._listen(orm.instrumentation._instrumentation_factory,
                        identifier, listen)

    @classmethod
    def _remove(cls, identifier, target, fn):
        raise NotImplementedError("Removal of instrumentation events "
                                    "not yet implemented")

    @classmethod
    def _clear(cls):
        super(InstrumentationEvents, cls)._clear()
        orm.instrumentation._instrumentation_factory.dispatch._clear()

    def class_instrument(self, cls):
        """Called after the given class is instrumented.

        To get at the :class:`.ClassManager`, use
        :func:`.manager_of_class`.

        """

    def class_uninstrument(self, cls):
        """Called before the given class is uninstrumented.

        To get at the :class:`.ClassManager`, use
        :func:`.manager_of_class`.

        """

    def attribute_instrument(self, cls, key, inst):
        """Called when an attribute is instrumented."""


class _InstrumentationEventsHold(object):
    """temporary marker object used to transfer from _accept_with() to
    _listen() on the InstrumentationEvents class.

    """
    def __init__(self, class_):
        self.class_ = class_

    dispatch = event.dispatcher(InstrumentationEvents)


class InstanceEvents(event.Events):
    """Define events specific to object lifecycle.

    e.g.::

        from sqlalchemy import event

        def my_load_listener(target, context):
            print "on load!"

        event.listen(SomeClass, 'load', my_load_listener)

    Available targets include:

    * mapped classes
    * unmapped superclasses of mapped or to-be-mapped classes
      (using the ``propagate=True`` flag)
    * :class:`.Mapper` objects
    * the :class:`.Mapper` class itself and the :func:`.mapper`
      function indicate listening for all mappers.

    .. versionchanged:: 0.8.0 instance events can be associated with
       unmapped superclasses of mapped classes.

    Instance events are closely related to mapper events, but
    are more specific to the instance and its instrumentation,
    rather than its system of persistence.

    When using :class:`.InstanceEvents`, several modifiers are
    available to the :func:`.event.listen` function.

    :param propagate=False: When True, the event listener should
       be applied to all inheriting classes as well as the
       class which is the target of this listener.
    :param raw=False: When True, the "target" argument passed
       to applicable event listener functions will be the
       instance's :class:`.InstanceState` management
       object, rather than the mapped instance itself.

    """
    @classmethod
    def _accept_with(cls, target):
        if isinstance(target, orm.instrumentation.ClassManager):
            return target
        elif isinstance(target, orm.Mapper):
            return target.class_manager
        elif target is orm.mapper:
            return orm.instrumentation.ClassManager
        elif isinstance(target, type):
            if issubclass(target, orm.Mapper):
                return orm.instrumentation.ClassManager
            else:
                manager = orm.instrumentation.manager_of_class(target)
                if manager:
                    return manager
                else:
                    return _InstanceEventsHold(target)
        return None

    @classmethod
    def _listen(cls, target, identifier, fn, raw=False, propagate=False):
        if not raw:
            orig_fn = fn

            def wrap(state, *arg, **kw):
                return orig_fn(state.obj(), *arg, **kw)
            fn = wrap

        event.Events._listen(target, identifier, fn, propagate=propagate)
        if propagate:
            for mgr in target.subclass_managers(True):
                event.Events._listen(mgr, identifier, fn, True)

    @classmethod
    def _remove(cls, identifier, target, fn):
        msg = "Removal of instance events not yet implemented"
        raise NotImplementedError(msg)

    @classmethod
    def _clear(cls):
        super(InstanceEvents, cls)._clear()
        _InstanceEventsHold._clear()

    def first_init(self, manager, cls):
        """Called when the first instance of a particular mapping is called.

        """

    def init(self, target, args, kwargs):
        """Receive an instance when it's constructor is called.

        This method is only called during a userland construction of
        an object.  It is not called when an object is loaded from the
        database.

        """

    def init_failure(self, target, args, kwargs):
        """Receive an instance when it's constructor has been called,
        and raised an exception.

        This method is only called during a userland construction of
        an object.  It is not called when an object is loaded from the
        database.

        """

    def load(self, target, context):
        """Receive an object instance after it has been created via
        ``__new__``, and after initial attribute population has
        occurred.

        This typically occurs when the instance is created based on
        incoming result rows, and is only called once for that
        instance's lifetime.

        Note that during a result-row load, this method is called upon
        the first row received for this instance.  Note that some
        attributes and collections may or may not be loaded or even
        initialized, depending on what's present in the result rows.

        :param target: the mapped instance.  If
         the event is configured with ``raw=True``, this will
         instead be the :class:`.InstanceState` state-management
         object associated with the instance.
        :param context: the :class:`.QueryContext` corresponding to the
         current :class:`.Query` in progress.  This argument may be
         ``None`` if the load does not correspond to a :class:`.Query`,
         such as during :meth:`.Session.merge`.

        """

    def refresh(self, target, context, attrs):
        """Receive an object instance after one or more attributes have
        been refreshed from a query.

        :param target: the mapped instance.  If
         the event is configured with ``raw=True``, this will
         instead be the :class:`.InstanceState` state-management
         object associated with the instance.
        :param context: the :class:`.QueryContext` corresponding to the
         current :class:`.Query` in progress.
        :param attrs: iterable collection of attribute names which
         were populated, or None if all column-mapped, non-deferred
         attributes were populated.

        """

    def expire(self, target, attrs):
        """Receive an object instance after its attributes or some subset
        have been expired.

        'keys' is a list of attribute names.  If None, the entire
        state was expired.

        :param target: the mapped instance.  If
         the event is configured with ``raw=True``, this will
         instead be the :class:`.InstanceState` state-management
         object associated with the instance.
        :param attrs: iterable collection of attribute
         names which were expired, or None if all attributes were
         expired.

        """

    def resurrect(self, target):
        """Receive an object instance as it is 'resurrected' from
        garbage collection, which occurs when a "dirty" state falls
        out of scope.

        :param target: the mapped instance.  If
         the event is configured with ``raw=True``, this will
         instead be the :class:`.InstanceState` state-management
         object associated with the instance.

        """

    def pickle(self, target, state_dict):
        """Receive an object instance when its associated state is
        being pickled.

        :param target: the mapped instance.  If
         the event is configured with ``raw=True``, this will
         instead be the :class:`.InstanceState` state-management
         object associated with the instance.
        :param state_dict: the dictionary returned by
         :class:`.InstanceState.__getstate__`, containing the state
         to be pickled.

        """

    def unpickle(self, target, state_dict):
        """Receive an object instance after it's associated state has
        been unpickled.

        :param target: the mapped instance.  If
         the event is configured with ``raw=True``, this will
         instead be the :class:`.InstanceState` state-management
         object associated with the instance.
        :param state_dict: the dictionary sent to
         :class:`.InstanceState.__setstate__`, containing the state
         dictionary which was pickled.

        """


class _EventsHold(object):
    """Hold onto listeners against unmapped, uninstrumented classes.

    Establish _listen() for that class' mapper/instrumentation when
    those objects are created for that class.

    """
    def __init__(self, class_):
        self.class_ = class_

    @classmethod
    def _clear(cls):
        cls.all_holds.clear()

    class HoldEvents(object):
        @classmethod
        def _listen(cls, target, identifier, fn, raw=False, propagate=False):
            if target.class_ in target.all_holds:
                collection = target.all_holds[target.class_]
            else:
                collection = target.all_holds[target.class_] = []

            collection.append((identifier, fn, raw, propagate))

            if propagate:
                stack = list(target.class_.__subclasses__())
                while stack:
                    subclass = stack.pop(0)
                    stack.extend(subclass.__subclasses__())
                    subject = target.resolve(subclass)
                    if subject is not None:
                        subject.dispatch._listen(subject, identifier, fn,
                                        raw=raw, propagate=propagate)

    @classmethod
    def populate(cls, class_, subject):
        for subclass in class_.__mro__:
            if subclass in cls.all_holds:
                collection = cls.all_holds[subclass]
                for ident, fn, raw, propagate in collection:
                    if propagate or subclass is class_:
                        # since we can't be sure in what order different classes
                        # in a hierarchy are triggered with populate(),
                        # we rely upon _EventsHold for all event
                        # assignment, instead of using the generic propagate
                        # flag.
                        subject.dispatch._listen(subject, ident,
                                                        fn, raw=raw,
                                                        propagate=False)


class _InstanceEventsHold(_EventsHold):
    all_holds = weakref.WeakKeyDictionary()

    def resolve(self, class_):
        return orm.instrumentation.manager_of_class(class_)

    class HoldInstanceEvents(_EventsHold.HoldEvents, InstanceEvents):
        pass

    dispatch = event.dispatcher(HoldInstanceEvents)


class MapperEvents(event.Events):
    """Define events specific to mappings.

    e.g.::

        from sqlalchemy import event

        def my_before_insert_listener(mapper, connection, target):
            # execute a stored procedure upon INSERT,
            # apply the value to the row to be inserted
            target.calculated_value = connection.scalar(
                                        "select my_special_function(%d)"
                                        % target.special_number)

        # associate the listener function with SomeClass,
        # to execute during the "before_insert" hook
        event.listen(
            SomeClass, 'before_insert', my_before_insert_listener)

    Available targets include:

    * mapped classes
    * unmapped superclasses of mapped or to-be-mapped classes
      (using the ``propagate=True`` flag)
    * :class:`.Mapper` objects
    * the :class:`.Mapper` class itself and the :func:`.mapper`
      function indicate listening for all mappers.

    .. versionchanged:: 0.8.0 mapper events can be associated with
       unmapped superclasses of mapped classes.

    Mapper events provide hooks into critical sections of the
    mapper, including those related to object instrumentation,
    object loading, and object persistence. In particular, the
    persistence methods :meth:`~.MapperEvents.before_insert`,
    and :meth:`~.MapperEvents.before_update` are popular
    places to augment the state being persisted - however, these
    methods operate with several significant restrictions. The
    user is encouraged to evaluate the
    :meth:`.SessionEvents.before_flush` and
    :meth:`.SessionEvents.after_flush` methods as more
    flexible and user-friendly hooks in which to apply
    additional database state during a flush.

    When using :class:`.MapperEvents`, several modifiers are
    available to the :func:`.event.listen` function.

    :param propagate=False: When True, the event listener should
       be applied to all inheriting mappers and/or the mappers of
       inheriting classes, as well as any
       mapper which is the target of this listener.
    :param raw=False: When True, the "target" argument passed
       to applicable event listener functions will be the
       instance's :class:`.InstanceState` management
       object, rather than the mapped instance itself.
    :param retval=False: when True, the user-defined event function
       must have a return value, the purpose of which is either to
       control subsequent event propagation, or to otherwise alter
       the operation in progress by the mapper.   Possible return
       values are:

       * ``sqlalchemy.orm.interfaces.EXT_CONTINUE`` - continue event
         processing normally.
       * ``sqlalchemy.orm.interfaces.EXT_STOP`` - cancel all subsequent
         event handlers in the chain.
       * other values - the return value specified by specific listeners,
         such as :meth:`~.MapperEvents.translate_row` or
         :meth:`~.MapperEvents.create_instance`.

    """

    @classmethod
    def _accept_with(cls, target):
        if target is orm.mapper:
            return orm.Mapper
        elif isinstance(target, type):
            if issubclass(target, orm.Mapper):
                return target
            else:
                mapper = orm.util._mapper_or_none(target)
                if mapper is not None:
                    return mapper
                else:
                    return _MapperEventsHold(target)
        else:
            return target

    @classmethod
    def _listen(cls, target, identifier, fn,
                            raw=False, retval=False, propagate=False):

        if not raw or not retval:
            if not raw:
                meth = getattr(cls, identifier)
                try:
                    target_index = \
                        inspect.getargspec(meth)[0].index('target') - 1
                except ValueError:
                    target_index = None

            wrapped_fn = fn

            def wrap(*arg, **kw):
                if not raw and target_index is not None:
                    arg = list(arg)
                    arg[target_index] = arg[target_index].obj()
                if not retval:
                    wrapped_fn(*arg, **kw)
                    return orm.interfaces.EXT_CONTINUE
                else:
                    return wrapped_fn(*arg, **kw)
            fn = wrap

        if propagate:
            for mapper in target.self_and_descendants:
                event.Events._listen(mapper, identifier, fn, propagate=True)
        else:
            event.Events._listen(target, identifier, fn)

    @classmethod
    def _clear(cls):
        super(MapperEvents, cls)._clear()
        _MapperEventsHold._clear()

    def instrument_class(self, mapper, class_):
        """Receive a class when the mapper is first constructed,
        before instrumentation is applied to the mapped class.

        This event is the earliest phase of mapper construction.
        Most attributes of the mapper are not yet initialized.

        This listener can either be applied to the :class:`.Mapper`
        class overall, or to any un-mapped class which serves as a base
        for classes that will be mapped (using the ``propagate=True`` flag)::

            Base = declarative_base()

            @event.listens_for(Base, "instrument_class", propagate=True)
            def on_new_class(mapper, cls_):
                " ... "

        :param mapper: the :class:`.Mapper` which is the target
         of this event.
        :param class\_: the mapped class.

        """

    def mapper_configured(self, mapper, class_):
        """Called when the mapper for the class is fully configured.

        This event is the latest phase of mapper construction, and
        is invoked when the mapped classes are first used, so that
        relationships between mappers can be resolved.   When the event is
        called, the mapper should be in its final state.

        While the configuration event normally occurs automatically,
        it can be forced to occur ahead of time, in the case where the event
        is needed before any actual mapper usage,  by using the
        :func:`.configure_mappers` function.


        :param mapper: the :class:`.Mapper` which is the target
         of this event.
        :param class\_: the mapped class.

        """
        # TODO: need coverage for this event

    def after_configured(self):
        """Called after a series of mappers have been configured.

        This corresponds to the :func:`.orm.configure_mappers` call, which
        note is usually called automatically as mappings are first
        used.

        Theoretically this event is called once per
        application, but is actually called any time new mappers
        have been affected by a :func:`.orm.configure_mappers`
        call.   If new mappings are constructed after existing ones have
        already been used, this event can be called again.

        """

    def translate_row(self, mapper, context, row):
        """Perform pre-processing on the given result row and return a
        new row instance.

        This listener is typically registered with ``retval=True``.
        It is called when the mapper first receives a row, before
        the object identity or the instance itself has been derived
        from that row.   The given row may or may not be a
        :class:`.RowProxy` object - it will always be a dictionary-like
        object which contains mapped columns as keys.  The
        returned object should also be a dictionary-like object
        which recognizes mapped columns as keys.

        :param mapper: the :class:`.Mapper` which is the target
         of this event.
        :param context: the :class:`.QueryContext`, which includes
         a handle to the current :class:`.Query` in progress as well
         as additional state information.
        :param row: the result row being handled.  This may be
         an actual :class:`.RowProxy` or may be a dictionary containing
         :class:`.Column` objects as keys.
        :return: When configured with ``retval=True``, the function
         should return a dictionary-like row object, or ``EXT_CONTINUE``,
         indicating the original row should be used.


        """

    def create_instance(self, mapper, context, row, class_):
        """Receive a row when a new object instance is about to be
        created from that row.

        The method can choose to create the instance itself, or it can return
        EXT_CONTINUE to indicate normal object creation should take place.
        This listener is typically registered with ``retval=True``.

        :param mapper: the :class:`.Mapper` which is the target
         of this event.
        :param context: the :class:`.QueryContext`, which includes
         a handle to the current :class:`.Query` in progress as well
         as additional state information.
        :param row: the result row being handled.  This may be
         an actual :class:`.RowProxy` or may be a dictionary containing
         :class:`.Column` objects as keys.
        :param class\_: the mapped class.
        :return: When configured with ``retval=True``, the return value
         should be a newly created instance of the mapped class,
         or ``EXT_CONTINUE`` indicating that default object construction
         should take place.

        """

    def append_result(self, mapper, context, row, target,
                        result, **flags):
        """Receive an object instance before that instance is appended
        to a result list.

        This is a rarely used hook which can be used to alter
        the construction of a result list returned by :class:`.Query`.

        :param mapper: the :class:`.Mapper` which is the target
         of this event.
        :param context: the :class:`.QueryContext`, which includes
         a handle to the current :class:`.Query` in progress as well
         as additional state information.
        :param row: the result row being handled.  This may be
         an actual :class:`.RowProxy` or may be a dictionary containing
         :class:`.Column` objects as keys.
        :param target: the mapped instance being populated.  If
         the event is configured with ``raw=True``, this will
         instead be the :class:`.InstanceState` state-management
         object associated with the instance.
        :param result: a list-like object where results are being
         appended.
        :param \**flags: Additional state information about the
         current handling of the row.
        :return: If this method is registered with ``retval=True``,
         a return value of ``EXT_STOP`` will prevent the instance
         from being appended to the given result list, whereas a
         return value of ``EXT_CONTINUE`` will result in the default
         behavior of appending the value to the result list.

        """

    def populate_instance(self, mapper, context, row,
                            target, **flags):
        """Receive an instance before that instance has
        its attributes populated.

        This usually corresponds to a newly loaded instance but may
        also correspond to an already-loaded instance which has
        unloaded attributes to be populated.  The method may be called
        many times for a single instance, as multiple result rows are
        used to populate eagerly loaded collections.

        Most usages of this hook are obsolete.  For a
        generic "object has been newly created from a row" hook, use
        :meth:`.InstanceEvents.load`.

        :param mapper: the :class:`.Mapper` which is the target
         of this event.
        :param context: the :class:`.QueryContext`, which includes
         a handle to the current :class:`.Query` in progress as well
         as additional state information.
        :param row: the result row being handled.  This may be
         an actual :class:`.RowProxy` or may be a dictionary containing
         :class:`.Column` objects as keys.
        :param target: the mapped instance.  If
         the event is configured with ``raw=True``, this will
         instead be the :class:`.InstanceState` state-management
         object associated with the instance.
        :return: When configured with ``retval=True``, a return
         value of ``EXT_STOP`` will bypass instance population by
         the mapper. A value of ``EXT_CONTINUE`` indicates that
         default instance population should take place.

        """

    def before_insert(self, mapper, connection, target):
        """Receive an object instance before an INSERT statement
        is emitted corresponding to that instance.

        This event is used to modify local, non-object related
        attributes on the instance before an INSERT occurs, as well
        as to emit additional SQL statements on the given
        connection.

        The event is often called for a batch of objects of the
        same class before their INSERT statements are emitted at
        once in a later step. In the extremely rare case that
        this is not desirable, the :func:`.mapper` can be
        configured with ``batch=False``, which will cause
        batches of instances to be broken up into individual
        (and more poorly performing) event->persist->event
        steps.

        .. warning::
            Mapper-level flush events are designed to operate **on attributes
            local to the immediate object being handled
            and via SQL operations with the given**
            :class:`.Connection` **only.** Handlers here should **not** make
            alterations to the state of the :class:`.Session` overall, and
            in general should not affect any :func:`.relationship` -mapped
            attributes, as session cascade rules will not function properly,
            nor is it always known if the related class has already been
            handled. Operations that **are not supported in mapper
            events** include:

            * :meth:`.Session.add`
            * :meth:`.Session.delete`
            * Mapped collection append, add, remove, delete, discard, etc.
            * Mapped relationship attribute set/del events,
              i.e. ``someobject.related = someotherobject``

            Operations which manipulate the state of the object
            relative to other objects are better handled:

            * In the ``__init__()`` method of the mapped object itself, or
              another method designed to establish some particular state.
            * In a ``@validates`` handler, see :ref:`simple_validators`
            * Within the  :meth:`.SessionEvents.before_flush` event.

        :param mapper: the :class:`.Mapper` which is the target
         of this event.
        :param connection: the :class:`.Connection` being used to
         emit INSERT statements for this instance.  This
         provides a handle into the current transaction on the
         target database specific to this instance.
        :param target: the mapped instance being persisted.  If
         the event is configured with ``raw=True``, this will
         instead be the :class:`.InstanceState` state-management
         object associated with the instance.
        :return: No return value is supported by this event.

        """

    def after_insert(self, mapper, connection, target):
        """Receive an object instance after an INSERT statement
        is emitted corresponding to that instance.

        This event is used to modify in-Python-only
        state on the instance after an INSERT occurs, as well
        as to emit additional SQL statements on the given
        connection.

        The event is often called for a batch of objects of the
        same class after their INSERT statements have been
        emitted at once in a previous step. In the extremely
        rare case that this is not desirable, the
        :func:`.mapper` can be configured with ``batch=False``,
        which will cause batches of instances to be broken up
        into individual (and more poorly performing)
        event->persist->event steps.

        .. warning::
            Mapper-level flush events are designed to operate **on attributes
            local to the immediate object being handled
            and via SQL operations with the given**
            :class:`.Connection` **only.** Handlers here should **not** make
            alterations to the state of the :class:`.Session` overall, and in
            general should not affect any :func:`.relationship` -mapped
            attributes, as session cascade rules will not function properly,
            nor is it always known if the related class has already been
            handled. Operations that **are not supported in mapper
            events** include:

            * :meth:`.Session.add`
            * :meth:`.Session.delete`
            * Mapped collection append, add, remove, delete, discard, etc.
            * Mapped relationship attribute set/del events,
              i.e. ``someobject.related = someotherobject``

            Operations which manipulate the state of the object
            relative to other objects are better handled:

            * In the ``__init__()`` method of the mapped object itself,
              or another method designed to establish some particular state.
            * In a ``@validates`` handler, see :ref:`simple_validators`
            * Within the  :meth:`.SessionEvents.before_flush` event.

        :param mapper: the :class:`.Mapper` which is the target
         of this event.
        :param connection: the :class:`.Connection` being used to
         emit INSERT statements for this instance.  This
         provides a handle into the current transaction on the
         target database specific to this instance.
        :param target: the mapped instance being persisted.  If
         the event is configured with ``raw=True``, this will
         instead be the :class:`.InstanceState` state-management
         object associated with the instance.
        :return: No return value is supported by this event.

        """

    def before_update(self, mapper, connection, target):
        """Receive an object instance before an UPDATE statement
        is emitted corresponding to that instance.

        This event is used to modify local, non-object related
        attributes on the instance before an UPDATE occurs, as well
        as to emit additional SQL statements on the given
        connection.

        This method is called for all instances that are
        marked as "dirty", *even those which have no net changes
        to their column-based attributes*. An object is marked
        as dirty when any of its column-based attributes have a
        "set attribute" operation called or when any of its
        collections are modified. If, at update time, no
        column-based attributes have any net changes, no UPDATE
        statement will be issued. This means that an instance
        being sent to :meth:`~.MapperEvents.before_update` is
        *not* a guarantee that an UPDATE statement will be
        issued, although you can affect the outcome here by
        modifying attributes so that a net change in value does
        exist.

        To detect if the column-based attributes on the object have net
        changes, and will therefore generate an UPDATE statement, use
        ``object_session(instance).is_modified(instance,
        include_collections=False)``.

        The event is often called for a batch of objects of the
        same class before their UPDATE statements are emitted at
        once in a later step. In the extremely rare case that
        this is not desirable, the :func:`.mapper` can be
        configured with ``batch=False``, which will cause
        batches of instances to be broken up into individual
        (and more poorly performing) event->persist->event
        steps.

        .. warning::
            Mapper-level flush events are designed to operate **on attributes
            local to the immediate object being handled
            and via SQL operations with the given** :class:`.Connection`
            **only.** Handlers here should **not** make alterations to the
            state of the :class:`.Session` overall, and in general should not
            affect any :func:`.relationship` -mapped attributes, as
            session cascade rules will not function properly, nor is it
            always known if the related class has already been handled.
            Operations that **are not supported in mapper events** include:

            * :meth:`.Session.add`
            * :meth:`.Session.delete`
            * Mapped collection append, add, remove, delete, discard, etc.
            * Mapped relationship attribute set/del events,
              i.e. ``someobject.related = someotherobject``

            Operations which manipulate the state of the object
            relative to other objects are better handled:

            * In the ``__init__()`` method of the mapped object itself,
              or another method designed to establish some particular state.
            * In a ``@validates`` handler, see :ref:`simple_validators`
            * Within the  :meth:`.SessionEvents.before_flush` event.

        :param mapper: the :class:`.Mapper` which is the target
         of this event.
        :param connection: the :class:`.Connection` being used to
         emit UPDATE statements for this instance.  This
         provides a handle into the current transaction on the
         target database specific to this instance.
        :param target: the mapped instance being persisted.  If
         the event is configured with ``raw=True``, this will
         instead be the :class:`.InstanceState` state-management
         object associated with the instance.
        :return: No return value is supported by this event.
        """

    def after_update(self, mapper, connection, target):
        """Receive an object instance after an UPDATE statement
        is emitted corresponding to that instance.

        This event is used to modify in-Python-only
        state on the instance after an UPDATE occurs, as well
        as to emit additional SQL statements on the given
        connection.

        This method is called for all instances that are
        marked as "dirty", *even those which have no net changes
        to their column-based attributes*, and for which
        no UPDATE statement has proceeded. An object is marked
        as dirty when any of its column-based attributes have a
        "set attribute" operation called or when any of its
        collections are modified. If, at update time, no
        column-based attributes have any net changes, no UPDATE
        statement will be issued. This means that an instance
        being sent to :meth:`~.MapperEvents.after_update` is
        *not* a guarantee that an UPDATE statement has been
        issued.

        To detect if the column-based attributes on the object have net
        changes, and therefore resulted in an UPDATE statement, use
        ``object_session(instance).is_modified(instance,
        include_collections=False)``.

        The event is often called for a batch of objects of the
        same class after their UPDATE statements have been emitted at
        once in a previous step. In the extremely rare case that
        this is not desirable, the :func:`.mapper` can be
        configured with ``batch=False``, which will cause
        batches of instances to be broken up into individual
        (and more poorly performing) event->persist->event
        steps.

        .. warning::
            Mapper-level flush events are designed to operate **on attributes
            local to the immediate object being handled
            and via SQL operations with the given** :class:`.Connection`
            **only.** Handlers here should **not** make alterations to the
            state of the :class:`.Session` overall, and in general should not
            affect any :func:`.relationship` -mapped attributes, as
            session cascade rules will not function properly, nor is it
            always known if the related class has already been handled.
            Operations that **are not supported in mapper events** include:

            * :meth:`.Session.add`
            * :meth:`.Session.delete`
            * Mapped collection append, add, remove, delete, discard, etc.
            * Mapped relationship attribute set/del events,
              i.e. ``someobject.related = someotherobject``

            Operations which manipulate the state of the object
            relative to other objects are better handled:

            * In the ``__init__()`` method of the mapped object itself,
              or another method designed to establish some particular state.
            * In a ``@validates`` handler, see :ref:`simple_validators`
            * Within the  :meth:`.SessionEvents.before_flush` event.

        :param mapper: the :class:`.Mapper` which is the target
         of this event.
        :param connection: the :class:`.Connection` being used to
         emit UPDATE statements for this instance.  This
         provides a handle into the current transaction on the
         target database specific to this instance.
        :param target: the mapped instance being persisted.  If
         the event is configured with ``raw=True``, this will
         instead be the :class:`.InstanceState` state-management
         object associated with the instance.
        :return: No return value is supported by this event.

        """

    def before_delete(self, mapper, connection, target):
        """Receive an object instance before a DELETE statement
        is emitted corresponding to that instance.

        This event is used to emit additional SQL statements on
        the given connection as well as to perform application
        specific bookkeeping related to a deletion event.

        The event is often called for a batch of objects of the
        same class before their DELETE statements are emitted at
        once in a later step.

        .. warning::
            Mapper-level flush events are designed to operate **on attributes
            local to the immediate object being handled
            and via SQL operations with the given** :class:`.Connection`
            **only.** Handlers here should **not** make alterations to the
            state of the :class:`.Session` overall, and in general should not
            affect any :func:`.relationship` -mapped attributes, as
            session cascade rules will not function properly, nor is it
            always known if the related class has already been handled.
            Operations that **are not supported in mapper events** include:

            * :meth:`.Session.add`
            * :meth:`.Session.delete`
            * Mapped collection append, add, remove, delete, discard, etc.
            * Mapped relationship attribute set/del events,
              i.e. ``someobject.related = someotherobject``

            Operations which manipulate the state of the object
            relative to other objects are better handled:

            * In the ``__init__()`` method of the mapped object itself,
              or another method designed to establish some particular state.
            * In a ``@validates`` handler, see :ref:`simple_validators`
            * Within the  :meth:`.SessionEvents.before_flush` event.

        :param mapper: the :class:`.Mapper` which is the target
         of this event.
        :param connection: the :class:`.Connection` being used to
         emit DELETE statements for this instance.  This
         provides a handle into the current transaction on the
         target database specific to this instance.
        :param target: the mapped instance being deleted.  If
         the event is configured with ``raw=True``, this will
         instead be the :class:`.InstanceState` state-management
         object associated with the instance.
        :return: No return value is supported by this event.

        """

    def after_delete(self, mapper, connection, target):
        """Receive an object instance after a DELETE statement
        has been emitted corresponding to that instance.

        This event is used to emit additional SQL statements on
        the given connection as well as to perform application
        specific bookkeeping related to a deletion event.

        The event is often called for a batch of objects of the
        same class after their DELETE statements have been emitted at
        once in a previous step.

        .. warning::
            Mapper-level flush events are designed to operate **on attributes
            local to the immediate object being handled
            and via SQL operations with the given** :class:`.Connection`
            **only.** Handlers here should **not** make alterations to the
            state of the :class:`.Session` overall, and in general should not
            affect any :func:`.relationship` -mapped attributes, as
            session cascade rules will not function properly, nor is it
            always known if the related class has already been handled.
            Operations that **are not supported in mapper events** include:

            * :meth:`.Session.add`
            * :meth:`.Session.delete`
            * Mapped collection append, add, remove, delete, discard, etc.
            * Mapped relationship attribute set/del events,
              i.e. ``someobject.related = someotherobject``

            Operations which manipulate the state of the object
            relative to other objects are better handled:

            * In the ``__init__()`` method of the mapped object itself,
              or another method designed to establish some particular state.
            * In a ``@validates`` handler, see :ref:`simple_validators`
            * Within the  :meth:`.SessionEvents.before_flush` event.

        :param mapper: the :class:`.Mapper` which is the target
         of this event.
        :param connection: the :class:`.Connection` being used to
         emit DELETE statements for this instance.  This
         provides a handle into the current transaction on the
         target database specific to this instance.
        :param target: the mapped instance being deleted.  If
         the event is configured with ``raw=True``, this will
         instead be the :class:`.InstanceState` state-management
         object associated with the instance.
        :return: No return value is supported by this event.

        """

    @classmethod
    def _remove(cls, identifier, target, fn):
        "Removal of mapper events not yet implemented"
        raise NotImplementedError(msg)


class _MapperEventsHold(_EventsHold):
    all_holds = weakref.WeakKeyDictionary()

    def resolve(self, class_):
        return orm.util._mapper_or_none(class_)

    class HoldMapperEvents(_EventsHold.HoldEvents, MapperEvents):
        pass

    dispatch = event.dispatcher(HoldMapperEvents)


class SessionEvents(event.Events):
    """Define events specific to :class:`.Session` lifecycle.

    e.g.::

        from sqlalchemy import event
        from sqlalchemy.orm import sessionmaker

        def my_before_commit(session):
            print "before commit!"

        Session = sessionmaker()

        event.listen(Session, "before_commit", my_before_commit)

    The :func:`~.event.listen` function will accept
    :class:`.Session` objects as well as the return result
    of :func:`.sessionmaker` and :func:`.scoped_session`.

    Additionally, it accepts the :class:`.Session` class which
    will apply listeners to all :class:`.Session` instances
    globally.

    """
    @classmethod
    def _accept_with(cls, target):
        if isinstance(target, orm.scoped_session):

            target = target.session_factory
            if not isinstance(target, orm.sessionmaker) and \
                (
                    not isinstance(target, type) or
                    not issubclass(target, orm.Session)
                ):
                raise exc.ArgumentError(
                            "Session event listen on a scoped_session "
                            "requires that its creation callable "
                            "is associated with the Session class.")

        if isinstance(target, orm.sessionmaker):
            return target.class_
        elif isinstance(target, type):
            if issubclass(target, orm.scoped_session):
                return orm.Session
            elif issubclass(target, orm.Session):
                return target
        elif isinstance(target, orm.Session):
            return target
        else:
            return None

    @classmethod
    def _remove(cls, identifier, target, fn):
        msg = "Removal of session events not yet implemented"
        raise NotImplementedError(msg)

    def after_transaction_create(self, session, transaction):
        """Execute when a new :class:`.SessionTransaction` is created.

        This event differs from :meth:`~.SessionEvents.after_begin`
        in that it occurs for each :class:`.SessionTransaction`
        overall, as opposed to when transactions are begun
        on individual database connections.  It is also invoked
        for nested transactions and subtransactions, and is always
        matched by a corresponding
        :meth:`~.SessionEvents.after_transaction_end` event
        (assuming normal operation of the :class:`.Session`).

        :param session: the target :class:`.Session`.
        :param transaction: the target :class:`.SessionTransaction`.

        .. versionadded:: 0.8

        .. seealso::

            :meth:`~.SessionEvents.after_transaction_end`

        """

    def after_transaction_end(self, session, transaction):
        """Execute when the span of a :class:`.SessionTransaction` ends.

        This event differs from :meth:`~.SessionEvents.after_commit`
        in that it corresponds to all :class:`.SessionTransaction`
        objects in use, including those for nested transactions
        and subtransactions, and is always matched by a corresponding
        :meth:`~.SessionEvents.after_transaction_create` event.

        :param session: the target :class:`.Session`.
        :param transaction: the target :class:`.SessionTransaction`.

        .. versionadded:: 0.8

        .. seealso::

            :meth:`~.SessionEvents.after_transaction_create`

        """

    def before_commit(self, session):
        """Execute before commit is called.

        .. note::

            The :meth:`.before_commit` hook is *not* per-flush,
            that is, the :class:`.Session` can emit SQL to the database
            many times within the scope of a transaction.
            For interception of these events, use the :meth:`~.SessionEvents.before_flush`,
            :meth:`~.SessionEvents.after_flush`, or :meth:`~.SessionEvents.after_flush_postexec`
            events.

        :param session: The target :class:`.Session`.

        .. seealso::

            :meth:`~.SessionEvents.after_commit`

            :meth:`~.SessionEvents.after_begin`

            :meth:`~.SessionEvents.after_transaction_create`

            :meth:`~.SessionEvents.after_transaction_end`

        """

    def after_commit(self, session):
        """Execute after a commit has occurred.

        .. note::

            The :meth:`~.SessionEvents.after_commit` hook is *not* per-flush,
            that is, the :class:`.Session` can emit SQL to the database
            many times within the scope of a transaction.
            For interception of these events, use the :meth:`~.SessionEvents.before_flush`,
            :meth:`~.SessionEvents.after_flush`, or :meth:`~.SessionEvents.after_flush_postexec`
            events.

        .. note::

            The :class:`.Session` is not in an active tranasction
            when the :meth:`~.SessionEvents.after_commit` event is invoked, and therefore
            can not emit SQL.  To emit SQL corresponding to every transaction,
            use the :meth:`~.SessionEvents.before_commit` event.

        :param session: The target :class:`.Session`.

        .. seealso::

            :meth:`~.SessionEvents.before_commit`

            :meth:`~.SessionEvents.after_begin`

            :meth:`~.SessionEvents.after_transaction_create`

            :meth:`~.SessionEvents.after_transaction_end`

        """

    def after_rollback(self, session):
        """Execute after a real DBAPI rollback has occurred.

        Note that this event only fires when the *actual* rollback against
        the database occurs - it does *not* fire each time the
        :meth:`.Session.rollback` method is called, if the underlying
        DBAPI transaction has already been rolled back.  In many
        cases, the :class:`.Session` will not be in
        an "active" state during this event, as the current
        transaction is not valid.   To acquire a :class:`.Session`
        which is active after the outermost rollback has proceeded,
        use the :meth:`.SessionEvents.after_soft_rollback` event, checking the
        :attr:`.Session.is_active` flag.

        :param session: The target :class:`.Session`.

        """

    def after_soft_rollback(self, session, previous_transaction):
        """Execute after any rollback has occurred, including "soft"
        rollbacks that don't actually emit at the DBAPI level.

        This corresponds to both nested and outer rollbacks, i.e.
        the innermost rollback that calls the DBAPI's
        rollback() method, as well as the enclosing rollback
        calls that only pop themselves from the transaction stack.

        The given :class:`.Session` can be used to invoke SQL and
        :meth:`.Session.query` operations after an outermost rollback
        by first checking the :attr:`.Session.is_active` flag::

            @event.listens_for(Session, "after_soft_rollback")
            def do_something(session, previous_transaction):
                if session.is_active:
                    session.execute("select * from some_table")

        :param session: The target :class:`.Session`.
        :param previous_transaction: The :class:`.SessionTransaction`
        transactional marker object which was just closed.   The current
        :class:`.SessionTransaction` for the given :class:`.Session` is
        available via the :attr:`.Session.transaction` attribute.

        .. versionadded:: 0.7.3

        """

    def before_flush(self, session, flush_context, instances):
        """Execute before flush process has started.

        :param session: The target :class:`.Session`.
        :param flush_context: Internal :class:`.UOWTransaction` object
         which handles the details of the flush.
        :param instances: Usually ``None``, this is the collection of
         objects which can be passed to the :meth:`.Session.flush` method
         (note this usage is deprecated).

        .. seealso::

            :meth:`~.SessionEvents.after_flush`

            :meth:`~.SessionEvents.after_flush_postexec`

        """

    def after_flush(self, session, flush_context):
        """Execute after flush has completed, but before commit has been
        called.

        Note that the session's state is still in pre-flush, i.e. 'new',
        'dirty', and 'deleted' lists still show pre-flush state as well
        as the history settings on instance attributes.

        :param session: The target :class:`.Session`.
        :param flush_context: Internal :class:`.UOWTransaction` object
         which handles the details of the flush.

        .. seealso::

            :meth:`~.SessionEvents.before_flush`

            :meth:`~.SessionEvents.after_flush_postexec`

        """

    def after_flush_postexec(self, session, flush_context):
        """Execute after flush has completed, and after the post-exec
        state occurs.

        This will be when the 'new', 'dirty', and 'deleted' lists are in
        their final state.  An actual commit() may or may not have
        occurred, depending on whether or not the flush started its own
        transaction or participated in a larger transaction.

        :param session: The target :class:`.Session`.
        :param flush_context: Internal :class:`.UOWTransaction` object
         which handles the details of the flush.


        .. seealso::

            :meth:`~.SessionEvents.before_flush`

            :meth:`~.SessionEvents.after_flush`

        """

    def after_begin(self, session, transaction, connection):
        """Execute after a transaction is begun on a connection

        :param session: The target :class:`.Session`.
        :param transaction: The :class:`.SessionTransaction`.
        :param connection: The :class:`~.engine.Connection` object
         which will be used for SQL statements.

        .. seealso::

            :meth:`~.SessionEvents.before_commit`

            :meth:`~.SessionEvents.after_commit`

            :meth:`~.SessionEvents.after_transaction_create`

            :meth:`~.SessionEvents.after_transaction_end`

        """

    def before_attach(self, session, instance):
        """Execute before an instance is attached to a session.

        This is called before an add, delete or merge causes
        the object to be part of the session.

        .. versionadded:: 0.8.  Note that :meth:`.after_attach` now
           fires off after the item is part of the session.
           :meth:`.before_attach` is provided for those cases where
           the item should not yet be part of the session state.

        .. seealso::

            :meth:`~.SessionEvents.after_attach`

        """

    def after_attach(self, session, instance):
        """Execute after an instance is attached to a session.

        This is called after an add, delete or merge.

        .. note::

           As of 0.8, this event fires off *after* the item
           has been fully associated with the session, which is
           different than previous releases.  For event
           handlers that require the object not yet
           be part of session state (such as handlers which
           may autoflush while the target object is not
           yet complete) consider the
           new :meth:`.before_attach` event.

        .. seealso::

            :meth:`~.SessionEvents.before_attach`

        """

    def after_bulk_update(self, session, query, query_context, result):
        """Execute after a bulk update operation to the session.

        This is called as a result of the :meth:`.Query.update` method.

        :param query: the :class:`.Query` object that this update operation was
         called upon.
        :param query_context: The :class:`.QueryContext` object, corresponding
         to the invocation of an ORM query.
        :param result: the :class:`.ResultProxy` returned as a result of the
         bulk UPDATE operation.

        """

    def after_bulk_delete(self, session, query, query_context, result):
        """Execute after a bulk delete operation to the session.

        This is called as a result of the :meth:`.Query.delete` method.

        :param query: the :class:`.Query` object that this update operation was
         called upon.
        :param query_context: The :class:`.QueryContext` object, corresponding
         to the invocation of an ORM query.
        :param result: the :class:`.ResultProxy` returned as a result of the
         bulk DELETE operation.

        """


class AttributeEvents(event.Events):
    """Define events for object attributes.

    These are typically defined on the class-bound descriptor for the
    target class.

    e.g.::

        from sqlalchemy import event

        def my_append_listener(target, value, initiator):
            print "received append event for target: %s" % target

        event.listen(MyClass.collection, 'append', my_append_listener)

    Listeners have the option to return a possibly modified version
    of the value, when the ``retval=True`` flag is passed
    to :func:`~.event.listen`::

        def validate_phone(target, value, oldvalue, initiator):
            "Strip non-numeric characters from a phone number"

            return re.sub(r'(?![0-9])', '', value)

        # setup listener on UserContact.phone attribute, instructing
        # it to use the return value
        listen(UserContact.phone, 'set', validate_phone, retval=True)

    A validation function like the above can also raise an exception
    such as :class:`.ValueError` to halt the operation.

    Several modifiers are available to the :func:`~.event.listen` function.

    :param active_history=False: When True, indicates that the
      "set" event would like to receive the "old" value being
      replaced unconditionally, even if this requires firing off
      database loads. Note that ``active_history`` can also be
      set directly via :func:`.column_property` and
      :func:`.relationship`.

    :param propagate=False: When True, the listener function will
      be established not just for the class attribute given, but
      for attributes of the same name on all current subclasses
      of that class, as well as all future subclasses of that
      class, using an additional listener that listens for
      instrumentation events.
    :param raw=False: When True, the "target" argument to the
      event will be the :class:`.InstanceState` management
      object, rather than the mapped instance itself.
    :param retval=False: when True, the user-defined event
      listening must return the "value" argument from the
      function.  This gives the listening function the opportunity
      to change the value that is ultimately used for a "set"
      or "append" event.

    """

    @classmethod
    def _accept_with(cls, target):
        # TODO: coverage
        if isinstance(target, orm.interfaces.MapperProperty):
            return getattr(target.parent.class_, target.key)
        else:
            return target

    @classmethod
    def _listen(cls, target, identifier, fn, active_history=False,
                                        raw=False, retval=False,
                                        propagate=False):
        if active_history:
            target.dispatch._active_history = True

        # TODO: for removal, need to package the identity
        # of the wrapper with the original function.

        if not raw or not retval:
            orig_fn = fn

            def wrap(target, value, *arg):
                if not raw:
                    target = target.obj()
                if not retval:
                    orig_fn(target, value, *arg)
                    return value
                else:
                    return orig_fn(target, value, *arg)
            fn = wrap

        event.Events._listen(target, identifier, fn, propagate)

        if propagate:
            manager = orm.instrumentation.manager_of_class(target.class_)

            for mgr in manager.subclass_managers(True):
                event.Events._listen(mgr[target.key], identifier, fn, True)

    @classmethod
    def _remove(cls, identifier, target, fn):
        msg = "Removal of attribute events not yet implemented"
        raise NotImplementedError(msg)

    def append(self, target, value, initiator):
        """Receive a collection append event.

        :param target: the object instance receiving the event.
          If the listener is registered with ``raw=True``, this will
          be the :class:`.InstanceState` object.
        :param value: the value being appended.  If this listener
          is registered with ``retval=True``, the listener
          function must return this value, or a new value which
          replaces it.
        :param initiator: the attribute implementation object
          which initiated this event.
        :return: if the event was registered with ``retval=True``,
         the given value, or a new effective value, should be returned.

        """

    def remove(self, target, value, initiator):
        """Receive a collection remove event.

        :param target: the object instance receiving the event.
          If the listener is registered with ``raw=True``, this will
          be the :class:`.InstanceState` object.
        :param value: the value being removed.
        :param initiator: the attribute implementation object
          which initiated this event.
        :return: No return value is defined for this event.
        """

    def set(self, target, value, oldvalue, initiator):
        """Receive a scalar set event.

        :param target: the object instance receiving the event.
          If the listener is registered with ``raw=True``, this will
          be the :class:`.InstanceState` object.
        :param value: the value being set.  If this listener
          is registered with ``retval=True``, the listener
          function must return this value, or a new value which
          replaces it.
        :param oldvalue: the previous value being replaced.  This
          may also be the symbol ``NEVER_SET`` or ``NO_VALUE``.
          If the listener is registered with ``active_history=True``,
          the previous value of the attribute will be loaded from
          the database if the existing value is currently unloaded
          or expired.
        :param initiator: the attribute implementation object
          which initiated this event.
        :return: if the event was registered with ``retval=True``,
         the given value, or a new effective value, should be returned.

        """
