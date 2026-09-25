#!/usr/bin/env python3
"""Replace dense vector movement with six authored camera curves and expressions."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from tools.build_sparse_vector_camera import _replace_vector_controller  # noqa: E402


def _curve(keys: list[dict], field: str, color: tuple[int, int, int]) -> str:
    handles: dict[tuple[int, str], tuple[float, float]] = {}
    for first, last in zip(keys, keys[1:]):
        frame_a, frame_b = first["frame"], last["frame"]
        value_a, value_b = first[field], last[field]
        third = (frame_b - frame_a) / 3
        if last.get("easing", "smooth") == "smooth":
            right_value, left_value = value_a, value_b
        else:
            right_value = value_a + (value_b - value_a) / 3
            left_value = value_a + 2 * (value_b - value_a) / 3
        handles[first["frame"], "RH"] = (frame_a + third, right_value)
        handles[last["frame"], "LH"] = (frame_b - third, left_value)
    lines = []
    for key in keys:
        frame = key["frame"]
        parts = [f'{key[field]:.12g}']
        for side in ("LH", "RH"):
            handle = handles.get((frame, side))
            if handle:
                parts.append(f'{side} = {{ {handle[0]:.12g}, {handle[1]:.12g} }}')
        lines.append(f'\t\t\t\t[{frame}] = {{ {", ".join(parts)} }},')
    red, green, blue = color
    return (f'BezierSpline {{ SplineColor = {{ Red = {red}, Green = {green}, Blue = {blue} }}, '
            f'KeyFrames = {{\n{chr(10).join(lines)}\n\t\t\t}} }}')


def build(package: Path, source: Path, target: Path) -> dict:
    metadata = json.loads((package / "metadata.json").read_text(encoding="utf-8"))
    animation = json.loads((package / "animation.json").read_text(encoding="utf-8"))
    keys = sorted(animation["keyframes"], key=lambda key: key["frame"])
    native, output = metadata["output"], animation["output"]
    vector_width = max(native["width"], output["width"])
    vector_height = max(native["height"], output["height"])
    x_scale = native["width"] / vector_width
    y_scale = native["height"] / vector_height
    scale_constant = output["width"] / native["width"]
    camera_keys = [{
        "frame": key["frame"],
        "center_x": key["center"]["x"],
        "center_y": key["center"]["y"],
        "view_width": key["view_width"],
        "easing": key.get("easing", "smooth"),
    } for key in keys]
    controller = f'''\t\tVector_CameraCenterX = {_curve(camera_keys, "center_x", (255, 0, 0))},
\t\tVector_CameraCenterY = {_curve(camera_keys, "center_y", (0, 255, 0))},
\t\tVector_CameraViewWidth = {_curve(camera_keys, "view_width", (0, 128, 255))},
\t\tVector_AnimationPath = XYPath {{
\t\t\tInputs = {{
\t\t\t\tX = Input {{ Expression = "(0.5 - Vector_CameraCenterX.Value) * ({scale_constant:.12g} / Vector_CameraViewWidth.Value) * {x_scale:.12g}", }},
\t\t\t\tY = Input {{ Expression = "(Vector_CameraCenterY.Value - 0.5) * ({scale_constant:.12g} / Vector_CameraViewWidth.Value) * {y_scale:.12g}", }},
\t\t\t}},
\t\t}},'''
    original = source.read_text(encoding="utf-8")
    result = _replace_vector_controller(original, controller)
    target.write_text(result, encoding="utf-8")
    return {
        "source": str(source), "target": str(target),
        "authored_camera_poses": len(camera_keys),
        "controller_curve_keys": len(camera_keys) * 3,
        "polygon_center_keyframes": 0,
        "movement": "XYPath expressions from center X, center Y and view width",
        "scale_constant": scale_constant,
        "vector_scale": {"x": x_scale, "y": y_scale},
        "note": "Resolve must validate expression references and visual alignment.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    package, source = args.package.resolve(), args.source.resolve()
    target = (args.output or source.with_name(source.stem + "_expression_camera.comp")).resolve()
    if target == source:
        raise SystemExit("Output must differ from source")
    report = build(package, source, target)
    target.with_suffix(".report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
