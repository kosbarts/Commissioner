import unittest
from defcon.objects.color import Color


class ColorTest(unittest.TestCase):

    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)

    def test_from_string(self):
        self.assertEqual(tuple(Color("1,1,1,1")), (1, 1, 1, 1))
        self.assertEqual(tuple(Color(".1,.1,.1,.1")),
                         (0.10000000000000001, 0.10000000000000001,
                          0.10000000000000001, 0.10000000000000001))
        self.assertEqual(tuple(Color("1, 1, 1, 1")), (1, 1, 1, 1))
        self.assertEqual(tuple(Color("0.1, 0.1, 0.1, 0.1")),
                         (0.10000000000000001, 0.10000000000000001,
                          0.10000000000000001, 0.10000000000000001))

    def test_from_tuple(self):
        self.assertEqual(tuple(Color((1, 1, 1, 1))), (1, 1, 1, 1))

    def test_to_string(self):
        self.assertEqual(Color((0, 0, 0, 0)), "0,0,0,0")
        self.assertEqual(Color((1, .1, .01, .001)), "1,0.1,0.01,0.001")
        self.assertEqual(Color((.0001, .00001, .000001, .000005)),
                         "0.0001,0.00001,0,0.00001")

    def test_to_sequence(self):
        self.assertEqual(tuple(Color((1, 1, 1, 1))), (1, 1, 1, 1))

    def test_component_attributes(self):
        c = Color((.1, .2, .3, .4))
        self.assertEqual(c.r, 0.10000000000000001)
        self.assertEqual(c.g, 0.20000000000000001)
        self.assertEqual(c.b, 0.29999999999999999)
        self.assertEqual(c.a, 0.40000000000000002)

    def test_invalid_values_negative(self):
        with self.assertRaises(
                ValueError,
                msg="The color for r (-1) is not between 0 and 1."):
            Color((-1, 0, 0, 0))
        with self.assertRaises(
                ValueError,
                msg="The color for g (-1) is not between 0 and 1."):
            Color((0, -1, 0, 0))
        with self.assertRaises(
                ValueError,
                msg="The color for b (-1) is not between 0 and 1."):
            Color((0, 0, -1, 0))
        with self.assertRaises(
                ValueError,
                msg="The color for a (-1) is not between 0 and 1."):
            Color((0, 0, 0, -1))

    def test_invalid_values_too_large(self):
        with self.assertRaises(
                ValueError,
                msg="The color for r (2) is not between 0 and 1."):
            Color((2, 0, 0, 0))
        with self.assertRaises(
                ValueError,
                msg="The color for g (2) is not between 0 and 1."):
            Color((0, 2, 0, 0))
        with self.assertRaises(
                ValueError,
                msg="The color for b (2) is not between 0 and 1."):
            Color((0, 0, 2, 0))
        with self.assertRaises(
                ValueError,
                msg="The color for a (2) is not between 0 and 1."):
            Color((0, 0, 0, 2))

    def test_iterate_component_attributes(self):
        color = Color((0.1, 0.2, 0.3, 0.4))
        expected_values = (0.10000000000000001, 0.20000000000000001,
                           0.29999999999999999, 0.40000000000000002)
        for index, component_attribute in enumerate(color):
            self.assertEqual(component_attribute, expected_values[index])

if __name__ == "__main__":
    unittest.main()
