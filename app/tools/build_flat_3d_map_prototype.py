#!/usr/bin/env python3
"""Wrap a generated 2D map composite in a shallow Fusion 3D camera rig.

The original composition is left untouched. Country geometry and close-up map
plates finish compositing in 2D, that result is textured onto one ImagePlane3D,
and inexpensive text/connection layers remain downstream of Renderer3D.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from tools.share_polygon_border import _tool_span


TILT_KEYS = {
    0: (0.0, 0.0, 0.0),
    371: (-4.0, 3.5, -0.8),
    705: (2.5, -4.0, 0.7),
    1120: (-3.5, 4.0, -0.7),
    1554: (3.5, -3.0, 0.8),
    1969: (-2.5, 2.5, -0.5),
}


def _smooth_spline(name: str, values: list[tuple[int, float]]) -> str:
    lines = []
    for index, (frame, value) in enumerate(values):
        handles = []
        if index:
            previous = values[index - 1][0]
            handles.append(f"LH = {{ {frame - (frame - previous) / 3:.12g}, {value:.12g} }}")
        if index + 1 < len(values):
            following = values[index + 1][0]
            handles.append(f"RH = {{ {frame + (following - frame) / 3:.12g}, {value:.12g} }}")
        suffix = ", " + ", ".join(handles) if handles else ""
        lines.append(f"\t\t\t\t[{frame}] = {{ {value:.12g}{suffix} }},")
    return f'''\t\t{name} = BezierSpline {{ KeyFrames = {{
{chr(10).join(lines)}
\t\t\t}} }},'''


def build(source: Path, target: Path) -> dict:
    content = source.read_text(encoding="utf-8")
    if "Map_3D_ImagePlane = ImagePlane3D" in content:
        raise ValueError("Composition already contains the flat 3D map rig")
    duration_match = re.search(r"RenderRange = \{\s*0,\s*(\d+)\s*\}", content)
    if not duration_match:
        raise ValueError("Could not determine the composition duration")
    duration = int(duration_match.group(1))
    keys = dict(TILT_KEYS)
    keys[duration] = (0.0, 0.0, 0.0)
    keyed = sorted((frame, value) for frame, value in keys.items()
                   if frame <= duration)

    splines = []
    for axis, component in zip("XYZ", range(3)):
        splines.append(_smooth_spline(
            f"Map_3D_Tilt_{axis}",
            [(frame, value[component]) for frame, value in keyed]))
    rig = f'''{chr(10).join(splines)}
\t\tMap_3D_ImagePlane = ImagePlane3D {{
\t\t\tNameSet = true,
\t\t\tInputs = {{
\t\t\t\t["Transform3DOp.Rotate.X"] = Input {{ SourceOp = "Map_3D_Tilt_X", Source = "Value", }},
\t\t\t\t["Transform3DOp.Rotate.Y"] = Input {{ SourceOp = "Map_3D_Tilt_Y", Source = "Value", }},
\t\t\t\t["Transform3DOp.Rotate.Z"] = Input {{ SourceOp = "Map_3D_Tilt_Z", Source = "Value", }},
\t\t\t\t["Transform3DOp.Scale.X"] = Input {{ Value = 1.35, }},
\t\t\t\t["Transform3DOp.Scale.Y"] = Input {{ Value = 1.35, }},
\t\t\t\t["Transform3DOp.Scale.Z"] = Input {{ Value = 1.35, }},
\t\t\t\t["SurfacePlaneInputs.ObjectID.ObjectID"] = Input {{ Value = 1, }},
\t\t\t\tMaterialInput = Input {{ SourceOp = "Final_Composite", Source = "Output", }},
\t\t\t\t["MtlStdInputs.UseTwoSidedLighting"] = Input {{ Value = 1, }},
\t\t\t\t["MtlStdInputs.MaterialID"] = Input {{ Value = 1, }}
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ 3070, -180 }} }},
\t\t}},
\t\tMap_3D_Camera = Camera3D {{
\t\t\tNameSet = true,
\t\t\tInputs = {{
\t\t\t\tAoV = Input {{ Value = 19.2642683071, }},
\t\t\t\t["Transform3DOp.Translate.Z"] = Input {{ Value = 3.35, }},
\t\t\t\t["Stereo.Mode"] = Input {{ Value = FuID {{ "Mono" }}, }},
\t\t\t\tApertureW = Input {{ Value = 0.467716535433, }},
\t\t\t\tApertureH = Input {{ Value = 0.831496062992, }},
\t\t\t\t["SurfacePlaneInputs.ObjectID.ObjectID"] = Input {{ Value = 2, }},
\t\t\t\t["MtlStdInputs.MaterialID"] = Input {{ Value = 2, }}
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ 3070, -20 }} }},
\t\t}},
\t\tMap_3D_Scene = Merge3D {{
\t\t\tNameSet = true,
\t\t\tInputs = {{
\t\t\t\tSceneInput1 = Input {{ SourceOp = "Map_3D_ImagePlane", Source = "Output", }},
\t\t\t\tSceneInput2 = Input {{ SourceOp = "Map_3D_Camera", Source = "Output", }}
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ 3300, -100 }} }},
\t\t}},
\t\tMap_3D_Renderer = Renderer3D {{
\t\t\tNameSet = true,
\t\t\tCustomData = {{ ToolVersion = 2, }},
\t\t\tInputs = {{
\t\t\t\tGlobalOut = Input {{ Value = {duration}, }},
\t\t\t\tWidth = Input {{ Value = 2160, }},
\t\t\t\tHeight = Input {{ Value = 3840, }},
\t\t\t\tUseFrameFormatSettings = Input {{ Value = 0, }},
\t\t\t\tSceneInput = Input {{ SourceOp = "Map_3D_Scene", Source = "Output", }},
\t\t\t\tRendererType = Input {{ Value = FuID {{ "RendererOpenGL" }}, }}
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ 3530, -100 }} }},
\t\t}},
\t\tMap_2D_3D_Switch = Switch {{
\t\t\tNameSet = true,
\t\t\tInputs = {{
\t\t\t\tNumberOfInputs = Input {{ Value = 2, }},
\t\t\t\tWhich = Input {{ Value = 1, }},
\t\t\t\tInput0 = Input {{ SourceOp = "Final_Composite", Source = "Output", }},
\t\t\t\tName0 = Input {{ Value = "ORIGINAL 2D", }},
\t\t\t\tInput1 = Input {{ SourceOp = "Map_3D_Renderer", Source = "Output", }},
\t\t\t\tName1 = Input {{ Value = "3D PERSPECTIVE", }}
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ 3760, -100 }} }},
\t\t\tColors = {{ TileColor = {{ R = 0.572549019608, G = 0.572549019608, B = 0.572549019608 }}, }}
\t\t}},
'''

    vector_start, vector_end = _tool_span(content, "Vector_Layers")
    vector = content[vector_start:vector_end]
    old = 'Background = Input { SourceOp = "Final_Composite", Source = "Output", }'
    if old not in vector:
        raise ValueError("Vector_Layers is not fed by Final_Composite")
    vector = vector.replace(
        old, 'Background = Input { SourceOp = "Map_2D_3D_Switch", Source = "Output", }', 1)
    result = content[:vector_start] + rig + vector + content[vector_end:]
    target.write_text(result, encoding="utf-8")
    return {
        "source": str(source),
        "target": str(target),
        "duration": duration,
        "animated_3d_keys": len(keyed),
        "vector_layers_remain_2d": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    args = parser.parse_args()
    print(build(args.source, args.target))


if __name__ == "__main__":
    main()
