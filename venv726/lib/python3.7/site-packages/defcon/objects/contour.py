from __future__ import absolute_import
import weakref
from warnings import warn
from fontTools.misc import bezierTools
from fontTools.misc import arrayTools
from defcon.objects.base import BaseObject
from defcon.tools import bezierMath
from defcon.tools.representations import contourBoundsRepresentationFactory,\
    contourControlPointBoundsRepresentationFactory, contourAreaRepresentationFactory,\
    contourFlattenedRepresentationFactory
from defcon.tools.identifiers import makeRandomIdentifier


class Contour(BaseObject):

    """
    This object represents a contour and it contains a list of points.

    **This object posts the following notifications:**

    ===============================
    Name
    ===============================
    Contour.Changed
    Contour.WindingDirectionChanged
    Contour.PointsChanged
    Contour.IdentifierChanged
    ===============================

    The Contour object has list like behavior. This behavior allows you to interact
    with point data directly. For example, to get a particular point::

        point = contour[0]

    To iterate over all points::

        for point in contour:

    To get the number of points::

        pointCount = len(contour)

    To interact with components or anchors in a similar way,
    use the ``components`` and ``anchors`` attributes.
    """

    changeNotificationName = "Contour.Changed"
    representationFactories = {
        "defcon.contour.bounds" : dict(
            factory=contourBoundsRepresentationFactory,
            destructiveNotifications=("Contour.PointsChanged")
        ),
        "defcon.contour.controlPointBounds" : dict(
            factory=contourControlPointBoundsRepresentationFactory,
            destructiveNotifications=("Contour.PointsChanged")
        ),
        "defcon.contour.area" : dict(
            factory=contourAreaRepresentationFactory,
            destructiveNotifications=("Contour.PointsChanged", "Contour.WindingDirectionChanged")
        ),
        "defcon.contour.flattened" : dict(
            factory=contourFlattenedRepresentationFactory,
            destructiveNotifications=("Contour.PointsChanged", "Contour.WindingDirectionChanged")
        )
    }

    def __init__(self, glyph=None, pointClass=None):
        self._font = None
        self._layerSet = None
        self._layer = None
        self._glyph = None
        self.glyph = glyph
        super(Contour, self).__init__()
        self.beginSelfNotificationObservation()
        self._points = []
        if pointClass is None:
            from .point import Point
            pointClass = Point
        self._pointClass = pointClass
        self._identifier = None
        self._dirty = False

    def __del__(self):
        super(Contour, self).__del__()
        self._points = None

    # --------------
    # Parent Objects
    # --------------

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

    font = property(_get_font, doc="The :class:`Font` that this contour belongs to.")

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

    layerSet = property(_get_layerSet, doc="The :class:`LayerSet` that this contour belongs to.")

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

    layer = property(_get_layer, doc="The :class:`Layer` that this contour belongs to.")

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

    glyph = property(_get_glyph, _set_glyph, doc="The :class:`Glyph` that this contour belongs to. This should not be set externally.")

    # ------
    # Points
    # ------

    def _get_pointClass(self):
        return self._pointClass

    pointClass = property(_get_pointClass, doc="The class used for point.")

    def _get_onCurvePoints(self):
        return [point for point in self._points if point.segmentType]

    onCurvePoints = property(_get_onCurvePoints, doc="A list of all on curve points in the contour.")

    def appendPoint(self, point):
        """
        Append **point** to the glyph. The point must be a defcon
        :class:`Point` object or a subclass of that object. An error
        will be raised if the point's identifier conflicts with any of
        the identifiers within the glyph.

        This will post *Contour.PointsChanged* and *Contour.Changed* notifications.
        """
        assert point not in self._points
        self.insertPoint(len(self._points), point)

    def insertPoint(self, index, point):
        """
        Insert **point** into the contour at index. The point
        must be a defcon :class:`Point` object or a subclass
        of that object. An error will be raised if the points's
        identifier conflicts with any of the identifiers within
        the glyph.

        This will post *Contour.PointsChanged* and *Contour.Changed* notifications.
        """
        assert point not in self._points
        if point.identifier is not None:
            identifiers = self.identifiers
            assert point.identifier not in identifiers
            if point.identifier is not None:
                identifiers.add(point.identifier)
        self._points.insert(index, point)
        self.postNotification("Contour.PointsChanged")
        self.dirty = True

    def removePoint(self, point):
        """
        Remove **point** from the contour.

        This will post *Contour.PointsChanged* and *Contour.Changed* notifications.
        """
        self._points.remove(point)
        if point.identifier is not None:
            self.identifiers.remove(point.identifier)
        self.postNotification("Contour.PointsChanged")
        self.dirty = True

    def setStartPoint(self, index):
        """
        Set the point at **index** as the first point in the contour.
        This point must be an on-curve point.

        This will post *Contour.PointsChanged* and *Contour.Changed* notifications.
        """
        onCurvePoints = self.onCurvePoints
        if len(onCurvePoints) < 2:
            return
        if self.open:
            return
        point = self._points[index]
        assert point.segmentType is not None, "index must represent an on curve point"
        before = self._points[:index]
        self._points = self._points[index:] + before
        self.postNotification("Contour.PointsChanged")
        self.dirty = True

    # -------------
    # List Behavior
    # -------------

    def __len__(self):
        return len(self._points)

    def __getitem__(self, index):
        return self._points.__getitem__(index)

    def __iter__(self):
        return iter(self._points)

    def clear(self):
        """
        Clear the contents of the contour.

        This posts *Contour.PointsChanged* and *Contour.Changed* notifications.
        """
        self._clear()

    def _clear(self, postNotification=True):
        # clear the internal storage
        self._points = []
        # reset the clockwise cache
        # post a dirty notification
        if postNotification:
            self.postNotification("Contour.PointsChanged")
            self.dirty = True

    def index(self, point):
        """
        Get the index for **point**.
        """
        return self._points.index(point)

    def reverse(self):
        """
        Reverse the direction of the contour. It's important to note
        that the actual points stored in this object will be completely
        repalced by new points.

        This will post *Contour.WindingDirectionChanged*,
        *Contour.PointsChanged* and *Contour.Changed* notifications.
        """
        from fontTools.pens.pointPen import ReverseContourPointPen
        oldDirection = self.clockwise
        # put the current points in another contour
        otherContour = self.__class__(glyph=None, pointClass=self.pointClass)
        # draw the points in this contour through
        # the reversing pen.
        reversePen = ReverseContourPointPen(otherContour)
        self.drawPoints(reversePen)
        # clear the points in this contour
        self._clear(postNotification=False)
        # set the points back into this contour
        self._points = otherContour._points
        # post a notification
        self.postNotification("Contour.WindingDirectionChanged", data=dict(oldValue=oldDirection, newValue=self.clockwise))
        self.postNotification("Contour.PointsChanged")
        self.dirty = True

    # --------
    # Segments
    # --------

    def _get_segments(self):
        if not len(self._points):
            return []
        segments = [[]]
        lastWasOffCurve = False
        for point in self._points:
            segments[-1].append(point)
            if point.segmentType is not None:
                segments.append([])
            lastWasOffCurve = point.segmentType is None
        if len(segments[-1]) == 0:
            del segments[-1]
        if lastWasOffCurve:
            lastSegment = segments[-1]
            segment = segments.pop(0)
            lastSegment.extend(segment)
        elif segments[0][-1].segmentType != "move":
            segment = segments.pop(0)
            segments.append(segment)
        return segments

    segments = property(_get_segments, doc="A list of all points in the contour organized into segments.")

    def removeSegment(self, segmentIndex, preserveCurve=False):
        """
        Remove the segment at **segmentIndex**. If
        **preserveCurve** is True, the contour will
        try to preserve the overall curve shape.
        """
        segments = self.segments
        nextIndex = segmentIndex + 1
        if nextIndex == len(segments):
            nextIndex = 0
        previousIndex = segmentIndex - 1
        if previousIndex < 0:
            previousIndex = len(segments) + previousIndex
        nextSegment = segments[nextIndex]
        segment = segments[segmentIndex]
        previousSegment = segments[previousIndex]
        # if preserveCurve is off
        # or if all are lines, handle it
        if not preserveCurve or (previousSegment[-1].segmentType == "line"\
            and segment[-1].segmentType == "line"\
            and nextSegment[-1].segmentType == "line"):
            for point in segment:
                self._points.remove(point)
            # if we're removing a move segment, we need to forward the move to
            # the next on curve
            if segment[-1].segmentType == "move":
                for point in nextSegment[:-1]:
                    self._points.remove(point)
                nextSegment[-1].segmentType = "move"
        # if have a curve, do the preservation
        else:
            # gather the needed points
            previousOnCurveX = previousSegment[-1].x
            previousOnCurveY = previousSegment[-1].y
            onCurveX = segment[-1].x
            onCurveY = segment[-1].y
            nextOnCurveX = nextSegment[-1].x
            nextOnCurveY = nextSegment[-1].y
            if segment[-1].segmentType == "curve":
                offCurve1X = segment[0].x
                offCurve1Y = segment[0].y
                offCurve2X = segment[-2].x
                offCurve2Y = segment[-2].y
            elif segment[-1].segmentType == "line":
                offCurve1X = previousOnCurveX
                offCurve1Y = previousOnCurveY
                offCurve2X = onCurveX
                offCurve2Y = onCurveY
            else:
                # XXX could be a quad. in that case, we can't handle it.
                raise NotImplementedError("unknown segment type: %s" % segment[-1].segmentType)
            if nextSegment[-1].segmentType == "curve":
                nextOffCurve1X = nextSegment[0].x
                nextOffCurve1Y = nextSegment[0].y
                nextOffCurve2X = nextSegment[-2].x
                nextOffCurve2Y = nextSegment[-2].y
            elif nextSegment[-1].segmentType == "line":
                nextOffCurve1X = onCurveX
                nextOffCurve1Y = onCurveY
                nextOffCurve2X = nextOnCurveX
                nextOffCurve2Y = nextOnCurveY
            else:
                # XXX could be a quad. in that case, we can't handle it.
                raise NotImplementedError("unknown segment type: %s" % nextSegment[-1].segmentType)
            # now do the math
            result = bezierMath.joinSegments((previousOnCurveX, previousOnCurveY),
                (offCurve1X, offCurve1Y), (offCurve2X, offCurve2Y), (onCurveX, onCurveY),
                (nextOffCurve1X, nextOffCurve1Y), (nextOffCurve2X, nextOffCurve2Y), (nextOnCurveX, nextOnCurveY))
            # remove the segment
            for point in segment:
                self._points.remove(point)
            # if the next segment type isn't a curve, make it one
            if not nextSegment[-1].segmentType == "curve":
                nextSegment[-1].segmentType = "curve"
                pointIndex = self._points.index(nextSegment[-1])
                newPoints = [self._pointClass((result[0][0], result[0][1])), self._pointClass((result[1][0], result[1][1]))]
                if pointIndex == 0:
                    self._points.extend(newPoints)
                else:
                    self._points = self._points[:pointIndex] + newPoints + self._points[pointIndex:]
            # otherwise, set the point positions
            else:
                nextSegment[0].x = result[0][0]
                nextSegment[0].y = result[0][1]
                nextSegment[1].x = result[1][0]
                nextSegment[1].y = result[1][1]
        # mark the contour as dirty
        self.dirty = True

    # ----------------
    # Basic Attributes
    # ----------------

    # clockwise

    def _get_clockwise(self):
        area = self.getRepresentation("defcon.contour.area")
        return area < 0

    def _set_clockwise(self, value):
        if self.clockwise != value:
            self.reverse()
            self._clockwiseCache = None

    clockwise = property(_get_clockwise, _set_clockwise, doc="A boolean representing if the contour has a clockwise direction. Setting this posts *Contour.WindingDirectionChanged* and *Contour.Changed* notifications.")

    # open

    def _get_open(self):
        if not self._points:
            return True
        return self._points[0].segmentType == 'move'

    open = property(_get_open, doc="A boolean indicating if the contour is open or not.")

    # ------
    # Bounds
    # ------

    def _get_bounds(self):
        return self.getRepresentation("defcon.contour.bounds")

    bounds = property(_get_bounds, doc="The bounds of the contour's outline expressed as a tuple of form (xMin, yMin, xMax, yMax).")

    def _get_controlPointBounds(self):
        return self.getRepresentation("defcon.contour.controlPointBounds")

    controlPointBounds = property(_get_controlPointBounds, doc="The control bounds of all points in the contour. This only measures the point positions, it does not measure curves. So, curves without points at the extrema will not be properly measured.")

    # ----
    # Area
    # ----

    def _get_area(self):
        return abs(self.getRepresentation("defcon.contour.area"))

    area = property(_get_area, doc="The area of the contour's outline.")

    # ----
    # Move
    # ----

    def move(self, values):
        """
        Move all points in the contour by **(x, y)**.

        This will post *Contour.PointsChanged* and *Contour.Changed* notifications.
        """
        (x, y) = values
        for point in self._points:
            point.move((x, y))
        # update the representations
        # XXX this is strictly against the rules.
        # XXX subclasses should never, ever do
        # XXX anything like this. this is a *very*
        # XXX special case.
        if "defcon.contour.bounds" in self._representations:
            bounds = self._representations["defcon.contour.bounds"][None]
            if bounds is not None:
                xMin, yMin, xMax, yMax = bounds
                xMin += x
                yMin += y
                xMax += x
                yMax += y
                bounds = (xMin, yMin, xMax, yMax)
            self._representations["defcon.contour.bounds"][None] = bounds
        if "defcon.contour.controlPointBounds" in self._representations:
            bounds = self._representations["defcon.contour.controlPointBounds"][None]
            if bounds is not None:
                xMin, yMin, xMax, yMax = bounds
                xMin += x
                yMin += y
                xMax += x
                yMax += y
                bounds = (xMin, yMin, xMax, yMax)
            self._representations["defcon.contour.controlPointBounds"][None] = bounds
        self.disableNotifications(observer=self)
        self.postNotification("Contour.PointsChanged")
        self.enableNotifications(observer=self)
        self.dirty = True

    # ------------
    # Point Inside
    # ------------

    def pointInside(self, coordinates, evenOdd=False):
        """
        Returns a boolean indicating if **(x, y)** is in the
        "black" area of the contour.
        """
        (x, y) = coordinates
        from fontTools.pens.pointInsidePen import PointInsidePen
        pen = PointInsidePen(glyphSet=None, testPoint=(x, y), evenOdd=evenOdd)
        self.draw(pen)
        return pen.getResult()

    # --------------
    # Contour Inside
    # --------------

    def contourInside(self, other, segmentLength=10):
        """
        Returns a boolean indicating if **other** is in the
        "black" area of the contour. This uses a flattened
        version of other's curves to calculate the location
        of the curves within this contour. **segmentLength**
        defines the desired length for the flattening process.
        A lower value will yeild higher accuracy but will require
        more computation time.
        """
        if segmentLength < 1:
            segmentLength = 1
        # test bounding boxes for intersection
        rect1 = self.bounds
        rect2 = other.bounds
        if not arrayTools.sectRect(rect1, rect2)[0]:
            return False
        # test existing on curves
        testedPoints = set()
        for point in other:
            if point.segmentType is None:
                continue
            pt = (point.x, point.y)
            if pt in testedPoints:
                continue
            if not self.pointInside(pt):
                return False
            testedPoints.add(pt)
        # flatten into line and test new points
        flat2 = other.getRepresentation("defcon.contour.flattened", approximateSegmentLength=segmentLength, segmentLines=True)
        for point in flat2:
            pt = (point.x, point.y)
            if pt in testedPoints:
                continue
            if not self.pointInside(pt):
                return False
            testedPoints.add(pt)
        return True

    # ---------
    # Splitting
    # ---------

    def positionForProspectivePointInsertionAtSegmentAndT(self, segmentIndex, t):
        """
        Get the precise coordinates and a boolean indicating
        if the point will be smooth for the given **segmentIndex**
        and **t**.
        """
        return self._splitAndInsertAtSegmentAndT(segmentIndex, t, False)

    def splitAndInsertPointAtSegmentAndT(self, segmentIndex, t):
        """
        Insert a point into the contour for the given
        **segmentIndex** and **t**.

        This posts a *Contour.Changed* notification.
        """
        self._splitAndInsertAtSegmentAndT(segmentIndex, t, True)

    def _splitAndInsertAtSegmentAndT(self, segmentIndex, t, insert):
        segments = self.segments
        segment = segments[segmentIndex]
        segment.insert(0, segments[segmentIndex-1][-1])
        firstPoint = segment[0]
        lastPoint = segment[-1]
        segmentType = lastPoint.segmentType
        segment = [(point.x, point.y) for point in segment]
        if segmentType == "line":
            (x1, y1), (x2, y2) = segment
            x = x1 + (x2 - x1) * t
            y = y1 + (y2 - y1) * t
            pointsToInsert = [((x, y), "line", False)]
            insertionPoint = (x, y)
            pointWillBeSmooth = False
        elif segmentType == "curve":
            pt1, pt2, pt3, pt4 = segment
            (pt1, pt2, pt3, pt4), (pt5, pt6, pt7, pt8) = bezierTools.splitCubicAtT(pt1, pt2, pt3, pt4, t)
            pointsToInsert = [(pt2, None, False), (pt3, None, False), (pt4, "curve", True), (pt6, None, False), (pt7, None, False)]
            insertionPoint = tuple(pt4)
            pointWillBeSmooth = True
        else:
            # XXX could be a quad. in that case, we could handle it.
            raise NotImplementedError("unknown segment type: %s" % segmentType)
        if insert:
            firstPointIndex = self._points.index(firstPoint)
            lastPointIndex = self._points.index(lastPoint)
            firstPoints = self._points[:firstPointIndex + 1]
            if firstPointIndex == len(self._points) - 1:
                firstPoints = firstPoints[lastPointIndex:]
                lastPoints = []
            elif lastPointIndex == 0:
                lastPoints = []
            else:
                lastPoints = self._points[lastPointIndex:]
            newPoints = [self._pointClass(pos, segmentType=segmentType, smooth=smooth) for pos, segmentType, smooth in pointsToInsert]
            self._points = firstPoints + newPoints + lastPoints
            self.dirty = True
        return insertionPoint, pointWillBeSmooth

    # -----------
    # Pen methods
    # -----------

    def beginPath(self, identifier=None):
        """
        Standard point pen *beginPath* method.
        This should not be used externally.
        """
        self.identifier = identifier

    def endPath(self):
        """
        Standard point pen *endPath* method.
        This should not be used externally.
        """
        pass

    def addPoint(self, values, segmentType=None, smooth=False, name=None, identifier=None, **kwargs):
        """
        Standard point pen *addPoint* method.
        This should not be used externally.
        """
        (x, y) = values
        point = self._pointClass((x, y), segmentType=segmentType, smooth=smooth, name=name, identifier=identifier, **kwargs)
        self.insertPoint(len(self._points), point)

    def draw(self, pen):
        """
        Draw the contour with **pen**.
        """
        from fontTools.pens.pointPen import PointToSegmentPen
        pointPen = PointToSegmentPen(pen)
        self.drawPoints(pointPen)

    def drawPoints(self, pointPen):
        """
        Draw the contour with **pointPen**.
        """
        try:
            pointPen.beginPath(identifier=self.identifier)
        except TypeError:
            pointPen.beginPath()
            warn("The beginPath method needs an identifier kwarg. The contour's identifier value has been discarded.", DeprecationWarning)
        for point in self._points:
            try:
                pointPen.addPoint((point.x, point.y), segmentType=point.segmentType, smooth=point.smooth, name=point.name, identifier=point.identifier)
            except TypeError:
                pointPen.addPoint((point.x, point.y), segmentType=point.segmentType, smooth=point.smooth, name=point.name)
                warn("The addPoint method needs an identifier kwarg. The point's identifier value has been discarded.", DeprecationWarning)
        pointPen.endPath()

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

    identifiers = property(_get_identifiers, doc="Set of identifiers for the glyph that this contour belongs to. This is primarily for internal use.")

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
        self.postNotification("Contour.IdentifierChanged", data=dict(oldValue=oldIdentifier, newValue=value))
        self.dirty = True

    identifier = property(_get_identifier, _set_identifier, doc="The identifier. Setting this will post *Contour.IdentifierChanged* and *Contour.Changed* notifications.")

    def generateIdentifier(self):
        """
        Create a new, unique identifier for and assign it to the contour.
        This will post *Contour.IdentifierChanged* and *Contour.Changed* notifications.
        """
        if self.identifier is None:
            identifier = makeRandomIdentifier(existing=self.identifiers)
            self.identifier = identifier
        return self.identifier

    def generateIdentifierForPoint(self, point):
        """
        Create a new, unique identifier for and assign it to the point.
        This will post *Contour.Changed* notification.
        """
        if point.identifier is None:
            identifier = makeRandomIdentifier(existing=self.identifiers)
            if identifier is not None:
                self.identifiers.add(identifier)
            point.identifier = identifier
            self.dirty = True
        return point.identifier

    # ------------------------
    # Notification Observation
    # ------------------------

    def endSelfNotificationObservation(self):
        super(Contour, self).endSelfNotificationObservation()
        self._font = None
        self._layerSet = None
        self._layer = None
        self._glyph = None

    # -----------------------------
    # Serialization/Deserialization
    # -----------------------------

    def getDataForSerialization(self, **kwargs):
        def get_points(key):
            # store the point pen protocol calls
            # this will store the identifier and the point data
            pointData = []
            self.drawPoints(Recorder(pointData))
            return pointData

        getters = [('pen', get_points)]
        return self._serialize(getters, **kwargs)

    def setDataFromSerialization(self, data):
        self.clear()
        self.identifier = None
        if 'pen' in data:
            # play back
            Recorder(data['pen'])(self)


