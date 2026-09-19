"""Validation and normalization for editable 2D map-animation shots."""
from __future__ import annotations

import math
from typing import Any

SCHEMA_VERSION = 1
EASINGS = {"linear", "smooth"}


def _number(value: Any, name: str) -> float:
    try:
        value = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a number") from exc
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


def normalize_animation(value: Any, metadata: dict) -> dict:
    """Return a safe, canonical animation document for this export package."""
    if not isinstance(value, dict):
        raise ValueError("animation must be an object")
    output = value.get("output") or {}
    native = metadata.get("output") or {}
    width = int(output.get("width", native.get("width", 0)))
    height = int(output.get("height", native.get("height", 0)))
    if (width, height) != (native.get("width"), native.get("height")):
        raise ValueError("animation output dimensions must match this exported package")
    fps = int(_number(output.get("fps", 24), "fps"))
    duration = int(_number(output.get("duration_frames", 168), "duration_frames"))
    if not 1 <= fps <= 120:
        raise ValueError("fps must be between 1 and 120")
    if not 1 <= duration <= 36_000:
        raise ValueError("duration_frames must be between 1 and 36000")

    wide_factor = _number(native.get("wide_factor", 2), "metadata wide_factor")
    keys = value.get("keyframes") or []
    if not isinstance(keys, list) or not keys:
        raise ValueError("add at least one keyframe")
    normalized = []
    frames = set()
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
        zoom = _number(key.get("zoom"), f"keyframe {i + 1} zoom")
        if zoom < 1 or zoom > wide_factor * 16:
            raise ValueError(f"keyframe {i + 1} zoom must be between 1 and {wide_factor * 16:g}")
        # The entire output view must stay on the wide image. This is also the
        # browser renderer's invariant, preventing black/transparent edges.
        half_w = 0.5 / zoom
        half_h = 0.5 / zoom
        if not (half_w <= x <= 1 - half_w and half_h <= y <= 1 - half_h):
            raise ValueError(f"keyframe {i + 1} view exceeds wide-background coverage")
        easing = str(key.get("easing", "smooth"))
        if easing not in EASINGS:
            raise ValueError(f"keyframe {i + 1} easing must be linear or smooth")
        normalized.append({"frame": frame, "center": {"x": x, "y": y},
                           "zoom": zoom, "easing": easing})
    normalized.sort(key=lambda key: key["frame"])
    return {
        "schema_version": SCHEMA_VERSION,
        "name": str(value.get("name") or "Map animation")[:120],
        "assets_metadata": "metadata.json",
        "output": {"width": width, "height": height, "fps": fps,
                   "duration_frames": duration},
        "keyframes": normalized,
    }
