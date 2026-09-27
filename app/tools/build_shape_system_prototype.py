#!/usr/bin/env python3
"""Build an isolated Fusion Shape-system country prototype.

The source composition is never modified.  One existing static MultiPoly mask
is converted to native sPolygon nodes, transformed while it is still vector
geometry, and rasterized once by sRender.  This lets the result be compared
with the current Background/Mask country pipeline inside Resolve.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from tools.build_closeup_lod_prototype import _block, _replace_source


DEFAULT_MASK = "USA_Entire_Detail_Fill_Mask"
DEFAULT_FILL = (0.235294117647, 0.23137254902, 0.43137254902, 1.0)


def _balanced(text: str, opening: int) -> tuple[int, str]:
    depth = 0
    for index in range(opening, len(text)):
        depth += (text[index] == "{") - (text[index] == "}")
        if depth == 0:
            return index + 1, text[opening:index + 1]
    raise ValueError("unterminated Fusion table")


def _polylines(mask_block: str) -> list[tuple[int, str]]:
    """Return numbered, static Polyline values from a MultiPoly node."""
    results = []
    pattern = re.compile(r'\["PolyMask(\d+)\.Polyline"\]\s*=\s*Input\s*\{')
    for match in pattern.finditer(mask_block):
        input_open = mask_block.find("{", match.start())
        input_end, input_block = _balanced(mask_block, input_open)
        value = re.search(r"Value\s*=\s*Polyline\s*\{", input_block)
        if not value:
            continue
        poly_open = input_block.find("{", value.start())
        _, polyline = _balanced(input_block, poly_open)
        if "Points" in polyline:
            results.append((int(match.group(1)), "Polyline " + polyline))
    if not results:
        raise ValueError("MultiPoly mask contains no static polygon rings")
    return sorted(results)


def _point_count(polylines: list[tuple[int, str]]) -> int:
    return sum(polyline.count("{ Linear = true") for _, polyline in polylines)


def _insert_tools(text: str, node_text: str) -> str:
    tools = re.search(r"(?m)^\s*Tools = (?:ordered\(\) )?\{", text)
    if not tools:
        raise ValueError("could not locate Fusion Tools block")
    opening = text.find("{", tools.start())
    end, _ = _balanced(text, opening)
    closing = end - 1
    prefix = text[:closing].rstrip()
    separator = "\n" if prefix.endswith(",") else ",\n"
    return prefix + separator + node_text + "\n" + text[closing:]


def _shape_nodes(polylines: list[tuple[int, str]], source_width: int,
                 source_height: int, canvas_width: int,
                 canvas_height: int, map_source: str) -> str:
    # Regular Polygon masks normalize X by the image width and Y by the image
    # height.  Fusion Shape coordinates use image width for both axes.  Apply
    # the canvas aspect correction to the Shape Y transform (including its
    # camera offset) so copied mask geometry remains geographically aligned.
    y_aspect = source_height / source_width
    nodes = []
    merge_inputs = []
    for order, (ring_number, polyline) in enumerate(polylines, 1):
        fill = f"Shape_Prototype_Ring_{ring_number:02d}_Fill"
        border = f"Shape_Prototype_Ring_{ring_number:02d}_Border"
        red, green, blue, alpha = DEFAULT_FILL
        nodes.append(f'''\t\t{fill} = sPolygon {{
\t\t\tNameSet = true,
\t\t\tInputs = {{
\t\t\t\tPolyline = Input {{ Value = {polyline}, }},
\t\t\t\tRed = Input {{ Value = {red}, }},
\t\t\t\tGreen = Input {{ Value = {green}, }},
\t\t\t\tBlue = Input {{ Value = {blue}, }},
\t\t\t\tAlpha = Input {{ Value = {alpha}, }}
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ -1650, {-360 + order * 70} }} }},
\t\t}},
\t\t{border} = sPolygon {{
\t\t\tNameSet = true,
\t\t\tSourceOp = "{fill}",
\t\t\tInputs = {{
\t\t\t\tSolid = Input {{ Value = 0, }},
\t\t\t\tBorderWidth = Input {{ Value = 0.0005, }},
\t\t\t\tRed = Input {{ Value = 1, }},
\t\t\t\tGreen = Input {{ Value = 1, }},
\t\t\t\tBlue = Input {{ Value = 1, }},
\t\t\t\tAlpha = Input {{ Value = 1, }}
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ -1420, {-360 + order * 70} }} }},
\t\t}},''')
        merge_inputs.extend((fill, border))

    inputs = "\n".join(
        f'\t\t\t\tInput{index} = Input {{ SourceOp = "{name}", Source = "Output", }},'
        for index, name in enumerate(merge_inputs, 1)
    )
    nodes.append(f'''\t\tShape_Prototype_Geometry = sMerge {{
\t\t\tNameSet = true,
\t\t\tInputs = {{
{inputs}
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ -1100, -100 }} }},
\t\t}},
\t\tShape_Prototype_Camera = sTransform {{
\t\t\tNameSet = true,
\t\t\tInputs = {{
\t\t\t\tXOffset = Input {{ Expression = "Map_Animation.Center.X - 0.5", }},
\t\t\t\tYOffset = Input {{ Expression = "(Map_Animation.Center.Y - 0.5) * {y_aspect:.12g}", }},
\t\t\t\tXSize = Input {{ Expression = "Map_Animation.Size * 0.5", }},
\t\t\t\tYSize = Input {{ Expression = "Map_Animation.Size * 0.5 * {y_aspect:.12g}", }},
\t\t\t\tInput = Input {{ SourceOp = "Shape_Prototype_Geometry", Source = "Output", }}
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ -850, -100 }} }},
\t\t}},
\t\tShape_Prototype_Render = sRender {{
\t\t\tNameSet = true,
\t\t\tInputs = {{
\t\t\t\tGlobalOut = Input {{ Value = 2272, }},
\t\t\t\tWidth = Input {{ Value = {canvas_width}, }},
\t\t\t\tHeight = Input {{ Value = {canvas_height}, }},
\t\t\t\tUseFrameFormatSettings = Input {{ Value = 0, }},
\t\t\t\tInput = Input {{ SourceOp = "Shape_Prototype_Camera", Source = "Output", }}
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ -600, -100 }} }},
\t\t}},
\t\tShape_Prototype_Canvas = Background {{
\t\t\tNameSet = true,
\t\t\tInputs = {{
\t\t\t\tGlobalOut = Input {{ Value = 2272, }},
\t\t\t\tWidth = Input {{ Value = {canvas_width}, }},
\t\t\t\tHeight = Input {{ Value = {canvas_height}, }},
\t\t\t\tUseFrameFormatSettings = Input {{ Value = 0, }},
\t\t\t\tTopLeftAlpha = Input {{ Value = 0, }}
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ 2050, -300 }} }},
\t\t}},
\t\tShape_Prototype_Map_Canvas = Merge {{
\t\t\tNameSet = true,
\t\t\tInputs = {{
\t\t\t\tBackground = Input {{ SourceOp = "Shape_Prototype_Canvas", Source = "Output", }},
\t\t\t\tForeground = Input {{ SourceOp = "{map_source}", Source = "Output", }}
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ 2200, -230 }} }},
\t\t}},
\t\tShape_Prototype_Composite = Merge {{
\t\t\tNameSet = true,
\t\t\tInputs = {{
\t\t\t\tBackground = Input {{ SourceOp = "Shape_Prototype_Map_Canvas", Source = "Output", }},
\t\t\t\tForeground = Input {{ SourceOp = "Shape_Prototype_Render", Source = "Output", }}
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ 2310, -180 }} }},
\t\t}},''')
    return "\n".join(nodes)


def build(composition: Path, output: Path, mask: str = DEFAULT_MASK,
          width: int = 3840, height: int = 2160,
          canvas_width: int | None = None,
          canvas_height: int | None = None) -> tuple[Path, int, int]:
    text = composition.read_text(encoding="utf-8")
    if "Shape_Prototype_Render" in text:
        raise ValueError("composition already contains the Shape prototype")
    _, _, mask_block = _block(text, mask, "MultiPoly")
    polylines = _polylines(mask_block)

    # Remove the existing rasterized country branch only in this copy. A
    # close-up-image prototype may already have performed this rewire.
    _, _, map_animation = _block(text, "Map_Animation", "Transform")
    if 'SourceOp = "Map_Country_Layers"' in map_animation:
        text = _replace_source(
            text, "Map_Animation", "Transform",
            "Map_Country_Layers", "Map_Raster_Layers",
        )
    elif 'SourceOp = "Map_Raster_Layers"' not in map_animation:
        raise ValueError("Map_Animation has an unsupported input branch")

    # Preserve adaptive close-up imagery if the source composition has it,
    # while bypassing its old post-map raster country composite.
    map_source = ("Map_LOD_Composite"
                  if "Map_LOD_Composite = Merge" in text
                  else "Map_Animation")
    _, _, final = _block(text, "Final_Composite", "Merge")
    final_sources = re.findall(r'SourceOp = "([^"]+)"', final)
    foreground = final_sources[-1] if final_sources else "Map_Animation"
    text = _replace_source(
        text, "Final_Composite", "Merge",
        foreground, "Shape_Prototype_Composite",
    )
    # A square working canvas preserves transformed vector content outside the
    # landscape source image.  Final_Composite crops this safely to the actual
    # portrait output instead of sRender cutting the territory prematurely.
    canvas_width = canvas_width or max(width, height)
    canvas_height = canvas_height or max(width, height)
    text = _insert_tools(
        text,
        _shape_nodes(
            polylines, width, height, canvas_width, canvas_height, map_source,
        ),
    )
    output.write_text(text, encoding="utf-8")
    return output, len(polylines), _point_count(polylines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("composition", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mask", default=DEFAULT_MASK)
    parser.add_argument("--width", type=int, default=3840)
    parser.add_argument("--height", type=int, default=2160)
    parser.add_argument("--canvas-width", type=int)
    parser.add_argument("--canvas-height", type=int)
    args = parser.parse_args()
    output, rings, points = build(
        args.composition.resolve(), args.output.resolve(), args.mask,
        args.width, args.height, args.canvas_width, args.canvas_height,
    )
    print(f"composition: {output}")
    print(f"shape rings: {rings}")
    print(f"geographic points stored once: {points}")


if __name__ == "__main__":
    main()
