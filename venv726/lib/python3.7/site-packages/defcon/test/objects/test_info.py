import unittest
from defcon import Font, Info
from defcon.test.testTools import getTestFontPath


class InfoTest(unittest.TestCase):

    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)

    def setUp(self):
        self.font = Font()
        self.info = Info()

    def tearDown(self):
        del self.font

    def test_getParent(self):
        info = self.info
        self.assertIsNone(info.getParent())
        info = Info(self.font)
        self.assertEqual(info.getParent(), self.font)

    def test_font(self):
        info = self.info
        self.assertIsNone(info.font)
        info = Info(self.font)
        self.assertEqual(info.font, self.font)

    def test_endSelfNotificationObservation(self):
        font = self.font
        info = Info(font)
        self.assertIsNotNone(info.dispatcher)
        info.endSelfNotificationObservation()
        self.assertIsNone(info.dispatcher)
        self.assertIsNone(info.font)


if __name__ == "__main__":
    unittest.main()
