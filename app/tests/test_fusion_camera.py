"""Camera projection regression checks; run with unittest discover -s app."""
import json
import math
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fusion.generator import (_camera_samples, _country_mask, _path_points, _key_lines,
                              _camera_timing_keys, _shape_territory,
                              _detail_footprint, MAX_CAMERA_TIMING_KEYS, generate)


class CameraProjectionTests(unittest.TestCase):
    def test_3d_satellite_flow_uses_one_horizontal_row(self):
        animation = {"output": {"width": 3840, "height": 2160,
                                "duration_frames": 25},
                     "keyframes": [{"frame": 0, "center": {"x": .5, "y": .5},
                                    "view_width": .3}], "connections": []}
        metadata = {"output": {"width": 3840, "height": 2160,
                               "wide_factor": 2}, "countries": []}

        def position(content, name):
            match = re.search(
                rf'\b{re.escape(name)} = \w+ \{{.*?ViewInfo = OperatorInfo '
                r'\{ Pos = \{ (-?\d+), (-?\d+) \}', content, re.S)
            self.assertIsNotNone(match, name)
            return tuple(map(int, match.groups()))

        for count in (0, 1, 10):
            with self.subTest(closeups=count), tempfile.TemporaryDirectory() as tmp:
                package = Path(tmp)
                plans = [{"frame": index + 5,
                          "normalized_bbox": (.4, .4, .6, .6),
                          "first": index + 4, "full_first": index + 5,
                          "full_last": index + 5, "last": index + 6,
                          "image_path": package / f"closeup_{index}.png"}
                         for index in range(count)]
                with patch("fusion.generator.closeup_lod.plan_closeups",
                           return_value=plans), patch(
                               "fusion.generator.closeup_lod.ensure_images",
                               return_value=plans):
                    content = generate(package, metadata, animation,
                                       mode="3d").read_text()
                image_names = ["Map_Wide", "Map_Detail"] + [
                    f"Map_Closeup_{index:02d}_{plan['frame']:04d}_Loader"
                    for index, plan in enumerate(plans, 1)]
                image_positions = [position(content, name) for name in image_names]
                self.assertEqual(len({y for _x, y in image_positions}), 1)
                self.assertTrue(all(b[0] - a[0] == 500 for a, b in zip(
                    image_positions, image_positions[1:])))
                plane_names = ["Map_3D_Satellite", "Map_3D_Detail"] + [
                    f"Map_Closeup_{index:02d}_{plan['frame']:04d}_Plane"
                    for index, plan in enumerate(plans, 1)]
                plane_positions = [position(content, name) for name in plane_names]
                self.assertTrue(all(plane[1] > image[1] for image, plane in zip(
                    image_positions, plane_positions)))
                scene = position(content, "Map_3D_Scene")
                renderer = position(content, "Map_3D_Renderer")
                output = position(content, "MediaOut1")
                self.assertGreater(scene[0], max(x for x, _y in plane_positions))
                self.assertGreater(renderer[0], scene[0])
                self.assertGreater(output[0], renderer[0])
                defined = set(re.findall(
                    r'^\s*([A-Za-z]\w*) = [A-Za-z]\w* \{', content, re.M))
                references = set(re.findall(r'SourceOp = "([^"]+)"', content))
                self.assertFalse(references - defined)

    def test_3d_detail_uses_saved_geographic_footprint(self):
        metadata = {"output": {"wide_factor": 2},
                    "wide": {"bbox_mercator": {"minx": 0, "miny": 0,
                                                "maxx": 100, "maxy": 100}},
                    "detail": {"bbox_mercator": {"minx": 30, "miny": 20,
                                                  "maxx": 80, "maxy": 70}}}
        self.assertEqual(_detail_footprint(metadata), (.3, .3, .8, .8))

    def test_3d_mode_reuses_map_and_moves_camera(self):
        animation = {"output": {"width": 2160, "height": 3840,
                                "duration_frames": 25},
                     "keyframes": [
                         {"frame": 0, "center": {"x": .5, "y": .5},
                          "view_width": .3, "easing": "linear"},
                         {"frame": 24, "center": {"x": .52, "y": .48},
                          "view_width": .15, "easing": "smooth"}],
                     "connections": []}
        metadata = {"output": {"width": 3840, "height": 2160,
                               "wide_factor": 2},
                    "wide": {"bbox_mercator": {"minx": -1e6, "miny": -1e6,
                                                "maxx": 1e6, "maxy": 1e6}},
                    "countries": [{"iso3": "TST", "color": "#123456",
                                   "border_color": "#ffffff",
                                   "geometry_file": "geometry_TST.geojson"}]}
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp)
            (package / "geometry_TST.geojson").write_text(json.dumps({
                "type": "Feature", "properties": {}, "geometry": {
                    "type": "Polygon", "coordinates": [[
                        [0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]}}))
            target = generate(package, metadata, animation, mode="3d")
            content = target.read_text()
        self.assertTrue(target.name.endswith("_3d.comp"))
        self.assertIn('Map_3D_Satellite = ImagePlane3D', content)
        self.assertIn('Map_3D_Detail = ImagePlane3D', content)
        self.assertIn('MaterialInput = Input { SourceOp = "Map_Wide"', content)
        self.assertIn('MaterialInput = Input { SourceOp = "Map_Detail"', content)
        self.assertNotIn('Map_Raster_Layers = MultiMerge', content)
        self.assertNotIn('Place_Detail = Transform', content)
        self.assertIn('Map_3D_Camera = Camera3D', content)
        self.assertIn('Map_3D_Renderer = Renderer3D', content)
        self.assertIn('Country_Edit_01_Plane = ImagePlane3D', content)
        self.assertIn('MaterialInput = Input { SourceOp = "Country_Edit_01_Mode"', content)
        self.assertIn('SceneInput3 = Input { SourceOp = "Country_Edit_01_Plane"', content)
        self.assertNotIn('Country_Vector_Canvas = Background', content)
        self.assertIn('Width = Input { Value = 2160', content)
        self.assertIn('Height = Input { Value = 3840', content)
        self.assertNotIn('Map_Animation = Transform', content)
        self.assertNotIn('Final_Composite = Merge', content)

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

    def test_map_timing_is_sparse_while_arrow_shapes_keep_frame_samples(self):
        animation = {"output": {"width": 2160, "height": 3840, "duration_frames": 90},
                     "keyframes": [
                         {"frame": 0, "center": {"x": .5, "y": .5}, "view_width": .3},
                         {"frame": 24, "center": {"x": .51, "y": .4}, "view_width": .08, "easing": "smooth"},
                         {"frame": 60, "center": {"x": .52, "y": .39}, "view_width": .05, "easing": "smooth"}],
                     "connections": [{"id": "example", "name": "example", "start": {"x": .4, "y": .4},
                                      "end": {"x": .6, "y": .35}, "bend": None,
                                      "path_type": "straight", "line_style": "solid", "thickness": 2,
                                      "color": "#ffffff", "arrowhead": True, "arrow_size": 14,
                                      "start_frame": 10, "arrival_frame": 45,
                                      "disappearance_frame": None, "easing": "linear"}]}
        metadata = {"output": {"width": 3840, "height": 2160, "wide_factor": 2}, "countries": []}
        with tempfile.TemporaryDirectory() as tmp:
            text = generate(Path(tmp), metadata, animation).read_text()
        self.assertIn('Map_Raster_Layers = MultiMerge', text)
        self.assertIn('Input = Input { SourceOp = "Map_Raster_Layers"', text)
        self.assertIn('ClippingMode = Input { Value = FuID { "None" }', text)
        self.assertIn('Vector_AnimationDisplacement = BezierSpline', text)
        self.assertIn('Vector_AnimationPath = PolyPath', text)
        vector_timing = text.split('Vector_AnimationDisplacement = BezierSpline', 1)[1].split('Vector_AnimationPath', 1)[0]
        self.assertEqual(len(re.findall(r'\[\d+\] = \{', vector_timing)), 61)
        self.assertIn('Vector_Layers = MultiMerge', text)
        self.assertIn('Input = Input { SourceOp = "Vector_Layers"', text)
        for name in ("Map_AnimationDisplacement", "Map_AnimationSize"):
            section = text.split(name + " = BezierSpline", 1)[1].split("Map_Animation", 1)[0]
            frames = [int(f) for f in re.findall(r"\[(\d+)\] = \{", section)]
            self.assertTrue({0, 24, 60}.issubset(frames))
            self.assertLess(len(frames), 20)
            self.assertIn("RH =", section)
            self.assertNotIn("Linear = true", section)
        arrow = text.split("Link_example_ArrowShape = BezierSpline", 1)[1]
        self.assertGreater(arrow.count("Value = Polyline"), 30)

    def test_country_polygons_are_static_before_map_animation(self):
        geometry = {"type": "Polygon", "coordinates": [[
            [0, 0], [1, 0], [1, 1], [0, 1], [0, 0],
        ]]}
        bbox = {"minx": 0, "miny": 0, "maxx": 1, "maxy": 1}
        text = _country_mask("Country_TST_Fill", geometry, bbox, 3840, 2160, outline=True)
        self.assertIn('["PolyMask1.Center"] = Input { Value = { 0.5, 0.5 }', text)
        self.assertIn('["PolyMask1.Size"] = Input { Value = 1', text)
        self.assertIn('["PolyMask1.BorderWidth"] = Input { Value = 0.0005', text)
        self.assertNotIn("SourceOp", text)

    def test_country_shape_stores_geometry_once_and_instances_border(self):
        geometry = {"type": "Polygon", "coordinates": [[
            [0, 0], [1, 0], [1, 1], [0, 1], [0, 0],
        ]]}
        metadata = {
            "output": {"width": 3840, "height": 2160, "wide_factor": 2},
            "wide": {"bbox_mercator": {"minx": 0, "miny": 0,
                                        "maxx": 2, "maxy": 2}},
            "detail": {"bbox_mercator": {"minx": .5, "miny": .5,
                                          "maxx": 1.5, "maxy": 1.5}},
            "countries": [{"iso3": "TST", "color": "#123456",
                           "border_color": "#abcdef",
                           "geometry_file": "geometry_TST.geojson"}],
        }
        animation = {
            "output": {"width": 2160, "height": 3840, "fps": 24,
                       "duration_frames": 48},
            "keyframes": [{"frame": 0, "center": {"x": .5, "y": .5},
                           "view_width": .5}],
            "connections": [],
            "region_groups": [{"iso3": "TST", "start_frame": None,
                               "end_frame": None,
                               "children": [{"id": "country-tst",
                                             "name": "Entire country",
                                             "category": "country",
                                             "start_frame": None,
                                             "end_frame": None}]}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp)
            (package / "geometry_TST.geojson").write_text(
                __import__("json").dumps({"type": "Feature", "geometry": geometry,
                                          "properties": {}}))
            text = generate(package, metadata, animation).read_text()
        self.assertIn('TST_Entire_Ring_01_Fill = sPolygon {', text)
        border = text.split("TST_Entire_Ring_01_Border = sPolygon", 1)[1].split(
            "TST_Entire_Shapes = sMerge", 1)[0]
        self.assertIn('SourceOp = "TST_Entire_Ring_01_Fill"', border)
        self.assertIn('BorderWidth = Input { Value = 0.0003', border)
        self.assertNotIn("Polyline = Input", border)
        self.assertNotIn("TST_Entire_Wide", text)
        self.assertNotIn("TST_Entire_Detail", text)

    def test_tiny_territories_and_optional_islands_use_thinner_borders(self):
        tiny, _output = _shape_territory(
            "Tiny", [(1, [(0, 0), (.001, 0), (.001, .001)])],
            (1, 0, 0), (1, 1, 1), "Input { Value = 1, }", 0)
        self.assertIn("BorderWidth = Input { Value = 0.0001", tiny)

        rings = [
            (1, [(0, 0), (1, 0), (1, 1)]),
            (1, [(0, 0), (.1, 0), (.1, .1)]),
        ]
        regular, _output = _shape_territory(
            "Regular", rings, (1, 0, 0), (1, 1, 1),
            "Input { Value = 1, }", 0)
        main = regular.split("Regular_Ring_01_Border = sPolygon", 1)[1].split(
            "Regular_Ring_02_Fill", 1)[0]
        island = regular.split("Regular_Ring_02_Border = sPolygon", 1)[1].split(
            "Regular_Shapes", 1)[0]
        self.assertIn("BorderWidth = Input { Value = 0.0003", main)
        self.assertIn("BorderWidth = Input { Value = 0.0001", island)

    def test_country_shape_rings_are_arranged_in_a_compact_grid(self):
        ring = [(0.1, 0.1), (0.2, 0.1), (0.2, 0.2), (0.1, 0.1)]
        geometry = {"type": "MultiPolygon", "coordinates": [
            [[list(point) for point in ring]] for _ in range(9)
        ]}
        metadata = {
            "output": {"width": 3840, "height": 2160, "wide_factor": 2},
            "wide": {"bbox_mercator": {"minx": 0, "miny": 0,
                                          "maxx": 1, "maxy": 1}},
            "countries": [{"iso3": "TST", "color": "#123456",
                           "border_color": "#abcdef",
                           "geometry_file": "geometry_TST.geojson"}],
        }
        animation = {
            "output": {"width": 2160, "height": 3840, "fps": 24,
                       "duration_frames": 48},
            "keyframes": [{"frame": 0, "center": {"x": .5, "y": .5},
                           "view_width": .5}],
            "connections": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp)
            (package / "geometry_TST.geojson").write_text(
                __import__("json").dumps({"geometry": geometry}))
            text = generate(package, metadata, animation).read_text()
        positions = re.findall(
            r'TST_Entire_Ring_\d+_Fill = sPolygon.*?Pos = \{ (-?\d+), (\d+) \}',
            text, re.S)
        self.assertEqual(len(positions), 9)
        self.assertEqual(len({x for x, _y in positions}), 4)
        self.assertEqual(len({y for _x, y in positions}), 3)

    def test_handles_approximate_smooth_zoom_with_authored_keys(self):
        animation = {"output": {"width": 2160, "height": 3840}, "keyframes": [
            {"frame": 0, "center": {"x": .5, "y": .5}, "view_width": .25},
            {"frame": 52, "center": {"x": .55, "y": .4}, "view_width": .04, "easing": "smooth"}]}
        samples = _camera_samples(animation, {"width": 3840, "height": 2160})
        keys = _camera_timing_keys(samples, {0, 52})
        self.assertLess(len(keys), 10)
        for a, b in zip(keys, keys[1:]):
            lines = _key_lines([a, b], samples, "size")
            handles = re.findall(r"RH = \{ [^,]+, ([\d.e+-]+) \}|LH = \{ [^,]+, ([\d.e+-]+) \}", lines)
            right, left = float(handles[0][0]), float(handles[1][1])
            for frame in range(a["frame"], b["frame"] + 1):
                t = (frame-a["frame"])/(b["frame"]-a["frame"])
                size = ((1-t)**3*a["zoom"] + 3*(1-t)**2*t*right +
                        3*(1-t)*t*t*left + t**3*b["zoom"])
                self.assertLessEqual(abs(size-samples[frame]["zoom"])/samples[frame]["zoom"], .0201)

    def test_generated_camera_timing_keys_have_an_editable_limit(self):
        samples = [{"frame": frame,
                    "zoom": 1 + (frame % 7) * .4,
                    "displacement": frame / 199 + (frame % 5) * .002}
                   for frame in range(200)]
        keys = _camera_timing_keys(samples, {0, 199})
        self.assertLessEqual(len(keys), MAX_CAMERA_TIMING_KEYS)
        self.assertEqual(keys[0]["frame"], 0)
        self.assertEqual(keys[-1]["frame"], 199)

    def test_deep_zoom_exports_cached_closeup_branch(self):
        metadata = {
            "output": {"width": 3840, "height": 2160, "wide_factor": 2},
            "wide": {"bbox_mercator": {"minx": 0, "miny": 0,
                                         "maxx": 100, "maxy": 100}},
            "countries": [],
        }
        animation = {
            "output": {"width": 2160, "height": 3840, "fps": 24,
                       "duration_frames": 101},
            "keyframes": [
                {"frame": 0, "center": {"x": .5, "y": .5}, "view_width": .2},
                {"frame": 50, "center": {"x": .5, "y": .5}, "view_width": .01},
                {"frame": 100, "center": {"x": .5, "y": .5}, "view_width": .2},
            ],
            "connections": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "closeup.png"

            def cached(_package, _metadata, _animation, plans):
                for plan in plans:
                    plan["image_path"] = image
                return plans

            with patch("fusion.generator.closeup_lod.ensure_images", side_effect=cached):
                text = generate(Path(tmp), metadata, animation).read_text()
        self.assertIn("Closeup_01_0050_Loader = Loader", text)
        self.assertIn("Closeup_01_0050_Animation = Transform", text)
        self.assertIn('Foreground = Input { SourceOp = "Closeup_01_0050_Animation"', text)
        self.assertIn("Map_Quality_Switch = Switch", text)
        quality = text.split("Map_Quality_Switch = Switch", 1)[1].split(
            "Output_Canvas = Background", 1)[0]
        self.assertIn('Input0 = Input { SourceOp = "Map_Animation"', quality)
        self.assertIn(
            'Input1 = Input { SourceOp = "Closeup_01_0050_Composite"', quality)
        self.assertIn('Name0 = Input { Value = "EDIT - base map only"', quality)
        self.assertIn(
            'Name1 = Input { Value = "RENDER - enable close-up imagery"', quality)

    def test_3d_closeup_keeps_full_resolution_on_registered_plane(self):
        metadata = {"output": {"width": 3840, "height": 2160, "wide_factor": 2},
                    "wide": {"bbox_mercator": {"minx": 0, "miny": 0,
                                                "maxx": 100, "maxy": 100}},
                    "countries": []}
        animation = {"output": {"width": 3840, "height": 2160,
                                "duration_frames": 101},
                     "keyframes": [
                         {"frame": 0, "center": {"x": .5, "y": .5},
                          "view_width": .5},
                         {"frame": 50, "center": {"x": .5, "y": .5},
                          "view_width": .12},
                         {"frame": 100, "center": {"x": .5, "y": .5},
                          "view_width": .5}], "connections": []}
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "closeup.png"

            def cached(_package, _metadata, _animation, plans):
                for plan in plans:
                    plan["image_path"] = image
                return plans

            with patch("fusion.generator.closeup_lod.ensure_images", side_effect=cached):
                content = generate(Path(tmp), metadata, animation, mode="3d").read_text()
        self.assertNotIn('Map_Raster_Layers = MultiMerge', content)
        self.assertIn('Map_Closeup_01_0050_Loader = Loader', content)
        self.assertIn('Map_Closeup_01_0050_Plane = ImagePlane3D', content)
        self.assertIn('MaterialInput = Input { SourceOp = "Map_Closeup_01_0050_Fade"', content)
        self.assertIn('SceneInput3 = Input { SourceOp = "Map_Closeup_01_0050_Plane"', content)
        self.assertNotIn('Map_Raster_Layers = Merge', content)
        self.assertIn('MaterialInput = Input { SourceOp = "Map_Wide"', content)
        self.assertIn('MaterialInput = Input { SourceOp = "Map_Detail"', content)
        self.assertNotIn('Map_Animation = Transform', content)

    def test_closeup_imagery_and_shape_territory_share_final_working_canvas(self):
        geometry = {"type": "Polygon", "coordinates": [[
            [-1, -1], [1, -1], [1, 1], [-1, 1], [-1, -1],
        ]]}
        metadata = {
            "output": {"width": 3840, "height": 2160, "wide_factor": 2},
            "wide": {"bbox_mercator": {"minx": -200000, "miny": -200000,
                                         "maxx": 200000, "maxy": 200000}},
            "detail": {"bbox_mercator": {"minx": -100000, "miny": -100000,
                                           "maxx": 100000, "maxy": 100000}},
            "countries": [{"iso3": "TST", "color": "#123456",
                           "border_color": "#ffffff",
                           "geometry_file": "geometry_TST.geojson"}],
        }
        animation = {
            "output": {"width": 2160, "height": 3840, "fps": 24,
                       "duration_frames": 101},
            "keyframes": [
                {"frame": 0, "center": {"x": .5, "y": .5}, "view_width": .2},
                {"frame": 50, "center": {"x": .5, "y": .5}, "view_width": .01},
                {"frame": 100, "center": {"x": .5, "y": .5}, "view_width": .2},
            ],
            "connections": [],
            "region_groups": [{"iso3": "TST", "start_frame": None,
                               "end_frame": None, "children": [{
                                   "id": "country-tst", "name": "Entire country",
                                   "category": "country", "start_frame": None,
                                   "end_frame": None}]}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp)
            (package / "geometry_TST.geojson").write_text(__import__("json").dumps(
                {"type": "Feature", "properties": {}, "geometry": geometry}))

            def cached(_package, _metadata, _animation, plans):
                for plan in plans:
                    plan["image_path"] = package / "closeup.png"
                return plans

            with patch("fusion.generator.closeup_lod.ensure_images", side_effect=cached):
                text = generate(package, metadata, animation).read_text()
        self.assertIn("Closeup_01_0050_Animation = Transform", text)
        self.assertIn("TST_Entire_Ring_01_Fill = sPolygon", text)
        self.assertEqual(text.count("TST_Entire_Ring_01_Fill = sPolygon"), 1)
        self.assertIn("Country_Deployment = MultiMerge", text)
        self.assertIn("Country_Vector_Canvas = Background", text)
        working = text.split("Map_Working_Canvas = Merge", 1)[1].split(
            "Map_With_Countries = Merge", 1)[0]
        self.assertIn('SourceOp = "Map_Quality_Switch"', working)
        self.assertNotIn("Closeup_01_0050_TST_Entire", text)


if __name__ == "__main__":
    unittest.main()
