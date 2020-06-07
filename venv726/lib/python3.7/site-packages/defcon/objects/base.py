from __future__ import absolute_import
import weakref
import pickle

class BaseObject(object):

    """
    The base object in defcon from which all other objects should be derived.

    **This object posts the following notifications:**

    ====================
    Name
    ====================
    BaseObject.Changed
    BaseObject.BeginUndo
    BaseObject.EndUndo
    BaseObject.BeginRedo
    BaseObject.EndRedo
    ====================

    Keep in mind that subclasses will not post these same notifications.

    Subclasses must override the following attributes:

    +-------------------------+--------------------------------------------------+
    | Name                    | Notes                                            |
    +=========================+==================================================+
    | changeNotificationName  | This must be a string unique to the class        |
    |                         | indicating the name of the notification          |
    |                         | to be posted when the dirty attribute is set.    |
    +-------------------------+--------------------------------------------------+
    | representationFactories | This must be a dictionary that is shared across  |
    |                         | *all* instances of the class.                    |
    +-------------------------+--------------------------------------------------+
    """

    changeNotificationName = "BaseObject.Changed"
    beginUndoNotificationName = "BaseObject.BeginUndo"
    endUndoNotificationName = "BaseObject.EndUndo"
    beginRedoNotificationName = "BaseObject.BeginRedo"
    endRedoNotificationName = "BaseObject.EndRedo"
    representationFactories = None

    def __init__(self):
        self._init()

    def _init(self):
        self._dispatcher = None
        self._dataOnDisk = None
        self._dataOnDiskTimeStamp = None
        self._undoManager = None
        self._representations = {}

    def __del__(self):
        self.endSelfNotificationObservation()

    # ------
    # Parent
    # ------

    def getParent(self):
        raise NotImplementedError

    # -------------
    # Notifications
    # -------------

    def _get_dispatcher(self):
        if self._dispatcher is not None:
            return self._dispatcher()
        else:
            try:
                dispatcher = self.font.dispatcher
                self._dispatcher = weakref.ref(dispatcher)
            except AttributeError:
                dispatcher = None
        return dispatcher

    dispatcher = property(_get_dispatcher, doc="The :class:`defcon.tools.notifications.NotificationCenter` assigned to the parent of this object.")

    def addObserver(self, observer, methodName, notification):
        """
        Add an observer to this object's notification dispatcher.

        * **observer** An object that can be referenced with weakref.
        * **methodName** A string representing the method to be called
          when the notification is posted.
        * **notification** The notification that the observer should
          be notified of.

        The method that will be called as a result of the action
        must accept a single *notification* argument. This will
        be a :class:`defcon.tools.notifications.Notification` object.

        This is a convenience method that does the same thing as::

            dispatcher = anObject.dispatcher
            dispatcher.addObserver(observer=observer, methodName=methodName,
                notification=notification, observable=anObject)
        """
        dispatcher = self.dispatcher
        if dispatcher is not None:
            self.dispatcher.addObserver(observer=observer, methodName=methodName,
                notification=notification, observable=self)

    def removeObserver(self, observer, notification):
        """
        Remove an observer from this object's notification dispatcher.

        * **observer** A registered object.
        * **notification** The notification that the observer was registered
          to be notified of.

        This is a convenience method that does the same thing as::

            dispatcher = anObject.dispatcher
            dispatcher.removeObserver(observer=observer,
                notification=notification, observable=anObject)
        """
        dispatcher = self.dispatcher
        if dispatcher is not None:
            self.dispatcher.removeObserver(observer=observer, notification=notification, observable=self)

    def hasObserver(self, observer, notification):
        """
        Returns a boolean indicating is the **observer** is registered for **notification**.

        This is a convenience method that does the same thing as::

            dispatcher = anObject.dispatcher
            dispatcher.hasObserver(observer=observer,
                notification=notification, observable=anObject)
        """
        dispatcher = self.dispatcher
        if dispatcher is not None:
            return self.dispatcher.hasObserver(observer=observer, notification=notification, observable=self)
        return False

    def holdNotifications(self, notification=None, note=None):
        """
        Hold this object's notifications until told to release them.

        * **notification** The specific notification to hold. This is optional.
          If no *notification* is given, all notifications will be held.
        * **note** An arbitrary string containing information about why the hold
          has been requested, the requester, etc. This is used for reference only.

        This is a convenience method that does the same thing as::

            dispatcher = anObject.dispatcher
            dispatcher.holdNotifications(
                observable=anObject, notification=notification, note=note)
        """
        dispatcher = self.dispatcher
        if dispatcher is not None:
            dispatcher.holdNotifications(observable=self, notification=notification, note=note)

    def releaseHeldNotifications(self, notification=None):
        """
        Release this object's held notifications.

        * **notification** The specific notification to hold. This is optional.

        This is a convenience method that does the same thing as::

            dispatcher = anObject.dispatcher
            dispatcher.releaseHeldNotifications(
                observable=anObject, notification=notification)
        """
        dispatcher = self.dispatcher
        if dispatcher is not None:
            dispatcher.releaseHeldNotifications(observable=self, notification=notification)

    def disableNotifications(self, notification=None, observer=None):
        """
        Disable this object's notifications until told to resume them.

        * **notification** The specific notification to disable. This is optional.
          If no *notification* is given, all notifications will be disabled.

        This is a convenience method that does the same thing as::

            dispatcher = anObject.dispatcher
            dispatcher.disableNotifications(
                observable=anObject, notification=notification, observer=observer)
        """
        dispatcher = self.dispatcher
        if dispatcher is not None:
            dispatcher.disableNotifications(observable=self, notification=notification, observer=observer)

    def enableNotifications(self, notification=None, observer=None):
        """
        Enable this object's notifications.

        * **notification** The specific notification to enable. This is optional.

        This is a convenience method that does the same thing as::

            dispatcher = anObject.dispatcher
            dispatcher.enableNotifications(
                observable=anObject, notification=notification, observer=observer)
        """
        dispatcher = self.dispatcher
        if dispatcher is not None:
            dispatcher.enableNotifications(observable=self, notification=notification, observer=observer)

    def postNotification(self, notification, data=None):
        """
        Post a **notification** through this object's notification dispatcher.

            * **notification** The name of the notification.
            * **data** Arbitrary data that will be stored in the :class:`Notification` object.

        This is a convenience method that does the same thing as::

            dispatcher = anObject.dispatcher
            dispatcher.postNotification(
                notification=notification, observable=anObject, data=data)
        """
        dispatcher = self.dispatcher
        if dispatcher is not None:
            dispatcher.postNotification(notification=notification, observable=self, data=data)

    # ------------------------
    # Notification Observation
    # ------------------------

    def beginSelfNotificationObservation(self):
        self.addObserver(self, "selfNotificationCallback", notification=None)

    def endSelfNotificationObservation(self):
        self.removeObserver(self, notification=None)
        self._dispatcher = None

    def selfNotificationCallback(self, notification):
        self._destroyRepresentationsForNotification(notification)

    # ----
    # Undo
    # ----

    # manager

    def _get_undoManager(self):
        return self._undoManager

    def _set_undoManager(self, manager):
        self._undoManager = manager

    undoManager = property(_get_undoManager, _set_undoManager,
                           doc="The undo manager assigned to this object.")

    # undo

    def canUndo(self):
        """
        Returns a boolean indicating whether the undo manager is able to
        perform an undo.
        """
        return self.undoManager.canUndo()

    def undo(self):
        """
        Perform an undo if possible, or return.
        If undo is performed, this will post *BaseObject.BeginUndo* and *BaseObject.EndUndo* notifications.
        """
        if not self.undoManager.canUndo():
            return
        self.postNotification(notification=self.beginUndoNotificationName)
        self.undoManager.undo()
        self.postNotification(notification=self.endUndoNotificationName)

    # redo

    def canRedo(self):
        """
        Returns a boolean indicating whether the undo manager is able to
        perform a redo.
        """
        return self.undoManager.canRedo()

    def redo(self):
        """
        Perform a redo if possible, or return.
        If redo is performed, this will post *BaseObject.BeginRedo* and *BaseObject.EndRedo* notifications.
        """
        if not self.undoManager.canRedo():
            return
        self.postNotification(notification=self.beginRedoNotificationName)
        self.undoManager.redo()
        self.postNotification(notification=self.endRedoNotificationName)

    # ---------------
    # Representations
    # ---------------

    def getRepresentation(self, name, **kwargs):
        """
        Get a representation. **name** must be a registered
        representation name. **\*\*kwargs** will be passed
        to the appropriate representation factory.
        """
        # only store the representation if the object has a
        # dispatcher. otherwise, notifications may not be
        # destroyed after an object change.
        if self.dispatcher is None:
            factory = self.representationFactories[name]
            return factory["factory"](self, **kwargs)
        else:
            if name not in self._representations:
                self._representations[name] = {}
            representations = self._representations[name]
            subKey = self._makeRepresentationSubKey(**kwargs)
            if subKey not in representations:
                factory = self.representationFactories[name]
                representation = factory["factory"](self, **kwargs)
                representations[subKey] = representation
            return representations[subKey]

    def destroyRepresentation(self, name, **kwargs):
        """
        Destroy the stored representation for **name**
        and **\*\*kwargs**. If no **kwargs** are given,
        any representation with **name** will be destroyed
        regardless of the **kwargs** passed when the
        representation was created.
        """
        if name not in self._representations:
            return
        if not kwargs:
            del self._representations[name]
        else:
            representations = self._representations[name]
            subKey = self._makeRepresentationSubKey(**kwargs)
            if subKey in representations:
                del self._representations[name][subKey]

    def destroyAllRepresentations(self, notification=None):
        """
        Destroy all representations.
        """
        self._representations.clear()

    def _destroyRepresentationsForNotification(self, notification):
        notificationName = notification.name
        for name, dataDict in self.representationFactories.items():
            if notificationName in dataDict["destructiveNotifications"]:
                self.destroyRepresentation(name)

    def representationKeys(self):
        """
        Get a list of all representation keys that are
        currently cached.
        """
        representations = []
        for name, subDict in self._representations.items():
            for subKey in subDict.keys():
                kwargs = {}
                if subKey is not None:
                    for k, v in subKey:
                        kwargs[k] = v
                representations.append((name, kwargs))
        return representations

    def hasCachedRepresentation(self, name, **kwargs):
        """
        Returns a boolean indicating if a representation for
        **name** and **\*\*kwargs** is cached in the object.
        """
        if name not in self._representations:
            return False
        subKey = self._makeRepresentationSubKey(**kwargs)
        return subKey in self._representations[name]

    def _makeRepresentationSubKey(self, **kwargs):
        if kwargs:
            key = sorted(kwargs.items())
            key = tuple(key)
        else:
            key = None
        return key

    # -----
    # Dirty
    # -----

    def _set_dirty(self, value):
        self._dirty = value
        dispatcher = self.dispatcher
        if dispatcher is not None:
            self.postNotification(self.changeNotificationName)

    def _get_dirty(self):
        return self._dirty

    dirty = property(_get_dirty, _set_dirty, doc="The dirty state of the object. True if the object has been changed. False if not. Setting this to True will cause the base changed notification to be posted. The object will automatically maintain this attribute and update it as you change the object.")

    # -----------------------------
    # Serialization/Deserialization
    # -----------------------------

    def serialize(self, dumpFunc=None, whitelist=None, blacklist=None):
        data = self.getDataForSerialization(whitelist=whitelist, blacklist=blacklist)

        dump = dumpFunc if dumpFunc is not None else pickle.dumps
        return dump(data)

    def deserialize(self, data, loadFunc=None):
        load = loadFunc if loadFunc is not None else pickle.loads
        self.setDataFromSerialization(load(data))

    def getDataForSerialization(self, **kwargs):
        """
        Return a dict of data that can be pickled.
        """
        return {}

    def setDataFromSerialization(self, data):
        """
        Restore state from the provided data-dict.
        """
        pass

    def _serialize(self, getters, whitelist=None, blacklist=None, **kwargs):
        """ A helper function for the defcon objects.

        Return a dict where the keys are the keys in getters and the values
        are the results of the getter functions

        getters is a list of tuples:
        [
            (:str:key, :callable:getter_function)
        ]

        if a whitelist is not None: the key must be in whitelist
        if a blacklist is not None: the key must not be in blacklist
        """
        data = {}
        for key, getter in getters:
            if whitelist is not None and key not in whitelist:
                continue
            if blacklist is not None and key in blacklist:
                continue
            data[key] = getter(key)
        return data

    # =============================================
    # = ufo lib writer/reader validation settings =
    # =============================================

    ufoLibReadValidate = True
    ufoLibWriteValidate = True


