"""Validation and migration for editable map-video animation shots."""
from __future__ import annotations

import math
from typing import Any

from core import package_layout

SCHEMA_VERSION = 3
EASINGS = {"linear", "smooth"}
LINE_STYLES = {"solid", "dashed"}
PATH_TYPES = {"straight", "curved"}
REGION_CATEGORIES = {"country", "administrative", "historical"}


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


def _commentary(value: Any) -> dict:
    """Optional, non-destructive narration clips in the export package."""
    if not value:
        return {"clips": []}
    if not isinstance(value, dict):
        raise ValueError("commentary must be an object")
    # Migrate the original single-commentary shape when an old shot is saved.
    clips = value.get("clips")
    if clips is None:
        clips = [] if not value.get("file") else [value]
    if not isinstance(clips, list):
        raise ValueError("commentary clips must be a list")
    normalized = []
    ids = set()
    for index, clip in enumerate(clips):
        if not isinstance(clip, dict):
            raise ValueError("commentary clip must be an object")
        file_name = str(clip.get("file", ""))
        if not file_name or "/" in file_name or "\\" in file_name or file_name.startswith("."):
            raise ValueError("commentary file must be a package-local name")
        clip_id = str(clip.get("id") or f"commentary_{index + 1}")
        if clip_id in ids:
            raise ValueError("commentary clip ids must be unique")
        ids.add(clip_id)
        trim_in = max(0.0, _number(clip.get("trim_in", 0), "commentary trim in"))
        trim_out = clip.get("trim_out")
        if trim_out is not None:
            trim_out = _number(trim_out, "commentary trim out")
            if trim_out <= trim_in:
                raise ValueError("commentary trim out must be after trim in")
        normalized.append({"id": clip_id, "file": file_name,
                           "volume": max(0.0, min(1.0, _number(clip.get("volume", 1), "commentary volume"))),
                           "start_frame": max(0, int(_number(clip.get("start_frame", 0), "commentary start frame"))),
                           "trim_in": trim_in, "trim_out": trim_out})
    return {"clips": normalized}


