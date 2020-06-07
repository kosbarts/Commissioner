from __future__ import absolute_import
import weakref
from defcon.objects.base import BaseDictObject


class Lib(BaseDictObject):

    """
    This object contains arbitrary data.

    **This object posts the following notifications:**

    ===============
    Name
    ===============
    Lib.Changed
    Lib.BeginUndo
    Lib.EndUndo
    Lib.BeginRedo
    Lib.EndRedo
    Lib.ItemSet
    Lib.ItemDeleted
    Lib.Cleared
    Lib.Updated
    ===============

    This object behaves like a dict. For example, to get a particular
    item from the lib::

        data = lib["com.typesupply.someApplication.blah"]

    To set the glyph list for a particular group name::

        lib["com.typesupply.someApplication.blah"] = 123

    And so on.

    **Note 1:** It is best to keep the data below the top level as shallow
    as possible. Changes below the top level will go unnoticed by the defcon
    change notification system. These changes will be saved the next time you
    save the font, however.

    **Note 2:** The keys used for storing data in the lib should follow the
    reverse domain naming convention detailed in the
    `UFO specification <http://unifiedfontobject.org/filestructure/lib.html>`_.
    """

    changeNotificationName = "Lib.Changed"
    beginUndoNotificationName = "Lib.BeginUndo"
    endUndoNotificationName = "Lib.EndUndo"
    beginRedoNotificationName = "Lib.BeginRedo"
    endRedoNotificationName = "Lib.EndRedo"
    setItemNotificationName = "Lib.ItemSet"
    deleteItemNotificationName = "Lib.ItemDeleted"
    clearNotificationName = "Lib.Cleared"
    updateNotificationName = "Lib.Updated"
    representationFactories = {}

    def __init__(self, font=None, layer=None, glyph=None):
        self._font = None
        self._layerSet = None
        self._layer = None
        self._glyph = None
        if font is not None:
            self.font = font
        if layer is not None:
            self.layer = layer
        if glyph is not None:
            self.glyph = glyph
        super(Lib, self).__init__()
        self.beginSelfNotificationObservation()

    # --------------
    # Parent Objects
    # --------------

    def getParent(self):
        if self._font is not None:
            return self.font
        elif self._layer is not None:
            return self.layer
        elif self._glyph is not None:
            return self.glyph
        return None

    def _get_font(self):
        font = None
        if self._font is None:
            layerSet = self.layerSet
            if layerSet is not None:
                font = layerSet.font
                if font is not None:
                    self._font = weakref.ref(font)
        else:
            font = self._font()
        return font

    def _set_font(self, font):
        assert self._font is None
        assert self._layer is None
        assert self._glyph is None
        if font is not None:
            font = weakref.ref(font)
        self._font = font

    font = property(_get_font, _set_font, doc="The :class:`Font` that this object belongs to. This should not be set externally.")

    def _get_layerSet(self):
        layerSet = None
        if self._layerSet is None:
            layer = self.layer
            if layer is not None:
                layerSet = layer.layerSet
                if layerSet is not None:
                    self._layerSet = weakref.ref(layerSet)
        else:
            layerSet = self._layerSet()
        return layerSet

    layerSet = property(_get_layerSet, doc="The :class:`LayerSet` that this object belongs to (if it isn't a font lib).")

    def _get_layer(self):
        layer = None
        if self._layer is None:
            glyph = self.glyph
            if glyph is not None:
                layer = glyph.layer
                if layer is not None:
                    self._layer = weakref.ref(layer)
        else:
            layer = self._layer()
        return layer

    def _set_layer(self, layer):
        assert self._font is None
        assert self._layer is None
        assert self._glyph is None
        if layer is not None:
            layer = weakref.ref(layer)
        self._layer = layer

    layer = property(_get_layer, _set_layer, doc="The :class:`Layer` that this object belongs to (if it isn't a font lib). This should not be set externally.")

    def _get_glyph(self):
        if self._glyph is not None:
            return self._glyph()
        return None

    def _set_glyph(self, glyph):
        assert self._font is None
        assert self._layer is None
        assert self._glyph is None
        if glyph is not None:
            glyph = weakref.ref(glyph)
        self._glyph = glyph

    glyph = property(_get_glyph, _set_glyph, doc="The :class:`Glyph` that this object belongs to (if it isn't a font or layer lib). This should not be set externally.")

    # ------------------------
    # Notification Observation
    # ------------------------

    def endSelfNotificationObservation(self):
        super(Lib, self).endSelfNotificationObservation()
        self._font = None
        self._layerSet = None
        self._layer = None
        self._glyph = None


if __name__ == "__main__":
    import doctest
    doctest.testmod()
