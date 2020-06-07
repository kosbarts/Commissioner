from __future__ import unicode_literals
import unittest
import os
from fontTools.ufoLib import UFOReader
from defcon import Font
from defcon.objects.imageSet import fileNameValidator
from defcon.test.testTools import (
    getTestFontPath, getTestFontCopyPath, makeTestFontCopy,
    tearDownTestFontCopy)

pngSignature = b"\x89PNG\r\n\x1a\n"


class ImageSetTest(unittest.TestCase):

    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)

    def tearDown(self):
        path = getTestFontCopyPath()
        if os.path.exists(path):
            tearDownTestFontCopy()

    def test_read(self):
        path = getTestFontPath()
        font = Font(path)
        self.assertEqual(sorted(font.images.fileNames),
                         ["image 1.png", "image 2.png"])

        data = font.images["image 1.png"]
        p = os.path.join(path, "images", "image 1.png")
        f = open(p, "rb")
        expected = f.read()
        f.close()
        self.assertEqual(data, expected)

        data = font.images["image 2.png"]
        p = os.path.join(path, "images", "image 2.png")
        f = open(p, "rb")
        expected = f.read()
        f.close()
        self.assertEqual(data, expected)

    def test_write(self):
        path = makeTestFontCopy()
        font = Font(path)
        font.images["image 3.png"] = font.images["image 1.png"]
        del font.images["image 1.png"]
        font.save()
        p = os.path.join(path, "images", "image 1.png")
        self.assertFalse(os.path.exists(p))
        p = os.path.join(path, "images", "image 2.png")
        self.assertTrue(os.path.exists(p))
        p = os.path.join(path, "images", "image 3.png")
        self.assertTrue(os.path.exists(p))
        tearDownTestFontCopy()

    def test_save_as(self):
        path = getTestFontPath()
        font = Font(path)
        saveAsPath = getTestFontCopyPath(path)
        font.save(saveAsPath)
        imagesDirectory = os.path.join(saveAsPath, "images")
        self.assertTrue(os.path.exists(imagesDirectory))
        imagePath = os.path.join(imagesDirectory, "image 1.png")
        self.assertTrue(os.path.exists(imagePath))
        imagePath = os.path.join(imagesDirectory, "image 2.png")
        self.assertTrue(os.path.exists(imagePath))
        tearDownTestFontCopy(saveAsPath)

    def test_unreferenced_images(self):
        path = getTestFontPath()
        font = Font(path)
        self.assertEqual(font.images.unreferencedFileNames, ["image 2.png"])

        path = makeTestFontCopy()
        font = Font(path)
        font.save(removeUnreferencedImages=True)
        p = os.path.join(path, "images", "image 1.png")
        self.assertTrue(os.path.exists(p))
        p = os.path.join(path, "images", "image 2.png")
        self.assertFalse(os.path.exists(p))
        tearDownTestFontCopy()

    def test_duplicate_image(self):
        path = getTestFontPath()
        font = Font(path)
        data = font.images["image 1.png"]
        self.assertEqual(font.images.findDuplicateImage(data), "image 1.png")
        imagePath = os.path.join(path, "images", "image 2.png")
        f = open(imagePath, "rb")
        data = f.read()
        f.close()
        self.assertEqual(font.images.findDuplicateImage(data), "image 2.png")

    def test_testExternalChanges_remove_in_memory_and_scan(self):
        path = makeTestFontCopy()
        font = Font(path)
        del font.images["image 1.png"]
        reader = UFOReader(path)
        self.assertEqual(font.images.testForExternalChanges(reader),
                         ([], [], []))
        tearDownTestFontCopy()

    def test_testExternalChanges_add_in_memory_and_scan(self):
        path = makeTestFontCopy()
        font = Font(path)
        font.images["image 3.png"] = pngSignature + b"blah"
        reader = UFOReader(path)
        self.assertEqual(font.images.testForExternalChanges(reader),
                         ([], [], []))
        tearDownTestFontCopy()

    def test_testExternalChanges_modify_in_memory_and_scan(self):
        path = makeTestFontCopy()
        font = Font(path)
        font.images["image 1.png"] = pngSignature + b"blah"
        reader = UFOReader(path)
        self.assertEqual(font.images.testForExternalChanges(reader),
                         ([], [], []))
        tearDownTestFontCopy()

    def test_testExternalChanges_remove_on_disk_and_scan(self):
        path = makeTestFontCopy()
        font = Font(path)
        os.remove(os.path.join(path, "images", "image 1.png"))
        reader = UFOReader(path)
        self.assertEqual(font.images.testForExternalChanges(reader),
                         ([], [], ["image 1.png"]))
        tearDownTestFontCopy()

    def test_testExternalChanges_add_on_disk_and_scan(self):
        import shutil
        path = makeTestFontCopy()
        font = Font(path)
        source = os.path.join(path, "images", "image 1.png")
        dest = os.path.join(path, "images", "image 3.png")
        shutil.copy(source, dest)
        reader = UFOReader(path)
        self.assertEqual(font.images.testForExternalChanges(reader),
                         ([], ["image 3.png"], []))
        tearDownTestFontCopy()

    def test_testExternalChanges_modify_on_disk_and_scan(self):
        path = makeTestFontCopy()
        font = Font(path)
        font.images["image 1.png"]  # image = font.images["image 1.png"]
        imagePath = os.path.join(path, "images", "image 1.png")
        f = open(imagePath, "rb")
        data = f.read()
        f.close()
        f = open(imagePath, "wb")
        f.write(data + b"blah")
        f.close()
        reader = UFOReader(path)
        self.assertEqual(font.images.testForExternalChanges(reader),
                         (["image 1.png"], [], []))
        tearDownTestFontCopy()

    def test_reloadImages(self):
        path = makeTestFontCopy()
        font = Font(path)
        image = font.images["image 1.png"]
        imagePath = os.path.join(path, "images", "image 1.png")
        newImageData = pngSignature + b"blah"
        f = open(imagePath, "wb")
        f.write(newImageData)
        f.close()
        font.images.reloadImages(["image 1.png"])
        image = font.images["image 1.png"]
        self.assertEqual(image, newImageData)
        tearDownTestFontCopy()

    def test_fileNameValidator(self):
        self.assertTrue(fileNameValidator('a'))
        self.assertTrue(fileNameValidator('A_'))
        self.assertTrue(fileNameValidator('A_E_'))
        self.assertTrue(fileNameValidator('A_e'))
        self.assertTrue(fileNameValidator('ae'))
        self.assertTrue(fileNameValidator('aE_'))
        self.assertTrue(fileNameValidator('a.alt'))
        self.assertTrue(fileNameValidator('A_.alt'))
        self.assertTrue(fileNameValidator('A_.A_lt'))
        self.assertTrue(fileNameValidator('A_.aL_t'))
        self.assertTrue(fileNameValidator('A_.alT_'))
        self.assertTrue(fileNameValidator('T__H_'))
        self.assertTrue(fileNameValidator('T__h'))
        self.assertTrue(fileNameValidator('t_h'))
        self.assertTrue(fileNameValidator('F__F__I_'))
        self.assertTrue(fileNameValidator('f_f_i'))
        self.assertTrue(fileNameValidator('A_acute_V_.swash'))
        self.assertTrue(fileNameValidator('_notdef'))
        self.assertTrue(fileNameValidator('_con'))
        self.assertTrue(fileNameValidator('C_O_N_'))
        self.assertTrue(fileNameValidator('_con.alt'))
        self.assertTrue(fileNameValidator('alt._con'))
        self.assertTrue(fileNameValidator('A_bC_dE_f'))

        self.assertFalse(fileNameValidator(b'A'))
        self.assertFalse(fileNameValidator('A'*256))
        self.assertFalse(fileNameValidator('A'))
        self.assertFalse(fileNameValidator('con'))
        self.assertFalse(fileNameValidator('a/alt'))

if __name__ == "__main__":
    unittest.main()
