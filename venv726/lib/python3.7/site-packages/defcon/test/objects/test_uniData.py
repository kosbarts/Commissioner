import unittest
from defcon.objects.font import Font
from defcon.test.testTools import getTestFontPath


class UnicodeDataTest(unittest.TestCase):

    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)

    def test_removeGlyphData(self):
        path = getTestFontPath()
        font = Font(path)
        font.newGlyph("XXX")
        font.unicodeData.addGlyphData("XXX", [65])
        font.unicodeData.removeGlyphData("A", [65])
        self.assertEqual(font.unicodeData[65], ['XXX'])

    def test_addGlyphData(self):
        path = getTestFontPath()
        font = Font(path)
        font.newGlyph("XXX")
        font.unicodeData.addGlyphData("XXX", [1000])
        self.assertEqual(font.unicodeData[1000], ['XXX'])
        font.unicodeData.addGlyphData("XXX", [65])
        self.assertEqual(font.unicodeData[65], ['A', 'XXX'])

    def test_delitem(self):
        path = getTestFontPath()
        font = Font(path)
        del font.unicodeData[65]
        self.assertNotIn(65, font.unicodeData)
        font.unicodeData.glyphNameForUnicode(65)

        self.assertNotIn(0xBEAF, font.unicodeData)
        del font.unicodeData[0xBEAF]
        self.assertNotIn(0xBEAF, font.unicodeData)

    def test_setitem(self):
        path = getTestFontPath()
        font = Font(path)
        font.newGlyph("XXX")
        font.unicodeData[1000] = ["XXX"]
        self.assertEqual(font.unicodeData[1000], ['XXX'])
        font.unicodeData[65] = ["YYY"]
        self.assertEqual(font.unicodeData[65], ['A', 'YYY'])

    def test_clear(self):
        path = getTestFontPath()
        font = Font(path)
        font.unicodeData.clear()
        self.assertEqual(list(font.unicodeData.keys()), [])

    def test_update(self):
        path = getTestFontPath()
        font1 = Font(path)
        font2 = Font()
        font2.unicodeData.update(font1.unicodeData)
        self.assertEqual(font1.unicodeData, font2.unicodeData)

    def test_unicodeForGlyphName(self):
        path = getTestFontPath()
        font = Font(path)
        self.assertEqual(font.unicodeData.unicodeForGlyphName("A"), 65)

    def test_glyphNameForUnicode(self):
        path = getTestFontPath()
        font = Font(path)
        self.assertEqual(font.unicodeData.glyphNameForUnicode(65), 'A')

    def test_pseudoUnicodeForGlyphName(self):
        path = getTestFontPath()
        font = Font(path)
        self.assertEqual(font.unicodeData.pseudoUnicodeForGlyphName("A"), 65)
        font.newGlyph("A.foo")
        self.assertEqual(font.unicodeData.pseudoUnicodeForGlyphName("A.foo"),
                         65)
        font.newGlyph("B_A")
        self.assertEqual(font.unicodeData.pseudoUnicodeForGlyphName("B_A"), 66)

    def test_forcedUnicodeForGlyphName(self):
        path = getTestFontPath()
        font = Font(path)
        self.assertEqual(font.unicodeData.forcedUnicodeForGlyphName("A"), 65)
        font.newGlyph("B_A")
        self.assertEqual(font.unicodeData.forcedUnicodeForGlyphName("B_A"),
                         0xE000)
        font.newGlyph("B_B")
        self.assertEqual(font.unicodeData.forcedUnicodeForGlyphName("B_B"),
                         0xE001)

    def test_glyphNameForForcedUnicode(self):
        path = getTestFontPath()
        font = Font(path)
        self.assertEqual(font.unicodeData.glyphNameForForcedUnicode(65), "A")
        font.newGlyph("B_A")
        self.assertIsNone(font.unicodeData.glyphNameForForcedUnicode(0xE000))
        font.unicodeData.forcedUnicodeForGlyphName("B_A")
        self.assertEqual(font.unicodeData.glyphNameForForcedUnicode(0xE000),
                         "B_A")
        font.newGlyph("B_B")
        font.unicodeData.forcedUnicodeForGlyphName("B_B")
        self.assertEqual(font.unicodeData.glyphNameForForcedUnicode(0xE001),
                         "B_B")

    def test_scriptForGlyphName(self):
        path = getTestFontPath()
        font = Font(path)
        font.newGlyph("A.alt")
        self.assertEqual(font.unicodeData.scriptForGlyphName("A"), 'Latin')
        self.assertEqual(font.unicodeData.scriptForGlyphName("A.alt"), 'Latin')
        self.assertEqual(font.unicodeData.scriptForGlyphName("A.alt", False),
                         'Unknown')
        font.newGlyph("Alpha")
        font["Alpha"].unicode = 0x0391
        self.assertEqual(font.unicodeData.scriptForGlyphName("Alpha"), 'Greek')

    def test_blockForGlyphName(self):
        path = getTestFontPath()
        font = Font(path)
        font.newGlyph("A.alt")
        self.assertEqual(font.unicodeData.blockForGlyphName("A"),
                         'Basic Latin')
        self.assertEqual(font.unicodeData.blockForGlyphName("A.alt"),
                         'Basic Latin')
        self.assertEqual(font.unicodeData.blockForGlyphName("A.alt", False),
                         'No_Block')
        font.newGlyph("schwa")
        font["schwa"].unicode = 0x0259
        self.assertEqual(font.unicodeData.blockForGlyphName("schwa"),
                         'IPA Extensions')

    def test_categoryForGlyphName(self):
        path = getTestFontPath()
        font = Font(path)
        font.newGlyph("A.alt")
        self.assertEqual(font.unicodeData.categoryForGlyphName("A"), 'Lu')
        self.assertEqual(font.unicodeData.categoryForGlyphName("A.alt"), 'Lu')
        self.assertEqual(font.unicodeData.categoryForGlyphName("A.alt", False),
                         'Cn')

    def test_decompositionBaseForGlyphName(self):
        path = getTestFontPath()
        font = Font(path)
        font.newGlyph("Aacute")
        font["Aacute"].unicode = int("00C1", 16)
        self.assertEqual(
            font.unicodeData.decompositionBaseForGlyphName("Aacute", True),
            'A')
        font.newGlyph("Aringacute")
        font["Aringacute"].unicode = int("01FA", 16)
        self.assertEqual(
            font.unicodeData.decompositionBaseForGlyphName("Aringacute", True),
            'A')
        font.newGlyph("Aacute.alt")
        self.assertEqual(
            font.unicodeData.decompositionBaseForGlyphName("Aacute.alt", True),
            'A')
        font.newGlyph("A.alt")
        self.assertEqual(
            font.unicodeData.decompositionBaseForGlyphName("Aacute.alt", True),
            'A.alt')

    def test_closeRelativeForGlyphName(self):
        font = Font()
        font.newGlyph("parenleft")
        font["parenleft"].unicode = int("0028", 16)
        font.newGlyph("parenright")
        font["parenright"].unicode = int("0029", 16)
        font.newGlyph("parenleft.alt")
        font.newGlyph("parenright.alt")
        self.assertEqual(
            font.unicodeData.closeRelativeForGlyphName("parenleft", True),
            'parenright')
        self.assertEqual(
            font.unicodeData.closeRelativeForGlyphName("parenleft.alt", True),
            'parenright.alt')
        del font["parenright.alt"]
        self.assertEqual(
            font.unicodeData.closeRelativeForGlyphName("parenleft.alt", True),
            'parenright')

    def test_openRelativeForGlyphName(self):
        font = Font()
        font.newGlyph("parenleft")
        font["parenleft"].unicode = int("0028", 16)
        font.newGlyph("parenright")
        font["parenright"].unicode = int("0029", 16)
        font.newGlyph("parenleft.alt")
        font.newGlyph("parenright.alt")
        self.assertEqual(
            font.unicodeData.openRelativeForGlyphName("parenright", True),
            'parenleft')
        self.assertEqual(
            font.unicodeData.openRelativeForGlyphName("parenright.alt", True),
            'parenleft.alt')
        del font["parenleft.alt"]
        self.assertEqual(
            font.unicodeData.openRelativeForGlyphName("parenright.alt", True),
            'parenleft')


