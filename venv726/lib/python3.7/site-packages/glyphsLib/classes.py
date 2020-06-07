# Copyright 2016 Georg Seifert. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import copy
import logging
import math
import os
import re
import uuid
from collections import OrderedDict
from io import StringIO
from typing import Any, Dict, Optional, Tuple, Union

from fontTools.pens.basePen import AbstractPen
from fontTools.pens.pointPen import (
    AbstractPointPen,
    PointToSegmentPen,
    SegmentToPointPen,
)

import glyphsLib
from glyphsLib.affine import Affine
from glyphsLib.parser import Parser
from glyphsLib.types import (
    Point,
    Rect,
    Transform,
    UnicodesList,
    ValueType,
    floatToString5,
    parse_color,
    parse_datetime,
    parse_float_or_int,
    readIntlist,
)
from glyphsLib.writer import Writer

logger = logging.getLogger(__name__)

__all__ = [
    "Glyphs",
    "GSFont",
    "GSFontMaster",
    "GSAlignmentZone",
    "GSInstance",
    "GSCustomParameter",
    "GSClass",
    "GSFeaturePrefix",
    "GSFeature",
    "GSGlyph",
    "GSLayer",
    "GSAnchor",
    "GSComponent",
    "GSSmartComponentAxis",
    "GSPath",
    "GSNode",
    "GSGuideLine",
    "GSAnnotation",
    "GSHint",
    "GSBackgroundImage",
    # Constants
    "__all__",
    "MOVE",
    "LINE",
    "CURVE",
    "QCURVE",
    "OFFCURVE",
    "GSMOVE",
    "GSLINE",
    "GSCURVE",
    "GSOFFCURVE",
    "GSSHARP",
    "GSSMOOTH",
    "TAG",
    "TOPGHOST",
    "STEM",
    "BOTTOMGHOST",
    "TTANCHOR",
    "TTSTEM",
    "TTALIGN",
    "TTINTERPOLATE",
    "TTDIAGONAL",
    "TTDELTA",
    "CORNER",
    "CAP",
    "TTDONTROUND",
    "TTROUND",
    "TTROUNDUP",
    "TTROUNDDOWN",
    "TRIPLE",
    "TEXT",
    "ARROW",
    "CIRCLE",
    "PLUS",
    "MINUS",
    "LTR",
    "RTL",
    "LTRTTB",
    "RTLTTB",
    "GSTopLeft",
    "GSTopCenter",
    "GSTopRight",
    "GSCenterLeft",
    "GSCenterCenter",
    "GSCenterRight",
    "GSBottomLeft",
    "GSBottomCenter",
    "GSBottomRight",
    "WEIGHT_CODES",
    "WIDTH_CODES",
]

# CONSTANTS
GSMOVE_ = 17
GSLINE_ = 1
GSCURVE_ = 35
GSOFFCURVE_ = 65
GSSHARP = 0
GSSMOOTH = 100

GSMOVE = "move"
GSLINE = "line"
GSCURVE = "curve"
GSQCURVE = "qcurve"
GSOFFCURVE = "offcurve"

MOVE = "move"
LINE = "line"
CURVE = "curve"
OFFCURVE = "offcurve"
QCURVE = "qcurve"

TAG = -2
TOPGHOST = -1
STEM = 0
BOTTOMGHOST = 1
TTANCHOR = 2
TTSTEM = 3
TTALIGN = 4
TTINTERPOLATE = 5
TTDIAGONAL = 6
TTDELTA = 7
CORNER = 16
CAP = 17

TTDONTROUND = 4
TTROUND = 0
TTROUNDUP = 1
TTROUNDDOWN = 2
TRIPLE = 128

# Annotations:
TEXT = 1
ARROW = 2
CIRCLE = 3
PLUS = 4
MINUS = 5

# Directions:
LTR = 0  # Left To Right (e.g. Latin)
RTL = 1  # Right To Left (e.g. Arabic, Hebrew)
LTRTTB = 3  # Left To Right, Top To Bottom
RTLTTB = 2  # Right To Left, Top To Bottom

# Reverse lookup for __repr__
hintConstants = {
    -2: "Tag",
    -1: "TopGhost",
    0: "Stem",
    1: "BottomGhost",
    2: "TTAnchor",
    3: "TTStem",
    4: "TTAlign",
    5: "TTInterpolate",
    6: "TTDiagonal",
    7: "TTDelta",
    16: "Corner",
    17: "Cap",
}

GSTopLeft = 6
GSTopCenter = 7
GSTopRight = 8
GSCenterLeft = 3
GSCenterCenter = 4
GSCenterRight = 5
GSBottomLeft = 0
GSBottomCenter = 1
GSBottomRight = 2

# Writing direction
LTR = 0
RTL = 1
LTRTTB = 3
RTLTTB = 2


WEIGHT_CODES = {
    "Thin": 100,
    "ExtraLight": 200,
    "UltraLight": 200,
    "Light": 300,
    None: 400,  # default value normally omitted in source
    "Normal": 400,
    "Regular": 400,
    "Medium": 500,
    "DemiBold": 600,
    "SemiBold": 600,
    "Bold": 700,
    "UltraBold": 800,
    "ExtraBold": 800,
    "Black": 900,
    "Heavy": 900,
}

WIDTH_CODES = {
    "Ultra Condensed": 1,
    "Extra Condensed": 2,
    "Condensed": 3,
    "SemiCondensed": 4,
    None: 5,  # default value normally omitted in source
    "Medium (normal)": 5,
    "Semi Expanded": 6,
    "Expanded": 7,
    "Extra Expanded": 8,
    "Ultra Expanded": 9,
}


class OnlyInGlyphsAppError(NotImplementedError):
    def __init__(self):
        NotImplementedError.__init__(
            self,
            "This property/method is only available in the real UI-based "
            "version of Glyphs.app.",
        )


def parse_hint_target(line=None):
    if line is None:
        return None
    if line[0] == "{":
        return Point(line)
    else:
        return line


def isString(string):
    return isinstance(string, str)


def transformStructToScaleAndRotation(transform):
    Det = transform[0] * transform[3] - transform[1] * transform[2]
    _sX = math.sqrt(math.pow(transform[0], 2) + math.pow(transform[1], 2))
    _sY = math.sqrt(math.pow(transform[2], 2) + math.pow(transform[3], 2))
    if Det < 0:
        _sY = -_sY
    _R = math.atan2(transform[1] * _sY, transform[0] * _sX) * 180 / math.pi

    if Det < 0 and (math.fabs(_R) > 135 or _R < -90):
        _sX = -_sX
        _sY = -_sY
        if _R < 0:
            _R += 180
        else:
            _R -= 180

    quadrant = 0
    if _R < -90:
        quadrant = 180
        _R += quadrant
    if _R > 90:
        quadrant = -180
        _R += quadrant
    _R = _R * _sX / _sY
    _R -= quadrant
    if _R < -179:
        _R += 360

    return _sX, _sY, _R


class GSApplication:
    __slots__ = "font", "fonts"

    def __init__(self):
        self.font = None
        self.fonts = []

    def open(self, path):
        newFont = GSFont(path)
        self.fonts.append(newFont)
        self.font = newFont
        return newFont

    def __repr__(self):
        return "<glyphsLib>"


Glyphs = GSApplication()


class GSBase:
    """Represent the base class for all GS classes.

    Attributes:
        _classesForName (dict): Pre-PEP 484 way of annotating instance variables with
            their types. Used by the parser during deserialization to insert
            instance variables into GS classes. Used during serialization to determine
            if some values should be serialized.
        _defaultsForName (dict): Used to determine which values to serialize and which
            to imply by their absence.
        _wrapperKeysTranslate (dict): Used to map field names to GS* instance variables
            during (de)serialization.
    """

    _classesForName = {}
    _defaultsForName = {}
    _wrapperKeysTranslate = {}

    def __repr__(self):
        content = ""
        if hasattr(self, "_dict"):
            content = str(self._dict)
        return f"<{self.__class__.__name__} {content}>"

    def classForName(self, name):
        return self._classesForName.get(name, str)

    def default_attr_value(self, attr_name):
        """Return the default value of the given attribute, if any."""

    # Note:
    # The dictionary API exposed by GS* classes is "private" in the sense that:
    #  * it should only be used by the parser, so it should only
    #    work for key names that are found in the files
    #  * and only for filling data in the objects, which is why it only
    #    implements `__setitem__`
    #
    # Users of the library should only rely on the object-oriented API that is
    # documented at https://docu.glyphsapp.com/
    def __setitem__(self, key, value):
        if isinstance(value, bytes) and key in self._classesForName:
            new_type = self._classesForName[key]
            if new_type is str:
                value = value.decode("utf-8")
            else:
                try:
                    value = new_type().read(value)
                except Exception:
                    # FIXME: too broad, should only catch specific exceptions
                    value = new_type(value)
        key = self._wrapperKeysTranslate.get(key, key)
        setattr(self, key, value)

    def shouldWriteValueForKey(self, key):
        getKey = self._wrapperKeysTranslate.get(key, key)
        value = getattr(self, getKey)
        klass = self._classesForName[key]
        default = self._defaultsForName.get(key, None)
        if isinstance(value, (list, glyphsLib.classes.Proxy, str)) and len(value) == 0:
            return False
        if default is not None:
            return default != value
        if klass in (int, float, bool) and value == 0:
            return False
        if isinstance(value, ValueType) and value.value is None:
            return False
        return True


class Proxy:
    __slots__ = "_owner"

    def __init__(self, owner):
        self._owner = owner

    def __repr__(self):
        """Return list-lookalike of representation string of objects"""
        strings = []
        for currItem in self:
            strings.append("%s" % currItem)
        return "(%s)" % (", ".join(strings))

    def __len__(self):
        values = self.values()
        if values is not None:
            return len(values)
        return 0

    def pop(self, i):
        if type(i) == int:
            node = self[i]
            del self[i]
            return node
        else:
            raise KeyError

    def __iter__(self):
        values = self.values()
        if values is not None:
            yield from values

    def index(self, value):
        return self.values().index(value)

    def __copy__(self):
        return list(self)

    def __deepcopy__(self, memo):
        return [x.copy() for x in self.values()]

    def setter(self, values):
        method = self.setterMethod()
        if type(values) == list:
            method(values)
        elif (
            type(values) == tuple
            or values.__class__.__name__ == "__NSArrayM"
            or type(values) == type(self)
        ):
            method(list(values))
        elif values is None:
            method(list())
        else:
            raise TypeError


class LayersIterator:
    __slots__ = "curInd", "_owner", "_orderedLayers"

    def __init__(self, owner):
        self.curInd = 0
        self._owner = owner
        self._orderedLayers = None

    def __iter__(self):
        return self

    def next(self):
        return self.__next__()

    def __next__(self):
        if self._owner.parent:
            if self.curInd >= len(self._owner.layers):
                raise StopIteration
            item = self.orderedLayers[self.curInd]
        else:
            if self.curInd >= len(self._owner._layers):
                raise StopIteration
            item = self._owner._layers[self.curInd]
        self.curInd += 1
        return item

    @property
    def orderedLayers(self):
        if not self._orderedLayers:
            glyphLayerIds = [
                l.associatedMasterId
                for l in self._owner._layers.values()
                if l.associatedMasterId == l.layerId
            ]
            masterIds = [m.id for m in self._owner.parent.masters]
            intersectedLayerIds = set(glyphLayerIds) & set(masterIds)
            orderedLayers = [
                self._owner._layers[m.id]
                for m in self._owner.parent.masters
                if m.id in intersectedLayerIds
            ]
            orderedLayers += [
                self._owner._layers[l.layerId]
                for l in self._owner._layers.values()
                if l.layerId not in intersectedLayerIds
            ]
            self._orderedLayers = orderedLayers
        return self._orderedLayers


