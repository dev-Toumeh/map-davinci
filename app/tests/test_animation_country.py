import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from server import Handler


GEOMETRY = {"type": "Polygon", "coordinates": [[
    [-10, 35], [-8, 35], [-8, 37], [-10, 37], [-10, 35],
]]}


class AnimationCountryTests(unittest.TestCase):
    def test_add_country_persists_geometry_metadata_and_animation_group(self):
        with tempfile.TemporaryDirectory() as folder:
            package = Path(folder)
            metadata = {
                "output": {"width": 3840, "height": 2160, "wide_factor": 2},
                "countries": [{"iso3": "ESP", "color": "#ff0000",
                               "border_color": "#ffffff",
                               "geometry_file": "geometry_ESP.geojson"}],
                "files": {},
            }
            animation = {
                "name": "test", "output": {"width": 3840, "height": 2160,
                "fps": 24, "duration_frames": 120},
                "keyframes": [{"frame": 0, "center": {"x": .5, "y": .5},
                               "view_width": 1, "easing": "linear"}],
                "connections": [],
            }
            (package / "metadata.json").write_text(json.dumps(metadata))
            (package / "animation.json").write_text(json.dumps(animation))
            handler = Handler.__new__(Handler)
            catalog = [{"iso3": "PRT", "name": "Portugal",
                        "default_color": "#006600",
                        "default_border_color": "#ffffff"}]
            with patch("server.exporter.load_countries", return_value=catalog), \
                    patch("server.exporter.get_geometry", return_value=GEOMETRY):
                result = handler._add_animation_country(
                    package, {"iso3": "PRT", "color": "#123456"})

            saved_metadata = json.loads((package / "metadata.json").read_text())
            saved_animation = json.loads((package / "animation.json").read_text())
            self.assertEqual(result["country"]["name"], "Portugal")
            self.assertEqual(saved_metadata["countries"][-1]["color"], "#123456")
            self.assertIn("geometry_PRT.geojson", saved_metadata["files"])
            self.assertEqual(saved_animation["region_groups"][-1]["iso3"], "PRT")
            self.assertEqual(saved_animation["region_groups"][-1]["children"][0]["category"],
                             "country")

    def test_duplicate_country_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            package = Path(folder)
            (package / "metadata.json").write_text(json.dumps({
                "countries": [{"iso3": "PRT"}],
            }))
            handler = Handler.__new__(Handler)
            catalog = [{"iso3": "PRT", "name": "Portugal"}]
            with patch("server.exporter.load_countries", return_value=catalog):
                with self.assertRaisesRegex(ValueError, "already in this animation"):
                    handler._add_animation_country(package, {"iso3": "PRT"})


class AnimationCountryUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (Path(__file__).parents[1] / "static" / "animation.html").read_text()

    def test_animation_editor_has_country_picker_and_endpoint(self):
        self.assertIn('id="addcountrychoice"', self.html)
        self.assertIn('id="addcountrycolor"', self.html)
        self.assertIn('/country`,{method:"POST"', self.html)

    def test_vector_preview_is_used_when_country_has_no_mask_image(self):
        self.assertIn('if(c.file)images[c.iso3]=await load(url(c.file))', self.html)
        self.assertIn('child.category==="country"&&images[group.iso3]', self.html)
        self.assertIn('country?.geometry_file?url(country.geometry_file)', self.html)


if __name__ == "__main__":
    unittest.main()
