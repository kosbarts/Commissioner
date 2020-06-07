import weakref
from fontTools.ttLib import TTFont
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from defcon.objects.base import BaseObject

try:
    import compositor
    from defcon.objects.uniData import UnicodeData
    from defcon.objects.features import Features
except ImportError:
    pass

# ---------
# Factories
# ---------

def _makeCMAP(unicodeData):
    mapping = {}
    for name, values in unicodeData.items():
        mapping[name] = values[0]
    return mapping

def _layoutEngineOTLTablesRepresentationFactory(layoutEngine):
    font = layoutEngine.font
    gdef = gsub = gpos = None
    if font.features.text:
        otf = TTFont()
        otf.setGlyphOrder(sorted(font.keys()))
        # compile with fontTools
        try:
            addOpenTypeFeaturesFromString(otf, font.features.text)
        except:
            import traceback
            print(traceback.format_exc(5))
        if "GDEF" in otf:
            gdef = otf["GDEF"]
        if "GSUB" in otf:
            gsub = otf["GSUB"]
        if "GPOS" in otf:
            gpos = otf["GPOS"]
    return gdef, gsub, gpos

# -----------
# Main Object
# -----------

class LayoutEngine(BaseObject):

    """
    This object provides a GDEF, GSUB and GPOS OpenType Layout Engine for
    the default layer of the given font. The engine uses the ``compositor``
    module so you must have that installed to use this object.

    **This object posts the following notifications:**

    ====================
    Name
    ====================
    LayoutEngine.Changed
    ====================

    This object monitors the font's feature text and character mapping. When
    those change, the compiled tables will be flagged for recompilation and
    the next time the engine is queried the tables will be recompiled. Any
    data that you have retrieved, such as the list of feature tags, may no
    longer be correct. Thus, the data will need to be retrieved again. To be
    notified when this is necessary, subscribe to the ``LayoutEngine.Changed``
    notification.
    """

    changeNotificationName = "LayoutEngine.Changed"
    representationFactories = {
        "defcon.layoutEngine.tables" : dict(
            factory=_layoutEngineOTLTablesRepresentationFactory,
            destructiveNotifications=("LayoutEngine._DestroyCachedTables")
        )
    }

    def __init__(self, font):
        self._needsInternalUpdate = True
        self._font = weakref.ref(font)
        self._layoutEngine = compositor.LayoutEngine()
        super(LayoutEngine, self).__init__()
        self.beginSelfNotificationObservation()

    def _get_font(self):
        if self._font is not None:
            return self._font()
        return None

    font = property(_get_font)

    def _get_engine(self):
        if self._needsInternalUpdate:
            self._updateEngine()
        return self._layoutEngine

    engine = property(_get_engine, doc="The compositor layout engine. This object must always be retrieved from the LayoutEngine for the automatic updating to occur.")

    # --------------
    # Engine Updates
    # --------------

    def _updateEngine(self):
        font = self.font
        cmap = _makeCMAP(font.unicodeData)
        self._layoutEngine.setCMAP(cmap)
        gdef, gsub, gpos = self.getRepresentation("defcon.layoutEngine.tables")
        self._layoutEngine.setFeatureTables(gdef, gsub, gpos)
        self._needsInternalUpdate = False

    # -------------
    # Notifications
    # -------------

    def beginSelfNotificationObservation(self):
        super(LayoutEngine, self).beginSelfNotificationObservation()
        self.beginSelfLayersObservation()
        self.beginSelfLayerObservation()
        self.beginSelfFeaturesObservation()

    def endSelfNotificationObservation(self):
        self.endSelfLayersObservation()
        self.endSelfLayerObservation()
        self.endSelfFeaturesObservation()
        super(LayoutEngine, self).endSelfNotificationObservation()
        self._font = None

    # default layer changed (changes cmap)

    def beginSelfLayersObservation(self):
        layers = self.font.layers
        layers.addObserver(observer=self, methodName="_layerSetDefaultLayerWillChange", notification="LayerSet.DefaultLayerWillChange")
        layers.addObserver(observer=self, methodName="_layerSetDefaultLayerChanged", notification="LayerSet.DefaultLayerChanged")

    def endSelfLayersObservation(self):
        layers = self.font.layers
        layers.removeObserver(observer=self, notification="LayerSet.DefaultLayerWillChange")
        layers.removeObserver(observer=self, notification="LayerSet.DefaultLayerChanged")

    def _layerSetDefaultLayerWillChange(self, notification):
        self.endSelfLayerObservation()

    def _layerSetDefaultLayerChanged(self, notification):
        self.beginLayerObservation()
        self._postNeedsUpdateNotification()

    # cmap change

    def beginSelfLayerObservation(self):
        layer = self.font.layers.defaultLayer
        layer.addObserver(observer=self, methodName="_layerGlyphUnicodesChanged", notification="Layer.GlyphUnicodesChanged")

    def endSelfLayerObservation(self):
        layer = self.font.layers.defaultLayer
        layer.removeObserver(observer=self, notification="Layer.GlyphUnicodesChanged")

    def _layerGlyphUnicodesChanged(self):
        self._postNeedsUpdateNotification()

    # feature text change

    def beginSelfFeaturesObservation(self):
        features = self.font.features
        features.addObserver(observer=self, methodName="_featuresTextChanged", notification="Features.TextChanged")

    def endSelfFeaturesObservation(self):
        features = self.font.features
        features.removeObserver(observer=self, notification="Features.TextChanged")

    def _featuresTextChanged(self, notification):
        self._destroyCachedTables()
        self._postNeedsUpdateNotification()

    # posting

    def _destroyCachedTables(self):
        self.postNotification("LayoutEngine._DestroyCachedTables")

    def _postNeedsUpdateNotification(self):
        self._needsInternalUpdate = True
        self.postNotification(self.changeNotificationName)

    # ----------
    # Engine API
    # ----------

    def process(self, stringOrGlyphList, script="latn", langSys=None, rightToLeft=False, case="unchanged"):
        """
        Process a string (or list of glyph names) with the current
        feature states for the given **script** and **langSys**.

        The writing will be left to right unless **rightToLeft**
        is set to True.

        The case may be changed following the Unicode case conversion
        rules by setting **case** to one of the following:

        +-----------+
        | unchanged |
        +-----------+
        | upper     |
        +-----------+
        | lower     |
        +-----------+
        """
        self._updateEngine()
        glyphRecords = self.engine.process(
                stringOrGlyphList,
                script=script, langSys=langSys,
                rightToLeft=rightToLeft, case=case
            )
        layer = self.font.layers.defaultLayer
        finalGlyphRecords = []
        for glyphRecord in glyphRecords:
            if glyphRecord.glyphName not in layer:
                continue
            layerGlyph = layer[glyphRecord.glyphName]
            glyphRecord.advanceWidth += layerGlyph.width
            glyphRecord.advanceHeight += layerGlyph.height
            finalGlyphRecords.append(glyphRecord)
        return finalGlyphRecords

    def getScriptList(self):
        """
        Get a list of defined scripts.
        """
        return self.engine.getScriptList()

    def getLanguageList(self):
        """
        Get a list of defined languages.
        """
        return self.engine.getLanguageList()

    def getFeatureList(self):
        """
        Get a list of defined features.
        """
        return self.engine.getFeatureList()

    def getFeatureState(self, name):
        """
        Get the state for the feature with **name**.
        """
        return self.engine.getFeatureState(name)

    def setFeatureState(self, name, state):
        """
        Set the state for the feature with **name**.
        """
        self.engine.setFeatureState(name, state)
