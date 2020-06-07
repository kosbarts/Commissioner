from __future__ import unicode_literals
import unittest
from defcon import Contour, Font, Glyph, Point
from defcon.test.testTools import getTestFontPath


def simpleSegment(segment):
    return [(i.x, i.y, i.segmentType) for i in segment]


class ContourTest(unittest.TestCase):

    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)

    def setUp(self):
        self.font = Font()
        self.glyph = self.font.newGlyph("A")
        self.contour = Contour()

    def tearDown(self):
        del self.contour
        del self.glyph
        del self.font

    def test_getParent(self):
        self.assertIsNone(self.contour.getParent())
        self.contour = Contour(self.glyph)
        self.assertEqual(self.contour.getParent(), self.glyph)

    def test_font(self):
        self.assertIsNone(self.contour.font)
        self.contour = Contour(self.glyph)
        self.assertEqual(self.contour.font, self.font)
        with self.assertRaises(AttributeError):
            self.contour.font = "foo"

    def test_layerSet(self):
        self.assertIsNone(self.contour.layerSet)
        self.contour = Contour(self.glyph)
        self.assertIsNotNone(self.contour.layerSet)
        self.assertEqual(self.contour.layerSet, self.glyph.layerSet)
        with self.assertRaises(AttributeError):
            self.contour.layerSet = "foo"

    def test_layer(self):
        self.assertIsNone(self.contour.layer)
        self.contour = Contour(self.glyph)
        self.assertIsNotNone(self.contour.layer)
        self.assertEqual(self.contour.layer, self.glyph.layer)
        with self.assertRaises(AttributeError):
            self.contour.layer = "foo"

    def test_glyph(self):
        self.assertIsNone(self.contour.glyph)
        self.contour = Contour(self.glyph)
        self.assertEqual(self.contour.glyph, self.glyph)
        glyph = Glyph()
        self.contour = Contour()
        self.contour.glyph = glyph
        self.assertEqual(self.contour.glyph, glyph)
        with self.assertRaises(AssertionError):
            self.contour.glyph = self.glyph

    def test_list_behavior(self):
        font = Font(getTestFontPath())
        glyph = font["A"]
        contour = glyph[0]
        with self.assertRaises(IndexError):
            contour[len(contour) + 1]
        self.assertEqual(contour[len(contour):len(contour)], [])
        self.assertEqual(contour[len(contour) + 1:len(contour) + 2], [])
        self.assertNotEqual(contour[0:len(contour) + 1], [])
        self.assertEqual([(point.x, point.y) for point in contour[0:]],
                         [(point.x, point.y)
                          for point in contour[0:len(contour) + 1]])
        self.assertEqual([(point.x, point.y) for point in contour[0:]],
                         [(0, 0), (700, 0), (700, 700), (0, 700)])
        self.assertEqual([(point.x, point.y) for point in contour],
                         [(0, 0), (700, 0), (700, 700), (0, 700)])

    def test_onCurvePoints(self):
        font = Font(getTestFontPath())
        glyph = font["A"]
        contour = glyph[0]
        self.assertEqual(len(contour.onCurvePoints), 4)
        self.assertEqual([(point.x, point.y)
                          for point in contour.onCurvePoints],
                         [(0, 0), (700, 0), (700, 700), (0, 700)])
        glyph = font["B"]
        contour = glyph[0]
        self.assertEqual(len(contour.onCurvePoints), 4)
        self.assertEqual([(point.x, point.y)
                          for point in contour.onCurvePoints],
                         [(0, 350), (350, 0), (700, 350), (350, 700)])

    def test_appendPoint(self):
        pointA = Point((0, 5))
        self.assertFalse(self.contour.dirty)
        self.contour.appendPoint(pointA)
        self.assertTrue(self.contour.dirty)
        self.assertEqual([(point.x, point.y)
                          for point in self.contour],
                         [(0, 5)])
        pointB = Point((6, 7))
        self.contour.appendPoint(pointB)
        self.assertEqual([(point.x, point.y)
                          for point in self.contour],
                         [(0, 5), (6, 7)])

    def test_insertPoint(self):
        pointA = Point((0, 5))
        pointB = Point((6, 7))
        pointC = Point((8, 9))
        self.assertFalse(self.contour.dirty)
        self.contour.insertPoint(0, pointA)
        self.assertTrue(self.contour.dirty)
        self.assertEqual([(point.x, point.y)
                          for point in self.contour],
                         [(0, 5)])
        self.contour.insertPoint(0, pointB)
        self.assertEqual([(point.x, point.y)
                          for point in self.contour],
                         [(6, 7), (0, 5)])
        self.contour.insertPoint(1, pointC)
        self.assertEqual([(point.x, point.y)
                          for point in self.contour],
                         [(6, 7), (8, 9), (0, 5)])

    def test_removePoint(self):
        font = Font(getTestFontPath())
        contour = font["A"][0]
        self.assertFalse(contour.dirty)
        contour.removePoint(contour[1])
        self.assertTrue(contour.dirty)
        self.assertEqual([(point.x, point.y)
                          for point in contour],
                         [(0, 0), (700, 700), (0, 700)])
        contour.removePoint(contour[0])
        self.assertEqual([(point.x, point.y)
                          for point in contour],
                         [(700, 700), (0, 700)])
        contour.removePoint(contour[1])
        self.assertEqual([(point.x, point.y)
                          for point in contour],
                         [(700, 700)])

    def test_setStartPoint(self):
        font = Font(getTestFontPath())
        contour = font["B"][0]
        start = [(point.segmentType, point.x, point.y) for point in contour]
        contour.setStartPoint(6)
        self.assertTrue(contour.dirty)
        contour.setStartPoint(6)
        end = [(point.segmentType, point.x, point.y) for point in contour]
        self.assertEqual(start, end)
        contour = font["A"][0]
        start = [(point.segmentType, point.x, point.y) for point in contour]
        contour.setStartPoint(2)
        contour.setStartPoint(2)
        end = [(point.segmentType, point.x, point.y) for point in contour]
        self.assertEqual(start, end)
        contour = font["B"][0]
        start = [(point.segmentType, point.x, point.y) for point in contour]
        contour.setStartPoint(3)
        contour.setStartPoint(9)
        end = [(point.segmentType, point.x, point.y) for point in contour]
        self.assertEqual(start, end)

    def test_len(self):
        font = Font(getTestFontPath())
        contour = font["A"][0]
        self.assertEqual(len(contour), 4)
        contour = font["B"][0]
        self.assertEqual(len(contour), 12)

    def test_iter(self):
        font = Font(getTestFontPath())
        contour = font["A"][0]
        self.assertEqual([(point.x, point.y) for point in contour],
                         [(0, 0), (700, 0), (700, 700), (0, 700)])

    def test_index(self):
        font = Font(getTestFontPath())
        contour = font["B"][0]
        self.assertEqual(contour.index(contour[2]), 2)

    def test_reverse(self):
        font = Font(getTestFontPath())
        contour = font["A"][0]
        contour.reverse()
        self.assertEqual([(point.x, point.y) for point in contour._points],
                         [(0, 0), (0, 700), (700, 700), (700, 0)])
        contour.reverse()
        self.assertEqual([(point.x, point.y) for point in contour._points],
                         [(0, 0), (700, 0), (700, 700), (0, 700)])

    def test_segments(self):
        font = Font(getTestFontPath())
        glyph = font["A"]
        contour = glyph[0]
        self.assertEqual(
            [simpleSegment(segment) for segment in contour.segments],
            [[(700, 0, "line")], [(700, 700, "line")],
             [(0, 700, "line")], [(0, 0, "line")]])
        glyph = font["B"]
        contour = glyph[0]
        self.assertEqual(
            [simpleSegment(segment) for segment in contour.segments],
            [[(0, 157, None), (157, 0, None), (350, 0, "curve")],
             [(543, 0, None), (700, 157, None), (700, 350, "curve")],
             [(700, 543, None), (543, 700, None), (350, 700, "curve")],
             [(157, 700, None), (0, 543, None), (0, 350, "curve")]])

    def test_removeSegment_lines(self):
        font = Font(getTestFontPath())
        glyph = font["A"]
        contour = glyph[0]
        contour.removeSegment(len(contour.segments) - 2)
        self.assertEqual(
            [simpleSegment(segment) for segment in contour.segments],
            [[(700, 0, "line")], [(700, 700, "line")],
             [(0, 0, "line")]])
        contour.removeSegment(len(contour.segments) - 1)
        self.assertEqual(
            [simpleSegment(segment) for segment in contour.segments],
            [[(700, 700, "line")], [(700, 0, "line")]])

    def test_removeSegment_first_segment(self):
        font = Font(getTestFontPath())
        glyph = font["A"]
        contour = glyph[0]
        contour.removeSegment(0)
        self.assertEqual(
            [simpleSegment(segment) for segment in contour.segments],
            [[(700, 700, "line")], [(0, 700, "line")],
             [(0, 0, "line")]])

    def test_removeSegment_last_segment(self):
        font = Font(getTestFontPath())
        glyph = font["A"]
        contour = glyph[0]
        contour.removeSegment(len(contour.segments) - 1)
        self.assertEqual(
            [simpleSegment(segment) for segment in contour.segments],
            [[(700, 700, "line")], [(0, 700, "line")],
             [(700, 0, "line")]])

    def test_removeSegment_curves(self):
        font = Font(getTestFontPath())
        glyph = font["B"]
        contour = glyph[0]
        contour.removeSegment(len(contour.segments) - 2)
        self.assertEqual(
            [simpleSegment(segment) for segment in contour.segments],
            [[(0, 157, None), (157, 0, None), (350, 0, "curve")],
             [(543, 0, None), (700, 157, None), (700, 350, "curve")],
             [(157, 700, None), (0, 543, None), (0, 350, "curve")]])

    def test_removeSegment_curves_preserveCurve(self):
        font = Font(getTestFontPath())
        glyph = font["B"]
        contour = glyph[0]
        contour.removeSegment(len(contour.segments) - 2, preserveCurve=True)
        self.assertEqual(
            [simpleSegment(segment) for segment in contour.segments],
            [[(0, 157, None), (157, 0, None), (350, 0, "curve")],
             [(543, 0, None), (700, 157, None), (700, 350, "curve")],
             [(700.0, 736.0, None), (0.0, 736.0, None), (0, 350, "curve")]])

    def test_clockwise_get(self):
        font = Font(getTestFontPath())
        contour = font["A"][0]
        self.assertFalse(contour.clockwise)
        contour = font["A"][1]
        self.assertTrue(contour.clockwise)
        contour._clockwiseCache = None
        contour.clockwise = False
        self.assertFalse(contour.clockwise)
        contour._clockwiseCache = None
        contour.clockwise = True
        self.assertTrue(contour.clockwise)

    def test_clockwise_set(self):
        font = Font(getTestFontPath())
        contour = font["A"][0]
        contour.clockwise = False
        self.assertFalse(contour.clockwise)
        contour._clockwiseCache = None
        contour.clockwise = True
        self.assertTrue(contour.clockwise)

    def test_open(self):
        font = Font(getTestFontPath("TestOpenContour.ufo"))
        glyph = font["A"]
        self.assertTrue(glyph[0].open)
        self.assertFalse(glyph[1].open)
        self.assertTrue(glyph[2].open)
        self.assertFalse(glyph[3].open)
        contour = Contour()
        self.assertTrue(contour.open)

    def test_bounds(self):
        font = Font(getTestFontPath())
        contour = font["A"][0]
        self.assertEqual(contour.bounds, (0, 0, 700, 700))

    def test_controlPointBounds(self):
        font = Font(getTestFontPath())
        contour = font["A"][0]
        self.assertEqual(contour.controlPointBounds, (0, 0, 700, 700))

    def test_move(self):
        font = Font(getTestFontPath())
        contour = font["A"][0]
        contour.move((100, 100))
        self.assertEqual(contour.bounds, (100, 100, 800, 800))
        self.assertTrue(contour.dirty)

    def test_pointInside(self):
        font = Font(getTestFontPath())
        contour = font["A"][0]
        self.assertTrue(contour.pointInside((100, 100)))
        self.assertFalse(contour.pointInside((0, 0)))
        self.assertFalse(contour.pointInside((-100, -100)))

    def test_positionForProspectivePointInsertionAtSegmentAndT(self):
        font = Font(getTestFontPath())
        contour = font["A"][0]
        self.assertEqual(
            contour.positionForProspectivePointInsertionAtSegmentAndT(0, .5),
            ((350.0, 0.0), False))
        contour = font["B"][0]
        self.assertEqual(
            contour.positionForProspectivePointInsertionAtSegmentAndT(0, .5),
            ((102.625, 102.625), True))
        contour = font["B"][1]
        self.assertEqual(
            contour.positionForProspectivePointInsertionAtSegmentAndT(0, .5),
            ((226.125, 473.5), True))

    def test_splitAndInsertPointAtSegmentAndT(self):
        font = Font(getTestFontPath())
        contour = font["A"][0]
        contour.splitAndInsertPointAtSegmentAndT(0, .5)
        self.assertEqual(
            [(point.x, point.y, point.segmentType) for point in contour],
            [(0, 0, "line"), (350.0, 0.0, "line"), (700, 0, "line"),
             (700, 700, "line"), (0, 700, "line")])
        contour = font["B"][0]
        contour.splitAndInsertPointAtSegmentAndT(0, .5)
        self.assertEqual(
            [(point.x, point.y, point.segmentType) for point in contour],
            [(0, 350, "curve"), (0.0, 253.5, None), (39.25, 166.0, None),
             (102.625, 102.625, "curve"), (166.0, 39.25, None),
             (253.5, 0.0, None), (350, 0, "curve"), (543, 0, None),
             (700, 157, None), (700, 350, "curve"), (700, 543, None),
             (543, 700, None), (350, 700, "curve"), (157, 700, None),
             (0, 543, None)])

    def test_identifier(self):
        glyph = Glyph()
        contour = Contour()
        glyph.appendContour(contour)
        contour.identifier = "contour 1"
        self.assertEqual(contour.identifier, "contour 1")
        self.assertEqual(sorted(glyph.identifiers), ["contour 1"])
        contour = Contour()
        glyph.appendContour(contour)
        with self.assertRaises(AssertionError):
            contour.identifier = "contour 1"
        contour.identifier = "contour 2"
        self.assertEqual(sorted(glyph.identifiers), ["contour 1", "contour 2"])
        contour.identifier = "not contour 2 anymore"
        self.assertEqual(contour.identifier, "contour 2")
        self.assertEqual(sorted(glyph.identifiers), ["contour 1", "contour 2"])
        contour.identifier = None
        self.assertEqual(contour.identifier, "contour 2")
        self.assertEqual(sorted(glyph.identifiers), ["contour 1", "contour 2"])
    
    def test_correct_direction_same_area(self):
        glyph = Glyph()
        pen = glyph.getPointPen()
        pen.beginPath()
        pen.addPoint((0, 0), segmentType="line")
        pen.addPoint((0, 50), segmentType="line")
        pen.addPoint((50, 50), segmentType="line")
        pen.endPath()
        pen.beginPath()
        pen.addPoint((50, 50), segmentType="line")
        pen.addPoint((50, 100), segmentType="line")
        pen.addPoint((100, 100), segmentType="line")
        pen.endPath()
        try:
            glyph.correctContourDirection()
        except Exception as e:
            self.fail("glyph.correctContourDirection() raised unexpected exception: "
                      + str(e))

if __name__ == "__main__":
    unittest.main()
