import unittest

from tools.build_expression_vector_camera import _curve


class ExpressionVectorCameraTests(unittest.TestCase):
    def test_curve_contains_only_authored_keys(self):
        keys = [
            {"frame": 0, "value": 0.0, "easing": "linear"},
            {"frame": 10, "value": 1.0, "easing": "smooth"},
        ]
        curve = _curve(keys, "value", (1, 2, 3))
        self.assertEqual(curve.count("Flags"), 0)
        self.assertEqual(curve.count("[0] ="), 1)
        self.assertEqual(curve.count("[10] ="), 1)
        self.assertIn("RH = { 3.33333333333, 0 }", curve)
        self.assertIn("LH = { 6.66666666667, 1 }", curve)


if __name__ == "__main__":
    unittest.main()
