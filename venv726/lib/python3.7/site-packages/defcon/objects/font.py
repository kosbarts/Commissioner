from __future__ import absolute_import
import os
import re
import tempfile
import shutil
from fontTools.misc.py23 import basestring
from fontTools.ufoLib import UFOReader, UFOWriter, UFOLibError, UFOFileStructure
from defcon.objects.base import BaseObject
from defcon.objects.layerSet import LayerSet
from defcon.objects.info import Info
from defcon.objects.kerning import Kerning
from defcon.objects.groups import Groups
from defcon.objects.features import Features
from defcon.objects.lib import Lib
from defcon.objects.imageSet import ImageSet
from defcon.objects.dataSet import DataSet
from defcon.objects.guideline import Guideline
from defcon.tools.notifications import NotificationCenter
from functools import partial
import logging


logger = logging.getLogger(__name__)


class Font(BaseObject):

    """
    If loading from an existing UFO, **path** should be the path to the UFO.

    If you subclass one of the sub objects, such as :class:`Glyph`,
    the class must be registered when the font is created for defcon
    to know about it. The **\*Class** arguments allow for individual
    ovverrides. If None is provided for an argument, the defcon
    appropriate class will be used.

    **This object posts the following notifications:**

    ======================
    Name
    ======================
    Font.Changed
    Font.ReloadedGlyphs
    Font.GlyphOrderChanged
    Font.GuidelinesChanged
    Font.GuidelineWillBeDeleted
    ======================

    The Font object has some dict like behavior. For example, to get a glyph::

        glyph = font["aGlyphName"]

    To iterate over all glyphs::

        for glyph in font:

    To get the number of glyphs::

        glyphCount = len(font)

    To find out if a font contains a particular glyph::

        exists = "aGlyphName" in font

    To remove a glyph::

        del font["aGlyphName"]
    """

    changeNotificationName = "Font.Changed"
    representationFactories = {}

    def __init__(self, path=None,
                    kerningClass=None, infoClass=None, groupsClass=None, featuresClass=None, libClass=None, unicodeDataClass=None,
                    layerSetClass=None, layerClass=None, imageSetClass=None, dataSetClass=None,
                    guidelineClass=None,
                    glyphClass=None, glyphContourClass=None, glyphPointClass=None, glyphComponentClass=None, glyphAnchorClass=None, glyphImageClass=None):

        super(Font, self).__init__()
        self._dispatcher = NotificationCenter()
        self.beginSelfNotificationObservation()

        if infoClass is None:
            infoClass = Info
        if kerningClass is None:
            kerningClass = Kerning
        if groupsClass is None:
            groupsClass = Groups
        if featuresClass is None:
            featuresClass = Features
        if libClass is None:
            libClass = Lib
        if layerSetClass is None:
            layerSetClass = LayerSet
        if imageSetClass is None:
            imageSetClass = ImageSet
        if dataSetClass is None:
            dataSetClass = DataSet
        if guidelineClass is None:
            guidelineClass = Guideline
        self._unicodeDataClass = unicodeDataClass
        self._layerSetClass = layerSetClass
        self._layerClass = layerClass
        self._glyphClass = glyphClass
        self._glyphContourClass = glyphContourClass
        self._glyphPointClass = glyphPointClass
        self._glyphComponentClass = glyphComponentClass
        self._glyphAnchorClass = glyphAnchorClass
        self._glyphImageClass = glyphImageClass
        self._kerningClass = kerningClass
        self._infoClass = infoClass
        self._groupsClass = groupsClass
        self._featuresClass = featuresClass
        self._libClass = libClass
        self._guidelineClass = guidelineClass
        self._imageSetClass = imageSetClass
        self._dataSetClass = dataSetClass

        self._path = path
        self._ufoFormatVersion = None
        self._ufoFileStructure = None

        self._kerning = None
        self._info = None
        self._groups = None
        self._features = None
        self._lib = None
        self._kerningGroupConversionRenameMaps = None

        self._layers = self.instantiateLayerSet()
        self.beginSelfLayerSetNotificationObservation()
        self._images = self.instantiateImageSet()
        self.beginSelfImageSetNotificationObservation()
        self._data = self.instantiateDataSet()
        self.beginSelfDataSetNotificationObservation()

        self._guidelines = []
        self._identifiers = set()

        self._dirty = False

        if path:
            if not isinstance(path, basestring) and not hasattr(path, "__fspath__"):
                raise TypeError(
                    "invalid path: expected string or os.PathLike, found %s"
                    % type(path).__name__
                )
            reader = UFOReader(self._path, validate=self.ufoLibReadValidate)
            self._ufoFormatVersion = reader.formatVersion
            self._ufoFileStructure = reader.fileStructure
            # go ahead and load the layers
            self._layers.disableNotifications()
            layerNames = reader.getLayerNames()
            for layerName in layerNames:
                glyphSet = reader.getGlyphSet(layerName, validateRead=self._layers.ufoLibReadValidate, validateWrite=self._layers.ufoLibWriteValidate)
                layer = self._layers.newLayer(layerName, glyphSet=glyphSet)
                layer.dirty = False
                self._beginSelfLayerNotificationObservation(layer)
            defaultLayerName = reader.getDefaultLayerName()
            self._layers.layerOrder = layerNames
            self._layers.defaultLayer = self._layers[defaultLayerName]
            self._layers.dirty = False
            self._layers.enableNotifications()
            # get the image file names
            self._images.disableNotifications()
            self._images.fileNames = reader.getImageDirectoryListing()
            self._images.enableNotifications()
            # get the data directory listing
            self._data.disableNotifications()
            self._data.fileNames = reader.getDataDirectoryListing()
            self._data.enableNotifications()
            # if the UFO version is 1, do some conversion.
            if self._ufoFormatVersion == 1:
                self._convertFromFormatVersion1RoboFabData()
            # if the ufo version is < 3, read the kerning and groups
            # right now. do this by creating a reference to the reader.
            # otherwise a situation could arise where the groups
            # are modified by an external source before being read.
            # that could create a data corruption within this object.
            if self._ufoFormatVersion < 3:
                self._reader = reader
                self._kerningGroupConversionRenameMaps = reader.getKerningGroupConversionRenameMaps()
                k = self.kerning
                g = self.groups
            else:
                # unless we did some conversion from an older ufo-format, mark
                # the font as unmodified
                self._dirty = False

        if self._layers.defaultLayer is None:
            layer = self.newLayer("public.default")
            self._layers.defaultLayer = layer

    def _get_dispatcher(self):
        return self._dispatcher

    dispatcher = property(_get_dispatcher, doc="The :class:`defcon.tools.notifications.NotificationCenter` assigned to this font.")

    # ------
    # Glyphs
    # ------

    def _get_glyphSet(self):
        return self._layers.defaultLayer

    _glyphSet = property(_get_glyphSet, doc="Convenience for getting the main layer.")

    def newGlyph(self, name):
        """
        Create a new glyph with **name** in the font's main layer.
        If a glyph with that name already exists, the existing
        glyph will be replaced with the new glyph.
        """
        return self._glyphSet.newGlyph(name)

    def insertGlyph(self, glyph, name=None):
        """
        Insert **glyph** into the font's main layer.
        Optionally, the glyph can be renamed at the same time by
        providing **name**. If a glyph with the glyph name, or
        the name provided as **name**, already exists, the existing
        glyph will be replaced with the new glyph.
        """
        return self._glyphSet.insertGlyph(glyph, name=name)

    def __iter__(self):
        for name in self._glyphSet.keys():
            yield self._glyphSet[name]

    def __getitem__(self, name):
        return self._glyphSet[name]

    def __delitem__(self, name):
        del self._glyphSet[name]

    def __len__(self):
        return len(self._glyphSet)

    def __contains__(self, name):
        return name in self._glyphSet

    def keys(self):
        return self._glyphSet.keys()

    # ------
    # Layers
    # ------

    def newLayer(self, name):
        """
        Create a new :class:`Layer` and add it to
        the top of the layer order.

        This posts *LayerSet.LayerAdded* and *LayerSet.Changed* notifications.
        """
        return self._layers.newLayer(name)

    # ----------
    # Attributes
    # ----------

    def _get_path(self):
        return self._path

    def _set_path(self, path):
        # XXX: this needs to be reworked for layers
        if not isinstance(path, basestring) and not hasattr(path, "__fspath__"):
            raise TypeError(
                "invalid path: expected string or os.PathLike, found %s"
                % type(path).__name__
            )
        # the file must already exist
        assert os.path.exists(path)
        self._path = path

    path = property(_get_path, _set_path, doc="The location of the file on disk. Setting the path should only be done when the user has moved the file in the OS interface. Setting the path is not the same as a save operation.")

    def _get_ufoFormatVersion(self):
        return self._ufoFormatVersion

    ufoFormatVersion = property(_get_ufoFormatVersion, doc="The UFO format version that will be used when saving. This is taken from a loaded UFO during __init__. If this font was not loaded from a UFO, this will return None until the font has been saved.")

    def _get_ufoFileStructure(self):
        return self._ufoFileStructure

    ufoFileStructure = property(
        _get_ufoFileStructure,
        doc=(
            "The UFO file structure that will be used when saving. "
            "This is taken from a loaded UFO during __init__. "
            "If this font was not loaded from a UFO, this will return None "
            "until the font has been saved."
        )
    )

    def _get_kerningGroupConversionRenameMaps(self):
        return self._kerningGroupConversionRenameMaps

    def _set_kerningGroupConversionRenameMaps(self, value):
        self._kerningGroupConversionRenameMaps = value

    kerningGroupConversionRenameMaps = property(_get_kerningGroupConversionRenameMaps, _set_kerningGroupConversionRenameMaps, doc="The kerning group rename map that will be used when writing UFO 1 and UFO 2. This follows the format defined in UFOReader. This will only not be None if it has been set or this object was loaded from a UFO 1 or UFO 2 file.")

    def _get_glyphsWithOutlines(self):
        return self._glyphSet.glyphsWithOutlines

    glyphsWithOutlines = property(_get_glyphsWithOutlines, doc="A list of glyphs containing outlines in the font's main layer.")

    def _get_componentReferences(self):
        return self._glyphSet.componentReferences

    componentReferences = property(_get_componentReferences, doc="A dict of describing the component relationships in the font's main layer. The dictionary is of form ``{base glyph : [references]}``.")

    def _get_bounds(self):
        return self._glyphSet.bounds

    bounds = property(_get_bounds, doc="The bounds of all glyphs in the font's main layer. This can be an expensive operation.")

    def _get_controlPointBounds(self):
        return self._glyphSet.controlPointBounds

    controlPointBounds = property(_get_controlPointBounds, doc="The control bounds of all glyphs in the font's main layer. This only measures the point positions, it does not measure curves. So, curves without points at the extrema will not be properly measured. This is an expensive operation.")

    # -----------
    # Sub-Objects
    # -----------

    # layers

    def instantiateLayerSet(self):
        layers = self._layerSetClass(
            font=self,
            libClass=self._libClass,
            unicodeDataClass=self._unicodeDataClass,
            guidelineClass=self._guidelineClass,
            layerClass=self._layerClass,
            glyphClass=self._glyphClass,
            glyphContourClass=self._glyphContourClass,
            glyphPointClass=self._glyphPointClass,
            glyphComponentClass=self._glyphComponentClass,
            glyphAnchorClass=self._glyphAnchorClass,
            glyphImageClass=self._glyphImageClass
        )
        return layers

    def beginSelfLayerSetNotificationObservation(self):
        layers = self.layers
        layers.addObserver(observer=self, methodName="_objectDirtyStateChange", notification="LayerSet.Changed")
        layers.addObserver(observer=self, methodName="_layerAddedNotificationCallback", notification="LayerSet.LayerAdded")
        layers.addObserver(observer=self, methodName="_layerWillBeDeletedNotificationCallback", notification="LayerSet.LayerWillBeDeleted")

    def endSelfLayerSetNotificationObservation(self):
        layers = self.layers
        if layers.dispatcher is None:
            return
        layers.removeObserver(observer=self, notification="LayerSet.Changed")
        layers.removeObserver(observer=self, notification="LayerSet.LayerAdded")
        layers.removeObserver(observer=self, notification="LayerSet.LayerWillBeDeleted")
        layers.endSelfNotificationObservation()

    def _get_layers(self):
        return self._layers

    layers = property(_get_layers, doc="The font's :class:`LayerSet` object.")

    # info

    def instantiateInfo(self):
        info = self._infoClass(
            font=self,
        )
        return info

    def beginSelfInfoSetNotificationObservation(self):
        info = self.info
        info.addObserver(observer=self, methodName="_objectDirtyStateChange", notification="Info.Changed")

    def endSelfInfoSetNotificationObservation(self):
        if self._info is None:
            return
        if self._info.dispatcher is None:
            return
        self._info.removeObserver(observer=self, notification="Info.Changed")
        self._info.endSelfNotificationObservation()

    def _get_info(self):
        if self._info is None:
            self._info = self.instantiateInfo()
            self.beginSelfInfoSetNotificationObservation()
            reader = None
            if self._path is not None:
                # info also contains the _font_ guidelines, disable self notifications
                # and bookkeep dirty
                dirty = self.dirty
                self.disableNotifications()
                #
                self._info.disableNotifications()
                reader = UFOReader(self._path, validate=False)
                reader.readInfo(self._info, validate=self._info.ufoLibReadValidate)
                self._info.dirty = False
                self._info.enableNotifications()
                #
                self.dirty = dirty
                self.enableNotifications()
                #
            self._stampInfoDataState(reader)
        return self._info

    info = property(_get_info, doc="The font's :class:`Info` object.")

    # kerning

    def _loadKerningAndGroups(self):
        # read
        if hasattr(self, "_reader"):
            reader = self._reader
        else:
            reader = UFOReader(self._path, validate=False)
        # instantiate everything and store it if valid
        self._groups = self.instantiateGroups()
        self.beginSelfGroupsNotificationObservation()
        self._kerning = self.instantiateKerning()
        self.beginSelfKerningNotificationObservation()
        # load data
        kerning = reader.readKerning(validate=self._kerning.ufoLibReadValidate)
        groups = reader.readGroups(validate=self._groups.ufoLibReadValidate)
        # Note: the incoming kerning data has not been validated.
        # Gremlins may be sneaking in through here.
        ## store groups
        self._groups.disableNotifications()
        self._groups.update(groups)
        self._groups.dirty = False
        self._groups.enableNotifications()
        self._stampGroupsDataState(reader)
        ## store kerning
        self._kerning.disableNotifications()
        self._kerning.update(kerning)
        self._kerning.dirty = False
        self._kerning.enableNotifications()
        self._stampKerningDataState(reader)

    def instantiateKerning(self):
        kerning = self._kerningClass(
            font=self
        )
        return kerning

    def beginSelfKerningNotificationObservation(self):
        kerning = self.kerning
        kerning.addObserver(observer=self, methodName="_objectDirtyStateChange", notification="Kerning.Changed")

    def endSelfKerningNotificationObservation(self):
        if self._kerning is None:
            return
        if self._kerning.dispatcher is None:
            return
        self._kerning.removeObserver(observer=self, notification="Kerning.Changed")
        self._kerning.endSelfNotificationObservation()

    def _get_kerning(self):
        if self._kerning is None:
            if self._path is None:
                self._kerning = self.instantiateKerning()
                self.beginSelfKerningNotificationObservation()
                self._stampKerningDataState(None)
            else:
                self._loadKerningAndGroups()
        return self._kerning

    kerning = property(_get_kerning, doc="The font's :class:`Kerning` object.")

    # groups

    def instantiateGroups(self):
        groups = self._groupsClass(
            font=self
        )
        return groups

    def beginSelfGroupsNotificationObservation(self):
        groups = self.groups
        groups.addObserver(observer=self, methodName="_objectDirtyStateChange", notification="Groups.Changed")

    def endSelfGroupsNotificationObservation(self):
        if self._groups is None:
            return
        if self._groups.dispatcher is None:
            return
        self._groups.removeObserver(observer=self, notification="Groups.Changed")
        self._groups.endSelfNotificationObservation()

    def _get_groups(self):
        if self._groups is None:
            if self._path is None:
                self._groups = self.instantiateGroups()
                self.beginSelfGroupsNotificationObservation()
                self._stampGroupsDataState(None)
            else:
                self._loadKerningAndGroups()
        return self._groups

    groups = property(_get_groups, doc="The font's :class:`Groups` object.")

    # features

    def instantiateFeatures(self):
        features = self._featuresClass(
            font=self
        )
        return features

    def beginSelfFeaturesNotificationObservation(self):
        features = self.features
        features.addObserver(observer=self, methodName="_objectDirtyStateChange", notification="Features.Changed")

    def endSelfFeaturesNotificationObservation(self):
        if self._features is None:
            return
        if self._features.dispatcher is None:
            return
        self._features.removeObserver(observer=self, notification="Features.Changed")
        self._features.endSelfNotificationObservation()

    def _get_features(self):
        if self._features is None:
            self._features = self.instantiateFeatures()
            self.beginSelfFeaturesNotificationObservation()
            reader = None
            if self._path is not None:
                self._features.disableNotifications()
                reader = UFOReader(self._path, validate=False)
                t = reader.readFeatures()
                self._features.text = t
                self._features.dirty = False
                self._features.enableNotifications()
            self._stampFeaturesDataState(reader)
        return self._features

    features = property(_get_features, doc="The font's :class:`Features` object.")

    # lib

    def instantiateLib(self):
        lib = self._libClass(
            font=self
        )
        return lib

    def beginSelfLibNotificationObservation(self):
        self._lib.addObserver(observer=self, methodName="_objectDirtyStateChange", notification="Lib.Changed")

    def endSelfLibNotificationObservation(self):
        if self._lib is None:
            return
        if self._lib.dispatcher is None:
            return
        self._lib.removeObserver(observer=self, notification="Lib.Changed")
        self._lib.endSelfNotificationObservation()

    def _get_lib(self):
        if self._lib is None:
            self._lib = self.instantiateLib()
            self.beginSelfLibNotificationObservation()
            reader = None
            if self._path is not None:
                self._lib.disableNotifications()
                reader = UFOReader(self._path, validate=False)
                d = reader.readLib(validate=self._lib.ufoLibReadValidate)
                self._lib.update(d)
                self._lib.enableNotifications()
            self._stampLibDataState(reader)
        return self._lib

    lib = property(_get_lib, doc="The font's :class:`Lib` object.")

    # images

    def instantiateImageSet(self):
        imageSet = self._imageSetClass(
            font=self
        )
        return imageSet

    def beginSelfImageSetNotificationObservation(self):
        self._images.addObserver(observer=self, methodName="_objectDirtyStateChange", notification="ImageSet.Changed")

    def endSelfImageSetNotificationObservation(self):
        if self._images.dispatcher is None:
            return
        self._images.removeObserver(observer=self, notification="ImageSet.Changed")
        self._images.endSelfNotificationObservation()

    def _get_images(self):
        return self._images

    images = property(_get_images, doc="The font's :class:`ImageSet` object.")

    # data

    def instantiateDataSet(self):
        dataSet = self._dataSetClass(
            font=self
        )
        return dataSet

    def beginSelfDataSetNotificationObservation(self):
        self._data.addObserver(observer=self, methodName="_objectDirtyStateChange", notification="DataSet.Changed")

    def endSelfDataSetNotificationObservation(self):
        if self._data.dispatcher is None:
            return
        self._data.removeObserver(observer=self, notification="DataSet.Changed")
        self._data.endSelfNotificationObservation()

    def _get_data(self):
        return self._data

    data = property(_get_data, doc="The font's :class:`DataSet` object.")

    # unicode data (legacy)

    def _get_unicodeData(self):
        return self._glyphSet.unicodeData

    unicodeData = property(_get_unicodeData, doc="The font's :class:`UnicodeData` object.")

    # glyph order

    def _get_glyphOrder(self):
        return list(self.lib.get("public.glyphOrder", []))

    def _set_glyphOrder(self, value):
        oldValue = self.lib.get("public.glyphOrder")
        if oldValue == value:
            return
        if value is None or len(value) == 0:
            value = None
            if "public.glyphOrder" in self.lib:
                del self.lib["public.glyphOrder"]
        else:
            self.lib["public.glyphOrder"] = value
        self.postNotification("Font.GlyphOrderChanged", data=dict(oldValue=oldValue, newValue=value))

    glyphOrder = property(_get_glyphOrder, _set_glyphOrder, doc="The font's glyph order. When setting the value must be a list of glyph names. There is no requirement, nor guarantee, that the list will contain only names of glyphs in the font. Setting this posts *Font.GlyphOrderChanged* and *Font.Changed* notifications.")

    def updateGlyphOrder(self, addedGlyph=None, removedGlyph=None):
        """
        This method tries to keep the glyph order in sync.
        This should not be called externally. It may be overriden
        by subclasses as needed.
        """
        order = self.glyphOrder
        index = None
        if removedGlyph is not None:
            # if removed glyph is present, store its index.
            # we'll either replace it with added glyph or delete it
            try:
                index = order.index(removedGlyph)
            except ValueError:
                pass
            else:
                if removedGlyph == addedGlyph:
                    return
        if addedGlyph is not None:
            if addedGlyph not in order:
                if index is not None:
                    order[index] = addedGlyph
                    index = None
                else:
                    order.append(addedGlyph)
        if index is not None:
            del order[index]
        self.glyphOrder = order

    # -------
    # Methods
    # -------

    def getSaveProgressBarTickCount(self, formatVersion=None):
        """
        Get the number of ticks that will be used by a progress bar
        in the save method. Subclasses may override this method to
        implement custom saving behavior.
        """
        # if not format version is given, use the existing.
        # if that doesn't exist, go to 3.
        if formatVersion is None:
            formatVersion = self._ufoFormatVersion
        if formatVersion is None:
            formatVersion = 3
        count = 0
        count += 1 # info
        count += 1 # groups
        count += 1 # lib
        if formatVersion != self._ufoFormatVersion and formatVersion < 3:
            count += 1
        else:
            count += int(self.kerning.dirty)
        if formatVersion >= 2:
            count += int(self.features.dirty)
        if formatVersion >= 3:
            count += self.images.getSaveProgressBarTickCount(formatVersion)
            count += self.data.getSaveProgressBarTickCount(formatVersion)
        count += self.layers.getSaveProgressBarTickCount(formatVersion)
        return count

    def save(
        self,
        path=None,
        formatVersion=None,
        removeUnreferencedImages=False,
        progressBar=None,
        structure=None,
    ):
        """
        Save the font to **path**. If path is None, the path
        from the last save or when the font was first opened
        will be used.

        The UFO will be saved using the format found at ``ufoFormatVersion``.
        This value is either the format version from the exising UFO or
        the format version specified in a previous save. If neither of
        these is available, the UFO will be written as format version 3.
        If you wish to specifiy the format version for saving, pass
        the desired number as the **formatVersion** argument.

        Optionally, the UFO can be purged of unreferenced images
        during this operation. To do this, pass ``True`` as the
        value for the removeUnreferencedImages argument.

        'structure' can be either None, "zip" or "package". If it's None,
        the destination UFO will use the same structure as original, provided
        that is compatible with any previous UFO at the output path.
        If 'structure' is "zip" the UFO will be saved as compressed archive,
        else it is saved as a regular folder or "package".
        """
        isNewFont = self._path is None
        if path is None:
            if isNewFont:
                from defcon.errors import DefconError
                raise DefconError("Can't save new font without a 'path'")
            # saving in-place to the same original path
            path = self._path
            saveAs = False
        else:
            if not isinstance(path, basestring) and not hasattr(path, "__fspath__"):
                raise TypeError(
                    "invalid path: expected string or os.PathLike, found %s"
                    % type(path).__name__
                )
            if isNewFont:
                # saving a new font is always a 'saveAs' operation
                saveAs = True
            else:
                # 'saveAs' if source and destination path are different
                saveAs = not samepath(self._path, path)

        # validate 'structure' argument
        if structure is not None:
            try:
                structure = UFOFileStructure(structure)
            except ValueError:
                from defcon.errors import DefconError
                raise DefconError(
                    "'%s' is not a valid UFOFileStructure; choose between %s"
                    % (structure, tuple(e.value for e in UFOFileStructure))
                )
        elif self._ufoFileStructure is not None:
            # if structure is None, fall back to the same as when first loaded
            structure = self._ufoFileStructure
        else:
            # if both None, default to "package" structure
            structure = UFOFileStructure.PACKAGE

        # if destination is an existing path, ensure matches the desired structure
        isExistingOSPath = os.path.exists(path)
        if isExistingOSPath:
            try:
                with UFOReader(path, validate=True) as reader:
                    existingStructure = reader.fileStructure
            except UFOLibError:
                # destination is an existing file but not a valid UFO, we'll
                # silently overwrite it. Perhaps we should blow up...
                saveAs = True
            if not saveAs and structure and structure is not existingStructure:
                from defcon.errors import DefconError
                raise DefconError(
                    "Can't save font in-place with a different structure; "
                    "expected %s, got %s"
                    % (existingStructure.value, structure.value)
                )

        # sanity checks on layer data before doing anything destructive
        assert self.layers.defaultLayer is not None
        if self.layers.defaultLayer.name != "public.default":
            assert "public.default" not in self.layers.layerOrder
        ## work out the format version
        # if None is given, fallback to the one that
        # came in when the UFO was loaded
        if formatVersion is None and self._ufoFormatVersion is not None:
            formatVersion = self._ufoFormatVersion
        # otherwise fallback to 3
        elif formatVersion is None:
            formatVersion = 3
        # if down-converting in-place or "saving as" to a pre-existing path,
        # we first write to a temporary folder, then move to destination
        overwritePath = None
        if ((not saveAs and formatVersion != self._ufoFormatVersion) or
                (saveAs and isExistingOSPath)):
            saveAs = True
            overwritePath = path
            path = os.path.join(tempfile.mkdtemp(), "temp.ufo")
        try:
            # make a UFOWriter
            try:
                writer = UFOWriter(
                    path,
                    formatVersion=formatVersion,
                    validate=self.ufoLibWriteValidate,
                    structure=structure,
                )
            except UFOLibError:
                if overwritePath is None and isExistingOSPath:
                    logger.exception("Invalid ufo found '%s', the existing ufo "
                                     "will be removed. Save will be handled as "
                                     "save-as.", path)
                    saveAs = True
                    overwritePath = path
                    path = os.path.join(tempfile.mkdtemp(), "temp.ufo")
                    writer = UFOWriter(
                        path,
                        formatVersion=formatVersion,
                        validate=self.ufoLibWriteValidate,
                        structure=structure,
                    )
                else:
                    raise
            # if changing ufo format versions, flag all objects
            # as dirty so that they will be saved
            if self._ufoFormatVersion != formatVersion:
                self.info.dirty = True
                self.groups.dirty = True
                self.kerning.dirty = True
                self.lib.dirty = True
                if formatVersion > 1:
                    self.features.dirty = True
            # set the kerning group remap if necessary
            if formatVersion < 3 and self._kerningGroupConversionRenameMaps is not None:
                writer.setKerningGroupConversionRenameMaps(self._kerningGroupConversionRenameMaps)
            # save the objects
            self._saveInfo(writer=writer, saveAs=saveAs, progressBar=progressBar)
            self._saveGroups(writer=writer, saveAs=saveAs, progressBar=progressBar)
            # Note: the outgoing kerning data has not been validated.
            # Gremlins may be sneaking out through here.
            self._saveKerning(writer=writer, saveAs=saveAs, progressBar=progressBar)
            self._saveLib(writer=writer, saveAs=saveAs, progressBar=progressBar)
            if formatVersion >= 2:
                self._saveFeatures(writer=writer, saveAs=saveAs, progressBar=progressBar)
            if formatVersion >= 3:
                self.saveImages(writer=writer, removeUnreferencedImages=removeUnreferencedImages, saveAs=saveAs, progressBar=progressBar)
                self.saveData(writer=writer, saveAs=saveAs, progressBar=progressBar)
            self.layers.save(writer, saveAs=saveAs, progressBar=progressBar)
            # we must close the writer's filesystem to actually create the zip;
            # Note that calling writer.close() makes all the SubFS instances
            # derived from it unusable
            if writer.fileStructure is UFOFileStructure.ZIP:
                writer.close()
            writer.setModificationTime()
            if overwritePath is not None:
                if os.path.isfile(overwritePath):
                    os.remove(overwritePath)
                elif os.path.isdir(overwritePath):
                    shutil.rmtree(overwritePath)
                shutil.move(path, overwritePath)
        finally:
            # if down converting in place or overwriting, handle the temp
            if overwritePath is not None:
                shutil.rmtree(os.path.dirname(path))
                path = overwritePath
        # done
        self._path = path
        self._ufoFormatVersion = formatVersion
        self._ufoFileStructure = writer.fileStructure
        self.dirty = False

    def _saveInfo(self, writer, saveAs=False, progressBar=None):
        # info should always be saved
        if progressBar is not None:
            progressBar.update(text="Saving info...", increment=0)
        self.saveInfo(writer)
        self.info.dirty = False
        self._stampInfoDataState(writer)
        if progressBar is not None:
            progressBar.update()

    def saveInfo(self, writer):
        """
        Save info. This method should not be called externally.
        Subclasses may override this method to implement custom saving behavior.
        """
        writer.writeInfo(self.info, validate=self.info.ufoLibWriteValidate)

    def _saveGroups(self, writer, saveAs=False, progressBar=None):
        # groups should always be saved
        if progressBar is not None:
            progressBar.update(text="Saving groups...", increment=0)
        self.saveGroups(writer)
        self.groups.dirty = False
        self._stampGroupsDataState(writer)
        if progressBar is not None:
            progressBar.update()

    def saveGroups(self, writer):
        """
        Save groups. This method should not be called externally.
        Subclasses may override this method to implement custom saving behavior.
        """
        writer.writeGroups(self.groups, validate=self.groups.ufoLibWriteValidate)

    def _saveKerning(self, writer, saveAs=False, progressBar=None):
        if self.kerning.dirty or saveAs:
            if progressBar is not None:
                progressBar.update(text="Saving kerning...", increment=0)
            self.saveKerning(writer)
            self.kerning.dirty = False
            self._stampKerningDataState(writer)
        if progressBar is not None:
            progressBar.update()

    def saveKerning(self, writer):
        """
        Save kerning. This method should not be called externally.
        Subclasses may override this method to implement custom saving behavior.
        """
        writer.writeKerning(self.kerning, validate=self.kerning.ufoLibWriteValidate)

    def _saveFeatures(self, writer, saveAs=False, progressBar=None):
        if self.features.dirty or saveAs:
            if progressBar is not None:
                progressBar.update(text="Saving features...", increment=0)
            if self.features.text is not None:
                self.saveFeatures(writer)
            self.features.dirty = False
            self._stampFeaturesDataState(writer)
        if progressBar is not None:
            progressBar.update()

    def saveFeatures(self, writer):
        """
        Save features. This method should not be called externally.
        Subclasses may override this method to implement custom saving behavior.
        """
        writer.writeFeatures(self.features.text, validate=self.features.ufoLibWriteValidate)

    def _saveLib(self, writer, saveAs=False, progressBar=None):
        # lib should always be saved
        if progressBar is not None:
            progressBar.update(text="Saving lib...", increment=0)
        self.saveLib(writer)
        self.lib.dirty = False
        self._stampLibDataState(writer)
        if progressBar is not None:
            progressBar.update()

    def saveLib(self, writer, saveAs=False, progressBar=None):
        """
        Save lib. This method should not be called externally.
        Subclasses may override this method to implement custom saving behavior.
        """
        # if making format version 1, do some
        # temporary down conversion before
        # passing the lib to the writer
        libCopy = dict(self.lib)
        if writer.formatVersion == 1:
            self._convertToFormatVersion1RoboFabData(libCopy)
        writer.writeLib(libCopy, validate=self.lib.ufoLibWriteValidate)

    def saveImages(self, writer, removeUnreferencedImages=False, saveAs=False, progressBar=None):
        """
        Save images. This method should not be called externally.
        Subclasses may override this method to implement custom saving behavior.
        """
        if progressBar is not None:
            progressBar.update(text="Saving images...", increment=0)
        self.images.save(writer, removeUnreferencedImages=removeUnreferencedImages, saveAs=saveAs, progressBar=progressBar)
        if progressBar is not None:
            progressBar.update()

    def saveData(self, writer, saveAs=False, progressBar=None):
        """
        Save data. This method should not be called externally.
        Subclasses may override this method to implement custom saving behavior.
        """
        if progressBar is not None:
            progressBar.update(text="Saving data...", increment=0)
        self.data.save(writer, saveAs=saveAs, progressBar=progressBar)
        if progressBar is not None:
            progressBar.update()

    # -----------
    # Identifiers
    # -----------

    def _get_identifiers(self):
        return self._identifiers

    identifiers = property(_get_identifiers, doc="Set of identifiers for the info. This is primarily for internal use.")

    # ----------
    # Guidelines
    # ----------

    # Note: Guidelines are stored in fontinfo.plist in UFOs,
    # thus any change to guidelines needs to set the info
    # object as dirty.

    def _get_guidelines(self):
        if self._info is None:
            self.info
        return list(self._guidelines)

    def _set_guidelines(self, value):
        self.clearGuidelines()
        self.holdNotifications(note="Requested by Font._set_guidelines.")
        for guideline in value:
            self.appendGuideline(guideline)
        self.releaseHeldNotifications()

    guidelines = property(_get_guidelines, _set_guidelines, doc="An ordered list of :class:`Guideline` objects stored in the font. Setting this will post a *Font.Changed* notification along with any notifications posted by the :py:meth:`Font.appendGuideline` and :py:meth:`Font.clearGuidelines` methods.")

    def instantiateGuideline(self, guidelineDict=None):
        guideline = self._guidelineClass(guidelineDict=guidelineDict)
        return guideline

    def beginSelfGuidelineNotificationObservation(self, guideline):
        if guideline.dispatcher is None:
            return
        guideline.addObserver(observer=self, methodName="_guidelineChanged", notification="Guideline.Changed")

    def endSelfGuidelineNotificationObservation(self, guideline):
        if guideline.dispatcher is None:
            return
        guideline.removeObserver(observer=self, notification="Guideline.Changed")
        guideline.endSelfNotificationObservation()

    def appendGuideline(self, guideline):
        """
        Append **guideline** to the font. The guideline must be a defcon
        :class:`Guideline` object or a subclass of that object. An error
        will be raised if the guideline's identifier conflicts with any of
        the identifiers within the font.

        This will post *Font.GuidelinesChanged* and *Font.Changed* notifications.
        """
        self.insertGuideline(len(self._guidelines), guideline)

    def insertGuideline(self, index, guideline):
        """
        Insert **guideline** into the font at index. The guideline
        must be a defcon :class:`Guideline` object or a subclass
        of that object. An error will be raised if the guideline's
        identifier conflicts with any of the identifiers within
        the font.

        This will post *Font.GuidelinesChanged* and *Font.Changed* notifications.
        """
        if not isinstance(guideline, self._guidelineClass):
            guideline = self.instantiateGuideline(guidelineDict=guideline)
        assert guideline.font in (self, None), "This guideline belongs to another font."
        if guideline.font is None:
            assert guideline.glyph is None, "This guideline belongs to a glyph."
        if guideline.font is None:
            if guideline.identifier is not None:
                identifiers = self._identifiers
                assert guideline.identifier not in identifiers
                if guideline.identifier is not None:
                    identifiers.add(guideline.identifier)
            guideline.font = self
            guideline.beginSelfNotificationObservation()
        self.beginSelfGuidelineNotificationObservation(guideline)
        self._guidelines.insert(index, guideline)
        self.postNotification("Font.GuidelinesChanged")
        self.info.dirty = True
        self.dirty = True

    def removeGuideline(self, guideline):
        """
        Remove **guideline** from the font.

        This will post *Font.GuidelineWillBeDeleted*, *Font.GuidelinesChanged* and *Font.Changed* notifications.
        """
        self.postNotification(notification="Font.GuidelineWillBeDeleted", data=dict(object=guideline))
        if guideline.identifier is not None:
            self._identifiers.remove(guideline.identifier)
        self._guidelines.remove(guideline)
        self.endSelfGuidelineNotificationObservation(guideline)
        self.postNotification("Font.GuidelinesChanged")
        self.info.dirty = True
        self.dirty = True

    def guidelineIndex(self, guideline):
        """
        Get the index for **guideline**.
        """
        return self._guidelines.index(guideline)

    def clearGuidelines(self):
        """
        Clear all guidelines from the font.

        This posts a *Font.Changed* notification.
        """
        self.holdNotifications(note="Requested by Font.clearGuidelines.")
        for guideline in reversed(self._guidelines):
            self.removeGuideline(guideline)
        self.releaseHeldNotifications()

    # ------------------------
    # Notification Observation
    # ------------------------

    def endSelfNotificationObservation(self):
        if self.dispatcher is None:
            return
        self.endSelfLayersNotificationObservation()
        self.endSelfLayerSetNotificationObservation()
        self.endSelfInfoSetNotificationObservation()
        self.endSelfKerningNotificationObservation()
        self.endSelfGroupsNotificationObservation()
        self.endSelfLibNotificationObservation()
        self.endSelfFeaturesNotificationObservation()
        self.endSelfImageSetNotificationObservation()
        self.endSelfDataSetNotificationObservation()
        for guideline in self._guidelines:
            self.endSelfGuidelineNotificationObservation(guideline)
        super(Font, self).endSelfNotificationObservation()

    def _objectDirtyStateChange(self, notification):
        if notification.object.dirty:
            self.dirty = True

    def beginSelfLayersNotificationObservation(self):
        for layer in self._layers:
            self._beginSelfLayerNotificationObservation(layer)

    def endSelfLayersNotificationObservation(self):
        for layer in self._layers:
            self._endSelfLayerNotificationObservation(layer)

    def _layerAddedNotificationCallback(self, notification):
        name = notification.data["name"]
        layer = self.layers[name]
        self._beginSelfLayerNotificationObservation(layer)

    def _beginSelfLayerNotificationObservation(self, layer):
        layer.addObserver(self, "_glyphAddedNotificationCallback", "Layer.GlyphAdded")
        layer.addObserver(self, "_glyphDeletedNotificationCallback", "Layer.GlyphDeleted")
        layer.addObserver(self, "_glyphRenamedNotificationCallback", "Layer.GlyphNameChanged")

    def _layerWillBeDeletedNotificationCallback(self, notification):
        name = notification.data["name"]
        layer = self.layers[name]
        self._endSelfLayerNotificationObservation(layer)

    def _endSelfLayerNotificationObservation(self, layer):
        layer.removeObserver(observer=self, notification="Layer.GlyphAdded")
        layer.removeObserver(observer=self, notification="Layer.GlyphDeleted")
        layer.removeObserver(observer=self, notification="Layer.GlyphNameChanged")

    def _glyphAddedNotificationCallback(self, notification):
        name = notification.data["name"]
        self.updateGlyphOrder(addedGlyph=name)

    def _glyphDeletedNotificationCallback(self, notification):
        name = notification.data["name"]
        stillExists = False
        for layer in self.layers:
            if name in layer:
                stillExists = True
                break
        if not stillExists:
            self.updateGlyphOrder(removedGlyph=name)

    def _glyphRenamedNotificationCallback(self, notification):
        oldName = notification.data["oldValue"]
        newName = notification.data["newValue"]
        oldStillExists = False
        for layer in self.layers:
            if oldName in layer:
                oldStillExists = True
                break
        removedGlyph = oldName if not oldStillExists else None
        self.updateGlyphOrder(addedGlyph=newName, removedGlyph=removedGlyph)

    def _guidelineChanged(self, notification):
        self.postNotification("Font.GuidelinesChanged")
        self.dirty = True

    # ---------------------
    # External Edit Support
    # ---------------------

    # data stamping

    def _stampFontDataState(self, obj, fileName, reader=None):
        # font is not on disk
        if self.path is None and reader is None:
            return
        # data has not been loaded
        if obj is None:
            return
        # make a reader if necessary
        if reader is None:
            reader = UFOReader(self.path, validate=False)
        # get the mod time from the reader
        modTime = reader.getFileModificationTime(fileName)
        # file is not in the UFO
        if modTime is None:
            data = None
            modTime = -1
        # get the data
        else:
            data = reader.readBytesFromPath(fileName)
        # store the data
        obj._dataOnDisk = data
        obj._dataOnDiskTimeStamp = modTime

    def _stampInfoDataState(self, reader=None):
        self._stampFontDataState(self._info, "fontinfo.plist", reader=reader)

    def _stampKerningDataState(self, reader=None):
        self._stampFontDataState(self._kerning, "kerning.plist", reader=reader)

    def _stampGroupsDataState(self, reader=None):
        self._stampFontDataState(self._groups, "groups.plist", reader=reader)

    def _stampFeaturesDataState(self, reader=None):
        self._stampFontDataState(self._features, "features.fea", reader=reader)

    def _stampLibDataState(self, reader=None):
        self._stampFontDataState(self._lib, "lib.plist", reader=reader)

    # data comparison

    def testForExternalChanges(self):
        """
        Test the UFO for changes that occured outside of this font's
        tree of objects. This returns a dictionary describing the changes::

            {
                "info"     : bool, # True if changed, False if not changed
                "kerning"  : bool, # True if changed, False if not changed
                "groups"   : bool, # True if changed, False if not changed
                "features" : bool, # True if changed, False if not changed
                "lib"      : bool, # True if changed, False if not changed
                "layers"   : {
                    "defaultLayer" : bool, # True if changed, False if not changed
                    "order"        : bool, # True if changed, False if not changed
                    "added"        : ["layer name 1", "layer name 2"],
                    "deleted"      : ["layer name 1", "layer name 2"],
                    "modified"     : {
                        "info"     : bool, # True if changed, False if not changed
                        "modified" : ["glyph name 1", "glyph name 2"],
                        "added"    : ["glyph name 1", "glyph name 2"],
                        "deleted"  : ["glyph name 1", "glyph name 2"]
                    }
                },
                "images"   : {
                    "modified" : ["image name 1", "image name 2"],
                    "added"    : ["image name 1", "image name 2"],
                    "deleted"  : ["image name 1", "image name 2"],
                },
                "data"     : {
                    "modified" : ["file name 1", "file name 2"],
                    "added"    : ["file name 1", "file name 2"],
                    "deleted"  : ["file name 1", "file name 2"],
                }
            }

        It is important to keep in mind that the user could have created
        conflicting data outside of the font's tree of objects. For example,
        say the user has set ``font.info.unitsPerEm = 1000`` inside of the
        font's :class:`Info` object and the user has not saved this change.
        In the the font's fontinfo.plist file, the user sets the unitsPerEm value
        to 2000. Which value is current? Which value is right? defcon leaves
        this decision up to you.
        """
        assert self.path is not None
        reader = UFOReader(self.path, validate=self.ufoLibReadValidate)
        infoChanged = self._testInfoForExternalModifications(reader)
        kerningChanged = self._testKerningForExternalModifications(reader)
        groupsChanged = self._testGroupsForExternalModifications(reader)
        featuresChanged = self._testFeaturesForExternalModifications(reader)
        libChanged = self._testLibForExternalModifications(reader)
        layerChanges = self.layers.testForExternalChanges(reader)
        modifiedImages = addedImages = deletedImages = []
        if self._images is not None:
            modifiedImages, addedImages, deletedImages = self._images.testForExternalChanges(reader)
        modifiedData = addedData = deletedData = []
        if self._data is not None:
            modifiedData, addedData, deletedData = self._data.testForExternalChanges(reader)
        # deprecated stuff
        defaultLayerName = self.layers.defaultLayer.name
        modifiedGlyphs = layerChanges["modified"].get(defaultLayerName, {}).get("modified")
        addedGlyphs = layerChanges["modified"].get(defaultLayerName, {}).get("added")
        deletedGlyphs = layerChanges["modified"].get(defaultLayerName, {}).get("deleted")
        return dict(
            info=infoChanged,
            kerning=kerningChanged,
            groups=groupsChanged,
            features=featuresChanged,
            lib=libChanged,
            layers=layerChanges,
            images=dict(
                modified=modifiedImages,
                added=addedImages,
                deleted=deletedImages
            ),
            data=dict(
                modifiedData=modifiedData,
                addedData=addedData,
                deletedData=deletedData
            ),
            # deprecated
            modifiedGlyphs=modifiedGlyphs,
            addedGlyphs=addedGlyphs,
            deletedGlyphs=deletedGlyphs
        )

    def _testFontDataForExternalModifications(self, obj, fileName, reader=None):
        # font is not on disk
        if self.path is None:
            return False
        # data has not been loaded
        if obj is None:
            return
        # make a reader if necessary
        if reader is None:
            reader = UFOReader(self.path, validate=False)
        # get the mod time from the reader
        modTime = reader.getFileModificationTime(fileName)
        # file is not in the UFO
        if modTime is None:
            if obj._dataOnDisk:
                return True
            return False
        # time stamp mismatch
        if modTime != obj._dataOnDiskTimeStamp:
            data = reader.readBytesFromPath(fileName)
            if data != obj._dataOnDisk:
                return True
        # fallback
        return False

    def _testInfoForExternalModifications(self, reader=None):
        return self._testFontDataForExternalModifications(self._info, "fontinfo.plist", reader=reader)

    def _testKerningForExternalModifications(self, reader=None):
        return self._testFontDataForExternalModifications(self._kerning, "kerning.plist", reader=reader)

    def _testGroupsForExternalModifications(self, reader=None):
        return self._testFontDataForExternalModifications(self._groups, "groups.plist", reader=reader)

    def _testFeaturesForExternalModifications(self, reader=None):
        return self._testFontDataForExternalModifications(self._features, "features.fea", reader=reader)

    def _testLibForExternalModifications(self, reader=None):
        return self._testFontDataForExternalModifications(self._lib, "lib.plist", reader=reader)

    # data reloading

    def reloadInfo(self):
        """
        Reload the data in the :class:`Info` object from the
        fontinfo.plist file in the UFO.
        """
        from fontTools.ufoLib import deprecatedFontInfoAttributesVersion2
        if self._info is None:
            obj = self.info
        else:
            reader = UFOReader(self.path, validate=False)
            newInfo = Info()
            reader.readInfo(newInfo, validate=self._info.ufoLibReadValidate)
            oldInfo = self._info
            for attr in dir(newInfo):
                if attr in deprecatedFontInfoAttributesVersion2:
                    continue
                if attr.startswith("_"):
                    continue
                if attr == "dirty":
                    continue
                if attr == "dispatcher":
                    continue
                if attr == "font":
                    continue
                if not hasattr(oldInfo, attr):
                    continue
                newValue = getattr(newInfo, attr)
                oldValue = getattr(oldInfo, attr)
                if hasattr(newValue, "im_func"):
                    continue
                if oldValue == newValue:
                    continue
                setattr(oldInfo, attr, newValue)
            self._stampInfoDataState(reader)

    def reloadKerning(self):
        """
        Reload the data in the :class:`Kerning` object from the
        kerning.plist file in the UFO.

        This validates the kerning against the groups loaded into the
        font. If groups are being reloaded in the same pass, the groups
        should always be reloaded before reloading the kerning.
        """
        if self._kerning is None:
            obj = self.kerning
        else:
            reader = UFOReader(self._path, validate=False)
            kerning = reader.readKerning(validate=self._kerning.ufoLibReadValidate)
            # Note: the incoming kerning data has not been validated.
            # Gremlins may be sneaking in through here.
            self._kerning.clear()
            self._kerning.update(kerning)
            self._stampKerningDataState(reader)

    def reloadGroups(self):
        """
        Reload the data in the :class:`Groups` object from the
        groups.plist file in the UFO.
        """
        if self._groups is None:
            obj = self.groups
        else:
            reader = UFOReader(self._path, validate=False)
            d = reader.readGroups(validate=self._groups.ufoLibReadValidate)
            self._groups.clear()
            self._groups.update(d)
            self._stampGroupsDataState(reader)

    def reloadFeatures(self):
        """
        Reload the data in the :class:`Features` object from the
        features.fea file in the UFO.
        """
        if self._features is None:
            obj = self.features
        else:
            reader = UFOReader(self._path, validate=False)
            text = reader.readFeatures()
            self._features.text = text
            self._stampFeaturesDataState(reader)

    def reloadLib(self):
        """
        Reload the data in the :class:`Lib` object from the
        lib.plist file in the UFO.
        """
        if self._lib is None:
            obj = self.lib
        else:
            reader = UFOReader(self._path, validate=False)
            d = reader.readLib(validate=self._lib.ufoLibReadValidate)
            self._lib.clear()
            self._lib.update(d)
            self._stampLibDataState(reader)

    def reloadImages(self, fileNames):
        """
        Reload the images listed in **fileNames** from the
        appropriate files within the UFO. When all of the
        loading is complete, a *Font.ReloadedImages* notification
        will be posted.
        """
        self.images.reloadImages(fileNames)
        self.postNotification(notification="Font.ReloadedImages")

    def reloadData(self, fileNames):
        """
        Reload the data files listed in **fileNames** from the
        appropriate files within the UFO. When all of the
        loading is complete, a *Font.ReloadedData* notification
        will be posted.
        """
        self.data.reloadData(fileNames)
        self.postNotification(notification="Font.ReloadedData")

    def reloadGlyphs(self, glyphNames):
        """
        Deprecated! Use reloadLayers!

        Reload the glyphs listed in **glyphNames** from the
        appropriate files within the UFO. When all of the
        loading is complete, a *Font.ReloadedGlyphs* notification
        will be posted.
        """
        defaultLayerName = self.layers.defaultLayer.name
        layerData = dict(
            layers={
                defaultLayerName : dict(glyphNames=glyphNames)
            }
        )
        self.reloadLayers(layerData)

    def reloadLayers(self, layerData):
        """
        Reload the data in the layers specfied in **layerData**.
        When all of the loading is complete, *Font.ReloadedLayers*
        and *Font.ReloadedGlyphs* notifications will be posted.
        The **layerData** must be a dictionary following this format::

            {
                "order"   : bool, # True if you want the order releaded
                "default" : bool, # True if you want the default layer reset
                "layers"  : {
                    "layer name" : {
                        "glyphNames" : ["glyph name 1", "glyph name 2"], # list of glyph names you want to reload
                        "info"       : bool, # True if you want the layer info reloaded
                    }
                }
            }
        """
        self.layers.reloadLayers(layerData)
        self.postNotification(notification="Font.ReloadedLayers")
        self.postNotification(notification="Font.ReloadedGlyphs")


    # -----------------------------
    # UFO Format Version Conversion
    # -----------------------------

    def _convertFromFormatVersion1RoboFabData(self):
        # migrate features from the lib
        features = []
        classes = self.lib.get("org.robofab.opentype.classes")
        if classes is not None:
            del self.lib["org.robofab.opentype.classes"]
            features.append(classes)
        splitFeatures = self.lib.get("org.robofab.opentype.features")
        if splitFeatures is not None:
            order = self.lib.get("org.robofab.opentype.featureorder")
            if order is None:
                order = sorted(splitFeatures.keys())
            else:
                del self.lib["org.robofab.opentype.featureorder"]
            del self.lib["org.robofab.opentype.features"]
            for tag in order:
                oneFeature = splitFeatures.get(tag)
                if oneFeature is not None:
                    features.append(oneFeature)
        self.features.text = "\n".join(features)
        # migrate hint data from the lib
        hintData = self.lib.get("org.robofab.postScriptHintData")
        if hintData is not None:
            del self.lib["org.robofab.postScriptHintData"]
            # settings
            blueFuzz = hintData.get("blueFuzz")
            if blueFuzz is not None:
                self.info.postscriptBlueFuzz = blueFuzz
            blueScale = hintData.get("blueScale")
            if blueScale is not None:
                self.info.postscriptBlueScale = blueScale
            blueShift = hintData.get("blueShift")
            if blueShift is not None:
                self.info.postscriptBlueShift = blueShift
            forceBold = hintData.get("forceBold")
            if forceBold is not None:
                self.info.postscriptForceBold = forceBold
            # stems
            vStems = hintData.get("vStems")
            if vStems is not None:
                self.info.postscriptStemSnapV = vStems
            hStems = hintData.get("hStems")
            if hStems is not None:
                self.info.postscriptStemSnapH = hStems
            # blues
            bluePairs = [
                ("postscriptBlueValues", "blueValues"),
                ("postscriptOtherBlues", "otherBlues"),
                ("postscriptFamilyBlues", "familyBlues"),
                ("postscriptFamilyOtherBlues", "familyOtherBlues"),
            ]
            for infoAttr, libKey in bluePairs:
                libValue = hintData.get(libKey)
                if libValue is not None:
                    value = []
                    for i, j in libValue:
                        value.append(i)
                        value.append(j)
                    setattr(self.info, infoAttr, value)

    featureRE = re.compile(
        "^"            # start of line
        "\s*"          #
        "feature"      # feature
        "\s+"          #
        "(\w{4})"      # four alphanumeric characters
        "\s*"          #
        "\{"           # {
        , re.MULTILINE # run in multiline to preserve line seps
    )

    def _splitFeaturesForConversion(self, text):
        classes = ""
        features = []
        while text:
            m = self.featureRE.search(text)
            if m is None:
                classes = text
                text = ""
            else:
                start, end = m.span()
                # if start is not zero, this is the first match
                # and all previous lines are part of the "classes"
                if start > 0:
                    assert not classes
                    classes = text[:start]
                # extract the current feature
                featureName = m.group(1)
                featureText = text[start:end]
                text = text[end:]
                # grab all text before the next feature definition
                # and add it to the current definition
                if text:
                    m = self.featureRE.search(text)
                    if m is not None:
                        start, end = m.span()
                        featureText += text[:start]
                        text = text[start:]
                    else:
                        featureText += text
                        text = ""
                # store the feature
                features.append((featureName, featureText))
        return classes, features

    def _convertToFormatVersion1RoboFabData(self, libCopy):
        # features
        features = self.features.text
        classes, features = self._splitFeaturesForConversion(features)
        if classes:
            libCopy["org.robofab.opentype.classes"] = classes.strip() + "\n"
        if features:
            featureDict = {}
            for featureName, featureText in features:
                featureDict[featureName] = featureText.strip() + "\n"
            libCopy["org.robofab.opentype.features"] = featureDict
            libCopy["org.robofab.opentype.featureorder"] = [featureName for featureName, featureText in features]
        # hint data
        hintData = dict(
            blueFuzz=self.info.postscriptBlueFuzz,
            blueScale=self.info.postscriptBlueScale,
            blueShift=self.info.postscriptBlueShift,
            forceBold=self.info.postscriptForceBold,
            vStems=self.info.postscriptStemSnapV,
            hStems=self.info.postscriptStemSnapH
        )
        bluePairs = [
            ("postscriptBlueValues", "blueValues"),
            ("postscriptOtherBlues", "otherBlues"),
            ("postscriptFamilyBlues", "familyBlues"),
            ("postscriptFamilyOtherBlues", "familyOtherBlues"),
        ]
        for infoAttr, libKey in bluePairs:
            values = getattr(self.info, infoAttr)
            if values is not None:
                finalValues = []
                for value in values:
                    if not finalValues or len(finalValues[-1]) == 2:
                        finalValues.append([])
                    finalValues[-1].append(value)
                hintData[libKey] = finalValues
        for key, value in list(hintData.items()):
            if value is None:
                del hintData[key]
        libCopy["org.robofab.postScriptHintData"] = hintData

    # -----------------------------
    # Serialization/Deserialization
    # -----------------------------

    def getDataForSerialization(self, **kwargs):
        simple_get = partial(getattr, self)
        serialize = lambda item: item.getDataForSerialization()
        serialized_get = lambda key: serialize(simple_get(key))
        serialized_list_get = lambda key: [serialize(item) for item in simple_get(key)]

        getters = (
            ('_ufoFormatVersion', simple_get),
            ('_kerningGroupConversionRenameMaps', simple_get),
            # _path ? => setting path may change the behavior when deserializing a lot!
            # also path should be set by the caller, e.g. when saving the font
            # otherwise, path should be deserialized as the very last item,
            # because otherwise the font object will try to load a lot data
            # from disk, when deserializing.
            ('data', serialized_get),
            ('features', serialized_get),
            ('groups', serialized_get),
            ('images', serialized_get),
            ('info',  serialized_get),
            ('kerning', serialized_get),
            ('layers',  serialized_get),
            ('lib', serialized_get),
            ('guidelines', serialized_list_get)
        )

        return self._serialize(getters, **kwargs)

    def setDataFromSerialization(self, data):
        set_attr = partial(setattr, self) # key, data

        def single_update(key, data):
            item = getattr(self, key)
            item.setDataFromSerialization(data)

        def init_set_layers(key, data):
            self.endSelfLayersNotificationObservation()
            self.endSelfLayerSetNotificationObservation()
            self._layers = self.instantiateLayerSet()
            self.beginSelfLayerSetNotificationObservation()
            self.beginSelfLayersNotificationObservation()
            self._layers.setDataFromSerialization(data)

        def init_set_data(key, data):
            self.endSelfDataSetNotificationObservation()
            self._data = self.instantiateDataSet()
            self.beginSelfDataSetNotificationObservation()
            self._data.setDataFromSerialization(data)

        def init_set_images(key, data):
            self.endSelfImageSetNotificationObservation()
            self._images = self.instantiateImageSet()
            self.beginSelfImageSetNotificationObservation()
            self._images.setDataFromSerialization(data)

        def set_guidelines(key, data):
            guides = []
            for d in data:
                guide = self.instantiateGuideline()
                guide.setDataFromSerialization(d)
                guides.append(guide)
            set_attr(key, guides)

        # TODO: fill the rest of setDataFromSerialization/getDataForSerialization pairs
        setters = (
            ('_ufoFormatVersion', set_attr),
            ('_kerningGroupConversionRenameMaps', set_attr),
            ('data', init_set_data),
            ('features', single_update),
            ('groups', single_update),
            ('images', init_set_images),
            ('info', single_update),
            ('kerning', single_update),
            ('layers', init_set_layers),
            ('lib', single_update),
            ('guidelines', set_guidelines)
        )

        for key, setter in setters:
            if key not in data:
                continue
            setter(key, data[key])


def samepath(p1, p2):
    """Return True if p1 and p2 refer to the same path. That is, when both
    are strings or os.PathLike objects, compare their absolute, case
    insensitive representation.
    """
    return os.path.normcase(os.path.realpath(os.path.abspath(p1))) == (
        os.path.normcase(os.path.realpath(os.path.abspath(p2)))
    )


if __name__ == "__main__":
    import doctest
    doctest.testmod()
