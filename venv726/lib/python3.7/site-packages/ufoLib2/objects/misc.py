from abc import abstractmethod
from collections.abc import Mapping, MutableMapping
from copy import deepcopy
from typing import (
    Any,
    Dict,
    Iterator,
    List,
    NamedTuple,
    Optional,
    Sequence,
    Set,
    Type,
    TypeVar,
    Union,
)

import attr
from fontTools.misc.transform import Transform
from fontTools.pens.boundsPen import BoundsPen, ControlBoundsPen
from fontTools.ufoLib import UFOReader, UFOWriter

from ufoLib2.typing import Drawable


class BoundingBox(NamedTuple):
    """Represents a bounding box as a tuple of (xMin, yMin, xMax, yMax)."""

    xMin: float
    yMin: float
    xMax: float
    yMax: float


def getBounds(drawable: Drawable, layer: Any) -> Optional[BoundingBox]:
    # XXX: layer should behave like a mapping of glyph names to Glyph objects, but
    # cyclic imports...
    pen = BoundsPen(layer)
    # raise 'KeyError' when a referenced component is missing from glyph set
    pen.skipMissingComponents = False
    drawable.draw(pen)
    return None if pen.bounds is None else BoundingBox(*pen.bounds)


def getControlBounds(drawable: Drawable, layer: Any) -> Optional[BoundingBox]:
    # XXX: layer should behave like a mapping of glyph names to Glyph objects, but
    # cyclic imports...
    pen = ControlBoundsPen(layer)
    # raise 'KeyError' when a referenced component is missing from glyph set
    pen.skipMissingComponents = False
    drawable.draw(pen)
    return None if pen.bounds is None else BoundingBox(*pen.bounds)


def _deepcopy_unlazify_attrs(self: Any, memo: Any) -> Any:
    if getattr(self, "_lazy", True) and hasattr(self, "unlazify"):
        self.unlazify()
    return self.__class__(
        **{
            (a.name if a.name[0] != "_" else a.name[1:]): deepcopy(
                getattr(self, a.name), memo
            )
            for a in attr.fields(self.__class__)
            if a.init and a.metadata.get("copyable", True)
        },
    )


class Placeholder:
    """Represents a sentinel value to signal a "lazy" object hasn't been loaded yet."""


_NOT_LOADED = Placeholder()


# Create a generic variable for mypy that can be 'DataStore' or any subclass.
Tds = TypeVar("Tds", bound="DataStore")


@attr.s(auto_attribs=True, slots=True, repr=False)
class DataStore(MutableMapping):
    """Represents the base class for ImageSet and DataSet.

    Both behave like a dictionary that loads its "values" lazily by default and only
    differ in which reader and writer methods they call.
    """

    _data: Dict[str, Union[bytes, Placeholder]] = attr.ib(factory=dict)

    _reader: Optional[UFOReader] = attr.ib(
        default=None, init=False, repr=False, eq=False
    )
    _scheduledForDeletion: Set[str] = attr.ib(factory=set, init=False, repr=False)

    @classmethod
    def read(cls: Type[Tds], reader: UFOReader, lazy: bool = True) -> Tds:
        """Instantiate the data store from a :class:`fontTools.ufoLib.UFOReader`."""
        self = cls()
        for fileName in cls.list_contents(reader):
            if lazy:
                self._data[fileName] = _NOT_LOADED
            else:
                self._data[fileName] = cls.read_data(reader, fileName)
        if lazy:
            self._reader = reader
        return self

    @staticmethod
    @abstractmethod
    def list_contents(reader: UFOReader) -> List[str]:
        """Returns a list of POSIX filename strings in the data store."""
        ...

    @staticmethod
    @abstractmethod
    def read_data(reader: UFOReader, filename: str) -> bytes:
        """Returns the data at filename within the store."""
        ...

    @staticmethod
    @abstractmethod
    def write_data(writer: UFOWriter, filename: str, data: bytes) -> None:
        """Writes the data to filename within the store."""
        ...

    @staticmethod
    @abstractmethod
    def remove_data(writer: UFOWriter, filename: str) -> None:
        """Remove the data at filename within the store."""
        ...

    def unlazify(self) -> None:
        """Load all data into memory."""
        for _ in self.items():
            pass

    __deepcopy__ = _deepcopy_unlazify_attrs

    # MutableMapping methods

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __getitem__(self, fileName: str) -> bytes:
        data_object = self._data[fileName]
        if isinstance(data_object, Placeholder):
            data_object = self._data[fileName] = self.read_data(self._reader, fileName)
        return data_object

    def __setitem__(self, fileName: str, data: bytes) -> None:
        # should we forbid overwrite?
        self._data[fileName] = data
        if fileName in self._scheduledForDeletion:
            self._scheduledForDeletion.remove(fileName)

    def __delitem__(self, fileName: str) -> None:
        del self._data[fileName]
        self._scheduledForDeletion.add(fileName)

    def __repr__(self) -> str:
        n = len(self._data)
        return "<{}.{} ({}) at {}>".format(
            self.__class__.__module__,
            self.__class__.__name__,
            "empty" if n == 0 else "{} file{}".format(n, "s" if n > 1 else ""),
            hex(id(self)),
        )

    def write(self, writer: UFOWriter, saveAs: Optional[bool] = None) -> None:
        """Write the data store to a :class:`fontTools.ufoLib.UFOWriter`."""
        if saveAs is None:
            saveAs = self._reader is not writer
        # if in-place, remove deleted data
        if not saveAs:
            for fileName in self._scheduledForDeletion:
                self.remove_data(writer, fileName)
        # Write data. Iterating over _data.items() prevents automatic loading.
        for fileName, data in self._data.items():
            # Two paths:
            # 1) We are saving in-place. Only write to disk what is loaded, it
            #    might be modified.
            # 2) We save elsewhere. Load all data files to write them back out.
            # XXX: Move write_data into `if saveAs` branch to simplify code?
            if isinstance(data, Placeholder):
                if saveAs:
                    data = self.read_data(self._reader, fileName)
                    self._data[fileName] = data
                else:
                    continue
            self.write_data(writer, fileName, data)
        self._scheduledForDeletion = set()
        if saveAs:
            # all data was read by now, ref to reader no longer needed
            self._reader = None

    @property
    def fileNames(self) -> List[str]:
        """Returns a list of filenames in the data store."""
        return list(self._data.keys())


class AttrDictMixin(Mapping):
    """Read attribute values using mapping interface.

    For use with Anchors and Guidelines classes, where client code
    expects them to behave as dict.
    """

    # XXX: Use generics?

    def __getitem__(self, key: str) -> Any:
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(key)

    def __iter__(self) -> Iterator[Any]:
        for key in attr.fields_dict(self.__class__):
            if getattr(self, key) is not None:
                yield key

    def __len__(self) -> int:
        return sum(1 for _ in self)


def _convert_transform(t: Union[Transform, Sequence[float]]) -> Transform:
    """Return a passed-in Transform as is, otherwise convert a sequence of
    numbers to a Transform if need be."""
    return t if isinstance(t, Transform) else Transform(*t)
