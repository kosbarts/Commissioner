import unittest
from defcon import Font


class GroupsTest(unittest.TestCase):

    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)

    def test_side1KerningGroups(self):
        font = Font()
        groups = font.groups
        groups["a"] = ["a"]
        result = groups.getRepresentation("defcon.groups.kerningSide1Groups")
        self.assertEqual(result, {})
        groups["public.kern1.a"] = ["a"]
        result = groups.getRepresentation("defcon.groups.kerningSide1Groups")
        self.assertEqual(result, {"public.kern1.a" : ["a"]})
        groups["public.kern1.a"] = ["b"]
        result = groups.getRepresentation("defcon.groups.kerningSide1Groups")
        self.assertEqual(result, {"public.kern1.a" : ["b"]})
        groups["public.kern2.a"] = ["b"]
        result = groups.getRepresentation("defcon.groups.kerningSide1Groups")
        self.assertEqual(result, {"public.kern1.a" : ["b"]})

    def test_side2KerningGroups(self):
        font = Font()
        groups = font.groups
        groups["a"] = ["a"]
        result = groups.getRepresentation("defcon.groups.kerningSide2Groups")
        self.assertEqual(result, {})
        groups["public.kern2.a"] = ["a"]
        result = groups.getRepresentation("defcon.groups.kerningSide2Groups")
        self.assertEqual(result, {"public.kern2.a" : ["a"]})
        groups["public.kern2.a"] = ["b"]
        result = groups.getRepresentation("defcon.groups.kerningSide2Groups")
        self.assertEqual(result, {"public.kern2.a" : ["b"]})
        groups["public.kern1.a"] = ["b"]
        result = groups.getRepresentation("defcon.groups.kerningSide2Groups")
        self.assertEqual(result, {"public.kern2.a" : ["b"]})

    def test_side1glyphToKerningGroups(self):
        font = Font()
        groups = font.groups
        groups["public.kern1.a"] = ["a"]
        result = groups.getRepresentation("defcon.groups.kerningGlyphToSide1Group")
        self.assertEqual(result, {'a': 'public.kern1.a'})
        del groups["public.kern1.a"]
        groups["public.kern1.b"] = ["a"]
        result = groups.getRepresentation("defcon.groups.kerningGlyphToSide1Group")
        self.assertEqual(result, {'a': 'public.kern1.b'})

    def test_side2glyphToKerningGroups(self):
        font = Font()
        groups = font.groups
        groups["public.kern2.a"] = ["a"]
        result = groups.getRepresentation("defcon.groups.kerningGlyphToSide2Group")
        self.assertEqual(result, {'a': 'public.kern2.a'})
        del groups["public.kern2.a"]
        groups["public.kern2.b"] = ["a"]
        result = groups.getRepresentation("defcon.groups.kerningGlyphToSide2Group")
        self.assertEqual(result, {'a': 'public.kern2.b'})

if __name__ == "__main__":
    unittest.main()
