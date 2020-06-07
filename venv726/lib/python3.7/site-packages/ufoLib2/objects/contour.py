import warnings
from collections.abc import MutableSequence
from typing import (
    TYPE_CHECKING,
    Iterable,
    Iterator,
    List,
    Optional,
    Tuple,
    Union,
    overload,
)

import attr
from fontTools.pens.basePen import AbstractPen
from fontTools.pens.pointPen import AbstractPointPen, PointToSegmentPen

from ufoLib2.objects.misc import BoundingBox, getBounds, getControlBounds
from ufoLib2.objects.point import Point

if TYPE_CHECKING:
    from ufoLib2.objects.layer import Layer  # noqa: F401


@attr.s(auto_attribs=True, slots=True)
class Contour(MutableSequence):
    """Represents a contour as a list of points.

    Behavior:
        The Contour object has list-like behavior. This behavior allows you to interact
        with point data directly. For example, to get a particular point::

            point = contour[0]

        To iterate over all points::

            for point in contour:
                ...

        To get the number of points::

            pointCount = len(contour)

        To delete a particular point::

            del contour[0]

        To set a particular point to another Point object::

            contour[0] = anotherPoint
    """

    points: List[Point] = attr.ib(factory=list)
    """The list of points in the contour."""

    identifier: Optional[str] = attr.ib(default=None, repr=False)
    """The globally unique identifier of the contour."""

    # collections.abc.MutableSequence interface

    def __delitem__(self, index: Union[int, slice]) -> None:
        del self.points[index]

    @overload
    def __getitem__(self, index: int) -> Point:
        ...

    @overload
    def __getitem__(self, index: slice) -> List[Point]:  # noqa: F811
        ...

    def __getitem__(  # noqa: F811
        self, index: Union[int, slice]
    ) -> Union[Point, List[Point]]:
        return self.points[index]

    def __setitem__(  # noqa: F811
        self, index: Union[int, slice], point: Union[Point, Iterable[Point]]
    ) -> None:
        if isinstance(index, int) and isinstance(point, Point):
            self.points[index] = point
        elif (
            isinstance(index, slice)
            and isinstance(point, Iterable)
            and all(isinstance(p, Point) for p in point)
        ):
            self.points[index] = point
        else:
            raise TypeError(
                f"Expected Point or Iterable[Point], found {type(point).__name__}."
            )

    def __iter__(self) -> Iterator[Point]:
        return iter(self.points)

    def __len__(self) -> int:
        return len(self.points)

    def insert(self, index: int, point: Point) -> None:
        """Insert Point object ``point`` into the contour at ``index``."""
        if not isinstance(point, Point):
            raise TypeError(f"Expected Point, found {type(point).__name__}.")
        self.points.insert(index, point)

    # TODO: rotate method?

    @property
    def open(self) -> bool:
        """Returns whether the contour is open or closed."""
        if not self.points:
            return True
        return self.points[0].type == "move"

    def move(self, delta: Tuple[float, float]) -> None:
        """Moves contour by (x, y) font units."""
        for point in self.points:
            point.move(delta)

    def getBounds(self, layer: Optional["Layer"] = None) -> Optional[BoundingBox]:
        """Returns the (xMin, yMin, xMax, yMax) bounding box of the glyph,
        taking the actual contours into account.

        Args:
            layer: Not applicable to contours, here for API symmetry.
        """
        return getBounds(self, layer)

    @property
    def bounds(self) -> Optional[BoundingBox]:
        """Returns the (xMin, yMin, xMax, yMax) bounding box of the glyph,
        taking the actual contours into account.

        |defcon_compat|
        """
        return self.getBounds()

    def getControlBounds(
        self, layer: Optional["Layer"] = None
    ) -> Optional[BoundingBox]:
        """Returns the (xMin, yMin, xMax, yMax) bounding box of the glyph,
        taking only the control points into account.

        Gives inaccurate results with extruding curvatures.

        Args:
            layer: Not applicable to contours, here for API symmetry.
        """
        return getControlBounds(self, layer)

    # XXX: Add property controlPointBounds (defcon compat API)?

    # -----------
    # Pen methods
    # -----------

    def draw(self, pen: AbstractPen) -> None:
        """Draws contour into given pen."""
        pointPen = PointToSegmentPen(pen)
        self.drawPoints(pointPen)

    def drawPoints(self, pointPen: AbstractPointPen) -> None:
        """Draws points of contour into given point pen."""
        try:
            pointPen.beginPath(identifier=self.identifier)
            for p in self.points:
                pointPen.addPoint(
                    (p.x, p.y),
                    segmentType=p.type,
                    smooth=p.smooth,
                    name=p.name,
                    identifier=p.identifier,
                )
        except TypeError:
            pointPen.beginPath()
            for p in self.points:
                pointPen.addPoint(
                    (p.x, p.y), segmentType=p.type, smooth=p.smooth, name=p.name
                )
            warnings.warn(
                "The pointPen needs an identifier kwarg. "
                "Identifiers have been discarded.",
                UserWarning,
            )
        pointPen.endPath()
