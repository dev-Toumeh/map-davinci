#!/usr/bin/env python3
"""Add an Edit/Final Render controller to a generated country MultiMerge."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from tools.share_polygon_border import _tool_span


LAYER = re.compile(
    r'(?P<foreground>\s*\["Layer(?P<layer>\d+)\.Foreground"\] = Input '
    r'\{ SourceOp = "(?P<source>[^"]+)", Source = "Output", \},\n)'
    r'(?P<indent>\s*)LayerName(?P=layer) = Input \{ Value = "(?P<label>[^"]+)", \},'
)


def _territory_name(label: str) -> str:
    for suffix in (" fill", " border"):
        if label.lower().endswith(suffix):
            return label[: -len(suffix)]
    return label


def _controller(names: list[str], default_index: int) -> str:
    strings = "\n".join(
        f'\t\t\t\tCCS_AddString = "{name}",' for name in names
    )
    return f'''\t\tPERFORMANCE_CONTROLLER = CustomTool {{
\t\t\tNameSet = true,
\t\t\tInputs = {{
\t\t\t\tFinalRender = Input {{ Value = 0, }},
\t\t\t\tActiveTerritory = Input {{ Value = {default_index}, }},
\t\t\t}},
\t\t\tUserControls = ordered() {{
\t\t\t\tFinalRender = {{
\t\t\t\t\tLINKID_DataType = "Number",
\t\t\t\t\tINPID_InputControl = "CheckboxControl",
\t\t\t\t\tLINKS_Name = "FINAL RENDER - Enable all territories",
\t\t\t\t\tINP_Default = 0,
\t\t\t\t}},
\t\t\t\tActiveTerritory = {{
\t\t\t\t\tLINKID_DataType = "Number",
\t\t\t\t\tINPID_InputControl = "ComboControl",
\t\t\t\t\tLINKS_Name = "EDIT MODE - Active territory",
\t\t\t\t\tINP_Default = {default_index},
{strings}
\t\t\t\t}},
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ -40, 1710 }} }},
\t\t}},
'''


def build(source: Path, target: Path, merge_name: str, default_name: str) -> dict:
    text = source.read_text(encoding="utf-8")
    if "PERFORMANCE_CONTROLLER = CustomTool" in text:
        raise ValueError("Composition already contains PERFORMANCE_CONTROLLER")

    start, end = _tool_span(text, merge_name)
    block = text[start:end]
    matches = list(LAYER.finditer(block))
    if not matches:
        raise ValueError(f"No named layers found in {merge_name}")

    names: list[str] = []
    name_to_index: dict[str, int] = {}
    layer_to_index: dict[int, int] = {}
    for match in matches:
        name = _territory_name(match.group("label"))
        if name not in name_to_index:
            name_to_index[name] = len(names)
            names.append(name)
        layer_to_index[int(match.group("layer"))] = name_to_index[name]

    default_index = name_to_index.get(default_name, len(names) - 1)

    def add_enabled(match: re.Match[str]) -> str:
        layer = int(match.group("layer"))
        territory = layer_to_index[layer]
        expression = (
            "iif(PERFORMANCE_CONTROLLER.FinalRender > 0.5, 1, "
            f"iif(PERFORMANCE_CONTROLLER.ActiveTerritory == {territory}, 1, 0))"
        )
        return (
            match.group(0)
            + f'\n{match.group("indent")}LayerEnabled{layer} = Input '
              f'{{ Expression = "{expression}", }},'
        )

    controlled_block, controlled = LAYER.subn(add_enabled, block)
    if controlled != len(matches):
        raise ValueError("Not every country layer received an enable expression")

    controller = _controller(names, default_index)
    result = text[:start] + controller + controlled_block + text[end:]
    target.write_text(result, encoding="utf-8")
    return {
        "source": str(source),
        "target": str(target),
        "multi_merge": merge_name,
        "default_mode": "Edit",
        "default_active_territory": names[default_index],
        "territories": names,
        "controlled_layers": controlled,
        "final_render_control": "PERFORMANCE_CONTROLLER.FinalRender",
        "edit_selection_control": "PERFORMANCE_CONTROLLER.ActiveTerritory",
        "note": "Resolve must confirm that disabled MultiMerge layers prune upstream rendering.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--merge", default="Country_USA_Regions")
    parser.add_argument("--default", default="Alaska Purchase")
    args = parser.parse_args()
    source, target = args.source.resolve(), args.output.resolve()
    if source == target:
        raise SystemExit("Output must differ from source")
    report = build(source, target, args.merge, args.default)
    target.with_suffix(".report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
