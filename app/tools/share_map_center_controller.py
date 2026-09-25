#!/usr/bin/env python3
"""Drive every polygon Center from the existing raster Map_AnimationPath."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from tools.share_polygon_border import _tool_span  # noqa: E402

CENTER_LINK = re.compile(
    r'\["PolyMask(?P<index>\d+)\.Center"\] = Input '
    r'\{ SourceOp = "Vector_AnimationPath", Source = "Position", \},'
)


def build(package: Path, source: Path, target: Path) -> dict:
    metadata = json.loads((package / "metadata.json").read_text(encoding="utf-8"))
    animation = json.loads((package / "animation.json").read_text(encoding="utf-8"))
    native, output = metadata["output"], animation["output"]
    vector_width = max(native["width"], output["width"])
    vector_height = max(native["height"], output["height"])
    x_scale = native["width"] / vector_width
    y_scale = native["height"] / vector_height
    expression = (
        f'Point(0.5 + (Map_AnimationPath.Position.X - 0.5) * {x_scale:.12g}, '
        f'0.5 + (Map_AnimationPath.Position.Y - 0.5) * {y_scale:.12g})'
    )
    original = source.read_text(encoding="utf-8")
    result, count = CENTER_LINK.subn(
        lambda match: f'["PolyMask{match.group("index")}.Center"] = Input '
                      f'{{ Expression = "{expression}", }},',
        original,
    )
    if not count:
        raise ValueError("No polygon Center links to Vector_AnimationPath were found")
    for name in ("Vector_AnimationDisplacement", "Vector_AnimationPath"):
        start, end = _tool_span(result, name)
        result = result[:start] + result[end:]
    if "Vector_AnimationPath" in result or "Vector_AnimationDisplacement" in result:
        raise ValueError("The separate vector movement controller was not fully removed")
    target.write_text(result, encoding="utf-8")
    map_start, map_end = _tool_span(result, "Map_AnimationDisplacement")
    map_keys = len(re.findall(r"^\s*\[\d+\] = \{", result[map_start:map_end], re.MULTILINE))
    return {
        "source": str(source), "target": str(target),
        "polygon_centers_converted": count,
        "polygon_center_keyframes": 0,
        "separate_vector_controller": False,
        "shared_map_displacement_keys": map_keys,
        "vector_canvas_scale": {"x": x_scale, "y": y_scale},
        "center_expression": expression,
        "note": "Resolve must validate the Point expression and visual alignment.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    package, source = args.package.resolve(), args.source.resolve()
    target = (args.output or source.with_name(source.stem + "_shared_map_center.comp")).resolve()
    if target == source:
        raise SystemExit("Output must differ from source")
    report = build(package, source, target)
    target.with_suffix(".report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
