import unittest
import glob
import os
from defcon import Font, Glyph, Color, Component, Anchor, Guideline
from defcon.test.testTools import (
    getTestFontPath, makeTestFontCopy, getTestFontCopyPath,
    tearDownTestFontCopy)

try:
    from plistlib import load, dump
except ImportError:
    from plistlib import readPlist as load, writePlist as dump


class LayerTest(unittest.TestCase):

    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)

    def test_set_parent_data_in_glyph(self):
        font = Font(getTestFontPath())
        layer = font.layers["public.default"]
        glyph = layer["A"]
        self.assertEqual(id(glyph.getParent()), id(font))

    def test_newGlyph(self):
        font = Font(getTestFontPath())
        layer = font.layers["public.default"]
        layer.newGlyph("NewGlyphTest")
        glyph = layer["NewGlyphTest"]
        self.assertEqual(glyph.name, "NewGlyphTest")
        self.assertTrue(glyph.dirty)
        self.assertTrue(font.dirty)
        self.assertEqual(sorted(layer.keys()), ["A", "B", "C", "NewGlyphTest"])

    def test_insertGlyph(self):
        font = Font()
        layer = font.layers[None]
        source = Glyph()
        source.unicodes = [1, 2]
        source.name = "a"
        dest = layer.insertGlyph(source, name="nota")
        self.assertNotEqual(dest, source)
        self.assertEqual(dest.name, "nota")
        self.assertEqual(list(layer.unicodeData.items()),
                         [(1, ["nota"]), (2, ["nota"])])
        source = Glyph()
        source.unicodes = [3]
        source.name = "b"
        dest = layer.insertGlyph(source)
        self.assertNotEqual(dest, source)
        self.assertEqual(dest.name, "b")
        self.assertEqual(list(layer.unicodeData.items()),
                         [(1, ["nota"]), (2, ["nota"]), (3, ["b"])])

    def test_iter(self):
        font = Font(getTestFontPath())
        layer = font.layers["public.default"]
        names = [glyph.name for glyph in layer]
        self.assertEqual(sorted(names), ["A", "B", "C"])
        names = []
        for glyph1 in layer:
            for glyph2 in layer:
                names.append((glyph1.name, glyph2.name))
        self.assertEqual(sorted(names),
                         [("A", "A"), ("A", "B"), ("A", "C"),
                          ("B", "A"), ("B", "B"), ("B", "C"),
                          ("C", "A"), ("C", "B"), ("C", "C")])

    def test_getitem(self):
        font = Font(getTestFontPath())
        layer = font.layers["public.default"]
        self.assertEqual(layer["A"].name, "A")
        self.assertEqual(layer["B"].name, "B")
        with self.assertRaises(KeyError):
            layer["NotInFont"]

    def test_len(self):
        font = Font(getTestFontPath())
        layer = font.layers["public.default"]
        self.assertEqual(len(layer), 3)

        font = Font()
        layer = font.layers["public.default"]
        self.assertEqual(len(layer), 0)

    def test_contains(self):
        font = Font(getTestFontPath())
        layer = font.layers["public.default"]
        self.assertTrue("A" in layer)
        self.assertFalse("NotInFont" in layer)

        font = Font()
        layer = font.layers["public.default"]
        self.assertFalse("A" in layer)

    def test_keys(self):
        font = Font(getTestFontPath())
        layer = font.layers["public.default"]
        self.assertEqual(sorted(layer.keys()), ["A", "B", "C"])
        del layer["A"]
        self.assertEqual(sorted(layer.keys()), ["B", "C"])
        layer.newGlyph("A")
        self.assertEqual(sorted(layer.keys()), ["A", "B", "C"])

        font = Font()
        layer = font.layers["public.default"]
        self.assertEqual(layer.keys(), set())
        layer.newGlyph("A")
        self.assertEqual(layer.keys(), {"A"})

    def test_color(self):
        font = Font(getTestFontPath())
        layer = font.layers["Layer 1"]
        self.assertIsInstance(layer.color, Color)
        self.assertEqual(str(layer.color), "0.1,0.2,0.3,0.4")
        layer.color = "0.5,0.5,0.5,0.5"
        self.assertIsInstance(layer.color, Color)
        layer.color = (.5, .5, .5, .5)
        self.assertIsInstance(layer.color, Color)
        self.assertEqual(str(layer.color), "0.5,0.5,0.5,0.5")

    def test_glyphsWithOutlines(self):
        font = Font(getTestFontPath())
        layer = font.layers["public.default"]
        self.assertEqual(sorted(layer.glyphsWithOutlines), ["A", "B"])
        font = Font(getTestFontPath())
        layer = font.layers["public.default"]
        for glyph in layer:
            pass
        self.assertEqual(sorted(layer.glyphsWithOutlines), ["A", "B"])

    def test_componentReferences(self):
        font = Font(getTestFontPath())
        layer = font.layers["public.default"]
        self.assertEqual(sorted(layer.componentReferences.items()),
                         [("A", set(["C"])), ("B", set(["C"]))])
        layer["C"]
        self.assertEqual(sorted(layer.componentReferences.items()),
                         [("A", set(["C"])), ("B", set(["C"]))])

    def test_imageReferences(self):
        font = Font(getTestFontPath())
        layer = font.layers["Layer 1"]
        self.assertEqual(layer.imageReferences, {"image 1.png": ["A"]})
        layer.newGlyph("B")
        glyph = layer["B"]
        glyph.image = dict(fileName="test", xScale=1, xyScale=1,
                           yxScale=1, yScale=1, xOffset=0, yOffset=0,
                           color=None)
        self.assertEqual(sorted(layer.imageReferences.items()),
                         [("image 1.png", ["A"]), ("test", ["B"])])

    def test_bounds(self):
        font = Font(getTestFontPath())
        layer = font.layers["public.default"]
        self.assertEqual(layer.bounds, (0, 0, 700, 700))

    def test_controlPointBounds(self):
        font = Font(getTestFontPath())
        layer = font.layers["public.default"]
        self.assertEqual(layer.controlPointBounds, (0, 0, 700, 700))

    def test_lib(self):
        font = Font(getTestFontPath())
        layer = font.layers["Layer 1"]
        self.assertEqual(layer.lib, {"com.typesupply.defcon.test": "1 2 3"})
        layer.lib.dirty = False
        layer.lib["blah"] = "abc"
        self.assertEqual(layer.lib["blah"], "abc")
        self.assertTrue(layer.lib.dirty)

    def test_testForExternalChanges(self):
        path = getTestFontPath("TestExternalEditing.ufo")
        path = makeTestFontCopy(path)
        try:
            font = Font(path)

            self.assertEqual(font.layers[None].testForExternalChanges(),
                             ([], [], []))

            # make a simple change to a glyph
            g = font.layers[None]["A"]
            path = os.path.join(font.path, "glyphs", "A_.glif")
            f = open(path, "r")
            t = f.read()
            f.close()
            t += " "
            f = open(path, "w")
            f.write(t)
            f.close()
            os.utime(path,
                     (g._dataOnDiskTimeStamp + 1, g._dataOnDiskTimeStamp + 1))
            self.assertEqual(font.layers[None].testForExternalChanges(),
                             (["A"], [], []))

            # save the glyph and test again
            font["A"].dirty = True
            font.save()
            self.assertEqual(font.layers[None].testForExternalChanges(),
                             ([], [], []))

            # add a glyph
            path = os.path.join(font.path, "glyphs", "A_.glif")
            f = open(path, "r")
            t = f.read()
            f.close()
            t = t.replace('<glyph name="A" format="1">',
                          '<glyph name="XYZ" format="1">')
            path = os.path.join(font.path, "glyphs", "XYZ.glif")
            f = open(path, "w")
            f.write(t)
            f.close()
            path = os.path.join(font.path, "glyphs", "contents.plist")
            with open(path, "rb") as f:
                plist = load(f)
            savePlist = dict(plist)
            plist["XYZ"] = "XYZ.glif"
            with open(path, "wb") as f:
                dump(plist, f)
            self.assertEqual(font.layers[None].testForExternalChanges(),
                             ([], ["XYZ"], []))
            path = font.path

            # delete a glyph
            font = Font(path)
            g = font["XYZ"]
            path = os.path.join(font.path, "glyphs", "contents.plist")
            with open(path, "wb") as f:
                dump(savePlist, f)
            path = os.path.join(font.path, "glyphs", "XYZ.glif")
            os.remove(path)
            self.assertEqual(font.layers[None].testForExternalChanges(),
                             ([], [], ["XYZ"]))
        finally:
            tearDownTestFontCopy(font.path)

    def test_reloadGlyphs(self):
        path = getTestFontPath("TestExternalEditing.ufo")
        font = Font(path)
        glyph = font.layers[None]["A"]

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
        font.layers[None].reloadGlyphs(["A"])
        self.assertEqual(glyph.width, 701)
        self.assertEqual(len(glyph), 2)

        t = t.replace('<advance width="701"/>', '<advance width="700"/>')
        f = open(path, "w")
        f.write(t)
        f.close()

    def test_glyph_name_change(self):
        font = Font(getTestFontPath())
        layer = font.layers["public.default"]
        glyph = layer["A"]
        glyph.name = "NameChangeTest"
        self.assertEqual(sorted(layer.keys()), ["B", "C", "NameChangeTest"])
        self.assertTrue(layer.dirty)

    def test_glyph_unicodes_changed(self):
        font = Font(getTestFontPath())
        layer = font.layers["public.default"]
        glyph = layer["A"]
        glyph.unicodes = [123, 456]
        self.assertEqual(layer.unicodeData[123], ["A"])
        self.assertEqual(layer.unicodeData[456], ["A"])
        self.assertEqual(layer.unicodeData[66], ["B"])
        self.assertIsNone(layer.unicodeData.get(65))

        font = Font(getTestFontPath())
        layer = font.layers["public.default"]
        layer.newGlyph("test")
        glyph = layer["test"]
        glyph.unicodes = [65]
        self.assertEqual(layer.unicodeData[65], ["test", "A"])

    def test_glyph_dispatcher_loaded(self):
        font = Font(getTestFontPath())
        glyph = font["A"]
        self.assertIsNotNone(glyph.dispatcher)
        self.assertEqual(glyph.dispatcher, font.dispatcher)
        contour = glyph[0]
        self.assertEqual(contour.getParent(), glyph)
        self.assertEqual(contour.dispatcher, font.dispatcher)
        anchor = glyph.anchors[0]
        self.assertEqual(anchor.getParent(), glyph)
        self.assertEqual(anchor.dispatcher, font.dispatcher)
        glyph = font["C"]
        component = glyph.components[0]
        self.assertEqual(component.getParent(), glyph)
        self.assertEqual(component.dispatcher, font.dispatcher)
        glyph = font.layers["Layer 1"]["A"]
        guideline = glyph.guidelines[0]
        self.assertEqual(guideline.getParent(), glyph)
        self.assertEqual(guideline.dispatcher, font.dispatcher)

    def test_glyph_dispatcher_new(self):
        font = Font()
        font.newGlyph("A")
        glyph = font["A"]
        pen = glyph.getPointPen()
        pen.beginPath()
        pen.addPoint((0, 0), segmentType="line")
        pen.addPoint((0, 100), segmentType="line")
        pen.addPoint((100, 100), segmentType="line")
        pen.addPoint((100, 0), segmentType="line")
        pen.endPath()
        contour = glyph[0]
        self.assertEqual(contour.getParent(), glyph)
        self.assertEqual(contour.dispatcher, font.dispatcher)
        component = Component()
        glyph.appendComponent(component)
        self.assertEqual(component.getParent(), glyph)
        self.assertEqual(component.dispatcher, font.dispatcher)
        anchor = Anchor()
        glyph.appendAnchor(anchor)
        self.assertEqual(anchor.getParent(), glyph)
        self.assertEqual(anchor.dispatcher, font.dispatcher)
        guideline = Guideline()
        glyph.appendGuideline(guideline)
        self.assertEqual(guideline.getParent(), glyph)
        self.assertEqual(guideline.dispatcher, font.dispatcher)

    def test_glyph_dispatcher_inserted(self):
        font = Font()
        font.newGlyph("A")
        glyph = font["A"]
        pen = glyph.getPointPen()
        pen.beginPath()
        pen.addPoint((0, 0), segmentType="line")
        pen.addPoint((0, 100), segmentType="line")
        pen.addPoint((100, 100), segmentType="line")
        pen.addPoint((100, 0), segmentType="line")
        pen.endPath()
        contour = glyph[0]
        component = Component()
        glyph.appendComponent(component)
        anchor = Anchor()
        glyph.appendAnchor(anchor)
        guideline = Guideline()
        glyph.appendGuideline(guideline)
        sourceGlyph = glyph
        newFont = Font()
        insertedGlyph = newFont.insertGlyph(sourceGlyph)
        contour = insertedGlyph[0]
        self.assertTrue(contour.getParent(), insertedGlyph)
        self.assertTrue(contour.dispatcher, newFont.dispatcher)
        component = insertedGlyph.components[0]
        self.assertTrue(component.getParent(), insertedGlyph)
        self.assertTrue(component.dispatcher, newFont.dispatcher)
        anchor = insertedGlyph.anchors[0]
        self.assertTrue(anchor.getParent(), insertedGlyph)
        self.assertTrue(anchor.dispatcher, newFont.dispatcher)
        guideline = insertedGlyph.guidelines[0]
        self.assertTrue(guideline.getParent(), insertedGlyph)
        self.assertTrue(guideline.dispatcher, newFont.dispatcher)


