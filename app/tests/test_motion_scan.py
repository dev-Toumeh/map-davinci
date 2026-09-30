"""Camera motion extraction from an actual encoded synthetic map video."""
import tempfile
import unittest
from pathlib import Path

from core.motion_scan import _gaps, _rapid_changes, scan


class MotionScanTests(unittest.TestCase):
    def test_tracks_pan_in_each_direction_and_zoom_reversal(self):
        try:
            import cv2
            import numpy as np
        except ImportError:
            self.skipTest("OpenCV and NumPy are needed for motion scanning")
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            rng = np.random.default_rng(7)
            map_image = rng.integers(0, 256, (900, 900, 3), dtype=np.uint8)
            map_path = folder / "wide.png"
            cv2.imwrite(str(map_path), map_image)
            video_path = folder / "reference.mp4"
            writer = cv2.VideoWriter(str(video_path), cv2.VideoWriter_fourcc(*"mp4v"),
                                     10, (320, 320))
            self.assertTrue(writer.isOpened())
            views = [(0.50, 0.50, .42), (0.60, 0.42, .30),
                     (0.40, 0.60, .30), (0.50, 0.50, .42)]
            for frame in range(40):
                segment = frame // 10
                if segment == 3:
                    x, y, width = views[3]
                else:
                    fraction = (frame % 10) / 10
                    x, y, width = [views[segment][part] * (1 - fraction) +
                                   views[segment + 1][part] * fraction for part in range(3)]
                pixels = round(width * 900)
                center_x, center_y = round(x * 900), round(y * 900)
                crop = map_image[center_y - pixels // 2:center_y - pixels // 2 + pixels,
                                 center_x - pixels // 2:center_x - pixels // 2 + pixels]
                writer.write(cv2.resize(crop, (320, 320)))
            writer.release()

            result = scan(video_path, map_path,
                          {"width": 900, "height": 900, "wide_factor": 2},
                          {"width": 320, "height": 320, "fps": 24})

        self.assertGreaterEqual(result["tracked_count"], 6)
        self.assertEqual(result["duration_frames"], 96)
        self.assertEqual(result["keyframes"][0]["frame"], 0)
        self.assertEqual(result["keyframes"][-1]["frame"], 95)
        samples = [item for item in result["samples"] if item["tracked"]]
        at = lambda time: min(samples, key=lambda item: abs(item["time"] - time))
        self.assertGreater(at(1)["center"]["x"], at(0)["center"]["x"])
        self.assertLess(at(2)["center"]["x"], at(1)["center"]["x"])
        self.assertLess(at(1)["center"]["y"], at(0)["center"]["y"])
        self.assertGreater(at(2)["center"]["y"], at(1)["center"]["y"])
        self.assertLess(at(1)["view_width"], at(0)["view_width"])
        self.assertGreater(at(3)["view_width"], at(2)["view_width"])

    def test_low_confidence_samples_are_reported_as_a_review_gap(self):
        samples = [{"time": t, "tracked": tracked} for t, tracked in
                   [(0, True), (.5, False), (1, False), (1.5, True)]]
        self.assertEqual(_gaps(samples, .5), [{"start": .5, "end": 1.5}])

    def test_abrupt_zoom_is_reported_for_review(self):
        samples = [
            {"time": 0, "tracked": True, "center": {"x": .5, "y": .5}, "view_width": .3},
            {"time": .5, "tracked": True, "center": {"x": .5, "y": .5}, "view_width": .15},
        ]
        self.assertEqual(_rapid_changes(samples, .5), [{"start": 0, "end": .5}])


if __name__ == "__main__":
    unittest.main()
