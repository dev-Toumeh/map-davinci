import unittest

from fusion.closeup_lod import local_samples, plan_closeups


class CloseupLodTests(unittest.TestCase):
    def metadata(self):
        return {
            "output": {"width": 3840, "height": 2160, "wide_factor": 2},
            "wide": {"bbox_mercator": {"minx": 0, "miny": 0,
                                         "maxx": 100, "maxy": 100}},
        }

    def animation(self, width):
        return {
            "output": {"width": 2160, "height": 3840,
                       "duration_frames": 101},
            "keyframes": [
                {"frame": 0, "center": {"x": .5, "y": .5},
                 "view_width": .2, "easing": "smooth"},
                {"frame": 50, "center": {"x": .5, "y": .5},
                 "view_width": width, "easing": "smooth"},
                {"frame": 100, "center": {"x": .5, "y": .5},
                 "view_width": .2, "easing": "smooth"},
            ],
        }

    def test_only_deep_zoom_creates_a_closeup(self):
        self.assertEqual(plan_closeups(self.metadata(), self.animation(.05)), [])
        plans = plan_closeups(self.metadata(), self.animation(.01))
        self.assertEqual(len(plans), 1)
        self.assertEqual(plans[0]["frame"], 50)
        self.assertLess(plans[0]["first"], 50)
        self.assertGreater(plans[0]["last"], 50)

    def test_local_camera_is_centered_at_target(self):
        animation = self.animation(.01)
        plan = plan_closeups(self.metadata(), animation)[0]
        sample = next(item for item in local_samples(
            animation, plan["normalized_bbox"], plan["first"], plan["last"])
                      if item["frame"] == 50)
        self.assertAlmostEqual(sample["fusion_path"]["x"], 0)
        self.assertAlmostEqual(sample["fusion_path"]["y"], 0)
        self.assertAlmostEqual(sample["zoom"], 1.5)


if __name__ == "__main__":
    unittest.main()
