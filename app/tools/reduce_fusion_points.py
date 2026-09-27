#!/usr/bin/env python3
"""Apply Fusion-style point reduction to every MultiPoly ring in a .comp."""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core import package_layout  # noqa: E402
from fusion.generator import _camera_samples  # noqa: E402

POLYLINE = re.compile(
    r'(?P<prefix>\["PolyMask\d+\.Polyline"\] = Input \{ Value = Polyline '
    r'\{ Closed = true, Points = \{ )(?P<points>.*?)(?P<suffix> \} \}, \})'
)
POINT = re.compile(
    r'\{ Linear = true, X = (?P<x>[^,]+), Y = (?P<y>[^,]+), '
    r'LX = 0, LY = 0, RX = 0, RY = 0 \},'
)


def _distance(point: tuple[float, float], start: tuple[float, float],
              end: tuple[float, float]) -> float:
    dx, dy = end[0] - start[0], end[1] - start[1]
    if dx == 0 and dy == 0:
        return math.hypot(point[0] - start[0], point[1] - start[1])
    return abs(dy * point[0] - dx * point[1] + end[0] * start[1] - end[1] * start[0]) / math.hypot(dx, dy)


def _rdp(points: list[tuple[float, float]], tolerance: float) -> list[tuple[float, float]]:
    if len(points) <= 2:
        return points
    keep = {0, len(points) - 1}
    stack = [(0, len(points) - 1)]
    while stack:
        first, last = stack.pop()
        largest, split = tolerance, None
        for index in range(first + 1, last):
            error = _distance(points[index], points[first], points[last])
            if error > largest:
                largest, split = error, index
        if split is not None:
            keep.add(split)
            stack.extend(((first, split), (split, last)))
    return [points[index] for index in sorted(keep)]


def _reduce_ring(points: list[tuple[float, float]], tolerance: float) -> list[tuple[float, float]]:
    """Reduce a closed ring as two arcs so the closing edge is also tested."""
    if len(points) <= 3:
        return points
    first = 0
    second = max(range(len(points)), key=lambda index:
                 (points[index][0] - points[first][0]) ** 2 +
                 (points[index][1] - points[first][1]) ** 2)
    first = max(range(len(points)), key=lambda index:
                (points[index][0] - points[second][0]) ** 2 +
                (points[index][1] - points[second][1]) ** 2)
    if first > second:
        first, second = second, first
    reduced = (_rdp(points[first:second + 1], tolerance)[:-1] +
               _rdp(points[second:] + points[:first + 1], tolerance)[:-1])
    return reduced if len(reduced) >= 3 else points


def _format_points(points: list[tuple[float, float]]) -> str:
    return " ".join(
        f'{{ Linear = true, X = {x:.12g}, Y = {y:.12g}, LX = 0, LY = 0, RX = 0, RY = 0 }},'
        for x, y in points
    )


def _geometry_tolerance(package: Path, tolerance_px: float) -> tuple[float, float, int]:
    metadata = json.loads(package_layout.metadata_path(package).read_text(encoding="utf-8"))
    animation = json.loads(package_layout.animation_path(package).read_text(encoding="utf-8"))
    samples = _camera_samples(animation, metadata["output"])
    maximum_size = max(sample["zoom"] for sample in samples)
    canvas = max(metadata["output"]["width"], metadata["output"]["height"],
                 animation["output"]["width"], animation["output"]["height"])
    return tolerance_px / (canvas * maximum_size), maximum_size, canvas


def build(package: Path, source: Path, target: Path, tolerance_px: float) -> dict:
    tolerance, maximum_size, canvas = _geometry_tolerance(package, tolerance_px)
    original = source.read_text(encoding="utf-8")
    before = after = rings = 0

    def replace(match: re.Match) -> str:
        nonlocal before, after, rings
        points = [(float(point.group("x")), float(point.group("y")))
                  for point in POINT.finditer(match.group("points"))]
        if len(points) < 3:
            raise ValueError("A MultiPoly ring has fewer than three points")
        reduced = _reduce_ring(points, tolerance)
        before += len(points)
        after += len(reduced)
        rings += 1
        return match.group("prefix") + _format_points(reduced) + match.group("suffix")

    result = POLYLINE.sub(replace, original)
    if not rings:
        raise ValueError("No MultiPoly rings found")
    target.write_text(result, encoding="utf-8")
    return {
        "source": str(source),
        "target": str(target),
        "rings_processed": rings,
        "source_polygon_points": before,
        "target_polygon_points": after,
        "point_reduction_percent": round(100 * (before - after) / before, 2),
        "source_bytes": len(original.encode("utf-8")),
        "target_bytes": len(result.encode("utf-8")),
        "size_reduction_percent": round(100 * (len(original) - len(result)) / len(original), 2),
        "requested_maximum_error_px": tolerance_px,
        "normalized_tolerance": tolerance,
        "maximum_camera_size": maximum_size,
        "vector_canvas_size": canvas,
        "note": "Point reduction does not remove rings; inspect coastlines and playback in Resolve.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--tolerance-px", type=float, default=0.5)
    args = parser.parse_args()
    package, source = args.package.resolve(), args.source.resolve()
    target = (args.output or source.with_name(source.stem + "_reduced_points.comp")).resolve()
    if target == source:
        raise SystemExit("Output must differ from source")
    report = build(package, source, target, args.tolerance_px)
    target.with_suffix(".report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
