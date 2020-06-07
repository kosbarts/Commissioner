from __future__ import unicode_literals
import unittest
from defcon import Component, Font, Glyph
from defcon.test.testTools import NotificationTestObserver
from defcon.test.testTools import getTestFontPath


class ComponentTest(unittest.TestCase):

    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)

    def setUp(self):
        self.font = Font()
        self.glyph = Glyph()
        self.component = Component(self.glyph)

    def tearDown(self):
        del self.component
        del self.glyph

    def test_getParent(self):
        self.assertEqual(self.component.getParent(), self.glyph)

    def test_font(self):
        self.assertIsNone(self.component.font)
        self.component = Component(self.font.newGlyph("A"))
        self.assertEqual(self.component.font, self.font)
        with self.assertRaises(AttributeError):
            self.component.font = "foo"

    def test_layerSet(self):
        self.assertIsNone(self.component.layerSet)
        self.glyph = self.font.newGlyph("A")
        self.component = Component(self.glyph)
        self.assertEqual(self.component.layerSet, self.glyph.layerSet)
        with self.assertRaises(AttributeError):
            self.component.layerSet = "foo"

    def test_layer(self):
        self.assertIsNone(self.component.layer)
        self.glyph = self.font.newGlyph("A")
        self.component = Component(self.glyph)
        self.assertEqual(self.component.layer, self.glyph.layer)
        with self.assertRaises(AttributeError):
            self.component.layer = "foo"

    def test_glyph(self):
        self.assertIsNone(self.component.layer)
        self.glyph = self.font.newGlyph("A")
        self.component = Component(self.glyph)
        self.assertEqual(self.component.layer, self.glyph.layer)
        with self.assertRaises(AttributeError):
            self.component.layer = "foo"

    def test_bounds(self):
        self.font = Font(getTestFontPath())
        self.glyph = self.font["C"]
        self.component = self.glyph.components[0]
        self.assertEqual(
            self.component.bounds,
            (0.0, 0.0, 350.0, 350.0)
        )
        with self.assertRaises(AttributeError):
            self.component.layer = (0.0, 0.0, 350.0, 350.0)

    def test_controlPointBounds(self):
        self.font = Font(getTestFontPath())
        self.glyph = self.font["C"]
        self.component = self.glyph.components[0]
        self.assertEqual(
            self.component.controlPointBounds,
            (0.0, 0.0, 350.0, 350.0)
        )
        with self.assertRaises(AttributeError):
            self.component.layer = (0.0, 0.0, 350.0, 350.0)

    def test_baseGlyph(self):
        self.assertIsNone(self.component.baseGlyph)

        self.font = Font(getTestFontPath())
        self.glyph = self.font["C"]
        self.component = self.glyph.components[0]
        self.assertEqual(self.component.baseGlyph, "A")
        self.component.baseGlyph = "B"
        self.assertEqual(self.component.baseGlyph, "B")

    def test_transformation(self):
        self.assertEqual(
            self.component.transformation,
            (1, 0, 0, 1, 0, 0)
        )

        self.font = Font(getTestFontPath())
        self.glyph = self.font["C"]
        self.component = self.glyph.components[0]
        self.assertEqual(
            self.component.transformation,
            (0.5, 0, 0, 0.5, 0, 0)
        )
        self.component = self.glyph.components[1]
        self.assertEqual(
            self.component.transformation,
            (0.5, 0, 0, 0.5, 350, 350)
        )

    def test_identifier(self):
        self.assertIsNone(self.component.identifier)
        self.component.identifier = "component 1"
        self.assertEqual(self.component.identifier, "component 1")

    def test_identifiers(self):
        self.assertEqual(sorted(self.glyph.identifiers), [])
        self.component.identifier = "component 1"
        self.assertEqual(sorted(self.glyph.identifiers), ["component 1"])

    def test_duplicate_identifier_error(self):
        glyph = self.glyph
        component = self.component
        component.identifier = "component 1"
        self.assertEqual(component.identifier, "component 1")
        component = Component(glyph)
        with self.assertRaises(AssertionError):
            component.identifier = "component 1"
        component.identifier = "component 2"
        self.assertEqual(sorted(glyph.identifiers),
                         ["component 1", "component 2"])
        component.identifier = "not component 2 anymore"
        self.assertEqual(component.identifier, "component 2")
        self.assertEqual(sorted(glyph.identifiers),
                         ["component 1", "component 2"])
        component.identifier = None
        self.assertEqual(component.identifier, "component 2")
        self.assertEqual(sorted(glyph.identifiers),
                         ["component 1", "component 2"])


class ComponentNotificationTest(unittest.TestCase):

    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)

    def setUp(self):
        self.font = Font()
        self.glyph = self.font.newGlyph("A")
        # self.font.newGlyph("B")
        self.component = Component(self.glyph)
        self.component.name = "component1"
        self.notificationObject = NotificationTestObserver()

    def tearDown(self):
        del self.component
        del self.glyph
        del self.font
        del self.notificationObject

    def test_changed_notification(self):
        self.component.dispatcher.addObserver(
            observer=self.notificationObject,
            methodName="notificationCallback",
            notification="Component.Changed",
            observable=self.component
        )
        self.assertEqual(self.notificationObject.stack, [])
        self.component.baseGlyph = "B"
        self.assertEqual(
            self.notificationObject.stack[-1],
            ("Component.Changed", "component1")
        )

    # TODO: other attributes

    def test_baseGlyph_changed_notification(self):
        self.component.dispatcher.addObserver(
            observer=self.notificationObject,
            methodName="notificationCallback",
            notification="Component.BaseGlyphChanged",
            observable=self.component
        )
        self.assertEqual(self.notificationObject.stack, [])
        self.component.baseGlyph = "B"
        self.assertEqual(
            self.notificationObject.stack[-1],
            ("Component.BaseGlyphChanged", "component1")
        )

    def test_transformation_changed_notification(self):
        self.component.dispatcher.addObserver(
            observer=self.notificationObject,
            methodName="notificationCallback",
            notification="Component.TransformationChanged",
            observable=self.component
        )
        self.assertEqual(self.notificationObject.stack, [])
        self.component.transformation = (1, 0, 0, 1.1, 0, 0)
        self.assertEqual(
            self.notificationObject.stack[-1],
            ("Component.TransformationChanged", "component1")
        )

    def test_identifier_changed_notification(self):
        self.component.dispatcher.addObserver(
            observer=self.notificationObject,
            methodName="notificationCallback",
            notification="Component.IdentifierChanged",
            observable=self.component
        )
        self.assertEqual(self.notificationObject.stack, [])
        self.component.identifier = "component1_identifier"
        self.assertEqual(
            self.notificationObject.stack[-1],
            ("Component.IdentifierChanged", "component1")
        )

if __name__ == "__main__":
    unittest.main()