class FontFontMasterProxy(Proxy):
    """The list of masters. You can access it with the index or the master ID.
    Usage:
        Font.masters[index]
        Font.masters[id]
        for master in Font.masters:
        ...
    """

    def __getitem__(self, Key):
        if type(Key) == slice:
            return self.values().__getitem__(Key)
        if type(Key) is int:
            if Key < 0:
                Key = self.__len__() + Key
            return self.values()[Key]
        elif isString(Key):
            # UUIDs are case-sensitive in Glyphs.app.
            for master in self.values():
                if master.id == Key:
                    return master
        else:
            raise KeyError

    def __setitem__(self, Key, FontMaster):
        FontMaster.font = self._owner
        if type(Key) is int:
            OldFontMaster = self.__getitem__(Key)
            if Key < 0:
                Key = self.__len__() + Key
            FontMaster.id = OldFontMaster.id
            self._owner._masters[Key] = FontMaster
        elif isString(Key):
            OldFontMaster = self.__getitem__(Key)
            FontMaster.id = OldFontMaster.id
            Index = self._owner._masters.index(OldFontMaster)
            self._owner._masters[Index] = FontMaster
        else:
            raise KeyError

    def __delitem__(self, Key):
        if type(Key) is int:
            if Key < 0:
                Key = self.__len__() + Key
            return self.remove(self._owner._masters[Key])
        else:
            OldFontMaster = self.__getitem__(Key)
            return self.remove(OldFontMaster)

    def values(self):
        return self._owner._masters

    def append(self, FontMaster):
        FontMaster.font = self._owner
        # If the master to be appended has no ID yet or it's a duplicate,
        # make up a new one.
        if not FontMaster.id or self[FontMaster.id]:
            FontMaster.id = str(uuid.uuid4()).upper()
        self._owner._masters.append(FontMaster)

        # Cycle through all glyphs and append layer
        for glyph in self._owner.glyphs:
            if not glyph.layers[FontMaster.id]:
                newLayer = GSLayer()
                glyph._setupLayer(newLayer, FontMaster.id)
                glyph.layers.append(newLayer)

    def remove(self, FontMaster):

        # First remove all layers in all glyphs that reference this master
        for glyph in self._owner.glyphs:
            for layer in glyph.layers:
                if (
                    layer.associatedMasterId == FontMaster.id
                    or layer.layerId == FontMaster.id
                ):
                    glyph.layers.remove(layer)

        self._owner._masters.remove(FontMaster)

    def insert(self, Index, FontMaster):
        FontMaster.font = self._owner
        self._owner._masters.insert(Index, FontMaster)

    def extend(self, FontMasters):
        for FontMaster in FontMasters:
            self.append(FontMaster)

    def setter(self, values):
        if isinstance(values, Proxy):
            values = list(values)
        self._owner._masters = values
        for m in self._owner._masters:
            m.font = self._owner


class FontGlyphsProxy(Proxy):
    """The list of glyphs. You can access it with the index or the glyph name.
    Usage:
        Font.glyphs[index]
        Font.glyphs[name]
        for glyph in Font.glyphs:
        ...
    """

    def __getitem__(self, key):
        if type(key) == slice:
            return self.values().__getitem__(key)

        # by index
        if isinstance(key, int):
            return self._owner._glyphs[key]

        if isinstance(key, str):
            return self._get_glyph_by_string(key)

        return None

    def __setitem__(self, key, glyph):
        if type(key) is int:
            self._owner._setupGlyph(glyph)
            self._owner._glyphs[key] = glyph
        else:
            raise KeyError  # TODO: add other access methods

    def __delitem__(self, key):
        if isinstance(key, int):
            del self._owner._glyphs[key]
        elif isString(key):
            glyph = self._get_glyph_by_string(key)
            if not glyph:
                raise KeyError("No glyph '%s' in the font" % key)
            self._owner._glyphs.remove(glyph)
        else:
            raise KeyError

    def __contains__(self, item):
        if isString(item):
            return self._get_glyph_by_string(item) is not None
        return item in self._owner._glyphs

    def _get_glyph_by_string(self, key):
        # FIXME: (jany) looks inefficient
        if isinstance(key, str):
            # by glyph name
            for glyph in self._owner._glyphs:
                if glyph.name == key:
                    return glyph
            # by string representation as u'ä'
            if len(key) == 1:
                for glyph in self._owner._glyphs:
                    if glyph.unicode == "%04X" % (ord(key)):
                        return glyph
            # by unicode
            else:
                for glyph in self._owner._glyphs:
                    if glyph.unicode == key.upper():
                        return glyph
        return None

    def values(self):
        return self._owner._glyphs

    def items(self):
        items = []
        for value in self._owner._glyphs:
            key = value.name
            items.append((key, value))
        return items

    def append(self, glyph):
        self._owner._setupGlyph(glyph)
        self._owner._glyphs.append(glyph)

    def extend(self, objects):
        for glyph in objects:
            self._owner._setupGlyph(glyph)
        self._owner._glyphs.extend(list(objects))

    def __len__(self):
        return len(self._owner._glyphs)

    def setter(self, values):
        if isinstance(values, Proxy):
            values = list(values)
        self._owner._glyphs = values
        for g in self._owner._glyphs:
            g.parent = self._owner
            for layer in g.layers.values():
                if (
                    not hasattr(layer, "associatedMasterId")
                    or layer.associatedMasterId is None
                    or len(layer.associatedMasterId) == 0
                ):
                    g._setupLayer(layer, layer.layerId)


class FontClassesProxy(Proxy):
    def __getitem__(self, key):
        if isinstance(key, (slice, int)):
            return self.values().__getitem__(key)
        if isinstance(key, str):
            for index, klass in enumerate(self.values()):
                if klass.name == key:
                    return self.values()[index]
        raise KeyError

    def __setitem__(self, key, value):
        if isinstance(key, int):
            self.values()[key] = value
            value._parent = self._owner
        elif isinstance(key, str):
            for index, klass in enumerate(self.values()):
                if klass.name == key:
                    self.values()[index] = value
                    value._parent = self._owner
        else:
            raise KeyError

    def __delitem__(self, key):
        if isinstance(key, int):
            del self.values()[key]
        elif isinstance(key, str):
            for index, klass in enumerate(self.values()):
                if klass.name == key:
                    del self.values()[index]

    # FIXME: (jany) def __contains__

    def append(self, item):
        self.values().append(item)
        item._parent = self._owner

    def insert(self, key, item):
        self.values().insert(key, item)
        item._parent = self._owner

    def extend(self, items):
        self.values().extend(items)
        for value in items:
            value._parent = self._owner

    def remove(self, item):
        self.values().remove(item)

    def values(self):
        return self._owner._classes

    def setter(self, values):
        if isinstance(values, Proxy):
            values = list(values)
        self._owner._classes = values
        for value in values:
            value._parent = self._owner


class GlyphLayerProxy(Proxy):
    def __getitem__(self, key):
        self._ensureMasterLayers()
        if isinstance(key, slice):
            return self.values().__getitem__(key)
        elif isinstance(key, int):
            if self._owner.parent:
                return list(self)[key]
            return list(self.values())[key]
        elif isString(key):
            if key in self._owner._layers:
                return self._owner._layers[key]

    def __setitem__(self, key, layer):
        if isinstance(key, int) and self._owner.parent:
            OldLayer = self._owner._layers.values()[key]
            if key < 0:
                key = self.__len__() + key
            layer.layerId = OldLayer.layerId
            layer.associatedMasterId = OldLayer.associatedMasterId
            self._owner._setupLayer(layer, OldLayer.layerId)
            self._owner._layers[key] = layer
        elif isinstance(key, str) and self._owner.parent:
            # FIXME: (jany) more work to do?
            layer.parent = self._owner
            self._owner._layers[key] = layer
        else:
            raise KeyError

    def __delitem__(self, key):
        if isinstance(key, int) and self._owner.parent:
            if key < 0:
                key = self.__len__() + key
            Layer = self.__getitem__(key)
            key = Layer.layerId
        del self._owner._layers[key]

    def __iter__(self):
        return LayersIterator(self._owner)

    def __len__(self):
        return len(self.values())

    def keys(self):
        self._ensureMasterLayers()
        return self._owner._layers.keys()

    def values(self):
        self._ensureMasterLayers()
        return self._owner._layers.values()

    def append(self, layer):
        assert layer is not None
        self._ensureMasterLayers()
        if not layer.associatedMasterId:
            if self._owner.parent:
                layer.associatedMasterId = self._owner.parent.masters[0].id
        if not layer.layerId:
            layer.layerId = str(uuid.uuid4()).upper()
        self._owner._setupLayer(layer, layer.layerId)
        self._owner._layers[layer.layerId] = layer

    def extend(self, layers):
        for layer in layers:
            self.append(layer)

    def remove(self, layer):
        return self._owner.removeLayerForKey_(layer.layerId)

    def insert(self, index, layer):
        self._ensureMasterLayers()
        self.append(layer)

    def setter(self, values):
        newLayers = OrderedDict()
        if type(values) == list or type(values) == tuple or type(values) == type(self):
            for layer in values:
                newLayers[layer.layerId] = layer
        elif type(values) == dict:  # or isinstance(values, NSDictionary)
            for layer in values.values():
                newLayers[layer.layerId] = layer
        else:
            raise TypeError
        for (key, layer) in newLayers.items():
            self._owner._setupLayer(layer, key)
        self._owner._layers = newLayers

    def _ensureMasterLayers(self):
        # Ensure existence of master-linked layers (even for iteration, len() etc.)
        # if accidentally deleted
        if not self._owner.parent:
            return
        for master in self._owner.parent.masters:
            # if (master.id not in self._owner._layers or
            #         self._owner._layers[master.id] is None):
            if self._owner.parent.masters[master.id] is None:
                newLayer = GSLayer()
                newLayer.associatedMasterId = master.id
                newLayer.layerId = master.id
                self._owner._setupLayer(newLayer, master.id)
                self.__setitem__(master.id, newLayer)

    def plistArray(self):
        return list(self._owner._layers.values())


class LayerAnchorsProxy(Proxy):
    def __getitem__(self, key):
        if isinstance(key, (slice, int)):
            return self.values().__getitem__(key)
        elif isinstance(key, str):
            for i, a in enumerate(self._owner._anchors):
                if a.name == key:
                    return self._owner._anchors[i]
        else:
            raise KeyError

    def __setitem__(self, key, anchor):
        if isinstance(key, str):
            anchor.name = key
            for i, a in enumerate(self._owner._anchors):
                if a.name == key:
                    self._owner._anchors[i] = anchor
                    return
            anchor._parent = self._owner
            self._owner._anchors.append(anchor)
        else:
            raise TypeError

    def __delitem__(self, key):
        if isinstance(key, int):
            del self._owner._anchors[key]
        elif isinstance(key, str):
            for i, a in enumerate(self._owner._anchors):
                if a.name == key:
                    self._owner._anchors[i]._parent = None
                    del self._owner._anchors[i]
                    return

    def values(self):
        return self._owner._anchors

    def append(self, anchor):
        for i, a in enumerate(self._owner._anchors):
            if a.name == anchor.name:
                anchor._parent = self._owner
                self._owner._anchors[i] = anchor
                return
        if anchor.name:
            self._owner._anchors.append(anchor)
        else:
            raise ValueError("Anchor must have name")

    def extend(self, anchors):
        for anchor in anchors:
            anchor._parent = self._owner
        self._owner._anchors.extend(anchors)

    def remove(self, anchor):
        if isinstance(anchor, str):
            anchor = self.values()[anchor]
        return self._owner._anchors.remove(anchor)

    def insert(self, index, anchor):
        anchor._parent = self._owner
        self._owner._anchors.insert(index, anchor)

    def __len__(self):
        return len(self._owner._anchors)

    def setter(self, anchors):
        if isinstance(anchors, Proxy):
            anchors = list(anchors)
        self._owner._anchors = anchors
        for anchor in anchors:
            anchor._parent = self._owner


class IndexedObjectsProxy(Proxy):
    def __getitem__(self, key):
        if isinstance(key, (slice, int)):
            return self.values().__getitem__(key)
        else:
            raise KeyError

    def __setitem__(self, key, value):
        if isinstance(key, int):
            self.values()[key] = value
            value._parent = self._owner
        else:
            raise KeyError

    def __delitem__(self, key):
        if isinstance(key, int):
            del self.values()[key]
        else:
            raise KeyError

    def values(self):
        return getattr(self._owner, self._objects_name)

    def append(self, value):
        self.values().append(value)
        value._parent = self._owner

    def extend(self, values):
        self.values().extend(values)
        for value in values:
            value._parent = self._owner

    def remove(self, value):
        self.values().remove(value)

    def insert(self, index, value):
        self.values().insert(index, value)
        value._parent = self._owner

    def __len__(self):
        return len(self.values())

    def setter(self, values):
        setattr(self._owner, self._objects_name, list(values))
        for value in self.values():
            value._parent = self._owner


class LayerPathsProxy(IndexedObjectsProxy):
    _objects_name = "_paths"

    def __init__(self, owner):
        super().__init__(owner)


class LayerHintsProxy(IndexedObjectsProxy):
    _objects_name = "_hints"

    def __init__(self, owner):
        super().__init__(owner)


class LayerComponentsProxy(IndexedObjectsProxy):
    _objects_name = "_components"

    def __init__(self, owner):
        super().__init__(owner)


class LayerAnnotationProxy(IndexedObjectsProxy):
    _objects_name = "_annotations"

    def __init__(self, owner):
        super().__init__(owner)


class LayerGuideLinesProxy(IndexedObjectsProxy):
    _objects_name = "_guides"

    def __init__(self, owner):
        super().__init__(owner)


