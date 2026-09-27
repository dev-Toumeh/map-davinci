"""Structured export-package and repeated-name regression tests."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from core import exporter, package_layout
from core.exporter import _available_output_dir
from fusion.generator import generate


class PackageLayoutTests(unittest.TestCase):
    def test_repeated_project_names_use_incrementing_suffixes(self):
        with tempfile.TemporaryDirectory() as folder:
            exports = Path(folder)
            (exports / "saudi_arabia").mkdir()
            (exports / "saudi_arabia_2").mkdir()
            self.assertEqual(_available_output_dir(exports, "saudi_arabia").name,
                             "saudi_arabia_3")

    def test_structured_paths_and_fusion_images(self):
        with tempfile.TemporaryDirectory() as folder:
            package = Path(folder)
            package_layout.create(package)
            metadata = {
                "package_layout": package_layout.manifest(),
                "assets": package_layout.default_assets(),
                "output": {"width": 3840, "height": 2160, "wide_factor": 2},
                "countries": [],
            }
            (package / package_layout.METADATA_FILE).write_text(json.dumps(metadata))
            animation = {"output": {"width": 1920, "height": 1080,
                         "fps": 24, "duration_frames": 2},
                         "keyframes": [{"frame": 0, "center": {"x": .5, "y": .5},
                                        "view_width": 1}], "connections": []}
            text = generate(package, metadata, animation).read_text()
            self.assertTrue(package_layout.structured(package))
            self.assertEqual(package_layout.animation_path(package),
                             package / package_layout.ANIMATION_FILE)
            self.assertEqual(package_layout.data_relative(package, "geometry_SAU.geojson"),
                             Path("data/geometry_SAU.geojson"))
            self.assertEqual(package_layout.sounds_relative(package, "voice.mp3"),
                             Path("sounds/voice.mp3"))
            self.assertIn(str(package / package_layout.SATELLITE_WIDE_FILE), text)
            self.assertIn(str(package / package_layout.SATELLITE_DETAIL_FILE), text)

    def test_new_export_writes_each_file_type_to_its_directory(self):
        geometry = {"type": "Polygon", "coordinates": [[
            [-.001, -.001], [.001, -.001], [.001, .001], [-.001, .001],
            [-.001, -.001],
        ]]}
        with tempfile.TemporaryDirectory() as folder:
            exports = Path(folder)
            config = {"name": "saudi_arabia", "countries": ["SAU"],
                      "orientation": "landscape", "resolution": "test",
                      "source": "google_satellite", "wide_factor": 2,
                      "detail_bbox_mercator": {
                          "minx": -1000, "miny": -562.5,
                          "maxx": 1000, "maxy": 562.5}}
            with patch("core.settings.exports_dir", return_value=exports), \
                    patch.object(exporter, "RESOLUTIONS", {"test": {"landscape": (16, 9)}}), \
                    patch.object(exporter, "stitch_bbox",
                                 side_effect=lambda *args, **kwargs: Image.new("RGB", (16, 9))), \
                    patch.object(exporter, "get_geometry", return_value=geometry):
                result = exporter.run_export(config, lambda *args: None)
            package = Path(result["output_dir"])
            for directory in package_layout.STRUCTURED_DIRS:
                self.assertTrue((package / directory).is_dir())
            self.assertTrue((package / package_layout.METADATA_FILE).is_file())
            self.assertTrue((package / package_layout.SATELLITE_WIDE_FILE).is_file())
            self.assertTrue((package / package_layout.mask_png("SAU")).is_file())
            self.assertTrue((package / package_layout.mask_svg("SAU")).is_file())
            self.assertTrue((package / package_layout.country_geometry("SAU")).is_file())
            metadata = json.loads((package / package_layout.METADATA_FILE).read_text())
            self.assertEqual(metadata["package_layout"], package_layout.manifest())
            self.assertEqual(metadata["assets"], package_layout.default_assets())


if __name__ == "__main__":
    unittest.main()
