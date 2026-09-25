import unittest

from tools.share_map_center_controller import CENTER_LINK


class SharedMapCenterTests(unittest.TestCase):
    def test_finds_generated_center_link(self):
        value = '["PolyMask12.Center"] = Input { SourceOp = "Vector_AnimationPath", Source = "Position", },'
        match = CENTER_LINK.fullmatch(value)
        self.assertIsNotNone(match)
        self.assertEqual(match.group("index"), "12")


if __name__ == "__main__":
    unittest.main()