class BaseDictObject(dict, BaseObject):

    """
    A subclass of BaseObject that implements a dict API. Any changes
    to the contents of the object will cause the dirty attribute
    to be set to True.
    """

    setItemNotificationName = None
    deleteItemNotificationName = None
    clearNotificationName = None
    updateNotificationName = None

    def __init__(self):
        super(BaseDictObject, self).__init__()
        self._init()
        self._dirty = False

    def _get_dict(self):
        from warnings import warn
        warn(
            "BaseDictObject is now a dict and _dict is gone.",
            DeprecationWarning
        )
        return self

    _dict = property(_get_dict)

    def __hash__(self):
        return id(self)

    def __setitem__(self, key, value):
        oldValue = None
        if key in self:
            oldValue = self[key]
            if value is not None and oldValue == value:
                # don't do this if the value is None since some
                # subclasses establish their keys at startup with
                # self[key] = None
                return
        super(BaseDictObject, self).__setitem__(key, value)
        if self.setItemNotificationName is not None:
            self.postNotification(self.setItemNotificationName, data=dict(key=key, oldValue=oldValue, newValue=value))
        self.dirty = True

    def __delitem__(self, key):
        super(BaseDictObject, self).__delitem__(key)
        if self.deleteItemNotificationName is not None:
            self.postNotification(self.deleteItemNotificationName, data=dict(key=key))
        self.dirty = True

    def __deepcopy__(self, memo={}):
        import copy
        obj = self.__class__()
        for k, v in self.items():
            k = copy.deepcopy(k)
            v = copy.deepcopy(v)
            obj[k] = v
        return obj

    def clear(self):
        if not len(self):
            return
        super(BaseDictObject, self).clear()
        if self.clearNotificationName is not None:
            self.postNotification(self.clearNotificationName)
        self.dirty = True

    def update(self, other):
        super(BaseDictObject, self).update(other)
        if self.updateNotificationName is not None:
            self.postNotification(self.updateNotificationName, data=dict(other=other))
        self.dirty = True

    # -----------------------------
    # Serialization/Deserialization
    # -----------------------------

    def getDataForSerialization(self, **kwargs):
        simple_get = lambda k: self[k]

        getters = []
        for k in self.keys():
            getters.append((k, simple_get))

        return self._serialize(getters, **kwargs)

    def setDataFromSerialization(self, data):
        self.clear()
        self.update(data)


def setUfoLibReadValidate(value):
    """
    Set the default read validation.
    """
    BaseObject.ufoLibReadValidate = value


def setUfoLibWriteValidate(value):
    """
    Set the default write validation.
    """
    BaseObject.ufoLibWriteValidate = value


if __name__ == "__main__":
    import doctest
    doctest.testmod()
