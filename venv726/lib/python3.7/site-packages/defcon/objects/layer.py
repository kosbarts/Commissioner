from __future__ import absolute_import
import weakref
from fontTools.misc.arrayTools import unionRect
from fontTools.misc.py23 import tounicode
from defcon.objects.base import BaseObject
from defcon.objects.glyph import Glyph
from defcon.objects.lib import Lib
from defcon.objects.uniData import UnicodeData
from defcon.objects.color import Color
from functools import partial


class Layer(BaseObject):

    """
    This object represents a layer in a :class:`LayerSet`.

    **This object posts the following notifications:**

    +----------------------------+
    |Name                        |
    +============================+
    |Layer.Changed               |
    +----------------------------+
    |Layer.GlyphsChanged         |
    +----------------------------+
    |Layer.GlyphChanged          |
    +----------------------------+
    |Layer.GlyphWillBeAdded      |
    +----------------------------+
    |Layer.GlyphAdded            |
    +----------------------------+
    |Layer.GlyphWillBeDeleted    |
    +----------------------------+
    |Layer.GlyphDeleted          |
    +----------------------------+
    |Layer.GlyphNameChanged      |
    +----------------------------+
    |Layer.GlyphUnicodesChanged  |
    +----------------------------+
    |Layer.NameChanged           |
    +----------------------------+
    |Layer.ColorChanged          |
    +----------------------------+

    The Layer object has some dict like behavior. For example, to get a glyph::

        glyph = layer["aGlyphName"]

    To iterate over all glyphs::

        for glyph in layer:

    To get the number of glyphs::

        glyphCount = len(layer)

    To find out if a font contains a particular glyph::

        exists = "aGlyphName" in layer

    To remove a glyph::

        del layer["aGlyphName"]
    """

    changeNotificationName = "Layer.Changed"
    representationFactories = {}

    def __init__(self, layerSet=None, glyphSet=None, libClass=None, unicodeDataClass=None,
                guidelineClass=None, glyphClass=None,
                glyphContourClass=None, glyphPointClass=None, glyphComponentClass=None, glyphAnchorClass=None, glyphImageClass=None):

        if layerSet is not None:
            layerSet = weakref.ref(layerSet)
        self._layerSet = layerSet
        super(Layer, self).__init__()
        self.beginSelfNotificationObservation()

        self._name = None

        if glyphClass is None:
            glyphClass = Glyph
        if libClass is None:
            libClass = Lib
        if unicodeDataClass is None:
            unicodeDataClass = UnicodeData
        self._glyphClass = glyphClass
        self._glyphContourClass = glyphContourClass
        self._glyphPointClass = glyphPointClass
        self._glyphComponentClass = glyphComponentClass
        self._glyphAnchorClass = glyphAnchorClass
        self._glyphImageClass = glyphImageClass
        self._libClass = libClass
        self._guidelineClass = guidelineClass
        self._unicodeDataClass = unicodeDataClass

        self._color = None
        self._lib = None
        self._unicodeData = None

        self._directory = None

        self._glyphs = {}
        self._glyphSet = glyphSet
        self._scheduledForDeletion = {}
        self._keys = set()

        self._dirty = False

        if glyphSet is not None:
            self._keys = set(self._glyphSet.keys())

    def __del__(self):
        super(Layer, self).__del__()
        self._glyphs = None
        self._lib = None
        self._unicodeData = None

    # --------------
    # Parent Objects
    # --------------

    def getParent(self):
        return self.layerSet

    def _get_font(self):
        layerSet = self.layerSet
        if layerSet is None:
            return None
        return layerSet.font

    font = property(_get_font, doc="The :class:`Font` that this layer belongs to.")

    def _get_layerSet(self):
        if self._layerSet is None:
            return None
        return self._layerSet()

    layerSet = property(_get_layerSet, doc="The :class:`LayerSet` that this layer belongs to.")

    # --------------
    # Glyph Creation
    # --------------

    def instantiateGlyphObject(self):
        glyph = self._glyphClass(
            layer=self,
            contourClass=self._glyphContourClass,
            pointClass=self._glyphPointClass,
            componentClass=self._glyphComponentClass,
            anchorClass=self._glyphAnchorClass,
            guidelineClass=self._guidelineClass,
            libClass=self._libClass,
            imageClass=self._glyphImageClass
        )
        return glyph

    def beginSelfGlyphNotificationObservation(self, glyph):
        glyph.addObserver(observer=self, methodName="_glyphDirtyStateChange", notification="Glyph.Changed")
        glyph.addObserver(observer=self, methodName="_glyphNameChange", notification="Glyph.NameChanged")
        glyph.addObserver(observer=self, methodName="_glyphUnicodesChange", notification="Glyph.UnicodesChanged")

    def endSelfGlyphNotificationObservation(self, glyph):
        if glyph.dispatcher is None:
            return
        glyph.removeObserver(observer=self, notification="Glyph.Changed")
        glyph.removeObserver(observer=self, notification="Glyph.NameChanged")
        glyph.removeObserver(observer=self, notification="Glyph.UnicodesChanged")
        glyph.endSelfNotificationObservation()

    def loadGlyph(self, name):
        """
        Load a glyph from the glyph set. This should not be called
        externally, but subclasses may override it for custom behavior.
        """
        if self._glyphSet is None or name not in self._glyphSet or name in self._scheduledForDeletion:
            raise KeyError("%s not in layer" % name)
        glyph = self.instantiateGlyphObject()
        glyph.disableNotifications()
        glyph._isLoading = True
        glyph.name = name
        self._stampGlyphDataState(glyph)
        self._insertGlyph(glyph)
        pointPen = glyph.getPointPen()
        self._glyphSet.readGlyph(glyphName=name, glyphObject=glyph, pointPen=pointPen)
        glyph.dirty = False
        glyph._isLoading = False
        glyph.enableNotifications()
        return glyph

    def newGlyph(self, name):
        """
        Create a new glyph with **name**. If a glyph with that
        name already exists, the existing glyph will be replaced
        with the new glyph.

        This posts *Layer.GlyphWillBeAdded*, *Layer.GlyphAdded*
        and *Layer.Changed* notifications.
        """
        self.postNotification("Layer.GlyphWillBeAdded", data=(dict(name=name)))
        if name in self and self._unicodeData is not None:
            self._unicodeData.removeGlyphData(name, self[name].unicodes)
        glyph = self.instantiateGlyphObject()
        glyph.disableNotifications()
        glyph.name = name
        self._insertGlyph(glyph)
        glyph.enableNotifications()
        self.postNotification("Layer.GlyphAdded", data=(dict(name=name)))
        self.dirty = True
        return glyph

    def insertGlyph(self, glyph, name=None):
        """
        Insert **glyph** into the layer. Optionally, the glyph
        can be renamed at the same time by providing **name**.
        If a glyph with the glyph name, or the name provided
        as **name**, already exists, the existing glyph will
        be replaced with the new glyph.

        This posts *Layer.GlyphWillBeAdded*, *Layer.GlyphAdded*
        and *Layer.Changed* notifications.
        """
        # DO NOT ACTUALLY INSERT THE GLYPH!
        # it is crucially important that the data be reconstructed
        # in its entirety so that the parent data is properly set
        # in all of the various objects.
        # FIXME: Please Explain!!
        source = glyph
        if name is None:
            name = source.name
        self.postNotification("Layer.GlyphWillBeAdded", data=(dict(name=name)))
        self.holdNotifications(note="Requested by Layer.insertGlyph.")
        dest = self.newGlyph(name)
        dest.copyDataFromGlyph(glyph)
        self.releaseHeldNotifications()
        return dest

    def _insertGlyph(self, glyph, beginObservations=True):
        name = glyph.name
        self._glyphs[name] = glyph
        if name in self._scheduledForDeletion:
            del self._scheduledForDeletion[name]
        self._keys.add(name)
        if beginObservations:
            self.beginSelfGlyphNotificationObservation(glyph)
        if glyph.unicodes and self._unicodeData is not None:
            self._unicodeData.addGlyphData(name, glyph.unicodes)

    # -------------
    # Dict Behavior
    # -------------

    def __iter__(self):
        # this is a value iterator, unlike dict()
        for name in self.keys():
            yield self[name]

    def __getitem__(self, name):
        if name not in self._glyphs:
            self.loadGlyph(name)
        return self._glyphs[name]

    def __delitem__(self, name):
        if name not in self:
            raise KeyError("%s not in layer" % name)
        self.postNotification("Layer.GlyphWillBeDeleted", data=dict(name=name))
        self._deleteGlyph(name)
        self.postNotification("Layer.GlyphDeleted", data=dict(name=name))
        self.dirty = True

    def _deleteGlyph(self, name, endObservations=True):
        if self._unicodeData is not None:
            self._unicodeData.removeGlyphData(name, self[name].unicodes)
        dataOnDiskTimeStamp = None
        dataOnDisk = None
        if name in self._glyphs:
            glyph = self._glyphs.pop(name)
            if endObservations:
                self.endSelfGlyphNotificationObservation(glyph)
            dataOnDiskTimeStamp = glyph._dataOnDiskTimeStamp
            dataOnDisk = glyph._dataOnDisk
        if name in self._keys:
            self._keys.remove(name)
        if self._glyphSet is not None and name in self._glyphSet:
            self._scheduledForDeletion[name] = dict(dataOnDiskTimeStamp=dataOnDiskTimeStamp, dataOnDisk=dataOnDisk)

    def __len__(self):
        return len(self.keys())

    def __contains__(self, name):
        return name in self.keys()

    def keys(self):
        """
        The names of all glyphs in the layer.
        """
        # this is not generated dynamically since we
        # support external editing. it must be fixed.
        if not self._scheduledForDeletion:
            return self._keys
        return self._keys - set(self._scheduledForDeletion.keys())

    # ----------
    # Attributes
    # ----------

    # name

    def _set_name(self, value):
        value = tounicode(value)
        oldName = self._name
        if oldName != value:
            self._name = value
            data = dict(oldName=oldName, newName=value)
            self.postNotification(notification="Layer.NameChanged", data=data)
            self.dirty = True

    def _get_name(self):
        return self._name

    name = property(_get_name, _set_name, doc="The name of the layer. Setting this posts *Layer.NameChanged* and *Layer.Changed* notifications.")

    # color

    def _get_color(self):
        return self._color

    def _set_color(self, color):
        if color is None:
            newColor = None
        else:
            newColor = Color(color)
        oldColor = self._color
        if oldColor != newColor:
            self._color = newColor
            data = dict(oldColor=oldColor, newColor=newColor)
            self.postNotification(notification="Layer.ColorChanged", data=data)
            self.dirty = True

    color = property(_get_color, _set_color, doc="The layer's :class:`Color` object. When setting, the value can be a UFO color string, a sequence of (r, g, b, a) or a :class:`Color` object. Setting this posts *Layer.ColorChanged* and *Layer.Changed* notifications.")

    # -------------
    # Data Skimmers
    # -------------

    # outlines

    def _get_glyphsWithOutlines(self):
        found = []
        # scan loaded glyphs
        for glyphName, glyph in self._glyphs.items():
            if glyphName in self._scheduledForDeletion:
                continue
            if len(glyph):
                found.append(glyphName)
        # scan glyphs that have not been loaded
        if self._glyphSet is not None:
            for glyphName, fileName in self._glyphSet.contents.items():
                if glyphName in self._glyphs or glyphName in self._scheduledForDeletion:
                    continue
                glif = self._glyphSet.getGLIF(glyphName)
                containsPoints = _fetchHasOutlineData(glif)
                if containsPoints:
                    found.append(glyphName)
        return found

    glyphsWithOutlines = property(_get_glyphsWithOutlines, doc="A list of glyphs containing outlines.")

    # component references

    def _get_componentReferences(self):
        found = {}
        # scan loaded glyphs
        for glyphName, glyph in self._glyphs.items():
            if glyphName in self._scheduledForDeletion:
                continue
            if not glyph.components:
                continue
            for component in glyph.components:
                baseGlyph = component.baseGlyph
                if baseGlyph not in found:
                    found[baseGlyph] = set()
                found[baseGlyph].add(glyphName)
        # scan glyphs that have not been loaded
        if self._glyphSet is not None:
            glyphNames = set(self._glyphSet.contents.keys()) - set(self._glyphs.keys())
            for glyphName, baseList in self._glyphSet.getComponentReferences(glyphNames).items():
                for baseGlyph in baseList:
                    if baseGlyph not in found:
                        found[baseGlyph] = set()
                    found[baseGlyph].add(glyphName)
        return found

    componentReferences = property(_get_componentReferences, doc="A dict of describing the component relationships in the layer. The dictionary is of form ``{base glyph : [references]}``.")

    # image references

    def _get_imageReferences(self):
        found = {}
        # scan loaded glyphs
        for glyphName, glyph in self._glyphs.items():
            if glyphName in self._scheduledForDeletion:
                continue
            image = glyph.image
            if image is not None and image.fileName is not None:
                fileName = image.fileName
                if fileName not in found:
                    found[fileName] = []
                found[fileName].append(glyphName)
        # scan glyphs that have not been loaded
        if self._glyphSet is not None:
            glyphNames = set(self._glyphSet.contents.keys()) - set(self._glyphs.keys())
            for glyphName, fileName in self._glyphSet.getImageReferences(glyphNames).items():
                if fileName not in found:
                    found[fileName] = []
                found[fileName].append(glyphName)
        return found

    imageReferences = property(_get_imageReferences, doc="A dict of describing the image file references in the layer. The dictionary is of form ``{image file name : [references]}``.")

    # bounds

    def _get_bounds(self):
        fontRect = None
        for glyph in self:
            glyphRect = glyph.bounds
            if glyphRect is None:
                continue
            if fontRect is None:
                fontRect = glyphRect
            else:
                fontRect = unionRect(fontRect, glyphRect)
        return fontRect

    bounds = property(_get_bounds, doc="The bounds of all glyphs in the layer. This can be an expensive operation.")

    # control point bounds

    def _get_controlPointBounds(self):
        fontRect = None
        for glyph in self:
            glyphRect = glyph.controlPointBounds
            if glyphRect is None:
                continue
            if fontRect is None:
                fontRect = glyphRect
            else:
                fontRect = unionRect(fontRect, glyphRect)
        return fontRect

    controlPointBounds = property(_get_controlPointBounds, doc="The control bounds of all glyphs in the layer. This only measures the point positions, it does not measure curves. So, curves without points at the extrema will not be properly measured. This is an expensive operation.")

    # -----------
    # Sub-Objects
    # -----------

    # lib

    def instantiateLib(self):
        lib = self._libClass(
            layer=self
        )
        return lib

    def beginSelfLibNotificationObservation(self):
        self._lib.addObserver(observer=self, methodName="_libDirtyStateChange", notification="Lib.Changed")

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
        return self._lib

    def _set_lib(self, value):
        if value is not None:
            self.lib.clear()
            self.lib.update(value)

    lib = property(_get_lib, _set_lib, doc="The layer's :class:`Lib` object.")

    # unicode data

    def instantiateUnicodeData(self):
        unicodeData = self._unicodeDataClass(
            layer=self
        )
        return unicodeData

    def beginSelfUnicodeDataNotificationObservation(self):
        pass

    def endSelfUnicodeDataNotificationObservation(self):
        if self._unicodeData is None or self._unicodeData.dispatcher is None:
            return
        self._unicodeData.endSelfNotificationObservation()

    def _get_unicodeData(self):
        if self._unicodeData is None:
            cmap = {}
            for glyphName, glyph in self._glyphs.items():
                if glyphName in self._scheduledForDeletion:
                    continue
                if not glyph.unicodes:
                    continue
                for code in glyph.unicodes:
                    if code in cmap:
                        cmap[code].append(glyphName)
                    else:
                        cmap[code] = [glyphName]
            if self._glyphSet is not None:
                glyphNames = set(self._glyphSet.keys()) - set(self._glyphs.keys())
                for glyphName, unicodes in self._glyphSet.getUnicodes(glyphNames=glyphNames).items():
                    for code in unicodes:
                        if code in cmap:
                            cmap[code].append(glyphName)
                        else:
                            cmap[code] = [glyphName]

            self._unicodeData = self.instantiateUnicodeData()
            self._unicodeData.disableNotifications()
            self._unicodeData.update(cmap)
            self._unicodeData.enableNotifications()
            self.beginSelfUnicodeDataNotificationObservation()
        return self._unicodeData

    unicodeData = property(_get_unicodeData, doc="The layer's :class:`UnicodeData` object.")

    # ----
    # Save
    # ----

    def getSaveProgressBarTickCount(self, formatVersion):
        """
        Get the number of ticks that will be used by a progress bar
        in the save method. This method should not be called externally.
        Subclasses may override this method to implement custom saving behavior.
        """
        return 0

    def save(self, glyphSet, saveAs=False, progressBar=None):
        """
        Save the layer. This method should not be called externally.
        Subclasses may override this method to implement custom saving behavior.
        """
        # for a save as operation, load all the glyphs
        # and treat them as dirty in saveGlyph. this could be more
        # efficiently handled by os.copy...
        if saveAs:
            for glyph in self:
                pass
        for glyphName, glyph in sorted(self._glyphs.items()):
            self.saveGlyph(glyph, glyphSet, saveAs=saveAs)
        # remove deleted glyphs
        if not saveAs and self._scheduledForDeletion:
            for glyphName in self._scheduledForDeletion.keys():
                if glyphName in glyphSet:
                    glyphSet.deleteGlyph(glyphName)
        glyphSet.writeContents()
        self._glyphSet = glyphSet
        self._scheduledForDeletion.clear()

    def saveGlyph(self, glyph, glyphSet, saveAs=False):
        """
        Save a glyph. This method should not be called externally.
        Subclasses may override this method to implement custom saving behavior.
        """
        if glyph.dirty or saveAs:
            glyphSet.writeGlyph(glyph.name, glyph, glyph.drawPoints)
            self._stampGlyphDataState(glyph, glyphSet=glyphSet)
            glyph.dirty = False

    # ---------------------
    # External Edit Support
    # ---------------------

    def _stampGlyphDataState(self, glyph, glyphSet=None):
        if glyphSet is None:
            glyphSet = self._glyphSet
        if glyphSet is None:
            return
        glyphName = glyph.name
        if glyphName not in glyphSet.contents:
            return
        modTime = glyphSet.getGLIFModificationTime(glyphName)
        text = glyphSet.getGLIF(glyphName)
        glyph._dataOnDisk = text
        glyph._dataOnDiskTimeStamp = modTime

    def testForExternalChanges(self):
        """
        Test for external changes. This should not be called externally.
        """
        glyphSet = self._glyphSet
        if glyphSet is None:
            return [], [], []
        glyphSet.rebuildContents()
        # glyphs added since we started up
        addedGlyphs = []
        for glyphName in set(self._glyphSet.keys()) - self._keys:
            # not scheduled for deletion
            if glyphName not in self._scheduledForDeletion:
                addedGlyphs.append(glyphName)
            # scheduled for deletion but not
            # what was scheduled for deletion.
            # consider this a new glyph.
            elif self._scheduledForDeletion[glyphName]["dataOnDiskTimeStamp"] != glyphSet.getGLIFModificationTime(glyphName):
                if self._scheduledForDeletion[glyphName]["dataOnDisk"] != glyphSet.getGLIFModificationTime(glyphName):
                    addedGlyphs.append(glyphName)
        # glyphs deleted since we started up
        deletedGlyphs = list(self._keys - set(glyphSet.keys()))
        # glyphs modified since loading
        modifiedGlyphs = []
        for glyphName, glyph in self._glyphs.items():
            # deleted glyph. skip.
            if glyphName not in glyphSet.contents:
                continue
            modTime = glyphSet.getGLIFModificationTime(glyphName)
            # mod time mismatch
            if modTime != glyph._dataOnDiskTimeStamp:
                text = glyphSet.getGLIF(glyphName)
                # data mismatch
                if text != glyph._dataOnDisk:
                    modifiedGlyphs.append(glyphName)
        # add loaded glyphs to the keys
        for glyphName in addedGlyphs:
            # if the glyph was deleted, but now it is new,
            # unschedule it for deletion.
            if glyphName in self._scheduledForDeletion:
                del self._scheduledForDeletion[glyphName]
            self._keys.add(glyphName)
        # done. whew.
        return modifiedGlyphs, addedGlyphs, deletedGlyphs

    def reloadGlyphs(self, glyphNames):
        """
        Reload the glyphs. This should not be called externally.
        """
        for glyphName in glyphNames:
            if glyphName not in self._glyphs:
                self.loadGlyph(glyphName)
            else:
                glyph = self._glyphs[glyphName]
                glyph.destroyAllRepresentations(None)
                glyph.clear()
                pointPen = glyph.getPointPen()
                self._glyphSet.readGlyph(glyphName=glyphName, glyphObject=glyph, pointPen=pointPen)
                glyph.dirty = False
                self._stampGlyphDataState(glyph)
        data = dict(glyphNames=glyphNames)
        # post a change notification for any glyphs that
        # reference the reloaded glyphs via components.
        componentReferences = self.componentReferences
        referenceChanges = set()
        for glyphName in glyphNames:
            if glyphName not in componentReferences:
                continue
            for reference in componentReferences[glyphName]:
                if reference in glyphNames:
                    continue
                if reference not in self._glyphs:
                    continue
                if reference in referenceChanges:
                    continue
                glyph = self._glyphs[reference]
                glyph.destroyAllRepresentations(None)
                glyph.postNotification(notification=glyph.changeNotificationName)
                referenceChanges.add(reference)

    # ------------------------
    # Notification Observation
    # ------------------------

    def endSelfNotificationObservation(self):
        if self.dispatcher is None:
            return
        for glyph in self._glyphs.values():
            self.endSelfGlyphNotificationObservation(glyph)
        self.endSelfLibNotificationObservation()
        self.endSelfUnicodeDataNotificationObservation()
        super(Layer, self).endSelfNotificationObservation()
        self._layerSet = None

    def _glyphDirtyStateChange(self, notification):
        self.postNotification("Layer.GlyphChanged")
        self.dirty = True

    def _libDirtyStateChange(self, notification):
        self.postNotification("Layer.LibChanged")
        self.dirty = True

    def _glyphNameChange(self, notification):
        data = notification.data
        oldName = data["oldValue"]
        newName = data["newValue"]
        glyph = self._glyphs[oldName]
        self._deleteGlyph(oldName, endObservations=False)
        if self._unicodeData is not None:
            self._unicodeData.removeGlyphData(oldName, glyph.unicodes)
        self._insertGlyph(glyph, beginObservations=False)
        self.postNotification("Layer.GlyphNameChanged", data=dict(oldValue=oldName, newValue=newName))

    def _glyphUnicodesChange(self, notification):
        glyphName = notification.object.name
        data = notification.data
        oldValues = data["oldValue"]
        newValues = data["newValue"]
        if self._unicodeData is not None:
            self._unicodeData.removeGlyphData(glyphName, oldValues)
            self._unicodeData.addGlyphData(glyphName, newValues)
        self.postNotification("Layer.GlyphUnicodesChanged", data=dict(oldValue=oldValues, newValue=newValues))

    # -----------------------------
    # Serialization/Deserialization
    # -----------------------------

    def getDataForSerialization(self, **kwargs):
        simple_get = partial(getattr, self)
        serialize = lambda item: item.getDataForSerialization()
        serialized_get = lambda key: serialize(simple_get(key))

        getters = (
            ('lib', serialized_get),
            ('color', simple_get),
            ('glyphs', lambda _: {name: self[name].getDataForSerialization() for name in self.keys()})
        )

        return self._serialize(getters, **kwargs)

    def setDataFromSerialization(self, data):
        set_attr = partial(setattr, self) # key, data

        def set_glyph(name, data):
            glyph = self.instantiateGlyphObject()
            glyph.setDataFromSerialization(data)
            # there is a redundancy of of the glyph name. I decide here that
            # the single source of truth is the dict key of the layer, not
            # whatever the glyph brings with it.
            glyph.name = name
            self._insertGlyph(glyph)

        def set_glyphs(key, glyphs):
            for name in glyphs:
                set_glyph(name, glyphs[name])

        setters = (
            ('lib', set_attr),
            ('color', set_attr),
            ('glyphs', set_glyphs)
        )

        for key, setter in setters:
            if key not in data:
                continue
            setter(key, data[key])


