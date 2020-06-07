import unittest
from defcon import Font, Glyph, Contour, Component, Anchor, Guideline, Layer
from defcon.test.testTools import getTestFontPath


class GlyphTest(unittest.TestCase):

    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)

    def test_identifiers(self):
        glyph = Glyph()
        pointPen = glyph.getPointPen()
        pointPen.beginPath(identifier="contour 1")
        pointPen.addPoint((0, 0), identifier="point 1")
        pointPen.addPoint((0, 0), identifier="point 2")
        pointPen.endPath()
        pointPen.beginPath(identifier="contour 2")
        pointPen.endPath()
        pointPen.addComponent("A", (1, 1, 1, 1, 1, 1),
                              identifier="component 1")
        pointPen.addComponent("A", (1, 1, 1, 1, 1, 1),
                              identifier="component 2")
        guideline = Guideline()
        guideline.identifier = "guideline 1"
        glyph.appendGuideline(guideline)
        guideline = Guideline()
        guideline.identifier = "guideline 2"
        glyph.appendGuideline(guideline)

        self.assertEqual([contour.identifier for contour in glyph],
                         ["contour 1", "contour 2"])
        self.assertEqual([point.identifier for point in glyph[0]],
                         ["point 1", "point 2"])
        self.assertEqual(
            [component.identifier for component in glyph.components],
            ["component 1", "component 2"])
        with self.assertRaises(AssertionError):
            pointPen.beginPath(identifier="contour 1")
        pointPen.endPath()

        pointPen.beginPath()
        pointPen.addPoint((0, 0))
        with self.assertRaises(AssertionError):
            pointPen.addPoint((0, 0), identifier="point 1")
        pointPen.endPath()

        with self.assertRaises(AssertionError):
            pointPen.addComponent("A", (1, 1, 1, 1, 1, 1),
                                  identifier="component 1")

        g = Guideline()
        g.identifier = "guideline 1"
        with self.assertRaises(AssertionError):
            glyph.appendGuideline(g)

        self.assertEqual(
            sorted(glyph.identifiers),
            ["component 1", "component 2", "contour 1", "contour 2",
             "guideline 1", "guideline 2", "point 1", "point 2"])
        glyph.removeContour(glyph[0])
        self.assertEqual(
            sorted(glyph.identifiers),
            ["component 1", "component 2", "contour 2",
             "guideline 1", "guideline 2"])
        glyph.removeComponent(glyph.components[0])
        self.assertEqual(
            sorted(glyph.identifiers),
            ["component 2", "contour 2", "guideline 1", "guideline 2"])
        glyph.removeGuideline(glyph.guidelines[0])
        self.assertEqual(
            sorted(glyph.identifiers),
            ["component 2", "contour 2", "guideline 2"])

    def test_name_set(self):
        font = Font(getTestFontPath())
        glyph = font["A"]
        glyph.name = "RenamedGlyph"
        self.assertEqual(glyph.name, "RenamedGlyph")
        self.assertEqual(sorted(font.keys()), ["B", "C", "RenamedGlyph"])

        font = Font(getTestFontPath())
        glyph = font["A"]
        glyph.name = "A"
        self.assertFalse(glyph.dirty)

    def test_name_get(self):
        font = Font(getTestFontPath())
        glyph = font["A"]
        self.assertEqual(glyph.name, "A")

    def test_unicodes_get(self):
        font = Font(getTestFontPath())
        glyph = font["A"]
        self.assertEqual(glyph.unicodes, [65])

    def test_unicodes_set(self):
        font = Font(getTestFontPath())
        glyph = font["A"]
        glyph.unicodes = [123, 456]
        self.assertEqual(glyph.unicodes, [123, 456])
        self.assertTrue(glyph.dirty)

    def test_bounds(self):
        font = Font(getTestFontPath())
        glyph = font["A"]
        self.assertEqual(glyph.bounds, (0, 0, 700, 700))
        glyph = font["B"]
        self.assertEqual(glyph.bounds, (0, 0, 700, 700))
        glyph = font["C"]
        self.assertEqual(glyph.bounds, (0.0, 0.0, 700.0, 700.0))

    def test_controlPointBounds(self):
        from defcon.test.testTools import getTestFontPath
        from defcon.objects.font import Font
        font = Font(getTestFontPath())
        glyph = font["A"]
        self.assertEqual(glyph.controlPointBounds, (0, 0, 700, 700))
        glyph = font["B"]
        self.assertEqual(glyph.controlPointBounds, (0, 0, 700, 700))
        glyph = font["C"]
        self.assertEqual(glyph.controlPointBounds, (0.0, 0.0, 700.0, 700.0))

    def test_leftMargin_get(self):
        font = Font(getTestFontPath())
        glyph = font["A"]
        self.assertEqual(glyph.leftMargin, 0)
        glyph = font["B"]
        self.assertEqual(glyph.leftMargin, 0)

    def test_leftMargin_set(self):
        font = Font(getTestFontPath())
        glyph = font["A"]
        glyph.leftMargin = 100
        self.assertEqual(glyph.leftMargin, 100)
        self.assertEqual(glyph.width, 800)
        self.assertTrue(glyph.dirty)

    def test_rightMargin_get(self):
        from defcon.test.testTools import getTestFontPath
        from defcon.objects.font import Font
        font = Font(getTestFontPath())
        glyph = font["A"]
        self.assertEqual(glyph.rightMargin, 0)

    def test_rightMargin_set(self):
        from defcon.test.testTools import getTestFontPath
        from defcon.objects.font import Font
        font = Font(getTestFontPath())
        glyph = font["A"]
        glyph.rightMargin = 100
        self.assertEqual(glyph.rightMargin, 100)
        self.assertEqual(glyph.width, 800)
        self.assertTrue(glyph.dirty)

    def test_bottomMargin_get(self):
        font = Font(getTestFontPath())
        glyph = font["A"]
        self.assertEqual(glyph.bottomMargin, 0)
        glyph = font["B"]
        self.assertEqual(glyph.bottomMargin, 0)
        # empty glyph
        glyph = font.newGlyph("D")
        self.assertIsNone(glyph.bottomMargin)

    def test_bottomMargin_set(self):
        font = Font(getTestFontPath())
        glyph = font["A"]
        glyph.bottomMargin = 100
        self.assertEqual(glyph.bottomMargin, 100)
        self.assertEqual(glyph.height, 600)
        self.assertEqual(glyph.verticalOrigin, 500)
        self.assertTrue(glyph.dirty)
        # now glyph.verticalOrigin is defined
        glyph.bottomMargin = 50
        self.assertEqual(glyph.bottomMargin, 50)
        self.assertEqual(glyph.height, 550)
        self.assertEqual(glyph.verticalOrigin, 500)
        self.assertTrue(glyph.dirty)
        # empty glyph
        glyph = font.newGlyph("D")
        glyph.dirty = False
        glyph.bottomMargin = 10
        self.assertIsNone(glyph.bottomMargin)
        self.assertEqual(glyph.height, 0)
        self.assertIsNone(glyph.verticalOrigin)
        self.assertFalse(glyph.dirty)


    def test_topMargin_get(self):
        from defcon.test.testTools import getTestFontPath
        from defcon.objects.font import Font
        font = Font(getTestFontPath())
        glyph = font["A"]
        self.assertEqual(glyph.topMargin, -200)
        # empty glyph
        glyph = font.newGlyph("D")
        self.assertIsNone(glyph.topMargin)

    def test_topMargin_set(self):
        from defcon.test.testTools import getTestFontPath
        from defcon.objects.font import Font
        font = Font(getTestFontPath())
        glyph = font["A"]
        glyph.topMargin = 100
        self.assertEqual(glyph.topMargin, 100)
        self.assertEqual(glyph.height, 800)
        self.assertEqual(glyph.verticalOrigin, 800)
        self.assertTrue(glyph.dirty)
        # now glyph.verticalOrigin is defined
        glyph.topMargin = 50
        self.assertEqual(glyph.topMargin, 50)
        self.assertEqual(glyph.height, 750)
        self.assertEqual(glyph.verticalOrigin, 750)
        self.assertTrue(glyph.dirty)
        # empty glyph
        glyph = font.newGlyph("D")
        glyph.dirty = False
        glyph.topMargin = 10
        self.assertIsNone(glyph.topMargin)
        self.assertEqual(glyph.height, 0)
        self.assertIsNone(glyph.verticalOrigin)
        self.assertFalse(glyph.dirty)


    def test_width_get(self):
        font = Font(getTestFontPath())
        glyph = font["A"]
        self.assertEqual(glyph.width, 700)

    def test_width_set(self):
        font = Font(getTestFontPath())
        glyph = font["A"]
        glyph.width = 100
        self.assertEqual(glyph.width, 100)
        self.assertTrue(glyph.dirty)

    def test_height_get(self):
        font = Font(getTestFontPath())
        glyph = font["A"]
        self.assertEqual(glyph.height, 500)

    def test_height_set(self):
        font = Font(getTestFontPath())
        glyph = font["A"]
        glyph.height = 100
        self.assertEqual(glyph.height, 100)
        self.assertEqual(glyph.verticalOrigin, None)
        self.assertTrue(glyph.dirty)

    def test_markColor(self):
        from defcon.objects.font import Font
        font = Font()
        font.newGlyph("A")
        glyph = font["A"]
        self.assertIsNone(glyph.markColor)
        glyph.markColor = "1,0,1,0"
        self.assertEqual(glyph.markColor, "1,0,1,0")
        glyph.markColor = "1,0,1,0"
        self.assertEqual(glyph.markColor, "1,0,1,0")
        glyph.markColor = None
        self.assertIsNone(glyph.markColor)

    def test_verticalOrigin(self):
        from defcon.test.testTools import getTestFontPath
        from defcon.objects.font import Font
        font = Font()
        font.newGlyph("A")
        glyph = font["A"]
        self.assertIsNone(glyph.verticalOrigin)
        self.assertEqual(glyph.height, 0)
        glyph.verticalOrigin = 1000
        self.assertEqual(glyph.verticalOrigin, 1000)
        self.assertEqual(glyph.height, 0)
        glyph.verticalOrigin = 0
        self.assertEqual(glyph.verticalOrigin, 0)
        self.assertEqual(glyph.height, 0)
        glyph.verticalOrigin = -10
        self.assertEqual(glyph.verticalOrigin, -10)
        self.assertEqual(glyph.height, 0)
        glyph.verticalOrigin = None
        self.assertIsNone(glyph.verticalOrigin)
        self.assertEqual(glyph.height, 0)

        font = Font(getTestFontPath())
        glyph = font["A"]
        self.assertIsNone(glyph.verticalOrigin)
        self.assertEqual(glyph.height, 500)
        glyph.verticalOrigin = 1000
        self.assertEqual(glyph.verticalOrigin, 1000)
        self.assertEqual(glyph.height, 500)
        glyph.verticalOrigin = 0
        self.assertEqual(glyph.verticalOrigin, 0)
        self.assertEqual(glyph.height, 500)
        glyph.verticalOrigin = -10
        self.assertEqual(glyph.verticalOrigin, -10)
        self.assertEqual(glyph.height, 500)
        glyph.verticalOrigin = None
        self.assertIsNone(glyph.verticalOrigin)
        self.assertEqual(glyph.height, 500)

    def test_appendContour(self):
        glyph = Glyph()
        glyph.dirty = False
        contour = Contour()
        glyph.appendContour(contour)
        self.assertEqual(len(glyph), 1)
        self.assertTrue(glyph.dirty)
        self.assertEqual(contour.getParent(), glyph)

    def test_removeContour(self):
        font = Font(getTestFontPath())
        glyph = font["A"]
        contour = glyph[0]
        glyph.removeContour(contour)
        self.assertFalse(contour in glyph._contours)
        self.assertIsNone(contour.getParent())

    def test_contourIndex(self):
        font = Font(getTestFontPath())
        glyph = font["A"]
        contour = glyph[0]
        self.assertEqual(glyph.contourIndex(contour), 0)
        contour = glyph[1]
        self.assertEqual(glyph.contourIndex(contour), 1)

    def test_clearContours(self):
        font = Font(getTestFontPath())
        glyph = font["A"]
        glyph.clearContours()
        self.assertEqual(len(glyph), 0)

    def test_components(self):
        font = Font(getTestFontPath())
        glyph = font["C"]
        self.assertEqual(len(glyph.components), 2)

    def test_appendComponent(self):
        glyph = Glyph()
        glyph.dirty = False
        component = Component()
        glyph.appendComponent(component)
        self.assertEqual(len(glyph.components), 1)
        self.assertTrue(glyph.dirty)
        self.assertEqual(component.getParent(), glyph)

    def test_removeComponent(self):
        font = Font(getTestFontPath())
        glyph = font["C"]
        component = glyph.components[0]
        glyph.removeComponent(component)
        self.assertFalse(component in glyph.components)
        self.assertIsNone(component.getParent())

    def test_componentIndex(self):
        font = Font(getTestFontPath())
        glyph = font["C"]
        component = glyph.components[0]
        self.assertEqual(glyph.componentIndex(component), 0)
        component = glyph.components[1]
        self.assertEqual(glyph.componentIndex(component), 1)

    def test_clearComponents(self):
        font = Font(getTestFontPath())
        glyph = font["C"]
        glyph.clearComponents()
        self.assertEqual(len(glyph.components), 0)

    def test_decomposeComponent(self):
        font = Font()

        font.newGlyph("baseGlyph")
        baseGlyph = font["baseGlyph"]
        pointPen = baseGlyph.getPointPen()
        pointPen.beginPath(identifier="contour1")
        pointPen.addPoint((0, 0), "move", identifier="point1")
        pointPen.addPoint((0, 100), "line")
        pointPen.addPoint((100, 100), "line")
        pointPen.addPoint((100, 0), "line")
        pointPen.addPoint((0, 0), "line")
        pointPen.endPath()

        font.newGlyph("referenceGlyph")
        referenceGlyph = font["referenceGlyph"]
        pointPen = referenceGlyph.getPointPen()
        pointPen.addComponent("baseGlyph", (1, 0, 0, 1, 0, 0))
        self.assertEqual(len(referenceGlyph.components), 1)
        self.assertEqual(len(referenceGlyph), 0)
        referenceGlyph.decomposeAllComponents()
        self.assertEqual(len(referenceGlyph.components), 0)
        self.assertEqual(len(referenceGlyph), 1)
        self.assertEqual(referenceGlyph[0].identifier, "contour1")
        self.assertEqual(referenceGlyph[0][0].identifier, "point1")

        pointPen.addComponent("baseGlyph", (1, 0, 0, 1, 100, 100))
        self.assertEqual(len(referenceGlyph.components), 1)
        self.assertEqual(len(referenceGlyph), 1)
        component = referenceGlyph.components[0]
        referenceGlyph.decomposeComponent(component)
        self.assertEqual(len(referenceGlyph.components), 0)
        self.assertEqual(len(referenceGlyph), 2)
        self.assertEqual(referenceGlyph[0].identifier, "contour1")
        self.assertEqual(referenceGlyph[0][0].identifier, "point1")
        referenceGlyph[1].identifier
        referenceGlyph[1][0].identifier

    def test_decomposeComponent_nested_components(self):
        font = Font()
        font.newGlyph("baseGlyph")
        baseGlyph = font["baseGlyph"]
        pointPen = baseGlyph.getPointPen()
        pointPen.beginPath(identifier="contour1")
        pointPen.addPoint((0, 0), "move", identifier="point1")
        pointPen.addPoint((0, 100), "line")
        pointPen.addPoint((100, 100), "line")
        pointPen.addPoint((100, 0), "line")
        pointPen.addPoint((0, 0), "line")
        pointPen.endPath()

        font.newGlyph("referenceGlyph1")
        referenceGlyph1 = font["referenceGlyph1"]
        pointPen = referenceGlyph1.getPointPen()
        pointPen.addComponent("baseGlyph", (1, 0, 0, 1, 3, 6))
        font.newGlyph("referenceGlyph2")
        referenceGlyph2 = font["referenceGlyph2"]
        pointPen = referenceGlyph2.getPointPen()
        pointPen.addComponent("referenceGlyph1", (1, 0, 0, 1, 10, 20))
        referenceGlyph2.decomposeAllComponents()
        self.assertEqual(len(referenceGlyph2.components), 0)
        self.assertEqual(len(referenceGlyph1.components), 1)
        self.assertEqual(len(referenceGlyph2), 1)
        self.assertEqual(referenceGlyph2.bounds, (13, 26, 113, 126))

    def test_anchors(self):
        font = Font(getTestFontPath())
        glyph = font["A"]
        self.assertEqual(len(glyph.anchors), 2)

    def test_appendAnchor(self):
        glyph = Glyph()
        glyph.dirty = False
        anchor = Anchor()
        glyph.appendAnchor(anchor)
        self.assertEqual(len(glyph.anchors), 1)
        self.assertTrue(glyph.dirty)
        self.assertEqual(anchor.getParent(), glyph)

    def test_removeAnchor(self):
        font = Font(getTestFontPath())
        glyph = font["A"]
        anchor = glyph.anchors[0]
        glyph.removeAnchor(anchor)
        self.assertFalse(anchor in glyph.anchors)
        self.assertIsNone(anchor.getParent())

    def test_anchorIndex(self):
        font = Font(getTestFontPath())
        glyph = font["A"]
        anchor = glyph.anchors[0]
        self.assertEqual(glyph.anchorIndex(anchor), 0)
        anchor = glyph.anchors[1]
        self.assertEqual(glyph.anchorIndex(anchor), 1)

    def test_clearAnchors(self):
        font = Font(getTestFontPath())
        glyph = font["A"]
        glyph.clearAnchors()
        self.assertEqual(len(glyph.anchors), 0)

    def test_appendGuideline(self):
        glyph = Glyph()
        glyph.dirty = False
        guideline = Guideline()
        glyph.appendGuideline(guideline)
        self.assertEqual(len(glyph.guidelines), 1)
        self.assertTrue(glyph.dirty)
        self.assertEqual(guideline.getParent(), glyph)

    def test_removeGuideline(self):
        font = Font(getTestFontPath())
        glyph = font.layers["Layer 1"]["A"]
        guideline = glyph.guidelines[0]
        glyph.removeGuideline(guideline)
        self.assertFalse(guideline in glyph.guidelines)
        self.assertIsNone(guideline.getParent())

    def test_clearGuidelines(self):
        font = Font(getTestFontPath())
        glyph = font["A"]
        glyph.clearGuidelines()
        self.assertEqual(len(glyph.guidelines), 0)

    def test_len(self):
        font = Font(getTestFontPath())
        glyph = font["A"]
        self.assertEqual(len(glyph), 2)

    def test_iter(self):
        font = Font(getTestFontPath())
        glyph = font["A"]
        self.assertEqual([len(contour) for contour in glyph], [4, 4])

    def test_copyDataFromGlyph(self):
        source = Glyph()
        source.name = "a"
        source.width = 1
        source.height = 2
        source.unicodes = [3, 4]
        source.note = "test image"
        source.image = dict(fileName="test image", xScale=1, xyScale=1,
                            yxScale=1, yScale=1, xOffset=0, yOffset=0,
                            color=None)
        source.anchors = [dict(x=100, y=200, name="test anchor")]
        source.guidelines = [dict(x=10, y=20, name="test guideline")]
        source.lib = {"foo": "bar"}
        pen = source.getPointPen()
        pen.beginPath()
        pen.addPoint((100, 200), segmentType="line")
        pen.addPoint((300, 400), segmentType="line")
        pen.endPath()
        component = Component()
        component.base = "b"
        source.appendComponent(component)
        dest = Glyph()
        dest.copyDataFromGlyph(source)

        self.assertNotEqual(source.name, dest.name)
        self.assertEqual(source.width, dest.width)
        self.assertEqual(source.height, dest.height)
        self.assertEqual(source.unicodes, dest.unicodes)
        self.assertEqual(source.note, dest.note)
        self.assertEqual(source.image.items(), dest.image.items())
        self.assertEqual([g.items() for g in source.guidelines],
                         [g.items() for g in dest.guidelines])
        self.assertEqual([g.items() for g in source.anchors],
                         [g.items() for g in dest.anchors])
        self.assertEqual(len(source), len(dest))
        self.assertEqual(len(source.components), len(dest.components))
        sourceContours = []
        for contour in source:
            sourceContours.append([])
            for point in contour:
                sourceContours[-1].append((point.x, point.x,
                                           point.segmentType, point.name))
        destContours = []
        for contour in dest:
            destContours.append([])
            for point in contour:
                destContours[-1].append((point.x, point.x,
                                         point.segmentType, point.name))
        self.assertEqual(sourceContours, destContours)
        self.assertEqual(source.components[0].baseGlyph,
                         dest.components[0].baseGlyph)

    def test_clear(self):
        font = Font(getTestFontPath())
        glyph = font["A"]
        contour = glyph[0]
        anchor = glyph.anchors[0]
        glyph.clear()
        self.assertEqual(len(glyph), 0)
        self.assertEqual(len(glyph.anchors), 0)
        glyph = font["C"]
        component = glyph.components[0]
        glyph.clear()
        self.assertEqual(len(glyph.components), 0)
        glyph = font.layers["Layer 1"]["A"]
        guideline = glyph.guidelines[0]
        glyph.clear()
        self.assertEqual(len(glyph.guidelines), 0)

        self.assertEqual((contour.getParent(), component.getParent(),
                         anchor.getParent(), guideline.getParent()),
                         (None, None, None, None))
        self.assertEqual((contour.dispatcher, component.dispatcher,
                         anchor.dispatcher, guideline.dispatcher),
                         (None, None, None, None))

    def test_move(self):
        font = Font(getTestFontPath())
        glyph = font["A"]
        xMin, yMin, xMax, yMax = glyph.bounds
        glyph.move((100, 50))
        self.assertEqual((xMin+100, yMin+50, xMax+100, yMax+50),
                         glyph.bounds)
        glyph = font["C"]
        xMin, yMin, xMax, yMax = glyph.bounds
        glyph.move((100, 50))
        self.assertEqual((xMin+100, yMin+50, xMax+100, yMax+50), glyph.bounds)

    def test_pointInside(self):
        font = Font(getTestFontPath())
        glyph = font["A"]
        self.assertTrue(glyph.pointInside((100, 100)))
        self.assertFalse(glyph.pointInside((350, 350)))
        self.assertFalse(glyph.pointInside((-100, -100)))


if __name__ == "__main__":
    unittest.main()
