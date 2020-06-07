from __future__ import absolute_import
import weakref
from defcon.objects.base import BaseDictObject
from defcon.objects.color import Color
from defcon.tools.identifiers import makeRandomIdentifier


class Anchor(BaseDictObject):

    """
    This object represents an anchor point.

    **This object posts the following notifications:**

    ========================
    Name
    ========================
    Anchor.Changed
    Anchor.XChanged
    Anchor.YChanged
    Anchor.NameChanged
    Anchor.ColorChanged
    Anchor.IdentifierChanged
    ========================

    During initialization an anchor dictionary can be passed. If so,
    the new object will be populated with the data from the dictionary.
    """

    changeNotificationName = "Anchor.Changed"
    representationFactories = {}

    def __init__(self, glyph=None, anchorDict=None):
        self._font = None
        self._layerSet = None
        self._layer = None
        self._glyph = None
        self.glyph = glyph
        super(Anchor, self).__init__()
        self.beginSelfNotificationObservation()
        self._dirty = False
        if anchorDict is not None:
            self.x = anchorDict.get("x")
            self.y = anchorDict.get("y")
            self.name = anchorDict.get("name")
            self.color = anchorDict.get("color")
            self.identifier = anchorDict.get("identifier")

    # parents

    def getParent(self):
        return self.glyph

    def _get_font(self):
        font = None
        if self._font is None:
            glyph = self.glyph
            if glyph is not None:
                font = glyph.font
                if font is not None:
                    self._font = weakref.ref(font)
        else:
            font = self._font()
        return font

    font = property(_get_font, doc="The :class:`Font` that this anchor belongs to.")

    def _get_layerSet(self):
        layerSet = None
        if self._layerSet is None:
            glyph = self.glyph
            if glyph is not None:
                layerSet = glyph.layerSet
                if layerSet is not None:
                    self._layerSet = weakref.ref(layerSet)
        else:
            layerSet = self._layerSet()
        return layerSet

    layerSet = property(_get_layerSet, doc="The :class:`LayerSet` that this anchor belongs to.")

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

    layer = property(_get_layer, doc="The :class:`Layer` that this anchor belongs to.")

    def _get_glyph(self):
        if self._glyph is None:
            return None
        return self._glyph()

    def _set_glyph(self, glyph):
        assert self._glyph is None
        if glyph is not None:
            glyph = weakref.ref(glyph)
        self._font = None
        self._layerSet = None
        self._layer = None
        self._glyph = glyph


    glyph = property(_get_glyph, _set_glyph, doc="The :class:`Glyph` that this anchor belongs to. This should not be set externally.")

    # coordinates

    def _get_x(self):
        return self.get("x")

    def _set_x(self, value):
        old = self.get("x")
        if value == old:
            return
        self["x"] = value
        self.postNotification("Anchor.XChanged", data=dict(oldValue=old, newValue=value))

    x = property(_get_x, _set_x, doc="The x coordinate. Setting this will post *Anchor.XChanged* and *Anchor.Changed* notifications.")

    def _get_y(self):
        return self.get("y")

    def _set_y(self, value):
        old = self.get("y")
        if value == old:
            return
        self["y"] = value
        self.postNotification("Anchor.YChanged", data=dict(oldValue=old, newValue=value))

    y = property(_get_y, _set_y, doc="The y coordinate. Setting this will post *Anchor.YChanged* and *Anchor.Changed* notifications.")

    # name

    def _get_name(self):
        return self.get("name")

    def _set_name(self, value):
        old = self.get("name")
        if value == old:
            return
        self["name"] = value
        self.postNotification("Anchor.NameChanged", data=dict(oldValue=old, newValue=value))

    name = property(_get_name, _set_name, doc="The name. Setting this will post *Anchor.NameChanged* and *Anchor.Changed* notifications.")

    # color

    def _get_color(self):
        return self.get("color")

    def _set_color(self, color):
        if color is None:
            newColor = None
        else:
            newColor = Color(color)
        oldColor = self.get("color")
        if newColor == oldColor:
            return
        self["color"] = newColor
        self.postNotification("Anchor.ColorChanged", data=dict(oldValue=oldColor, newValue=newColor))

    color = property(_get_color, _set_color, doc="The anchors's :class:`Color` object. When setting, the value can be a UFO color string, a sequence of (r, g, b, a) or a :class:`Color` object. Setting this posts *Anchor.ColorChanged* and *Anchor.Changed* notifications.")

    # identifier

    def _get_identifiers(self):
        identifiers = None
        glyph = self.glyph
        if glyph is not None:
            identifiers = glyph.identifiers
        if identifiers is None:
            identifiers = set()
        return identifiers

    identifiers = property(_get_identifiers, doc="Set of identifiers for the glyph that this anchor belongs to. This is primarily for internal use.")

    def _get_identifier(self):
        return self.get("identifier")

    def _set_identifier(self, value):
        # don't allow overwritting an existing identifier
        if self.identifier is not None:
            return
        oldIdentifier = self.identifier
        if value == oldIdentifier:
            return
        # don't allow a duplicate
        identifiers = self.identifiers
        assert value not in identifiers
        # free the old identifier
        if oldIdentifier in identifiers:
            identifiers.remove(oldIdentifier)
        # store
        self["identifier"] = value
        if value is not None:
            identifiers.add(value)
        # post notifications
        self.postNotification("Anchor.IdentifierChanged", data=dict(oldValue=oldIdentifier, newValue=value))

    identifier = property(_get_identifier, _set_identifier, doc="The identifier. Setting this will post *Anchor.IdentifierChanged* and *Anchor.Changed* notifications.")

    def generateIdentifier(self):
        """
        Create a new, unique identifier for and assign it to the guideline.
        This will post *Anchor.IdentifierChanged* and *Anchor.Changed* notifications.
        """
        if self.identifier is None:
            identifier = makeRandomIdentifier(existing=self.identifiers)
            self.identifier = identifier
        return self.identifier

    # ----
    # Move
    # ----

    def move(self, values):
        """
        Move the anchor by **(x, y)**.

        This will post *Anchor.XChange*, *Anchor.YChanged* and *Anchor.Changed* notifications if anything changed.
        """
        (x, y) = values
        self.x += x
        self.y += y

    # ------------------------
    # Notification Observation
    # ------------------------

    def endSelfNotificationObservation(self):
        super(Anchor, self).endSelfNotificationObservation()
        self._font = None
        self._layerSet = None
        self._layer = None
        self._glyph = None


if __name__ == "__main__":
    import doctest
    doctest.testmod()