class PathNodesProxy(IndexedObjectsProxy):
    _objects_name = "_nodes"

    def __init__(self, owner):
        super().__init__(owner)


class CustomParametersProxy(Proxy):
    def __getitem__(self, key):
        if isinstance(key, slice):
            return self.values().__getitem__(key)
        if isinstance(key, int):
            return self._owner._customParameters[key]
        else:
            customParameter = self._get_parameter_by_key(key)
            if customParameter is not None:
                return customParameter.value
        return None

    def _get_parameter_by_key(self, key):
        for customParameter in self._owner._customParameters:
            if customParameter.name == key:
                return customParameter

    def __setitem__(self, key, value):
        customParameter = self._get_parameter_by_key(key)
        if customParameter is not None:
            customParameter.value = value
        else:
            parameter = GSCustomParameter(name=key, value=value)
            self._owner._customParameters.append(parameter)

    def __delitem__(self, key):
        if isinstance(key, int):
            del self._owner._customParameters[key]
        elif isinstance(key, str):
            for parameter in self._owner._customParameters:
                if parameter.name == key:
                    self._owner._customParameters.remove(parameter)
        else:
            raise KeyError

    def __contains__(self, item):
        if isString(item):
            return self.__getitem__(item) is not None
        return item in self._owner._customParameters

    def __iter__(self):
        for index in range(len(self._owner._customParameters)):
            yield self._owner._customParameters[index]

    def append(self, parameter):
        parameter.parent = self._owner
        self._owner._customParameters.append(parameter)

    def extend(self, parameters):
        for parameter in parameters:
            parameter.parent = self._owner
        self._owner._customParameters.extend(parameters)

    def remove(self, parameter):
        if isString(parameter):
            parameter = self.__getitem__(parameter)
        self._owner._customParameters.remove(parameter)

    def insert(self, index, parameter):
        parameter.parent = self._owner
        self._owner._customParameters.insert(index, parameter)

    def __len__(self):
        return len(self._owner._customParameters)

    def values(self):
        return self._owner._customParameters

    def __setter__(self, parameters):
        for parameter in parameters:
            parameter.parent = self._owner
        self._owner._customParameters = parameters

    def setterMethod(self):
        return self.__setter__


class UserDataProxy(Proxy):
    def __getitem__(self, key):
        if self._owner._userData is None:
            return None
        # This is not the normal `dict` behaviour, because this does not raise
        # `KeyError` and instead just returns `None`. It matches Glyphs.app.
        return self._owner._userData.get(key)

    def __setitem__(self, key, value):
        if self._owner._userData is not None:
            self._owner._userData[key] = value
        else:
            self._owner._userData = {key: value}

    def __delitem__(self, key):
        if self._owner._userData is not None and key in self._owner._userData:
            del self._owner._userData[key]

    def __contains__(self, item):
        if self._owner._userData is None:
            return False
        return item in self._owner._userData

    def __iter__(self):
        if self._owner._userData is None:
            return
        # This is not the normal `dict` behaviour, because this yields values
        # instead of keys. It matches Glyphs.app though. Urg.
        yield from self._owner._userData.values()

    def values(self):
        if self._owner._userData is None:
            return []
        return self._owner._userData.values()

    def keys(self):
        if self._owner._userData is None:
            return []
        return self._owner._userData.keys()

    def items(self):
        if self._owner._userData is None:
            return []
        return self._owner._userData.items()

    def get(self, key):
        if self._owner._userData is None:
            return None
        return self._owner._userData.get(key)

    def setter(self, values):
        self._owner._userData = values


class GSCustomParameter(GSBase):
    __slots__ = ("name", "_value")

    _classesForName = {"name": str, "value": None}

    _CUSTOM_INT_PARAMS = frozenset(
        (
            "ascender",
            "blueShift",
            "capHeight",
            "descender",
            "hheaAscender",
            "hheaDescender",
            "hheaLineGap",
            "subscriptXSize",
            "subscriptYSize",
            "subscriptXOffset",
            "subscriptYOffset",
            "superscriptXSize",
            "superscriptYSize",
            "superscriptXOffset",
            "superscriptYOffset",
            "macintoshFONDFamilyID",
            "openTypeHeadLowestRecPPEM",
            "openTypeHheaAscender",
            "openTypeHheaCaretOffset",
            "openTypeHheaCaretSlopeRise",
            "openTypeHheaCaretSlopeRun",
            "openTypeHheaDescender",
            "openTypeHheaLineGap",
            "openTypeOS2StrikeoutPosition",
            "openTypeOS2StrikeoutSize",
            "openTypeOS2SubscriptXOffset",
            "openTypeOS2SubscriptXSize",
            "openTypeOS2SubscriptYOffset",
            "openTypeOS2SubscriptYSize",
            "openTypeOS2SuperscriptXOffset",
            "openTypeOS2SuperscriptXSize",
            "openTypeOS2SuperscriptYOffset",
            "openTypeOS2SuperscriptYSize",
            "openTypeOS2TypoAscender",
            "openTypeOS2TypoDescender",
            "openTypeOS2TypoLineGap",
            "openTypeOS2WeightClass",
            "openTypeOS2WidthClass",
            "openTypeOS2WinAscent",
            "openTypeOS2WinDescent",
            "openTypeVheaCaretOffset",
            "openTypeVheaCaretSlopeRise",
            "openTypeVheaCaretSlopeRun",
            "openTypeVheaVertTypoAscender",
            "openTypeVheaVertTypoDescender",
            "openTypeVheaVertTypoLineGap",
            "postscriptBlueFuzz",
            "postscriptBlueShift",
            "postscriptDefaultWidthX",
            "postscriptUnderlinePosition",
            "postscriptUnderlineThickness",
            "postscriptUniqueID",
            "postscriptWindowsCharacterSet",
            "shoulderHeight",
            "smallCapHeight",
            "typoAscender",
            "typoDescender",
            "typoLineGap",
            "underlinePosition",
            "underlineThickness",
            "strikeoutSize",
            "strikeoutPosition",
            "unitsPerEm",
            "vheaVertAscender",
            "vheaVertDescender",
            "vheaVertLineGap",
            "weightClass",
            "widthClass",
            "winAscent",
            "winDescent",
            "year",
            "Grid Spacing",
        )
    )
    _CUSTOM_FLOAT_PARAMS = frozenset(("postscriptSlantAngle", "postscriptBlueScale"))

    _CUSTOM_BOOL_PARAMS = frozenset(
        (
            "isFixedPitch",
            "postscriptForceBold",
            "postscriptIsFixedPitch",
            "Don\u2019t use Production Names",
            "DisableAllAutomaticBehaviour",
            "Use Typo Metrics",
            "Has WWS Names",
            "Use Extension Kerning",
            "Disable Subroutines",
            "Don't use Production Names",
            "Disable Last Change",
        )
    )
    _CUSTOM_INTLIST_PARAMS = frozenset(
        (
            "fsType",
            "openTypeOS2CodePageRanges",
            "openTypeOS2FamilyClass",
            "openTypeOS2Panose",
            "openTypeOS2Type",
            "openTypeOS2UnicodeRanges",
            "panose",
            "unicodeRanges",
            "codePageRanges",
            "openTypeHeadFlags",
        )
    )
    _CUSTOM_DICT_PARAMS = frozenset("GASP Table")

    def __init__(self, name="New Value", value="New Parameter"):
        self.name = name
        self.value = value

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.name}: {self._value}>"

    def plistValue(self):
        string = StringIO()
        writer = Writer(string)
        writer.writeDict({"name": self.name, "value": self.value})
        return string.getvalue()

    def getValue(self):
        return self._value

    def setValue(self, value):
        """Cast some known data in custom parameters."""
        if self.name in self._CUSTOM_INT_PARAMS:
            value = int(value)
        elif self.name in self._CUSTOM_FLOAT_PARAMS:
            value = float(value)
        elif self.name in self._CUSTOM_BOOL_PARAMS:
            value = bool(value)
        elif self.name in self._CUSTOM_INTLIST_PARAMS:
            value = readIntlist(value)
        elif self.name in self._CUSTOM_DICT_PARAMS:
            parser = Parser()
            value = parser.parse(value)
        elif self.name == "note":
            value = str(value)
        self._value = value

    value = property(getValue, setValue)


class GSAlignmentZone(GSBase):
    __slots__ = ("position", "size")

    def __init__(self, pos=0, size=20):
        self.position = pos
        self.size = size

    def read(self, src):
        if src is not None:
            p = Point(src)
            self.position = parse_float_or_int(p.value[0])
            self.size = parse_float_or_int(p.value[1])
        return self

    def __repr__(self):
        return "<{} pos:{:g} size:{:g}>".format(
            self.__class__.__name__, self.position, self.size
        )

    def __lt__(self, other):
        return (self.position, self.size) < (other.position, other.size)

    def plistValue(self):
        return '"{{{}, {}}}"'.format(
            floatToString5(self.position), floatToString5(self.size)
        )


class GSGuideLine(GSBase):
    __slots__ = (
        "alignment",
        "angle",
        "filter",
        "locked",
        "name",
        "position",
        "showMeasurement",
    )

    _classesForName = {
        "alignment": str,
        "angle": parse_float_or_int,
        "locked": bool,
        "position": Point,
        "showMeasurement": bool,
        "filter": str,
        "name": str,
    }
    _parent = None
    _defaultsForName = {"position": Point(0, 0), "angle": 0}

    def __init__(self):
        self.alignment = ""
        self.angle = self._defaultsForName["angle"]
        self.filter = ""
        self.locked = False
        self.name = ""
        self.position = copy.deepcopy(self._defaultsForName["position"])
        self.showMeasurement = False

    def __repr__(self):
        return "<{} x={:.1f} y={:.1f} angle={:.1f}>".format(
            self.__class__.__name__, self.position.x, self.position.y, self.angle
        )

    @property
    def parent(self):
        return self._parent


MASTER_NAME_WEIGHTS = ("Light", "SemiLight", "SemiBold", "Bold")
MASTER_NAME_WIDTHS = ("Condensed", "SemiCondensed", "Extended", "SemiExtended")


