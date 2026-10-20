"""Add an icon and fake shadow as one country-local 3D group."""
from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path


NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"


def _tool_span(content: str, name: str) -> tuple[int, int]:
    marker = re.search(rf"(?m)^\s*{re.escape(name)}\s*=\s*\w+\s*\{{", content)
    if not marker:
        raise ValueError(f"Fusion tool {name} was not found")
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
                return marker.start(), end
    raise ValueError(f"Fusion tool {name} has an unclosed block")


def _tool_block(content: str, name: str) -> str:
    start, end = _tool_span(content, name)
    return content[start:end]


def _input_value(block: str, input_name: str) -> float:
    match = re.search(
        rf'{re.escape(input_name)}"?\]\s*=\s*Input\s*\{{\s*Value\s*=\s*({NUMBER})', block)
    if not match:
        match = re.search(
            rf'\b{re.escape(input_name)}\s*=\s*Input\s*\{{\s*Value\s*=\s*({NUMBER})', block)
    if not match:
        raise ValueError(f"Input {input_name} was not found")
    return float(match.group(1))


def build(source: Path, target: Path, icon_source: Path, icon_target: Path,
          country_prefix: str = "EGY", country_plane: str = "Country_Edit_01_Plane",
          icon_label: str = "Islam") -> dict:
    content = source.read_text(encoding="utf-8")
    prefix = f"{country_prefix}_{icon_label}"
    if f"{prefix}_Icon_Loader" in content:
        raise ValueError("source composition already contains this icon")

    country = _tool_block(content, country_plane)
    center_x = _input_value(country, "Transform3DOp.Translate.X")
    center_y = _input_value(country, "Transform3DOp.Translate.Y")
    country_z = _input_value(country, "Transform3DOp.Translate.Z")
    country_scale = _input_value(country, "Transform3DOp.Scale.X")
    icon_scale = country_scale * (0.07 / 0.436316653129)
    shadow_local_offset = 1 / 7
    shadow_local_depth = -0.00001 / icon_scale
    duration = round(_input_value(_tool_block(content, "Map_3D_Renderer"), "GlobalOut"))
    icon_path = str(icon_target.resolve()).replace("\\", "/")

    nodes = f'''\t\t{prefix}_Icon_Loader = Loader {{
\t\t\tNameSet = true,
\t\t\tClips = {{ Clip {{ ID = "Clip1", Filename = "{icon_path}", Length = 1, GlobalEnd = {duration}, TrimOut = 0, Loop = 1 }} }},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ 2500, -1080 }} }},
\t\t}},
\t\t{prefix}_Icon_Color = Background {{ NameSet = true, Inputs = {{
\t\t\tGlobalOut = Input {{ Value = {duration}, }}, Width = Input {{ Value = 512, }}, Height = Input {{ Value = 512, }}, UseFrameFormatSettings = Input {{ Value = 0, }},
\t\t\tTopLeftRed = Input {{ Value = 1, }}, TopLeftGreen = Input {{ Value = 0.84, }}, TopLeftBlue = Input {{ Value = 0.22, }},
\t\t\tEffectMask = Input {{ SourceOp = "{prefix}_Icon_Loader", Source = "Output", }}
\t\t}}, ViewInfo = OperatorInfo {{ Pos = {{ 2500, -940 }} }}, }},
\t\t{prefix}_Shadow_Color = Background {{ NameSet = true, Inputs = {{
\t\t\tGlobalOut = Input {{ Value = {duration}, }}, Width = Input {{ Value = 512, }}, Height = Input {{ Value = 512, }}, UseFrameFormatSettings = Input {{ Value = 0, }},
\t\t\tTopLeftRed = Input {{ Value = 0, }}, TopLeftGreen = Input {{ Value = 0, }}, TopLeftBlue = Input {{ Value = 0, }}, TopLeftAlpha = Input {{ Value = 0.28, }},
\t\t\tEffectMask = Input {{ SourceOp = "{prefix}_Icon_Loader", Source = "Output", }}
\t\t}}, ViewInfo = OperatorInfo {{ Pos = {{ 2700, -940 }} }}, }},
\t\t{prefix}_Shadow_Blur = Blur {{ NameSet = true, Inputs = {{ XBlurSize = Input {{ Value = 12, }}, YBlurSize = Input {{ Value = 12, }}, Input = Input {{ SourceOp = "{prefix}_Shadow_Color", Source = "Output", }} }}, ViewInfo = OperatorInfo {{ Pos = {{ 2700, -800 }} }}, }},
\t\t{prefix}_Icon_Plane = ImagePlane3D {{ NameSet = true, Inputs = {{
\t\t\tMaterialInput = Input {{ SourceOp = "{prefix}_Icon_Color", Source = "Output", }}, ["MtlStdInputs.UseTwoSidedLighting"] = Input {{ Value = 1, }}
\t\t}}, ViewInfo = OperatorInfo {{ Pos = {{ 2500, -800 }} }}, }},
\t\t{prefix}_Shadow_Plane = ImagePlane3D {{ NameSet = true, Inputs = {{
\t\t\t["Transform3DOp.Translate.X"] = Input {{ Value = {shadow_local_offset:.12g}, }},
\t\t\t["Transform3DOp.Translate.Y"] = Input {{ Value = {-shadow_local_offset:.12g}, }},
\t\t\t["Transform3DOp.Translate.Z"] = Input {{ Value = {shadow_local_depth:.12g}, }},
\t\t\tMaterialInput = Input {{ SourceOp = "{prefix}_Shadow_Blur", Source = "Output", }}, ["MtlStdInputs.UseTwoSidedLighting"] = Input {{ Value = 1, }}
\t\t}}, ViewInfo = OperatorInfo {{ Pos = {{ 2700, -660 }} }}, }},
\t\t{prefix}_Object_3D_Group = Merge3D {{ NameSet = true, Inputs = {{
\t\t\tSceneInput1 = Input {{ SourceOp = "{prefix}_Shadow_Plane", Source = "Output", }},
\t\t\tSceneInput2 = Input {{ SourceOp = "{prefix}_Icon_Plane", Source = "Output", }}
\t\t}}, ViewInfo = OperatorInfo {{ Pos = {{ 2860, -720 }} }}, }},
\t\t{prefix}_Object_3D_Transform = Transform3D {{ NameSet = true, Inputs = {{
\t\t\t["Transform3DOp.Translate.X"] = Input {{ Value = {center_x:.12g}, }},
\t\t\t["Transform3DOp.Translate.Y"] = Input {{ Value = {center_y:.12g}, }},
\t\t\t["Transform3DOp.Translate.Z"] = Input {{ Value = {country_z + 0.00002:.12g}, }},
\t\t\t["Transform3DOp.Scale.X"] = Input {{ Value = {icon_scale:.12g}, }}, ["Transform3DOp.Scale.Y"] = Input {{ Value = {icon_scale:.12g}, }}, ["Transform3DOp.Scale.Z"] = Input {{ Value = {icon_scale:.12g}, }},
\t\t\tSceneInput = Input {{ SourceOp = "{prefix}_Object_3D_Group", Source = "Output", }}
\t\t}}, ViewInfo = OperatorInfo {{ Pos = {{ 3020, -720 }} }}, }},
'''
    scene_marker = "\t\tMap_3D_Scene = Merge3D"
    if content.count(scene_marker) != 1:
        raise ValueError("expected one Map_3D_Scene insertion point")
    content = content.replace(scene_marker, nodes + scene_marker, 1)

    scene_start, scene_end = _tool_span(content, "Map_3D_Scene")
    scene = content[scene_start:scene_end]
    old_source = f'SourceOp = "{country_plane}"'
    if scene.count(old_source) != 1:
        raise ValueError("expected the country plane once in Map_3D_Scene")
    scene_inputs = [int(value) for value in re.findall(r"\bSceneInput(\d+)\s*=", scene)]
    next_input = max(scene_inputs, default=0) + 1
    camera_line = re.search(
        r'(\n\s*SceneInput\d+\s*=\s*Input\s*\{\s*SourceOp\s*=\s*"Map_3D_Camera"[^\n]*)(\n)',
        scene,
    )
    if not camera_line:
        raise ValueError("Map_3D_Camera scene input was not found")
    addition = (
        f',\n\t\t\t\tSceneInput{next_input} = Input {{ SourceOp = '
        f'"{prefix}_Object_3D_Transform", Source = "Output", }}'
    )
    scene = scene[:camera_line.end(1)] + addition + scene[camera_line.end(1):]
    content = content[:scene_start] + scene + content[scene_end:]

    target.parent.mkdir(parents=True, exist_ok=True)
    icon_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(icon_source, icon_target)
    target.write_text(content, encoding="utf-8")
    return {
        "source": str(source), "target": str(target), "country": country_prefix,
        "center": [center_x, center_y], "country_z": country_z,
        "shadow_z": country_z + 0.00001, "icon_z": country_z + 0.00002,
        "topology": "country remains independent; shadow + icon -> one object Transform3D -> main Merge3D",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("icon_source", type=Path)
    parser.add_argument("icon_target", type=Path)
    parser.add_argument("--country", default="EGY")
    parser.add_argument("--country-plane", default="Country_Edit_01_Plane")
    parser.add_argument("--icon-label", default="Islam")
    args = parser.parse_args()
    print(build(args.source, args.target, args.icon_source, args.icon_target,
                args.country, args.country_plane, args.icon_label))


if __name__ == "__main__":
    main()
