"""Flag texture and Fusion routing checks for a short two-country shot."""
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from fusion.generator import generate
from fusion.flag_assets import MAX_TEXTURE_SIDE, make_texture


def geometry(x):
    return {"type": "Polygon", "coordinates": [[
        [x + 4, 1], [x + 8, 5], [x + 4, 9], [x, 5], [x + 4, 1],
    ]]}


class CountryFlagTests(unittest.TestCase):
    def shot(self, second="CAN"):
        metadata = {"output": {"width": 1280, "height": 720, "wide_factor": 2},
                    "wide": {"bbox_mercator": {"minx": -3000000, "miny": -1000000,
                                                 "maxx": 3000000, "maxy": 2000000}},
                    "countries": [{"iso3": iso, "color": "#2299ee",
                                   "border_color": "#ffffff",
                                   "geometry_file": f"geometry_{iso}.geojson"}
                                  for iso in ("USA", second)]}
        animation = {"output": {"width": 1280, "height": 720, "fps": 24,
                                "duration_frames": 24},
                     "keyframes": [{"frame": 0, "center": {"x": .4, "y": .5},
                                    "view_width": .8, "easing": "linear"},
                                   {"frame": 23, "center": {"x": .6, "y": .5},
                                    "view_width": .4, "easing": "linear"}],
                     "connections": []}
        return metadata, animation

    def test_independent_flag_switches_in_both_modes(self):
        metadata, animation = self.shot()
        with tempfile.TemporaryDirectory() as folder:
            package = Path(folder)
            for iso, x in (("USA", -20), ("CAN", 10)):
                (package / f"geometry_{iso}.geojson").write_text(
                    json.dumps({"geometry": geometry(x)}))
            warnings = []
            text = generate(package, metadata, animation, warnings).read_text()
            for iso in ("USA", "CAN"):
                texture = next((package / "images" / "flags").glob(f"{iso}_cover_*.png"))
                self.assertTrue(texture.is_file())
                with Image.open(texture) as image:
                    self.assertEqual(image.mode, "RGBA")
                    self.assertEqual(image.getpixel((0, 0))[3], 255)
                    self.assertEqual(image.getchannel("A").getextrema(), (255, 255))
                switch = text.split(f"{iso}_Flag_Color_Flag = Switch", 1)[1].split(
                    f"{iso}_Flag_Border_Geometry", 1)[0]
                self.assertIn("Which = Input { Value = 0", switch)
                self.assertIn('Name0 = Input { Value = "Flag"', text)
                self.assertIn('Name1 = Input { Value = "Color"', text)
                self.assertNotIn('Name2 = Input { Value = "Transparent"', text)
                self.assertIn('NumberOfInputs = Input { Value = 2', switch)
                self.assertIn(f'SourceOp = "{iso}_Flag_Color_Flag"', text)
                self.assertIn(f'SourceOp = "{iso}_Flag_Border_Render"', text)
            self.assertNotEqual(
                next((package / "images/flags").glob("USA_cover_*.png")).read_bytes(),
                next((package / "images/flags").glob("CAN_cover_*.png")).read_bytes())
            self.assertNotIn('Country_Edit_Controller', text)
            self.assertNotIn('CustomTool', text)
            self.assertIn('Input1 = Input { SourceOp = "USA_Render"', text)
            self.assertIn('Input0 = Input { SourceOp = "USA_Flag_With_Border"', text)
            self.assertIn('Input1 = Input { SourceOp = "CAN_Render"', text)
            self.assertIn('Input0 = Input { SourceOp = "CAN_Flag_With_Border"', text)
            self.assertIn("Country_Deployment = MultiMerge", text)
            self.assertIn('SourceOp = "Map_AnimationPath"', text)
            self.assertIn('SourceOp = "Map_AnimationSize"', text)
            self.assertNotIn("Country_Raster_Camera_Path", text)
            self.assertIn("Point(0.5 + (Map_Animation.Center.X - 0.5)", text)
            self.assertIn('Size = Input { Expression = "Map_Animation.Size /', text)
            self.assertIn("USA_Flag_Local_Transform = Transform", text)
            self.assertIn('Input = Input { SourceOp = "USA_Flag_Loader"', text)
            self.assertNotIn("USA_Flag_Adjust", text)
            self.assertIn('Blend = Input { Value = 1,', text)
            self.assertIn('EffectMask = Input { SourceOp = "USA_Render"', text)
            self.assertIn("USA_Flag_Masked_On_Working_Canvas = Merge", text)
            self.assertEqual(warnings, [])
            self.assertTrue((package / "images" / "flags" / "LICENSE.flag-icons.txt").is_file())

    def test_missing_flag_keeps_color_and_reports_warning(self):
        metadata, animation = self.shot("ZZZ")
        with tempfile.TemporaryDirectory() as folder:
            package = Path(folder)
            for iso, x in (("USA", -20), ("ZZZ", 10)):
                (package / f"geometry_{iso}.geojson").write_text(
                    json.dumps({"geometry": geometry(x)}))
            warnings = []
            text = generate(package, metadata, animation, warnings).read_text()
            self.assertIn("ZZZ: no matching flag asset; using color fill", warnings)
            self.assertNotIn("ZZZ_Flag_Color_Flag", text)
            self.assertIn("ZZZ_Entire_Shapes", text)

    def test_texture_cap_reports_possible_softening(self):
        rings = [(1, [(-.25, -.25), (.25, -.25), (.25, .25), (-.25, .25)])]
        with tempfile.TemporaryDirectory() as folder:
            path, placement, warnings = make_texture(
                Path(folder), "USA", "us", rings, 2000, 2000, 10)
            with Image.open(path) as image:
                self.assertEqual(max(image.size), MAX_TEXTURE_SIDE)
            self.assertEqual(placement["size"], 1)
            self.assertTrue(any("capped" in warning for warning in warnings))


if __name__ == "__main__":
    unittest.main()
