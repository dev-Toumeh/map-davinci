"""Regression checks for the manually controlled Fusion border prototype."""
import tempfile
import unittest
from pathlib import Path

from tools.build_border_highlight_prototype import _nodes, _tool_block, build


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
    def test_app_overlay_has_no_external_image_dependencies(self):
        import re
        text = _nodes('EGY', [(0, 0), (.1, 0), (.1, .1)],
                      99, 800, 600, overlay_only=True)
        group = _tool_block(text, 'EGY_Border_Highlight_Group')
        children = set(re.findall(r'^\s+(EGY_\w+) = (?!GroupOperator)\w+ \{', group, re.M))
        self.assertTrue(set(re.findall(r'SourceOp = "([^"]+)"', group)) <= children)
        final = _tool_block(group, 'EGY_Merge')
        self.assertIn('Background = Input { SourceOp = "EGY_Transparent"', final)
        self.assertIn('Blend = Input { Value = 0', final)

    def test_supports_country_prefixed_canvas_and_plane(self):
        source_text = SOURCE.replace('Country_Edit_01_', 'EGY_').replace('EGY_Mode', 'EGY_Enabled')
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'source.comp'
            target = Path(folder) / 'target.comp'
            source.write_text(source_text)
            build(source, target)
            result = target.read_text()
        self.assertNotIn('Country_Edit_', result)
        self.assertIn('SourceOp = "EGY_Enabled"', result)
        self.assertIn('MaterialInput = Input { SourceOp = "EGY_Border_Highlight_Group", Source = "MainOutput1"', result)

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
        self.assertIn('MaterialInput = Input { SourceOp = "EGY_Border_Highlight_Group", Source = "MainOutput1"', result)
        # Shape Y coordinates are width-relative; PolylineMask Y coordinates
        # must be corrected for the 800x600 local canvas.
        self.assertIn("X = 0, Y = -0.933333333333", result)
        self.assertIn("X = 0.4, Y = -0.933333333333", result)

    def test_short_children_are_globally_unique(self):
        import re
        all_children = set()
        for iso in ('EGY', 'PAK'):
            text = _nodes(iso, [(0, 0), (.1, 0), (.1, .1)], 99, 800, 600)
            group = _tool_block(text, f'{iso}_Border_Highlight_Group')
            children = set(re.findall(rf'^\s+({iso}_\w+) = (?!GroupOperator)\w+ \{{', group, re.M))
            self.assertEqual(len(children), 9)
            self.assertFalse(children & all_children)
            all_children.update(children)
            self.assertNotRegex(group, rf'{iso}_Border_Highlight_\w+ = (?!GroupOperator)\w+ \{{')
            references = set(re.findall(r'SourceOp = "([^"]+)"', group))
            self.assertEqual(references - children, {f'{iso}_Enabled'})
            self.assertIn(f'SourceOp = "{iso}_Merge"', group)
            self.assertIn('Blend = Input { Value = 0', _tool_block(group, f'{iso}_Merge'))


if __name__ == "__main__":
    unittest.main()
