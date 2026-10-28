"""Add an editable neon border highlight stack to an exported Fusion comp."""
from __future__ import annotations

import argparse
import re
from pathlib import Path


NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"

# Positions saved by Resolve in the user's Egypt reference composition.
REFERENCE_HIGHLIGHT_POSITIONS = {
    "Path": (1220, 810),
    "Core": (1380, 810),
    "Transparent": (1269.3, 881.071),
    "Inner_Glow": (1532.17, 756.187),
    "Outer_Glow": (1530, 900),
    "Outer_Merge": (1680, 900),
    "Inner_Merge": (1810, 850),
    "Layers": (1940, 800),
    "Merge": (1938.32, 755.066),
}


def _tool_block(content: str, name: str) -> str:
    marker = re.search(rf"(?m)^\s*{re.escape(name)}\s*=\s*\w+\s*\{{", content)
    if not marker:
        raise ValueError(f"Fusion tool {name} was not found")
    start = marker.start()
    opening = content.find("{", marker.start())
    depth = 0
    quoted = False
    escaped = False
    for index in range(opening, len(content)):
        character = content[index]
        if quoted:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                quoted = False
            continue
        if character == '"':
            quoted = True
        elif character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                end = index + 1
                if end < len(content) and content[end] == ",":
                    end += 1
                return content[start:end]
    raise ValueError(f"Fusion tool {name} has an unclosed block")


def _value(block: str, input_name: str) -> float:
    match = re.search(
        rf"\b{re.escape(input_name)}\s*=\s*Input\s*\{{\s*Value\s*=\s*({NUMBER})",
        block,
    )
    if not match:
        raise ValueError(f"Input {input_name} was not found")
    return float(match.group(1))


def _main_ring_points(content: str, country_prefix: str) -> list[tuple[float, float]]:
    block = _tool_block(content, f"{country_prefix}_Entire_Ring_01_Fill")
    points = [(float(x), float(y)) for x, y in re.findall(
        rf"\bX\s*=\s*({NUMBER}),\s*Y\s*=\s*({NUMBER})", block)]
    if len(points) < 3:
        raise ValueError(f"{country_prefix} main border has too few points")
    return points


def _local_points(content: str, country_prefix: str,
                  width: int, height: int) -> list[tuple[float, float]]:
    transform = _tool_block(content, f"{country_prefix}_Flag_Border_Local")
    x_offset = _value(transform, "XOffset")
    y_offset = _value(transform, "YOffset")
    x_size = _value(transform, "XSize")
    y_size = _value(transform, "YSize")
    # Fusion's Shape tools express both axes in width-relative units. A
    # PolylineMask uses its own image height for Y, so preserve the rendered
    # pixel position by applying the local canvas aspect ratio.
    y_aspect = width / height
    return [(x * x_size + x_offset, (y * y_size + y_offset) * y_aspect)
            for x, y in _main_ring_points(content, country_prefix)]


