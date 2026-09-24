"""Google styled-map session and tile proxy regression checks."""
import unittest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from core import exporter


class GoogleMapTilesTests(unittest.TestCase):
    def setUp(self):
        exporter._GOOGLE_SESSION.clear()
        self.cache_directory = tempfile.TemporaryDirectory()
        self.cache_patch = patch.object(exporter, "TILE_CACHE", Path(self.cache_directory.name))
        self.cache_patch.start()
        self.usage_patch = patch.object(
            exporter, "GOOGLE_TILE_USAGE_FILE",
            Path(self.cache_directory.name) / "usage.json",
        )
        self.usage_patch.start()

    def tearDown(self):
        self.usage_patch.stop()
        self.cache_patch.stop()
        self.cache_directory.cleanup()

    @patch("core.settings.google_maps_api_key", return_value="test-secret-key")
    @patch("core.exporter.requests.get")
    @patch("core.exporter.requests.post")
    def test_key_stays_in_server_requests_and_style_is_sent(self, post, get, _key):
        session_response = Mock(status_code=200)
        session_response.json.return_value = {
            "session": "session-token", "expiry": "4102444800",
        }
        post.return_value = session_response
        get.return_value = Mock(
            status_code=200,
            content=b"png-data",
            headers={"Cache-Control": "private, max-age=86400, must-revalidate",
                     "ETag": '"example"'},
        )

        self.assertEqual(exporter.google_simple_tile(4, 8, 7), b"png-data")
        self.assertEqual(exporter.google_simple_tile(4, 8, 7), b"png-data")
        request = post.call_args
        self.assertEqual(request.kwargs["params"], {"key": "test-secret-key"})
        self.assertEqual(request.kwargs["json"]["mapType"], "roadmap")
        self.assertGreater(len(request.kwargs["json"]["styles"]), 20)
        self.assertIsInstance(
            next(styler["gamma"] for rule in request.kwargs["json"]["styles"]
                 for styler in rule.get("stylers", []) if "gamma" in styler),
            float,
        )
        self.assertEqual(get.call_args.kwargs["params"], {
            "session": "session-token", "key": "test-secret-key",
        })
        self.assertEqual(get.call_count, 1)
        self.assertEqual(exporter.google_tile_usage()["requests"], 1)

    def test_rejects_invalid_tile_coordinates_before_request(self):
        with self.assertRaises(ValueError):
            exporter.google_simple_tile(4, 16, 0)


if __name__ == "__main__":
    unittest.main()
