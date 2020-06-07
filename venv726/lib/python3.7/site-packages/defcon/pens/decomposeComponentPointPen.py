from __future__ import absolute_import
from defcon.pens.glyphObjectPointPen import GlyphObjectPointPen
from defcon.pens.transformPointPen import TransformPointPen
from defcon.objects.component import _defaultTransformation


class DecomposeComponentPointPen(GlyphObjectPointPen):

    def __init__(self, glyph, layer):
        self._layer = layer
        super(DecomposeComponentPointPen, self).__init__(glyph)

    def addComponent(self, baseGlyphName, transformation, identifier=None, **kwargs):
        if baseGlyphName in self._layer:
            baseGlyph = self._layer[baseGlyphName]
            if transformation == _defaultTransformation:
                baseGlyph.drawPoints(self)
            else:
                transformPointPen = TransformPointPen(self, transformation)
                baseGlyph.drawPoints(transformPointPen)