def _region_groups(value: Any, metadata: dict, duration: int) -> list[dict]:
    """Normalize persistent, manually controlled country and territory layers."""
    countries = {str(item.get("iso3", "")).upper(): item
                 for item in metadata.get("countries", []) if item.get("iso3")}
    if value is None:
        return [{"iso3": iso3, "start_frame": None, "end_frame": None,
                 "children": [{"id": f"country-{iso3.lower()}", "name": "Entire country",
                                "category": "country", "start_frame": None,
                                "end_frame": None}]}
                for iso3 in countries]
    if not isinstance(value, list):
        raise ValueError("region_groups must be a list")
    groups, seen_countries = [], set()
    for group_index, group in enumerate(value):
        if not isinstance(group, dict):
            raise ValueError("region group must be an object")
        iso3 = str(group.get("iso3", "")).upper()
        if iso3 not in countries:
            raise ValueError(f"region group country is not in this export: {iso3}")
        if iso3 in seen_countries:
            raise ValueError(f"only one region group is allowed for {iso3}")
        seen_countries.add(iso3)
        children_value = group.get("children") or []
        if not isinstance(children_value, list):
            raise ValueError(f"{iso3} region children must be a list")
        children, ids = [], set()
        for child_index, child in enumerate(children_value):
            if not isinstance(child, dict):
                raise ValueError(f"{iso3} child region must be an object")
            identifier = str(child.get("id", ""))[:120]
            if not __import__("re").fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,119}", identifier):
                raise ValueError(f"{iso3} child region has an invalid id")
            if identifier in ids:
                raise ValueError(f"{iso3} child region ids must be unique")
            ids.add(identifier)
            category = str(child.get("category", ""))
            if category not in REGION_CATEGORIES:
                raise ValueError(f"{iso3} child region has an invalid category")
            if category == "historical" and iso3 != "USA":
                raise ValueError("historical acquisition regions are available only for USA")
            normalized = {"id": identifier, "name": str(child.get("name") or identifier)[:120],
                          "category": category, "start_frame": None,
                          "end_frame": None}
            geometry_file = child.get("geometry_file")
            if geometry_file:
                geometry_file = str(geometry_file)
                if not __import__("re").fullmatch(r"(?:data/)?regions/geometry_[A-Za-z0-9_.-]+\.geojson", geometry_file):
                    raise ValueError("sub-territory geometry file must be package-local")
                normalized["geometry_file"] = geometry_file
            children.append(normalized)
        groups.append({"iso3": iso3, "start_frame": None, "end_frame": None,
                       "children": children})
    # Metadata order remains authoritative and missing groups are restored with
    # the backward-compatible entire-country child.
    by_country = {group["iso3"]: group for group in groups}
    defaults = _region_groups(None, metadata, duration)
    return [by_country.get(group["iso3"], group) for group in defaults]


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
        normalized_key = {"frame": frame, "center": {"x": x, "y": y},
                          "view_width": view_width, "easing": easing}
        # An optional Fusion-path offset records a creator-approved camera
        # calibration without changing the browser's geographic camera key.
        fusion_path = key.get("fusion_path")
        if fusion_path is not None:
            if not isinstance(fusion_path, dict):
                raise ValueError(f"keyframe {i + 1} fusion path must be an object")
            normalized_key["fusion_path"] = {
                "x": _number(fusion_path.get("x"), f"keyframe {i + 1} fusion path x"),
                "y": _number(fusion_path.get("y"), f"keyframe {i + 1} fusion path y"),
            }
        normalized.append(normalized_key)
    normalized.sort(key=lambda key: key["frame"])
    connections = value.get("connections") or []
    if not isinstance(connections, list):
        raise ValueError("connections must be a list")
    normalized_connections = []
    seen_ids = set()
    for index, connection in enumerate(connections):
        if not isinstance(connection, dict):
            raise ValueError(f"connection {index + 1} must be an object")
        identifier = str(connection.get("id") or f"connection_{index + 1}")[:80]
        if identifier in seen_ids:
            raise ValueError("connection IDs must be unique")
        seen_ids.add(identifier)
        def point(key: str, *, required: bool = False) -> dict | None:
            raw = connection.get(key) or {}
            if not raw and not required:
                return None
            x, y = _number(raw.get("x"), f"connection {index + 1} {key} x"), _number(raw.get("y"), f"connection {index + 1} {key} y")
            if not (0 <= x <= 1 and 0 <= y <= 1):
                raise ValueError(f"connection {index + 1} {key} must be inside the map")
            return {"x": x, "y": y}
        start, end = point("start"), point("end")
        path_type = str(connection.get("path_type", "straight"))
        line_style = str(connection.get("line_style", "solid"))
        if path_type not in PATH_TYPES or line_style not in LINE_STYLES:
            raise ValueError(f"connection {index + 1} has an invalid path or line style")
        bend = point("bend") if path_type == "curved" and start and end else None
        start_frame = int(_number(connection.get("start_frame", 0), f"connection {index + 1} start frame"))
        arrival_frame = int(_number(connection.get("arrival_frame", 1), f"connection {index + 1} arrival frame"))
        raw_disappearance = connection.get("disappearance_frame")
        disappearance_frame = None if raw_disappearance is None else int(_number(
            raw_disappearance, f"connection {index + 1} disappearance frame"))
        effective_end = duration - 1 if disappearance_frame is None else disappearance_frame
        if start and end and not (0 <= start_frame < arrival_frame < effective_end < duration):
            raise ValueError(f"connection {index + 1} timing must satisfy start < arrival < disappearance inside the shot")
        color = str(connection.get("color", "#ffffff"))
        if not __import__("re").fullmatch(r"#[0-9a-fA-F]{6}", color):
            raise ValueError(f"connection {index + 1} color must be a hex color")
        thickness = _number(connection.get("thickness", 2), f"connection {index + 1} thickness")
        if not 0.25 <= thickness <= 30:
            raise ValueError(f"connection {index + 1} thickness must be between 0.25 and 30")
        easing = str(connection.get("easing", "linear"))
        if easing not in EASINGS:
            raise ValueError(f"connection {index + 1} easing must be linear or smooth")
        normalized_connections.append({"id": identifier, "name": str(connection.get("name") or f"Connection {index + 1}")[:120],
            "start": start, "end": end, "bend": bend, "path_type": path_type, "line_style": line_style,
            "color": color, "thickness": thickness, "arrowhead": bool(connection.get("arrowhead", True)),
            "arrow_size": max(1, min(100, _number(connection.get("arrow_size", 14), f"connection {index + 1} arrow size"))),
            "start_frame": start_frame, "arrival_frame": arrival_frame, "disappearance_frame": disappearance_frame, "easing": easing})
    metadata_file = (str(package_layout.METADATA_FILE)
                     if int((metadata.get("package_layout") or {}).get("version", 1))
                     >= package_layout.VERSION
                     else str(package_layout.LEGACY_METADATA_FILE))
    return {"schema_version": SCHEMA_VERSION,
            "name": str(value.get("name") or "Map animation")[:120],
            "assets_metadata": metadata_file,
            "output": {"width": width, "height": height, "fps": fps,
                       "duration_frames": duration},
             "commentary": _commentary(value.get("commentary")),
             "keyframes": normalized, "connections": normalized_connections,
             "region_groups": _region_groups(value.get("region_groups"), metadata, duration)}
