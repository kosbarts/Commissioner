from collections import OrderedDict
from typing import AbstractSet, Any, Iterable, Iterator, List, Optional, Sized, Union

import attr
from fontTools.ufoLib import UFOReader, UFOWriter

from ufoLib2.constants import DEFAULT_LAYER_NAME
from ufoLib2.errors import Error
from ufoLib2.objects.layer import Layer
from ufoLib2.objects.misc import _NOT_LOADED, Placeholder, _deepcopy_unlazify_attrs
from ufoLib2.typing import T


def _must_have_at_least_one_item(self: Any, attribute: Any, value: Sized) -> None:
    if not len(value):
        raise ValueError("value must have at least one item.")


@attr.s(auto_attribs=True, slots=True, repr=False)
class LayerSet:
    """Represents a mapping of layer names to Layer objects.

    See http://unifiedfontobject.org/versions/ufo3/layercontents.plist/ for layer
    semantics.

    Behavior:
        LayerSet behaves **partly** like a dictionary of type ``Dict[str, Layer]``,
        but creating and loading layers is done through their own methods. Unless the
        font is loaded eagerly (with ``lazy=False``), the layer objects and their
        glyphs are by default only loaded into memory when accessed.

        To get the number of layers in the font::

            layerCount = len(font.layers)

        To iterate over all layers::

            for layer in font.layers:
                ...

        To check if a specific layer exists::

            exists = "myLayerName" in font.layers

        To get a specific layer::

            font.layers["myLayerName"]

        To delete a specific layer::

            del font.layers["myLayerName"]
    """

    _layers: "OrderedDict[str, Union[Layer, Placeholder]]" = attr.ib(
        validator=_must_have_at_least_one_item,
    )

    defaultLayer: Layer
    """The Layer that is marked as the default, typically named ``public.default``."""

    _reader: Optional[UFOReader] = attr.ib(default=None, init=False, eq=False)

    def __attrs_post_init__(self) -> None:
        if not any(layer is self.defaultLayer for layer in self._layers.values()):
            raise ValueError(
                f"Default layer {repr(self.defaultLayer)} must be in layer set."
            )

    @classmethod
    def default(cls) -> "LayerSet":
        """Return a new LayerSet with an empty default Layer."""
        return cls.from_iterable([Layer()])

    @classmethod
    def from_iterable(
        cls, value: Iterable[Layer], defaultLayerName: str = DEFAULT_LAYER_NAME
    ) -> "LayerSet":
        """Instantiates a LayerSet from an iterable of :class:`.Layer` objects.

        Args:
            value: an iterable of :class:`.Layer` objects.
            defaultLayerName: the name of the default layer of the ones in ``value``.
        """
        layers: OrderedDict[str, Union[Layer, Placeholder]] = OrderedDict()
        defaultLayer = None
        for layer in value:
            if not isinstance(layer, Layer):
                raise TypeError(f"expected 'Layer', found '{type(layer).__name__}'")
            if layer.name in layers:
                raise KeyError(f"duplicate layer name: '{layer.name}'")
            if layer.name == defaultLayerName:
                defaultLayer = layer
            layers[layer.name] = layer

        if defaultLayerName not in layers:
            raise ValueError(f"expected one layer named '{defaultLayerName}'.")
        assert defaultLayer is not None

        return cls(layers=layers, defaultLayer=defaultLayer)

    @classmethod
    def read(cls, reader: UFOReader, lazy: bool = True) -> "LayerSet":
        """Instantiates a LayerSet object from a :class:`fontTools.ufoLib.UFOReader`.

        Args:
            path: The path to the UFO to load.
            lazy: If True, load glyphs, data files and images as they are accessed. If
                False, load everything up front.
        """
        layers: OrderedDict[str, Union[Layer, Placeholder]] = OrderedDict()
        defaultLayer = None

        defaultLayerName = reader.getDefaultLayerName()

        for layerName in reader.getLayerNames():
            isDefault = layerName == defaultLayerName
            if isDefault or not lazy:
                layer = cls._loadLayer(reader, layerName, lazy)
                if isDefault:
                    defaultLayer = layer
                layers[layerName] = layer
            else:
                layers[layerName] = _NOT_LOADED

        assert defaultLayer is not None

        self = cls(layers=layers, defaultLayer=defaultLayer)
        if lazy:
            self._reader = reader

        return self

    def unlazify(self) -> None:
        """Load all layers into memory."""
        for layer in self:
            layer.unlazify()

    __deepcopy__ = _deepcopy_unlazify_attrs

    @staticmethod
    def _loadLayer(reader: UFOReader, layerName: str, lazy: bool = True) -> Layer:
        glyphSet = reader.getGlyphSet(layerName)
        return Layer.read(layerName, glyphSet, lazy=lazy)

    def loadLayer(self, layerName: str, lazy: bool = True) -> Layer:
        # XXX: Remove this method and do business via _loadLayer or take this one
        # private.
        assert self._reader is not None
        if layerName not in self._layers:
            raise KeyError(layerName)
        layer = self._loadLayer(self._reader, layerName, lazy)
        self._layers[layerName] = layer
        return layer

    def __contains__(self, name: str) -> bool:
        return name in self._layers

    def __delitem__(self, name: str) -> None:
        if self.defaultLayer is not None:
            if name == self.defaultLayer.name:
                raise KeyError("cannot delete default layer %r" % name)
        del self._layers[name]

    def __getitem__(self, name: str) -> Layer:
        layer_object = self._layers[name]
        if isinstance(layer_object, Placeholder):
            return self.loadLayer(name)
        return layer_object

    def __iter__(self) -> Iterator[Layer]:
        for layer_name, layer_object in self._layers.items():
            if isinstance(layer_object, Placeholder):
                yield self.loadLayer(layer_name)
            else:
                yield layer_object

    def __len__(self) -> int:
        return len(self._layers)

    def get(self, name: str, default: Optional[T] = None) -> Union[Optional[T], Layer]:
        try:
            return self[name]
        except KeyError:
            return default

    def keys(self) -> AbstractSet[str]:
        return self._layers.keys()

    def __repr__(self) -> str:
        n = len(self._layers)
        return "<{}.{} ({} layer{}) at {}>".format(
            self.__class__.__module__,
            self.__class__.__name__,
            n,
            "s" if n > 1 else "",
            hex(id(self)),
        )

    @property
    def layerOrder(self) -> List[str]:
        """The font's layer order.

        Getter:
            Returns the font's layer order.

        Note:
            The getter always returns a new list, modifications to it do not change
            the LayerSet.

        Setter:
            Sets the font's layer order. The set order value must contain all layers
            that are present in the LayerSet.
        """
        return list(self._layers)

    @layerOrder.setter
    def layerOrder(self, order: List[str]) -> None:
        if set(order) != set(self._layers):
            raise Error(
                "`order` must contain the same layers that are currently present."
            )
        layers = OrderedDict()
        for name in order:
            layers[name] = self._layers[name]
        self._layers = layers

    def newLayer(self, name: str, **kwargs: Any) -> Layer:
        """Creates and returns a named layer.

        Args:
            name: The layer name.
            kwargs: Arguments passed to the constructor of Layer.
        """
        if name in self._layers:
            raise KeyError("layer %r already exists" % name)
        self._layers[name] = layer = Layer(name, **kwargs)
        return layer

    def renameGlyph(self, name: str, newName: str, overwrite: bool = False) -> None:
        """Renames a glyph across all layers.

        Args:
            name: The old name.
            newName: The new name.
            overwrite: If False, raises exception if newName is already taken in any
                layer. If True, overwrites (read: deletes) the old Glyph object.
        """
        # Note: this would be easier if the glyph contained the layers!
        if name == newName:
            return
        # make sure we're copying something
        if not any(name in layer for layer in self):
            raise KeyError("name %r is not in layer set" % name)
        # prepare destination, delete if overwrite=True or error
        for layer in self:
            if newName in layer:
                if overwrite:
                    del layer[newName]
                else:
                    raise KeyError("target name %r already exists" % newName)
        # now do the move
        for layer in self:
            if name in layer:
                layer[newName] = glyph = layer.pop(name)
                glyph._name = newName

    def renameLayer(self, name: str, newName: str, overwrite: bool = False) -> None:
        """Renames a layer.

        Args:
            name: The old name.
            newName: The new name.
            overwrite: If False, raises exception if newName is already taken. If True,
                overwrites (read: deletes) the old Layer object.
        """
        if name == newName:
            return
        if not overwrite and newName in self._layers:
            raise KeyError("target name %r already exists" % newName)
        layer = self[name]
        del self._layers[name]
        self._layers[newName] = layer
        layer._name = newName

    def write(self, writer: UFOWriter, saveAs: Optional[bool] = None) -> None:
        """Writes this LayerSet to a :class:`fontTools.ufoLib.UFOWriter`.

        Args:
            writer(fontTools.ufoLib.UFOWriter): The writer to write to.
            saveAs: If True, tells the writer to save out-of-place. If False, tells the
                writer to save in-place. This affects how resources are cleaned before
                writing.
        """
        if saveAs is None:
            saveAs = self._reader is not writer
        # if in-place, remove deleted layers
        layers = self._layers
        if not saveAs:
            for name in set(writer.getLayerNames()).difference(layers):
                writer.deleteGlyphSet(name)
        # write layers
        defaultLayer = self.defaultLayer
        for name, layer in layers.items():
            default = layer is defaultLayer
            if isinstance(layer, Placeholder):
                if saveAs:
                    layer = self.loadLayer(name, lazy=False)
                else:
                    continue
            glyphSet = writer.getGlyphSet(name, defaultLayer=default)
            layer.write(glyphSet, saveAs=saveAs)
        writer.writeLayerContents(self.layerOrder)
