"""
PointPen for reversing the winding direction of contours.

NOTE: The module is deprecated and the ``ReverseContourPointPen`` class has
been moved to ``fontTools.pens.pointPen`` module.
"""

from fontTools.pens.pointPen import AbstractPointPen, ReverseContourPointPen
import warnings


warnings.warn(
    "Importing the `defcon.pens.reverseContourPointPen` module is deprecated. "
    "Use `from fontTools.pens.pointPen import ReverseContourPointPen` instead.",
    DeprecationWarning, stacklevel=2)
