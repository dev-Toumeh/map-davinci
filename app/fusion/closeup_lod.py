"""Plan and cache high-resolution local map plates for deep camera zooms."""
from __future__ import annotations

import hashlib
import math
from pathlib import Path

from core import exporter, package_layout


MAX_DETAIL_MAGNIFICATION = 6.0
CLOSEUP_MARGIN = 0.25
MAX_CLOSEUPS = 12


def camera_at(animation: dict, frame: int) -> tuple[float, float, float]:
    keys = sorted(animation["keyframes"], key=lambda key: key["frame"])
    index = 0
    while index < len(keys) - 1 and frame > keys[index + 1]["frame"]:
        index += 1
    start, end = keys[index], keys[min(index + 1, len(keys) - 1)]
    span = end["frame"] - start["frame"]
    amount = (frame - start["frame"]) / span if span else 0.0
    amount = max(0.0, min(1.0, amount))
    if end.get("easing", "smooth") == "smooth":
        amount = amount * amount * (3 - 2 * amount)
    return (
        start["center"]["x"] + (end["center"]["x"] - start["center"]["x"]) * amount,
        start["center"]["y"] + (end["center"]["y"] - start["center"]["y"]) * amount,
        start["view_width"] + (end["view_width"] - start["view_width"]) * amount,
    )


def _normalized_bbox(metadata: dict, animation: dict, frame: int,
                     margin: float) -> tuple[float, float, float, float]:
    native, output = metadata["output"], animation["output"]
    center_x, center_y, view_width = camera_at(animation, frame)
    view_height = (view_width * native["width"] / native["height"] /
                   (output["width"] / output["height"]))
    local_width = view_width * (1 + 2 * margin)
    local_height = view_height * (1 + 2 * margin)
    return (center_x - local_width / 2, center_y - local_height / 2,
            center_x + local_width / 2, center_y + local_height / 2)


def mercator_bbox(metadata: dict, normalized: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    wide = metadata["wide"]["bbox_mercator"]
    span_x, span_y = wide["maxx"] - wide["minx"], wide["maxy"] - wide["miny"]
    x0, y0, x1, y1 = normalized
    return (wide["minx"] + x0 * span_x,
            wide["maxy"] - y1 * span_y,
            wide["minx"] + x1 * span_x,
            wide["maxy"] - y0 * span_y)


def _coverage(metadata: dict, animation: dict,
              normalized: tuple[float, float, float, float],
              target: int) -> tuple[int, int]:
    native, output = metadata["output"], animation["output"]
    source_aspect = native["width"] / native["height"]
    output_aspect = output["width"] / output["height"]
    valid = set()
    for frame in range(int(output["duration_frames"])):
        x, y, width = camera_at(animation, frame)
        height = width * source_aspect / output_aspect
        if (x - width / 2 >= normalized[0] and x + width / 2 <= normalized[2] and
                y - height / 2 >= normalized[1] and y + height / 2 <= normalized[3]):
            valid.add(frame)
    first = last = target
    while first - 1 in valid:
        first -= 1
    while last + 1 in valid:
        last += 1
    return first, last


def local_samples(animation: dict, normalized: tuple[float, float, float, float],
                  first: int, last: int) -> list[dict]:
    x0, y0, x1, y1 = normalized
    local_width, local_height = x1 - x0, y1 - y0
    samples = []
    for frame in range(first, last + 1):
        x, y, view_width = camera_at(animation, frame)
        local_x, local_y = (x - x0) / local_width, (y - y0) / local_height
        zoom = local_width / view_width
        samples.append({"frame": frame, "zoom": zoom,
                        "fusion_path": {"x": (0.5 - local_x) * zoom,
                                        "y": (local_y - 0.5) * zoom}})
    lengths = [0.0]
    for previous, current in zip(samples, samples[1:]):
        p, q = previous["fusion_path"], current["fusion_path"]
        lengths.append(lengths[-1] + math.hypot(q["x"] - p["x"], q["y"] - p["y"]))
    total = lengths[-1]
    for sample, length in zip(samples, lengths):
        sample["displacement"] = length / total if total else 0.0
    return samples


def plan_closeups(metadata: dict, animation: dict) -> list[dict]:
    """Choose a small set of deep authored views and their useful intervals."""
    native, output = metadata["output"], animation["output"]
    factor = float(native["wide_factor"])
    candidates = []
    for key in animation["keyframes"]:
        magnification = output["width"] / native["width"] / key["view_width"] / factor
        if magnification > MAX_DETAIL_MAGNIFICATION:
            candidates.append((magnification, int(key["frame"])))
    selected = []
    for magnification, frame in sorted(candidates, reverse=True):
        if any(plan["first"] <= frame <= plan["last"] for plan in selected):
            continue
        normalized = _normalized_bbox(metadata, animation, frame, CLOSEUP_MARGIN)
        first, last = _coverage(metadata, animation, normalized, frame)
        fade = min(6, max(1, (last - first) // 4))
        selected.append({
            "frame": frame, "magnification": magnification,
            "normalized_bbox": normalized,
            "bbox_mercator": mercator_bbox(metadata, normalized),
            "first": first, "last": last,
            "full_first": min(last, first + fade),
            "full_last": max(first, last - fade),
        })
        if len(selected) >= MAX_CLOSEUPS:
            break
    return sorted(selected, key=lambda plan: plan["frame"])


def ensure_images(package: Path, metadata: dict, animation: dict,
                  plans: list[dict]) -> list[dict]:
    """Generate missing close-up plates and reuse deterministic cached files."""
    if not plans:
        return plans
    source_key = metadata.get("imagery", {}).get("source", "google_satellite")
    source = exporter.SOURCES[source_key]
    output = animation["output"]
    image_dir = package / package_layout.closeups_relative(package)
    image_dir.mkdir(parents=True, exist_ok=True)
    for plan in plans:
        signature = repr((plan["bbox_mercator"], output["width"], output["height"],
                          source_key)).encode()
        suffix = hashlib.sha256(signature).hexdigest()[:10]
        image_path = image_dir / f'closeup_{plan["frame"]:04d}_{suffix}.png'
        if not image_path.is_file():
            minx, miny, maxx, maxy = plan["bbox_mercator"]
            center_lon, center_lat = exporter.merc_to_ll((minx + maxx) / 2,
                                                         (miny + maxy) / 2)
            target_mpp = (maxx - minx) / int(output["width"])
            ground_mpp = target_mpp * math.cos(math.radians(center_lat))
            zoom, _ = exporter.choose_tile_zoom(ground_mpp, center_lat, source["max_zoom"])
            image = exporter.stitch_bbox(
                source, source_key, zoom, plan["bbox_mercator"],
                (int(output["width"]), int(output["height"])),
                lambda *_args: None, f'closeup_{plan["frame"]}',
            )
            image.save(image_path)
        plan["image_path"] = image_path
    return plans
