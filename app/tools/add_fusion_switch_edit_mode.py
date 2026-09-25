#!/usr/bin/env python3
"""Add native Fusion Switch nodes for lightweight territory editing."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from tools.share_polygon_border import _tool_span


LAYER = re.compile(
    r'\["Layer(?P<layer>\d+)\.Foreground"\] = Input '
    r'\{ SourceOp = "(?P<source>[^"]+)", Source = "Output", \},\s*\n'
    r'\s*LayerName(?P=layer) = Input \{ Value = "(?P<label>[^"]+)", \},'
)


def _territory_name(label: str) -> str:
    for suffix in (" fill", " border"):
        if label.lower().endswith(suffix):
            return label[: -len(suffix)]
    return label


def _safe_name(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_")
    return value or "Territory"


def _switch(name: str, inputs: list[tuple[str, str]], x: int, y: int) -> str:
    lines = [
        f"\t\t{name} = Switch {{",
        "\t\t\tNameSet = true,",
        "\t\t\tInputs = {",
        f"\t\t\t\tNumberOfInputs = Input {{ Value = {len(inputs)}, }},",
    ]
    for index, (label, source) in enumerate(inputs, 1):
        lines.extend([
            f'\t\t\t\tInput{index} = Input {{ SourceOp = "{source}", Source = "Output", }},',
            f'\t\t\t\tName{index} = Input {{ Value = "{label}", }},',
        ])
    lines.extend([
        "\t\t\t},",
        f"\t\t\tViewInfo = OperatorInfo {{ Pos = {{ {x}, {y} }} }},",
        "\t\t},",
    ])
    return "\n".join(lines) + "\n"


def build(source: Path, target: Path, merge_name: str, gate_name: str, default_name: str) -> dict:
    text = source.read_text(encoding="utf-8")
    for name in ("EDIT_TERRITORY_SWITCH", "EDIT_FINAL_SWITCH"):
        if f"{name} = Switch" in text:
            raise ValueError(f"Composition already contains {name}")

    merge_start, merge_end = _tool_span(text, merge_name)
    merge_block = text[merge_start:merge_end]
    pairs: dict[str, dict[str, str]] = {}
    order: list[str] = []
    for match in LAYER.finditer(merge_block):
        label = match.group("label")
        territory = _territory_name(label)
        if territory not in pairs:
            pairs[territory] = {}
            order.append(territory)
        kind = "border" if label.lower().endswith(" border") else "fill"
        pairs[territory][kind] = match.group("source")
    incomplete = [name for name, pair in pairs.items() if set(pair) != {"fill", "border"}]
    if not pairs or incomplete:
        raise ValueError(f"Incomplete territory fill/border pairs: {incomplete}")

    if default_name in order:
        order.remove(default_name)
        order.insert(0, default_name)

    tools: list[str] = []
    switch_inputs: list[tuple[str, str]] = []
    for index, territory in enumerate(order):
        pair = pairs[territory]
        composite = f"EDIT_{_safe_name(territory)}_Composite"
        switch_inputs.append((territory, composite))
        tools.append(f'''\t\t{composite} = MultiMerge {{
\t\t\tNameSet = true,
\t\t\tInputs = {{
\t\t\t\tBackground = Input {{ SourceOp = "Country_USA_Canvas", Source = "Output", }},
\t\t\t\t["Layer1.Foreground"] = Input {{ SourceOp = "{pair['fill']}", Source = "Output", }},
\t\t\t\tLayerName1 = Input {{ Value = "{territory} fill", }},
\t\t\t\t["Layer2.Foreground"] = Input {{ SourceOp = "{pair['border']}", Source = "Output", }},
\t\t\t\tLayerName2 = Input {{ Value = "{territory} border", }},
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ -40, {1710 + index * 65} }} }},
\t\t}},
''')
    tools.append(_switch("EDIT_TERRITORY_SWITCH", switch_inputs, 180, 1710))
    tools.append(_switch(
        "EDIT_FINAL_SWITCH",
        [("EDIT MODE - selected territory", "EDIT_TERRITORY_SWITCH"),
         ("FINAL RENDER - all territories", merge_name)],
        400,
        1710,
    ))

    insertion = "".join(tools)
    result = text[:merge_end] + insertion + text[merge_end:]
    gate_start, gate_end = _tool_span(result, gate_name)
    gate_block = result[gate_start:gate_end]
    old = f'Foreground = Input {{ SourceOp = "{merge_name}", Source = "Output", }}'
    new = 'Foreground = Input { SourceOp = "EDIT_FINAL_SWITCH", Source = "Output", }'
    if gate_block.count(old) != 1:
        raise ValueError(f"Could not find the {merge_name} foreground in {gate_name}")
    gate_block = gate_block.replace(old, new, 1)
    result = result[:gate_start] + gate_block + result[gate_end:]
    target.write_text(result, encoding="utf-8")
    return {
        "source": str(source),
        "target": str(target),
        "edit_switch": "EDIT_TERRITORY_SWITCH",
        "final_switch": "EDIT_FINAL_SWITCH",
        "default_edit_territory": order[0],
        "territories": order,
        "territory_composites": len(order),
        "instructions": {
            "edit": "On EDIT_FINAL_SWITCH choose EDIT MODE, then choose a territory on EDIT_TERRITORY_SWITCH.",
            "render": "On EDIT_FINAL_SWITCH choose FINAL RENDER.",
        },
        "note": "Resolve must validate Switch serialization and upstream pruning.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--merge", default="Country_USA_Regions")
    parser.add_argument("--gate", default="Country_USA_Gate")
    parser.add_argument("--default", default="Alaska Purchase")
    args = parser.parse_args()
    source, target = args.source.resolve(), args.output.resolve()
    if source == target:
        raise SystemExit("Output must differ from source")
    report = build(source, target, args.merge, args.gate, args.default)
    target.with_suffix(".report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
