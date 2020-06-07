#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import unittest
from defcon.tools.unicodeTools import (
    decompositionBase, openRelative, closeRelative, category, script, block
)


class UnicodeToolsTest(unittest.TestCase):

    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)

    def test_decompositionBase(self):
        self.assertEqual(decompositionBase(ord("ç")), ord("c"))
        self.assertEqual(decompositionBase(ord("a")), -1)
        self.assertEqual(decompositionBase(0x0001000), -1)

    def test_openRelative(self):
        self.assertEqual(openRelative(ord(")")), ord("("))
        self.assertIsNone(openRelative(ord("a")))
        self.assertIsNone(openRelative(0x0001000))

    def test_closeRelative(self):
        self.assertEqual(closeRelative(ord("(")), ord(")"))
        self.assertIsNone(closeRelative(ord("a")))
        self.assertIsNone(closeRelative(0x0001000))

    def test_category(self):
        self.assertEqual(category(ord("a")), "Ll")
        self.assertEqual(category(0x0001000), "Lo")

    def test_script(self):
        self.assertEqual(script(ord("a")), "Latin")
        self.assertEqual(script(0x00010000), "Linear B")

    def test_block(self):
        self.assertEqual(block(ord("a")), "Basic Latin")
        self.assertEqual(block(0x00010000), "Linear B Syllabary")
