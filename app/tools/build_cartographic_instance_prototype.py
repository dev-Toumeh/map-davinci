#!/usr/bin/env python3
"""Build a lightweight cartographic Fusion prototype with instanced borders."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core import package_layout  # noqa: E402
from fusion.generator import _camera_samples  # noqa: E402
from tools.reduce_fusion_points import POINT, _format_points, _reduce_ring  # noqa: E402
from tools.share_polygon_border import _tool_span  # noqa: E402

DEFAULT_LIMITS = {
    "country_usa": 20,
    "us_original_1783": 20,
    "louisiana_purchase_1803": 10,
    "florida_cession_1819": 15,
    "texas_annexation_1845": 5,
    "oregon_territory_1846": 5,
    "mexican_cession_1848": 5,
    "hawaii_annexation_1898": 10,
    "alaska_purchase_1867": 40,
}

RING = re.compile(
    r'\["PolyMask(?P<index>\d+)\.Level"\] = Input \{ Value = (?P<level>-?\d+), \},.*?'
    r'\["PolyMask(?P=index)\.Polyline"\] = Input \{ Value = Polyline '
    r'\{ Closed = true, Points = \{ (?P<points>.*?) \} \}, \}',
    re.DOTALL,
)


def _area(points: list[tuple[float, float]]) -> float:
    return abs(sum(
        points[index][0] * points[(index + 1) % len(points)][1] -
        points[(index + 1) % len(points)][0] * points[index][1]
        for index in range(len(points))
    ) / 2)


def _mask_position(block: str) -> tuple[str, str]:
    match = re.search(r"ViewInfo = OperatorInfo \{ Pos = \{ ([^,]+), ([^}]+) \}", block)
    return match.groups() if match else ("0", "0")


def _mask_dimensions(block: str) -> tuple[int, int]:
    width = re.search(r"MaskWidth = Input \{ Value = (\d+)", block)
    height = re.search(r"MaskHeight = Input \{ Value = (\d+)", block)
    if not width or not height:
        raise ValueError("Mask dimensions are missing")
    return int(width.group(1)), int(height.group(1))


def _fill_mask(name: str, rings: list[tuple[int, list[tuple[float, float]]]],
               width: int, height: int, position: tuple[str, str]) -> str:
    inputs, definitions = [], []
    for index, (level, points) in enumerate(rings, 1):
        inputs.append(f'''\t\t\t\t["PolyMask{index}.Level"] = Input {{ Value = {level}, }},
\t\t\t\t["PolyMask{index}.Filter"] = Input {{ Value = FuID {{ "Fast Gaussian" }}, }},
\t\t\t\t["PolyMask{index}.Center"] = Input {{ SourceOp = "Vector_AnimationPath", Source = "Position", }},
\t\t\t\t["PolyMask{index}.Size"] = Input {{ SourceOp = "Map_AnimationSize", Source = "Value", }},
\t\t\t\t["PolyMask{index}.Polyline"] = Input {{ Value = Polyline {{ Closed = true, Points = {{ {_format_points(points)} }} }}, }},
\t\t\t\t["PolyMask{index}.Polyline2"] = Input {{ Value = Polyline {{ }}, Disabled = true, }},''')
        definitions.append(
            f'\t\t\tPolyMask{index} = PolyMaskInputs {{ DrawMode = "InsertAndModify", '
            f'DrawMode2 = "InsertAndModify" }},'
        )
    order = ", ".join(str(index) for index in range(1, len(rings) + 1))
    return f'''\t\t{name} = MultiPoly {{
\t\t\tNameSet = true,
\t\t\tInputs = {{
\t\t\t\tMaskWidth = Input {{ Value = {width}, }}, MaskHeight = Input {{ Value = {height}, }},
\t\t\t\tPixelAspect = Input {{ Value = {{ 1, 1 }}, }}, UseFrameFormatSettings = Input {{ Value = 0, }},
\t\t\t\tClippingMode = Input {{ Value = FuID {{ "None" }}, }},
\t\t\t\tPolyOrder = Input {{ Value = ScriptVal {{ {{ [0] = {order} }} }}, }},
{chr(10).join(inputs)}
\t\t\t}},
{chr(10).join(definitions)}
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ {position[0]}, {position[1]} }} }},
\t\t}},'''


def _border_instance(name: str, source: str, ring_count: int,
                     position: tuple[str, str]) -> str:
    inputs, definitions = [], []
    for index in range(1, ring_count + 1):
        inputs.append(f'''\t\t\t\t["PolyMask{index}.Solid"] = Input {{ Value = 0, }},
\t\t\t\t["PolyMask{index}.BorderWidth"] = Input {{ SourceOp = "Map_CountryBorderWidth", Source = "Value", }},''')
        definitions.append(
            f'\t\t\tPolyMask{index} = PolyMaskInputs {{ DrawMode = "InsertAndModify", '
            f'DrawMode2 = "InsertAndModify" }},'
        )
    return f'''\t\t{name} = MultiPoly {{
\t\t\tNameSet = true,
\t\t\tSourceOp = "{source}",
\t\t\tInputs = {{
{chr(10).join(inputs)}
\t\t\t}},
{chr(10).join(definitions)}
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ {position[0]}, {position[1]} }} }},
\t\t}},'''


def _camera_tolerance(package: Path, pixels: float) -> tuple[float, float, int]:
    metadata = json.loads(package_layout.metadata_path(package).read_text(encoding="utf-8"))
    animation = json.loads(package_layout.animation_path(package).read_text(encoding="utf-8"))
    maximum = max(sample["zoom"] for sample in _camera_samples(animation, metadata["output"]))
    canvas = max(metadata["output"]["width"], metadata["output"]["height"],
                 animation["output"]["width"], animation["output"]["height"])
    return pixels / (canvas * maximum), maximum, canvas


def build(package: Path, source: Path, target: Path, tolerance_px: float) -> dict:
    original = source.read_text(encoding="utf-8")
    tolerance, maximum_size, canvas = _camera_tolerance(package, tolerance_px)
    fill_names = re.findall(r"^\t\t([A-Za-z0-9_]+_Fill_Mask) = MultiPoly \{", original, re.MULTILINE)
    replacements = []
    territories = []
    total_source_rings = total_target_rings = total_source_points = total_target_points = 0

    for fill_name in fill_names:
        identifier = fill_name.removeprefix("Country_USA_Region_").removesuffix("_Fill_Mask")
        if identifier not in DEFAULT_LIMITS:
            continue
        fill_start, fill_end = _tool_span(original, fill_name)
        fill_block = original[fill_start:fill_end]
        parsed = []
        for match in RING.finditer(fill_block):
            points = [(float(point.group("x")), float(point.group("y")))
                      for point in POINT.finditer(match.group("points"))]
            if len(points) >= 3:
                parsed.append((int(match.group("level")), points))
        if not parsed:
            raise ValueError(f"No rings parsed from {fill_name}")
        limit = DEFAULT_LIMITS[identifier]
        kept = sorted(parsed, key=lambda item: _area(item[1]), reverse=True)[:limit]
        reduced = [(level, _reduce_ring(points, tolerance)) for level, points in kept]
        width, height = _mask_dimensions(fill_block)
        replacements.append((fill_start, fill_end,
                             _fill_mask(fill_name, reduced, width, height, _mask_position(fill_block))))

        border_name = fill_name.replace("_Fill_Mask", "_Border_Mask")
        border_start, border_end = _tool_span(original, border_name)
        border_block = original[border_start:border_end]
        replacements.append((border_start, border_end,
                             _border_instance(border_name, fill_name, len(reduced),
                                              _mask_position(border_block))))
        source_points = sum(len(points) for _, points in parsed)
        target_points = sum(len(points) for _, points in reduced)
        territories.append({
            "id": identifier,
            "source_rings": len(parsed), "target_rings": len(reduced),
            "source_points": source_points, "target_points": target_points,
        })
        total_source_rings += len(parsed)
        total_target_rings += len(reduced)
        total_source_points += source_points
        total_target_points += target_points

    if len(territories) != len(DEFAULT_LIMITS):
        raise ValueError(f"Expected {len(DEFAULT_LIMITS)} territories, converted {len(territories)}")
    result = original
    for start, end, replacement in sorted(replacements, reverse=True):
        result = result[:start] + replacement + result[end:]
    target.write_text(result, encoding="utf-8")
    return {
        "source": str(source), "target": str(target),
        "source_bytes": len(original.encode("utf-8")),
        "target_bytes": len(result.encode("utf-8")),
        "size_reduction_percent": round(100 * (len(original) - len(result)) / len(original), 2),
        "source_rings": total_source_rings, "target_rings": total_target_rings,
        "ring_reduction_percent": round(100 * (total_source_rings - total_target_rings) / total_source_rings, 2),
        "source_polygon_points": total_source_points, "target_polygon_points": total_target_points,
        "point_reduction_percent": round(100 * (total_source_points - total_target_points) / total_source_points, 2),
        "border_instances": len(territories),
        "requested_maximum_error_px": tolerance_px,
        "normalized_tolerance": tolerance,
        "maximum_camera_size": maximum_size,
        "vector_canvas_size": canvas,
        "territories": territories,
        "note": "Cartographic prototype: inspect retained islands, outlines, borders, alignment and playback in Resolve.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--tolerance-px", type=float, default=4.0)
    args = parser.parse_args()
    package, source = args.package.resolve(), args.source.resolve()
    target = (args.output or source.with_name(source.stem + "_cartographic_instances.comp")).resolve()
    if target == source:
        raise SystemExit("Output must differ from source")
    report = build(package, source, target, args.tolerance_px)
    target.with_suffix(".report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
