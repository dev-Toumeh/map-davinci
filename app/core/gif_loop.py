"""Convert uploaded GIFs to editable Fusion groups with external PNG assets."""

from __future__ import annotations

import io
import json
import math
import re
import shutil
import tempfile
import uuid
import zipfile
from pathlib import Path

from PIL import Image, UnidentifiedImageError

MAX_UPLOAD_BYTES = 25 * 1024 * 1024
MAX_FRAMES = 512
MAX_DIMENSION = 4096
MAX_DECODED_PIXELS = 128_000_000


def lua_string(value: str) -> str:
    escaped = []
    for char in value:
        if char in ('"', '\\'):
            escaped.append('\\' + char)
        elif ord(char) < 32:
            escaped.append(f'\\{ord(char):03d}')
        else:
            escaped.append(char)
    return '"' + ''.join(escaped) + '"'


def build_source_time_expression(durations: list[int], tool: str) -> str:
    """Balanced comparisons preserve GIF timing without linear nesting depth."""
    if not durations or any(d <= 0 for d in durations):
        raise ValueError("GIF frame durations must be positive")
    boundaries = []
    elapsed = 0
    for duration in durations:
        elapsed += duration
        boundaries.append(elapsed)
    phase = (f"(((time-comp.RenderStart)*1000/{tool}.TimelineFPS"
             f"*{tool}.Speed+{tool}.Offset*1000)%{elapsed})")

    def branch(start: int, end: int) -> str:
        if end - start == 1:
            return str(start)
        middle = (start + end) // 2
        return (f"iif({phase}<{boundaries[middle - 1]},"
                f"{branch(start, middle)},{branch(middle, end)})")

    return branch(0, len(durations))


def build_setting(first_png: Path, name: str, token: str,
                  durations: list[int], fps: float) -> str:
    frames = f"GIF_{token}_Frames"
    timing = f"GIF_{token}_Timing"
    canvas = f"GIF_{token}_Canvas"
    merge = f"GIF_{token}_MultiMerge"
    expression = lua_string(build_source_time_expression(durations, timing))
    controls = []
    definitions = []
    for key, label, default, lower, upper, maximum in (
        ("Speed", "Speed", 1, 0, 4, 100),
        ("TimelineFPS", "Timeline FPS", fps, 1, 60, 240),
        ("Offset", "Offset (seconds)", 0, 0, sum(durations) / 1000, 100000),
    ):
        controls.append(f'{key} = InstanceInput {{ SourceOp = "{timing}", '
                        f'Source = "{key}", Name = {lua_string(label)}, }},')
        definitions.append(f'{key} = {{ LINKS_Name = {lua_string(label)}, '
                           'LINKID_DataType = "Number", INPID_InputControl = "SliderControl", '
                           f'INP_Default = {default}, INP_MinScale = {lower}, '
                           f'INP_MaxScale = {upper}, INP_MinAllowed = {lower}, '
                           f'INP_MaxAllowed = {maximum}, ICS_ControlPage = "Controls", }},')
    for key, source, label in (("Position", "Layer1.Center", "Position"),
                               ("Size", "Layer1.Size", "Size"),
                               ("Angle", "Layer1.Angle", "Angle"),
                               ("Blend", "Layer1.Blend", "Blend")):
        controls.append(f'{key} = InstanceInput {{ SourceOp = "{merge}", '
                        f'Source = "{source}", Name = "{label}", }},')
    for key in ("Width", "Height"):
        controls.append(f'Canvas{key} = InstanceInput {{ SourceOp = "{canvas}", '
                        f'Source = "{key}", Name = "Canvas {key.lower()}", }},')
    return f'''{{
 Tools = ordered() {{
  {name} = GroupOperator {{
   NameSet = true,
   Inputs = ordered() {{ {" ".join(controls)} }},
   Outputs = {{ MainOutput1 = InstanceOutput {{ SourceOp = "{merge}", Source = "Output", }}, }},
   ViewInfo = GroupInfo {{ Pos = {{ 0, 0 }}, }},
   Tools = ordered() {{
    {frames} = Loader {{
     NameSet = true,
     Clips = {{ Clip {{
      ID = "Clip1", Filename = {lua_string(str(first_png))}, FormatID = "PNGFormat",
      StartFrame = 0, Length = {len(durations)}, LengthSetManually = true,
      TrimIn = 0, TrimOut = {len(durations) - 1}, ExtendFirst = 0, ExtendLast = 0,
      Loop = 1, AspectMode = 0, Depth = 0, TimeCode = 0,
      GlobalStart = 0, GlobalEnd = 1000000,
     }}, }},
     Inputs = {{ ["Clip1.PNGFormat.PostMultiply"] = Input {{ Value = 1, }}, }},
     ViewInfo = OperatorInfo {{ Pos = {{ 0, 0 }}, }},
    }},
    {timing} = TimeStretcher {{
     NameSet = true,
     Inputs = {{
      Input = Input {{ SourceOp = "{frames}", Source = "Output", }},
      SourceTime = Input {{ Expression = {expression}, }},
      Speed = Input {{ Value = 1, }},
      TimelineFPS = Input {{ Value = {fps}, }},
      Offset = Input {{ Value = 0, }},
     }},
     UserControls = ordered() {{ {" ".join(definitions)} }},
     ViewInfo = OperatorInfo {{ Pos = {{ 220, 0 }}, }},
    }},
    {canvas} = Background {{
     NameSet = true,
     Inputs = {{
      GlobalOut = Input {{ Value = 1000000, }},
      Width = Input {{ Value = 3840, }}, Height = Input {{ Value = 2160, }},
      UseFrameFormatSettings = Input {{ Value = 0, }},
      TopLeftAlpha = Input {{ Value = 0, }},
     }},
     ViewInfo = OperatorInfo {{ Pos = {{ 220, 100 }}, }},
    }},
    {merge} = MultiMerge {{
     NameSet = true,
     Inputs = {{
      LayerOrder = Input {{ Value = ScriptVal {{ {{ [0] = 1 }} }}, }},
      Background = Input {{ SourceOp = "{canvas}", Source = "Output", }},
      ["Layer1.Foreground"] = Input {{ SourceOp = "{timing}", Source = "Output", }},
      ["Layer1.Center"] = Input {{ Value = {{ 0.5, 0.5 }}, }},
      ["Layer1.Size"] = Input {{ Value = 1, }},
      ["Layer1.Angle"] = Input {{ Value = 0, }},
      ["Layer1.Blend"] = Input {{ Value = 1, }},
      LayerEnabled1 = Input {{ Value = 1, }},
      LayerName1 = Input {{ Value = "GIF", }},
     }},
     ViewInfo = OperatorInfo {{ Pos = {{ 440, 0 }}, }},
    }},
   }},
  }},
 }},
 ActiveTool = "{name}",
}}
'''


