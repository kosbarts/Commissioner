import unittest
from defcon import Image, Font
from defcon.test.testTools import (
    getTestFontPath, makeTestFontCopy, tearDownTestFontCopy)


class ImageTest(unittest.TestCase):

    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)

    def test_transformation(self):
        i = Image()
        i.transformation = (1, 2, 3, 4, 5, 6)
        self.assertEqual(i.transformation, (1, 2, 3, 4, 5, 6))
        self.assertTrue(i.dirty)

    def test_color(self):
        i = Image()
        i.color = "1, 1, 1, 1"
        self.assertEqual(i.color, "1,1,1,1")
        self.assertTrue(i.dirty)

    def test_dirty(self):
        i = Image()
        self.assertFalse(i.dirty)

    def test_fileName(self):
        i = Image()
        i.fileName = "foo"
        self.assertEqual(i.fileName, "foo")
        self.assertTrue(i.dirty)

    def test_instance(self):
        i = Image(imageDict=dict(fileName="foo.png", xScale="1", xyScale="2",
                                 yxScale="3", yScale="4", xOffset="5",
                                 yOffset="6", color="0,0,0,0"))
        self.assertEqual(
            (i.fileName, i.transformation, i.color),
            ('foo.png', ('1', '2', '3', '4', '5', '6'), '0,0,0,0'))

    def test_read(self):
        font = Font(getTestFontPath())
        glyph = font.layers["Layer 1"]["A"]
        image = glyph.image
        self.assertEqual(image.fileName, 'image 1.png')
        self.assertEqual(image.color, '0.1,0.2,0.3,0.4')
        self.assertEqual(image.transformation, (0.5, 0, 0, 0.5, 0, 0))

    def test_write(self):
        path = makeTestFontCopy()
        font = Font(path)
        glyph = font.layers[None]["A"]
        glyph.image = glyph.instantiateImage()
        glyph.image.color = "1,1,1,1"
        glyph.image.fileName = "foo.png"
        glyph.image.transformation = (1, 2, 3, 4, 5, 6)
        font.save()
        font = Font(path)
        glyph = font.layers[None]["A"]
        self.assertEqual(sorted(glyph.image.items()),
                         [('color', '1,1,1,1'), ('fileName', 'foo.png'),
                          ('xOffset', 5), ('xScale', 1), ('xyScale', 2),
                          ('yOffset', 6), ('yScale', 4), ('yxScale', 3)])
        tearDownTestFontCopy()


if __name__ == "__main__":
    unittest.main()
