import unittest
import os
import glob
import tempfile
import shutil
from defcon import Font, Glyph, LayerSet, Guideline
from defcon.errors import DefconError
from defcon.tools.notifications import NotificationCenter
from defcon.test.testTools import (
    getTestFontPath, getTestFontCopyPath, makeTestFontCopy,
    tearDownTestFontCopy)
from fontTools.ufoLib import UFOReader, UFOWriter, UFOFileStructure
import fs.path
import zipfile
import logging
from fontTools.misc.loggingTools import CapturingLogHandler

try:
    from plistlib import load, dump
except ImportError:
    from plistlib import readPlist as load, writePlist as dump

testFeaturesText = """
@class1 = [a b c d];

feature liga {
    sub f i by fi;
} liga;

@class2 = [x y z];

feature salt {
    sub a by a.alt;
} salt; feature ss01 {sub x by x.alt} ss01;

feature ss02 {sub y by y.alt} ss02;

# feature calt {
#     sub a b' by b.alt;
# } calt;
"""

class FontTest(unittest.TestCase):

    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)
        # Python 3 renamed assertRaisesRegexp to assertRaisesRegex,
        # and fires deprecation warnings if a program uses the old name.
        if not hasattr(self, "assertRaisesRegex"):
            self.assertRaisesRegex = self.assertRaisesRegexp

    def tearDown(self):
        if os.path.exists(getTestFontCopyPath()):
            tearDownTestFontCopy()

    def test_set_parent_data_in_glyph(self):
        font = Font(getTestFontPath())
        glyph = font["A"]
        self.assertEqual(id(glyph.getParent()), id(font))

    def test_dispatcher(self):
        font = Font()
        self.assertIsInstance(font.dispatcher, NotificationCenter)
        with self.assertRaises(AttributeError):
            self.font.dispatcher = "foo"

    def test_newGlyph(self):
        font = Font(getTestFontPath())
        glyph = font.newGlyph("NewGlyphTest")
        self.assertEqual(glyph.name, "NewGlyphTest")
        self.assertTrue(glyph.dirty)
        self.assertTrue(font.dirty)
        self.assertEqual(sorted(font.keys()), ["A", "B", "C", "NewGlyphTest"])

    def test_insertGlyph(self):
        font = Font(getTestFontPath())
        glyph = Glyph()
        glyph.name = "NewGlyphTest"
        self.assertEqual(sorted(font.keys()), ["A", "B", "C"])
        font.insertGlyph(glyph)
        self.assertEqual(sorted(font.keys()), ["A", "B", "C", "NewGlyphTest"])

    def test_iter(self):
        font = Font(getTestFontPath())
        self.assertEqual(sorted(glyph.name for glyph in font), ["A", "B", "C"])
        names = []
        for glyph1 in font:
            for glyph2 in font:
                names.append((glyph1.name, glyph2.name))
        self.assertEqual(sorted(names),
                         [("A", "A"), ("A", "B"), ("A", "C"),
                          ("B", "A"), ("B", "B"), ("B", "C"),
                          ("C", "A"), ("C", "B"), ("C", "C")])

    def test_getitem(self):
        font = Font(getTestFontPath())
        self.assertEqual(font["A"].name, "A")
        self.assertEqual(font["B"].name, "B")
        with self.assertRaises(KeyError):
            font["NotInFont"]

    def test_delitem(self):
        path = makeTestFontCopy()
        font = Font(path)
        del font["A"]
        self.assertTrue(font.dirty)
        font.newGlyph("NewGlyphTest")
        del font["NewGlyphTest"]
        self.assertEqual(sorted(font.keys()), ["B", "C"])
        self.assertEqual(len(font), 2)
        self.assertFalse("A" in font)
        font.save()
        fileNames = glob.glob(os.path.join(path, 'glyphs', '*.glif'))
        fileNames = [os.path.basename(fileName) for fileName in fileNames]
        self.assertEqual(sorted(fileNames), ["B_.glif", "C_.glif"])
        with self.assertRaises(KeyError):
            del font["NotInFont"]

    def test_delitem_glyph_not_dirty(self):
        path = makeTestFontCopy()
        font = Font(path)
        font["A"]  # glyph = font["A"]
        glyphPath = os.path.join(path, "glyphs", "A_.glif")
        os.remove(glyphPath)
        contentsPath = os.path.join(path, "glyphs", "contents.plist")
        with open(contentsPath, "rb") as f:
            plist = load(f)
        del plist["A"]
        with open(contentsPath, "wb") as f:
            dump(plist, f)
        r = font.testForExternalChanges()
        self.assertEqual(r["deletedGlyphs"], ["A"])
        del font["A"]
        font.save()
        self.assertFalse(os.path.exists(glyphPath))

    def test_delitem_glyph_dirty(self):
        path = makeTestFontCopy()
        font = Font(path)
        glyph = font["A"]
        glyph.dirty = True
        glyphPath = os.path.join(path, "glyphs", "A_.glif")
        os.remove(glyphPath)
        contentsPath = os.path.join(path, "glyphs", "contents.plist")
        with open(contentsPath, "rb") as f:
            plist = load(f)
        del plist["A"]
        with open(contentsPath, "wb") as f:
            dump(plist, f)
        r = font.testForExternalChanges()
        self.assertEqual(r["deletedGlyphs"], ["A"])
        del font["A"]
        font.save()
        self.assertFalse(os.path.exists(glyphPath))

    def test_len(self):
        font = Font(getTestFontPath())
        self.assertEqual(len(font), 3)
        font = Font()
        self.assertEqual(len(font), 0)

    def test_contains(self):
        font = Font(getTestFontPath())
        self.assertTrue("A" in font)
        self.assertFalse("NotInFont" in font)
        font = Font()
        self.assertFalse("A" in font)

    def test_keys(self):
        font = Font(getTestFontPath())
        self.assertEqual(sorted(font.keys()), ["A", "B", "C"])
        del font["A"]
        self.assertEqual(sorted(font.keys()), ["B", "C"])
        font.newGlyph("A")
        self.assertEqual(sorted(font.keys()), ["A", "B", "C"])
        font = Font()
        self.assertEqual(font.keys(), set())
        font.newGlyph("A")
        self.assertEqual(sorted(font.keys()), ["A"])

    def test_path_get(self):
        path = getTestFontPath()
        font = Font(path)
        self.assertEqual(font.path, path)
        font = Font()
        self.assertIsNone(font.path)

    def test_path_set(self):
        path1 = getTestFontPath()
        font = Font(path1)
        path2 = getTestFontPath("setPathTest.ufo")
        shutil.copytree(path1, path2)
        font.path = path2
        self.assertEqual(font.path, path2)
        shutil.rmtree(path2)

    def test_glyphsWithOutlines(self):
        font = Font(getTestFontPath())
        self.assertEqual(sorted(font.glyphsWithOutlines), ["A", "B"])
        font = Font(getTestFontPath())
        for glyph in font:
            pass
        self.assertEqual(sorted(font.glyphsWithOutlines), ["A", "B"])

    def test_componentReferences(self):
        font = Font(getTestFontPath())
        self.assertEqual(font.componentReferences,
                         {"A": set(["C"]), "B": set(["C"])})

    def test_bounds(self):
        font = Font(getTestFontPath())
        self.assertEqual(font.bounds, (0, 0, 700, 700))

    def test_controPointsBounds(self):
        font = Font(getTestFontPath())
        self.assertEqual(font.controlPointBounds, (0, 0, 700, 700))

    def test_beginSelfLayerSetNotificationObservation(self):
        font = Font()
        self.assertTrue(font.dispatcher.hasObserver(
            font, "LayerSet.Changed", font.layers))
        self.assertTrue(font.dispatcher.hasObserver(
            font, "LayerSet.LayerAdded", font.layers))
        self.assertTrue(font.dispatcher.hasObserver(
            font, "LayerSet.LayerWillBeDeleted", font.layers))

        font.layers.removeObserver(
            observer=self, notification="LayerSet.Changed")
        font.layers.removeObserver(
            observer=self, notification="LayerSet.LayerAdded")
        font.layers.removeObserver(
            observer=self, notification="LayerSet.LayerWillBeDeleted")
        font.layers.endSelfNotificationObservation()

        font.beginSelfLayerSetNotificationObservation()
        self.assertTrue(font.dispatcher.hasObserver(
            font, "LayerSet.Changed", font.layers))
        self.assertTrue(font.dispatcher.hasObserver(
            font, "LayerSet.LayerAdded", font.layers))
        self.assertTrue(font.dispatcher.hasObserver(
            font, "LayerSet.LayerWillBeDeleted", font.layers))

    def test_endSelfLayerSetNotificationObservation(self):
        font = Font()
        font.endSelfLayerSetNotificationObservation()
        self.assertFalse(font.dispatcher.hasObserver(
            font, "LayerSet.Changed", font.layers))
        self.assertFalse(font.dispatcher.hasObserver(
            font, "LayerSet.LayerAdded", font.layers))
        self.assertFalse(font.dispatcher.hasObserver(
            font, "LayerSet.LayerWillBeDeleted", font.layers))

    def test_layers(self):
        font = Font(getTestFontPath())
        self.assertIsInstance(font.layers, LayerSet)
        self.assertEqual(font.layers.layerOrder,
                         ["public.default", "public.background", "Layer 1"])
        self.assertTrue(font.layers.hasObserver(font, "LayerSet.Changed"))
        self.assertTrue(font.layers.hasObserver(font, "LayerSet.LayerAdded"))
        self.assertTrue(font.layers.hasObserver(font,
                                                "LayerSet.LayerWillBeDeleted"))

    def test_font_observes_new_layer(self):
        font = Font()
        font.layers.newLayer("test_layer")
        layer = font.layers["test_layer"]
        self.assertTrue(layer.hasObserver(font, "Layer.GlyphAdded"))

    def test_font_observes_loaded_layers(self):
        font = Font(getTestFontPath())
        for layername in font.layers.layerOrder:
            layer = font.layers[layername]
            self.assertTrue(layer.hasObserver(font, "Layer.GlyphAdded"))

    def test_glyphOrder(self):
        font = Font(getTestFontPath())
        self.assertEqual(font.glyphOrder, [])
        font.glyphOrder = sorted(font.keys())
        self.assertEqual(font.glyphOrder, ["A", "B", "C"])
        layer = font.layers.defaultLayer
        layer.newGlyph("X")
        self.assertEqual(sorted(layer.keys()), ["A", "B", "C", "X"])
        self.assertEqual(font.glyphOrder, ["A", "B", "C", "X"])
        del layer["A"]
        self.assertEqual(font.glyphOrder, ["A", "B", "C", "X"])
        del layer["X"]
        self.assertEqual(font.glyphOrder, ["A", "B", "C"])
        layer["B"].name = "Y"
        self.assertEqual(font.glyphOrder, ["A", "Y", "C"])

    def test_updateGlyphOrder_none(self):
        font = Font(getTestFontPath())
        self.assertEqual(font.glyphOrder, [])
        font.updateGlyphOrder()
        self.assertEqual(font.glyphOrder, [])

    def test_updateGlyphOrder_add(self):
        font = Font(getTestFontPath())
        self.assertEqual(font.glyphOrder, [])
        font.updateGlyphOrder(addedGlyph="test")
        self.assertEqual(font.glyphOrder, ["test"])

    def test_updateGlyphOrder_remove(self):
        font = Font(getTestFontPath())
        self.assertEqual(font.glyphOrder, [])
        font.glyphOrder = ["test"]
        self.assertEqual(font.glyphOrder, ["test"])
        font.updateGlyphOrder(removedGlyph="test")
        self.assertEqual(font.glyphOrder, [])

    def test_updateGlyphOrder_rename(self):
        font = Font(getTestFontPath())
        self.assertEqual(font.glyphOrder, [])
        font.glyphOrder = sorted(font.keys())
        self.assertEqual(font.glyphOrder, ["A", "B", "C"])
        font.updateGlyphOrder(addedGlyph="new", removedGlyph="B")
        self.assertEqual(font.glyphOrder, ["A", "new", "C"])

    def test_guidelines(self):
        font = Font(getTestFontPath())
        self.assertEqual(font.guidelines, [])
        guideline1 = Guideline(guidelineDict={"x": 100})
        guideline2 = Guideline(guidelineDict={"y": 200})
        font.guidelines = [guideline1, guideline2]
        self.assertEqual(font.guidelines, [guideline1, guideline2])

    def test_instantiateGuideline(self):
        font = Font(getTestFontPath())
        guideline = font.instantiateGuideline()
        self.assertIsInstance(guideline, Guideline)
        guideline = font.instantiateGuideline(guidelineDict={"x": 100})
        self.assertEqual(guideline, {'x': 100})

    def test_beginSelfGuidelineNotificationObservation(self):
        font = Font(getTestFontPath())
        guideline = font.instantiateGuideline()
        guideline.font = font
        self.assertFalse(guideline.dispatcher.hasObserver(
            font, "Guideline.Changed", guideline))
        font.beginSelfGuidelineNotificationObservation(guideline)
        self.assertTrue(guideline.dispatcher.hasObserver(
            font, "Guideline.Changed", guideline))

    def test_endSelfGuidelineNotificationObservation(self):
        font = Font(getTestFontPath())
        guideline = font.instantiateGuideline()
        guideline.font = font
        font.beginSelfGuidelineNotificationObservation(guideline)
        self.assertTrue(guideline.hasObserver(
            font, "Guideline.Changed"))
        font.endSelfGuidelineNotificationObservation(guideline)
        self.assertIsNone(guideline.dispatcher)
        self.assertFalse(guideline.hasObserver(
            font, "Guideline.Changed"))

    def test_appendGuideline(self):
        font = Font(getTestFontPath())
        guideline1 = Guideline(guidelineDict={"x": 100})
        font.appendGuideline(guideline1)
        self.assertEqual(font.guidelines, [{'x': 100}])
        guideline2 = Guideline(guidelineDict={"y": 200})
        font.appendGuideline(guideline2)
        self.assertEqual(font.guidelines, [{'x': 100}, {'y': 200}])
        guideline3 = Guideline(guidelineDict={"y": 100})
        font.appendGuideline(guideline3)
        self.assertEqual(font.guidelines, [{'x': 100}, {'y': 200}, {'y': 100}])

    def test_insertGuideline(self):
        font = Font(getTestFontPath())
        guideline1 = Guideline(guidelineDict={"x": 100})
        font.insertGuideline(0, guideline1)
        self.assertEqual(font.guidelines, [{'x': 100}])
        guideline2 = Guideline(guidelineDict={"y": 200})
        font.insertGuideline(0, guideline2)
        self.assertEqual(font.guidelines, [{'y': 200}, {'x': 100}])
        guideline3 = Guideline(guidelineDict={"y": 100})
        font.insertGuideline(2, guideline3)
        self.assertEqual(font.guidelines, [{'y': 200}, {'x': 100}, {'y': 100}])

    def test_removeGuideline(self):
        font = Font(getTestFontPath())
        guideline1 = Guideline(guidelineDict={"x": 100})
        guideline2 = Guideline(guidelineDict={"y": 200})
        font.guidelines = [guideline1, guideline2]
        font.removeGuideline(guideline1)
        self.assertEqual(font.guidelines, [guideline2])

    def test_guidelineIndex(self):
        font = Font(getTestFontPath())
        guideline1 = Guideline(guidelineDict={"x": 100})
        guideline2 = Guideline(guidelineDict={"y": 200})
        font.guidelines = [guideline1, guideline2]
        self.assertEqual(font.guidelineIndex(guideline1), 0)
        self.assertEqual(font.guidelineIndex(guideline2), 1)

    def test_clearGuidelines(self):
        font = Font(getTestFontPath())
        guideline1 = Guideline(guidelineDict={"x": 100})
        guideline2 = Guideline(guidelineDict={"y": 200})
        font.guidelines = [guideline1, guideline2]
        self.assertEqual(font.guidelines, [guideline1, guideline2])
        font.clearGuidelines()
        self.assertEqual(font.guidelines, [])

    def test_save(self):
        for ufo in ("TestFont.ufo", "TestFont.ufoz"):
            path = makeTestFontCopy(getTestFontPath(ufo))
            try:
                font = Font(path)
                origFileStructure = font.ufoFileStructure
                for glyph in font:
                    glyph.dirty = True
                font.save()
                fileNames = sorted(
                    [
                        fs.path.basename(m.path)
                        for m in UFOReader(path).fs.glob("glyphs/*.glif")
                    ]
                )
                self.assertEqual(fileNames, ["A_.glif", "B_.glif", "C_.glif"])
                self.assertEqual(origFileStructure, font.ufoFileStructure)
            finally:
                tearDownTestFontCopy(path)

    def test_save_as(self):
        for ufo in ("TestFont.ufo", "TestFont.ufoz"):
            path = getTestFontPath(ufo)
            font = Font(path)
            origFileStructure = font.ufoFileStructure
            saveAsPath = getTestFontCopyPath(path)
            self.assertFalse(os.path.exists(saveAsPath))
            font.save(saveAsPath)
            try:
                fileNames = sorted(
                    [
                        fs.path.basename(m.path)
                        for m in UFOReader(saveAsPath).fs.glob("glyphs/*.glif")
                    ]
                )
                self.assertEqual(fileNames, ["A_.glif", "B_.glif", "C_.glif"])
                self.assertEqual(font.path, saveAsPath)
                self.assertEqual(origFileStructure, font.ufoFileStructure)
            finally:
                tearDownTestFontCopy(saveAsPath)

    def test_save_same_path(self):
        for ufo in ("TestFont.ufo", "TestFont.ufoz"):
            path = makeTestFontCopy(getTestFontPath(ufo))
            isZip = zipfile.is_zipfile(path)
            try:
                font = Font(path)
                font.save(path)
                if isZip:
                    self.assertTrue(zipfile.is_zipfile(path))
                else:
                    self.assertTrue(os.path.isdir(path))
            finally:
                tearDownTestFontCopy(path)

    def test_save_same_path_different_structure(self):
        for ufo in ("TestFont.ufo", "TestFont.ufoz"):
            path = getTestFontPath(ufo)
            isZip = zipfile.is_zipfile(path)
            font = Font(path)
            with self.assertRaisesRegex(
                DefconError,
                "Can't save font in-place with a different structure"
            ):
                font.save(path, structure="package" if isZip else "zip")

    def test_save_new_font_without_path(self):
        font = Font()
        msg = "Can't save new font without a 'path'"
        with self.assertRaisesRegex(DefconError, msg):
            font.save()

    def test_save_new_font_to_exsisting_directory(self):
        for ufo in ("TestFont.ufo", "TestFont.ufoz"):
            path = makeTestFontCopy(getTestFontPath(ufo))
            try:
                self.assertTrue(os.path.exists(path))
                font = Font()
                font.save(path)
                self.assertTrue(os.path.isdir(path))
            finally:
                tearDownTestFontCopy(path)

    def test_save_ufoz(self):
        path = getTestFontPath()
        tmpdir = tempfile.mkdtemp()
        dest = os.path.join(tmpdir, "TestFont.ufoz")
        try:
            self.assertFalse(os.path.exists(dest))
            font = Font(path)
            self.assertEqual(font.path, path)
            font.save(dest, structure="zip")
            self.assertTrue(os.path.exists(dest))
            self.assertTrue(zipfile.is_zipfile(dest))
            self.assertEqual(font.path, dest)
            self.assertEqual(font.ufoFileStructure, UFOFileStructure.ZIP)
            fileNames = sorted(
                [
                    fs.path.basename(m.path)
                    for m in UFOReader(dest).fs.glob("glyphs/*.glif")
                ]
            )
            self.assertEqual(fileNames, ["A_.glif", "B_.glif", "C_.glif"])
        finally:
            shutil.rmtree(tmpdir)

    def test_save_new_font_to_existing_file(self):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            pass
        path = tmp.name
        self.assertTrue(os.path.exists(path))
        try:
            font = Font()
            font.save(path)
            self.assertTrue(os.path.isdir(path))
        finally:
            if os.path.isfile(path):
                os.remove(path)
            elif os.path.isdir(path):
                shutil.rmtree(path)

    def test_save_in_place_different_format(self):
        path = makeTestFontCopy()
        font = Font(path)
        self.assertEqual(font._ufoFormatVersion, 3)
        font.save(formatVersion=2)
        self.assertEqual(font._ufoFormatVersion, 2)

    def test_save_in_place_invalid_ufo(self):
        path = makeTestFontCopy()
        font = Font(path)
        layercontents = os.path.join(path, "layercontents.plist")
        os.remove(layercontents)
        self.assertFalse(os.path.exists(layercontents))

        logger = logging.getLogger("defcon.objects.font")
        with CapturingLogHandler(logger, level="ERROR") as captor:
            font.save()
        captor.assertRegex("Invalid ufo found")

        self.assertTrue(os.path.exists(layercontents))
        font = Font(path)
        _ = font.layers
        font.save()

    def test_testForExternalChanges(self):
        path = getTestFontPath("TestExternalEditing.ufo")
        font = Font(path)

        # load all the objects so that they get stamped
        font.info  # i = font.info
        k = font.kerning
        font.groups  # g = font.groups
        font.lib  # l = font.lib
        font["A"]  # g = font["A"]

        d = font.testForExternalChanges()
        self.assertFalse(d["info"])
        self.assertFalse(d["kerning"])
        self.assertFalse(d["groups"])
        self.assertFalse(d["lib"])

        # make a simple change to the kerning data
        path = os.path.join(font.path, "kerning.plist")
        f = open(path, "r")
        t = f.read()
        f.close()
        t += " "
        f = open(path, "w")
        f.write(t)
        f.close()
        os.utime(path,
                 (k._dataOnDiskTimeStamp + 1, k._dataOnDiskTimeStamp + 1))

        d = font.testForExternalChanges()
        self.assertTrue(d["kerning"])
        self.assertFalse(d["groups"])
        self.assertFalse(d["info"])
        self.assertFalse(d["lib"])

        # save the kerning data and test again
        font.kerning.dirty = True
        font.save()
        d = font.testForExternalChanges()
        self.assertFalse(d["kerning"])
        self.assertFalse(d["groups"])
        self.assertFalse(d["info"])
        self.assertFalse(d["lib"])

    def test_reloadInfo(self):
        path = getTestFontPath("TestExternalEditing.ufo")
        font = Font(path)
        info = font.info

        path = os.path.join(font.path, "fontinfo.plist")
        f = open(path, "r")
        t = f.read()
        f.close()
        t = t.replace("<integer>750</integer>", "<integer>751</integer>")
        f = open(path, "w")
        f.write(t)
        f.close()

        self.assertEqual(info.ascender, 750)
        font.reloadInfo()
        self.assertEqual(info.ascender, 751)

        t = t.replace("<integer>751</integer>", "<integer>750</integer>")
        f = open(path, "w")
        f.write(t)
        f.close()

    def test_reloadKerning(self):
        path = getTestFontPath("TestExternalEditing.ufo")
        font = Font(path)
        kerning = font.kerning

        path = os.path.join(font.path, "kerning.plist")
        f = open(path, "r")
        t = f.read()
        f.close()
        t = t.replace("<integer>-100</integer>", "<integer>-101</integer>")
        f = open(path, "w")
        f.write(t)
        f.close()

        self.assertEqual(list(kerning.items()), [(("A", "A"), -100)])
        font.reloadKerning()
        self.assertEqual(list(kerning.items()), [(("A", "A"), -101)])

        t = t.replace("<integer>-101</integer>", "<integer>-100</integer>")
        f = open(path, "w")
        f.write(t)
        f.close()

    def test_reloadGroups(self):
        path = getTestFontPath("TestExternalEditing.ufo")
        font = Font(path)
        groups = font.groups

        path = os.path.join(font.path, "groups.plist")
        f = open(path, "r")
        t = f.read()
        f.close()
        t = t.replace("<key>TestGroup</key>", "<key>XXX</key>")
        f = open(path, "w")
        f.write(t)
        f.close()

        self.assertEqual(list(groups.keys()), ["TestGroup"])
        font.reloadGroups()
        self.assertEqual(list(groups.keys()), ["XXX"])

        t = t.replace("<key>XXX</key>", "<key>TestGroup</key>")
        f = open(path, "w")
        f.write(t)
        f.close()

    def test_reloadLib(self):
        path = getTestFontPath("TestExternalEditing.ufo")
        font = Font(path)
        lib = font.lib

        path = os.path.join(font.path, "lib.plist")
        f = open(path, "r")
        t = f.read()
        f.close()
        t = t.replace("<key>org.robofab.glyphOrder</key>",
                      "<key>org.robofab.glyphOrder.XXX</key>")
        f = open(path, "w")
        f.write(t)
        f.close()

        self.assertEqual(list(lib.keys()), ["org.robofab.glyphOrder"])
        font.reloadLib()
        self.assertEqual(list(lib.keys()), ["org.robofab.glyphOrder.XXX"])

        t = t.replace("<key>org.robofab.glyphOrder.XXX</key>",
                      "<key>org.robofab.glyphOrder</key>")
        f = open(path, "w")
        f.write(t)
        f.close()

    def test_reloadGlyphs(self):
        path = getTestFontPath("TestExternalEditing.ufo")
        font = Font(path)
        glyph = font["A"]

        path = os.path.join(font.path, "glyphs", "A_.glif")
        f = open(path, "r")
        t = f.read()
        f.close()
        t = t.replace('<advance width="700"/>', '<advance width="701"/>')
        f = open(path, "w")
        f.write(t)
        f.close()

        self.assertEqual(glyph.width, 700)
        self.assertEqual(len(glyph), 2)
        font.reloadGlyphs(["A"])
        self.assertEqual(glyph.width, 701)
        self.assertEqual(len(glyph), 2)

        t = t.replace('<advance width="701"/>', '<advance width="700"/>')
        f = open(path, "w")
        f.write(t)
        f.close()

    def test_splitFeaturesForConversion(self):
        font = Font()
        self.assertEqual(
            font._splitFeaturesForConversion(testFeaturesText),
            (
                "\n@class1 = [a b c d];\n",
                [("liga", "\nfeature liga {\n    sub f i by fi;\n} liga;\n\n"
                  "@class2 = [x y z];\n"),
                 ("salt", "\nfeature salt {\n    sub a by a.alt;\n} salt; "
                  "feature ss01 {sub x by x.alt} ss01;\n"),
                 ("ss02", "\nfeature ss02 {sub y by y.alt} ss02;\n\n"
                  "# feature calt {\n#     sub a b' by b.alt;\n# } calt;\n")]
            )
        )

    def test_glyph_name_change(self):
        font = Font(getTestFontPath())
        glyph = font["A"]
        glyph.name = "NameChangeTest"
        self.assertEqual(sorted(font.keys()), ["B", "C", "NameChangeTest"])
        self.assertTrue(font.dirty)

    def test_glyph_unicodes_changed(self):
        font = Font(getTestFontPath())
        glyph = font["A"]
        glyph.unicodes = [123, 456]
        self.assertEqual(font.unicodeData[123], ["A"])
        self.assertEqual(font.unicodeData[456], ["A"])
        self.assertEqual(font.unicodeData[66], ["B"])

        font = Font(getTestFontPath())
        glyph = font.newGlyph("test")
        glyph.unicodes = [65]
        self.assertEqual(font.unicodeData[65], ["test", "A"])

if __name__ == "__main__":
    unittest.main()
