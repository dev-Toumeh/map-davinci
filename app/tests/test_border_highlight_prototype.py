"""Regression checks for the manually controlled Fusion border prototype."""
import tempfile
import unittest
from pathlib import Path

from tools.build_border_highlight_prototype import build


SOURCE = '''Composition {
\tTools = ordered() {
\t\tEGY_Entire_Ring_01_Fill = sPolygon { Inputs = {
\t\t\tPolyline = Input { Value = Polyline { Closed = true, Points = {
\t\t\t\t{ Linear = true, X = -0.1, Y = -0.2 },
\t\t\t\t{ Linear = true, X = 0.1, Y = -0.2 },
\t\t\t\t{ Linear = true, X = 0.1, Y = 0.2 },
\t\t\t} }, },
\t\t} },
\t\tEGY_Flag_Border_Local = sTransform { Inputs = { XOffset = Input { Value = 0.2, }, YOffset = Input { Value = -0.1, }, XSize = Input { Value = 2, }, YSize = Input { Value = 3, }, } },
\t\tCountry_Edit_01_Canvas = Background { Inputs = { GlobalOut = Input { Value = 99, }, Width = Input { Value = 800, }, Height = Input { Value = 600, }, } },
\t\tCountry_Edit_01_Mode = Switch {},
\t\tCountry_Edit_01_Plane = ImagePlane3D { Inputs = {
\t\t\tMaterialInput = Input { SourceOp = "Country_Edit_01_Mode", Source = "Output", },
\t\t} },
\t}
}
'''


class BorderHighlightPrototypeTests(unittest.TestCase):
    def test_adds_disabled_editable_neon_stack_before_country_plane(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source.comp"
            target = Path(folder) / "target.comp"
            source.write_text(SOURCE)
            report = build(source, target)
            result = target.read_text()
            original = source.read_text()

        self.assertEqual(report["border_points"], 3)
        self.assertFalse(report["default_enabled"])
        self.assertEqual(original, SOURCE)
        self.assertIn("EGY_Border_Highlight_Group = GroupOperator", result)
        self.assertIn("Flags = { Expanded = true", result)
        self.assertNotIn("EGY_Border_Settings", result)
        self.assertNotIn("EGY_Border_Highlight_Control", result)
        self.assertIn('WritePosition = Input { Value = 0,', result)
        self.assertIn('WriteLength = Input { Value = 0.25,', result)
        self.assertIn('Blend = Input { Value = 0,', result)
        self.assertEqual(result.count(" = Glow {"), 2)
        self.assertIn('MaterialInput = Input { SourceOp = "EGY_Border_Highlight_Merge"', result)
        # Shape Y coordinates are width-relative; PolylineMask Y coordinates
        # must be corrected for the 800x600 local canvas.
        self.assertIn("X = 0, Y = -0.933333333333", result)
        self.assertIn("X = 0.4, Y = -0.933333333333", result)


if __name__ == "__main__":
    unittest.main()
