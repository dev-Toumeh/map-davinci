#!/usr/bin/env python3
"""Build one adaptive close-up image and patch it into a Fusion comp copy.

This is deliberately a prototype tool: it proves that a native-resolution
regional image can be camera-transformed independently and composited after
the global map transform, without adding polygon animation keyframes.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

from core import exporter, package_layout
from fusion.generator import _camera_timing_keys, _key_lines, _path_points


def _camera(animation: dict, frame: int) -> tuple[float, float, float]:
    keys = sorted(animation["keyframes"], key=lambda key: key["frame"])
    index = 0
    while index < len(keys) - 1 and frame > keys[index + 1]["frame"]:
        index += 1
    start, end = keys[index], keys[min(index + 1, len(keys) - 1)]
    span = end["frame"] - start["frame"]
    amount = (frame - start["frame"]) / span if span else 0.0
    if end.get("easing", "smooth") == "smooth":
        amount = amount * amount * (3 - 2 * amount)
    center_x = start["center"]["x"] + (end["center"]["x"] - start["center"]["x"]) * amount
    center_y = start["center"]["y"] + (end["center"]["y"] - start["center"]["y"]) * amount
    width = start["view_width"] + (end["view_width"] - start["view_width"]) * amount
    return center_x, center_y, width


def _local_samples(animation: dict, bbox: tuple[float, float, float, float],
                   first: int, last: int) -> list[dict]:
    x0, y0, x1, y1 = bbox
    local_width, local_height = x1 - x0, y1 - y0
    samples = []
    for frame in range(first, last + 1):
        x, y, view_width = _camera(animation, frame)
        local_x, local_y = (x - x0) / local_width, (y - y0) / local_height
        zoom = local_width / view_width
        samples.append({
            "frame": frame,
            "zoom": zoom,
            "fusion_path": {
                "x": (0.5 - local_x) * zoom,
                "y": (local_y - 0.5) * zoom,
            },
        })
    lengths = [0.0]
    for previous, current in zip(samples, samples[1:]):
        p, q = previous["fusion_path"], current["fusion_path"]
        lengths.append(lengths[-1] + math.hypot(q["x"] - p["x"], q["y"] - p["y"]))
    total = lengths[-1]
    for sample, length in zip(samples, lengths):
        sample["displacement"] = length / total if total else 0.0
    return samples


def _block(text: str, name: str, kind: str) -> tuple[int, int, str]:
    match = re.search(rf"(?m)^\s*{re.escape(name)} = {re.escape(kind)} \{{", text)
    if not match:
        raise ValueError(f"Fusion node not found: {name}")
    opening, depth = text.find("{", match.start()), 0
    for index in range(opening, len(text)):
        depth += (text[index] == "{") - (text[index] == "}")
        if depth == 0:
            return match.start(), index + 1, text[match.start():index + 1]
    raise ValueError(f"Unterminated Fusion node: {name}")


def _replace_source(text: str, node: str, kind: str,
                    old_source: str, new_source: str) -> str:
    start, end, block = _block(text, node, kind)
    old = f'SourceOp = "{old_source}"'
    if old not in block:
        raise ValueError(f"{node} is not connected to {old_source}")
    return text[:start] + block.replace(old, f'SourceOp = "{new_source}"', 1) + text[end:]


def _mercator_bbox(metadata: dict, normalized: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    wide = metadata["wide"]["bbox_mercator"]
    span_x, span_y = wide["maxx"] - wide["minx"], wide["maxy"] - wide["miny"]
    x0, y0, x1, y1 = normalized
    return (wide["minx"] + x0 * span_x,
            wide["maxy"] - y1 * span_y,
            wide["minx"] + x1 * span_x,
            wide["maxy"] - y0 * span_y)


def build(package: Path, composition: Path, target_frame: int,
          margin: float, output: Path) -> tuple[Path, Path, tuple[int, int]]:
    metadata = json.loads(package_layout.metadata_path(package).read_text(encoding="utf-8"))
    animation = json.loads(package_layout.animation_path(package).read_text(encoding="utf-8"))
    output_config, native = animation["output"], metadata["output"]
    center_x, center_y, view_width = _camera(animation, target_frame)
    source_aspect = native["width"] / native["height"]
    output_aspect = output_config["width"] / output_config["height"]
    view_height = view_width * source_aspect / output_aspect
    local_width, local_height = view_width * (1 + 2 * margin), view_height * (1 + 2 * margin)
    normalized = (center_x - local_width / 2, center_y - local_height / 2,
                  center_x + local_width / 2, center_y + local_height / 2)

    # Determine the complete interval where the camera viewport remains inside
    # the regional plate. Fade slightly inside these hard coverage boundaries.
    valid = []
    duration = int(output_config["duration_frames"])
    for frame in range(duration):
        x, y, width = _camera(animation, frame)
        height = width * source_aspect / output_aspect
        if (x - width / 2 >= normalized[0] and x + width / 2 <= normalized[2] and
                y - height / 2 >= normalized[1] and y + height / 2 <= normalized[3]):
            valid.append(frame)
    if target_frame not in valid:
        raise ValueError("target camera does not fit its generated Close-up extent")
    first = last = target_frame
    while first - 1 in valid:
        first -= 1
    while last + 1 in valid:
        last += 1
    fade = min(6, max(1, (last - first) // 4))
    full_first, full_last = first + fade, last - fade

    mercator_bbox = _mercator_bbox(metadata, normalized)
    minx, miny, maxx, maxy = mercator_bbox
    center_lon, center_lat = exporter.merc_to_ll((minx + maxx) / 2, (miny + maxy) / 2)
    target_mpp = (maxx - minx) / int(output_config["width"])
    ground_mpp = target_mpp * math.cos(math.radians(center_lat))
    source_key = metadata.get("imagery", {}).get("source", "google_satellite")
    source = exporter.SOURCES[source_key]
    zoom, _ = exporter.choose_tile_zoom(ground_mpp, center_lat, source["max_zoom"])
    image_dir = output.parent.parent / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    image_path = image_dir / f"closeup_frame_{target_frame:04d}.png"

    def progress(stage: str, pct: float, message: str) -> None:
        print(f"{stage}: {pct:5.1f}% {message}")

    image = exporter.stitch_bbox(
        source, source_key, zoom, mercator_bbox,
        (int(output_config["width"]), int(output_config["height"])),
        progress, f"closeup_{target_frame}")
    image.save(image_path)

    samples = _local_samples(animation, normalized, first, last)
    authored = {first, target_frame, last}
    keys = _camera_timing_keys(samples, authored)
    duration_end = int(re.search(r"GlobalRange = \{\s*0,\s*(\d+)\s*\}",
                                 composition.read_text(encoding="utf-8")).group(1))
    node = f"Closeup_{target_frame:04d}"
    visibility = {
        0: 0, first: 0, full_first: 1, full_last: 1,
        last: 0, duration_end: 0,
    }
    visibility_lines = "\n".join(
        f'\t\t\t\t[{frame}] = {{ {value}, Flags = {{ Linear = true }} }},'
        for frame, value in sorted(visibility.items()))
    nodes = f'''\t\t{node}_Loader = Loader {{ NameSet = true, Clips = {{ Clip {{ ID = "Clip1", Filename = "{str(image_path.resolve()).replace(chr(92), chr(92) * 2).replace(chr(34), chr(92) + chr(34))}", Length = 1, GlobalEnd = {duration_end}, TrimOut = 0, Loop = 1 }} }}, ViewInfo = OperatorInfo {{ Pos = {{ 1930, -260 }} }}, }},
\t\t{node}_Displacement = BezierSpline {{ KeyFrames = {{
{_key_lines(keys, samples, 'displacement')}
\t\t\t}} }},
\t\t{node}_Size = BezierSpline {{ KeyFrames = {{
{_key_lines(keys, samples, 'size')}
\t\t\t}} }},
\t\t{node}_Path = PolyPath {{ Inputs = {{ Displacement = Input {{ SourceOp = "{node}_Displacement", Source = "Value", }}, PolyLine = Input {{ Value = Polyline {{ Points = {{
{_path_points(samples)}
\t\t\t\t\t\t}} }}, }} }}, }},
\t\t{node}_Animation = Transform {{ NameSet = true, Inputs = {{ Center = Input {{ SourceOp = "{node}_Path", Source = "Position", }}, Size = Input {{ SourceOp = "{node}_Size", Source = "Value", }}, ClippingMode = Input {{ Value = FuID {{ "None" }}, }}, Input = Input {{ SourceOp = "{node}_Loader", Source = "Output", }} }}, ViewInfo = OperatorInfo {{ Pos = {{ 2160, -260 }} }}, }},
\t\t{node}_Visibility = BezierSpline {{ KeyFrames = {{
{visibility_lines}
\t\t\t}} }},
\t\tMap_LOD_Composite = Merge {{ NameSet = true, Inputs = {{ Background = Input {{ SourceOp = "Map_Animation", Source = "Output", }}, Foreground = Input {{ SourceOp = "{node}_Animation", Source = "Output", }}, Blend = Input {{ SourceOp = "{node}_Visibility", Source = "Value", }} }}, ViewInfo = OperatorInfo {{ Pos = {{ 2390, -130 }} }}, }},
\t\tCountry_Animation = Transform {{ NameSet = true, Inputs = {{ Center = Input {{ SourceOp = "Map_AnimationPath", Source = "Position", }}, Size = Input {{ SourceOp = "Map_AnimationSize", Source = "Value", }}, ClippingMode = Input {{ Value = FuID {{ "None" }}, }}, Input = Input {{ SourceOp = "Country_Mode_Switch", Source = "Output", }} }}, ViewInfo = OperatorInfo {{ Pos = {{ 2390, 130 }} }}, }},
\t\tMap_Country_LOD_Composite = Merge {{ NameSet = true, Inputs = {{ Background = Input {{ SourceOp = "Map_LOD_Composite", Source = "Output", }}, Foreground = Input {{ SourceOp = "Country_Animation", Source = "Output", }} }}, ViewInfo = OperatorInfo {{ Pos = {{ 2620, 0 }} }}, }},
'''
    text = composition.read_text(encoding="utf-8")
    if node in text:
        raise ValueError(f"composition already contains {node}")
    text = _replace_source(text, "Map_Animation", "Transform",
                           "Map_Country_Layers", "Map_Raster_Layers")
    text = _replace_source(text, "Final_Composite", "Merge",
                           "Map_Animation", "Map_Country_LOD_Composite")
    tools_match = re.search(r"(?m)^\s*Tools = \{", text)
    if not tools_match:
        raise ValueError("could not locate Fusion Tools block")
    tools_opening, depth, insertion = text.find("{", tools_match.start()), 0, -1
    for index in range(tools_opening, len(text)):
        depth += (text[index] == "{") - (text[index] == "}")
        if depth == 0:
            insertion = index
            break
    if insertion < 0:
        raise ValueError("could not locate Fusion Tools closing block")
    prefix = text[:insertion].rstrip()
    if not prefix.endswith("}"):
        raise ValueError("Fusion Tools block does not end with a tool definition")
    # Resolve omits the trailing comma from the final saved tool. Once new
    # tools are appended, that former final tool needs a table separator.
    text = prefix + ",\n" + nodes + text[insertion:]
    output.write_text(text, encoding="utf-8")
    return output, image_path, (first, last)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("package", type=Path)
    parser.add_argument("composition", type=Path)
    parser.add_argument("--frame", type=int, required=True)
    parser.add_argument("--margin", type=float, default=.25)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    comp, image, active = build(args.package.resolve(), args.composition.resolve(),
                                args.frame, args.margin, args.output.resolve())
    print(f"composition: {comp}")
    print(f"image: {image}")
    print(f"coverage: frames {active[0]}-{active[1]}")


if __name__ == "__main__":
    main()