class GSFontMaster(GSBase):
    __slots__ = (
        "_customParameters",
        "_name",
        "_userData",
        "alignmentZones",
        "ascender",
        "capHeight",
        "customName",
        "customValue",
        "customValue1",
        "customValue2",
        "customValue3",
        "descender",
        "font",
        "guides",
        "horizontalStems",
        "iconName",
        "id",
        "italicAngle",
        "verticalStems",
        "visible",
        "weight",
        "weightValue",
        "width",
        "widthValue",
        "xHeight",
    )

    _classesForName = {
        "alignmentZones": GSAlignmentZone,
        "ascender": parse_float_or_int,
        "capHeight": parse_float_or_int,
        "custom": str,
        "customValue": parse_float_or_int,
        "customValue1": parse_float_or_int,
        "customValue2": parse_float_or_int,
        "customValue3": parse_float_or_int,
        "customParameters": GSCustomParameter,
        "descender": parse_float_or_int,
        "guideLines": GSGuideLine,
        "horizontalStems": int,
        "iconName": str,
        "id": str,
        "italicAngle": parse_float_or_int,
        "name": str,
        "userData": dict,
        "verticalStems": int,
        "visible": bool,
        "weight": str,
        "weightValue": parse_float_or_int,
        "width": str,
        "widthValue": parse_float_or_int,
        "xHeight": parse_float_or_int,
    }
    _defaultsForName = {
        # FIXME: (jany) In the latest Glyphs (1113), masters don't have a width
        # and weight anymore as attributes, even though those properties are
        # still written to the saved files.
        "weight": "Regular",
        "width": "Regular",
        "weightValue": 100,
        "widthValue": 100,
        "customValue": 0,
        "customValue1": 0,
        "customValue2": 0,
        "customValue3": 0,
        "xHeight": 500,
        "capHeight": 700,
        "ascender": 800,
        "descender": -200,
        "italicAngle": 0,
    }
    _wrapperKeysTranslate = {
        "guideLines": "guides",
        "custom": "customName",
        "name": "_name",
    }
    _keyOrder = (
        "alignmentZones",
        "ascender",
        "capHeight",
        "custom",
        "customValue",
        "customValue1",
        "customValue2",
        "customValue3",
        "customParameters",
        "descender",
        "guideLines",
        "horizontalStems",
        "iconName",
        "id",
        "italicAngle",
        "name",
        "userData",
        "verticalStems",
        "visible",
        "weight",
        "weightValue",
        "width",
        "widthValue",
        "xHeight",
    )

    def __init__(self):
        self._customParameters = []
        self._name = None
        self._userData = None
        self.alignmentZones = []
        self.ascender = self._defaultsForName["ascender"]
        self.capHeight = self._defaultsForName["capHeight"]
        self.customName = ""
        self.customValue = self._defaultsForName["customValue"]
        self.customValue1 = self._defaultsForName["customValue1"]
        self.customValue2 = self._defaultsForName["customValue2"]
        self.customValue3 = self._defaultsForName["customValue3"]
        self.descender = self._defaultsForName["descender"]
        self.font = None
        self.guides = []
        self.horizontalStems = 0
        self.iconName = ""
        self.id = str(uuid.uuid4()).upper()
        self.italicAngle = self._defaultsForName["italicAngle"]
        self.verticalStems = 0
        self.visible = False
        self.weight = self._defaultsForName["weight"]
        self.weightValue = self._defaultsForName["weightValue"]
        self.width = self._defaultsForName["width"]
        self.widthValue = self._defaultsForName["widthValue"]
        self.xHeight = self._defaultsForName["xHeight"]

    def __repr__(self):
        return '<GSFontMaster "{}" width {} weight {}>'.format(
            self.name, self.widthValue, self.weightValue
        )

    def shouldWriteValueForKey(self, key):
        if key in ("weight", "width"):
            return getattr(self, key) != "Regular"
        if key in ("xHeight", "capHeight", "ascender", "descender"):
            # Always write those values
            return True
        if key == "_name":
            # Only write out the name if we can't make it by joining the parts
            return self._name != self.name
        return super().shouldWriteValueForKey(key)

    @property
    def name(self):
        name = self.customParameters["Master Name"]
        if name:
            return name
        if self._name:
            return self._name
        return self._joinName()

    @name.setter
    def name(self, name):
        """This function will take the given name and split it into components
        weight, width, customName, and possibly the full name.
        This is what Glyphs 1113 seems to be doing, approximately.
        """
        weight, width, custom_name = self._splitName(name)
        self.set_all_name_components(name, weight, width, custom_name)

    def set_all_name_components(self, name, weight, width, custom_name):
        """This function ensures that after being called, the master.name,
        master.weight, master.width, and master.customName match the given
        values.
        """
        self.weight = weight or "Regular"
        self.width = width or "Regular"
        self.customName = custom_name or ""
        # Only store the requested name if we can't build it from the parts
        if self._joinName() == name:
            self._name = None
            del self.customParameters["Master Name"]
        else:
            self._name = name
            self.customParameters["Master Name"] = name

    def _joinName(self):
        # Remove None and empty string
        names = list(filter(None, [self.width, self.weight, self.customName]))
        # Remove redundant occurences of 'Regular'
        while len(names) > 1 and "Regular" in names:
            names.remove("Regular")
        if self.italicAngle:
            if names == ["Regular"]:
                return "Italic"
            if "Italic" not in self.customName:
                names.append("Italic")
        return " ".join(names)

    def _splitName(self, value):
        if value is None:
            value = ""
        weight = "Regular"
        width = "Regular"
        custom = ""
        names = []
        previous_was_removed = False
        for name in value.split(" "):
            if name == "Regular":
                pass
            elif name in MASTER_NAME_WEIGHTS:
                if previous_was_removed:
                    # Get the double space in custom
                    names.append("")
                previous_was_removed = True
                weight = name
            elif name in MASTER_NAME_WIDTHS:
                if previous_was_removed:
                    # Get the double space in custom
                    names.append("")
                previous_was_removed = True
                width = name
            else:
                previous_was_removed = False
                names.append(name)
        custom = " ".join(names).strip()
        return weight, width, custom

    customParameters = property(
        lambda self: CustomParametersProxy(self),
        lambda self, value: CustomParametersProxy(self).setter(value),
    )

    userData = property(
        lambda self: UserDataProxy(self),
        lambda self, value: UserDataProxy(self).setter(value),
    )


class GSNode(GSBase):
    __slots__ = ("_userData", "position", "smooth", "type")

    _PLIST_VALUE_RE = re.compile(
        r'"([-.e\d]+) ([-.e\d]+) (LINE|CURVE|QCURVE|OFFCURVE|n/a)'
        r'(?: (SMOOTH))?(?: ({.*}))?"',
        re.DOTALL,
    )
    _parent = None

    def __init__(self, position=(0, 0), nodetype=LINE, smooth=False, name=None):
        self._userData = None
        self.position = Point(position[0], position[1])
        self.smooth = smooth
        self.type = nodetype
        # Optimization: Points can number in the 10000s, don't access the userDataProxy
        # through `name` unless needed.
        if name is not None:
            self.name = name

    def __repr__(self):
        content = self.type
        if self.smooth:
            content += " smooth"
        return "<{} {:g} {:g} {}>".format(
            self.__class__.__name__, self.position.x, self.position.y, content
        )

    userData = property(
        lambda self: UserDataProxy(self),
        lambda self, value: UserDataProxy(self).setter(value),
    )

    @property
    def parent(self):
        return self._parent

    def plistValue(self):
        content = self.type.upper()
        if self.smooth:
            content += " SMOOTH"
        if self._userData is not None and len(self._userData) > 0:
            string = StringIO()
            writer = Writer(string)
            writer.writeDict(self._userData)
            content += " "
            content += self._encode_dict_as_string(string.getvalue())
        return '"{} {} {}"'.format(
            floatToString5(self.position[0]), floatToString5(self.position[1]), content
        )

    def read(self, line):
        """Parse a Glyphs node string into a GSNode.

        The format of a Glyphs node string (`line`) is:

            "X Y (LINE|CURVE|QCURVE|OFFCURVE)"
            "X Y (LINE|CURVE|QCURVE|OFFCURVE) SMOOTH"
            "X Y (LINE|CURVE|QCURVE|OFFCURVE) SMOOTH {dictionary}"
            "X Y (LINE|CURVE|QCURVE|OFFCURVE) {dictionary}"

        X and Y can be integers or floats, positive or negative.

        WARNING: This method is HOT. It is called for every single node and can
        account for a significant portion of the file parsing time.
        """
        m = self._PLIST_VALUE_RE.match(line).groups()
        self.position = Point(parse_float_or_int(m[0]), parse_float_or_int(m[1]))
        self.type = m[2].lower()
        self.smooth = bool(m[3])

        if m[4] is not None and len(m[4]) > 0:
            value = self._decode_dict_as_string(m[4])
            parser = Parser()
            self._userData = parser.parse(value)

        return self

    @property
    def name(self):
        if "name" in self.userData:
            return self.userData["name"]
        return None

    @name.setter
    def name(self, value):
        if value is None:
            if "name" in self.userData:
                del self.userData["name"]
        else:
            self.userData["name"] = value

    @property
    def index(self):
        assert self.parent
        return self.parent.nodes.index(self)

    @property
    def nextNode(self):
        assert self.parent
        index = self.index
        if index == (len(self.parent.nodes) - 1):
            return self.parent.nodes[0]
        elif index < len(self.parent.nodes):
            return self.parent.nodes[index + 1]

    @property
    def prevNode(self):
        assert self.parent
        index = self.index
        if index == 0:
            return self.parent.nodes[-1]
        elif index < len(self.parent.nodes):
            return self.parent.nodes[index - 1]

    def makeNodeFirst(self):
        assert self.parent
        if self.type == "offcurve":
            raise ValueError("Off-curve points cannot become start points.")
        nodes = self.parent.nodes
        index = self.index
        newNodes = nodes[index : len(nodes)] + nodes[0:index]
        self.parent.nodes = newNodes

    def toggleConnection(self):
        self.smooth = not self.smooth

    # TODO
    @property
    def connection(self):
        raise NotImplementedError

    # TODO
    @property
    def selected(self):
        raise OnlyInGlyphsAppError

    @staticmethod
    def _encode_dict_as_string(value):
        """Takes the PLIST string of a dict, and returns the same string
        encoded such that it can be included in the string representation
        of a GSNode."""
        # Strip the first and last newlines
        if value.startswith("{\n"):
            value = "{" + value[2:]
        if value.endswith("\n}"):
            value = value[:-2] + "}"
        # escape double quotes and newlines
        return value.replace('"', '\\"').replace("\\n", "\\\\n").replace("\n", "\\n")

    _ESCAPED_CHAR_RE = re.compile(r'\\(\\*)(?:(n)|("))')

    @staticmethod
    def _unescape_char(m):
        backslashes = m.group(1) or ""
        if m.group(2):
            return "\n" if not backslashes else backslashes + "n"
        else:
            return backslashes + '"'

    @classmethod
    def _decode_dict_as_string(cls, value):
        """Reverse function of _encode_string_as_dict"""
        # strip one level of backslashes preceding quotes and newlines
        return cls._ESCAPED_CHAR_RE.sub(cls._unescape_char, value)

    def _indices(self):
        """Find the path_index and node_index that identify the given node."""
        path = self.parent
        layer = path.parent
        for path_index in range(len(layer.paths)):
            if path == layer.paths[path_index]:
                for node_index in range(len(path.nodes)):
                    if self == path.nodes[node_index]:
                        return Point(path_index, node_index)
        return None


class GSPath(GSBase):
    __slots__ = ("closed", "_nodes")

    _classesForName = {"nodes": GSNode, "closed": bool}
    _defaultsForName = {"closed": True}
    _parent = None

    def __init__(self):
        self.closed = self._defaultsForName["closed"]
        self.nodes = []

    @property
    def parent(self):
        return self._parent

    def shouldWriteValueForKey(self, key):
        if key == "closed":
            return True
        return super().shouldWriteValueForKey(key)

    nodes = property(
        lambda self: PathNodesProxy(self),
        lambda self, value: PathNodesProxy(self).setter(value),
    )

    @property
    def segments(self):
        self._segments = []
        self._segmentLength = 0

        nodeCount = 0
        segmentCount = 0
        while nodeCount < len(self.nodes):
            newSegment = segment()
            newSegment.parent = self
            newSegment.index = segmentCount

            if nodeCount == 0:
                newSegment.appendNode(self.nodes[-1])
            else:
                newSegment.appendNode(self.nodes[nodeCount - 1])

            if self.nodes[nodeCount].type == "offcurve":
                newSegment.appendNode(self.nodes[nodeCount])
                newSegment.appendNode(self.nodes[nodeCount + 1])
                newSegment.appendNode(self.nodes[nodeCount + 2])
                nodeCount += 3
            elif self.nodes[nodeCount].type == "line":
                newSegment.appendNode(self.nodes[nodeCount])
                nodeCount += 1

            self._segments.append(newSegment)
            self._segmentLength += 1
            segmentCount += 1

        return self._segments

    @segments.setter
    def segments(self, value):
        if type(value) in (list, tuple):
            self.setSegments(value)
        else:
            raise TypeError

    def setSegments(self, segments):
        self.nodes = []
        for segment in segments:
            if len(segment.nodes) == 2 or len(segment.nodes) == 4:
                self.nodes.extend(segment.nodes[1:])
            else:
                raise ValueError

    @property
    def bounds(self):
        left, bottom, right, top = None, None, None, None
        for segment in self.segments:
            newLeft, newBottom, newRight, newTop = segment.bbox()
            if left is None:
                left = newLeft
            else:
                left = min(left, newLeft)
            if bottom is None:
                bottom = newBottom
            else:
                bottom = min(bottom, newBottom)
            if right is None:
                right = newRight
            else:
                right = max(right, newRight)
            if top is None:
                top = newTop
            else:
                top = max(top, newTop)
        return Rect(Point(left, bottom), Point(right - left, top - bottom))

    @property
    def direction(self):
        direction = 0
        for i in range(len(self.nodes)):
            thisNode = self.nodes[i]
            nextNode = thisNode.nextNode
            direction += (nextNode.position.x - thisNode.position.x) * (
                nextNode.position.y + thisNode.position.y
            )
        if direction < 0:
            return -1
        else:
            return 1

    @property
    def selected(self):
        raise OnlyInGlyphsAppError

    @property
    def bezierPath(self):
        raise OnlyInGlyphsAppError

    def reverse(self):
        segments = list(reversed(self.segments))
        for s, segment in enumerate(segments):
            segment.nodes = list(reversed(segment.nodes))
            if s == len(segments) - 1:
                nextSegment = segments[0]
            else:
                nextSegment = segments[s + 1]
            if len(segment.nodes) == 2 and segment.nodes[-1].type == "curve":
                segment.nodes[-1].type = "line"
                nextSegment.nodes[0].type = "line"
            elif len(segment.nodes) == 4 and segment.nodes[-1].type == "line":
                segment.nodes[-1].type = "curve"
                nextSegment.nodes[0].type = "curve"
        self.setSegments(segments)

    # TODO
    def addNodesAtExtremes(self):
        raise NotImplementedError

    # TODO
    def applyTransform(self, transformationMatrix):
        raise NotImplementedError

        # Using both skew values (>0.0) produces different results than Glyphs.
        # Skewing just on of the two works.
        # Needs more attention.
        assert len(transformationMatrix) == 6
        for node in self.nodes:
            transformation = (
                Affine.translation(transformationMatrix[4], transformationMatrix[5])
                * Affine.scale(transformationMatrix[0], transformationMatrix[3])
                * Affine.shear(
                    transformationMatrix[2] * 45.0, transformationMatrix[1] * 45.0
                )
            )
            x, y = (node.position.x, node.position.y) * transformation
            node.position.x = x
            node.position.y = y

    def draw(self, pen: AbstractPen) -> None:
        """Draws contour with the given pen."""
        pointPen = PointToSegmentPen(pen)
        self.drawPoints(pointPen)

    def drawPoints(self, pointPen: AbstractPointPen) -> None:
        """Draws points of contour with the given point pen."""
        nodes = list(self.nodes)

        pointPen.beginPath()

        if not nodes:
            pointPen.endPath()
            return

        if not self.closed:
            node = nodes.pop(0)
            assert node.type == "line", "Open path starts with off-curve points"
            pointPen.addPoint(tuple(node.position), segmentType="move")
        else:
            # In Glyphs.app, the starting node of a closed contour is always
            # stored at the end of the nodes list.
            nodes.insert(0, nodes.pop())

        for node in nodes:
            node_type = node.type if node.type in _UFO_NODE_TYPES else None
            node_data = dict(node.userData)
            node_name = node_data.pop("name", None)
            pointPen.addPoint(
                tuple(node.position),
                segmentType=node_type,
                smooth=node.smooth,
                name=node_name,
                userData=node_data,
            )
        pointPen.endPath()


