import unittest
from defcon.objects.anchor import Anchor
from defcon.objects.font import Font
from defcon.test.testTools import NotificationTestObserver


class AnchorTest(unittest.TestCase):

    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)

    def setUp(self):
        self.font = Font()
        self.glyph = self.font.newGlyph("A")
        self.anchor = Anchor()

    def tearDown(self):
        del self.anchor
        del self.glyph
        del self.font

    def test_dirty(self):
        self.assertFalse(self.anchor.dirty)
        notdirty = not self.anchor.dirty
        self.anchor.dirty = notdirty
        self.assertEqual(self.anchor.dirty, notdirty)
        self.anchor.dirty = not notdirty
        self.assertNotEqual(self.anchor.dirty, notdirty)

    def test_getParent(self):
        self.assertIsNone(self.anchor.getParent())
        self.anchor = Anchor(self.glyph)
        self.assertEqual(self.anchor.getParent(), self.glyph)

    def test_font(self):
        self.assertIsNone(self.anchor.font)
        self.anchor = Anchor(self.glyph)
        self.assertEqual(self.anchor.font, self.font)
        with self.assertRaises(AttributeError):
            self.anchor.font = "foo"

    def test_layerSet(self):
        self.assertIsNone(self.anchor.layerSet)
        self.anchor = Anchor(self.glyph)
        self.assertEqual(self.anchor.layerSet, self.glyph.layerSet)
        self.assertIsNotNone(self.anchor.layerSet)
        with self.assertRaises(AttributeError):
            self.anchor.layerSet = "foo"

    def test_layer(self):
        self.assertIsNone(self.anchor.layer)
        self.anchor = Anchor(self.glyph)
        self.assertEqual(self.anchor.layer, self.glyph.layer)
        self.assertIsNotNone(self.anchor.layer)
        with self.assertRaises(AttributeError):
            self.anchor.layer = "foo"

    def test_x(self):
        self.anchor.x = 100
        self.assertEqual(self.anchor.x, 100)
        self.assertTrue(self.anchor.dirty)

    def test_y(self):
        self.anchor.y = 100
        self.assertEqual(self.anchor.y, 100)
        self.assertTrue(self.anchor.dirty)

    def test_name(self):
        self.anchor.name = "foo"
        self.assertEqual(self.anchor.name, "foo")
        self.assertTrue(self.anchor.dirty)
        self.anchor.name = None
        self.assertIsNone(self.anchor.name)
        self.assertTrue(self.anchor.dirty)

    def test_color(self):
        self.anchor.color = "1,1,1,1"
        self.assertEqual(self.anchor.color, "1,1,1,1")
        self.assertTrue(self.anchor.dirty)

    def test_identifiers(self):
        anchor = Anchor(self.glyph)
        self.assertEqual(anchor.identifiers, self.glyph.identifiers)

    def test_identifier(self):
        self.assertIsNone(self.anchor.identifier)
        identifier = self.anchor.generateIdentifier()
        self.assertEqual(identifier, self.anchor.identifier)
        self.assertIsNotNone(self.anchor.identifier)

    def test_identifier_set(self):
        self.assertIsNone(self.anchor.identifier)
        self.anchor.identifier = "foo"
        self.assertEqual(self.anchor.identifier, "foo")
        self.anchor.identifier = "bar"
        self.assertEqual(self.anchor.identifier, "foo")
        self.anchor.identifier = None
        self.assertEqual(self.anchor.identifier, "foo")

    def test_instance(self):
        a = Anchor(anchorDict=dict(x=1, y=2, name="3", identifier="4",
                                   color="1,1,1,1"))
        self.assertEqual((a.x, a.y, a.name, a.identifier, a.color),
                         (1, 2, "3", "4", "1,1,1,1"))

    def test_move(self):
        a = Anchor(anchorDict=dict(x=1, y=2, name="3"))
        a.dirty = False
        self.assertEqual((a.x, a.y), (1, 2))
        a.move((10, 0))
        self.assertTrue(a.dirty)

        a.dirty = False
        self.assertEqual((a.x, a.y), (11, 2))
        a.move((0, -123))
        self.assertTrue(a.dirty)

        a.dirty = False
        self.assertEqual((a.x, a.y), (11, -121))
        a.move((-11, 121))
        self.assertEqual((a.x, a.y), (0, 0))
        self.assertTrue(a.dirty)


