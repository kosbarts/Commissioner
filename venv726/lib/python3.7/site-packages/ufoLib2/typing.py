import os
import sys
from typing import TypeVar, Union

from fontTools.pens.basePen import AbstractPen

if sys.version_info >= (3, 8):
    from typing import Protocol
else:
    from typing_extensions import Protocol


T = TypeVar("T")
"""Generic variable for mypy for trivial generic function signatures."""

PathLike = Union[str, bytes, os.PathLike]
"""Represents a path in various possible forms."""


class Drawable(Protocol):
    """Stand-in for an object that can draw itself with a given pen.

    See :mod:`fontTools.pens.basePen` for an introduction to pens.
    """

    def draw(self, pen: AbstractPen) -> None:
        ...
