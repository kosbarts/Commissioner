import unittest
from defcon.tools.fuzzyNumber import FuzzyNumber


class TestFuzzyNumber(unittest.TestCase):

    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)

    def test_init(self):
        fuzzyNumber1 = FuzzyNumber(value=0, threshold=1)
        fuzzyNumber2 = FuzzyNumber(2, 3)
        self.assertEqual([fuzzyNumber1.value, fuzzyNumber1.threshold],
                         [0, 1])
        self.assertEqual([fuzzyNumber2.value, fuzzyNumber2.threshold],
                         [2, 3])

    def test_repr(self):
        fuzzyNumber = FuzzyNumber(0, 1)
        self.assertEqual(repr(fuzzyNumber), "[0.000000 1.000000]")

    def test_comparison(self):
        fuzzyNumber1 = FuzzyNumber(value=0, threshold=1)
        # self.assertEqual(fuzzyNumber1, 0)
        self.assertTrue(fuzzyNumber1 < 1)
        self.assertFalse(fuzzyNumber1 < -0.000001)
        self.assertFalse(fuzzyNumber1 < 0)

        fuzzyNumber2 = FuzzyNumber(value=0.999999, threshold=1)
        self.assertEqual(
            repr(sorted([fuzzyNumber1, fuzzyNumber2])),
            "[[0.000000 1.000000], [0.999999 1.000000]]"
        )
        self.assertFalse(fuzzyNumber1 < fuzzyNumber2)

        fuzzyNumber2 = FuzzyNumber(value=1, threshold=1)
        self.assertEqual(
            repr(sorted([fuzzyNumber1, fuzzyNumber2])),
            "[[0.000000 1.000000], [1.000000 1.000000]]"
        )
        self.assertTrue(fuzzyNumber1 < fuzzyNumber2)

        fuzzyNumber2 = FuzzyNumber(value=-0.999999, threshold=1)
        self.assertEqual(
            repr(sorted([fuzzyNumber1, fuzzyNumber2])),
            "[[0.000000 1.000000], [-0.999999 1.000000]]"
        )
        self.assertFalse(fuzzyNumber1 > fuzzyNumber2)

        fuzzyNumber2 = FuzzyNumber(value=-1, threshold=1)
        self.assertEqual(
            repr(sorted([fuzzyNumber1, fuzzyNumber2])),
            "[[-1.000000 1.000000], [0.000000 1.000000]]"
        )
        self.assertTrue(fuzzyNumber1 > fuzzyNumber2)