# ------------
# Fast Parsers
# ------------

# this was forked from glifLib.

def _number(s):
    try:
        n = int(s)
        return n
    except ValueError:
        pass
    n = float(s)
    return n

class _DoneParsing(Exception): pass

class _BaseParser(object):

    def __init__(self):
        self._elementStack = []

    def parse(self, text):
        from xml.parsers.expat import ParserCreate
        parser = ParserCreate()
        # no attribute returns_unicode in Python3
        if hasattr(parser, "returns_unicode"):
            parser.returns_unicode = 0
        parser.StartElementHandler = self.startElementHandler
        parser.EndElementHandler = self.endElementHandler
        parser.Parse(text)

    def startElementHandler(self, name, attrs):
        self._elementStack.append(name)

    def endElementHandler(self, name):
        other = self._elementStack.pop(-1)
        assert other == name


def _fetchControlPointBoundsData(glif):
    parser = _FetchControlPointBoundsDataParser()
    try:
        parser.parse(glif)
    except _DoneParsing:
        pass
    return list(parser.points), list(parser.components)

_onCurvePointTypes = set(("move", "line", "curve", "qcurve"))
_transformationInfo = (
    ("xScale",    1),
    ("xyScale",   0),
    ("yxScale",   0),
    ("yScale",    1),
    ("xOffset",   0),
    ("yOffset",   0),
)

