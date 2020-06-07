from __future__ import absolute_import
import weakref
from warnings import warn
from fontTools.misc.py23 import basestring
from fontTools.misc.arrayTools import unionRect
from defcon.objects.base import BaseObject
from defcon.objects.contour import Contour
from defcon.objects.point import Point
from defcon.objects.component import Component
from defcon.objects.anchor import Anchor
from defcon.objects.lib import Lib
from defcon.objects.guideline import Guideline
from defcon.objects.image import Image
from defcon.objects.color import Color
from defcon.tools.representations import glyphAreaRepresentationFactory
from defcon.pens.decomposeComponentPointPen import DecomposeComponentPointPen


def addRepresentationFactory(name, factory):
    warn("addRepresentationFactory is deprecated. Use the functions in defcon.__init__.", DeprecationWarning)
    Glyph.representationFactories[name] = dict(factory=factory, destructiveNotifications=["Glyph.Changed"])

def removeRepresentationFactory(name):
    warn("removeRepresentationFactory is deprecated. Use the functions in defcon.__init__.", DeprecationWarning)
    del Glyph.representationFactories[name]


class Glyph(BaseObject):

    """
    This object represents a glyph and it contains contour, component, anchor
    and other assorted bits data about the glyph.

    **This object posts the following notifications:**

    ============================
    Name
    ============================
    Glyph.Changed
    Glyph.BeginUndo
    Glyph.EndUndo
    Glyph.BeginRedo
    Glyph.EndRedo
    Glyph.NameWillChange
    Glyph.NameChanged
    Glyph.UnicodesChanged
    Glyph.WidthChanged
    Glyph.HeightChanged
    Glyph.NoteChanged
    Glyph.LibChanged
    Glyph.ImageChanged
    Glyph.ImageWillBeDeleted
    Glyph.ContourWillBeAdded
    Glyph.ContourWillBeDeleted
    Glyph.ContoursChanged
    Glyph.ComponentWillBeAdded
    Glyph.ComponentWillBeDeleted
    Glyph.ComponentsChanged
    Glyph.AnchorWillBeAdded
    Glyph.AnchorWillBeDeleted
    Glyph.AnchorsChanged
    Glyph.GuidelineWillBeAdded
    Glyph.GuidelineWillBeDeleted
    Glyph.GuidelinesChanged
    Glyph.MarkColorChanged
    Glyph.VerticalOriginChanged
    ============================

    The Glyph object has list like behavior. This behavior allows you to interact
    with contour data directly. For example, to get a particular contour::

        contour = glyph[0]

    To iterate over all contours::

        for contour in glyph:

    To get the number of contours::

        contourCount = len(glyph)

    To interact with components or anchors in a similar way,
    use the ``components`` and ``anchors`` attributes.
    """

    changeNotificationName = "Glyph.Changed"
    beginUndoNotificationName = "Glyph.BeginUndo"
    endUndoNotificationName = "Glyph.EndUndo"
    beginRedoNotificationName = "Glyph.BeginRedo"
    endRedoNotificationName = "Glyph.EndRedo"
    representationFactories = {
        "defcon.glyph.area" : dict(
            factory=glyphAreaRepresentationFactory,
            destructiveNotifications=("Glyph.ContoursChanged", "Glyph.ComponentsChanged", "Glyph.ComponentBaseGlyphDataChanged")
        )
    }

    def __init__(self, layer=None,
        contourClass=None, pointClass=None, componentClass=None, anchorClass=None,
        guidelineClass=None, libClass=None, imageClass=None):
        layerSet = font = None
        if layer is not None:
            layerSet = layer.layerSet
            if layerSet is not None:
                font = weakref.ref(layer.layerSet.font)
                layerSet = weakref.ref(layer.layerSet)
            layer = weakref.ref(layer)
        self._font = font
        self._layerSet = layerSet
        self._layer = layer
        super(Glyph, self).__init__()
        self.beginSelfNotificationObservation()

        self._isLoading = False
        self._dirty = False
        self._name = None
        self._unicodes = []
        self._width = 0
        self._height = 0
        self._note = None
        self._image = None
        self._identifiers = set()
        self._shallowLoadedContours = None
        self._contours = []
        self._components = []
        self._anchors = []
        self._guidelines = []
        self._lib = None

        if contourClass is None:
            contourClass = Contour
        if pointClass is None:
            pointClass = Point
        if componentClass is None:
            componentClass = Component
        if anchorClass is None:
            anchorClass = Anchor
        if guidelineClass is None:
            guidelineClass = Guideline
        if libClass is None:
            libClass = Lib
        if imageClass is None:
            imageClass = Image
        self._contourClass = contourClass
        self._pointClass = pointClass
        self._componentClass = componentClass
        self._anchorClass = anchorClass
        self._guidelineClass = guidelineClass
        self._libClass = libClass
        self._imageClass = imageClass

    def __del__(self):
        super(Glyph, self).__del__()
        self._contours = None
        self._components = None
        self._anchors = None
        self._guidelines = None
        self._lib = None
        self._image = None

    # --------------
    # Parent Objects
    # --------------

    def getParent(self):
        return self.font

    def _get_font(self):
        if self._font is None:
            return None
        return self._font()

    font = property(_get_font, doc="The :class:`Font` that this glyph belongs to.")

    def _get_layerSet(self):
        if self._layerSet is None:
            return None
        return self._layerSet()

    layerSet = property(_get_layerSet, doc="The :class:`LayerSet` that this glyph belongs to.")

    def _get_layer(self):
        if self._layer is None:
            return None
        return self._layer()

    layer = property(_get_layer, doc="The :class:`Layer` that this glyph belongs to.")

    # ----------------
    # Basic Attributes
    # ----------------

    # identifiers

    def _get_identifiers(self):
        return self._identifiers

    identifiers = property(_get_identifiers, doc="Set of identifiers for the glyph. This is primarily for internal use.")

    # name

    def _set_name(self, value):
        oldName = self._name
        if oldName != value:
            self.postNotification(notification="Glyph.NameWillChange", data=dict(oldValue=oldName, newValue=value))
            self._name = value
            self.postNotification(notification="Glyph.NameChanged", data=dict(oldValue=oldName, newValue=value))
            self.dirty = True

    def _get_name(self):
        return self._name

    name = property(_get_name, _set_name, doc="The name of the glyph. Setting this posts *GLyph.NameChanged* and *Glyph.NameChanged* notifications.")

    # unicodes

    def _get_unicodes(self):
        return list(self._unicodes)

    def _set_unicodes(self, value):
        oldValue = self.unicodes
        if oldValue != value:
            self._unicodes = value
            self.postNotification(notification="Glyph.UnicodesChanged", data=dict(oldValue=oldValue, newValue=value))
            self.dirty = True

    unicodes = property(_get_unicodes, _set_unicodes, doc="The list of unicode values assigned to the glyph. Setting this posts *Glyph.UnicodesChanged* and *Glyph.Changed* notifications.")

    def _get_unicode(self):
        if self._unicodes:
            return self._unicodes[0]
        return None

    def _set_unicode(self, value):
        if value is None:
            self.unicodes = []
        else:
            existing = list(self._unicodes)
            if value in existing:
                existing.pop(existing.index(value))
            existing.insert(0, value)
            self.unicodes = existing

    unicode = property(_get_unicode, _set_unicode, doc="The primary unicode value for the glyph. This is the equivalent of ``glyph.unicodes[0]``. This is a convenience attribute that works with the ``unicodes`` attribute.")

    # -------
    # Metrics
    # -------

    # bounds

    def _getContourComponentBounds(self, attr):
        bounds = None
        subObjects = [contour for contour in self]
        subObjects += [component for component in self.components]
        for subObject in subObjects:
            b = getattr(subObject, attr)
            if b is not None:
                if bounds is None:
                    bounds = b
                else:
                    bounds = unionRect(bounds, b)
        return bounds

    def _get_bounds(self):
        return self._getContourComponentBounds("bounds")

    bounds = property(_get_bounds, doc="The bounds of the glyph's outline expressed as a tuple of form (xMin, yMin, xMax, yMax).")

    def _get_controlPointBounds(self):
        return self._getContourComponentBounds("controlPointBounds")

    controlPointBounds = property(_get_controlPointBounds, doc="The control bounds of all points in the glyph. This only measures the point positions, it does not measure curves. So, curves without points at the extrema will not be properly measured.")

    # area

    def _get_area(self):
        return self.getRepresentation("defcon.glyph.area")

    area = property(_get_area, doc="The area of the glyph's outline.")

    # margins

    def _get_leftMargin(self):
        bounds = self.bounds
        if bounds is None:
            return None
        xMin, yMin, xMax, yMax = bounds
        return xMin

    def _set_leftMargin(self, value):
        bounds = self.bounds
        if bounds is None:
            return
        xMin, yMin, xMax, yMax = bounds
        oldValue = xMin
        diff = value - xMin
        if value != oldValue:
            self.move((diff, 0))
            self.width += diff
            self.dirty = True

    leftMargin = property(_get_leftMargin, _set_leftMargin, doc="The left margin of the glyph. Setting this post *Glyph.WidthChanged* and *Glyph.Changed* notifications among others.")

    def _get_rightMargin(self):
        bounds = self.bounds
        if bounds is None:
            return None
        xMin, yMin, xMax, yMax = bounds
        return self._width - xMax

    def _set_rightMargin(self, value):
        bounds = self.bounds
        if bounds is None:
            return
        xMin, yMin, xMax, yMax = bounds
        oldValue = self._width - xMax
        if oldValue != value:
            self.width = xMax + value
            self.dirty = True

    rightMargin = property(_get_rightMargin, _set_rightMargin, doc="The right margin of the glyph. Setting this posts *Glyph.WidthChanged* and *Glyph.Changed* notifications among others.")

    def _get_bottomMargin(self):
        bounds = self.bounds
        if bounds is None:
            return None
        xMin, yMin, xMax, yMax = bounds
        if self.verticalOrigin is None:
            return yMin
        else:
            return yMin - (self.verticalOrigin - self.height)

    def _set_bottomMargin(self, value):
        bounds = self.bounds
        if bounds is None:
            return
        xMin, yMin, xMax, yMax = bounds
        if self.verticalOrigin is None:
            oldValue = yMin
            self.verticalOrigin = self.height
        else:
            oldValue = yMin - (self.verticalOrigin - self.height)
        diff = value - oldValue
        if value != oldValue:
            self.height += diff
            self.dirty = True

    bottomMargin = property(_get_bottomMargin, _set_bottomMargin, doc="The bottom margin of the glyph. Setting this post *Glyph.HeightChanged* and *Glyph.Changed* notifications among others.")

    def _get_topMargin(self):
        bounds = self.bounds
        if bounds is None:
            return None
        xMin, yMin, xMax, yMax = bounds
        if self.verticalOrigin is None:
            return self._height - yMax
        else:
            return self.verticalOrigin - yMax

    def _set_topMargin(self, value):
        bounds = self.bounds
        if bounds is None:
            return
        xMin, yMin, xMax, yMax = bounds
        if self.verticalOrigin is None:
            oldValue = self._height - yMax
        else:
            oldValue = self.verticalOrigin - yMax
        diff = value - oldValue
        if oldValue != value:
            self.verticalOrigin = yMax + value
            self.height += diff
            self.dirty = True

    topMargin = property(_get_topMargin, _set_topMargin, doc="The top margin of the glyph. Setting this posts *Glyph.HeightChanged*, *Glyph.VerticalOriginChanged* and *Glyph.Changed* notifications among others.")

    # width

    def _get_width(self):
        return self._width

    def _set_width(self, value):
        oldValue = self._width
        if oldValue != value:
            self._width = value
            self.postNotification(notification="Glyph.WidthChanged", data=dict(oldValue=oldValue, newValue=value))
            self.dirty = True

    width = property(_get_width, _set_width, doc="The width of the glyph. Setting this posts *Glyph.WidthChanged* and *Glyph.Changed* notifications.")

    # height

    def _get_height(self):
        return self._height

    def _set_height(self, value):
        oldValue = self._height
        if oldValue != value:
            self._height = value
            self.postNotification(notification="Glyph.HeightChanged", data=dict(oldValue=oldValue, newValue=value))
            self.dirty = True

    height = property(_get_height, _set_height, doc="The height of the glyph. Setting this posts *Glyph.HeightChanged* and *Glyph.Changed* notifications.")

    # ----------------------
    # Lib Wrapped Attributes
    # ----------------------

    # mark color

    def _get_markColor(self):
        value = self.lib.get("public.markColor")
        if value is not None:
            value = Color(value)
        return value

    def _set_markColor(self, value):
        # convert to a color object
        if value is not None:
            value = Color(value)
        # don't write if there is no change
        oldValue = self.lib.get("public.markColor")
        if oldValue is not None:
            oldValue = Color(oldValue)
        if value == oldValue:
            return
        # remove
        if value is None:
            if "public.markColor" in self.lib:
                del self.lib["public.markColor"]
        # store
        else:
            self.lib["public.markColor"] = value
        self.postNotification(notification="Glyph.MarkColorChanged", data=dict(oldValue=oldValue, newValue=value))

    markColor = property(_get_markColor, _set_markColor, doc="The glyph's mark color. When setting, the value can be a UFO color string, a sequence of (r, g, b, a) or a :class:`Color` object. Setting this posts *Glyph.MarkColorChanged* and *Glyph.Changed* notifications.")

    # vertical origin

    def _get_verticalOrigin(self):
        value = self.lib.get("public.verticalOrigin")
        return value

    def _set_verticalOrigin(self, value):
        # don't write if there is no change
        oldValue = self.lib.get("public.verticalOrigin")
        if value == oldValue:
            return
        # remove
        if value is None:
            if "public.verticalOrigin" in self.lib:
                del self.lib["public.verticalOrigin"]
        # store
        else:
            self.lib["public.verticalOrigin"] = value
        self.postNotification(notification="Glyph.VerticalOriginChanged", data=dict(oldValue=oldValue, newValue=value))

    verticalOrigin = property(_get_verticalOrigin, _set_verticalOrigin, doc="The glyph's vertical origin. Setting this posts *Glyph.VerticalOriginChanged* and *Glyph.Changed* notifications.")

    # -------
    # Pen API
    # -------

    def draw(self, pen):
        """
        Draw the glyph with **pen**.
        """
        from fontTools.pens.pointPen import PointToSegmentPen
        pointPen = PointToSegmentPen(pen)
        self.drawPoints(pointPen)

    def drawPoints(self, pointPen):
        """
        Draw the glyph with **pointPen**.
        """
        if self._shallowLoadedContours:
            self._drawShallowLoadedContours(pointPen, self._shallowLoadedContours)
        else:
            for contour in self._contours:
                contour.drawPoints(pointPen)
        for component in self._components:
            component.drawPoints(pointPen)

    def _drawShallowLoadedContours(self, pointPen, contours):
        for contour in contours:
            try:
                pointPen.beginPath(identifier=contour.get("identifier"))
            except TypeError:
                pointPen.beginPath()
                warn("The beginPath method needs an identifier kwarg. The contour's identifier value has been discarded.", DeprecationWarning)
            for args, kwargs in contour["points"]:
                pointPen.addPoint(*args, **kwargs)
            pointPen.endPath()

    def getPen(self):
        """
        Get the pen used to draw into this glyph.
        """
        from fontTools.pens.pointPen import SegmentToPointPen
        return SegmentToPointPen(self.getPointPen())

    def getPointPen(self):
        """
        Get the point pen used to draw into this glyph.
        """
        from defcon.pens.glyphObjectPointPen import GlyphObjectPointPen, GlyphObjectLoadingPointPen
        if self._isLoading:
            self._shallowLoadedContours = []
            return GlyphObjectLoadingPointPen(self)
        else:
            return GlyphObjectPointPen(self)

    # --------
    # Contours
    # --------

    def _get_contourClass(self):
        return self._contourClass

    contourClass = property(_get_contourClass, doc="The class used for contours.")

    def _get_pointClass(self):
        return self._pointClass

    pointClass = property(_get_pointClass, doc="The class used for points.")

    def _fullyLoadShallowLoadedContours(self):
        if not self._shallowLoadedContours:
            self._shallowLoadedContours = None
            return
        self.disableNotifications()
        contours = list(self._shallowLoadedContours)
        self._shallowLoadedContours = None
        dirty = self.dirty
        pointPen = self.getPointPen()
        self._drawShallowLoadedContours(pointPen, contours)
        self.dirty = dirty
        self.enableNotifications()

    def instantiateContour(self):
        contour = self._contourClass(
            glyph=self,
            pointClass=self.pointClass
        )
        return contour

    def beginSelfContourNotificationObservation(self, contour):
        if contour.dispatcher is None:
            return
        contour.addObserver(observer=self, methodName="_contourChanged", notification="Contour.Changed")

    def endSelfContourNotificationObservation(self, contour):
        if contour.dispatcher is None:
            return
        contour.removeObserver(observer=self, notification="Contour.Changed")
        contour.endSelfNotificationObservation()

    def appendContour(self, contour):
        """
        Append **contour** to the glyph. The contour must be a defcon
        :class:`Contour` object or a subclass of that object. An error
        will be raised if the contour's identifier or a point identifier
        conflicts with any of the identifiers within the glyph.

        This will post a *Glyph.Changed* notification.
        """
        self.insertContour(len(self), contour)

    def insertContour(self, index, contour):
        """
        Insert **contour** into the glyph at index. The contour
        must be a defcon :class:`Contour` object or a subclass
        of that object. An error will be raised if the contour's
        identifier or a point identifier conflicts with any of
        the identifiers within the glyph.

        This will post a *Glyph.Changed* notification.
        """
        assert contour not in self
        assert contour.glyph in (self, None), "This contour belongs to another glyph."
        self.postNotification(notification="Glyph.ContourWillBeAdded", data=dict(object=contour))
        if contour.glyph is None:
            identifiers = self._identifiers
            if contour.identifier is not None:
                assert contour.identifier not in identifiers
                identifiers.add(contour.identifier)
            for point in contour:
                if point.identifier is not None:
                    assert point.identifier not in identifiers
                    identifiers.add(point.identifier)
            contour.glyph = self
            contour.beginSelfNotificationObservation()
        self.beginSelfContourNotificationObservation(contour)
        self._contours.insert(index, contour)
        self.postNotification(notification="Glyph.ContoursChanged")
        self.dirty = True

    def removeContour(self, contour):
        """
        Remove **contour** from the glyph.

        This will post a *Glyph.Changed* notification.
        """
        if contour not in self:
            raise IndexError("contour not in glyph")
        self.postNotification(notification="Glyph.ContourWillBeDeleted", data=dict(object=contour))
        identifiers = self._identifiers
        if contour.identifier is not None:
            identifiers.remove(contour.identifier)
        for point in contour:
            if point.identifier is not None:
                identifiers.remove(point.identifier)
        self._contours.remove(contour)
        self.endSelfContourNotificationObservation(contour)
        self.postNotification(notification="Glyph.ContoursChanged")
        self.dirty = True

    def contourIndex(self, contour):
        """
        Get the index for **contour**.
        """
        return self._getContourIndex(contour)

    def clearContours(self):
        """
        Clear all contours from the glyph.

        This posts a *Glyph.Changed* notification.
        """
        self.holdNotifications(note="Requested by Glyph.clearContours.")
        for contour in reversed(self):
            self.removeContour(contour)
        self.releaseHeldNotifications()

    def correctContourDirection(self, trueType=False, segmentLength=10):
        """
        Correct the direction of all contours in the glyph.

        This posts a *Glyph.Changed* notification.
        """
        # set the contours to the same direction
        for contour in self:
            contour.clockwise = False
        # sort the contours by area in reverse (i.e. largest first)
        contours = sorted(self, key=lambda contour: -contour.area)
        # build a tree of nested contours
        tree = {}
        for largeIndex, largeContour in enumerate(contours):
            for smallContour in contours[largeIndex + 1:]:
                if largeContour.contourInside(smallContour, segmentLength=segmentLength):
                    if largeContour not in tree:
                        tree[largeContour] = []
                    tree[largeContour].append(smallContour)
        # run through the tree, largest to smallest, flipping
        # the direction of each contour nested within another contour
        for largeContour in contours:
            if largeContour in tree:
                for smallContour in tree[largeContour]:
                    smallContour.reverse()
        # set to the opposite if needed
        if trueType:
            for contour in self:
                contour.reverse()

    # ----------
    # Components
    # ----------

    def _get_componentClass(self):
        return self._componentClass

    componentClass = property(_get_componentClass, doc="The class used for components.")

    def _get_components(self):
        return list(self._components)

    components = property(_get_components, doc="An ordered list of :class:`Component` objects stored in the glyph.")

    def instantiateComponent(self):
        component = self._componentClass(
            glyph=self
        )
        return component

    def beginSelfComponentNotificationObservation(self, component):
        if component.dispatcher is None:
            return
        component.addObserver(observer=self, methodName="_componentChanged", notification="Component.Changed")
        component.addObserver(observer=self, methodName="_componentBaseGlyphDataChanged", notification="Component.BaseGlyphDataChanged")

    def endSelfComponentNotificationObservation(self, component):
        if component.dispatcher is None:
            return
        component.removeObserver(observer=self, notification="Component.Changed")
        component.removeObserver(observer=self, notification="Component.BaseGlyphDataChanged")
        component.endSelfNotificationObservation()

    def appendComponent(self, component):
        """
        Append **component** to the glyph. The component must be a defcon
        :class:`Component` object or a subclass of that object. An error
        will be raised if the component's identifier conflicts with any of
        the identifiers within the glyph.

        This will post a *Glyph.Changed* notification.
        """
        self.insertComponent(len(self._components), component)

    def insertComponent(self, index, component):
        """
        Insert **component** into the glyph at index. The component
        must be a defcon :class:`Component` object or a subclass
        of that object. An error will be raised if the component's
        identifier conflicts with any of the identifiers within
        the glyph.

        This will post a *Glyph.Changed* notification.
        """
        assert component not in self._components
        assert component.glyph in (self, None), "This component belongs to another glyph."
        self.postNotification(notification="Glyph.ComponentWillBeAdded", data=dict(object=component))
        if component.glyph is None:
            if component.identifier is not None:
                identifiers = self._identifiers
                assert component.identifier not in identifiers
                identifiers.add(component.identifier)
            component.glyph = self
            component.beginSelfNotificationObservation()
        self.beginSelfComponentNotificationObservation(component)
        self._components.insert(index, component)
        self.postNotification(notification="Glyph.ComponentsChanged")
        self.dirty = True

    def removeComponent(self, component):
        """
        Remove **component** from the glyph.

        This will post a *Glyph.Changed* notification.
        """
        self.postNotification(notification="Glyph.ComponentWillBeDeleted", data=dict(object=component))
        if component.identifier is not None:
            self._identifiers.remove(component.identifier)
        self._components.remove(component)
        self.endSelfComponentNotificationObservation(component)
        self.postNotification(notification="Glyph.ComponentsChanged")
        self.dirty = True

    def componentIndex(self, component):
        """
        Get the index for **component**.
        """
        return self._components.index(component)

    def clearComponents(self):
        """
        Clear all components from the glyph.

        This posts a *Glyph.Changed* notification.
        """
        self.holdNotifications(note="Requested by Glyph.clearComponents.")
        for component in reversed(self._components):
            self.removeComponent(component)
        self.releaseHeldNotifications()

    def decomposeComponent(self, component):
        """
        Decompose **component**. This will preserve the identifiers
        in the incoming contours and points unless there is a conflict.
        In that case, the conflicting incoming identifier will be discarded.

        This posts *Glyph.ComponentsChanged*, *Glyph.ContoursChanged*
        and *Glyph.Changed* notifications.
        """
        self.holdNotifications(note="Requested by Glyph.decomposeComponent.")
        layer = self.layer
        pointPen = DecomposeComponentPointPen(self, layer)
        self._decomposeComponent(component, layer, pointPen)
        self.releaseHeldNotifications()
        self.postNotification(notification="Glyph.ContoursChanged")

    def decomposeAllComponents(self):
        """
        Decompose all components in this glyph. This will preserve the
        identifiers in the incoming contours and points unless there is a
        conflict. In that case, the conflicting incoming identifier will
        be discarded.

        This posts *Glyph.ComponentsChanged*, *Glyph.ContoursChanged*
        and *Glyph.Changed* notifications.
        """
        if not self.components:
            return
        self.holdNotifications(note="Requested by Glyph.decomposeAllComponents.")
        layer = self.layer
        pointPen = DecomposeComponentPointPen(self, layer)
        for component in self.components:
            self._decomposeComponent(component, layer, pointPen)
        self.releaseHeldNotifications()
        self.postNotification(notification="Glyph.ContoursChanged")

    def _decomposeComponent(self, component, layer, pointPen):
        pointPen.skipConflictingIdentifiers = True
        component.drawPoints(pointPen)
        self.removeComponent(component)

    # -------
    # Anchors
    # -------

    def _get_anchorClass(self):
        return self._anchorClass

    anchorClass = property(_get_anchorClass, doc="The class used for anchors.")

    def _get_anchors(self):
        return list(self._anchors)

    def _set_anchors(self, value):
        self.clearAnchors()
        self.holdNotifications(note="Requested by Glyph._set_anchors.")
        for anchor in value:
            self.appendAnchor(anchor)
        self.releaseHeldNotifications()

    anchors = property(_get_anchors, _set_anchors, doc="An ordered list of :class:`Anchor` objects stored in the glyph.")

    def instantiateAnchor(self, anchorDict=None):
        anchor = self._anchorClass(anchorDict=anchorDict)
        return anchor

    def beginSelfAnchorNotificationObservation(self, anchor):
        if anchor.dispatcher is None:
            return
        anchor.addObserver(observer=self, methodName="_anchorChanged", notification="Anchor.Changed")

    def endSelfAnchorNotificationObservation(self, anchor):
        if anchor.dispatcher is None:
            return
        anchor.removeObserver(observer=self, notification="Anchor.Changed")
        anchor.endSelfNotificationObservation()

    def appendAnchor(self, anchor):
        """
        Append **anchor** to the glyph. The anchor must be a defcon
        :class:`Anchor` object or a subclass of that object. An error
        will be raised if the anchor's identifier conflicts with any of
        the identifiers within the glyph.

        This will post a *Glyph.Changed* notification.
        """
        self.insertAnchor(len(self._anchors), anchor)

    def insertAnchor(self, index, anchor):
        """
        Insert **anchor** into the glyph at index. The anchor
        must be a defcon :class:`Anchor` object or a subclass
        of that object. An error will be raised if the anchor's
        identifier conflicts with any of the identifiers within
        the glyph.

        This will post a *Glyph.Changed* notification.
        """
        try:
            assert anchor.glyph is None
        except AttributeError:
            pass
        self.postNotification(notification="Glyph.AnchorWillBeAdded")
        if not isinstance(anchor, self._anchorClass):
            anchor = self.instantiateAnchor(anchorDict=anchor)
        if anchor.identifier is not None:
            identifiers = self._identifiers
            assert anchor.identifier not in identifiers
            identifiers.add(anchor.identifier)
        anchor.glyph = self
        anchor.beginSelfNotificationObservation()
        self.beginSelfAnchorNotificationObservation(anchor)
        self._anchors.insert(index, anchor)
        self.postNotification(notification="Glyph.AnchorsChanged")
        self.dirty = True

    def removeAnchor(self, anchor):
        """
        Remove **anchor** from the glyph.

        This will post a *Glyph.Changed* notification.
        """
        self.postNotification(notification="Glyph.AnchorWillBeDeleted", data=dict(object=anchor))
        if anchor.identifier is not None:
            self._identifiers.remove(anchor.identifier)
        self._anchors.remove(anchor)
        self.endSelfAnchorNotificationObservation(anchor)
        self.postNotification(notification="Glyph.AnchorsChanged")
        self.dirty = True

    def anchorIndex(self, anchor):
        """
        Get the index for **anchor**.
        """
        return self._anchors.index(anchor)

    def clearAnchors(self):
        """
        Clear all anchors from the glyph.

        This posts a *Glyph.Changed* notification.
        """
        self.holdNotifications(note="Requested by Glyph.clearAnchors.")
        for anchor in reversed(self._anchors):
            self.removeAnchor(anchor)
        self.releaseHeldNotifications()

    # ----------
    # Guidelines
    # ----------

    def _get_guidelineClass(self):
        return self._guidelineClass

    guidelineClass = property(_get_guidelineClass, doc="The class used for guidelines.")

    def _get_guidelines(self):
        return list(self._guidelines)

    def _set_guidelines(self, value):
        self.clearGuidelines()
        self.holdNotifications(note="Requested by Glyph._set_guidelines.")
        for guideline in value:
            self.appendGuideline(guideline)
        self.releaseHeldNotifications()

    guidelines = property(_get_guidelines, _set_guidelines, doc="An ordered list of :class:`Guideline` objects stored in the glyph. Setting this will post a *Glyph.Changed* notification along with any notifications posted by the :py:meth:`Glyph.appendGuideline` and :py:meth:`Glyph.clearGuidelines` methods.")

    def instantiateGuideline(self, guidelineDict=None):
        guideline = self._guidelineClass(guidelineDict=guidelineDict)
        return guideline

    def beginSelfGuidelineNotificationObservation(self, guideline):
        if guideline.dispatcher is None:
            return
        guideline.addObserver(observer=self, methodName="_guidelineChanged", notification="Guideline.Changed")

    def endSelfGuidelineNotificationObservation(self, guideline):
        if guideline.dispatcher is None:
            return
        guideline.removeObserver(observer=self, notification="Guideline.Changed")
        guideline.endSelfNotificationObservation()

    def appendGuideline(self, guideline):
        """
        Append **guideline** to the glyph. The guideline must be a defcon
        :class:`Guideline` object or a subclass of that object. An error
        will be raised if the guideline's identifier conflicts with any of
        the identifiers within the glyph.

        This will post a *Glyph.Changed* notification.
        """
        self.insertGuideline(len(self._guidelines), guideline)

    def insertGuideline(self, index, guideline):
        """
        Insert **guideline** into the glyph at index. The guideline
        must be a defcon :class:`Guideline` object or a subclass
        of that object. An error will be raised if the guideline's
        identifier conflicts with any of the identifiers within
        the glyph.

        This will post a *Glyph.Changed* notification.
        """
        assert id(guideline) not in [id(guide) for guide in self.guidelines]
        self.postNotification(notification="Glyph.GuidelineWillBeAdded")
        if not isinstance(guideline, self._guidelineClass):
            guideline = self.instantiateGuideline(guidelineDict=guideline)
        assert guideline.glyph in (self, None), "This guideline belongs to another glyph."
        if guideline.glyph is None:
            assert guideline.font is None, "This guideline belongs to a font."
        if guideline.glyph is None:
            if guideline.identifier is not None:
                identifiers = self._identifiers
                assert guideline.identifier not in identifiers
                if guideline.identifier is not None:
                    identifiers.add(guideline.identifier)
            guideline.glyph = self
            guideline.beginSelfNotificationObservation()
        self.beginSelfGuidelineNotificationObservation(guideline)
        self._guidelines.insert(index, guideline)
        self.postNotification(notification="Glyph.GuidelinesChanged")
        self.dirty = True

    def removeGuideline(self, guideline):
        """
        Remove **guideline** from the glyph.

        This will post a *Glyph.Changed* notification.
        """
        self.postNotification(notification="Glyph.GuidelineWillBeDeleted", data=dict(object=guideline))
        if guideline.identifier is not None:
            self._identifiers.remove(guideline.identifier)
        self._guidelines.remove(guideline)
        self.endSelfGuidelineNotificationObservation(guideline)
        self.postNotification(notification="Glyph.GuidelinesChanged")
        self.dirty = True

    def guidelineIndex(self, guideline):
        """
        Get the index for **guideline**.
        """
        return self._guidelines.index(guideline)

    def clearGuidelines(self):
        """
        Clear all guidelines from the glyph.

        This posts a *Glyph.Changed* notification.
        """
        self.holdNotifications(note="Requested by Glyph.clearGuidelines.")
        for guideline in reversed(self._guidelines):
            self.removeGuideline(guideline)
        self.releaseHeldNotifications()

    # ----
    # Note
    # ----

    def _get_note(self):
        return self._note

    def _set_note(self, value):
        if value is not None:
            assert isinstance(value, basestring)
        oldValue = self._note
        if oldValue != value:
            self._note = value
            self.postNotification(notification="Glyph.NoteChanged", data=dict(oldValue=oldValue, newValue=value))
            self.dirty = True

    note = property(_get_note, _set_note, doc="An arbitrary note for the glyph. Setting this will post a *Glyph.Changed* notification.")

    # ---
    # Lib
    # ---

    def _get_libClass(self):
        return self._libClass

    libClass = property(_get_libClass, doc="The class used for the lib.")

    def instantiateLib(self):
        lib = self._libClass(
            glyph=self
        )
        return lib

    def _get_lib(self):
        if self._lib is None:
            self._lib = self.instantiateLib()
            self.beginSelfLibNotificationObservation()
        return self._lib

    def _set_lib(self, value):
        lib = self.lib
        lib.clear()
        lib.update(value)
        self.dirty = True

    lib = property(_get_lib, _set_lib, doc="The glyph's :class:`Lib` object. Setting this will clear any existing lib data and post a *Glyph.Changed* notification if data was replaced.")

    def beginSelfLibNotificationObservation(self):
        if self._lib.dispatcher is None:
            return
        self._lib.addObserver(observer=self, methodName="_libContentChanged", notification="Lib.Changed")

    def endSelfLibNotificationObservation(self):
        if self._lib is None:
            return
        if self._lib.dispatcher is None:
            return
        self._lib.removeObserver(observer=self, notification="Lib.Changed")
        self._lib.endSelfNotificationObservation()

    # -----
    # Image
    # -----

    def _get_imageClass(self):
        return self._imageClass

    imageClass = property(_get_imageClass, doc="The class used for the image.")

    def instantiateImage(self):
        image = self._imageClass(
            glyph=self
        )
        return image

    def _get_image(self):
        if self._image is None:
            self._image = self.instantiateImage()
            self.beginSelfImageNotificationObservation()
        return self._image

    def _set_image(self, image):
        # removing image
        if image is None:
            if self._image is not None:
                self.postNotification(notification="Glyph.ImageWillBeDeleted")
                self.endSelfImageNotificationObservation()
                self._image = None
                self.postNotification(notification="Glyph.ImageChanged")
                self.dirty = True
        # adding image
        else:
            if self._image is None:
                # create the image object
                i = self.image
            if set(self._image.items()) != set(image.items()):
                self._image.fileName = image["fileName"]
                self._image.transformation = (image["xScale"], image["xyScale"], image["yxScale"], image["yScale"], image["xOffset"], image["yOffset"])
                self._image.color = image.get("color")
                self.postNotification(notification="Glyph.ImageChanged")
                self.dirty = True

    image = property(_get_image, _set_image, doc="The glyph's :class:`Image` object. Setting this posts *Glyph.ImageChanged* and *Glyph.Changed* notifications.")

    def clearImage(self):
        self.image = None

    def beginSelfImageNotificationObservation(self):
        if self._image.dispatcher is None:
            return
        self._image.addObserver(observer=self, methodName="_imageChanged", notification="Image.Changed")
        self._image.addObserver(observer=self, methodName="_imageDataChanged", notification="Image.ImageDataChanged")

    def endSelfImageNotificationObservation(self):
        if self._image is None:
            return
        if self._image.dispatcher is None:
            return
        self._image.removeObserver(observer=self, notification="Image.Changed")
        self._image.removeObserver(observer=self, notification="Image.ImageDataChanged")
        self._image.endSelfNotificationObservation()

    # -------------
    # List Behavior
    # -------------

    def __contains__(self, contour):
        if self._shallowLoadedContours is not None:
            self._fullyLoadShallowLoadedContours()
        return contour in self._contours

    def __len__(self):
        if self._shallowLoadedContours is not None:
            self._fullyLoadShallowLoadedContours()
        return len(self._contours)

    def __iter__(self):
        if self._shallowLoadedContours is not None:
            self._fullyLoadShallowLoadedContours()
        return iter(self._contours)

    def __getitem__(self, index):
        if self._shallowLoadedContours is not None:
            self._fullyLoadShallowLoadedContours()
        return self._contours[index]

    def _getContourIndex(self, contour):
        if self._shallowLoadedContours is not None:
            self._fullyLoadShallowLoadedContours()
        return self._contours.index(contour)

    # ----------------
    # Glyph Absorption
    # ----------------

    def copyDataFromGlyph(self, glyph):
        """
        Copy data from **glyph**. This copies the following data:

        ==========
        width
        height
        unicodes
        note
        image
        contours
        components
        anchors
        guidelines
        lib
        ==========

        The name attribute is purposefully omitted.
        """
        from copy import deepcopy
        self.width = glyph.width
        self.height = glyph.height
        self.unicodes = list(glyph.unicodes)
        self.note = glyph.note
        self.guidelines = [self.instantiateGuideline(g) for g in glyph.guidelines]
        self.anchors = [self.instantiateAnchor(a) for a in glyph.anchors]
        self.image = glyph.image
        pointPen = self.getPointPen()
        glyph.drawPoints(pointPen)
        self.lib = deepcopy(glyph.lib)

    # -----
    # Clear
    # -----

    def clear(self):
        """
        Clear all contours, components, anchors and guidelines from the glyph.

        This posts a *Glyph.Changed* notification.
        """
        self.holdNotifications(note="Requested by Glyph.clear.")
        self.clearContours()
        self.clearComponents()
        self.clearAnchors()
        self.clearGuidelines()
        self.clearImage()
        self.releaseHeldNotifications()

    # ----
    # Move
    # ----

    def move(self, values):
        """
        Move all contours, components and anchors in the glyph
        by **(x, y)**.

        This posts a *Glyph.Changed* notification.
        """
        (x, y) = values
        for contour in self:
            contour.move((x, y))
        for component in self._components:
            component.move((x, y))
        for anchor in self._anchors:
            anchor.move((x, y))

    # ------------
    # Point Inside
    # ------------

    def pointInside(self, coordinates, evenOdd=False):
        """
        Returns a boolean indicating if **(x, y)** is in the
        "black" area of the glyph.
        """
        (x, y) = coordinates
        from fontTools.pens.pointInsidePen import PointInsidePen
        pen = PointInsidePen(glyphSet=None, testPoint=(x, y), evenOdd=evenOdd)
        self.draw(pen)
        return pen.getResult()

    # ----------------------
    # Notification Callbacks
    # ----------------------

    def endSelfNotificationObservation(self):
        if self.dispatcher is None:
            return
        if self._contours:
            for contour in self:
                self.endSelfContourNotificationObservation(contour)
        for component in self.components:
            self.endSelfComponentNotificationObservation(component)
        for anchor in self.anchors:
            self.endSelfAnchorNotificationObservation(anchor)
        for guideline in self.guidelines:
            self.endSelfGuidelineNotificationObservation(guideline)
        self.endSelfLibNotificationObservation()
        self.endSelfImageNotificationObservation()
        super(Glyph, self).endSelfNotificationObservation()
        self._font = None
        self._layerSet = None
        self._layer = None

    def _imageDataChanged(self, notification):
        self.postNotification(notification="Glyph.ImageChanged")
        self.postNotification(notification=self.changeNotificationName)

    def _imageChanged(self, notification):
        self.postNotification(notification="Glyph.ImageChanged")
        self.dirty = True

    def _contourChanged(self, notification):
        self.postNotification(notification="Glyph.ContoursChanged")
        self.dirty = True

    def _componentChanged(self, notification):
        self.postNotification(notification="Glyph.ComponentsChanged")
        self.dirty = True

    def _componentBaseGlyphDataChanged(self, notification):
        self.postNotification(notification="Glyph.ComponentsChanged")
        self.postNotification(notification=self.changeNotificationName)

    def _anchorChanged(self, notification):
        self.postNotification(notification="Glyph.AnchorsChanged")
        self.dirty = True

    def _guidelineChanged(self, notification):
        self.postNotification(notification="Glyph.GuidelinesChanged")
        self.dirty = True

    def _libContentChanged(self, notification):
        self.postNotification(notification="Glyph.LibChanged")
        self.dirty = True

    # -----------------------------
    # Serialization/Deserialization
    # -----------------------------

    def getDataForSerialization(self, **kwargs):
        from functools import partial

        simple_get = partial(getattr, self)
        serialize = lambda item: item.getDataForSerialization()
        serialized_get = lambda key: serialize(simple_get(key))
        serialized_list_get = lambda key: [serialize(item) for item in simple_get(key)]

        getters = [
            ('name', simple_get),
            ('unicodes', simple_get),
            ('width', simple_get),
            ('height', simple_get),
            ('note', simple_get),
            ('components', serialized_list_get),
            ('anchors', serialized_list_get),
            ('guidelines', serialized_list_get),
            ('image', serialized_get),
            ('lib', serialized_get)
        ]

        if self._shallowLoadedContours is not None:
            getters.append(('_shallowLoadedContours', simple_get))
        else:
            getters.append(('_contours', serialized_list_get))

        return self._serialize(getters, **kwargs)

    def setDataFromSerialization(self, data):
        from functools import partial

        set_attr = partial(setattr, self) # key, data

        def set_each(setter, drop_key=False):

            _setter = lambda k, v: setter(v) if drop_key else setter

            def wrapper(key, data):
                for d in data:
                    _setter(key, d)
            return wrapper

        def single_init(factory, data):
            item = factory()
            item.setDataFromSerialization(data)
            return item

        def list_init(factory, data):
            return [single_init(factory, childData) for childData in data]

        def init_set(init, factory, setter):
            def wrapper(key, data):
                setter(key, init(factory, data))
            return wrapper

        # Clear all contours, components, anchors and guidelines from the glyph.
        self.clear()

        setters = (
            ('name', set_attr),
            ('unicodes', set_attr),
            ('width',  set_attr),
            ('height',  set_attr),
            ('note',  set_attr),
            ('lib',  set_attr),
            ('_shallowLoadedContours', set_attr),
            ('_contours', init_set(list_init, self.instantiateContour, set_each(self.appendContour, True))),
            ('components', init_set(list_init, self.instantiateComponent, set_each(self.appendComponent, True))),
            ('guidelines', init_set(list_init, self.instantiateGuideline, set_attr)),
            ('anchors', init_set(list_init, self.instantiateAnchor, set_attr)),
            ('image', init_set(single_init, self.instantiateImage, set_attr))
        )

        for key, setter in setters:
            if key not in data:
                continue
            setter(key, data[key])


if __name__ == "__main__":
    import doctest
    doctest.testmod()