def _nodes(country_prefix: str, points: list[tuple[float, float]],
           duration: int, width: int, height: int,
           mode_name: str | None = None, row: int = 360,
           overlay_only: bool = False) -> str:
    mode_name = mode_name or f"{country_prefix}_Enabled"
    point_text = ", ".join(
        f"{{ Linear = true, X = {x:.12g}, Y = {y:.12g}, LX = 0, LY = 0, RX = 0, RY = 0 }}"
        for x, y in points)
    # Resolve can bind duplicate child IDs across different groups on import.
    # Keep every ID globally unique, without the redundant Highlight label.
    path = f"{country_prefix}_Path"
    core = f"{country_prefix}_Core"
    transparent = f"{country_prefix}_Transparent"
    inner = f"{country_prefix}_Inner_Glow"
    outer = f"{country_prefix}_Outer_Glow"
    outer_merge = f"{country_prefix}_Outer_Merge"
    inner_merge = f"{country_prefix}_Inner_Merge"
    layers = f"{country_prefix}_Layers"
    final = f"{country_prefix}_Merge"
    # App exports use an independent RGBA overlay, not a country passthrough.
    # It can feed a Local MultiMerge foreground without creating a cycle.
    background = transparent if overlay_only else mode_name
    inner = f'''\t\t{path} = PolylineMask {{
\t\t\tNameSet = true,
\t\t\tInputs = {{
\t\t\t\tFilter = Input {{ Value = FuID {{ "Fast Gaussian" }}, }},
\t\t\t\tBorderWidth = Input {{ Value = 0.004, }},
\t\t\t\tSolid = Input {{ Value = 0, }},
\t\t\t\tWritePosition = Input {{ Value = 0, }},
\t\t\t\tWriteLength = Input {{ Value = 0.25, }},
\t\t\t\tMaskWidth = Input {{ Value = {width}, }},
\t\t\t\tMaskHeight = Input {{ Value = {height}, }},
\t\t\t\tPixelAspect = Input {{ Value = {{ 1, 1 }}, }},
\t\t\t\tUseFrameFormatSettings = Input {{ Value = 0, }},
\t\t\t\tClippingMode = Input {{ Value = FuID {{ "None" }}, }},
\t\t\t\tPolyline = Input {{ Value = Polyline {{ Closed = true, Points = {{ {point_text} }} }}, }},
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ 1220, 810 }} }},
\t\t}},
\t\t{core} = Background {{ NameSet = true, Inputs = {{
\t\t\t\tGlobalOut = Input {{ Value = {duration}, }}, Width = Input {{ Value = {width}, }}, Height = Input {{ Value = {height}, }}, UseFrameFormatSettings = Input {{ Value = 0, }},
\t\t\t\tTopLeftRed = Input {{ Value = 0, }}, TopLeftGreen = Input {{ Value = 0.85, }}, TopLeftBlue = Input {{ Value = 1, }},
\t\t\t\tEffectMask = Input {{ SourceOp = "{path}", Source = "Mask", }}
\t\t\t}}, ViewInfo = OperatorInfo {{ Pos = {{ 1380, 810 }} }}, }},
\t\t{transparent} = Background {{ NameSet = true, Inputs = {{ GlobalOut = Input {{ Value = {duration}, }}, Width = Input {{ Value = {width}, }}, Height = Input {{ Value = {height}, }}, UseFrameFormatSettings = Input {{ Value = 0, }}, TopLeftAlpha = Input {{ Value = 0, }} }}, ViewInfo = OperatorInfo {{ Pos = {{ 1380, 960 }} }}, }},
\t\t{inner} = Glow {{ NameSet = true, Inputs = {{ Blend = Input {{ Value = 0.55, }}, Filter = Input {{ Value = FuID {{ "Fast Gaussian" }}, }}, XGlowSize = Input {{ Value = 7, }}, Glow = Input {{ Value = 0.85, }}, ColorScale = Input {{ Value = 1, }}, Input = Input {{ SourceOp = "{core}", Source = "Output", }} }}, ViewInfo = OperatorInfo {{ Pos = {{ 1530, 770 }} }}, }},
\t\t{outer} = Glow {{ NameSet = true, Inputs = {{ Blend = Input {{ Value = 0.3, }}, Filter = Input {{ Value = FuID {{ "Fast Gaussian" }}, }}, XGlowSize = Input {{ Value = 22, }}, Glow = Input {{ Value = 0.85, }}, ColorScale = Input {{ Value = 1, }}, Input = Input {{ SourceOp = "{core}", Source = "Output", }} }}, ViewInfo = OperatorInfo {{ Pos = {{ 1530, 900 }} }}, }},
\t\t{outer_merge} = Merge {{ NameSet = true, Inputs = {{ Background = Input {{ SourceOp = "{transparent}", Source = "Output", }}, Foreground = Input {{ SourceOp = "{outer}", Source = "Output", }} }}, ViewInfo = OperatorInfo {{ Pos = {{ 1680, 900 }} }}, }},
\t\t{inner_merge} = Merge {{ NameSet = true, Inputs = {{ Background = Input {{ SourceOp = "{outer_merge}", Source = "Output", }}, Foreground = Input {{ SourceOp = "{inner}", Source = "Output", }} }}, ViewInfo = OperatorInfo {{ Pos = {{ 1810, 850 }} }}, }},
\t\t{layers} = Merge {{ NameSet = true, Inputs = {{ Background = Input {{ SourceOp = "{inner_merge}", Source = "Output", }}, Foreground = Input {{ SourceOp = "{core}", Source = "Output", }} }}, ViewInfo = OperatorInfo {{ Pos = {{ 1940, 800 }} }}, }},
\t\t{final} = Merge {{ NameSet = true, Inputs = {{ Background = Input {{ SourceOp = "{background}", Source = "Output", }}, Foreground = Input {{ SourceOp = "{layers}", Source = "Output", }}, Blend = Input {{ Value = 0, }} }}, ViewInfo = OperatorInfo {{ Pos = {{ 1940, 700 }} }}, }},
'''
    for suffix, (x, y) in REFERENCE_HIGHLIGHT_POSITIONS.items():
        node = f"{country_prefix}_{suffix}"
        y += row - 360
        pattern = (rf"({re.escape(node)} = \w+ \{{.*?"
                   rf"ViewInfo = OperatorInfo \{{ Pos = \{{ )[^}}]+( \}} \}})")
        inner, count = re.subn(
            pattern,
            lambda match: f"{match.group(1)}{x}, {y}{match.group(2)}",
            inner,
            count=1,
            flags=re.S,
        )
        if count != 1:
            raise ValueError(f"position was not found for {node}")
    inner_tools = "\n".join("\t" + line for line in inner.splitlines())
    return f'''\t\t{country_prefix}_Border_Highlight_Group = GroupOperator {{
\t\t\tNameSet = true,
\t\t\tOutputs = {{
\t\t\t\tMainOutput1 = InstanceOutput {{
\t\t\t\t\tSourceOp = "{final}",
\t\t\t\t\tSource = "Output",
\t\t\t\t}},
\t\t\t}},
\t\t\tViewInfo = GroupInfo {{
\t\t\t\tPos = {{ 1160, {row + 290} }},
\t\t\t\tFlags = {{ Expanded = true, AllowPan = false, RemoveRouters = true }},
\t\t\t\tSize = {{ 928.485, 239.633, 37.3621, -47.0363 }},
\t\t\t\tDirection = "Horizontal",
\t\t\t\tPipeStyle = "Direct",
\t\t\t\tScale = 1,
\t\t\t\tOffset = {{ -1160, {-row - 290} }},
\t\t\t}},
\t\t\tTools = ordered() {{
{inner_tools}
\t\t\t}},
\t\t}},
'''