class AnchorNotificationTest(unittest.TestCase):

    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)

    def setUp(self):
        self.font = Font()
        self.glyph = self.font.newGlyph("A")
        self.anchor = Anchor(
            self.glyph,
            {"name": "anchor1", "x": 300, "y": 700}
        )
        self.notificationObject = NotificationTestObserver()

    def tearDown(self):
        del self.anchor
        del self.glyph
        del self.font
        del self.notificationObject

    def test_x_changed_notification(self):
        self.anchor.dispatcher.addObserver(
            observer=self.notificationObject,
            methodName="notificationCallback",
            notification="Anchor.XChanged",
            observable=self.anchor
        )
        self.assertEqual(self.notificationObject.stack, [])
        self.anchor.x += 10
        self.assertEqual(
            self.notificationObject.stack[-1],
            ("Anchor.XChanged", "anchor1")
        )

    def test_y_changed_notification(self):
        self.anchor.dispatcher.addObserver(
            observer=self.notificationObject,
            methodName="notificationCallback",
            notification="Anchor.YChanged",
            observable=self.anchor
        )
        self.assertEqual(self.notificationObject.stack, [])
        self.anchor.y += 10
        self.assertEqual(
            self.notificationObject.stack[-1],
            ("Anchor.YChanged", "anchor1")
        )

    def test_name_notification(self):
        self.anchor.dispatcher.addObserver(
            observer=self.notificationObject,
            methodName="notificationCallback",
            notification="Anchor.NameChanged",
            observable=self.anchor
        )
        self.assertEqual(self.notificationObject.stack, [])
        self.anchor.name += "_suffix"
        self.assertEqual(
            self.notificationObject.stack[-1],
            ("Anchor.NameChanged", "anchor1_suffix")
        )

    def test_color_notification(self):
        self.anchor.dispatcher.addObserver(
            observer=self.notificationObject,
            methodName="notificationCallback",
            notification="Anchor.ColorChanged",
            observable=self.anchor
        )
        self.assertEqual(self.notificationObject.stack, [])
        self.anchor.color = "1,1,1,1"
        self.assertEqual(
            self.notificationObject.stack[-1],
            ("Anchor.ColorChanged", "anchor1")
        )

    def test_identifier_notification(self):
        self.anchor.dispatcher.addObserver(
            observer=self.notificationObject,
            methodName="notificationCallback",
            notification="Anchor.IdentifierChanged",
            observable=self.anchor
        )
        self.assertEqual(self.notificationObject.stack, [])
        self.anchor.identifier = "anchor1_identifier"
        self.assertEqual(
            self.notificationObject.stack[-1],
            ("Anchor.IdentifierChanged", "anchor1")
        )

    def test_endSelfNotificationObservation(self):
        self.assertIsNotNone(self.anchor.dispatcher)
        self.assertIsNotNone(self.anchor.font)
        self.assertIsNotNone(self.anchor.layerSet)
        self.assertIsNotNone(self.anchor.layer)
        self.assertIsNotNone(self.anchor.glyph)

        self.anchor.endSelfNotificationObservation()

        self.assertIsNone(self.anchor.dispatcher)
        self.assertIsNone(self.anchor.font)
        self.assertIsNone(self.anchor.layerSet)
        self.assertIsNone(self.anchor.layer)
        self.assertIsNone(self.anchor.glyph)


if __name__ == "__main__":
    unittest.main()
