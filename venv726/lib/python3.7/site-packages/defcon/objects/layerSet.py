from __future__ import absolute_import
import weakref
from fontTools.ufoLib import UFOReader, UFOFileStructure
from defcon.objects.base import BaseObject
from defcon.objects.layer import Layer


class LayerSet(BaseObject):

    """
    This object manages all layers in the font.

    **This object posts the following notifications:**

    +-------------------------------+
    |Name                           |
    +===============================+
    |LayerSet.Changed               |
    +-------------------------------+
    |LayerSet.LayersChanged         |
    +-------------------------------+
    |LayerSet.LayerChanged          |
    +-------------------------------+
    |LayerSet.DefaultLayerWillChange|
    +-------------------------------+
    |LayerSet.DefaultLayerChanged   |
    +-------------------------------+
    |LayerSet.LayerOrderChanged     |
    +-------------------------------+
    |LayerSet.LayerAdded            |
    +-------------------------------+
    |LayerSet.LayerDeleted          |
    +-------------------------------+
    |LayerSet.LayerWillBeDeleted    |
    +-------------------------------+
    |LayerSet.LayerNameChanged      |
    +-------------------------------+

    This object behaves like a dict. For example, to get a particular
    layer::

        layer = layerSet["layer name"]

    If the layer name is None, the default layer will be retrieved.

    Note: It's up to the caller to ensure that a default layer is present
    as required by the UFO specification.
    """

    changeNotificationName = "LayerSet.Changed"
    representationFactories = {}

    def __init__(self, font=None, layerClass=None, libClass=None, unicodeDataClass=None,
            guidelineClass=None, glyphClass=None,
            glyphContourClass=None, glyphPointClass=None, glyphComponentClass=None, glyphAnchorClass=None,
            glyphImageClass=None):

        if font is not None:
            font = weakref.ref(font)
        self._font = font
        super(LayerSet, self).__init__()
        self.beginSelfNotificationObservation()

        if layerClass is None:
            layerClass = Layer
        self._layerClass = layerClass
        self._libClass = libClass
        self._unicodeDataClass = unicodeDataClass
        self._glyphClass = glyphClass
        self._glyphContourClass = glyphContourClass
        self._glyphPointClass = glyphPointClass
        self._glyphComponentClass = glyphComponentClass
        self._glyphAnchorClass = glyphAnchorClass
        self._glyphImageClass = glyphImageClass
        self._guidelineClass = guidelineClass

        self._layers = {}
        self._layerOrder = []
        self._defaultLayer = None

        self._layerActionHistory = []

    def __del__(self):
        super(LayerSet, self).__del__()
        self._layers = None

    # --------------
    # Parent Objects
    # --------------

    def getParent(self):
        return self.font

    def _get_font(self):
        if self._font is None:
            return None
        return self._font()

    font = property(_get_font, doc="The :class:`Font` that this layer set belongs to.")

    # -------------
    # Default Layer
    # -------------

    def _get_defaultLayerName(self):
        defaultLayer = self.defaultLayer
        for name, layer in self._layers.items():
            if layer == defaultLayer:
                return name

    _defaultLayerName = property(_get_defaultLayerName)

    def _get_defaultLayer(self):
        return self._defaultLayer

    def _set_defaultLayer(self, layer):
        if layer is None:
            raise ValueError("The default layer must not be None.")
        if layer == self._defaultLayer:
            return
        self.postNotification(notification="LayerSet.DefaultLayerWillChange")
        oldName = None
        if self._defaultLayer is not None:
            oldName = self._defaultLayer.name
        self._defaultLayer = layer
        self._layerActionHistory.append(dict(action="default", newDefault=layer.name, oldDefault=oldName))
        self.postNotification(notification="LayerSet.DefaultLayerChanged", data=dict(oldValue=oldName, newValue=layer.name))
        self.dirty = True

    defaultLayer = property(_get_defaultLayer, _set_defaultLayer, doc="The default :class:`Layer` object. Setting this will post *LayerSet.DefaultLayerChanged* and *LayerSet.Changed* notifications.")

    # -----------
    # Layer Order
    # -----------

    def _get_layerOrder(self):
        return list(self._layerOrder)

    def _set_layerOrder(self, order):
        oldOrder = self._layerOrder
        if self._layerOrder == order:
            return
        assert len(order) == len(self._layerOrder)
        assert set(order) == set(self._layerOrder)
        self._layerOrder = list(order)
        self.postNotification(notification="LayerSet.LayerOrderChanged", data=dict(oldValue=oldOrder, newValue=order))
        self.dirty = True

    layerOrder = property(_get_layerOrder, _set_layerOrder, doc="The layer order from top to bottom. Setting this will post *LayerSet.LayerOrderChanged* and *LayerSet.Changed* notifications.")

    # -------------
    # Layer Creation
    # -------------

    def instantiateLayer(self, glyphSet):
        layer = self._layerClass(
            layerSet=self,
            glyphSet=glyphSet,
            libClass=self._libClass,
            unicodeDataClass=self._unicodeDataClass,
            glyphClass=self._glyphClass,
            glyphContourClass=self._glyphContourClass,
            glyphPointClass=self._glyphPointClass,
            glyphComponentClass=self._glyphComponentClass,
            glyphAnchorClass=self._glyphAnchorClass,
            guidelineClass=self._guidelineClass,
            glyphImageClass=self._glyphImageClass
        )
        return layer

    def beginSelfLayerNotificationObservation(self, layer):
        layer.addObserver(observer=self, methodName="_layerDirtyStateChange", notification="Layer.Changed")
        layer.addObserver(observer=self, methodName="_layerNameChange", notification="Layer.NameChanged")

    def endSelfLayerNotificationObservation(self, layer):
        if layer.dispatcher is None:
            return
        layer.removeObserver(observer=self, notification="Layer.Changed")
        layer.removeObserver(observer=self, notification="Layer.NameChanged")
        layer.endSelfNotificationObservation()

    def newLayer(self, name, glyphSet=None):
        """
        Create a new :class:`Layer` and add it to
        the top of the layer order. **glyphSet** should
        only be passed when reading from a UFO.

        This posts *LayerSet.LayerAdded* and *LayerSet.Changed* notifications.
        """
        if name in self._layers:
            raise KeyError("A layer named \"%s\" already exists." % name)
        assert name is not None
        layer = self.instantiateLayer(glyphSet)
        self.beginSelfLayerNotificationObservation(layer)
        layer.disableNotifications()
        layer.name = name
        if glyphSet is None:
            layer.dirty = True
        else:
            glyphSet.readLayerInfo(layer)
            layer.dirty = False
        layer.enableNotifications()
        self._stampLayerInfoDataState(layer)
        self._layers[name] = layer
        self._layerOrder.append(name)
        self._layerActionHistory.append(dict(action="new", name=name))
        self.postNotification("LayerSet.LayerAdded", data=dict(name=name))
        self.postNotification("LayerSet.LayersChanged")
        self.dirty = True
        return layer

    # -------------
    # Dict Behavior
    # -------------

    def __iter__(self):
        for name in self.layerOrder:
            yield self[name]

    def __getitem__(self, name):
        if name is None:
            name = self._defaultLayerName
        return self._layers[name]

    def __delitem__(self, name):
        if name is None:
            name = self._defaultLayerName
        if name not in self:
            raise KeyError("%s not in layers" % name)
        self.postNotification("LayerSet.LayerWillBeDeleted", data=dict(name=name))
        layer = self._layers[name]
        self.endSelfLayerNotificationObservation(layer)
        del self._layers[name]
        self._layerOrder.remove(name)
        self._layerActionHistory.append(dict(action="delete", name=name))
        self.postNotification("LayerSet.LayerDeleted", data=dict(name=name))
        self.postNotification("LayerSet.LayersChanged")
        self.dirty = True

    def __len__(self):
        return len(self.layerOrder)

    def __contains__(self, name):
        if name is None:
            name = self._defaultLayerName
        return name in self._layers

    # ----
    # Save
    # ----

    def getSaveProgressBarTickCount(self, formatVersion):
        """
        Get the number of ticks that will be used by a progress bar
        in the save method. This method should not be called externally.
        Subclasses may override this method to implement custom saving behavior.
        """
        count = 0
        if formatVersion < 3:
            count += 1
            count += self.defaultLayer.getSaveProgressBarTickCount(formatVersion)
        else:
            for layer in self:
                count += 1
                count += layer.getSaveProgressBarTickCount(formatVersion)
        return count

    def save(self, writer, saveAs=False, progressBar=None):
        """
        Save all layers. This method should not be called externally.
        Subclasses may override this method to implement custom saving behavior.
        """
        # work through the layer action history
        if not saveAs:
            for actionData in self._layerActionHistory:
                action = actionData["action"]
                if action == "delete":
                    layerName = actionData["name"]
                    if layerName in writer.layerContents:
                        writer.deleteGlyphSet(layerName)
                elif action == "rename":
                    oldName = actionData["oldName"]
                    newName = actionData["newName"]
                    if oldName in writer.layerContents:
                        writer.renameGlyphSet(oldName, newName)
                        if newName == self.defaultLayer.name:
                            writer.renameGlyphSet(newName, newName, defaultLayer=True)
                elif action == "default":
                    newDefault = actionData["newDefault"]
                    oldDefault = actionData["oldDefault"]
                    # if either one is already in the writer.layerContents it should be renamed
                    # otherwise it will be handled by the creation of the glyph set
                    if oldDefault in writer.layerContents:
                        # rename the old default layer by itself and unflag it as the default layer
                        writer.renameGlyphSet(oldDefault, oldDefault, defaultLayer=False)
                    if newDefault in writer.layerContents:
                        # rename the new default layer by itself and flag it as the default layer
                        writer.renameGlyphSet(newDefault, newDefault, defaultLayer=True)

                elif action == "new":
                    # this will be handled by the creation of the glyph set
                    pass
        # save the layers

        # The parent ZipFS is going to be closed inside Font.save, hence
        # any operations on the GlyphSet's SubFS will fail after that.
        # To prevent this, we need to reset each layer._glyphSet to None
        # after saving, when the file structure is zip.
        # By the time we finish saving a layer, all the glyph data has
        # been loaded so this is ok. However, setting _glyphSet to None
        # also means that the Layer.testForExternalChanges method will
        # produce no effect when the file structure is zip.
        # This is understandable because only one process at a time
        # can write to a zip file.
        isZip = writer.fileStructure is UFOFileStructure.ZIP

        if writer.formatVersion < 3:
            if progressBar is not None:
                progressBar.update(text="Saving glyphs...", increment=0)
            layer = self.defaultLayer
            glyphSet = writer.getGlyphSet(layerName=None, defaultLayer=True, validateRead=self.ufoLibReadValidate, validateWrite=self.ufoLibWriteValidate)
            layer.save(glyphSet, saveAs=saveAs, progressBar=progressBar)
            if isZip:
                layer._glyphSet = None
            if progressBar is not None:
                progressBar.update()
        else:
            for layerName in self.layerOrder:
                if progressBar is not None:
                    progressBar.update(text="Saving layer \"%s\"..." % layerName, increment=0)
                layer = self[layerName]
                isDefaultLayer = layer == self.defaultLayer
                glyphSet = writer.getGlyphSet(layerName=layerName, defaultLayer=isDefaultLayer, validateRead=self.ufoLibReadValidate, validateWrite=self.ufoLibWriteValidate)
                layer.save(glyphSet, saveAs=saveAs, progressBar=progressBar)
                if isZip:
                    layer._glyphSet = None
                # this prevents us from saving when the color was deleted
                #if layer.lib or layer.color:
                glyphSet.writeLayerInfo(layer)
                self._stampLayerInfoDataState(layer)
                layer.dirty = False
                if progressBar is not None:
                    progressBar.update()
            writer.writeLayerContents(self.layerOrder)
        # reset the action history
        self._layerActionHistory = []
        # if < UFO 3 was written, flag all of the non-default layers as "new"
        defaultLayer = self.defaultLayer
        for layer in self:
            if layer == defaultLayer:
                continue
            self._layerActionHistory.append(dict(action="new", name=layer.name))

    # ------------------------
    # Notification Observation
    # ------------------------

    def endSelfNotificationObservation(self):
        if self.dispatcher is None:
            return
        for layer in self._layers.values():
            self.endSelfLayerNotificationObservation(layer)
        super(LayerSet, self).endSelfNotificationObservation()
        self._font = None

    def _layerDirtyStateChange(self, notification):
        self.postNotification("LayerSet.LayerChanged")
        self.dirty = True

    def _layerNameChange(self, notification):
        data = notification.data
        oldName = data["oldName"]
        newName = data["newName"]
        self._layers[newName] = self._layers.pop(oldName)
        index = self._layerOrder.index(oldName)
        self._layerOrder.pop(index)
        self._layerOrder.insert(index, newName)
        self._layerActionHistory.append(dict(action="rename", oldName=oldName, newName=newName))
        self.postNotification("LayerSet.LayerNameChanged")

    # ---------------------
    # External Edit Support
    # ---------------------

    def _stampLayerInfoDataState(self, layer):
        if layer._glyphSet is None:
            return
        # there isn't a mod time function
        # so load the data and pack it.
        i = _StaticLayerInfoMaker()
        layer._glyphSet.readLayerInfo(i)
        layer._dataOnDisk = i.pack()

    def testForExternalChanges(self, reader):
        """
        Test for external changes. This should not be called externally.
        """
        # changed default
        defaultLayerName = self._defaultLayerName
        onDiskDefaultLayerName = reader.getDefaultLayerName()
        defaultLayerChanged = defaultLayerName != onDiskDefaultLayerName
        # changed layer order
        onDiskLayerOrder = reader.getLayerNames()
        layerOrderChanged = onDiskLayerOrder != self.layerOrder
        # layers added since we started up
        addedLayers = []
        for layerName in set(onDiskLayerOrder) - set(self.layerOrder):
            # try to filter out layers that were removed in memory
            wasDeletedInMemory = False
            for actionData in self._layerActionHistory:
                action = actionData["action"]
                if action == "delete" and actionData["name"] == layerName:
                    wasDeletedInMemory = True
            if not wasDeletedInMemory:
                addedLayers.append(layerName)
        # layers deleted since we started up
        deletedLayers = list(set(self.layerOrder) - set(onDiskLayerOrder))
        # modified layers
        modifiedLayers = {}
        for layerName in self.layerOrder:
            layer = self[layerName]
            newLayerInfo = _StaticLayerInfoMaker()
            layerInfoChanged = False
            if layer._glyphSet is not None:
                layer._glyphSet.readLayerInfo(newLayerInfo)
                layerInfoChanged = layer._dataOnDisk != newLayerInfo.pack()
            modifiedGlyphs, addedGlyphs, deletedGlyphs = layer.testForExternalChanges()
            if modifiedGlyphs or addedGlyphs or deletedGlyphs or layerInfoChanged:
                modifiedLayers[layerName] = dict(
                    info=layerInfoChanged,
                    modified=modifiedGlyphs,
                    added=addedGlyphs,
                    deleted=deletedGlyphs
                )
        # pack
        result = dict(
            defaultLayer=defaultLayerChanged,
            order=layerOrderChanged,
            added=addedLayers,
            deleted=deletedLayers,
            modified=modifiedLayers
        )
        # cross your fingers
        return result

    def reloadLayers(self, layerData):
        """
        Reload the layers. This should not be called externally.
        """
        reader = UFOReader(self.font.path, validate=self.font.ufoLibReadValidate)
        # handle the layers
        currentLayerOrder = self.layerOrder
        for layerName, l in layerData.get("layers", {}).items():
            # new layer
            if layerName not in currentLayerOrder:
                glyphSet = reader.getGlyphSet(layerName, validateRead=self.ufoLibReadValidate, validateWrite=self.font.ufoLibWriteValidate)
                self.newLayer(layerName, glyphSet)
            # get the layer
            layer = self[layerName]
            # reload the layer info
            if l.get("info"):
                layer.color = None
                layer.lib.clear()
                layer._glyphSet.readLayerInfo(layer)
                self._stampLayerInfoDataState(layer)
            # reload the glyphs
            glyphNames = l.get("glyphNames", [])
            if glyphNames:
                layer.reloadGlyphs(glyphNames)
        # handle the order
        if layerData.get("order", False):
            newLayerOrder = reader.getLayerNames()
            for layerName in self.layerOrder:
                if layerName not in newLayerOrder:
                    newLayerOrder.append(layerName)
            self.layerOrder = newLayerOrder
        # handle the default layer
        if layerData.get("default", False):
            newDefaultLayerName = reader.getDefaultLayerName()
            self.defaultLayer = self[newDefaultLayerName]

    # -----------------------------
    # Serialization/Deserialization
    # -----------------------------

    def getDataForSerialization(self, **kwargs):
        serialize = lambda item: item.getDataForSerialization()

        def get_layers(k):
            layers = []
            for name in self.layerOrder:
                layer = self[name]
                isDefaultLayer = layer == self.defaultLayer
                layers.append((name, serialize(layer), isDefaultLayer))
            return layers

        getters = [('layers', get_layers)]

        return self._serialize(getters, **kwargs)

    def setDataFromSerialization(self, data):
        if 'layers' not in data:
            return
        for name, data, isDefault in data['layers']:
            layer = self.newLayer(name)
            layer.setDataFromSerialization(data)
            if isDefault:
                self.defaultLayer = layer

class _StaticLayerInfoMaker(object):

    def __init__(self):
        self.lib = {}
        self.color = None

    def pack(self):
        from fontTools.misc import plistlib
        data = {}
        if self.lib:
            data["lib"] = self.lib
        if self.color is not None:
            data["color"] = self.color
        return plistlib.dumps(data)


if __name__ == "__main__":
    import doctest
    doctest.testmod()
