import unittest

from tools.build_cartographic_instance_prototype import _border_instance


class CartographicInstancePrototypeTests(unittest.TestCase):
    def test_border_is_instance_without_polyline_copy(self):
        block = _border_instance("Border", "Fill", 2, ("1", "2"))
        self.assertIn('SourceOp = "Fill"', block)
        self.assertEqual(block.count(".Solid\"]"), 2)
        self.assertEqual(block.count(".BorderWidth\"]"), 2)
        self.assertNotIn(".Polyline\"]", block)


if __name__ == "__main__":
    unittest.main()