# 'offcurve' GSNode.type is equivalent to 'None' in UFO PointPen API
_UFO_NODE_TYPES = {"line", "curve", "qcurve"}


class segment(list):
    __slots__ = ("nodes", "parent", "index")

    def appendNode(self, node):
        if not hasattr(
            self, "nodes"
        ):  # instead of defining this in __init__(), because I hate super()
            self.nodes = []
        self.nodes.append(node)
        self.append(Point(node.position.x, node.position.y))

    @property
    def nextSegment(self):
        assert self.parent
        index = self.index
        if index == (len(self.parent._segments) - 1):
            return self.parent._segments[0]
        elif index < len(self.parent._segments):
            return self.parent._segments[index + 1]

    @property
    def prevSegment(self):
        assert self.parent
        index = self.index
        if index == 0:
            return self.parent._segments[-1]
        elif index < len(self.parent._segments):
            return self.parent._segments[index - 1]

    def bbox(self):
        if len(self) == 2:
            left = min(self[0].x, self[1].x)
            bottom = min(self[0].y, self[1].y)
            right = max(self[0].x, self[1].x)
            top = max(self[0].y, self[1].y)
            return left, bottom, right, top
        elif len(self) == 4:
            left, bottom, right, top = self.bezierMinMax(
                self[0].x,
                self[0].y,
                self[1].x,
                self[1].y,
                self[2].x,
                self[2].y,
                self[3].x,
                self[3].y,
            )
            return left, bottom, right, top
        else:
            raise ValueError

    def bezierMinMax(self, x0, y0, x1, y1, x2, y2, x3, y3):
        tvalues = []
        xvalues = []
        yvalues = []

        for i in range(2):
            if i == 0:
                b = 6 * x0 - 12 * x1 + 6 * x2
                a = -3 * x0 + 9 * x1 - 9 * x2 + 3 * x3
                c = 3 * x1 - 3 * x0
            else:
                b = 6 * y0 - 12 * y1 + 6 * y2
                a = -3 * y0 + 9 * y1 - 9 * y2 + 3 * y3
                c = 3 * y1 - 3 * y0

            if abs(a) < 1e-12:
                if abs(b) < 1e-12:
                    continue
                t = -c / b
                if 0 < t < 1:
                    tvalues.append(t)
                continue

            b2ac = b * b - 4 * c * a
            if b2ac < 0:
                continue
            sqrtb2ac = math.sqrt(b2ac)
            t1 = (-b + sqrtb2ac) / (2 * a)
            if 0 < t1 < 1:
                tvalues.append(t1)
            t2 = (-b - sqrtb2ac) / (2 * a)
            if 0 < t2 < 1:
                tvalues.append(t2)

        for j in range(len(tvalues) - 1, -1, -1):
            t = tvalues[j]
            mt = 1 - t
            newxValue = (
                (mt * mt * mt * x0)
                + (3 * mt * mt * t * x1)
                + (3 * mt * t * t * x2)
                + (t * t * t * x3)
            )
            if len(xvalues) > 0:
                xvalues[j] = newxValue
            else:
                xvalues.append(newxValue)
            newyValue = (
                (mt * mt * mt * y0)
                + (3 * mt * mt * t * y1)
                + (3 * mt * t * t * y2)
                + (t * t * t * y3)
            )
            if len(yvalues) > 0:
                yvalues[j] = newyValue
            else:
                yvalues.append(newyValue)

        xvalues.append(x0)
        xvalues.append(x3)
        yvalues.append(y0)
        yvalues.append(y3)

        return min(xvalues), min(yvalues), max(xvalues), max(yvalues)


class GSComponent(GSBase):
    __slots__ = (
        "alignment",
        "anchor",
        "locked",
        "name",
        "smartComponentValues",
        "transform",
    )

    _classesForName = {
        "alignment": int,
        "anchor": str,
        "locked": bool,
        "name": str,
        "piece": dict,
        "transform": Transform,
    }
    _wrapperKeysTranslate = {"piece": "smartComponentValues"}
    _defaultsForName = {"transform": Transform(1, 0, 0, 1, 0, 0)}
    _parent = None

    # TODO: glyph arg is required
    def __init__(self, glyph="", offset=(0, 0), scale=(1, 1), transform=None):
        self.alignment = 0
        self.anchor = ""
        self.locked = False

        if isinstance(glyph, str):
            self.name = glyph
        elif isinstance(glyph, GSGlyph):
            self.name = glyph.name

        self.smartComponentValues = {}

        if transform is None:
            if scale != (1, 1) or offset != (0, 0):
                xx, yy = scale
                dx, dy = offset
                self.transform = Transform(xx, 0, 0, yy, dx, dy)
            else:
                self.transform = copy.deepcopy(self._defaultsForName["transform"])
        else:
            self.transform = transform

    def __repr__(self):
        return '<GSComponent "{}" x={:.1f} y={:.1f}>'.format(
            self.name, self.transform[4], self.transform[5]
        )

    def shouldWriteValueForKey(self, key):
        if key == "piece":
            value = self.smartComponentValues
            return len(value) > 0
        return super().shouldWriteValueForKey(key)

    @property
    def parent(self):
        return self._parent

    # .position
    @property
    def position(self):
        return Point(self.transform[4], self.transform[5])

    @position.setter
    def position(self, value):
        self.transform[4] = value[0]
        self.transform[5] = value[1]

    # .scale
    @property
    def scale(self):
        self._sX, self._sY, self._R = transformStructToScaleAndRotation(
            self.transform.value
        )
        return self._sX, self._sY

    @scale.setter
    def scale(self, value):
        self._sX, self._sY, self._R = transformStructToScaleAndRotation(
            self.transform.value
        )
        if type(value) in [int, float]:
            self._sX = value
            self._sY = value
        elif type(value) in [tuple, list] and len(value) == 2:
            self._sX, self._sY = value
        else:
            raise ValueError
        self.updateAffineTransform()

    # .rotation
    @property
    def rotation(self):
        self._sX, self._sY, self._R = transformStructToScaleAndRotation(
            self.transform.value
        )
        return self._R

    @rotation.setter
    def rotation(self, value):
        self._sX, self._sY, self._R = transformStructToScaleAndRotation(
            self.transform.value
        )
        self._R = value
        self.updateAffineTransform()

    def updateAffineTransform(self):
        affine = list(
            Affine.translation(self.transform[4], self.transform[5])
            * Affine.scale(self._sX, self._sY)
            * Affine.rotation(self._R)
        )[:6]
        self.transform = Transform(
            affine[0], affine[1], affine[3], affine[4], affine[2], affine[5]
        )

    @property
    def componentName(self):
        return self.name

    @componentName.setter
    def componentName(self, value):
        self.name = value

    @property
    def component(self):
        return self.parent.parent.parent.glyphs[self.name]

    @property
    def layer(self):
        return self.parent.parent.parent.glyphs[self.name].layers[self.parent.layerId]

    def applyTransformation(self, x, y):
        x *= self.scale[0]
        y *= self.scale[1]
        x += self.position.x
        y += self.position.y
        # TODO:
        # Integrate rotation
        return x, y

    @property
    def bounds(self):
        bounds = self.layer.bounds
        if bounds is not None:
            left, bottom, width, height = self.layer.bounds
            right = left + width
            top = bottom + height

            left, bottom = self.applyTransformation(left, bottom)
            right, top = self.applyTransformation(right, top)

            if (
                left is not None
                and bottom is not None
                and right is not None
                and top is not None
            ):
                return Rect(Point(left, bottom), Point(right - left, top - bottom))

    # smartComponentValues = property(
    #     lambda self: self.piece,
    #     lambda self, value: setattr(self, "piece", value))

    def draw(self, pen: AbstractPen) -> None:
        """Draws component with given pen."""
        pen.addComponent(self.name, self.transform)

    def drawPoints(self, pointPen: AbstractPointPen) -> None:
        """Draws points of component with given point pen."""
        pointPen.addComponent(self.name, self.transform)


class GSSmartComponentAxis(GSBase):
    __slots__ = (
        "bottomName",
        "bottomValue",
        "name",
        "topName",
        "topValue",
    )

    _classesForName = {
        "name": str,
        "bottomName": str,
        "bottomValue": parse_float_or_int,
        "topName": str,
        "topValue": parse_float_or_int,
    }
    _defaultsForName = {"bottomValue": 0, "topValue": 0}
    _keyOrder = ("name", "bottomName", "bottomValue", "topName", "topValue")

    def __init__(self):
        self.bottomName = ""
        self.bottomValue = self._defaultsForName["bottomValue"]
        self.name = ""
        self.topName = ""
        self.topValue = self._defaultsForName["topValue"]

    def shouldWriteValueForKey(self, key):
        if key in ("bottomValue", "topValue"):
            return True
        return super().shouldWriteValueForKey(key)


class GSAnchor(GSBase):
    __slots__ = ("position", "name")

    _classesForName = {"name": str, "position": Point}
    _parent = None
    _defaultsForName = {"position": Point(0, 0)}

    def __init__(self, name=None, position=None):
        self.name = "" if name is None else name
        if position is None:
            self.position = copy.deepcopy(self._defaultsForName["position"])
        else:
            self.position = position

    def __repr__(self):
        return '<{} "{}" x={:.1f} y={:.1f}>'.format(
            self.__class__.__name__, self.name, self.position[0], self.position[1]
        )

    def shouldWriteValueForKey(self, key):
        if key == "position":
            return True
        return super().shouldWriteValueForKey(key)

    @property
    def parent(self):
        return self._parent


