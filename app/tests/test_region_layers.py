"""Sub-territory schema and native Fusion hierarchy regression tests."""
import json
import re
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

    def test_legacy_timing_is_removed_and_shapes_remain_available(self):
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
        self.assertIsNone(animation["region_groups"][0]["start_frame"])
        self.assertIsNone(animation["region_groups"][0]["end_frame"])
        for child in animation["region_groups"][0]["children"]:
            self.assertIsNone(child["start_frame"])
            self.assertIsNone(child["end_frame"])
        with tempfile.TemporaryDirectory() as folder:
            package = Path(folder)
            (package / "geometry_USA.geojson").write_text(json.dumps({"geometry": GEOMETRY}))
            (package / "regions").mkdir()
            (package / "regions/geometry_texas-annexation-1845.geojson").write_text(
                json.dumps({"geometry": GEOMETRY}))
            text = generate(package, self.metadata(), animation).read_text()
        self.assertNotIn("_Visibility = BezierSpline", text)
        self.assertIn("USA_Entire_Shapes = sMerge", text)
        self.assertIn("USA_Texas_Annexation_1845_Shapes = sMerge", text)
        self.assertIn("Country_Deployment = MultiMerge", text)
        self.assertNotIn("CustomTool", text)
        self.assertNotIn("UserControls", text)
        self.assertIn("Country_Edit_Selected = MultiMerge", text)
        self.assertIn("Country_Mode_Switch = Switch", text)
        self.assertNotIn('Country_Edit_Controller', text)
        self.assertIn('Name0 = Input { Value = "USA - Entire country"', text)
        self.assertIn('Name0 = Input { Value = "USA - Texas Annexation"', text)
        self.assertIn('SourceOp = "Country_Edit_01_Enabled"', text)
        self.assertIn('SourceOp = "Country_Edit_02_Enabled"', text)
        deployment = text.split("Country_Deployment = MultiMerge", 1)[1].split(
            "Country_Edit_Selected = MultiMerge", 1)[0]
        self.assertIn('SourceOp = "USA_Flag_Color_Flag"', deployment)
        self.assertIn('SourceOp = "Country_Edit_02_Render"', deployment)
        self.assertIn('Name0 = Input { Value = "EDIT MODE - native territory switches"', text)
        self.assertIn('Name1 = Input { Value = "DEPLOYMENT - all countries and territories"', text)
        self.assertIn('SourceOp = "Country_Deployment", Source = "Output"', text)
        self.assertIn('Map_With_Countries = Merge', text)
        self.assertIn('Input = Input { SourceOp = "Map_Raster_Layers"', text)
        self.assertIn('Background = Input { SourceOp = "Map_Working_Canvas"', text)
        self.assertNotIn("USA_Entire_Wide", text)
        self.assertNotIn("USA_Entire_Detail", text)
        self.assertEqual(text.count('SourceOp = "USA_Entire_Shapes"'), 1)
        self.assertNotIn("Vector_AnimationDisplacement", text)
        self.assertNotIn("Vector_AnimationPath", text)
        border = text.split(
            "USA_Entire_Ring_01_Border = sPolygon", 1)[1].split(
                "USA_Entire_Shapes = sMerge", 1)[0]
        self.assertIn('SourceOp = "USA_Entire_Ring_01_Fill"', border)
        self.assertNotIn("Polyline = Input", border)

    def test_structured_region_geometry_path_survives_a_second_save(self):
        animation = self.base_animation()
        animation["region_groups"] = [{"iso3": "USA", "children": [
            {"id": "country-usa", "name": "Entire country", "category": "country"},
            {"id": "admin-us-tx", "name": "Texas", "category": "administrative",
             "geometry_file": "data/regions/geometry_admin-us-tx.geojson"},
        ]}]
        normalized = normalize_animation(animation, self.metadata())
        saved_again = normalize_animation(normalized, self.metadata())
        self.assertEqual(
            saved_again["region_groups"][0]["children"][1]["geometry_file"],
            "data/regions/geometry_admin-us-tx.geojson",
        )

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

    def test_invalid_legacy_child_interval_is_cleared(self):
        animation = self.base_animation()
        animation["region_groups"] = [{"iso3": "USA", "children": [{
            "id": "bad", "name": "Bad", "category": "historical",
            "start_frame": 60, "end_frame": 30}]}]
        normalized = normalize_animation(animation, self.metadata())
        child = normalized["region_groups"][0]["children"][0]
        self.assertIsNone(child["start_frame"])
        self.assertIsNone(child["end_frame"])

    def test_native_switches_enable_regions_without_custom_controllers(self):
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
        edit = text.split("Country_Deployment = MultiMerge", 1)[0]
        self.assertNotIn('Country_Edit_Controller', text)
        self.assertNotIn('CustomTool', text)
        self.assertNotIn('UserControls', text)
        flag_switches = re.findall(
            r'([A-Z]{3}_Flag_Color_Flag = Switch).*?Which = Input \{ Value = (\d)',
            edit, re.S)
        self.assertEqual(flag_switches, [
            ('USA_Flag_Color_Flag = Switch', '0'),
            ('CAN_Flag_Color_Flag = Switch', '0'),
        ])
        self.assertIn('Name0 = Input { Value = "USA - Entire country"', edit)
        self.assertIn('Name0 = Input { Value = "CAN - Entire country"', edit)
        self.assertIn('Country_Edit_01_Enabled = Switch', edit)
        self.assertIn('Country_Edit_02_Enabled = Switch', edit)
        for index in (1, 2):
            enabled = edit.split(f'Country_Edit_{index:02d}_Enabled = Switch', 1)[1].split(
                'ViewInfo', 1)[0]
            self.assertIn(f'Input0 = Input {{ SourceOp = "', enabled)
            self.assertIn('Name1 = Input { Value = "OFF"', enabled)
            self.assertIn('Which = Input { Value = 0', enabled)
            self.assertNotIn('Expression', enabled)
        selected = text.split("Country_Edit_Selected = MultiMerge", 1)[1].split(
            "Country_Mode_Switch = Switch", 1)[0]
        self.assertIn('SourceOp = "Country_Edit_01_Enabled"', selected)
        self.assertIn('SourceOp = "Country_Edit_02_Enabled"', selected)
        deployment = text.split("Country_Deployment = MultiMerge", 1)[1].split(
            "Country_Edit_Selected = MultiMerge", 1)[0]
        self.assertIn('SourceOp = "USA_Flag_Color_Flag"', deployment)
        self.assertIn('SourceOp = "CAN_Flag_Color_Flag"', deployment)
        self.assertEqual(text.count("Country_Mode_Switch = Switch"), 1)

    def test_3d_countries_keep_independent_local_masks_and_flag_switches(self):
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
            content = generate(package, metadata, animation, mode="3d").read_text()
        self.assertNotIn("Map_3D_Country = ImagePlane3D", content)
        self.assertNotIn("Country_Vector_Canvas = Background", content)
        self.assertIn("Country_Edit_01_Local = sTransform", content)
        self.assertIn("Country_Edit_02_Local = sTransform", content)
        self.assertIn("Country_Edit_01_Plane = ImagePlane3D", content)
        self.assertIn("Country_Edit_02_Plane = ImagePlane3D", content)
        self.assertIn('SceneInput3 = Input { SourceOp = "Country_Edit_01_Plane"', content)
        self.assertIn('SceneInput4 = Input { SourceOp = "Country_Edit_02_Plane"', content)
        self.assertNotIn('CustomTool', content)
        self.assertNotIn('UserControls', content)
        self.assertNotIn('Country_Mode_Switch', content)
        self.assertNotIn('Country_Edit_Controller', content)
        for index in (1, 2):
            enabled = content.split(f"Country_Edit_{index:02d}_Enabled = Switch", 1)[1].split(
                "ViewInfo", 1)[0]
            self.assertIn('Which = Input { Value = 0', enabled)
            self.assertNotIn('Expression', enabled)
            self.assertNotIn(f'Country_Edit_{index:02d}_Mode', content)
            self.assertIn('Input0 = Input { SourceOp = "', enabled)
            self.assertIn(f'Input1 = Input {{ SourceOp = "Country_Edit_{index:02d}_Canvas"', enabled)
            self.assertIn(f'Name1 = Input {{ Value = "OFF"', enabled)
        for iso3 in ("USA", "CAN"):
            switch = content.split(f"{iso3}_Flag_Color_Flag = Switch", 1)[1].split(
                "ViewInfo", 1)[0]
            self.assertIn("Which = Input { Value = 0", switch)
            self.assertIn('Name0 = Input { Value = "Flag"', switch)

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
        self.assertIn("USA_Entire_Optional_Group = GroupOperator", text)
        group = text.split("USA_Entire_Optional_Group = GroupOperator", 1)[1].split(
            "Map_Raster_Layers", 1)[0]
        self.assertIn("Tools = ordered()", group)
        frame = re.search(
            r'ViewInfo = GroupInfo \{.*?Pos = \{ (-?[\d.]+), \d+ \}.*?'
            r'Size = \{ ([\d.]+),', group, re.S)
        self.assertIsNotNone(frame)
        # Absolute group positions change with the balanced country layout;
        # its local frame size and internal alignment must remain intact.
        self.assertGreater(float(frame.group(2)), 0)
        self.assertEqual(text.count('SourceOp = "USA_Entire_Optional_Islands"'), 1)
        positions = {}
        for index, kind in ((1, "Fill"), (1, "Border"),
                            (2, "Fill"), (2, "Border")):
            match = re.search(
                rf'USA_Entire_Ring_{index:02d}_{kind} = sPolygon.*?Pos = \{{ (-?\d+), (\d+) \}}',
                group, re.S)
            self.assertIsNotNone(match)
            positions[index, kind] = tuple(map(int, match.groups()))
        self.assertEqual(positions[1, "Border"][0], positions[1, "Fill"][0])
        self.assertEqual(positions[2, "Border"][0], positions[2, "Fill"][0])
        self.assertGreater(positions[1, "Fill"][1], positions[1, "Border"][1])
        self.assertGreater(positions[2, "Fill"][1], positions[2, "Border"][1])
        self.assertGreater(positions[2, "Border"][1], positions[1, "Border"][1])


if __name__ == "__main__":
    unittest.main()