def build(source: Path, target: Path, country_prefix: str = "EGY") -> dict:
    content = source.read_text(encoding="utf-8")
    if (f"{country_prefix}_Border_Highlight_Control" in content or
            f"{country_prefix}_Border_Highlight_Group = " in content):
        raise ValueError("source composition already contains the border highlight prototype")
    # New exports use country prefixes; keep the original prototype fixture
    # supported without imposing its numbered names on future exports.
    native_names = f"{country_prefix}_Canvas = " in content
    base = country_prefix if native_names else "Country_Edit_01"
    canvas = _tool_block(content, f"{base}_Canvas")
    duration = round(_value(canvas, "GlobalOut"))
    width = round(_value(canvas, "Width"))
    height = round(_value(canvas, "Height"))
    points = _local_points(content, country_prefix, width, height)
    marker = f"\t\t{base}_Plane = ImagePlane3D"
    if content.count(marker) != 1:
        raise ValueError(f"expected one {base}_Plane insertion point")
    plane = _tool_block(content, f"{base}_Plane")
    material = re.search(r'MaterialInput = Input \{ SourceOp = "([^"]+)"', plane)
    if not material:
        raise ValueError(f"{base}_Plane has no material source")
    material_source = material.group(1)
    content = content.replace(marker, _nodes(
        country_prefix, points, duration, width, height, mode_name=material_source) + marker, 1)
    old_material = f'MaterialInput = Input {{ SourceOp = "{material_source}", Source = "Output", }},'
    new_material = (f'MaterialInput = Input {{ SourceOp = "{country_prefix}_Border_Highlight_Group", '
                    'Source = "MainOutput1", },')
    if content.count(old_material) != 1:
        raise ValueError("expected one country plane material connection")
    content = content.replace(old_material, new_material, 1)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return {"source": str(source), "target": str(target), "country": country_prefix,
            "border_points": len(points), "default_enabled": False}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("--country", default="EGY")
    args = parser.parse_args()
    print(build(args.source, args.target, args.country))


if __name__ == "__main__":
    main()
