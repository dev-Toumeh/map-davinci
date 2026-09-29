#!/usr/bin/env python3
"""Build a short, low-resolution 2D/3D depth comparison from scene_v022."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from tools.build_flat_3d_map_prototype import _smooth_spline
from tools.share_polygon_border import _tool_span


SHOT_START = 305
SHOT_FOCUS = 371
SHOT_END = 396
PREVIEW_WIDTH = 540
PREVIEW_HEIGHT = 960
TEXTURE_SIZE = 960

# Camera positions look at the origin. Moving both sideways and vertically
# makes perspective unmistakable while the two scene planes remain registered.
CAMERA_KEYS = {
    SHOT_START: (-0.20, -0.85, 3.75),
    338: (0.05, -1.10, 3.45),
    SHOT_FOCUS: (0.38, -1.35, 3.15),
    SHOT_END: (0.12, -0.95, 3.55),
}


def _replace_tool(content: str, name: str, old: str, new: str) -> str:
    start, end = _tool_span(content, name)
    block = content[start:end]
    if old not in block:
        raise ValueError(f"Could not find expected value in {name}: {old}")
    return content[:start] + block.replace(old, new, 1) + content[end:]


def build(source: Path, target: Path) -> dict:
    content = source.read_text(encoding="utf-8")
    required = ["Map_Working_Canvas", "Country_Edit_01_Render",
                "Final_Composite", "Vector_Layers", "Map_Quality_Switch"]
    for name in required:
        _tool_span(content, name)

    # Keep all authored animation at its original absolute frames and limit
    # only the playback/render range to this 3.8-second comparison shot.
    content = re.sub(r"CurrentTime = \d+", f"CurrentTime = {SHOT_FOCUS}",
                     content, count=1)
    content = re.sub(r"RenderRange = \{\s*\d+,\s*\d+\s*\}",
                     f"RenderRange = {{ {SHOT_START}, {SHOT_END} }}",
                     content, count=1)
    content = re.sub(r"GlobalRange = \{\s*\d+,\s*\d+\s*\}",
                     f"GlobalRange = {{ {SHOT_START}, {SHOT_END} }}",
                     content, count=1)

    # Frame 371 has a cached close-up. Enable the existing render-quality path
    # rather than creating or retiming any local imagery.
    content = _replace_tool(
        content, "Map_Quality_Switch",
        "Which = Input { Value = 0, }", "Which = Input { Value = 1, }")

    splines = []
    positions = sorted(CAMERA_KEYS.items())
    for axis, component in zip("XYZ", range(3)):
        splines.append(_smooth_spline(
            f"Depth_Test_Camera_{axis}",
            [(frame, value[component]) for frame, value in positions]))

    rig = f'''{chr(10).join(splines)}
\t\tDepth_Test_2D_Preview = BetterResize {{
\t\t\tNameSet = true,
\t\t\tInputs = {{ Width = Input {{ Value = {PREVIEW_WIDTH}, }}, Height = Input {{ Value = {PREVIEW_HEIGHT}, }}, KeepAspect = Input {{ Value = 1, }}, HiQOnly = Input {{ Value = 0, }}, PixelAspect = Input {{ Value = {{ 1, 1 }}, }}, Input = Input {{ SourceOp = "Final_Composite", Source = "Output", }} }},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ 3070, 130 }} }},
\t\t}},
\t\tDepth_Test_Ground_Texture = BetterResize {{
\t\t\tNameSet = true,
\t\t\tInputs = {{ Width = Input {{ Value = {TEXTURE_SIZE}, }}, Height = Input {{ Value = {TEXTURE_SIZE}, }}, KeepAspect = Input {{ Value = 1, }}, HiQOnly = Input {{ Value = 0, }}, PixelAspect = Input {{ Value = {{ 1, 1 }}, }}, Input = Input {{ SourceOp = "Map_Working_Canvas", Source = "Output", }} }},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ 3070, -250 }} }},
\t\t}},
\t\tDepth_Test_Territory_Texture = BetterResize {{
\t\t\tNameSet = true,
\t\t\tInputs = {{ Width = Input {{ Value = {TEXTURE_SIZE}, }}, Height = Input {{ Value = {TEXTURE_SIZE}, }}, KeepAspect = Input {{ Value = 1, }}, HiQOnly = Input {{ Value = 0, }}, PixelAspect = Input {{ Value = {{ 1, 1 }}, }}, Input = Input {{ SourceOp = "Country_Edit_01_Render", Source = "Output", }} }},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ 3070, -100 }} }},
\t\t}},
\t\tDepth_Test_Ground_Plane = ImagePlane3D {{
\t\t\tNameSet = true,
\t\t\tInputs = {{
\t\t\t\t["Transform3DOp.Scale.X"] = Input {{ Value = 1.6, }},
\t\t\t\t["Transform3DOp.Scale.Y"] = Input {{ Value = 1.6, }},
\t\t\t\t["Transform3DOp.Scale.Z"] = Input {{ Value = 1.6, }},
\t\t\t\t["SurfacePlaneInputs.ObjectID.ObjectID"] = Input {{ Value = 1, }},
\t\t\t\tMaterialInput = Input {{ SourceOp = "Depth_Test_Ground_Texture", Source = "Output", }},
\t\t\t\t["MtlStdInputs.UseTwoSidedLighting"] = Input {{ Value = 1, }},
\t\t\t\t["MtlStdInputs.MaterialID"] = Input {{ Value = 1, }}
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ 3300, -250 }} }},
\t\t}},
\t\tDepth_Test_Louisiana_Raised = ImagePlane3D {{
\t\t\tNameSet = true,
\t\t\tInputs = {{
\t\t\t\t["Transform3DOp.Translate.Z"] = Input {{ Value = 0.065, }},
\t\t\t\t["Transform3DOp.Scale.X"] = Input {{ Value = 1.6, }},
\t\t\t\t["Transform3DOp.Scale.Y"] = Input {{ Value = 1.6, }},
\t\t\t\t["Transform3DOp.Scale.Z"] = Input {{ Value = 1.6, }},
\t\t\t\t["SurfacePlaneInputs.ObjectID.ObjectID"] = Input {{ Value = 2, }},
\t\t\t\tMaterialInput = Input {{ SourceOp = "Depth_Test_Territory_Texture", Source = "Output", }},
\t\t\t\t["MtlStdInputs.UseTwoSidedLighting"] = Input {{ Value = 1, }},
\t\t\t\t["MtlStdInputs.MaterialID"] = Input {{ Value = 2, }}
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ 3300, -100 }} }},
\t\t}},
\t\tDepth_Test_Camera = Camera3D {{
\t\t\tNameSet = true,
\t\t\tInputs = {{
\t\t\t\tAoV = Input {{ Value = 24, }},
\t\t\t\t["Transform3DOp.Translate.X"] = Input {{ SourceOp = "Depth_Test_Camera_X", Source = "Value", }},
\t\t\t\t["Transform3DOp.Translate.Y"] = Input {{ SourceOp = "Depth_Test_Camera_Y", Source = "Value", }},
\t\t\t\t["Transform3DOp.Translate.Z"] = Input {{ SourceOp = "Depth_Test_Camera_Z", Source = "Value", }},
\t\t\t\t["Transform3DOp.UseTarget"] = Input {{ Value = 1, }},
\t\t\t\t["Transform3DOp.Target.X"] = Input {{ Value = 0, }},
\t\t\t\t["Transform3DOp.Target.Y"] = Input {{ Value = 0, }},
\t\t\t\t["Transform3DOp.Target.Z"] = Input {{ Value = 0, }},
\t\t\t\t["Stereo.Mode"] = Input {{ Value = FuID {{ "Mono" }}, }},
\t\t\t\tApertureW = Input {{ Value = 0.467716535433, }},
\t\t\t\tApertureH = Input {{ Value = 0.831496062992, }},
\t\t\t\t["SurfacePlaneInputs.ObjectID.ObjectID"] = Input {{ Value = 3, }},
\t\t\t\t["MtlStdInputs.MaterialID"] = Input {{ Value = 3, }}
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ 3300, 50 }} }},
\t\t}},
\t\tDepth_Test_Scene = Merge3D {{
\t\t\tNameSet = true,
\t\t\tInputs = {{
\t\t\t\tSceneInput1 = Input {{ SourceOp = "Depth_Test_Ground_Plane", Source = "Output", }},
\t\t\t\tSceneInput2 = Input {{ SourceOp = "Depth_Test_Louisiana_Raised", Source = "Output", }},
\t\t\t\tSceneInput3 = Input {{ SourceOp = "Depth_Test_Camera", Source = "Output", }}
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ 3530, -100 }} }},
\t\t}},
\t\tDepth_Test_Renderer = Renderer3D {{
\t\t\tNameSet = true,
\t\t\tCustomData = {{ ToolVersion = 2, }},
\t\t\tInputs = {{
\t\t\t\tGlobalIn = Input {{ Value = {SHOT_START}, }},
\t\t\t\tGlobalOut = Input {{ Value = {SHOT_END}, }},
\t\t\t\tWidth = Input {{ Value = {PREVIEW_WIDTH}, }},
\t\t\t\tHeight = Input {{ Value = {PREVIEW_HEIGHT}, }},
\t\t\t\tUseFrameFormatSettings = Input {{ Value = 0, }},
\t\t\t\tSceneInput = Input {{ SourceOp = "Depth_Test_Scene", Source = "Output", }},
\t\t\t\tRendererType = Input {{ Value = FuID {{ "RendererOpenGL" }}, }}
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ 3760, -100 }} }},
\t\t}},
\t\tDepth_Test_2D_3D = Switch {{
\t\t\tNameSet = true,
\t\t\tInputs = {{
\t\t\t\tNumberOfInputs = Input {{ Value = 2, }},
\t\t\t\tWhich = Input {{ Value = 1, }},
\t\t\t\tInput0 = Input {{ SourceOp = "Depth_Test_2D_Preview", Source = "Output", }},
\t\t\t\tName0 = Input {{ Value = "2D BASELINE - 540x960", }},
\t\t\t\tInput1 = Input {{ SourceOp = "Depth_Test_Renderer", Source = "Output", }},
\t\t\t\tName1 = Input {{ Value = "3D DEPTH - 540x960", }}
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ 3990, -100 }} }},
\t\t\tColors = {{ TileColor = {{ R = 0.572549019608, G = 0.572549019608, B = 0.572549019608 }}, }}
\t\t}},
'''

    vector_start, vector_end = _tool_span(content, "Vector_Layers")
    vector = content[vector_start:vector_end]
    old = 'Background = Input { SourceOp = "Final_Composite", Source = "Output", }'
    if old not in vector:
        raise ValueError("Vector_Layers is not fed by Final_Composite")
    vector = vector.replace(
        old, 'Background = Input { SourceOp = "Depth_Test_2D_3D", Source = "Output", }', 1)
    result = content[:vector_start] + rig + vector + content[vector_end:]
    target.write_text(result, encoding="utf-8")
    return {
        "source": str(source),
        "target": str(target),
        "shot_frames": [SHOT_START, SHOT_END],
        "shot_seconds": (SHOT_END - SHOT_START + 1) / 24,
        "focus_frame": SHOT_FOCUS,
        "preview_resolution": [PREVIEW_WIDTH, PREVIEW_HEIGHT],
        "texture_resolution": [TEXTURE_SIZE, TEXTURE_SIZE],
        "raised_source": "Country_Edit_01_Render (Louisiana Purchase)",
        "territory_height": 0.065,
        "camera_pose_keys": len(CAMERA_KEYS),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    args = parser.parse_args()
    print(build(args.source, args.target))


if __name__ == "__main__":
    main()
