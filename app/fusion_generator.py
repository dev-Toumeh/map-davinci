"""Generate a simple editable 2D Fusion composition from an animation shot.

The generated .comp is deliberately small: Loaders, ordinary Merge nodes and
one final Transform.  It is a starting graph that remains editable in Resolve.
"""
from __future__ import annotations

from pathlib import Path
import re


def _name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", value)


def _lua_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "\\\\").replace('"', '\\"')


def _key_lines(keys: list[dict], component: str) -> str:
    """Fusion BezierSpline keyframes; explicit linear flags give predictable
    endpoint timing. Smooth segments are represented with standard ease
    handles; Resolve users can refine them in the Spline editor.
    """
    lines = []
    for index, key in enumerate(keys):
        if component == "size":
            value = key["zoom"]
        elif component == "displacement":
            value = index / max(1, len(keys) - 1)
        else:
            value = key["fusion_center"][component]
        flag = "Linear = true" if key["easing"] == "linear" else ""
        flags = f", Flags = {{ {flag} }}" if flag else ""
        lines.append(f"\t\t\t\t[{key['frame']}] = {{ {value:.12g}{flags} }},")
    return "\n".join(lines)


def _path_points(keys: list[dict]) -> str:
    """Points used by PolyPath to produce Transform.Center's Position output.

    PolyPath's Position output is an offset from the normal Transform center:
    a point at 0, 0 evaluates to Center .5, .5. Convert from the browser's
    normalized Transform center to that offset grid so a browser center of
    .5, .5 remains centred in Resolve.
    """
    points = []
    for key in keys:
        center = key["fusion_center"]
        points.append("\t\t\t\t\t\t\t{ Linear = true, X = %.12g, Y = %.12g, LX = 0, LY = 0, RX = 0, RY = 0 },"
                      % (center["x"] - 0.5, center["y"] - 0.5))
    if len(points) == 1:
        points.append(points[0])
    return "\n".join(points)


def generate(package: Path, metadata: dict, animation: dict) -> Path:
    out = animation["output"]
    keys = []
    for key in animation["keyframes"]:
        # Fusion Transform's Center is where the source centre lands after
        # scaling. This converts the editor's camera/view centre to that value.
        z, center = key["zoom"], key["center"]
        keys.append({**key, "fusion_center": {
            "x": 0.5 + (0.5 - center["x"]) * z,
            "y": 0.5 + (0.5 - center["y"]) * z,
        }})
    wide_factor = float(metadata["output"]["wide_factor"])
    tools = []
    tools.append(f'''\t\tMap_Wide = Loader {{
\t\t\tNameSet = true,
\t\t\tClips = {{ Clip {{ ID = "Clip1", Filename = "{_lua_path(package / 'satellite_wide.png')}", Length = 1, GlobalEnd = {out['duration_frames'] - 1}, TrimOut = 0, Loop = 1 }} }},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ -220, 0 }} }},
\t\t}},''')
    current = "Map_Wide"
    tools.append(f'''\t\tMap_Detail = Loader {{
\t\t\tNameSet = true,
\t\t\tClips = {{ Clip {{ ID = "Clip1", Filename = "{_lua_path(package / 'satellite_detail.png')}", Length = 1, GlobalEnd = {out['duration_frames'] - 1}, TrimOut = 0, Loop = 1 }} }},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ -220, 70 }} }},
\t\t}},
\t\tPlace_Detail = Transform {{
\t\t\tInputs = {{ Size = Input {{ Value = {1 / wide_factor:.12g}, }}, Input = Input {{ SourceOp = "Map_Detail", Source = "Output", }} }},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ -90, 70 }} }},
\t\t}},
\t\tMerge_Detail = Merge {{
\t\t\tInputs = {{ Background = Input {{ SourceOp = "Map_Wide", Source = "Output", }}, Foreground = Input {{ SourceOp = "Place_Detail", Source = "Output", }} }},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ 50, 0 }} }},
\t\t}},''')
    current = "Merge_Detail"
    for number, country in enumerate(metadata.get("countries", []), 1):
        iso = _name(country["iso3"])
        loader, place, merge = f"Country_{iso}", f"Place_{iso}", f"Merge_{iso}"
        tools.append(f'''\t\t{loader} = Loader {{
\t\t\tNameSet = true,
\t\t\tClips = {{ Clip {{ ID = "Clip1", Filename = "{_lua_path(package / country['file'])}", Length = 1, GlobalEnd = {out['duration_frames'] - 1}, TrimOut = 0, Loop = 1 }} }},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ -220, {140 + number * 60} }} }},
\t\t}},
\t\t{place} = Transform {{
\t\t\tInputs = {{ Size = Input {{ Value = {1 / wide_factor:.12g}, }}, Input = Input {{ SourceOp = "{loader}", Source = "Output", }} }},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ -90, {140 + number * 60} }} }},
\t\t}},
\t\t{merge} = Merge {{
\t\t\tInputs = {{ Background = Input {{ SourceOp = "{current}", Source = "Output", }}, Foreground = Input {{ SourceOp = "{place}", Source = "Output", }} }},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ {190 + number * 130}, 0 }} }},
\t\t}},''')
        current = merge
    tools.append(f'''\t\tMap_AnimationDisplacement = BezierSpline {{ KeyFrames = {{
{_key_lines(keys, 'displacement')}
\t\t\t}} }},
\t\tMap_AnimationSize = BezierSpline {{ KeyFrames = {{
{_key_lines(keys, 'size')}
\t\t\t}} }},
\t\tMap_AnimationPath = PolyPath {{
\t\t\tInputs = {{
\t\t\t\tDisplacement = Input {{ SourceOp = "Map_AnimationDisplacement", Source = "Value", }},
\t\t\t\tPolyLine = Input {{ Value = Polyline {{ Points = {{
{_path_points(keys)}
\t\t\t\t\t\t}} }}, }},
\t\t\t}},
\t\t}},
\t\tMap_Animation = Transform {{
\t\t\tNameSet = true,
\t\t\tInputs = {{
\t\t\t\tCenter = Input {{ SourceOp = "Map_AnimationPath", Source = "Position", }},
\t\t\t\tSize = Input {{ SourceOp = "Map_AnimationSize", Source = "Value", }},
\t\t\t\tInput = Input {{ SourceOp = "{current}", Source = "Output", }},
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ 700, 0 }} }},
\t\t}},
\t\tMediaOut1 = MediaOut {{
\t\t\tInputs = {{ Input = Input {{ SourceOp = "Map_Animation", Source = "Output", }} }},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ 850, 0 }} }},
\t\t}},''')
    content = f'''Composition {{
\tCurrentTime = 0,
\tRenderRange = {{ 0, {out['duration_frames'] - 1} }},
\tGlobalRange = {{ 0, {out['duration_frames'] - 1} }},
\tTools = {{
{chr(10).join(tools)}
\t}}
}}
'''
    fusion_dir = package / "fusion"
    fusion_dir.mkdir(exist_ok=True)
    target = fusion_dir / "scene.comp"
    target.write_text(content, encoding="utf-8")
    return target