class GSHint(GSBase):
    __slots__ = (
        "_origin",
        "_originNode",
        "_other1",
        "_other2",
        "_otherNode1",
        "_otherNode2",
        "_target",
        "_targetNode",
        "horizontal",
        "name",
        "options",
        "place",
        "scale",
        "settings",
        "stem",
        "type",
    )

    _classesForName = {
        "horizontal": bool,
        "options": int,  # bitfield
        "origin": Point,  # Index path to node
        "other1": Point,  # Index path to node for third node
        "other2": Point,  # Index path to node for fourth node
        "place": Point,  # (position, width)
        "scale": Point,  # for corners
        "stem": int,  # index of stem
        "target": parse_hint_target,  # Index path to node or 'up'/'down'
        "type": str,
        "name": str,
        "settings": dict,
    }
    _defaultsForName = {
        # TODO: (jany) check defaults in glyphs
        "origin": None,
        "other1": None,
        "other2": None,
        "place": None,
        "scale": None,
        "stem": -2,
    }
    _keyOrder = (
        "horizontal",
        "origin",
        "place",
        "target",
        "other1",
        "other2",
        "scale",
        "type",
        "stem",
        "name",
        "options",
        "settings",
    )

    def __init__(self):
        self.horizontal = False
        self.name = ""
        self.options = 0
        self.origin = self._defaultsForName["origin"]
        self.other1 = self._defaultsForName["other1"]
        self.other2 = self._defaultsForName["other2"]
        self.place = self._defaultsForName["place"]
        self.scale = self._defaultsForName["scale"]
        self.settings = {}
        self.stem = self._defaultsForName["stem"]
        self.type = ""

    def shouldWriteValueForKey(self, key):
        if key == "settings" and (self.settings is None or len(self.settings) == 0):
            return None
        return super().shouldWriteValueForKey(key)

    def _origin_pos(self):
        if self.originNode:
            if self.horizontal:
                return self.originNode.position.y
            else:
                return self.originNode.position.x
        return self.origin

    def _width_pos(self):
        if self.targetNode:
            if self.horizontal:
                return self.targetNode.position.y
            else:
                return self.targetNode.position.x
        return self.width

    def __repr__(self):
        if self.horizontal:
            direction = "horizontal"
        else:
            direction = "vertical"
        if self.type == "BOTTOMGHOST" or self.type == "TOPGHOST":
            return "<GSHint {} origin=({})>".format(self.type, self._origin_pos())
        elif self.type == "STEM":
            return "<GSHint {} Stem origin=({}) target=({})>".format(
                direction, self._origin_pos(), self._width_pos()
            )
        elif self.type == "CORNER" or self.type == "CAP":
            return f"<GSHint {self.type} {self.name}>"
        else:
            return f"<GSHint {self.type} {direction}>"

    @property
    def parent(self):
        return self._parent

    @property
    def originNode(self):
        if self._originNode is not None:
            return self._originNode
        if self._origin is not None:
            return self.parent._find_node_by_indices(self._origin)

    @originNode.setter
    def originNode(self, node):
        self._originNode = node
        self._origin = None

    @property
    def origin(self):
        if self._origin is not None:
            return self._origin
        if self._originNode is not None:
            return self._originNode._indices()

    @origin.setter
    def origin(self, origin):
        self._origin = origin
        self._originNode = None

    @property
    def targetNode(self):
        if self._targetNode is not None:
            return self._targetNode
        if self._target is not None:
            return self.parent._find_node_by_indices(self._target)

    @targetNode.setter
    def targetNode(self, node):
        self._targetNode = node
        self._target = None

    @property
    def target(self):
        if self._target is not None:
            return self._target
        if self._targetNode is not None:
            return self._targetNode._indices()

    @target.setter
    def target(self, target):
        self._target = target
        self._targetNode = None

    @property
    def otherNode1(self):
        if self._otherNode1 is not None:
            return self._otherNode1
        if self._other1 is not None:
            return self.parent._find_node_by_indices(self._other1)

    @otherNode1.setter
    def otherNode1(self, node):
        self._otherNode1 = node
        self._other1 = None

    @property
    def other1(self):
        if self._other1 is not None:
            return self._other1
        if self._otherNode1 is not None:
            return self._otherNode1._indices()

    @other1.setter
    def other1(self, other1):
        self._other1 = other1
        self._otherNode1 = None

    @property
    def otherNode2(self):
        if self._otherNode2 is not None:
            return self._otherNode2
        if self._other2 is not None:
            return self.parent._find_node_by_indices(self._other2)

    @otherNode2.setter
    def otherNode2(self, node):
        self._otherNode2 = node
        self._other2 = None

    @property
    def other2(self):
        if self._other2 is not None:
            return self._other2
        if self._otherNode2 is not None:
            return self._otherNode2._indices()

    @other2.setter
    def other2(self, other2):
        self._other2 = other2
        self._otherNode2 = None


class GSFeature(GSBase):
    __slots__ = ("automatic", "_code", "disabled", "name", "notes")

    _classesForName = {
        "automatic": bool,
        "code": str,
        "name": str,
        "notes": str,
        "disabled": bool,
    }

    def __init__(self, name="xxxx", code=""):
        self.automatic = False
        self.code = code
        self.disabled = False
        self.name = name
        self.notes = ""

    def shouldWriteValueForKey(self, key):
        if key == "code":
            return True
        return super().shouldWriteValueForKey(key)

    def getCode(self):
        return self._code

    def setCode(self, code):
        replacements = (
            ("\\012", "\n"),
            ("\\011", "\t"),
            ("\\U2018", "'"),
            ("\\U2019", "'"),
            ("\\U201C", '"'),
            ("\\U201D", '"'),
        )
        for escaped, unescaped in replacements:
            code = code.replace(escaped, unescaped)
        self._code = code

    code = property(getCode, setCode)

    def __repr__(self):
        return f'<{self.__class__.__name__} "{self.name}">'

    @property
    def parent(self):
        return self._parent


class GSClass(GSFeature):
    pass


class GSFeaturePrefix(GSFeature):
    pass


class GSAnnotation(GSBase):
    __slots__ = (
        "angle",
        "position",
        "text",
        "type",
        "width",
    )

    _classesForName = {
        "angle": parse_float_or_int,
        "position": Point,
        "text": str,
        "type": str,
        "width": parse_float_or_int,  # the width of the text field or size of the cicle
    }
    _defaultsForName = {
        "angle": 0,
        "position": Point(0, 0),
        "text": None,
        "type": 0,
        "width": 100,
    }
    _parent = None

    def __init__(self):
        self.angle = self._defaultsForName["angle"]
        self.position = copy.deepcopy(self._defaultsForName["position"])
        self.text = self._defaultsForName["text"]
        self.type = self._defaultsForName["type"]
        self.width = self._defaultsForName["width"]

    @property
    def parent(self):
        return self._parent


class GSInstance(GSBase):
    __slots__ = (
        "_customParameters",
        "active",
        "custom",
        "customValue",
        "customValue1",
        "customValue2",
        "customValue3",
        "instanceInterpolations",
        "isBold",
        "isItalic",
        "linkStyle",
        "manualInterpolation",
        "name",
        "visible",
        "weight",
        "weightValue",
        "width",
        "widthValue",
    )

    _classesForName = {
        "customParameters": GSCustomParameter,
        "active": bool,
        "exports": bool,
        "instanceInterpolations": dict,
        "interpolationCustom": parse_float_or_int,
        "interpolationCustom1": parse_float_or_int,
        "interpolationCustom2": parse_float_or_int,
        "interpolationCustom3": parse_float_or_int,
        "interpolationWeight": parse_float_or_int,
        "interpolationWidth": parse_float_or_int,
        "isBold": bool,
        "isItalic": bool,
        "linkStyle": str,
        "manualInterpolation": bool,
        "name": str,
        "weightClass": str,
        "widthClass": str,
    }
    _defaultsForName = {
        "active": True,
        "exports": True,
        "interpolationCustom": 0,
        "interpolationCustom1": 0,
        "interpolationCustom2": 0,
        "interpolationCustom3": 0,
        "interpolationWeight": 100,
        "interpolationWidth": 100,
        "weightClass": "Regular",
        "widthClass": "Medium (normal)",
        "instanceInterpolations": {},
    }
    _keyOrder = (
        "active",
        "exports",
        "customParameters",
        "interpolationCustom",
        "interpolationCustom1",
        "interpolationCustom2",
        "interpolationCustom3",
        "interpolationWeight",
        "interpolationWidth",
        "instanceInterpolations",
        "isBold",
        "isItalic",
        "linkStyle",
        "manualInterpolation",
        "name",
        "weightClass",
        "widthClass",
    )
    _wrapperKeysTranslate = {
        "weightClass": "weight",
        "widthClass": "width",
        "interpolationWeight": "weightValue",
        "interpolationWidth": "widthValue",
        "interpolationCustom": "customValue",
        "interpolationCustom1": "customValue1",
        "interpolationCustom2": "customValue2",
        "interpolationCustom3": "customValue3",
    }

    def __init__(self):
        self._customParameters = []
        self.active = self._defaultsForName["active"]
        self.custom = None
        self.customValue = self._defaultsForName["interpolationCustom"]
        self.customValue1 = self._defaultsForName["interpolationCustom1"]
        self.customValue2 = self._defaultsForName["interpolationCustom2"]
        self.customValue3 = self._defaultsForName["interpolationCustom3"]
        self.instanceInterpolations = copy.deepcopy(
            self._defaultsForName["instanceInterpolations"]
        )
        self.isBold = False
        self.isItalic = False
        self.linkStyle = ""
        self.manualInterpolation = False
        self.name = "Regular"
        self.visible = True
        self.weight = self._defaultsForName["weightClass"]
        self.weightValue = self._defaultsForName["interpolationWeight"]
        self.width = self._defaultsForName["widthClass"]
        self.widthValue = self._defaultsForName["interpolationWidth"]

    customParameters = property(
        lambda self: CustomParametersProxy(self),
        lambda self, value: CustomParametersProxy(self).setter(value),
    )

    @property
    def exports(self):
        """Deprecated alias for `active`, which is in the documentation."""
        return self.active

    @exports.setter
    def exports(self, value):
        self.active = value

    @property
    def familyName(self):
        value = self.customParameters["familyName"]
        if value:
            return value
        return self.parent.familyName

    @familyName.setter
    def familyName(self, value):
        self.customParameters["familyName"] = value

    @property
    def preferredFamily(self):
        value = self.customParameters["preferredFamily"]
        if value:
            return value
        return self.parent.familyName

    @preferredFamily.setter
    def preferredFamily(self, value):
        self.customParameters["preferredFamily"] = value

    @property
    def preferredSubfamilyName(self):
        value = self.customParameters["preferredSubfamilyName"]
        if value:
            return value
        return self.name

    @preferredSubfamilyName.setter
    def preferredSubfamilyName(self, value):
        self.customParameters["preferredSubfamilyName"] = value

    @property
    def windowsFamily(self):
        value = self.customParameters["styleMapFamilyName"]
        if value:
            return value
        if self.name not in ("Regular", "Bold", "Italic", "Bold Italic"):
            return self.familyName + " " + self.name
        else:
            return self.familyName

    @windowsFamily.setter
    def windowsFamily(self, value):
        self.customParameters["styleMapFamilyName"] = value

    @property
    def windowsStyle(self):
        if self.name in ("Regular", "Bold", "Italic", "Bold Italic"):
            return self.name
        else:
            return "Regular"

    @property
    def windowsLinkedToStyle(self):
        value = self.linkStyle
        return value
        if self.name in ("Regular", "Bold", "Italic", "Bold Italic"):
            return self.name
        else:
            return "Regular"

    @property
    def fontName(self):
        value = self.customParameters["postscriptFontName"]
        if value:
            return value
        # TODO: strip invalid characters
        return "".join(self.familyName.split(" ")) + "-" + self.name

    @fontName.setter
    def fontName(self, value):
        self.customParameters["postscriptFontName"] = value

    @property
    def fullName(self):
        value = self.customParameters["postscriptFullName"]
        if value:
            return value
        return self.familyName + " " + self.name

    @fullName.setter
    def fullName(self, value):
        self.customParameters["postscriptFullName"] = value


class GSBackgroundImage(GSBase):
    __slots__ = (
        "_R",
        "_alpha",
        "_sX",
        "_sY",
        "crop",
        "imagePath",
        "locked",
        "transform",
    )

    _classesForName = {
        "crop": Rect,
        "imagePath": str,
        "locked": bool,
        "transform": Transform,
        "alpha": int,
    }
    _defaultsForName = {"alpha": 50, "transform": Transform(1, 0, 0, 1, 0, 0)}
    _wrapperKeysTranslate = {"alpha": "_alpha"}

    def __init__(self, path=None):
        self._R = 0.0
        self._sX = 1.0
        self._sY = 1.0
        self.alpha = self._defaultsForName["alpha"]
        self.crop = Rect()
        self.imagePath = path
        self.locked = False
        self.transform = copy.deepcopy(self._defaultsForName["transform"])

    def __repr__(self):
        return "<GSBackgroundImage '%s'>" % self.imagePath

    # .path
    @property
    def path(self):
        return self.imagePath

    @path.setter
    def path(self, value):
        # FIXME: (jany) use posix pathnames here?
        # FIXME: (jany) the following code must have never been tested.
        #   Also it would require to keep track of the parent for background
        #   images.
        # if os.path.dirname(os.path.abspath(value)) == \
        #       os.path.dirname(os.path.abspath(self.parent.parent.parent.filepath)):
        #     self.imagePath = os.path.basename(value)
        # else:
        self.imagePath = value

    # .position
    @property
    def position(self):
        return Point(self.transform[4], self.transform[5])

    @position.setter
    def position(self, value):
        self.transform[4] = value[0]
        self.transform[5] = value[1]

    # .scale
    @property
    def scale(self):
        return self._sX, self._sY

    @scale.setter
    def scale(self, value):
        if type(value) in [int, float]:
            self._sX = value
            self._sY = value
        elif type(value) in [tuple, list] and len(value) == 2:
            self._sX, self._sY = value
        else:
            raise ValueError
        self.updateAffineTransform()

    # .rotation
    @property
    def rotation(self):
        return self._R

    @rotation.setter
    def rotation(self, value):
        self._R = value
        self.updateAffineTransform()

    # .alpha
    @property
    def alpha(self):
        return self._alpha

    @alpha.setter
    def alpha(self, value):
        if not 10 <= value <= 100:
            value = 50
        self._alpha = value

    def updateAffineTransform(self):
        affine = list(
            Affine.translation(self.transform[4], self.transform[5])
            * Affine.scale(self._sX, self._sY)
            * Affine.rotation(self._R)
        )[:6]
        self.transform = Transform(
            affine[0], affine[1], affine[3], affine[4], affine[2], affine[5]
        )


