"""Validation and migration for editable map-video animation shots."""
from __future__ import annotations

import math
from typing import Any

SCHEMA_VERSION = 2
EASINGS = {"linear", "smooth"}


def _number(value: Any, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a number") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _aspect(output: dict, native: dict) -> tuple[float, float]:
    width = int(_number(output.get("width", native.get("width", 0)), "output width"))
    height = int(_number(output.get("height", native.get("height", 0)), "output height"))
    if not (16 <= width <= 7680 and 16 <= height <= 7680):
        raise ValueError("output dimensions must be between 16 and 7680 pixels")
    return width, height


def normalize_animation(value: Any, metadata: dict) -> dict:
    """Return a canonical V2 shot. V1 zoom keyframes are migrated safely."""
    if not isinstance(value, dict):
        raise ValueError("animation must be an object")
    native = metadata.get("output") or {}
    source_w, source_h = int(native.get("width", 0)), int(native.get("height", 0))
    if source_w <= 0 or source_h <= 0:
        raise ValueError("export metadata has invalid source dimensions")
    output = value.get("output") or {}
    width, height = _aspect(output, native)
    fps = int(_number(output.get("fps", 24), "fps"))
    duration = int(_number(output.get("duration_frames", 168), "duration_frames"))
    if not 1 <= fps <= 120:
        raise ValueError("fps must be between 1 and 120")
    if not 1 <= duration <= 36_000:
        raise ValueError("duration_frames must be between 1 and 36000")

    source_aspect, output_aspect = source_w / source_h, width / height
    max_view_width = min(1.0, output_aspect / source_aspect)
    min_view_width = max_view_width / (float(native.get("wide_factor", 2)) * 16)
    keys = value.get("keyframes") or []
    if not isinstance(keys, list) or not keys:
        raise ValueError("add at least one keyframe")
    normalized, frames = [], set()
    for i, key in enumerate(keys):
        if not isinstance(key, dict):
            raise ValueError(f"keyframe {i + 1} must be an object")
        frame = int(_number(key.get("frame"), f"keyframe {i + 1} frame"))
        if not 0 <= frame < duration:
            raise ValueError(f"keyframe {i + 1} must be inside the shot duration")
        if frame in frames:
            raise ValueError("only one keyframe is allowed at each frame")
        frames.add(frame)
        center = key.get("center") or {}
        x = _number(center.get("x"), f"keyframe {i + 1} center x")
        y = _number(center.get("y"), f"keyframe {i + 1} center y")
        # V1 stored a square-view zoom. Its max view width was one source width.
        view_width = key.get("view_width")
        if view_width is None:
            zoom = _number(key.get("zoom", 1), f"keyframe {i + 1} zoom")
            view_width = max_view_width / zoom
        view_width = _number(view_width, f"keyframe {i + 1} view width")
        if not min_view_width <= view_width <= max_view_width:
            raise ValueError(f"keyframe {i + 1} view width exceeds the available image range")
        view_height = view_width * source_aspect / output_aspect
        if not (view_width / 2 <= x <= 1 - view_width / 2 and
                view_height / 2 <= y <= 1 - view_height / 2):
            raise ValueError(f"keyframe {i + 1} view exceeds wide-background coverage")
        easing = str(key.get("easing", "smooth"))
        if easing not in EASINGS:
            raise ValueError(f"keyframe {i + 1} easing must be linear or smooth")
        normalized.append({"frame": frame, "center": {"x": x, "y": y},
                           "view_width": view_width, "easing": easing})
    normalized.sort(key=lambda key: key["frame"])
    return {"schema_version": SCHEMA_VERSION,
            "name": str(value.get("name") or "Map animation")[:120],
            "assets_metadata": "metadata.json",
            "output": {"width": width, "height": height, "fps": fps,
                       "duration_frames": duration},
            "keyframes": normalized}