class _FetchControlPointBoundsDataParser(_BaseParser):

    def __init__(self):
        self.points = set()
        self.components = []
        super(_FetchControlPointBoundsDataParser, self).__init__()

    def startElementHandler(self, name, attrs):
        if name == "point" and self._elementStack and self._elementStack[-1] == "contour":
            if attrs.get("type") in _onCurvePointTypes:
                x = attrs.get("x")
                y = attrs.get("y")
                if x is not None and y is not None:
                    x = _number(x)
                    y = _number(y)
                    self.points.add((x, y))
        elif name == "component" and self._elementStack and self._elementStack[-1] == "outline":
            base = attrs.get("base")
            transformation = []
            for attr, default in _transformationInfo:
                value = attrs.get(attr)
                if value is None:
                    value = default
                else:
                    value = _number(value)
                transformation.append(value)
            self.components.append((base, transformation))
        super(_FetchControlPointBoundsDataParser, self).startElementHandler(name, attrs)

    def endElementHandler(self, name):
        if name == "outline":
            raise _DoneParsing
        super(_FetchControlPointBoundsDataParser, self).endElementHandler(name)


def _fetchHasOutlineData(glif):
    parser = _FetchHasOutlineDataParser()
    try:
        parser.parse(glif)
    except _DoneParsing:
        pass
    return parser.hasOutline

class _FetchHasOutlineDataParser(_BaseParser):

    def __init__(self):
        self.hasOutline = False
        super(_FetchHasOutlineDataParser, self).__init__()

    def startElementHandler(self, name, attrs):
        if name == "point" and self._elementStack and self._elementStack[-1] == "contour":
            segmentType = attrs.get("type")
            if segmentType not in ("move", "offcurve", None):
                self.hasOutline = True
                raise _DoneParsing
        super(_FetchHasOutlineDataParser, self).startElementHandler(name, attrs)

    def endElementHandler(self, name):
        if name == "outline":
            raise _DoneParsing
        super(_FetchHasOutlineDataParser, self).endElementHandler(name)


if __name__ == "__main__":
    import doctest
    doctest.testmod()
