from __future__ import print_function, division, absolute_import, unicode_literals

import math
from collections import namedtuple
import logging

from ufo2ft.fontInfoData import getAttrWithFallback
from ufo2ft.filters import BaseFilter

from fontTools.misc.py23 import round
from fontTools.misc.fixedTools import otRound
from fontTools.misc.transform import Transform, Identity
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.transformPen import TransformPen as _TransformPen
from enum import IntEnum


log = logging.getLogger(__name__)


class TransformPen(_TransformPen):
    def __init__(self, outPen, transformation, modified=None):
        super(TransformPen, self).__init__(outPen, transformation)
        self.modified = modified if modified is not None else set()
        self._inverted = self._transformation.inverse()

    def addComponent(self, baseGlyph, transformation):
        if baseGlyph in self.modified:

            if transformation[:4] == (1, 0, 0, 1):
                # if the component's transform only has a simple offset, then
                # we don't need to transform the component again
                self._outPen.addComponent(baseGlyph, transformation)
                return

            # multiply the component's transformation matrix with the inverse
            # of the filter's transformation matrix to compensate for the
            # transformation already applied to the base glyph
            transformation = Transform(*transformation).transform(self._inverted)

        super(TransformPen, self).addComponent(baseGlyph, transformation)


class TransformationsFilter(BaseFilter):
    class Origin(IntEnum):
        CAP_HEIGHT = 0
        HALF_CAP_HEIGHT = 1
        X_HEIGHT = 2
        HALF_X_HEIGHT = 3
        BASELINE = 4

    _kwargs = {
        "OffsetX": 0,
        "OffsetY": 0,
        "ScaleX": 100,
        "ScaleY": 100,
        "Slant": 0,
        "Origin": 4,  # BASELINE
    }

    def start(self):
        self.options.Origin = self.Origin(self.options.Origin)

    def get_origin_height(self, font, origin):
        if origin is self.Origin.BASELINE:
            return 0
        elif origin is self.Origin.CAP_HEIGHT:
            return getAttrWithFallback(font.info, "capHeight")
        elif origin is self.Origin.HALF_CAP_HEIGHT:
            return otRound(getAttrWithFallback(font.info, "capHeight") / 2)
        elif origin is self.Origin.X_HEIGHT:
            return getAttrWithFallback(font.info, "xHeight")
        elif origin is self.Origin.HALF_X_HEIGHT:
            return otRound(getAttrWithFallback(font.info, "xHeight") / 2)
        else:
            raise AssertionError(origin)

    def set_context(self, font, glyphSet):
        ctx = super(TransformationsFilter, self).set_context(font, glyphSet)

        origin_height = self.get_origin_height(font, self.options.Origin)

        m = Identity
        dx, dy = self.options.OffsetX, self.options.OffsetY
        if dx != 0 or dy != 0:
            m = m.translate(dx, dy)

        sx, sy = self.options.ScaleX, self.options.ScaleY
        angle = self.options.Slant
        # TODO Add support for "Cursify" option
        # cursify = self.options.SlantCorrection
        if sx != 100 or sy != 100 or angle != 0:
            # vertically shift glyph to the specified 'Origin' before
            # scaling and/or slanting, then move it back
            if origin_height != 0:
                m = m.translate(0, origin_height)
            if sx != 100 or sy != 100:
                m = m.scale(sx / 100, sy / 100)
            if angle != 0:
                m = m.skew(math.radians(angle))
            if origin_height != 0:
                m = m.translate(0, -origin_height)

        ctx.matrix = m

        return ctx

    def filter(self, glyph):
        matrix = self.context.matrix
        if matrix == Identity or not (glyph or glyph.components or glyph.anchors):
            return False  # nothing to do

        modified = self.context.modified
        glyphSet = self.context.glyphSet
        for component in glyph.components:
            base_name = component.baseGlyph
            if base_name in modified:
                continue
            base_glyph = glyphSet[base_name]
            if self.include(base_glyph) and self.filter(base_glyph):
                # base glyph is included but was not transformed yet; we
                # call filter recursively until all the included bases are
                # transformed, or there are no more components
                modified.add(base_name)

        rec = RecordingPen()
        glyph.draw(rec)
        glyph.clearContours()
        glyph.clearComponents()

        outpen = glyph.getPen()
        filterpen = TransformPen(outpen, matrix, modified)
        rec.replay(filterpen)

        # anchors are not drawn through the pen API,
        # must be transformed separately
        for a in glyph.anchors:
            a.x, a.y = matrix.transformPoint((a.x, a.y))

        return True