class GSLayer(GSBase):
    __slots__ = (
        "_anchors",
        "_annotations",
        "_background",
        "_components",
        "_foreground",
        "_guides",
        "_hints",
        "_layerId",
        "_name",
        "_paths",
        "_selection",
        "_userData",
        "associatedMasterId",
        "backgroundImage",
        "color",
        "leftMetricsKey",
        "parent",
        "rightMetricsKey",
        "vertOrigin",
        "vertWidth",
        "visible",
        "width",
        "widthMetricsKey",
    )

    _classesForName = {
        "anchors": GSAnchor,
        "annotations": GSAnnotation,
        "associatedMasterId": str,
        # The next line is added after we define GSBackgroundLayer
        # "background": GSBackgroundLayer,
        "backgroundImage": GSBackgroundImage,
        "color": parse_color,
        "components": GSComponent,
        "guideLines": GSGuideLine,
        "hints": GSHint,
        "layerId": str,
        "leftMetricsKey": str,
        "name": str,
        "paths": GSPath,
        "rightMetricsKey": str,
        "userData": dict,
        "vertWidth": parse_float_or_int,
        "vertOrigin": parse_float_or_int,
        "visible": bool,
        "width": parse_float_or_int,
        "widthMetricsKey": str,
    }
    _defaultsForName = {
        "width": 600,
        "leftMetricsKey": None,
        "rightMetricsKey": None,
        "widthMetricsKey": None,
        "vertWidth": 0,
        "vertOrigin": 0,
    }
    _wrapperKeysTranslate = {"guideLines": "guides", "background": "_background"}
    _keyOrder = (
        "anchors",
        "annotations",
        "associatedMasterId",
        "background",
        "backgroundImage",
        "color",
        "components",
        "guideLines",
        "hints",
        "layerId",
        "leftMetricsKey",
        "widthMetricsKey",
        "rightMetricsKey",
        "name",
        "paths",
        "userData",
        "visible",
        "vertOrigin",
        "vertWidth",
        "width",
    )

    def __init__(self):
        self._anchors = []
        self._annotations = []
        self._background = None
        self._foreground = None
        self._components = []
        self._guides = []
        self._hints = []
        self._layerId = ""
        self._name = ""
        self._paths = []
        self._selection = []
        self._userData = None
        self.associatedMasterId = ""
        self.backgroundImage = None
        self.color = None
        self.leftMetricsKey = self._defaultsForName["leftMetricsKey"]
        self.parent = None
        self.rightMetricsKey = self._defaultsForName["rightMetricsKey"]
        self.vertOrigin = self._defaultsForName["vertOrigin"]
        self.vertWidth = self._defaultsForName["vertWidth"]
        self.visible = False
        self.width = self._defaultsForName["width"]
        self.widthMetricsKey = self._defaultsForName["widthMetricsKey"]

    def __setitem__(self, key, value):
        # On parsing, a background layer is attached to self via GSBase.__setitem__. We
        # must additionally set a backreference in it.
        super().__setitem__(key, value)
        if key == "background":
            self._background._foreground = self
            self._background.parent = self.parent

    def __repr__(self):
        name = self.name
        try:
            # assert self.name
            name = self.name
        except AttributeError:
            name = "orphan (n)"
        try:
            assert self.parent.name
            parent = self.parent.name
        except (AttributeError, AssertionError):
            parent = "orphan"
        return f'<{self.__class__.__name__} "{name}" ({parent})>'

    def __lt__(self, other):
        if self.master and other.master and self.associatedMasterId == self.layerId:
            return (
                self.master.weightValue < other.master.weightValue
                or self.master.widthValue < other.master.widthValue
            )

    @property
    def layerId(self):
        return self._layerId

    @layerId.setter
    def layerId(self, value):
        self._layerId = value
        # Update the layer map in the parent glyph, if any.
        # The "hasattr" is here because this setter is called by the GSBase
        # __init__() method before the parent property is set.
        if hasattr(self, "parent") and self.parent:
            parent_layers = OrderedDict()
            updated = False
            for id, layer in self.parent._layers.items():
                if layer == self:
                    parent_layers[self._layerId] = self
                    updated = True
                else:
                    parent_layers[id] = layer
            if not updated:
                parent_layers[self._layerId] = self
            self.parent._layers = parent_layers

    @property
    def master(self):
        if self.associatedMasterId and self.parent:
            master = self.parent.parent.masterForId(self.associatedMasterId)
            return master

    def shouldWriteValueForKey(self, key):
        if key == "width":
            return True
        if key == "associatedMasterId":
            return self.layerId != self.associatedMasterId
        if key == "name":
            return (
                self.name is not None
                and len(self.name) > 0
                and self.layerId != self.associatedMasterId
            )
        return super().shouldWriteValueForKey(key)

    @property
    def name(self):
        if (
            self.associatedMasterId
            and self.associatedMasterId == self.layerId
            and self.parent
        ):
            master = self.parent.parent.masterForId(self.associatedMasterId)
            if master:
                return master.name
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    anchors = property(
        lambda self: LayerAnchorsProxy(self),
        lambda self, value: LayerAnchorsProxy(self).setter(value),
    )

    hints = property(
        lambda self: LayerHintsProxy(self),
        lambda self, value: LayerHintsProxy(self).setter(value),
    )

    paths = property(
        lambda self: LayerPathsProxy(self),
        lambda self, value: LayerPathsProxy(self).setter(value),
    )

    components = property(
        lambda self: LayerComponentsProxy(self),
        lambda self, value: LayerComponentsProxy(self).setter(value),
    )

    guides = property(
        lambda self: LayerGuideLinesProxy(self),
        lambda self, value: LayerGuideLinesProxy(self).setter(value),
    )

    annotations = property(
        lambda self: LayerAnnotationProxy(self),
        lambda self, value: LayerAnnotationProxy(self).setter(value),
    )

    userData = property(
        lambda self: UserDataProxy(self),
        lambda self, value: UserDataProxy(self).setter(value),
    )

    @property
    def smartComponentPoleMapping(self):
        if "PartSelection" not in self.userData:
            self.userData["PartSelection"] = {}
        return self.userData["PartSelection"]

    @smartComponentPoleMapping.setter
    def smartComponentPoleMapping(self, value):
        self.userData["PartSelection"] = value

    @property
    def bounds(self):
        left, bottom, right, top = None, None, None, None

        for item in self.paths.values() + self.components.values():

            newLeft, newBottom, newWidth, newHeight = item.bounds
            newRight = newLeft + newWidth
            newTop = newBottom + newHeight

            if left is None:
                left = newLeft
            else:
                left = min(left, newLeft)
            if bottom is None:
                bottom = newBottom
            else:
                bottom = min(bottom, newBottom)
            if right is None:
                right = newRight
            else:
                right = max(right, newRight)
            if top is None:
                top = newTop
            else:
                top = max(top, newTop)

        if (
            left is not None
            and bottom is not None
            and right is not None
            and top is not None
        ):
            return Rect(Point(left, bottom), Point(right - left, top - bottom))

    def _find_node_by_indices(self, point):
        """"Find the GSNode that is refered to by the given indices.

        See GSNode::_indices()
        """
        path_index, node_index = point
        path = self.paths[int(path_index)]
        node = path.nodes[int(node_index)]
        return node

    @property
    def background(self):
        """Only a getter on purpose. See the tests."""
        if self._background is None:
            self._background = GSBackgroundLayer()
            self._background._foreground = self
            self._background.parent = self.parent
        return self._background

    # FIXME: (jany) how to check whether there is a background without calling
    #               ::background?
    @property
    def hasBackground(self):
        return bool(self._background)

    @property
    def foreground(self):
        """Forbidden, and also forbidden to set it."""
        raise AttributeError

    def getPen(self) -> AbstractPen:
        """Returns a pen for others to draw into self."""
        pen = SegmentToPointPen(self.getPointPen())
        return pen

    def getPointPen(self) -> AbstractPointPen:
        """Returns a point pen for others to draw points into self."""
        pointPen = LayerPointPen(self)
        return pointPen

    def draw(self, pen: AbstractPen) -> None:
        """Draws glyph with the given pen."""
        pointPen = PointToSegmentPen(pen)
        self.drawPoints(pointPen)

    def drawPoints(self, pointPen: AbstractPointPen) -> None:
        """Draws points of glyph with the given point pen."""
        for path in self.paths:
            path.drawPoints(pointPen)
        for component in self.components:
            component.drawPoints(pointPen)


class GSBackgroundLayer(GSLayer):
    def shouldWriteValueForKey(self, key):
        if key == "width":
            return False
        return super().shouldWriteValueForKey(key)

    @property
    def background(self):
        return None

    @property
    def foreground(self):
        return self._foreground

    # The width property of this class behaves like this in Glyphs:
    #  - Always returns 600.0
    #  - Settable but does not remember the value (basically useless)
    # Reproduce this behaviour here so that the roundtrip does not rely on it.
    @property
    def width(self):
        return 600

    @width.setter
    def width(self, whatever):
        pass


GSLayer._classesForName["background"] = GSBackgroundLayer


class GSGlyph(GSBase):
    __slots__ = (
        "_layers",
        "_unicodes",
        "_userData",
        "bottomKerningGroup",
        "bottomMetricsKey",
        "category",
        "color",
        "export",
        "lastChange",
        "leftKerningGroup",
        "leftKerningKey",
        "leftMetricsKey",
        "name",
        "note",
        "parent",
        "partsSettings",
        "production",
        "rightKerningGroup",
        "rightKerningKey",
        "rightMetricsKey",
        "script",
        "selected",
        "subCategory",
        "topKerningGroup",
        "topMetricsKey",
        "vertWidthMetricsKey",
        "widthMetricsKey",
    )

    _classesForName = {
        "bottomKerningGroup": str,
        "bottomMetricsKey": str,
        "category": str,
        "color": parse_color,
        "export": bool,
        "glyphname": str,
        "lastChange": parse_datetime,
        "layers": GSLayer,
        "leftKerningGroup": str,
        "leftKerningKey": str,
        "leftMetricsKey": str,
        "note": str,
        "partsSettings": GSSmartComponentAxis,
        "production": str,
        "rightKerningGroup": str,
        "rightKerningKey": str,
        "rightMetricsKey": str,
        "script": str,
        "subCategory": str,
        "topKerningGroup": str,
        "topMetricsKey": str,
        "unicode": UnicodesList,
        "userData": dict,
        "vertWidthMetricsKey": str,
        "widthMetricsKey": str,
    }
    _wrapperKeysTranslate = {
        "unicode": "unicodes",
        "glyphname": "name",
        "partsSettings": "smartComponentAxes",
    }
    _defaultsForName = {
        "category": None,
        "color": None,
        "export": True,
        "lastChange": None,
        "leftKerningGroup": None,
        "leftMetricsKey": None,
        "name": None,
        "note": None,
        "rightKerningGroup": None,
        "rightMetricsKey": None,
        "script": None,
        "subCategory": None,
        "userData": None,
        "widthMetricsKey": None,
    }
    _keyOrder = (
        "color",
        "export",
        "glyphname",
        "production",
        "lastChange",
        "layers",
        "leftKerningGroup",
        "leftMetricsKey",
        "widthMetricsKey",
        "vertWidthMetricsKey",
        "note",
        "rightKerningGroup",
        "rightMetricsKey",
        "topKerningGroup",
        "topMetricsKey",
        "bottomKerningGroup",
        "bottomMetricsKey",
        "unicode",
        "script",
        "category",
        "subCategory",
        "userData",
        "partsSettings",
    )

    def __init__(self, name=None):
        self._layers = OrderedDict()
        self._unicodes = []
        self.bottomKerningGroup = ""
        self.bottomMetricsKey = ""
        self.category = self._defaultsForName["category"]
        self.color = self._defaultsForName["color"]
        self.export = self._defaultsForName["export"]
        self.lastChange = self._defaultsForName["lastChange"]
        self.leftKerningGroup = self._defaultsForName["leftKerningGroup"]
        self.leftKerningKey = ""
        self.leftMetricsKey = self._defaultsForName["leftMetricsKey"]
        self.name = name
        self.note = self._defaultsForName["note"]
        self.parent = None
        self.partsSettings = []
        self.production = ""
        self.rightKerningGroup = self._defaultsForName["rightKerningGroup"]
        self.rightKerningKey = ""
        self.rightMetricsKey = self._defaultsForName["rightMetricsKey"]
        self.script = self._defaultsForName["script"]
        self.selected = False
        self.subCategory = self._defaultsForName["subCategory"]
        self.topKerningGroup = ""
        self.topMetricsKey = ""
        self.userData = self._defaultsForName["userData"]
        self.vertWidthMetricsKey = ""
        self.widthMetricsKey = self._defaultsForName["widthMetricsKey"]

    def __repr__(self):
        return '<GSGlyph "{}" with {} layers>'.format(self.name, len(self.layers))

    def shouldWriteValueForKey(self, key):
        if key in ("script", "category", "subCategory"):
            return getattr(self, key) is not None
        return super().shouldWriteValueForKey(key)

    layers = property(
        lambda self: GlyphLayerProxy(self),
        lambda self, value: GlyphLayerProxy(self).setter(value),
    )

    def _setupLayer(self, layer, key):
        assert isinstance(key, str)
        layer.parent = self
        if layer.hasBackground:
            layer._background.parent = self
        layer.layerId = key
        # TODO use proxy `self.parent.masters[key]`
        if self.parent and self.parent.masterForId(key):
            layer.associatedMasterId = key

    # def setLayerForKey(self, layer, key):
    #     if Layer and Key:
    #         Layer.parent = self
    #         Layer.layerId = Key
    #         if self.parent.fontMasterForId(Key):
    #             Layer.associatedMasterId = Key
    #         self._layers[key] = layer

    def removeLayerForKey_(self, key):
        for layer in list(self._layers):
            if layer == key:
                del self._layers[key]

    @property
    def string(self):
        if self.unicode:
            return chr(int(self.unicode, 16))

    userData = property(
        lambda self: UserDataProxy(self),
        lambda self, value: UserDataProxy(self).setter(value),
    )

    @property
    def glyphname(self):
        return self.name

    @glyphname.setter
    def glyphname(self, value):
        self.name = value

    @property
    def smartComponentAxes(self):
        return self.partsSettings

    @smartComponentAxes.setter
    def smartComponentAxes(self, value):
        self.partsSettings = value

    @property
    def id(self):
        """An unique identifier for each glyph"""
        return self.name

    @property
    def unicode(self):
        if self._unicodes:
            return self._unicodes[0]
        return None

    @unicode.setter
    def unicode(self, unicode):
        self._unicodes = UnicodesList(unicode)

    @property
    def unicodes(self):
        return self._unicodes

    @unicodes.setter
    def unicodes(self, unicodes):
        self._unicodes = UnicodesList(unicodes)


