from typing import TYPE_CHECKING, Any, Optional, Tuple

from fontTools.misc.transform import Transform
from fontTools.pens.pointPen import AbstractPointPen

from ufoLib2.objects.component import Component
from ufoLib2.objects.contour import Contour
from ufoLib2.objects.point import Point

if TYPE_CHECKING:
    from ufoLib2.objects.glyph import Glyph


class GlyphPointPen(AbstractPointPen):
    """A point pen.

    See :mod:`fontTools.pens.basePen` and :mod:`fontTools.pens.pointPen` for an
    introduction to pens.
    """

    __slots__ = "_glyph", "_contour"

    def __init__(self, glyph: "Glyph") -> None:
        self._glyph: "Glyph" = glyph
        self._contour: Optional[Contour] = None

    def beginPath(self, identifier: Optional[str] = None, **kwargs: Any) -> None:
        self._contour = Contour(identifier=identifier)

    def endPath(self) -> None:
        if self._contour is None:
            raise ValueError("Call beginPath first.")
        self._glyph.contours.append(self._contour)
        self._contour = None

    def addPoint(
        self,
        pt: Tuple[float, float],
        segmentType: Optional[str] = None,
        smooth: bool = False,
        name: Optional[str] = None,
        identifier: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        if self._contour is None:
            raise ValueError("Call beginPath first.")
        x, y = pt
        self._contour.append(
            Point(
                x, y, type=segmentType, smooth=smooth, name=name, identifier=identifier
            )
        )

    def addComponent(
        self,
        baseGlyph: str,
        transformation: Transform,
        identifier: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        component = Component(baseGlyph, transformation, identifier=identifier)
        self._glyph.components.append(component)
