import unittest

from tools.build_closeup_lod_prototype import _camera, _local_samples, _replace_source


class CloseupLodPrototypeTests(unittest.TestCase):
    def test_local_camera_is_centered_and_uses_plate_margin_as_zoom(self):
        animation = {
            "keyframes": [
                {"frame": 0, "center": {"x": .5, "y": .5},
                 "view_width": .1, "easing": "linear"},
                {"frame": 10, "center": {"x": .6, "y": .5},
                 "view_width": .1, "easing": "linear"},
            ]
        }
        self.assertEqual(_camera(animation, 5), (.55, .5, .1))
        samples = _local_samples(animation, (.475, .4, .625, .6), 5, 5)
        self.assertAlmostEqual(samples[0]["zoom"], 1.5)
        self.assertAlmostEqual(samples[0]["fusion_path"]["x"], 0)
        self.assertAlmostEqual(samples[0]["fusion_path"]["y"], 0)

    def test_rewire_changes_only_the_named_fusion_node(self):
        text = '''Composition {
\tTools = {
\t\tMap_Animation = Transform {
\t\t\tInputs = { Input = Input { SourceOp = "Old", Source = "Output", } },
\t\t},
\t\tOther = Transform {
\t\t\tInputs = { Input = Input { SourceOp = "Old", Source = "Output", } },
\t\t},
\t}
}'''
        updated = _replace_source(text, "Map_Animation", "Transform", "Old", "New")
        self.assertEqual(updated.count('SourceOp = "New"'), 1)
        self.assertEqual(updated.count('SourceOp = "Old"'), 1)


if __name__ == "__main__":
    unittest.main()