class SortGlyphNamesTest(unittest.TestCase):

    def setUp(self):
        self.font = font = Font()
        font.newGlyph("a")
        font["a"].unicode = 0x0061
        font.newGlyph("b")
        font["b"].unicode = 0x0062
        font.newGlyph("c")
        font["c"].unicode = 0x0063
        font.newGlyph("alpha")
        font["alpha"].unicode = 0x03B1
        font.newGlyph("aacute")
        font["aacute"].unicode = 0x00E1
        font.newGlyph("comma")
        font["comma"].unicode = 0x002C
        font.newGlyph("schwa")
        font["schwa"].unicode = 0x0259
        font.newGlyph("undefined")

    def tearDown(self):
        del self.font

    def test_sortGlyphNames_unicode(self):
        font = self.font
        self.assertEqual(
            font.unicodeData.sortGlyphNames(["a", "c", "b"]),
            ["a", "b", "c"]
        )
        self.assertEqual(
            font.unicodeData.sortGlyphNames(
                ["a.suf1", "a.suf2", "a", "b"]),
            ["a", "b", "a.suf1", "a.suf2"]
        )
        self.assertEqual(
            font.unicodeData.sortGlyphNames(
                ["a.suf1", "a.suf2", "a", "b"],
                sortDescriptors=[dict(type="unicode", allowPseudoUnicode=True)]
            ),
            ["a", "a.suf1", "a.suf2", "b"]
        )
        self.assertEqual(
            font.unicodeData.sortGlyphNames(
                ["a", "b", "c"],
                sortDescriptors=[dict(type="unicode", ascending=False)]
            ),
            ["c", "b", "a"]
        )

    def test_sortGlyphNames_alphabetical(self):
        font = self.font
        self.assertEqual(
            font.unicodeData.sortGlyphNames(
                ["b", "c", "a.suf1", "a.suf2", "a"],
                sortDescriptors=[dict(type="alphabetical")]
            ),
            ["a", "a.suf1", "a.suf2", "b", "c"]
        )
        self.assertEqual(
            font.unicodeData.sortGlyphNames(
                ["a.suf1", "a.suf2", "a", "b", "c"],
                sortDescriptors=[dict(type="alphabetical", ascending=False)]
            ),
            ["c", "b", "a.suf2", "a.suf1", "a"]
        )

    def test_sortGlyphNames_multiple_sortDescriptors(self):
        font = self.font
        self.assertEqual(
            font.unicodeData.sortGlyphNames(
                ["a.suf1", "a.suf2", "a", "b", "c"],
                sortDescriptors=[
                    dict(type="alphabetical", ascending=False),
                    dict(type="suffix")
                ]
            ),
            ["c", "b", "a", "a.suf1", "a.suf2"]
        )
        self.assertEqual(
            font.unicodeData.sortGlyphNames(
                ["a.suf1", "a.suf2", "a", "b", "c"],
                sortDescriptors=[
                    dict(type="alphabetical"),
                    dict(type="suffix", ascending=False)
                ]
            ),
            ["a", "b", "c", "a.suf1", "a.suf2"]
            # XXX: ["a.suf2", "a.suf1", "a", "b", "c"]
        )

    def test_sortGlyphNames_script(self):
        font = self.font
        self.assertEqual(
            font.unicodeData.sortGlyphNames(
                ["b", "alpha", "a"],
                sortDescriptors=[dict(type="script")]
            ),
            ["b", "a", "alpha"]
        )
        self.assertEqual(
            font.unicodeData.sortGlyphNames(
                ["b", "alpha", "a"],
                sortDescriptors=[dict(type="script", ascending=False)]
            ),
            ["alpha", "b", "a"]
        )
        self.assertEqual(
            font.unicodeData.sortGlyphNames(
                ["b", "alpha", "a", "a.suf1", "a.suf2"],
                sortDescriptors=[dict(type="script")]
            ),
            ["b", "a", "alpha", "a.suf1", "a.suf2"]
        )
        self.assertEqual(
            font.unicodeData.sortGlyphNames(
                ["b", "alpha", "a", "a.suf1", "a.suf2"],
                sortDescriptors=[dict(type="script", allowPseudoUnicode=True)]
            ),
            ["b", "a", "a.suf1", "a.suf2", "alpha"]
        )

    def test_sortGlyphNames_category(self):
        font = self.font
        self.assertEqual(
            font.unicodeData.sortGlyphNames(
                ["b", "comma", "a"],
                sortDescriptors=[dict(type="category")]
            ),
            ["b", "a", "comma"]
        )
        self.assertEqual(
            font.unicodeData.sortGlyphNames(
                ["b", "comma", "a"],
                sortDescriptors=[dict(type="category", ascending=False)]
            ),
            ["comma", "b", "a"]
        )
        self.assertEqual(
            font.unicodeData.sortGlyphNames(
                ["b", "a.suf1", "a.suf2", "comma", "a"],
                sortDescriptors=[
                    dict(type="category")
                ]
            ),
            ["b", "a", "comma", "a.suf1", "a.suf2"]
        )
        self.assertEqual(
            font.unicodeData.sortGlyphNames(
                ["b", "a.suf1", "a.suf2", "comma", "a"],
                sortDescriptors=[
                    dict(type="category", allowPseudoUnicode=True)
                ]
            ),
            ["b", "a.suf1", "a.suf2", "a", "comma"]
        )

    def test_sortGlyphNames_block(self):
        font = self.font
        self.assertEqual(
            font.unicodeData.sortGlyphNames(
                ["b", "schwa", "a", "undefined"],
                sortDescriptors=[dict(type="block")]
            ),
            ["b", "a", "schwa"]
        )
        self.assertEqual(
            font.unicodeData.sortGlyphNames(
                ["b", "schwa", "a", "undefined"],
                sortDescriptors=[dict(type="block", ascending=False)]
            ),
            ["schwa", "b", "a"]
        )

    def test_sortGlyphNames_suffix(self):
        font = self.font
        self.assertEqual(
            font.unicodeData.sortGlyphNames(
                ["b", "a.suf2", "a", "a.suf1", "c"],
                sortDescriptors=[dict(type="suffix")]
            ),
            ["b", "a", "c", "a.suf1", "a.suf2"]
        )
        self.assertEqual(
            font.unicodeData.sortGlyphNames(
                ["b", "a.suf2", "a", "a.suf1", "c"],
                sortDescriptors=[dict(type="suffix", ascending=False)]
            ),
            ["b", "a", "c", "a.suf1", "a.suf2"]
            # XXX: ["a.suf2", "a.suf1", "b", "a", "c"]?
        )
        self.assertEqual(
            font.unicodeData.sortGlyphNames(
                ["b", "a.suf2", "a", "a.suf1", "c"],
                sortDescriptors=[dict(type="suffix", allowPseudoUnicode=True)]
            ),
            ["b", "a", "c", "a.suf1", "a.suf2"]
        )
        self.assertEqual(
            font.unicodeData.sortGlyphNames(
                ["b", "a.suf2", "a", "a.suf1", "c"],
                sortDescriptors=[
                    dict(type="suffix", ascending=False,
                         allowPseudoUnicode=True)]
            ),
            ["b", "a", "c", "a.suf1", "a.suf2"]
            # XXX: ["a.suf2", "a.suf1", "b", "a", "c"]?
        )

    def test_sortGlyphNames_decompositionBase(self):
        font = self.font
        self.assertEqual(
            font.unicodeData.sortGlyphNames(
                ["a", "a.alt", "aacute", "aacute.alt"],
                sortDescriptors=[dict(type="decompositionBase")]
            ),
            ["a", "aacute", "a.alt", "aacute.alt"]
        )
        self.assertEqual(
            font.unicodeData.sortGlyphNames(
                ["a", "a.alt", "aacute", "aacute.alt"],
                sortDescriptors=[
                    dict(type="decompositionBase", ascending=False)]
            ),
            ["aacute.alt", "a.alt", "a", "aacute"]
        )

    def test_sortGlyphNames_weightedSuffix(self):
        font = self.font
        self.assertEqual(
            font.unicodeData.sortGlyphNames(
                ["a", "a.alt", "aacute", "aacute.alt", "b", "b.suf1",
                 "b.suf2", "b.suf3", "a.sc"],
                sortDescriptors=[dict(type="weightedSuffix")]
            ),
            ["a", "aacute", "b", "a.alt", "aacute.alt", "a.sc", "b.suf1",
             "b.suf2", "b.suf3"]
        )
        self.assertEqual(
            font.unicodeData.sortGlyphNames(
                ["a", "a.alt", "aacute", "aacute.alt", "b", "b.suf1",
                 "b.suf2", "b.suf3", "a.sc"],
                sortDescriptors=[
                    dict(type="weightedSuffix", ascending=False)]
            ),
            ["b.suf3", "b.suf2", "b.suf1", "a.sc", "aacute.alt", "a.alt", "a",
             "aacute", "b", ]
        )

    def test_sortGlyphNames_ligature(self):
        font = self.font
        self.assertEqual(
            font.unicodeData.sortGlyphNames(
                ["b", "a", "a_b", "c", "c_a"],
                sortDescriptors=[dict(type="ligature")]),
            ["b", "a", "c", "a_b", "c_a"]
        )
        self.assertEqual(
            font.unicodeData.sortGlyphNames(
                ["b", "a", "a_b", "c", "c_a"],
                sortDescriptors=[dict(type="ligature", ascending=False)]),
            ["c_a", "a_b", "c", "a", "b"]
        )

    def test_sortGlyphNames_cannedDesign(self):
        font = self.font
        self.assertEqual(
            font.unicodeData.sortGlyphNames(
                ["b", "a", "a_b", "c", "c_a", "a.alt", "a.suf1", "b.suf1",
                 "a.suf2", "b.suf2", "schwa", "alpha", "comma", "aacute",
                 "aacute.alt"],
                sortDescriptors=[dict(type="cannedDesign")]),
            ["a", "aacute", "b", "c", "schwa", "alpha", "comma", "a_b", "c_a",
             "a.alt", "aacute.alt", "a.suf1", "b.suf1", "a.suf2", "b.suf2"]
        )
        self.assertEqual(
            font.unicodeData.sortGlyphNames(
                ["b", "a", "a_b", "c", "c_a", "a.alt", "a.suf1", "b.suf1",
                 "a.suf2", "b.suf2", "schwa", "alpha", "comma", "aacute",
                 "aacute.alt"],
                sortDescriptors=[dict(type="cannedDesign", ascending=False)]),
            ["b.suf2", "a.suf2", "b.suf1", "a.suf1", "aacute.alt", "a.alt",
             "c_a", "a_b", "comma", "alpha", "schwa", "c", "b", "aacute", "a"]
        )

    def test_sortGlyphNames_custom(self):
        font = self.font

        def sortByE(font, glyphNames, ascending=True,
                    allowsPseudoUnicodes=False):
            startsWithE = []
            doesNotStartWithE = []
            for glyphName in glyphNames:
                if glyphName.startswith("E"):
                    startsWithE.append(glyphName)
                else:
                    doesNotStartWithE.append(glyphName)
            return [startsWithE, doesNotStartWithE]

        self.assertEqual(
            font.unicodeData.sortGlyphNames(
                ["A", "B", "C", "D", "E", "Eacute", "Egrave"],
                sortDescriptors=[dict(type="custom", function=sortByE)]),
            ["E", "Eacute", "Egrave", "A", "B", "C", "D"]
        )

    def test_endSelfNotificationObservation(self):
        font = Font()
        self.assertIsNotNone(font.unicodeData.dispatcher)
        self.assertIsNotNone(font.unicodeData.font)
        self.assertIsNotNone(font.unicodeData.layerSet)
        self.assertIsNotNone(font.unicodeData.layer)

        font.unicodeData.endSelfNotificationObservation()

        self.assertIsNone(font.unicodeData.dispatcher)
        self.assertIsNone(font.unicodeData.font)
        self.assertIsNone(font.unicodeData.layerSet)
        self.assertIsNone(font.unicodeData.layer)


if __name__ == "__main__":
    unittest.main()
