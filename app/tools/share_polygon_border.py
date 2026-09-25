#!/usr/bin/env python3
"""Replace duplicated Fusion border masks with image-space generated borders.

For each exported region this keeps the solid fill MultiPoly as the single
geometry source. A white image using that mask is expanded with ErodeDilate
and placed behind the colored fill. The source composition is never changed.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def _tool_span(content: str, name: str) -> tuple[int, int]:
    marker = f"\t\t{name} = "
    start = content.find(marker)
    if start < 0:
        raise ValueError(f"Could not find tool {name}")
    brace = content.find("{", start + len(marker))
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


def _remove_tools(content: str, names: list[str]) -> str:
    spans = sorted((_tool_span(content, name) for name in names), reverse=True)
    for start, end in spans:
        content = content[:start] + content[end:]
    return content


def _replace_border_background(content: str, base: str, amount: float) -> str:
    name = f"{base}_Border"
    start, end = _tool_span(content, name)
    block = content[start:end]
    old_mask = f'SourceOp = "{base}_Border_Mask"'
    if old_mask not in block:
        raise ValueError(f"{name} does not use its expected border mask")
    matte = block.replace(f"\t\t{name} = Background", f"\t\t{name}Matte = Background", 1)
    matte = matte.replace(old_mask, f'SourceOp = "{base}_Fill_Mask"', 1)
    grow = f'''
\t\t{name} = ErodeDilate {{
\t\t\tNameSet = true,
\t\t\tInputs = {{
\t\t\t\tXAmount = Input {{ Value = {amount:.12g}, }},
\t\t\t\tYAmount = Input {{ Value = {amount:.12g}, }},
\t\t\t\tInput = Input {{ SourceOp = "{name}Matte", Source = "Output", }},
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ -180, 0 }} }},
\t\t}},'''
    return content[:start] + matte + grow + content[end:]


def _put_border_behind_fill(content: str, base: str) -> str:
    fill_pattern = re.compile(
        rf'(?P<indent>\s*)\["Layer(?P<fill_layer>\d+)\.Foreground"\] = Input '
        rf'\{{ SourceOp = "{re.escape(base)}_Fill", Source = "Output", \}},\s*'
        rf'LayerName(?P=fill_layer) = Input \{{ Value = "(?P<label>[^"]+) fill", \}},\s*'
        rf'\["Layer(?P<border_layer>\d+)\.Foreground"\] = Input '
        rf'\{{ SourceOp = "{re.escape(base)}_Border", Source = "Output", \}},\s*'
        rf'LayerName(?P=border_layer) = Input \{{ Value = "(?P=label) border", \}},'
    )
    match = fill_pattern.search(content)
    if not match:
        raise ValueError(f"Could not find adjacent fill/border layers for {base}")
    indent = match.group("indent")
    fill_layer = match.group("fill_layer")
    border_layer = match.group("border_layer")
    label = match.group("label")
    replacement = (
        f'{indent}["Layer{fill_layer}.Foreground"] = Input {{ SourceOp = "{base}_Border", Source = "Output", }},\n'
        f'{indent}LayerName{fill_layer} = Input {{ Value = "{label} generated border", }},\n'
        f'{indent}["Layer{border_layer}.Foreground"] = Input {{ SourceOp = "{base}_Fill", Source = "Output", }},\n'
        f'{indent}LayerName{border_layer} = Input {{ Value = "{label} fill", }},'
    )
    return content[:match.start()] + replacement + content[match.end():]


def build(source: Path, target: Path, amount: float) -> dict:
    original = source.read_text(encoding="utf-8")
    border_masks = re.findall(r"^\t\t([A-Za-z0-9_]+)_Border_Mask = MultiPoly \{", original, re.MULTILINE)
    if not border_masks:
        raise ValueError("No generated region border masks were found")
    result = original
    for base in border_masks:
        result = _replace_border_background(result, base, amount)
        result = _put_border_behind_fill(result, base)
    result = _remove_tools(result, [f"{base}_Border_Mask" for base in border_masks])
    if "_Border_Mask = MultiPoly" in result:
        raise ValueError("At least one duplicated border mask remains")
    target.write_text(result, encoding="utf-8")

    point_pattern = re.compile(r"Linear = true, X =")
    ring_pattern = re.compile(r'\["PolyMask\d+\.Polyline"\]')
    return {
        "source": str(source),
        "target": str(target),
        "territories_converted": len(border_masks),
        "border_grow_amount": amount,
        "source_bytes": len(original.encode("utf-8")),
        "target_bytes": len(result.encode("utf-8")),
        "size_reduction_percent": round(100 * (len(original) - len(result)) / len(original), 2),
        "source_points": len(point_pattern.findall(original)),
        "target_points": len(point_pattern.findall(result)),
        "source_rings": len(ring_pattern.findall(original)),
        "target_rings": len(ring_pattern.findall(result)),
        "remaining_multipoly_nodes": len(re.findall(r"= MultiPoly \{", result)),
        "generated_border_nodes": len(re.findall(r"_Border = ErodeDilate \{", result)),
        "note": "Border is generated behind the fill; verify thickness and playback in Resolve.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--amount", type=float, default=0.001)
    args = parser.parse_args()
    source = args.source.resolve()
    target = (args.output or source.with_name(source.stem + "_shared_border.comp")).resolve()
    if source == target:
        raise SystemExit("Output must differ from source")
    report = build(source, target, args.amount)
    target.with_suffix(".report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