class LayerWithTestFontCopyTest(unittest.TestCase):

    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)

    def setUp(self):
        self.path = makeTestFontCopy()

    def tearDown(self):
        if os.path.exists(getTestFontCopyPath()):
            tearDownTestFontCopy()

    def test_delitem(self):
        path = self.path
        font = Font(path)
        layer = font.layers["public.default"]
        # glyph = layer["A"]
        self.assertTrue("A" in layer)
        del layer["A"]
        self.assertFalse("A" in layer)
        self.assertTrue(layer.dirty)
        layer.newGlyph("NewGlyphTest")
        del layer["NewGlyphTest"]
        self.assertEqual(sorted(layer.keys()), ["B", "C"])
        self.assertEqual(len(layer), 2)
        self.assertFalse("A" in layer)
        font.save()
        fileNames = glob.glob(os.path.join(path, "glyphs", "*.glif"))
        fileNames = [os.path.basename(fileName) for fileName in fileNames]
        self.assertEqual(sorted(fileNames), ["B_.glif", "C_.glif"])
        with self.assertRaises(KeyError):
            del layer["NotInFont"]

    def test_delitem_glyph_not_dirty(self):
        path = self.path
        font = Font(path)
        layer = font.layers["public.default"]
        # glyph = layer["A"]
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
        del layer["A"]
        font.save()
        self.assertFalse(os.path.exists(glyphPath))

    def test_delitem_glyph_dirty(self):
        path = self.path
        font = Font(path)
        layer = font.layers["public.default"]
        glyph = layer["A"]
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
        del layer["A"]
        font.save()
        self.assertFalse(os.path.exists(glyphPath))


if __name__ == "__main__":
    unittest.main()