def create_gif_loop_group(data: bytes, exports_dir: Path,
                          group_name: str = "GIFLoop", timeline_fps: float = 24,
                          output_dir: Path | None = None) -> dict:
    if not 6 <= len(data) <= MAX_UPLOAD_BYTES:
        raise ValueError("Choose a GIF file up to 25 MB")
    if data[:6] not in (b"GIF87a", b"GIF89a"):
        raise ValueError("The selected file is not a GIF")
    try:
        fps = float(timeline_fps)
    except (TypeError, ValueError) as exc:
        raise ValueError("Timeline FPS must be between 1 and 240") from exc
    if not math.isfinite(fps) or not 1 <= fps <= 240:
        raise ValueError("Timeline FPS must be between 1 and 240")
    safe_name = re.sub(r"[^A-Za-z0-9_]", "_", group_name.strip())[:64] or "GIFLoop"
    safe_name = "GIF_" + safe_name  # Also avoids Lua reserved words such as 'end'.
    token = uuid.uuid4().hex
    group = f"{safe_name}_{token[:8]}"
    root = output_dir.resolve() if output_dir is not None else exports_dir.resolve() / "gif-loops"
    root.mkdir(parents=True, exist_ok=True)
    final = root / f"{safe_name}_{token}"
    temporary = Path(tempfile.mkdtemp(prefix=".gif-", dir=root))
    try:
        frames_dir = temporary / "Frames"
        frames_dir.mkdir()
        durations = []
        try:
            with Image.open(io.BytesIO(data)) as gif:
                if gif.format != "GIF":
                    raise ValueError("The selected file is not a GIF")
                width, height = gif.size
                if max(width, height) > MAX_DIMENSION:
                    raise ValueError("GIF dimensions must not exceed 4096 pixels per side")
                count = gif.n_frames
                if count > MAX_FRAMES or width * height * count > MAX_DECODED_PIXELS:
                    raise ValueError("GIF is too large: maximum 512 frames and 128 million decoded pixels")
                for index in range(count):
                    # Sequential seek lets Pillow apply GIF disposal/compositing.
                    gif.seek(index)
                    duration = int(gif.info.get("duration", 0) or 0)
                    durations.append(duration if duration > 0 else 100)
                    gif.convert("RGBA").save(frames_dir / f"frame_{index:04d}.png")
        except (UnidentifiedImageError, EOFError, OSError, Image.DecompressionBombError) as exc:
            raise ValueError("Could not decode the GIF; choose a complete, valid GIF file") from exc
        (temporary / "source.gif").write_bytes(data)
        setting_name = f"{group}.setting"
        (temporary / setting_name).write_text(
            build_setting(final / "Frames" / "frame_0000.png", group, token, durations, fps),
            encoding="utf-8")
        metadata = {"group_name": group, "frame_count": len(durations),
                    "width": width, "height": height, "durations_ms": durations,
                    "loop_ms": sum(durations), "timeline_fps": fps}
        (temporary / "timing.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
        archive_name = f"{group}.zip"
        files = sorted(p for p in temporary.rglob("*") if p.is_file())
        with zipfile.ZipFile(temporary / archive_name, "w", zipfile.ZIP_DEFLATED) as archive:
            for source in files:
                archive.write(source, Path(final.name) / source.relative_to(temporary))
        temporary.rename(final)
        return {**metadata, "output_dir": str(final),
                "setting_path": str(final / setting_name),
                "setting_relative": str((final / setting_name).relative_to(root)),
                "zip_relative": str((final / archive_name).relative_to(root))}
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
