import attr


@attr.s(auto_attribs=True, slots=True)
class Features:
    """A data class representing UFO features.

    See http://unifiedfontobject.org/versions/ufo3/features.fea/.
    """

    text: str = ""
    """Holds the content of the features.fea file."""

    def __bool__(self) -> bool:
        return bool(self.text)

    def __str__(self) -> str:
        return self.text
