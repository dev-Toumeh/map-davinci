#!/usr/bin/env python3
"""Build an isolated Fusion prototype with a sparse shared vector camera.

The normal exporter uses a dense PolyPath displacement curve so raster and
vector layers match at every rendered frame.  That is accurate, but long
shots produce one vector-camera key per frame.  This tool replaces only that
controller in an already exported composition with a shared XYPath whose X
and Y curves are adaptively fitted to the same per-frame camera samples.

The source composition and the application exporter are never modified.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from fusion.generator import _camera_samples  # noqa: E402


def _fit_handles(samples: list[dict], first: int, last: int, field: str) -> tuple[float, float]:
    """Least-squares cubic handles, constrained to the endpoint range."""
    y0, y3 = samples[first][field], samples[last][field]
    if last - first < 2 or abs(y3 - y0) < 1e-15:
        return y0 + (y3 - y0) / 3, y0 + 2 * (y3 - y0) / 3
    aa = ab = bb = ar = br = 0.0
    for index in range(first + 1, last):
        t = (index - first) / (last - first)
        u = 1.0 - t
        basis_a, basis_b = 3 * u * u * t, 3 * u * t * t
        residual = samples[index][field] - y0 * u**3 - y3 * t**3
        aa += basis_a * basis_a
        ab += basis_a * basis_b
        bb += basis_b * basis_b
        ar += basis_a * residual
        br += basis_b * residual
    determinant = aa * bb - ab * ab
    if abs(determinant) < 1e-20:
        right, left = y0 + (y3 - y0) / 3, y0 + 2 * (y3 - y0) / 3
    else:
        right = (ar * bb - br * ab) / determinant
        left = (br * aa - ar * ab) / determinant
    low, high = sorted((y0, y3))
    return max(low, min(high, right)), max(low, min(high, left))


def _evaluate(y0: float, right: float, left: float, y3: float, t: float) -> float:
    u = 1.0 - t
    return y0 * u**3 + 3 * right * u * u * t + 3 * left * u * t * t + y3 * t**3


def _sparse_indices(samples: list[dict], authored_frames: set[int], width: int,
                    height: int, tolerance_px: float) -> list[int]:
    offset = samples[0]["frame"]
    retained = {frame - offset for frame in authored_frames}
    retained.update({0, len(samples) - 1})

    def split(first: int, last: int) -> None:
        if last - first < 2:
            return
        x_right, x_left = _fit_handles(samples, first, last, "vector_x")
        y_right, y_left = _fit_handles(samples, first, last, "vector_y")
        worst_error, worst_index = 0.0, None
        for index in range(first + 1, last):
            t = (index - first) / (last - first)
            x = _evaluate(samples[first]["vector_x"], x_right, x_left,
                          samples[last]["vector_x"], t)
            y = _evaluate(samples[first]["vector_y"], y_right, y_left,
                          samples[last]["vector_y"], t)
            dx = (x - samples[index]["vector_x"]) * width
            dy = (y - samples[index]["vector_y"]) * height
            error = (dx * dx + dy * dy) ** 0.5
            if error > worst_error:
                worst_error, worst_index = error, index
        if worst_error > tolerance_px and worst_index is not None:
            retained.add(worst_index)
            split(first, worst_index)
            split(worst_index, last)

    anchors = sorted(retained)
    for first, last in zip(anchors, anchors[1:]):
        split(first, last)
    return sorted(retained)


def _curve(samples: list[dict], indices: list[int], field: str, color: tuple[int, int, int]) -> str:
    handles: dict[tuple[int, str], tuple[float, float]] = {}
    for first, last in zip(indices, indices[1:]):
        right, left = _fit_handles(samples, first, last, field)
        first_frame, last_frame = samples[first]["frame"], samples[last]["frame"]
        third = (last_frame - first_frame) / 3
        handles[first, "RH"] = (first_frame + third, right)
        handles[last, "LH"] = (last_frame - third, left)
    lines = []
    for index in indices:
        frame = samples[index]["frame"]
        parts = [f'{samples[index][field]:.12g}']
        for side in ("LH", "RH"):
            handle = handles.get((index, side))
            if handle:
                parts.append(f'{side} = {{ {handle[0]:.12g}, {handle[1]:.12g} }}')
        lines.append(f'\t\t\t\t[{frame}] = {{ {", ".join(parts)} }},')
    red, green, blue = color
    return (f'BezierSpline {{ SplineColor = {{ Red = {red}, Green = {green}, Blue = {blue} }}, '
            f'KeyFrames = {{\n{chr(10).join(lines)}\n\t\t\t}} }}')


def _tool_span(content: str, name: str) -> tuple[int, int]:
    marker = f'\t\t{name} = '
    start = content.find(marker)
    if start < 0:
        raise ValueError(f"Could not find {name} in the composition")
    brace = content.find("{", start + len(marker))
    if brace < 0:
        raise ValueError(f"Malformed {name} tool")
    depth = 0
    in_string = False
    escaped = False
    for index in range(brace, len(content)):
        char = content[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                end = index + 1
                if end < len(content) and content[end] == ",":
                    end += 1
                return start, end
    raise ValueError(f"Unbalanced braces in {name}")


def _replace_vector_controller(content: str, controller: str) -> str:
    spans = [_tool_span(content, "Vector_AnimationDisplacement"),
             _tool_span(content, "Vector_AnimationPath")]
    start = min(span[0] for span in spans)
    end = max(span[1] for span in spans)
    between = content[start:end]
    if between.count("Vector_AnimationDisplacement") != 2:
        raise ValueError("Unexpected vector controller structure; refusing an unsafe replacement")
    return content[:start] + controller + content[end:]


def _max_error(samples: list[dict], indices: list[int], width: int, height: int) -> float:
    maximum = 0.0
    for first, last in zip(indices, indices[1:]):
        xr, xl = _fit_handles(samples, first, last, "vector_x")
        yr, yl = _fit_handles(samples, first, last, "vector_y")
        for index in range(first + 1, last):
            t = (index - first) / (last - first)
            dx = (_evaluate(samples[first]["vector_x"], xr, xl,
                            samples[last]["vector_x"], t) - samples[index]["vector_x"]) * width
            dy = (_evaluate(samples[first]["vector_y"], yr, yl,
                            samples[last]["vector_y"], t) - samples[index]["vector_y"]) * height
            maximum = max(maximum, (dx * dx + dy * dy) ** 0.5)
    return maximum


def build(package: Path, source: Path, target: Path, tolerance_px: float) -> dict:
    metadata = json.loads((package / "metadata.json").read_text(encoding="utf-8"))
    animation = json.loads((package / "animation.json").read_text(encoding="utf-8"))
    samples = _camera_samples(animation, metadata["output"])
    native = metadata["output"]
    output = animation["output"]
    vector_width = max(native["width"], output["width"])
    vector_height = max(native["height"], output["height"])
    x_scale = native["width"] / vector_width
    y_scale = native["height"] / vector_height
    for sample in samples:
        # Path/XYPath modifier coordinates are stored relative to Fusion's
        # implicit 0.5,0.5 point origin. PolyPath adds that origin when it
        # publishes Position; XYPath does the same, so feed it the raw offset.
        # Adding 0.5 here a second time displaces masks from the raster map.
        sample["vector_x"] = sample["fusion_path"]["x"] * x_scale
        sample["vector_y"] = sample["fusion_path"]["y"] * y_scale
    authored_frames = {key["frame"] for key in animation["keyframes"]}
    indices = _sparse_indices(samples, authored_frames, vector_width, vector_height, tolerance_px)
    x_curve = _curve(samples, indices, "vector_x", (255, 0, 0))
    y_curve = _curve(samples, indices, "vector_y", (0, 255, 0))
    controller = f'''\t\tVector_AnimationX = {x_curve},
\t\tVector_AnimationY = {y_curve},
\t\tVector_AnimationPath = XYPath {{
\t\t\tInputs = {{
\t\t\t\tX = Input {{ SourceOp = "Vector_AnimationX", Source = "Value", }},
\t\t\t\tY = Input {{ SourceOp = "Vector_AnimationY", Source = "Value", }},
\t\t\t}},
\t\t}},'''
    original = source.read_text(encoding="utf-8")
    result = _replace_vector_controller(original, controller)
    if result.count('SourceOp = "Vector_AnimationPath", Source = "Position"') == 0:
        raise ValueError("No vector masks reference the shared controller")
    if result.count("Vector_AnimationDisplacement"):
        raise ValueError("Dense vector controller was not fully removed")
    target.write_text(result, encoding="utf-8")
    key_pattern = re.compile(r"^\s*\[\d+\] = \{", re.MULTILINE)
    source_key_count = len(key_pattern.findall(original))
    target_key_count = len(key_pattern.findall(result))
    return {
        "source": str(source),
        "target": str(target),
        "source_bytes": len(original.encode("utf-8")),
        "target_bytes": len(result.encode("utf-8")),
        "rendered_frames": len(samples),
        "authored_camera_frames": len(authored_frames),
        "sparse_vector_keys_per_axis": len(indices),
        "total_sparse_vector_keys": len(indices) * 2,
        "source_serialized_animation_keys": source_key_count,
        "target_serialized_animation_keys": target_key_count,
        "animation_key_reduction_percent": round(
            100 * (source_key_count - target_key_count) / source_key_count, 2
        ) if source_key_count else 0,
        "maximum_sample_error_px": _max_error(samples, indices, vector_width, vector_height),
        "requested_tolerance_px": tolerance_px,
        "vector_canvas": {"width": vector_width, "height": vector_height},
        "xy_path_coordinates": "relative to Fusion's implicit 0.5,0.5 origin",
        "note": "Open the target in Resolve and compare playback/alignment; the exporter was not changed.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--tolerance-px", type=float, default=0.25)
    args = parser.parse_args()
    package = args.package.resolve()
    source = (args.source or package / "fusion" / "scene_v001.comp").resolve()
    target = (args.output or source.with_name(source.stem + "_sparse_xy_prototype.comp")).resolve()
    if source == target:
        raise SystemExit("Output must differ from the source composition")
    report = build(package, source, target, args.tolerance_px)
    report_path = target.with_suffix(".report.json")
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
