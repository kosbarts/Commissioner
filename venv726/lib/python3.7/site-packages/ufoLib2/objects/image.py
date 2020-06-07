from collections.abc import Mapping
from typing import Any, Iterator, Optional, Tuple

import attr
from fontTools.misc.transform import Identity, Transform

from .misc import _convert_transform


@attr.s(auto_attribs=True, slots=True)
class Image(Mapping):
    """Represents a background image reference.

    See http://unifiedfontobject.org/versions/ufo3/images/ and
    http://unifiedfontobject.org/versions/ufo3/glyphs/glif/#image.
    """

    fileName: Optional[str] = None
    """The filename of the image."""

    transformation: Transform = attr.ib(default=Identity, converter=_convert_transform)
    """The affine transformation applied to the image."""

    color: Optional[str] = None
    """The color applied to the image."""

    def clear(self) -> None:
        """Resets the image reference to factory settings."""
        self.fileName = None
        self.transformation = Identity
        self.color = None

    def __bool__(self) -> bool:
        """Indicates whether fileName is set."""
        return self.fileName is not None

    # implementation of collections.abc.Mapping abstract methods.
    # the fontTools.ufoLib.validators.imageValidator requires that image is a
    # subclass of Mapping...

    _transformation_keys_: Tuple[str, str, str, str, str, str] = (
        "xScale",
        "xyScale",
        "yxScale",
        "yScale",
        "xOffset",
        "yOffset",
    )
    _valid_keys_: Tuple[str, str, str, str, str, str, str, str] = (
        "fileName",
    ) + _transformation_keys_ + ("color",)

    def __getitem__(self, key: str) -> Any:
        try:
            i = self._transformation_keys_.index(key)
        except ValueError:
            try:
                return getattr(self, key)
            except AttributeError:
                raise KeyError(key)
        else:
            return self.transformation[i]

    def __len__(self) -> int:
        return len(self._valid_keys_)

    def __iter__(self) -> Iterator[str]:
        return iter(self._valid_keys_)
