"""The reference upload should save an MP4 without touching the shot."""

import io
import tempfile
import unittest
from pathlib import Path

from server import Handler


class ReferenceVideoUploadTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.package = Path(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def upload(self, data):
        handler = Handler.__new__(Handler)
        handler.path = "/api/animation/example/reference-video"
        handler.headers = {"Content-Length": str(len(data)), "Content-Type": "video/mp4"}
        handler.rfile = io.BytesIO(data)
        handler._package = lambda name: self.package
        responses = []
        handler._json = lambda body, code=200: responses.append((code, body))
        handler.do_POST()
        return responses[0]

    def test_upload_replaces_reference_and_rejects_invalid_video(self):
        first = b"\x00\x00\x00\x14ftypisomfirst"
        second = b"\x00\x00\x00\x15ftypisomsecond"
        target = self.package / "videos" / "reference.mp4"

        code, result = self.upload(first)
        self.assertEqual(code, 200)
        self.assertEqual(result["name"], "reference.mp4")
        self.assertEqual(target.read_bytes(), first)

        code, result = self.upload(b"not an mp4 file")
        self.assertNotEqual(code, 200)
        self.assertIn("error", result)
        self.assertEqual(target.read_bytes(), first)

        code, result = self.upload(second)
        self.assertEqual(code, 200)
        self.assertEqual(target.read_bytes(), second)


if __name__ == "__main__":
    unittest.main()
