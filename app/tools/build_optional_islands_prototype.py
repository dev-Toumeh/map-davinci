#!/usr/bin/env python3
"""Split one Shape territory into active and disconnected optional rings.

This is an exported-composition prototype.  It does not modify the app
generator.  Ring importance is measured relative to the largest rendered
ring.  Optional geometry remains in the comp but its sMerge is deliberately
disconnected, so Fusion does not evaluate it until the editor reconnects it.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from tools.build_sparse_vector_camera import _tool_span


def _ring_area(content: str, tool_name: str) -> float:
    start, end = _tool_span(content, tool_name)
    points = [(float(x), float(y)) for x, y in re.findall(
        r"X = ([\d.e+-]+), Y = ([\d.e+-]+)", content[start:end])]
    if len(points) < 3:
        return 0.0
    return abs(sum(
        points[index][0] * points[(index + 1) % len(points)][1] -
        points[(index + 1) % len(points)][0] * points[index][1]
        for index in range(len(points))
    ) / 2)


def _merge(name: str, territory: str, rings: list[int], pos: tuple[int, int]) -> str:
    sources = []
    for ring in rings:
        root = f"{territory}_Ring_{ring:02d}"
        sources.extend((root + "_Fill", root + "_Border"))
    inputs = "\n".join(
        f'\t\t\t\tInput{index} = Input {{ SourceOp = "{source}", Source = "Output", }},'
        for index, source in enumerate(sources, 1))
    return f'''\t\t{name} = sMerge {{
\t\t\tNameSet = true,
\t\t\tInputs = {{
{inputs}
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ {pos[0]}, {pos[1]} }} }},
\t\t}},'''


def build(source: Path, target: Path, territory: str = "GBR_Entire",
          threshold: float = 0.05) -> dict:
    content = source.read_text(encoding="utf-8")
    pattern = re.compile(rf"\t\t{re.escape(territory)}_Ring_(\d+)_Fill = sPolygon")
    ring_numbers = sorted({int(value) for value in pattern.findall(content)})
    if not ring_numbers:
        raise ValueError(f"No Shape rings found for {territory}")
    areas = {ring: _ring_area(content, f"{territory}_Ring_{ring:02d}_Fill")
             for ring in ring_numbers}
    largest = max(areas.values())
    if largest <= 0:
        raise ValueError(f"Could not measure Shape rings for {territory}")
    essential = [ring for ring in ring_numbers if areas[ring] / largest >= threshold]
    optional = [ring for ring in ring_numbers if ring not in essential]
    merge_name = territory + "_Shapes"
    start, end = _tool_span(content, merge_name)
    active_merge = _merge(merge_name, territory, essential, (-50, 6105))
    optional_merge = _merge(territory + "_Optional_Shapes", territory, optional,
                            (-50, 6780))
    result = content[:start] + active_merge + "\n" + optional_merge + content[end:]
    if optional_merge and f'SourceOp = "{territory}_Optional_Shapes"' in result:
        raise ValueError("Optional merge must remain disconnected in the prototype")
    target.write_text(result, encoding="utf-8")
    return {
        "source": str(source),
        "target": str(target),
        "territory": territory,
        "threshold_percent": threshold * 100,
        "total_rings": len(ring_numbers),
        "essential_rings": essential,
        "optional_rings": optional,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("--territory", default="GBR_Entire")
    parser.add_argument("--threshold", type=float, default=0.05)
    args = parser.parse_args()
    print(build(args.source, args.target, args.territory, args.threshold))


if __name__ == "__main__":
    main()
