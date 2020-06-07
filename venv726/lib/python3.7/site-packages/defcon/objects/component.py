from __future__ import absolute_import
import weakref
from warnings import warn
from fontTools.misc.transform import Transform
from defcon.objects.base import BaseObject
from defcon.tools.identifiers import makeRandomIdentifier
from defcon.tools.representations import componentBoundsRepresentationFactory, componentPointBoundsRepresentationFactory

_defaultTransformation = (1, 0, 0, 1, 0, 0)


class Component(BaseObject):

    """
    This object represents a reference to another glyph.

    **This object posts the following notifications:**

    ===============================
    Name
    ===============================
    Component.Changed
    Component.BaseGlyphChanged
    Component.BaseGlyphDataChanged
    Component.TransformationChanged
    Component.IdentifierChanged
    ===============================
    """

    changeNotificationName = "Component.Changed"
    representationFactories = {
        "defcon.component.bounds" : dict(
            factory=componentBoundsRepresentationFactory,
            destructiveNotifications=("Component.TransformationChanged", "Component.BaseGlyphChanged")
        ),
        "defcon.component.controlPointBounds" : dict(
            factory=componentPointBoundsRepresentationFactory,
            destructiveNotifications=("Component.TransformationChanged", "Component.BaseGlyphChanged")
        )
    }

    def __init__(self, glyph=None):
        self._font = None
        self._layerSet = None
        self._layer = None
        self._glyph = None
        self.glyph = glyph

        self._dirty = False
        self._baseGlyph = None
        self._transformation = tuple(_defaultTransformation)
        self._identifier = None

        super(Component, self).__init__()
        self.beginSelfNotificationObservation()

    # ----------
    # Attributes
    # ----------

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

    font = property(_get_font, doc="The :class:`Font` that this component belongs to.")

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

    layerSet = property(_get_layerSet, doc="The :class:`LayerSet` that this component belongs to.")

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

    layer = property(_get_layer, doc="The :class:`Layer` that this component belongs to.")

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

    glyph = property(_get_glyph, _set_glyph, doc="The :class:`Glyph` that this component belongs to. This should not be set externally.")

    # bounds

    def _get_bounds(self):
        return self.getRepresentation("defcon.component.bounds")

    bounds = property(_get_bounds, doc="The bounds of the components's outline expressed as a tuple of form (xMin, yMin, xMax, yMax).")

    def _get_controlPointBounds(self):
        return self.getRepresentation("defcon.component.controlPointBounds")

    controlPointBounds = property(_get_controlPointBounds, doc="The control bounds of all points in the components. This only measures the point positions, it does not measure curves. So, curves without points at the extrema will not be properly measured.")

    # base glyph

    def _set_baseGlyph(self, value):
        newBaseGlyph = value
        oldBaseGlyph = self._baseGlyph
        if newBaseGlyph == oldBaseGlyph:
            return
        self.endSelfBaseGlyphNotificationObservation()
        self._baseGlyph = newBaseGlyph
        self.beginSelfBaseGlyphNotificationObservation()
        self.postNotification(notification="Component.BaseGlyphChanged", data=dict(oldValue=oldBaseGlyph, newValue=newBaseGlyph))
        self.dirty = True

    def _get_baseGlyph(self):
        return self._baseGlyph

    baseGlyph = property(_get_baseGlyph, _set_baseGlyph, doc="The glyph that the components references. Setting this will post *Component.BaseGlyphChanged* and *Component.Changed* notifications.")

    # transformation

    def _set_transformation(self, value):
        oldValue = self._transformation
        if value == oldValue:
            return
        self._transformation = value
        self.postNotification(notification="Component.TransformationChanged", data=dict(oldValue=oldValue, newValue=value))
        self.dirty = True

    def _get_transformation(self):
        return self._transformation

    transformation = property(_get_transformation, _set_transformation, doc="The transformation matrix for the component. Setting this will post *Component.TransformationChanged* and *Component.Changed* notifications.")

    # -----------
    # Pen Methods
    # -----------

    def draw(self, pen):
        """
        Draw the component with **pen**.
        """
        from fontTools.pens.pointPen import PointToSegmentPen
        pointPen = PointToSegmentPen(pen)
        self.drawPoints(pointPen)

    def drawPoints(self, pointPen):
        """
        Draw the component with **pointPen**.
        """
        try:
            pointPen.addComponent(self._baseGlyph, self._transformation, identifier=self.identifier)
        except TypeError:
            pointPen.addComponent(self._baseGlyph, self._transformation)
            warn("The addComponent method needs an identifier kwarg. The component's identifier value has been discarded.", DeprecationWarning)

    # ----
    # Move
    # ----

    def move(self, values):
        """
        Move the component by **(x, y)**.

        This posts *Component.TransformationChanged* and *Component.Changed* notifications.
        """
        (x, y) = values
        xScale, xyScale, yxScale, yScale, xOffset, yOffset = self._transformation
        xOffset += x
        yOffset += y
        self.transformation = (xScale, xyScale, yxScale, yScale, xOffset, yOffset)

    # ------------
    # Point Inside
    # ------------

    def pointInside(self, coordinates, evenOdd=False):
        """
        Returns a boolean indicating if **(x, y)** is in the
        "black" area of the component.
        """
        (x, y) = coordinates
        from fontTools.pens.pointInsidePen import PointInsidePen
        glyph = self.glyph
        if glyph is None:
            return False
        font = self.font
        if font is None:
            return False
        pen = PointInsidePen(glyphSet=font, testPoint=(x, y), evenOdd=evenOdd)
        self.draw(pen)
        return pen.getResult()

    # ----------
    # Identifier
    # ----------

    def _get_identifiers(self):
        identifiers = None
        glyph = self.glyph
        if glyph is not None:
            identifiers = glyph.identifiers
        if identifiers is None:
            identifiers = set()
        return identifiers

    identifiers = property(_get_identifiers, doc="Set of identifiers for the glyph that this component belongs to. This is primarily for internal use.")

    def _get_identifier(self):
        return self._identifier

    def _set_identifier(self, value):
        # don't allow overwritting an existing identifier
        if self._identifier is not None:
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
        self._identifier = value
        if value is not None:
            identifiers.add(value)
        # post notifications
        self.postNotification("Component.IdentifierChanged", data=dict(oldValue=oldIdentifier, newValue=value))
        self.dirty = True

    identifier = property(_get_identifier, _set_identifier, doc="The identifier. Setting this will post *Component.IdentifierChanged* and *Component.Changed* notifications.")

    def generateIdentifier(self):
        """
        Create a new, unique identifier for and assign it to the contour.
        This will post *Component.IdentifierChanged* and *Component.Changed* notifications.
        """
        if self.identifier is None:
            identifier = makeRandomIdentifier(existing=self.identifiers)
            self.identifier = identifier
        return self.identifier

    # ------------------------
    # Notification Observation
    # ------------------------

    def beginSelfNotificationObservation(self):
        super(Component, self).beginSelfNotificationObservation()
        self.beginSelfBaseGlyphNotificationObservation()

    def endSelfNotificationObservation(self):
        self.endSelfBaseGlyphNotificationObservation()
        super(Component, self).endSelfNotificationObservation()
        self._font = None
        self._layerSet = None
        self._layer = None
        self._glyph = None

    def beginSelfBaseGlyphNotificationObservation(self):
        baseGlyph = self.baseGlyph
        if baseGlyph is None:
            return
        dispatcher = self.dispatcher
        if dispatcher is None:
            return
        layer = self.layer
        # base glyph is available
        if baseGlyph in layer:
            self._beginBaseGlyphObservations()
        # base glyph is not available
        else:
            self._beginLayerObservations()

    def endSelfBaseGlyphNotificationObservation(self):
        dispatcher = self.dispatcher
        if dispatcher is None:
            return
        self._endBaseGlyphObservations()
        self._endLayerObservations()

    def _beginBaseGlyphObservations(self, baseGlyph=None):
        layer = self.layer
        if baseGlyph is None:
            baseGlyph = layer[self.baseGlyph]
        baseGlyph.addObserver(self, "baseGlyphNameChangedNotificationCallback", "Glyph.NameChanged")
        baseGlyph.addObserver(self, "baseGlyphDataChangedNotificationCallback", "Glyph.ContoursChanged")
        baseGlyph.addObserver(self, "baseGlyphDataChangedNotificationCallback", "Glyph.ComponentsChanged")
        layer.addObserver(self, "layerGlyphWillBeDeletedNotificationCallback", "Layer.GlyphWillBeDeleted")

    def _endBaseGlyphObservations(self, baseGlyph=None):
        layer = self.layer
        if baseGlyph is None:
            baseGlyph = self.baseGlyph
            if baseGlyph is None:
                return
            if baseGlyph in layer:
                baseGlyph = layer[baseGlyph]
            else:
                return
        if baseGlyph.hasObserver(self, "Glyph.NameChanged"):
            baseGlyph.removeObserver(self, "Glyph.NameChanged")
            baseGlyph.removeObserver(self, "Glyph.ContoursChanged")
            baseGlyph.removeObserver(self, "Glyph.ComponentsChanged")
        if layer.hasObserver(self, "Layer.GlyphWillBeDeleted"):
            layer.removeObserver(self, "Layer.GlyphWillBeDeleted")

    def _beginLayerObservations(self):
        layer = self.layer
        layer.addObserver(self, "layerGlyphNameChangedNotificationCallback", "Layer.GlyphNameChanged")
        layer.addObserver(self, "layerGlyphAddedNotificationCallback", "Layer.GlyphAdded")

    def _endLayerObservations(self):
        layer = self.layer
        if not layer.hasObserver(self, "Layer.GlyphNameChanged"):
            return
        layer.removeObserver(self, "Layer.GlyphNameChanged")
        layer.removeObserver(self, "Layer.GlyphAdded")

    def baseGlyphNameChangedNotificationCallback(self, notification):
        newName = notification.data["newValue"]
        layer = self.layer
        notBaseGlyph = layer[newName]
        self._endBaseGlyphObservations(notBaseGlyph)
        self._beginLayerObservations()

    def layerGlyphNameChangedNotificationCallback(self, notification):
        newName = notification.data["newValue"]
        baseGlyph = self.baseGlyph
        if newName != baseGlyph:
            return
        self._endLayerObservations()
        self._beginBaseGlyphObservations()

    def layerGlyphWillBeDeletedNotificationCallback(self, notification):
        name = notification.data["name"]
        if name != self.baseGlyph:
            return
        self._endBaseGlyphObservations()
        self._beginLayerObservations()

    def layerGlyphAddedNotificationCallback(self, notification):
        name = notification.data["name"]
        if name != self.baseGlyph:
            return
        self._endLayerObservations()
        self._beginBaseGlyphObservations()

    def baseGlyphDataChangedNotificationCallback(self, notification):
        self.postNotification("Component.BaseGlyphDataChanged")

    # -----------------------------
    # Serialization/Deserialization
    # -----------------------------

    def getDataForSerialization(self, **kwargs):
        from functools import partial

        simple_get = partial(getattr, self)
        getters = (
            ('baseGlyph', simple_get),
            ('transformation', simple_get),
            ('identifier', simple_get)
        )

        return self._serialize(getters, **kwargs)

    def setDataFromSerialization(self, data):
        from functools import partial

        simple_set = partial(setattr, self)
        setters = (
            ('baseGlyph', simple_set),
            ('transformation', simple_set),
            ('identifier', simple_set)
        )
        for key, setter in setters:
            if key not in data:
                continue
            setter(key, data[key])


if __name__ == "__main__":
    import doctest
    doctest.testmod()
