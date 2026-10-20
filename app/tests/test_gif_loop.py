"""GIF conversion, generated Fusion timing, and HTTP integration."""

import bisect
import io
import json
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from core import gif_loop
from server import Handler


def sample_gif(durations=(70, 60, 70), disposal=(1, 2, 1)):
    frames = []
    for i in range(len(durations)):
        frame = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
        frame.putpixel((i % 8, i % 8), (255, 30 * i, 0, 255))
        frames.append(frame)
    stream = io.BytesIO()
    frames[0].save(stream, format="GIF", save_all=True, append_images=frames[1:],
                   duration=list(durations) if len(frames) > 1 else durations[0],
                   disposal=list(disposal) if len(frames) > 1 else disposal[0], loop=1)
    return stream.getvalue()


class GifLoopTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()

    def tearDown(self):
        self.temp.cleanup()

    def test_pixels_timing_assets_and_unique_packages(self):
        data = sample_gif()
        first = gif_loop.create_gif_loop_group(data, self.root, "A 'GIF'", 29.97)
        second = gif_loop.create_gif_loop_group(data, self.root, "A 'GIF'", 29.97)
        self.assertNotEqual(first["output_dir"], second["output_dir"])
        output = Path(first["output_dir"])
        with Image.open(io.BytesIO(data)) as original:
            for i in range(original.n_frames):
                original.seek(i)
                with Image.open(output / "Frames" / f"frame_{i:04d}.png") as extracted:
                    self.assertEqual(extracted.mode, "RGBA")
                    self.assertEqual(extracted.tobytes(), original.convert("RGBA").tobytes())
        timing = json.loads((output / "timing.json").read_text())
        self.assertEqual(timing["durations_ms"], [70, 60, 70])
        self.assertEqual(first["loop_ms"], 200)
        setting = Path(first["setting_path"]).read_text()
        self.assertIn(str(output / "Frames" / "frame_0000.png"), setting)
        self.assertIn("GlobalEnd = 1000000", setting)
        self.assertNotIn("__FIRST_PNG__", setting)
        with zipfile.ZipFile(self.root / "gif-loops" / first["zip_relative"]) as archive:
            self.assertIsNone(archive.testzip())
            self.assertEqual(len(archive.namelist()), 6)
            self.assertTrue(all(n.startswith(output.name + "/") for n in archive.namelist()))
        self.assertFalse(any(p.name.startswith(".gif-") for p in output.parent.iterdir()))

    def test_single_frame_and_duration_fallback(self):
        data = sample_gif((0,), (1,))
        result = gif_loop.create_gif_loop_group(data, self.root)
        self.assertEqual(result["frame_count"], 1)
        self.assertEqual(result["loop_ms"], 100)
        self.assertEqual(gif_loop.build_source_time_expression([100], "Timing"), "0")

    def test_invalid_inputs_and_failed_conversion_cleanup(self):
        for data, fps in [(b"not GIF", 30), (sample_gif(), 0), (sample_gif(), float("nan")),
                          (sample_gif(), 241), (b"GIF89acorrupt data", 30)]:
            with self.subTest(fps=fps, data=data[:10]):
                with self.assertRaises(ValueError):
                    gif_loop.create_gif_loop_group(data, self.root, timeline_fps=fps)
        self.assertFalse((self.root / "gif-loops").exists() and
                         list((self.root / "gif-loops").iterdir()))
        for bound, value in [("MAX_FRAMES", 2), ("MAX_DIMENSION", 4), ("MAX_DECODED_PIXELS", 10)]:
            with patch.object(gif_loop, bound, value), self.assertRaises(ValueError):
                gif_loop.create_gif_loop_group(sample_gif(), self.root)
        self.assertEqual(list((self.root / "gif-loops").iterdir()), [])

    @unittest.skipUnless(shutil.which("luajit"), "LuaJIT is required for generated Lua validation")
    def test_lua_setting_escaping_and_links(self):
        result = gif_loop.create_gif_loop_group(sample_gif(), self.root / 'quote"\\dir', "end")
        script = '''local h=assert(io.open(arg[1])); local f=assert(loadstring("return "..h:read("*a"))); h:close()
setfenv(f,setmetatable({ordered=function() return function(t) return t end end},{__index=function() return function(t) return t end end}))
local s=f(); local g=s.Tools[s.ActiveTool]; local merge=g.Tools[g.Outputs.MainOutput1.SourceOp]
local timing=g.Tools[merge.Inputs["Layer1.Foreground"].SourceOp]
assert(timing and timing.Inputs.SourceTime.Expression)
local loader=g.Tools[timing.Inputs.Input.SourceOp]; assert(loader.Clips[1].Loop==1)
local file=assert(io.open(loader.Clips[1].Filename)); file:close()
local canvas=g.Tools[merge.Inputs.Background.SourceOp]; assert(canvas.Inputs.TopLeftAlpha.Value==0)
assert(canvas.Inputs.Width.Value==3840 and canvas.Inputs.Height.Value==2160)
assert(merge.Inputs.LayerEnabled1.Value==1 and merge.Inputs["Layer1.Blend"].Value==1)
assert(not merge.Inputs["Layer2.Foreground"])
local tools=0; for _,tool in pairs(g.Tools) do tools=tools+1; assert(not tool.Tools) end; assert(tools==4)
local outputs=0; for _ in pairs(g.Outputs) do outputs=outputs+1 end; assert(outputs==1)
for _,input in pairs(g.Inputs) do local tool=g.Tools[input.SourceOp]; assert(tool and (tool.Inputs[input.Source] or tool.UserControls[input.Source])) end
'''
        checked = subprocess.run(["luajit", "-", result["setting_path"]], input=script,
                                 text=True, capture_output=True)
        self.assertEqual(checked.returncode, 0, checked.stderr)

    @unittest.skipUnless(shutil.which("luajit"), "LuaJIT is required for timing validation")
    def test_expression_matches_duration_boundaries_and_playback(self):
        durations = [70, 60, 70, 70, 60, 70, 70, 60, 70, 70, 60, 60]
        boundaries = []
        total = 0
        for duration in durations:
            total += duration
            boundaries.append(total)
        expression = gif_loop.build_source_time_expression(durations, "Timing")
        samples = []
        for fps in (24, 25, 30, 29.97, 60):
            for speed in (0, .5, 1, 2):
                for t in (0, 1, 25, 90, 275, 1262, 10000):
                    samples.append((t, fps, speed, .13))
        # Sample every source interval boundary, on the boundary and just before.
        samples.extend((ms / 1000 * 30, 30, 1, 0)
                       for b in [0] + boundaries for ms in (b, b + .001, max(0, b - .001)))
        script = "local iif=function(c,a,b) if c then return a else return b end end\n"
        script += "local comp={RenderStart=0}; local Timing={}; local time=0\n"
        script += "local function frame() return " + expression + " end\n"
        for t, fps, speed, offset in samples:
            script += f"time={t}; Timing.TimelineFPS={fps}; Timing.Speed={speed}; Timing.Offset={offset}; print(frame())\n"
        checked = subprocess.run(["luajit", "-"], input=script, text=True, capture_output=True)
        self.assertEqual(checked.returncode, 0, checked.stderr)
        actual = [int(v) for v in checked.stdout.splitlines()]
        expected = [bisect.bisect_right(boundaries, (t * 1000 / fps * speed + offset * 1000) % total)
                    for t, fps, speed, offset in samples]
        self.assertEqual(actual, expected)
        # A large GIF should remain parseable, rather than nesting 511 levels.
        large = gif_loop.build_source_time_expression([100] * 512, "Timing")
        parsed = subprocess.run(["luajit", "-"], input="assert(loadstring(" + gif_loop.lua_string("return " + large) + "))",
                                text=True, capture_output=True)
        self.assertEqual(parsed.returncode, 0, parsed.stderr)

    def test_http_routes_and_upload(self):
        handler = Handler.__new__(Handler)
        handler.path = "/gif"
        files = []
        handler._file = lambda path, root: files.append(path)
        handler.do_GET()
        self.assertEqual(files[0].name, "gif.html")
        data = sample_gif()
        handler.path = "/api/gif?name=Test&fps=25"
        handler.headers = {"Content-Length": str(len(data))}
        handler.rfile = io.BytesIO(data)
        responses = []
        handler._json = lambda body, code=200: responses.append((code, body))
        with patch("server.app_settings.exports_dir", return_value=self.root), \
             patch("server.app_settings.gif_exports_dir", return_value=self.root / "gif-loops"):
            handler.do_POST()
        code, result = responses[-1]
        self.assertEqual(code, 200)
        self.assertEqual(result["timeline_fps"], 25)
        self.assertTrue(result["setting_url"].startswith("/api/gif/files/"))
        self.assertTrue(Path(result["setting_path"]).is_file())
        handler.headers = {"Content-Length": str(gif_loop.MAX_UPLOAD_BYTES + 1)}
        handler.rfile = io.BytesIO(b"")
        handler.do_POST()
        self.assertEqual(responses[-1][0], 413)
        handler.headers = {"Content-Length": "7"}
        handler.rfile = io.BytesIO(b"not GIF")
        with patch("server.app_settings.exports_dir", return_value=self.root), \
             patch("server.app_settings.gif_exports_dir", return_value=self.root / "gif-loops"):
            handler.do_POST()
        self.assertEqual(responses[-1][0], 400)

    def test_custom_folder_persists_and_serves_files_without_changing_map_path(self):
        from core import settings
        prefs = self.root / "preferences.json"
        map_root = self.root / "maps"
        custom_root = self.root / "my nodes"
        with patch.object(settings, "SETTINGS_FILE", prefs):
            settings.save({"exports_path": str(map_root), "unrelated": True})
            handler = Handler.__new__(Handler)
            responses = []
            handler._json = lambda body, code=200: responses.append((code, body))
            handler.path = "/api/gif/settings"
            data = json.dumps({"path": str(custom_root)}).encode()
            handler.headers = {"Content-Length": str(len(data))}
            handler.rfile = io.BytesIO(data)
            handler.do_POST()
            self.assertEqual(responses[-1][0], 200)
            self.assertEqual(settings.gif_exports_dir(), custom_root)
            self.assertEqual(settings.exports_dir(), map_root)
            self.assertTrue(settings.load()["unrelated"])
            handler.do_GET()
            self.assertEqual(responses[-1][1]["path"], str(custom_root))
            handler.path = "/api/gif?name=Custom"
            data = sample_gif()
            handler.headers = {"Content-Length": str(len(data))}
            handler.rfile = io.BytesIO(data)
            handler.do_POST()
            result = responses[-1][1]
            self.assertEqual(result["timeline_fps"], 24)
            self.assertEqual(Path(result["output_dir"]).parent, custom_root)
            setting = Path(result["setting_path"])
            self.assertIn(str(setting.parent / "Frames" / "frame_0000.png"), setting.read_text())
            sent = []
            handler._send = lambda code, body, mime: sent.append((code, body, mime))
            handler.path = result["setting_url"]
            handler.do_GET()
            self.assertEqual(sent[-1][1], setting.read_bytes())
            handler.path = "/api/gif/files/../preferences.json"
            handler.do_GET()
            self.assertEqual(responses[-1][0], 403)
            handler.path = "/api/gif/settings"
            data = b'{"use_default":true}'
            handler.headers = {"Content-Length": str(len(data))}
            handler.rfile = io.BytesIO(data)
            handler.do_POST()
            self.assertEqual(settings.gif_exports_dir(), map_root / "gif-loops")
            self.assertTrue(setting.is_file())  # Resetting the path does not move/delete assets.


if __name__ == "__main__":
    unittest.main()
