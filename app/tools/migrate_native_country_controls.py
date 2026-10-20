"""Move legacy country flag and border controls onto native Fusion inputs.

The input is an exported .comp. The output is a separate .comp so the source
remains available for comparison until Resolve has passed a reopen test.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path


COUNTRIES = ("PAK", "IRN", "AFG", "IND")
NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"


def _braced_end(text: str, opening: int) -> int:
    depth = 0
    quoted = escaped = False
    for index in range(opening, len(text)):
        char = text[index]
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index + 1
    raise ValueError("unclosed Fusion table")


def _tool_span(text: str, name: str) -> tuple[int, int]:
    matches = list(re.finditer(
        rf"(?m)^[\t ]*{re.escape(name)} = \w+ \{{", text))
    if len(matches) != 1:
        raise ValueError(f"expected one tool {name}, found {len(matches)}")
    start = matches[0].start()
    end = _braced_end(text, text.find("{", matches[0].start()))
    if text[end:end + 1] == ",":
        end += 1
    return start, end


def _tool(text: str, name: str) -> str:
    start, end = _tool_span(text, name)
    return text[start:end]


def _replace_tool(text: str, name: str, replacement: str) -> str:
    start, end = _tool_span(text, name)
    return text[:start] + replacement + text[end:]


def _remove_tool(text: str, name: str) -> str:
    start, end = _tool_span(text, name)
    if text[end:end + 1] == "\n":
        end += 1
    return text[:start] + text[end:]


def _input(block: str, name: str) -> str:
    matches = list(re.finditer(
        rf"\b{re.escape(name)} = Input \{{", block))
    if len(matches) != 1:
        raise ValueError(f"expected one input {name}, found {len(matches)}")
    start = matches[0].start()
    opening = block.find("{", start)
    return block[start:_braced_end(block, opening)]


def _set_input(block: str, name: str, payload: str) -> str:
    old = _input(block, name)
    return block.replace(old, f"{name} = Input {{ {payload} }}", 1)


def _value(block: str, name: str) -> float:
    match = re.search(rf"\bValue = ({NUMBER})", _input(block, name))
    if not match:
        raise ValueError(f"{name} is animated, not a static number")
    return float(match.group(1))


def _source(block: str, name: str) -> str | None:
    match = re.search(r'SourceOp = "([^"]+)"', _input(block, name))
    return match.group(1) if match else None


def _expression(block: str, name: str) -> str:
    match = re.search(r'Expression = "([^"]+)"', _input(block, name))
    if not match:
        raise ValueError(f"missing expression on {name}")
    return match.group(1)


def _number(value: float) -> str:
    return f"{value:.12g}"


def _move_spline_into_group(text: str, old: str, new: str, group: str) -> str:
    spline = _tool(text, old).replace(f"{old} = BezierSpline", f"{new} = BezierSpline", 1)
    if not spline.startswith("\t\t"):
        raise ValueError(f"unexpected spline indentation: {old}")
    text = _remove_tool(text, old)
    group_block = _tool(text, group)
    marker = "\t\t\tTools = ordered() {\n"
    if group_block.count(marker) != 1:
        raise ValueError(f"missing group tool list: {group}")
    nested = "\n".join("\t\t" + line for line in spline.splitlines())
    group_block = group_block.replace(marker, marker + nested + "\n", 1)
    return _replace_tool(text, group, group_block)


def _flag(text: str, country: str) -> str:
    control = f"{country}_Flag_Adjust"
    merge = f"{country}_Flag_Masked_On_Working_Canvas"
    adjust = _tool(text, control)
    node = _tool(text, merge)
    center = _expression(node, "Center")
    shape = re.fullmatch(
        rf"Point\(0\.5 \+ \(({NUMBER}) - ({NUMBER}) \+ {control}\.Offset_X\) / ({NUMBER}), "
        rf"0\.5 \+ \(({NUMBER}) - ({NUMBER}) \+ {control}\.Offset_Y\) \* ({NUMBER})\)", center)
    if not shape:
        raise ValueError(f"unexpected flag placement expression: {country}")
    left, right, divisor, top, bottom, multiplier = map(float, shape.groups())
    x = 0.5 + (left - right + _value(adjust, "Offset_X")) / divisor
    y = 0.5 + (top - bottom + _value(adjust, "Offset_Y")) * multiplier
    size_expression = _expression(node, "Size")
    size_match = re.fullmatch(
        rf"{control}\.Scale \* ({NUMBER})", size_expression)
    if not size_match:
        raise ValueError(f"unexpected flag size expression: {country}")
    size = _value(adjust, "Scale") * float(size_match.group(1))
    opacity_spline = _source(adjust, "Opacity")
    if opacity_spline:
        new_spline = f"{merge}Blend"
        spline = _tool(text, opacity_spline).replace(
            f"{opacity_spline} = BezierSpline", f"{new_spline} = BezierSpline", 1)
        text = _replace_tool(text, opacity_spline, spline)
        blend = f'SourceOp = "{new_spline}", Source = "Value",'
    else:
        blend = f"Value = {_number(_value(adjust, 'Opacity'))},"
    node = _set_input(node, "Center", f"Value = {{ {_number(x)}, {_number(y)} }},")
    node = _set_input(node, "Size", f"Value = {_number(size)},")
    node = _set_input(node, "Blend", blend)
    text = _replace_tool(text, merge, node)
    return _remove_tool(text, control)


def _border(text: str, country: str) -> str:
    settings_name = f"{country}_Border_Settings"
    group = f"{country}_Border_Highlight_Group"
    path = f"{country}_Border_Highlight_Path"
    core = f"{country}_Border_Highlight_Core"
    inner = f"{country}_Border_Highlight_Inner_Glow"
    outer = f"{country}_Border_Highlight_Outer_Glow"
    merge = f"{country}_Border_Highlight_Merge"
    settings = _tool(text, settings_name)
    mapping = (
        (path, "BorderWidth", "Core_Width"),
        (path, "WritePosition", "Start_Position"),
        (path, "WriteLength", "Segment_Length"),
        (core, "TopLeftRed", "Red"),
        (core, "TopLeftGreen", "Green"),
        (core, "TopLeftBlue", "Blue"),
        (inner, "XGlowSize", "Inner_Glow_Size"),
        (outer, "XGlowSize", "Outer_Glow_Size"),
        (inner, "Glow", "Glow_Strength"),
        (outer, "Glow", "Glow_Strength"),
    )
    splines = []
    for node_name, input_name, setting_name in mapping:
        source = _source(settings, setting_name)
        if source:
            new_source = f"{node_name}{input_name}"
            if (source, new_source) not in splines:
                splines.append((source, new_source))
            payload = f'SourceOp = "{new_source}", Source = "Value",'
        else:
            payload = f"Value = {_number(_value(settings, setting_name))},"
        node = _tool(text, node_name)
        node = _set_input(node, input_name, payload)
        text = _replace_tool(text, node_name, node)
    enabled_source = _source(settings, "Enabled")
    opacity_source = _source(settings, "Opacity")
    enabled = None if enabled_source else _value(settings, "Enabled")
    opacity = None if opacity_source else _value(settings, "Opacity")
    if enabled_source and opacity_source:
        raise ValueError(f"two animated border blend factors: {country}")
    if enabled_source:
        if opacity != 1:
            raise ValueError(f"cannot preserve animated border with opacity {opacity}")
        source = enabled_source
    elif opacity_source:
        if enabled != 1:
            raise ValueError(f"cannot preserve animated opacity with enabled {enabled}")
        source = opacity_source
    else:
        source = None
    if source:
        new_source = f"{merge}Blend"
        splines.append((source, new_source))
        blend = f'SourceOp = "{new_source}", Source = "Value",'
    else:
        blend = f"Value = {_number(enabled * opacity)},"
    node = _tool(text, merge)
    node = _set_input(node, "Blend", blend)
    text = _replace_tool(text, merge, node)
    text = _remove_tool(text, settings_name)
    for old, new in splines:
        text = _move_spline_into_group(text, old, new, group)
    return text


def migrate(source: Path, target: Path) -> None:
    if source.resolve() == target.resolve():
        raise ValueError("source and target must differ")
    text = source.read_text(encoding="utf-8")
    for country in COUNTRIES:
        text = _flag(text, country)
        text = _border(text, country)
    for country in COUNTRIES:
        if f"{country}_Flag_Adjust" in text or f"{country}_Border_Settings" in text:
            raise ValueError(f"legacy controller reference remains: {country}")
    names = set(re.findall(r"(?m)^[\t ]*([A-Za-z]\w*) = \w+ \{", text))
    refs = set(re.findall(r'SourceOp = "([^"]+)"', text))
    missing = refs - names
    if missing:
        raise ValueError(f"unresolved SourceOp: {', '.join(sorted(missing))}")
    target.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    args = parser.parse_args()
    migrate(args.source, args.target)


if __name__ == "__main__":
    main()
