import unittest
from defcon import Font, Info, Kerning, Groups
from defcon.objects.base import setUfoLibReadValidate, setUfoLibWriteValidate
from defcon.test.testTools import getTestFontPath


class UFOReadWriteValidateTest(unittest.TestCase):

    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)

    def test_ufoLibReadValidate_defaults(self):
        font = Font()
        self.assertTrue(font.ufoLibReadValidate)
        self.assertTrue(font.ufoLibWriteValidate)
        self.assertTrue(font.info.ufoLibReadValidate)
        self.assertTrue(font.info.ufoLibWriteValidate)

    def test_ufoLibReadValidate_settingDefaults(self):
        setUfoLibReadValidate(False)
        setUfoLibWriteValidate(False)
        font = Font()
        self.assertFalse(font.ufoLibReadValidate)
        self.assertFalse(font.ufoLibWriteValidate)
        self.assertFalse(font.info.ufoLibReadValidate)
        self.assertFalse(font.info.ufoLibWriteValidate)

        setUfoLibReadValidate(False)
        setUfoLibWriteValidate(True)
        font = Font()
        self.assertFalse(font.ufoLibReadValidate)
        self.assertTrue(font.ufoLibWriteValidate)
        self.assertFalse(font.info.ufoLibReadValidate)
        self.assertTrue(font.info.ufoLibWriteValidate)

        setUfoLibReadValidate(True)
        setUfoLibWriteValidate(False)
        font = Font()
        self.assertTrue(font.ufoLibReadValidate)
        self.assertFalse(font.ufoLibWriteValidate)
        self.assertTrue(font.info.ufoLibReadValidate)
        self.assertFalse(font.info.ufoLibWriteValidate)

    def test_customClasses(self):

        class CustomInfo(Info):

            ufoLibReadValidate = False
            ufoLibWriteValidate = False

        class CustomKerning(Kerning):

            ufoLibReadValidate = True
            ufoLibWriteValidate = False

        font = Font(infoClass=CustomInfo, kerningClass=CustomKerning)
        self.assertTrue(font.ufoLibReadValidate)
        self.assertTrue(font.ufoLibWriteValidate)
        self.assertFalse(font.info.ufoLibReadValidate)
        self.assertFalse(font.info.ufoLibWriteValidate)
        self.assertTrue(font.kerning.ufoLibReadValidate)
        self.assertFalse(font.kerning.ufoLibWriteValidate)


if __name__ == "__main__":
    unittest.main()
