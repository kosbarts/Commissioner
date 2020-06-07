from __future__ import absolute_import
from fontTools.pens.areaPen import AreaPen
from fontTools.pens.boundsPen import ControlBoundsPen, BoundsPen
from fontTools.misc.arrayTools import unionRect

# ------
# Groups
# ------

def kerningSide1GroupsRepresentationFactory(groups):
    return _gatherGroupsWithPrefix(groups, "public.kern1.")

def kerningSide2GroupsRepresentationFactory(groups):
    return _gatherGroupsWithPrefix(groups, "public.kern2.")

def _gatherGroupsWithPrefix(groups, prefix):
    found = {}
    for name, glyphNames in groups.items():
        if name.startswith(prefix):
            found[name] = glyphNames
    return found

def glyphToKerningSide1GroupsRepresentationFactory(groups):
    groups = groups.getRepresentation("defcon.groups.kerningSide1Groups")
    return _makeGlyphToGroupMapping(groups)

def glyphToKerningSide2GroupsRepresentationFactory(groups):
    groups = groups.getRepresentation("defcon.groups.kerningSide2Groups")
    return _makeGlyphToGroupMapping(groups)

def _makeGlyphToGroupMapping(groups):
    glyphToGroup = {}
    for groupName, glyphNames in groups.items():
        for glyphName in glyphNames:
            glyphToGroup[glyphName] = groupName
    return glyphToGroup

# -----
# Glyph
# -----

def glyphAreaRepresentationFactory(glyph):
    pen = AreaPen()
    glyph.draw(pen)
    return abs(pen.value)

# -------
# Contour
# -------

# bounds

def contourBoundsRepresentationFactory(obj):
    pen = BoundsPen(None)
    obj.draw(pen)
    return pen.bounds

def contourControlPointBoundsRepresentationFactory(obj):
    pen = ControlBoundsPen(None)
    obj.draw(pen)
    return pen.bounds

# area

def contourAreaRepresentationFactory(contour):
    pen = AreaPen()
    pen._endPath = pen._closePath
    contour.draw(pen)
    return pen.value

# flattened

def contourFlattenedRepresentationFactory(contour, approximateSegmentLength=5, segmentLines=False):
    from fontPens.flattenPen import FlattenPen
    from defcon.objects.glyph import Glyph
    contourClass = contour.__class__
    glyph = Glyph(contourClass=contourClass)
    outputPen = glyph.getPen()
    flattenPen = FlattenPen(outputPen, approximateSegmentLength=approximateSegmentLength, segmentLines=segmentLines)
    contour.draw(flattenPen)
    output = glyph[0]
    return output

# ---------
# Component
# ---------

# bounds

def componentBoundsRepresentationFactory(obj):
    pen = BoundsPen(obj.layer)
    obj.draw(pen)
    return pen.bounds

def componentPointBoundsRepresentationFactory(obj):
    pen = ControlBoundsPen(obj.layer)
    obj.draw(pen)
    return pen.bounds
