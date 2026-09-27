"""Sub-territory schema and native Fusion hierarchy regression tests."""
import json
import tempfile
import unittest
from pathlib import Path

from core.animation_schema import normalize_animation
from fusion.generator import _territory_base, _territory_label, generate


GEOMETRY = {"type": "Polygon", "coordinates": [[
    [-101, 35], [-99, 35], [-99, 37], [-101, 37], [-101, 35],
]]}


class RegionLayerTests(unittest.TestCase):
    def metadata(self):
        return {
            "output": {"width": 3840, "height": 2160, "wide_factor": 2},
            "wide": {"bbox_mercator": {"minx": -15000000, "miny": 1000000,
                                         "maxx": -6000000, "maxy": 8000000}},
            "countries": [{"iso3": "USA", "color": "#1689ff",
                           "border_color": "#ffffff",
                           "geometry_file": "geometry_USA.geojson"}],
        }

    def base_animation(self):
        return {"name": "regions", "output": {"width": 2160, "height": 3840,
                "fps": 24, "duration_frames": 120}, "keyframes": [
                    {"frame": 0, "center": {"x": .5, "y": .5},
                     "view_width": .25, "easing": "linear"}], "connections": []}

    def test_v2_animation_migrates_to_entire_country_child(self):
        animation = normalize_animation(self.base_animation(), self.metadata())
        self.assertEqual(animation["schema_version"], 3)
        group = animation["region_groups"][0]
        self.assertEqual(group["iso3"], "USA")
        self.assertEqual(group["children"][0]["category"], "country")
        self.assertIsNone(group["children"][0]["start_frame"])

    def test_parent_and_child_timing_generate_shape_deployment(self):
        animation = self.base_animation()
        animation["region_groups"] = [{"iso3": "USA", "start_frame": 5,
            "end_frame": 110, "children": [
                {"id": "country-usa", "name": "Entire country", "category": "country",
                 "start_frame": None, "end_frame": 25},
                {"id": "texas-annexation-1845", "name": "Texas Annexation",
                 "category": "historical", "start_frame": 30, "end_frame": 90,
                 "geometry_file": "regions/geometry_texas-annexation-1845.geojson"},
            ]}]
        animation = normalize_animation(animation, self.metadata())
        with tempfile.TemporaryDirectory() as folder:
            package = Path(folder)
            (package / "geometry_USA.geojson").write_text(json.dumps({"geometry": GEOMETRY}))
            (package / "regions").mkdir()
            (package / "regions/geometry_texas-annexation-1845.geojson").write_text(
                json.dumps({"geometry": GEOMETRY}))
            text = generate(package, self.metadata(), animation).read_text()
        self.assertIn("USA_Entire_Visibility = BezierSpline", text)
        self.assertIn("USA_Texas_Annexation_1845_Visibility", text)
        self.assertIn("USA_Entire_Shapes = sMerge", text)
        self.assertIn("USA_Texas_Annexation_1845_Shapes = sMerge", text)
        self.assertIn("Country_Deployment_Geometry = sMerge", text)
        self.assertIn("Country_Deployment_Camera = sTransform", text)
        self.assertIn("Country_Deployment_Render = sRender", text)
        self.assertIn("Country_Edit_Controller = CustomTool", text)
        self.assertIn("Country_Edit_Selected = MultiMerge", text)
        self.assertIn("Country_Mode_Switch = Switch", text)
        self.assertIn('LINKS_Name = "USA - Entire country"', text)
        self.assertIn('LINKS_Name = "USA - Texas Annexation"', text)
        self.assertIn('Expression = "Country_Edit_Controller.Show_01"', text)
        self.assertIn('Expression = "Country_Edit_Controller.Show_02"', text)
        self.assertIn('SourceOp = "Country_Edit_01_Enabled"', text)
        self.assertIn('SourceOp = "Country_Edit_02_Enabled"', text)
        deployment = text.split("Country_Deployment_Geometry = sMerge", 1)[1].split(
            "Country_Deployment_Camera = sTransform", 1)[0]
        self.assertIn('Input1 = Input { SourceOp = "USA_Entire_Shapes"', deployment)
        self.assertIn(
            'Input2 = Input { SourceOp = "USA_Texas_Annexation_1845_Shapes"',
            deployment)
        self.assertIn('Name0 = Input { Value = "EDIT MODE - checked countries and territories"', text)
        self.assertIn('Name1 = Input { Value = "DEPLOYMENT - all countries and territories"', text)
        self.assertIn(
            'Input1 = Input { SourceOp = "Country_Deployment_Render", Source = "Output"',
            text)
        self.assertIn('Map_With_Countries = Merge', text)
        self.assertIn('Input = Input { SourceOp = "Map_Raster_Layers"', text)
        self.assertIn('Background = Input { SourceOp = "Map_Working_Canvas"', text)
        self.assertNotIn("USA_Entire_Wide", text)
        self.assertNotIn("USA_Entire_Detail", text)
        self.assertEqual(text.count('SourceOp = "USA_Entire_Shapes"'), 2)
        self.assertNotIn("Vector_AnimationDisplacement", text)
        self.assertNotIn("Vector_AnimationPath", text)
        border = text.split(
            "USA_Entire_Ring_01_Border = sPolygon", 1)[1].split(
                "USA_Entire_Shapes = sMerge", 1)[0]
        self.assertIn('SourceOp = "USA_Entire_Ring_01_Fill"', border)
        self.assertNotIn("Polyline = Input", border)

    def test_territory_names_are_short_and_explain_original_territory(self):
        entire = {"id": "country-usa", "name": "Entire country", "category": "country"}
        original = {"id": "us-original-1783", "name": "Original US Territory",
                    "category": "historical"}
        louisiana = {"id": "louisiana-purchase-1803", "name": "Louisiana Purchase",
                     "category": "historical"}
        self.assertEqual(_territory_base("USA", entire), "USA_Entire")
        self.assertEqual(_territory_base("USA", original), "USA_Territory_1783")
        self.assertEqual(_territory_label(original), "Territory recognized in 1783")
        self.assertEqual(_territory_base("USA", louisiana),
                         "USA_Louisiana_Purchase_1803")

    def test_invalid_child_interval_is_rejected(self):
        animation = self.base_animation()
        animation["region_groups"] = [{"iso3": "USA", "children": [{
            "id": "bad", "name": "Bad", "category": "historical",
            "start_frame": 60, "end_frame": 30}]}]
        with self.assertRaisesRegex(ValueError, "appear frame must precede"):
            normalize_animation(animation, self.metadata())

    def test_edit_controller_can_enable_regions_across_multiple_countries(self):
        metadata = self.metadata()
        metadata["countries"].append({
            "iso3": "CAN", "color": "#ff0000", "border_color": "#ffffff",
            "geometry_file": "geometry_CAN.geojson",
        })
        animation = normalize_animation(self.base_animation(), metadata)
        with tempfile.TemporaryDirectory() as folder:
            package = Path(folder)
            for iso3 in ("USA", "CAN"):
                (package / f"geometry_{iso3}.geojson").write_text(
                    json.dumps({"geometry": GEOMETRY}))
            text = generate(package, metadata, animation).read_text()
        edit = text.split("Country_Edit_Controller = CustomTool", 1)[1].split(
            "Country_Deployment_Geometry = sMerge", 1)[0]
        self.assertIn('Show_01 = Input { Value = 1', edit)
        self.assertIn('Show_02 = Input { Value = 0', edit)
        self.assertIn('LINKS_Name = "USA - Entire country"', edit)
        self.assertIn('LINKS_Name = "CAN - Entire country"', edit)
        self.assertIn('Country_Edit_01_Enabled = Switch', edit)
        self.assertIn('Country_Edit_02_Enabled = Switch', edit)
        selected = text.split("Country_Edit_Selected = MultiMerge", 1)[1].split(
            "Country_Mode_Switch = Switch", 1)[0]
        self.assertIn('SourceOp = "Country_Edit_01_Enabled"', selected)
        self.assertIn('SourceOp = "Country_Edit_02_Enabled"', selected)
        deployment = text.split("Country_Deployment_Geometry = sMerge", 1)[1].split(
            "Country_Deployment_Camera = sTransform", 1)[0]
        self.assertIn('SourceOp = "USA_Entire_Shapes"', deployment)
        self.assertIn('SourceOp = "CAN_Entire_Shapes"', deployment)
        self.assertEqual(text.count("Country_Mode_Switch = Switch"), 1)

    def test_small_exterior_islands_are_retained_but_disconnected(self):
        metadata = self.metadata()
        geometry = {"type": "MultiPolygon", "coordinates": [
            [[[-10, 0], [0, 0], [0, 10], [-10, 10], [-10, 0]]],
            [[[1, 0], [2, 0], [2, 1], [1, 1], [1, 0]]],
        ]}
        animation = normalize_animation(self.base_animation(), metadata)
        with tempfile.TemporaryDirectory() as folder:
            package = Path(folder)
            (package / "geometry_USA.geojson").write_text(
                json.dumps({"geometry": geometry}))
            text = generate(package, metadata, animation).read_text()
        active = text.split("USA_Entire_Shapes = sMerge", 1)[1].split(
            "USA_Entire_Optional_Islands", 1)[0]
        optional = text.split("USA_Entire_Optional_Islands = sMerge", 1)[1].split(
            "Map_Raster_Layers", 1)[0]
        self.assertIn("USA_Entire_Ring_01_Fill", active)
        self.assertNotIn("USA_Entire_Ring_02_Fill", active)
        self.assertIn("USA_Entire_Ring_02_Fill", optional)
        self.assertEqual(text.count('SourceOp = "USA_Entire_Optional_Islands"'), 0)


if __name__ == "__main__":
    unittest.main()
