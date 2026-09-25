import unittest

from tools.reduce_fusion_points import _reduce_ring


class ReduceFusionPointsTests(unittest.TestCase):
    def test_reduces_collinear_closed_ring_without_losing_corners(self):
        ring = [(0, 0), (.5, 0), (1, 0), (1, .5), (1, 1),
                (.5, 1), (0, 1), (0, .5)]
        reduced = _reduce_ring(ring, .01)
        self.assertEqual(set(reduced), {(0, 0), (1, 0), (1, 1), (0, 1)})

    def test_never_reduces_triangle_below_three_points(self):
        triangle = [(0, 0), (1, 0), (0, 1)]
        self.assertEqual(_reduce_ring(triangle, 10), triangle)


if __name__ == "__main__":
    unittest.main()
