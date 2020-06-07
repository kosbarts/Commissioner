import unittest
import os
import shutil
from fontTools.ufoLib import UFOReader
from defcon import Font
from defcon.test.testTools import (
    getTestFontPath, getTestFontCopyPath, makeTestFontCopy,
    tearDownTestFontCopy)


try:
    from plistlib import load, dump
except ImportError:
    from plistlib import readPlist as load, writePlist as dump


class LayerTest(unittest.TestCase):

    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)
        if not hasattr(self, "assertRaisesRegex"):
            self.assertRaisesRegex = self.assertRaisesRegexp

    def tearDown(self):
        if os.path.exists(getTestFontCopyPath()):
            tearDownTestFontCopy()

    def test_set_parent_data_in_layer(self):
        font = Font(getTestFontPath())
        layers = font.layers
        layer = font.layers[None]
        self.assertEqual(id(layer.getParent()), id(layers))

    def test_defaultLayer(self):
        font = Font(getTestFontPath())
        layers = font.layers
        layer = layers.defaultLayer
        self.assertEqual(layer, layers["public.default"])
        layer = layers["Layer 1"]
        layers.defaultLayer = layer
        self.assertEqual(layer, layers.defaultLayer)

    def test_layerOrder(self):
        font = Font(getTestFontPath())
        layers = font.layers
        self.assertEqual(layers.layerOrder,
                         ["public.default", "public.background", "Layer 1"])
        self.assertEqual(list(reversed(layers.layerOrder)),
                         ["Layer 1", "public.background", "public.default"])

    def test_newLayer(self):
        font = Font(getTestFontPath())
        layers = font.layers
        layer = font.newLayer("Test")
        self.assertTrue(layer.dirty)
        self.assertTrue(layers.dirty)
        self.assertTrue(font.dirty)
        self.assertEqual(
            layers.layerOrder,
            ["public.default", "public.background", "Layer 1", "Test"])

    def test_iter(self):
        font = Font(getTestFontPath())
        layers = font.layers
        self.assertEqual([layer.name for layer in layers],
                         ["public.default", "public.background", "Layer 1"])

    def test_getitem(self):
        font = Font(getTestFontPath())
        layers = font.layers
        self.assertEqual(layers["public.default"].name, "public.default")

    def test_delitem(self):
        font = Font(makeTestFontCopy())
        path = os.path.join(font.path, "glyphs.public.background")
        self.assertTrue(os.path.exists(path))
        layers = font.layers
        del layers["public.background"]
        layers.dirty = True
        self.assertEqual(layers.layerOrder, ["public.default", "Layer 1"])
        self.assertNotIn("public.background", layers)

        self.assertEqual(len(layers), 2)
        with self.assertRaisesRegex(KeyError, "public.background"):
            layers["public.background"]
        font.save()
        path = os.path.join(font.path, "glyphs.public.background")
        self.assertFalse(os.path.exists(path))
        tearDownTestFontCopy()

        font = Font(makeTestFontCopy())
        path = os.path.join(font.path, "glyphs.public.background")
        del font.layers["public.background"]
        layer = font.newLayer("public.background")
        layer.newGlyph("B")
        font.save()
        self.assertFalse(os.path.exists(os.path.join(path, "A_.glif")))
        self.assertTrue(os.path.exists(os.path.join(path, "B_.glif")))

    def test_len(self):
        font = Font(getTestFontPath())
        layers = font.layers
        self.assertEqual(len(layers), 3)

        font = Font()
        layers = font.layers
        self.assertEqual(len(layers), 1)

    def test_contains(self):
        font = Font(getTestFontPath())
        layers = font.layers
        self.assertIn("public.default", layers)
        self.assertNotIn("NotInFont", layers)

    def test_testForExternalChanges(self):
        path = getTestFontPath("TestExternalEditing.ufo")
        path = makeTestFontCopy(path)
        font = Font(path)
        reader = UFOReader(path)
        self.assertEqual(font.layers.testForExternalChanges(reader),
                         {"deleted": [], "added": [], "modified": {},
                          "defaultLayer": False, "order": False})
        tearDownTestFontCopy(font.path)

    def test_testForExternalChanges_layerinfo(self):
        # layerinfo.plist
        path = getTestFontPath("TestExternalEditing.ufo")
        path = makeTestFontCopy(path)
        font = Font(path)
        reader = UFOReader(path)
        p = os.path.join(path, "glyphs", "layerinfo.plist")
        data = {"lib": {}}
        data["lib"]["testForExternalChanges.test"] = 1
        with open(p, "wb") as f:
            dump(data, f)
        self.assertTrue(
            font.layers.testForExternalChanges(reader)
            ["modified"]["public.default"]["info"])
        tearDownTestFontCopy(font.path)

    def test_testForExternalChanges_add_a_layer(self):
        path = getTestFontPath("TestExternalEditing.ufo")
        path = makeTestFontCopy(path)
        font = Font(path)
        shutil.copytree(os.path.join(path, "glyphs"),
                        os.path.join(path, "glyphs.test"))
        with open(os.path.join(path, "layercontents.plist"), "rb") as f:
            contents = load(f)
        contents.append(("test", "glyphs.test"))
        with open(os.path.join(path, "layercontents.plist"), "wb") as f:
            dump(contents, f)
        reader = UFOReader(path)
        self.assertEqual(font.layers.testForExternalChanges(reader)["added"],
                         ["test"])
        tearDownTestFontCopy(font.path)

    def test_testForExternalChanges_remove_a_layer(self):
        path = getTestFontPath("TestExternalEditing.ufo")
        path = makeTestFontCopy(path)
        shutil.copytree(os.path.join(path, "glyphs"),
                        os.path.join(path, "glyphs.test"))
        with open(os.path.join(path, "layercontents.plist"), "rb") as f:
            contents = load(f)
        contents.append(("test", "glyphs.test"))
        with open(os.path.join(path, "layercontents.plist"), "wb") as f:
            dump(contents, f)
        font = Font(path)
        shutil.rmtree(os.path.join(path, "glyphs.test"))
        with open(os.path.join(path, "layercontents.plist"), "rb") as f:
            contents = load(f)
        contents.pop(1)  # n = contents.pop(1)
        with open(os.path.join(path, "layercontents.plist"), "wb") as f:
            dump(contents, f)
        reader = UFOReader(path)
        self.assertEqual(font.layers.testForExternalChanges(reader)["deleted"],
                         ["test"])
        tearDownTestFontCopy(font.path)

    def test_testForExternalChanges_change_layer_order(self):
        path = getTestFontPath("TestExternalEditing.ufo")
        path = makeTestFontCopy(path)
        shutil.copytree(os.path.join(path, "glyphs"),
                        os.path.join(path, "glyphs.test"))
        with open(os.path.join(path, "layercontents.plist"), "rb") as f:
            contents = load(f)
        contents.append(("test", "glyphs.test"))
        with open(os.path.join(path, "layercontents.plist"), "wb") as f:
            dump(contents, f)
        font = Font(path)
        with open(os.path.join(path, "layercontents.plist"), "rb") as f:
            contents = load(f)
        contents.reverse()
        with open(os.path.join(path, "layercontents.plist"), "wb") as f:
            dump(contents, f)
        reader = UFOReader(path)
        self.assertEqual(font.layers.testForExternalChanges(reader),
                         {"deleted": [], "added": [], "modified": {},
                          "defaultLayer": False, "order": True})
        tearDownTestFontCopy(font.path)

    def test_testForExternalChanges_change_default_layer(self):
        path = getTestFontPath("TestExternalEditing.ufo")
        path = makeTestFontCopy(path)
        shutil.copytree(os.path.join(path, "glyphs"),
                        os.path.join(path, "glyphs.test"))
        contents = [("foo", "glyphs"), ("test", "glyphs.test")]
        with open(os.path.join(path, "layercontents.plist"), "wb") as f:
            dump(contents, f)
        font = Font(path)
        contents = [("test", "glyphs"), ("foo", "glyphs.test")]
        contents.reverse()
        with open(os.path.join(path, "layercontents.plist"), "wb") as f:
            dump(contents, f)
        reader = UFOReader(path)
        self.assertEqual(font.layers.testForExternalChanges(reader),
                         {"deleted": [], "added": [], "modified": {},
                          "defaultLayer": True, "order": False})
        tearDownTestFontCopy(font.path)

    def test_reloadLayers_layerinfo(self):
        path = getTestFontPath("TestExternalEditing.ufo")
        path = makeTestFontCopy(path)
        font = Font(path)
        p = os.path.join(path, "glyphs", "layerinfo.plist")
        data = {"lib": {}}
        data["lib"]["testForExternalChanges.test"] = 1
        with open(p, "wb") as f:
            dump(data, f)
        font.reloadLayers(dict(layers={"public.default": dict(info=True)}))
        self.assertEqual(font.layers["public.default"].lib,
                         {"testForExternalChanges.test": 1})
        tearDownTestFontCopy(font.path)

    def test_reloadLayers_add_a_layer(self):
        path = getTestFontPath("TestExternalEditing.ufo")
        path = makeTestFontCopy(path)
        font = Font(path)
        shutil.copytree(os.path.join(path, "glyphs"),
                        os.path.join(path, "glyphs.test"))
        with open(os.path.join(path, "layercontents.plist"), "rb") as f:
            contents = load(f)
        contents.append(("test", "glyphs.test"))
        with open(os.path.join(path, "layercontents.plist"), "wb") as f:
            dump(contents, f)
        font.reloadLayers(dict(layers={"test": {}}))
        self.assertEqual(font.layers.layerOrder, ["public.default", "test"])
        tearDownTestFontCopy(font.path)

    def test_reloadLayers_change_layer_order(self):
        path = getTestFontPath("TestExternalEditing.ufo")
        path = makeTestFontCopy(path)
        shutil.copytree(os.path.join(path, "glyphs"),
                        os.path.join(path, "glyphs.test"))
        with open(os.path.join(path, "layercontents.plist"), "rb") as f:
            contents = load(f)
        contents.append(("test", "glyphs.test"))
        with open(os.path.join(path, "layercontents.plist"), "wb") as f:
            dump(contents, f)
        font = Font(path)
        with open(os.path.join(path, "layercontents.plist"), "rb") as f:
            contents = load(f)
        contents.reverse()
        with open(os.path.join(path, "layercontents.plist"), "wb") as f:
            dump(contents, f)
        font.reloadLayers(dict(order=True))
        self.assertEqual(font.layers.layerOrder, ["test", "public.default"])
        tearDownTestFontCopy(font.path)

    def test_reloadLayers_change_default_layer(self):
        path = getTestFontPath("TestExternalEditing.ufo")
        path = makeTestFontCopy(path)
        shutil.copytree(os.path.join(path, "glyphs"),
                        os.path.join(path, "glyphs.test"))
        contents = [("foo", "glyphs"), ("test", "glyphs.test")]
        with open(os.path.join(path, "layercontents.plist"), "wb") as f:
            dump(contents, f)
        font = Font(path)
        contents = [("test", "glyphs"), ("foo", "glyphs.test")]
        contents.reverse()
        with open(os.path.join(path, "layercontents.plist"), "wb") as f:
            dump(contents, f)
        font.reloadLayers(dict(default=True))
        self.assertEqual(font.layers.defaultLayer.name, "test")
        tearDownTestFontCopy(font.path)

    def test_layer_info(self):
        # open and change some values
        font = Font(makeTestFontCopy())
        layer = font.layers["Layer 1"]
        self.assertEqual(layer.color,
                         "0.1,0.2,0.3,0.4")
        layer.color = "0.5,0.5,0.5,0.5"
        self.assertEqual(layer.lib,
                         {"com.typesupply.defcon.test": "1 2 3"})
        layer.lib["foo"] = "bar"
        font.save()
        path = font.path

        # reopen and check the changes
        font = Font(path)
        layer = font.layers["Layer 1"]
        self.assertEqual(layer.color,
                         "0.5,0.5,0.5,0.5")
        self.assertEqual(sorted(layer.lib.items()),
                         [("com.typesupply.defcon.test", "1 2 3"),
                          ("foo", "bar")])
        tearDownTestFontCopy()

    def test_name_change(self):
        font = Font(getTestFontPath())
        layers = font.layers
        layer = layers["public.background"]
        layers.dirty = False
        layer.dirty = False
        layer.name = "Name Change Test"
        self.assertEqual(layers.layerOrder,
                         ["public.default", "Name Change Test", "Layer 1"])
        self.assertTrue(layer.dirty)

    def test_rename_default_layer(self):
        # https://github.com/unified-font-object/ufoLib/issues/123
        path = getTestFontCopyPath()
        font = Font()
        font.save(path)
        font.layers.defaultLayer.name = "somethingElse"
        font.save()
        self.assertEqual(Font(path).layers.defaultLayer.name, "somethingElse")


if __name__ == "__main__":
    unittest.main()
