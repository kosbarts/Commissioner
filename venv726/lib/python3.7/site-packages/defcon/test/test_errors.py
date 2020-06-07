import unittest
from defcon import DefconError


class DefconErrorTest(unittest.TestCase):

    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)
        if not hasattr(self, "assertRaisesRegex"):
            self.assertRaisesRegex = self.assertRaisesRegexp

    def test_DefconError(self):
        with self.assertRaisesRegex(DefconError, "foobar"):
            raise DefconError("foobar")

    def test_report(self):
        defconError = DefconError("foo")
        defconError.report = "bar"
        self.assertEqual(defconError.report, "bar")

if __name__ == "__main__":
    unittest.main()