class Recorder(object):
    """
    Records all method calls it receives in a list of tuples in the form of
    [(:str:command, :list:args, :dict: kwargs)]

    Method calls to be recorded must not start with an underscore.

    This class creates a callable object which can be used like a
    function: "recorder(target)" because that way calls to all methods
    that don't start with underscores can be recorded.

    This is useful to record the commands of both pen protocols
    and it may become useful for other things as well, like recording
    undo commands.

    Example Session PointPen:

    data_glyphA = []
    recorderPointPen = Recorder(data_glyphA)
    glyphA.drawPoints(recorderPointPen)

    # The point data of the glyph is now stored within data
    # we can either replay it immediately or take it away and use it
    # to replay it later

    stored_data = pickle.dumps(data_glyphA)
    restored_data_glyphA = pickle.loads(stored_data)

    player = Recorder(restored_data_glyphA)
    # The recorder behaves like glyphA.drawPoints
    player(glyphB)

    Example Session SegmentPen:

    data_glyphA = []
    recorderPen = Recorder(data_glyphA)
    glyphA.draw(recorderPen)

    # reuse it immediately
    # The recorder behaves like glyphA.draw
    recorderPen(glyphB)
    """
    def __init__(self, data=None):
        self.__dict__['_data'] = data if data is not None else []

    def __call__(self, target):
        """
        Public API.
        Replay all method calls to this Recorder to target.
        """
        for cmd, args, kwargs in self._data:
            getattr(target, cmd)(*args, **kwargs)

    def __setattr__(self, name, value):
        raise AttributeError('It\'s not allowed to set attributes here.', name)

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)

        def command(*args, **kwargs):
            self._data.append((name, args, kwargs))
        # cache the method, don't use __setattr__
        self.__dict__[name] = command
        return command


if __name__ == "__main__":
    import doctest
    doctest.testmod()
