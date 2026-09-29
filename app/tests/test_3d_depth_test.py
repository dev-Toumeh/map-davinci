import tempfile
import unittest
from pathlib import Path

from tools.build_3d_depth_test import build


SOURCE = '''Composition {
\tCurrentTime = 0, RenderRange = { 0, 2231 }, GlobalRange = { 0, 2231 },
\tTools = {
\t\tMap_Quality_Switch = Switch { Inputs = { Which = Input { Value = 0, }, }, },
\t\tMap_Working_Canvas = Merge { Inputs = {}, },
\t\tCountry_Edit_01_Render = sRender { Inputs = {}, },
\t\tFinal_Composite = Merge { Inputs = {}, },
\t\tVector_Layers = MultiMerge { Inputs = { Background = Input { SourceOp = "Final_Composite", Source = "Output", }, }, },
\t}
}
'''


class DepthTestBuilderTests(unittest.TestCase):
    def test_builds_short_aligned_2d_3d_comparison(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source.comp"
            target = Path(folder) / "target.comp"
            source.write_text(SOURCE)
            report = build(source, target)
            result = target.read_text()
        self.assertEqual(report["shot_frames"], [305, 396])
        self.assertIn("CurrentTime = 371", result)
        self.assertIn("RenderRange = { 305, 396 }", result)
        self.assertIn('Input = Input { SourceOp = "Map_Working_Canvas"', result)
        self.assertIn(
            'MaterialInput = Input { SourceOp = "Depth_Test_Ground_Texture"', result)
        self.assertIn(
            'Input = Input { SourceOp = "Country_Edit_01_Render"', result)
        self.assertIn(
            'MaterialInput = Input { SourceOp = "Depth_Test_Territory_Texture"', result)
        self.assertIn('["Transform3DOp.Translate.Z"] = Input { Value = 0.065', result)
        self.assertIn('["Transform3DOp.UseTarget"] = Input { Value = 1', result)
        self.assertIn("Depth_Test_Renderer = Renderer3D", result)
        self.assertIn('Name0 = Input { Value = "2D BASELINE - 540x960"', result)
        self.assertIn('Name1 = Input { Value = "3D DEPTH - 540x960"', result)
        self.assertIn('SourceOp = "Depth_Test_2D_3D"', result)
        quality = result.split("Map_Quality_Switch", 1)[1].split(
            "Map_Working_Canvas", 1)[0]
        self.assertIn("Which = Input { Value = 1", quality)


if __name__ == "__main__":
    unittest.main()
