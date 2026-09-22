"""Camera projection regression checks; run with unittest discover -s app."""
import math
import re
import unittest

from fusion_generator import _camera_samples, _path_points


class CameraProjectionTests(unittest.TestCase):
    def test_browser_projection_at_every_frame(self):
        for output in [(2160, 3840), (1920, 1080), (1080, 1080)]:
            for easing in ["linear", "smooth"]:
                with self.subTest(output=output, easing=easing):
                    animation = {"output": {"width": output[0], "height": output[1]},
                                 "keyframes": [
                                     {"frame": 0, "center": {"x": .45, "y": .35}, "view_width": .25},
                                     {"frame": 52, "center": {"x": .55, "y": .4},
                                      "view_width": .04, "easing": easing}]}
                    samples = _camera_samples(animation, {"width": 3840, "height": 2160})
                    # Read serialized geometry and reconstruct the exported path.
                    points = [(float(x), float(y)) for x, y in re.findall(
                        r"X = ([\d.e+-]+), Y = ([\d.e+-]+)", _path_points(samples))]
                    lengths = [0.0]
                    for p, q in zip(points, points[1:]):
                        lengths.append(lengths[-1] + math.dist(p, q))
                    for frame, sample in enumerate(samples):
                        t = frame / 52
                        if easing == "smooth":
                            t = 3 * t**2 - 2 * t**3
                        cx, cy, width = .45 + .1*t, .35 + .05*t, .25 - .21*t
                        distance = sample["displacement"] * lengths[-1]
                        j = next((i for i in range(1, len(lengths)) if lengths[i] >= distance), len(lengths)-1)
                        u = (distance-lengths[j-1])/(lengths[j]-lengths[j-1])
                        dx, dy = [points[j-1][axis] + u*(points[j][axis]-points[j-1][axis]) for axis in (0, 1)]
                        # Project an arbitrary landmark through source Transform then centered Merge.
                        px, py = .47, .38
                        fusion_x = output[0]/2 + 3840*((px-.5)*sample["zoom"]+dx)
                        fusion_y = output[1]/2 + 2160*((py-.5)*sample["zoom"]-dy)
                        browser_x = output[0]/2 + (px-cx)*output[0]/width
                        browser_y = output[1]/2 + (py-cy)*output[0]/width*2160/3840
                        self.assertAlmostEqual(fusion_x, browser_x, places=6)
                        self.assertAlmostEqual(fusion_y, browser_y, places=6)

    def test_hold_and_single_key(self):
        key = {"frame": 5, "center": {"x": .6, "y": .4}, "view_width": .2}
        animation = {"output": {"width": 2160, "height": 3840}, "keyframes": [key]}
        native = {"width": 3840, "height": 2160}
        single = _camera_samples(animation, native)
        self.assertEqual(len(single), 1)
        self.assertEqual(single[0]["displacement"], 0)
        animation["keyframes"].append({**key, "frame": 15})
        held = _camera_samples(animation, native)
        self.assertTrue(all(s["fusion_path"] == single[0]["fusion_path"] for s in held))
        self.assertEqual(_path_points(held).count("Linear = true"), 2)

    def test_explicit_calibration_preserved(self):
        animation = {"output": {"width": 2160, "height": 3840}, "keyframes": [
            {"frame": 0, "center": {"x": .5, "y": .5}, "view_width": .2,
             "fusion_path": {"x": .1, "y": -.2}},
            {"frame": 10, "center": {"x": .6, "y": .4}, "view_width": .1,
             "fusion_path": {"x": .3, "y": -.4}}]}
        samples = _camera_samples(animation, {"width": 3840, "height": 2160})
        for sample, key in [(samples[0], animation["keyframes"][0]), (samples[-1], animation["keyframes"][-1])]:
            for axis in ["x", "y"]:
                self.assertAlmostEqual(sample["fusion_path"][axis], key["fusion_path"][axis])


if __name__ == "__main__":
    unittest.main()
