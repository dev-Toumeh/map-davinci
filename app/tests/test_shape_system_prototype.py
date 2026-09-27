import tempfile
import unittest
from pathlib import Path

from tools.build_closeup_lod_prototype import _block
from tools.build_shape_system_prototype import _point_count, _polylines, build


MASK = '''\t\tTest_Mask = MultiPoly {
\t\t\tInputs = {
\t\t\t\t["PolyMask2.Polyline"] = Input { Value = Polyline { Closed = true, Points = {
\t\t\t\t\t{ Linear = true, X = 0.1, Y = 0.2 },
\t\t\t\t\t{ Linear = true, X = 0.3, Y = 0.4 }
\t\t\t\t} }, },
\t\t\t\t["PolyMask1.Polyline"] = Input { Value = Polyline { Closed = true, Points = {
\t\t\t\t\t{ Linear = true, X = -0.1, Y = -0.2 }
\t\t\t\t} }, }
\t\t\t}
\t\t}'''


class ShapeSystemPrototypeTests(unittest.TestCase):
    def test_extracts_static_rings_in_numeric_order(self):
        rings = _polylines(MASK)
        self.assertEqual([number for number, _ in rings], [1, 2])
        self.assertEqual(_point_count(rings), 3)

    def test_build_rewires_only_prototype_copy(self):
        comp = '''Composition {
\tTools = ordered() {
''' + MASK + ''',
\t\tMap_Animation = Transform { Inputs = { Input = Input { SourceOp = "Map_Country_Layers", Source = "Output", } } },
\t\tFinal_Composite = Merge { Inputs = { Foreground = Input { SourceOp = "Map_Animation", Source = "Output", } } }
\t}
}'''
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source.comp"
            output = Path(temporary) / "prototype.comp"
            source.write_text(comp, encoding="utf-8")
            result, rings, points = build(source, output, "Test_Mask")
            text = result.read_text(encoding="utf-8")
        self.assertEqual((rings, points), (2, 3))
        self.assertIn("Shape_Prototype_Ring_01_Fill = sPolygon", text)
        self.assertIn('SourceOp = "Shape_Prototype_Ring_01_Fill"', text)
        self.assertIn("Shape_Prototype_Camera = sTransform", text)
        self.assertIn("Shape_Prototype_Render = sRender", text)
        self.assertIn("BorderWidth = Input { Value = 0.0005", text)
        self.assertIn("Shape_Prototype_Canvas = Background", text)
        self.assertIn("Shape_Prototype_Map_Canvas = Merge", text)
        self.assertIn(
            'Background = Input { SourceOp = "Shape_Prototype_Map_Canvas"',
            text,
        )
        render = text.split("Shape_Prototype_Render = sRender", 1)[1].split(
            "Shape_Prototype_Canvas = Background", 1
        )[0]
        self.assertIn("Height = Input { Value = 3840", render)
        self.assertIn(
            'YOffset = Input { Expression = "(Map_Animation.Center.Y - 0.5) * 0.5625"',
            text,
        )
        self.assertIn(
            'YSize = Input { Expression = "Map_Animation.Size * 0.5 * 0.5625"',
            text,
        )
        self.assertIn('SourceOp = "Map_Raster_Layers"', text)
        self.assertIn('SourceOp = "Shape_Prototype_Composite"', text)
        self.assertNotIn('SourceOp = "Map_Country_Layers"', text)

    def test_build_preserves_existing_closeup_imagery_branch(self):
        comp = '''Composition {
\tTools = ordered() {
''' + MASK + ''',
\t\tMap_Animation = Transform { Inputs = { Input = Input { SourceOp = "Map_Raster_Layers", Source = "Output", } } },
\t\tMap_LOD_Composite = Merge { Inputs = { Background = Input { SourceOp = "Map_Animation", Source = "Output", }, Foreground = Input { SourceOp = "Closeup_0961_Animation", Source = "Output", } } },
\t\tMap_Country_LOD_Composite = Merge { Inputs = { Background = Input { SourceOp = "Map_LOD_Composite", Source = "Output", }, Foreground = Input { SourceOp = "Country_Animation", Source = "Output", } } },
\t\tFinal_Composite = Merge { Inputs = { Foreground = Input { SourceOp = "Map_Country_LOD_Composite", Source = "Output", } } }
\t}
}'''
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source.comp"
            output = Path(temporary) / "prototype.comp"
            source.write_text(comp, encoding="utf-8")
            build(source, output, "Test_Mask")
            text = output.read_text(encoding="utf-8")
        map_canvas = text.split("Shape_Prototype_Map_Canvas = Merge", 1)[1].split(
            "Shape_Prototype_Composite = Merge", 1
        )[0]
        self.assertIn('SourceOp = "Map_LOD_Composite"', map_canvas)
        _, _, final = _block(text, "Final_Composite", "Merge")
        self.assertIn('SourceOp = "Shape_Prototype_Composite"', final)
        self.assertNotIn('SourceOp = "Map_Country_LOD_Composite"', final)


if __name__ == "__main__":
    unittest.main()