class GSFont(GSBase):
    __slots__ = (
        "DisplayStrings",
        "_classes",
        "_customParameters",
        "_features",
        "_glyphs",
        "_instances",
        "_kerning",
        "_masters",
        "_userData",
        "_versionMinor",
        "appVersion",
        "copyright",
        "date",
        "designer",
        "designerURL",
        "disablesAutomaticAlignment",
        "disablesNiceNames",
        "familyName",
        "featurePrefixes",
        "filepath",
        "grid",
        "gridSubDivisions",
        "keepAlternatesTogether",
        "keyboardIncrement",
        "manufacturer",
        "manufacturerURL",
        "upm",
        "versionMajor",
    )

    _classesForName = {
        ".appVersion": str,
        "DisplayStrings": str,
        "classes": GSClass,
        "copyright": str,
        "customParameters": GSCustomParameter,
        "date": parse_datetime,
        "designer": str,
        "designerURL": str,
        "disablesAutomaticAlignment": bool,
        "disablesNiceNames": bool,
        "familyName": str,
        "featurePrefixes": GSFeaturePrefix,
        "features": GSFeature,
        "fontMaster": GSFontMaster,
        "glyphs": GSGlyph,
        "gridLength": int,
        "gridSubDivision": int,
        "instances": GSInstance,
        "keepAlternatesTogether": bool,
        "kerning": OrderedDict,
        "keyboardIncrement": parse_float_or_int,
        "manufacturer": str,
        "manufacturerURL": str,
        "unitsPerEm": int,
        "userData": dict,
        "versionMajor": int,
        "versionMinor": int,
    }
    _wrapperKeysTranslate = {
        ".appVersion": "appVersion",
        "fontMaster": "masters",
        "unitsPerEm": "upm",
        "gridLength": "grid",
        "gridSubDivision": "gridSubDivisions",
    }
    _defaultsForName = {
        "classes": [],
        "customParameters": [],
        "disablesAutomaticAlignment": False,
        "disablesNiceNames": False,
        "gridLength": 1,
        "gridSubDivision": 1,
        "unitsPerEm": 1000,
        "kerning": OrderedDict(),
        "keyboardIncrement": 1,
    }

    def __init__(self, path=None):
        self.DisplayStrings = ""
        self._features = []
        self._glyphs = []
        self._instances = []
        self._masters = []
        self._userData = None
        self._versionMinor = 0
        self.appVersion = "895"  # minimum required version
        self.classes = copy.deepcopy(self._defaultsForName["classes"])
        self.copyright = ""
        self.customParameters = copy.deepcopy(self._defaultsForName["customParameters"])
        self.date = None
        self.designer = ""
        self.designerURL = ""
        self.disablesAutomaticAlignment = self._defaultsForName[
            "disablesAutomaticAlignment"
        ]
        self.disablesNiceNames = self._defaultsForName["disablesNiceNames"]
        self.familyName = "Unnamed font"
        self.featurePrefixes = []
        self.filepath = None
        self.grid = self._defaultsForName["gridLength"]
        self.gridSubDivisions = self._defaultsForName["gridSubDivision"]
        self.keepAlternatesTogether = False
        self.kerning = copy.deepcopy(self._defaultsForName["kerning"])
        self.keyboardIncrement = self._defaultsForName["keyboardIncrement"]
        self.manufacturer = ""
        self.manufacturerURL = ""
        self.upm = self._defaultsForName["unitsPerEm"]
        self.versionMajor = 1

        if path:
            path = os.fsdecode(os.fspath(path))
            assert os.path.splitext(path)[-1] == ".glyphs", (
                "Please supply a file path to a .glyphs file",
            )

            with open(path, "r", encoding="utf-8") as fp:
                logger.info('Parsing "%s" file into <GSFont>', path)
                p = Parser()
                p.parse_into_object(self, fp.read())
            self.filepath = path
            for master in self.masters:
                master.font = self

    def __repr__(self):
        return f'<{self.__class__.__name__} "{self.familyName}">'

    def shouldWriteValueForKey(self, key):
        if key in ("unitsPerEm", "versionMajor", "versionMinor"):
            return True
        return super().shouldWriteValueForKey(key)

    def save(self, path=None):
        if path is None:
            if self.filepath:
                path = self.filepath
            else:
                raise ValueError("No path provided and GSFont has no filepath")
        with open(path, "w", encoding="utf-8") as fp:
            w = Writer(fp)
            logger.info("Writing %r to .glyphs file", self)
            w.write(self)

    def getVersionMinor(self):
        return self._versionMinor

    def setVersionMinor(self, value):
        """Ensure that the minor version number is between 0 and 999."""
        assert 0 <= value <= 999
        self._versionMinor = value

    versionMinor = property(getVersionMinor, setVersionMinor)

    glyphs = property(
        lambda self: FontGlyphsProxy(self),
        lambda self, value: FontGlyphsProxy(self).setter(value),
    )

    def _setupGlyph(self, glyph):
        glyph.parent = self
        for layer in glyph.layers:
            if (
                not hasattr(layer, "associatedMasterId")
                or layer.associatedMasterId is None
                or len(layer.associatedMasterId) == 0
            ):
                glyph._setupLayer(layer, layer.layerId)

    @property
    def features(self):
        return self._features

    @features.setter
    def features(self, value):
        # FIXME: (jany) why not use Proxy like every other attribute?
        # FIXME: (jany) do the same for featurePrefixes?
        self._features = value
        for g in self._features:
            g._parent = self

    masters = property(
        lambda self: FontFontMasterProxy(self),
        lambda self, value: FontFontMasterProxy(self).setter(value),
    )

    def masterForId(self, key):
        for master in self._masters:
            if master.id == key:
                return master
        return None

    # FIXME: (jany) Why is this not a FontInstanceProxy?
    @property
    def instances(self):
        return self._instances

    @instances.setter
    def instances(self, value):
        self._instances = value
        for i in self._instances:
            i.parent = self

    classes = property(
        lambda self: FontClassesProxy(self),
        lambda self, value: FontClassesProxy(self).setter(value),
    )

    customParameters = property(
        lambda self: CustomParametersProxy(self),
        lambda self, value: CustomParametersProxy(self).setter(value),
    )

    userData = property(
        lambda self: UserDataProxy(self),
        lambda self, value: UserDataProxy(self).setter(value),
    )

    @property
    def kerning(self):
        return self._kerning

    @kerning.setter
    def kerning(self, kerning):
        self._kerning = kerning
        for master_map in kerning.values():
            for glyph_map in master_map.values():
                for right_glyph, value in glyph_map.items():
                    glyph_map[right_glyph] = parse_float_or_int(value)

    @property
    def selection(self):
        return (glyph for glyph in self.glyphs if glyph.selected)

    @property
    def note(self):
        value = self.customParameters["note"]
        if value:
            return value
        else:
            return ""

    @note.setter
    def note(self, value):
        self.customParameters["note"] = value

    @property
    def gridLength(self):
        if self.gridSubDivisions > 0:
            return self.grid / self.gridSubDivisions
        else:
            return self.grid

    EMPTY_KERNING_VALUE = (1 << 63) - 1  # As per the documentation

    def kerningForPair(self, fontMasterId, leftKey, rightKey, direction=LTR):
        # TODO: (jany) understand and use the direction parameter
        if not self._kerning:
            return self.EMPTY_KERNING_VALUE
        try:
            return self._kerning[fontMasterId][leftKey][rightKey]
        except KeyError:
            return self.EMPTY_KERNING_VALUE

    def setKerningForPair(self, fontMasterId, leftKey, rightKey, value, direction=LTR):
        # TODO: (jany) understand and use the direction parameter
        if not self._kerning:
            self._kerning = {}
        if fontMasterId not in self._kerning:
            self._kerning[fontMasterId] = {}
        if leftKey not in self._kerning[fontMasterId]:
            self._kerning[fontMasterId][leftKey] = {}
        self._kerning[fontMasterId][leftKey][rightKey] = value

    def removeKerningForPair(self, fontMasterId, leftKey, rightKey, direction=LTR):
        # TODO: (jany) understand and use the direction parameter
        if not self._kerning:
            return
        if fontMasterId not in self._kerning:
            return
        if leftKey not in self._kerning[fontMasterId]:
            return
        if rightKey not in self._kerning[fontMasterId][leftKey]:
            return
        del self._kerning[fontMasterId][leftKey][rightKey]
        if not self._kerning[fontMasterId][leftKey]:
            del self._kerning[fontMasterId][leftKey]
        if not self._kerning[fontMasterId]:
            del self._kerning[fontMasterId]


Number = Union[int, float]


class LayerPointPen(AbstractPointPen):
    """A point pen to draw onto GSLayer object.

    See :mod:`fontTools.pens.basePen` and :mod:`fontTools.pens.pointPen` for an
    introduction to pens.
    """

    __slots__ = ("_layer", "_path")

    def __init__(self, layer: GSLayer) -> None:
        self._layer: GSLayer = layer
        self._path: Optional[GSPath] = None

    def beginPath(self, **kwargs: Any) -> None:
        if self._path is not None:
            raise ValueError("Call endPath first.")

        self._path = GSPath()
        self._path.closed = True  # Until proven otherwise.

    def endPath(self) -> None:
        if self._path is None:
            raise ValueError("Call beginPath first.")

        if self._path.closed:
            self._path.nodes.append(self._path.nodes.pop(0))
        self._layer.paths.append(self._path)
        self._path = None

    def addPoint(
        self,
        pt: Tuple[Number, Number],
        segmentType: Optional[str] = None,
        smooth: bool = False,
        name: Optional[str] = None,
        userData: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        if self._path is None:
            raise ValueError("Call beginPath first.")

        if segmentType == "move":
            if self._path.nodes:
                raise ValueError("For an open contour, 'move' must come first.")
            self._path.closed = False

        node = GSNode(
            Point(*pt),
            nodetype=_to_glyphs_node_type(segmentType),
            smooth=smooth,
            name=name,
        )
        if userData:
            node.userData = userData
        self._path.nodes.append(node)

    def addComponent(
        self,
        baseGlyph: str,
        transformation: Union[
            Transform, Tuple[float, float, float, float, float, float]
        ],
        **kwargs: Any,
    ) -> None:
        if not isinstance(transformation, Transform):
            transformation = Transform(*transformation)
        component = GSComponent(baseGlyph, transform=transformation)
        self._layer.components.append(component)


def _to_glyphs_node_type(node_type):
    if node_type is None:
        return OFFCURVE
    if node_type == "move":
        return LINE
    return node_type
