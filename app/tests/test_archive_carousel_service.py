"""The Python side owns lifecycle only; generation remains in the Go module."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from core import archive_carousel_service as bridge


class CarouselBridgeTests(unittest.TestCase):
    def test_reuses_running_child(self):
        child = mock.Mock()
        child.poll.return_value = None
        with mock.patch.object(bridge, "_process", child), mock.patch.object(bridge, "_url", "http://127.0.0.1:9999"):
            self.assertEqual(bridge.start(Path("/unused"), "http://127.0.0.1/"), "http://127.0.0.1:9999")

    def test_missing_go_has_actionable_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            with mock.patch.object(bridge, "RUNTIME", Path(temporary)), mock.patch.object(bridge, "_process", None), mock.patch.object(bridge.shutil, "which", return_value=None):
                with self.assertRaisesRegex(RuntimeError, "Install Go"):
                    bridge.start(Path(temporary), "http://127.0.0.1/")

    def test_stops_only_owned_child(self):
        child = mock.Mock()
        child.poll.return_value = None
        with mock.patch.object(bridge, "_process", child), mock.patch.object(bridge, "_url", "http://127.0.0.1:9999"):
            bridge.stop()
            child.terminate.assert_called_once()
            child.wait.assert_called_once_with(timeout=8)
            self.assertIsNone(bridge._process)


if __name__ == "__main__":
    unittest.main()
