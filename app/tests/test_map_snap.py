"""MapSnap's size, frame, and single-file export contracts."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from core import exporter, map_snap


class MapSnapTests(unittest.TestCase):
    def test_dimensions_cover_shapes_and_sizes(self):
        self.assertEqual(map_snap.dimensions("16:9", "4k"), (3840, 2160))
        self.assertEqual(map_snap.dimensions("9:16", "hd"), (720, 1280))
        self.assertEqual(map_snap.dimensions("1:1", "750"), (750, 750))
        self.assertEqual(map_snap.dimensions("4:5", "fhd"), (1536, 1920))
        self.assertEqual(map_snap.dimensions("16:9", "750"), (750, 422))

    def test_exports_one_clean_png_and_keeps_existing_name(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / "map.png").write_bytes(b"original")
            config = {"name": "map", "output_folder": directory, "aspect": "4:3",
                      "resolution": "750", "source": "esri_world_imagery",
                      "bbox_mercator": {"minx": -1000, "miny": -750,
                                        "maxx": 1000, "maxy": 750}}
            with patch.object(exporter, "choose_tile_zoom", return_value=(9, False)), \
                    patch.object(exporter, "stitch_bbox",
                                 side_effect=lambda source, key, zoom, bbox, size, progress, stage:
                                 Image.new("RGB", size, (12, 34, 56))) as stitch:
                result = map_snap.export_image(config, lambda *args: None)
            self.assertEqual(result["filename"], "map_2.png")
            self.assertEqual((folder / "map.png").read_bytes(), b"original")
            self.assertEqual(Image.open(result["path"]).size, (750, 562))
            self.assertEqual(Image.open(result["path"]).getpixel((1, 1)), (12, 34, 56))
            self.assertEqual(stitch.call_args.args[3], (-1000, -750, 1000, 750))
            self.assertEqual(sorted(path.name for path in folder.iterdir()), ["map.png", "map_2.png"])

    def test_rejects_mismatched_frame(self):
        with tempfile.TemporaryDirectory() as directory:
            config = {"name": "map", "output_folder": directory, "aspect": "16:9",
                      "resolution": "hd", "source": "esri_world_imagery",
                      "bbox_mercator": {"minx": 0, "miny": 0,
                                        "maxx": 1000, "maxy": 1000}}
            with self.assertRaisesRegex(ValueError, "aspect"):
                map_snap.validate(config)


if __name__ == "__main__":
    unittest.main()
