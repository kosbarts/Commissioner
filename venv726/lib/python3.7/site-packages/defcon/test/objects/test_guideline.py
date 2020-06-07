import unittest
from defcon import Guideline


class GuidelineTest(unittest.TestCase):

    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)

    def test_x(self):
        g = Guideline()
        g.x = 100
        self.assertEqual(g.x, 100)
        self.assertTrue(g.dirty)
        g.x = None
        self.assertIsNone(g.x)
        self.assertTrue(g.dirty)

    def test_y(self):
        g = Guideline()
        g.y = 100
        self.assertEqual(g.y, 100)
        self.assertTrue(g.dirty)
        g.y = None
        self.assertIsNone(g.y)
        self.assertTrue(g.dirty)

    def test_angle(self):
        g = Guideline()
        g.angle = 100
        self.assertEqual(g.angle, 100)
        self.assertTrue(g.dirty)
        g.angle = None
        self.assertIsNone(g.angle)
        self.assertTrue(g.dirty)

    def test_name(self):
        g = Guideline()
        g.name = "foo"
        self.assertEqual(g.name, "foo")
        self.assertTrue(g.dirty)
        g.name = None
        self.assertIsNone(g.name)
        self.assertTrue(g.dirty)

    def test_color(self):
        g = Guideline()
        g.color = "1,1,1,1"
        self.assertEqual(g.color, "1,1,1,1")
        self.assertTrue(g.dirty)
        g.color = None
        self.assertIsNone(g.color)
        self.assertTrue(g.dirty)

    def test_identifier(self):
        g = Guideline()
        self.assertIsNone(g.identifier)
        g.generateIdentifier()
        self.assertIsNotNone(g.identifier)
        self.assertTrue(g.dirty)

    def test_dirty(self):
        g = Guideline()
        self.assertFalse(g.dirty)

    def test_instance(self):
        g = Guideline(guidelineDict=dict(x=1, y=2, angle=3, name="4",
                                         identifier="5", color="1,1,1,1"))
        self.assertEqual((g.x, g.y, g.angle, g.name, g.identifier, g.color),
                         (1, 2, 3, '4', '5', '1,1,1,1'))


if __name__ == "__main__":
    unittest.main()
