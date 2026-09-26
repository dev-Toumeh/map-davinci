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

    def test_parent_and_child_timing_generate_nested_multimerge(self):
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
        self.assertIn("USA_Visibility = BezierSpline", text)
        self.assertIn("USA_Texas_Annexation_1845_Visibility", text)
        self.assertIn("USA_Entire_Combined_Layers = MultiMerge", text)
        self.assertIn("USA_Texas_Annexation_1845_Combined_Layers = MultiMerge", text)
        entire_combined = text.split("USA_Entire_Combined_Layers = MultiMerge", 1)[1].split(
            "USA_Texas_Annexation_1845_Wide_Fill_Mask", 1)[0]
        self.assertIn('Background = Input { SourceOp = "USA_Wide_Canvas"',
                      entire_combined)
        self.assertIn(
            '["Layer1.Foreground"] = Input { SourceOp = "USA_Entire_Wide_Gate"',
            entire_combined)
        self.assertIn(
            '["Layer2.Foreground"] = Input { SourceOp = "USA_Entire_Detail_Placed"',
            entire_combined)
        self.assertIn("Country_Deployment_Layers = MultiMerge", text)
        self.assertIn("Map_Country_Layers = MultiMerge", text)
        self.assertIn("Country_Edit_Switch = Switch", text)
        self.assertIn("Country_Mode_Switch = Switch", text)
        self.assertIn('Name0 = Input { Value = "USA - Entire country"', text)
        self.assertIn('Name1 = Input { Value = "USA - Texas Annexation"', text)
        self.assertIn('Input0 = Input { SourceOp = "USA_Entire_Combined_Layers"', text)
        self.assertIn('Input1 = Input { SourceOp = "USA_Texas_Annexation_1845_Combined_Layers"', text)
        deployment = text.split("Country_Deployment_Layers = MultiMerge", 1)[1].split(
            "Country_Edit_Switch = Switch", 1)[0]
        self.assertIn(
            '["Layer1.Foreground"] = Input { SourceOp = "USA_Entire_Combined_Layers"',
            deployment)
        self.assertIn(
            '["Layer2.Foreground"] = Input { SourceOp = "USA_Texas_Annexation_1845_Combined_Layers"',
            deployment)
        self.assertIn('Name0 = Input { Value = "EDIT MODE - selected country or territory"', text)
        self.assertIn('Name1 = Input { Value = "DEPLOYMENT - all countries and territories"', text)
        self.assertIn(
            'Input1 = Input { SourceOp = "Country_Deployment_Layers", Source = "Output"',
            text)
        self.assertIn('Input = Input { SourceOp = "Map_Country_Layers"', text)
        self.assertIn('Background = Input { SourceOp = "Map_Raster_Layers"', text)
        self.assertNotIn("USA_Wide_Regions", text)
        self.assertNotIn("USA_Detail_Regions", text)
        self.assertNotIn("Country_Final_", text)
        self.assertNotIn("Edit_USA_", text)
        self.assertEqual(text.count('SourceOp = "USA_Entire_Combined_Layers"'), 2)
        self.assertNotIn("Vector_AnimationDisplacement", text)
        self.assertNotIn("Vector_AnimationPath", text)
        border = text.split(
            "USA_Entire_Wide_Border_Mask = MultiPoly", 1)[1].split(
                "USA_Entire_Detail_Fill_Mask", 1)[0]
        self.assertIn(
            'SourceOp = "USA_Entire_Wide_Fill_Mask"', border)
        self.assertNotIn(".Polyline\"]", border)

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

    def test_one_edit_switch_selects_regions_across_multiple_countries(self):
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
        edit = text.split("Country_Edit_Switch = Switch", 1)[1].split(
            "Country_Mode_Switch = Switch", 1)[0]
        self.assertIn("NumberOfInputs = Input { Value = 2", edit)
        self.assertIn('Name0 = Input { Value = "USA - Entire country"', edit)
        self.assertIn('Name1 = Input { Value = "CAN - Entire country"', edit)
        self.assertIn('Input0 = Input { SourceOp = "USA_Entire_Combined_Layers"', edit)
        self.assertIn('Input1 = Input { SourceOp = "CAN_Entire_Combined_Layers"', edit)
        deployment = text.split("Country_Deployment_Layers = MultiMerge", 1)[1].split(
            "Country_Edit_Switch = Switch", 1)[0]
        self.assertIn('SourceOp = "USA_Entire_Combined_Layers"', deployment)
        self.assertIn('SourceOp = "CAN_Entire_Combined_Layers"', deployment)
        self.assertEqual(text.count("Country_Mode_Switch = Switch"), 1)


if __name__ == "__main__":
    unittest.main()
