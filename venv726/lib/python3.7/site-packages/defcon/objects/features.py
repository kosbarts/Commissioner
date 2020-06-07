from __future__ import absolute_import
import weakref
from defcon.objects.base import BaseObject


class Features(BaseObject):

    """
    This object contais the test represening features in the font.

    **This object posts the following notifications:**

    ================
    Name
    ================
    Features.Changed
    Features.BeginUndo
    Features.EndUndo
    Features.BeginRedo
    Features.EndRedo
    Features.TextChanged
    ================
    """

    changeNotificationName = "Features.Changed"
    beginUndoNotificationName = "Features.BeginUndo"
    endUndoNotificationName = "Features.EndUndo"
    beginRedoNotificationName = "Features.BeginRedo"
    endRedoNotificationName = "Features.EndRedo"
    representationFactories = {}

    def __init__(self, font=None):
        self._font = None
        if font is not None:
            self._font = weakref.ref(font)
        super(Features, self).__init__()
        self.beginSelfNotificationObservation()
        self._dirty = False
        self._text = None

    # --------------
    # Parent Objects
    # --------------

    def getParent(self):
        return self.font

    def _get_font(self):
        if self._font is not None:
            return self._font()
        return None

    font = property(_get_font, doc="The :class:`Font` that this object belongs to.")

    # ----
    # Text
    # ----

    def _set_text(self, value):
        oldValue = self._text
        if oldValue == value:
            return
        self._text = value
        self.postNotification("Features.TextChanged", data=dict(oldValue=oldValue, newValue=value))
        self.dirty = True

    def _get_text(self):
        return self._text

    text = property(_get_text, _set_text, doc="The raw feature text. Setting this post *Features.TextChanged* and *Features.Changed* notifications.")

    # ------------------------
    # Notification Observation
    # ------------------------

    def endSelfNotificationObservation(self):
        super(Features, self).endSelfNotificationObservation()
        self._font = None

    # -----------------------------
    # Serialization/Deserialization
    # -----------------------------

    def getDataForSerialization(self, **kwargs):
        from functools import partial

        getters = [('text', partial(getattr, self))]
        return self._serialize(getters, **kwargs)

    def setDataFromSerialization(self, data):
        if 'text' in data:
            self.text = data['text']
