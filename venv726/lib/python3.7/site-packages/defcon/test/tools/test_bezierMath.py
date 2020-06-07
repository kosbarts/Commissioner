import unittest
from defcon.tools.bezierMath import joinSegments


class TestBezierMath(unittest.TestCase):

    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)

    def test_joinSegments(self):
        joined = joinSegments((0, 0), (0, 138), (112, 250), (250, 250),
                              (250, 388), (500, 138), (500, 0))
        self.assertEqual(
            joined,
            ((0.0, 276.0), (500.0, 276.0), (500, 0))
        )
        # XXX in defcon/tools/bezierMath.py, the docstring was expecting
        # ((0.0, 195.16147160748713), (500.0, 471.16147160748704), (500, 0))
        # instead of ((0.0, 276.0), (500.0, 276.0), (500, 0))

    # TODO: need more tests!
