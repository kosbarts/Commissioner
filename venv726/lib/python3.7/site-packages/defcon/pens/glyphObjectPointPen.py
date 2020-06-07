from fontTools.pens.pointPen import AbstractPointPen

class GlyphObjectPointPen(AbstractPointPen):

    def __init__(self, glyph):
        self._glyph = glyph
        self._contour = None
        self.skipConflictingIdentifiers = False

    def beginPath(self, identifier=None, **kwargs):
        self._contour = self._glyph.instantiateContour()
        self._contour.disableNotifications()
        if identifier is not None:
            if self.skipConflictingIdentifiers and identifier in self._glyph.identifiers:
                pass
            else:
                self._contour.identifier = identifier

    def endPath(self):
        self._contour.dirty = False
        self._glyph.appendContour(self._contour)
        self._contour.enableNotifications()
        self._contour = None

    def addPoint(self, pt, segmentType=None, smooth=False, name=None, identifier=None, **kwargs):
        if self.skipConflictingIdentifiers and identifier in self._glyph.identifiers:
            identifier = None
        self._contour.addPoint(pt, segmentType, smooth, name, identifier=identifier)

    def addComponent(self, baseGlyphName, transformation, identifier=None, **kwargs):
        if self.skipConflictingIdentifiers and identifier in self._glyph.identifiers:
            identifier = None
        component = self._glyph.instantiateComponent()
        component.baseGlyph = baseGlyphName
        component.transformation = transformation
        component.identifier = identifier
        self._glyph.appendComponent(component)


class GlyphObjectLoadingPointPen(GlyphObjectPointPen):

    def __init__(self, glyph):
        super(GlyphObjectLoadingPointPen, self).__init__(glyph)
        self._contours = glyph._shallowLoadedContours

    def beginPath(self, identifier=None, **kwargs):
        contour = dict(points=[])
        if identifier is not None and self.skipConflictingIdentifiers and identifier in self._glyph.identifiers:
            identifier = None
        if identifier is not None:
            if identifier in self._glyph.identifiers:
                raise DefconError("The contour identifier (%s) is already used." % identifier)
            # FIXME: we should do self._glyph.identifiers.add(identifier)
            # otherwise the shallow contours could define the same identifier multiple times
            # or even between shallow loading and real loading something else could
            # take the identifier. The check above is pretty much worthless
            # without storing the identifier.
            contour["identifier"] = identifier
        self._contours.append(contour)

    def endPath(self):
        pass

    def addPoint(self, pt, segmentType=None, smooth=False, name=None, identifier=None, **kwargs):
        args = (pt,)
        kwargs = dict(
            segmentType=segmentType,
            smooth=smooth,
            name=name
        )
        if identifier is not None and self.skipConflictingIdentifiers and identifier in self._glyph.identifiers:
            identifier = None
        if identifier is not None:
            if identifier in self._glyph.identifiers:
                raise DefconError("The contour identifier (%s) is already used." % identifier)
            # FIXME: we should do self._glyph.identifiers.add(identifier)
            # otherwise the shallow contours could define the same identifier multiple times
            # or even between shallow loading and real loading something else could
            # take the identifier. The check above is pretty much worthless
            # without storing the identifier.
            kwargs["identifier"] = identifier
        self._contours[-1]["points"].append((args, kwargs))
