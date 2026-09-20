"""Generate an editable 2D Fusion composition for a map-video shot.

Satellite imagery remains raster. Country highlights are native Fusion
MultiPoly masks built from saved GeoJSON points and composed with MultiMerge.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

R = 6378137.0


def _name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", value)


def _lua_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "\\\\").replace('"', '\\"')


def _merc(lon: float, lat: float) -> tuple[float, float]:
    lat = max(-85.05112878, min(85.05112878, lat))
    return (R * math.radians(lon), R * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)))


def _polygons(geom: dict) -> list[list[list[tuple[float, float]]]]:
    if geom["type"] == "Polygon":
        return [[[(float(x), float(y)) for x, y in ring] for ring in geom["coordinates"]]]
    if geom["type"] == "MultiPolygon":
        return [[[(float(x), float(y)) for x, y in ring] for ring in poly] for poly in geom["coordinates"]]
    if geom["type"] == "GeometryCollection":
        return [poly for child in geom.get("geometries", []) for poly in _polygons(child)]
    raise ValueError(f"unsupported geometry type {geom['type']!r}")


def _geometry(package: Path, country: dict) -> dict:
    """Use the immutable saved GeoJSON; old packages fall back to current NE."""
    geometry_file = country.get("geometry_file")
    if geometry_file and (package / geometry_file).is_file():
        return json.loads((package / geometry_file).read_text(encoding="utf-8"))["geometry"]
    # Existing packages predate geometry_<ISO>.geojson. This fallback lets them
    # use native vectors but new exports are fully self-contained.
    import exporter
    return exporter.get_geometry(country["iso3"])


def _polyline(ring: list[tuple[float, float]], bbox: dict) -> str:
    minx, miny, maxx, maxy = bbox["minx"], bbox["miny"], bbox["maxx"], bbox["maxy"]
    points = []
    # GeoJSON closes rings by repeating the first point; Fusion's Closed flag
    # supplies that segment, so omit the duplicate.
    source = ring[:-1] if len(ring) > 1 and ring[0] == ring[-1] else ring
    for lon, lat in source:
        x, y = _merc(lon, lat)
        # Fusion polygon controls are centered at 0,0 and use Y-up. The
        # geographic calculation above is normalized top-left 0..1, so convert
        # it before emitting native MultiPoly points.
        px = (x - minx) / (maxx - minx) - 0.5
        py = 0.5 - (maxy - y) / (maxy - miny)
        points.append(f"{{ Linear = true, X = {px:.12g}, Y = {py:.12g}, LX = 0, LY = 0, RX = 0, RY = 0 }},")
    return " ".join(points)


def _country_mask(name: str, geometry: dict, wide_bbox: dict, width: int, height: int,
                  *, outline: bool = False, pos: tuple[int, int] = (0, 0)) -> str:
    rings: list[tuple[int, list[tuple[float, float]]]] = []
    for polygon in _polygons(geometry):
        for index, ring in enumerate(polygon):
            if len(ring) >= 3:
                # MultiPoly levels add outer rings and subtract interior holes.
                rings.append((1 if index == 0 else -1, ring))
    if not rings:
        raise ValueError(f"{name} has no valid polygon rings")
    inputs, definitions, order = [], [], []
    for index, (level, ring) in enumerate(rings, 1):
        order.append(str(index))
        outline_inputs = (f'\n\t\t\t\t["PolyMask{index}.Solid"] = Input {{ Value = 0, }},'
                          f'\n\t\t\t\t["PolyMask{index}.BorderWidth"] = Input {{ Value = 0.0005, }},') if outline else ""
        inputs.append(f'''\t\t\t\t["PolyMask{index}.Level"] = Input {{ Value = {level}, }},
\t\t\t\t["PolyMask{index}.Filter"] = Input {{ Value = FuID {{ "Fast Gaussian" }}, }},
\t\t\t\t["PolyMask{index}.Polyline"] = Input {{ Value = Polyline {{ Closed = true, Points = {{ {_polyline(ring, wide_bbox)} }} }}, }},
\t\t\t\t["PolyMask{index}.Polyline2"] = Input {{ Value = Polyline {{ }}, Disabled = true, }},{outline_inputs}''')
        definitions.append(f"\t\t\tPolyMask{index} = PolyMaskInputs {{ DrawMode = \"InsertAndModify\", DrawMode2 = \"InsertAndModify\" }},")
    return f'''\t\t{name}_Mask = MultiPoly {{
\t\t\tNameSet = true,
\t\t\tInputs = {{
\t\t\t\tMaskWidth = Input {{ Value = {width}, }}, MaskHeight = Input {{ Value = {height}, }},
\t\t\t\tPixelAspect = Input {{ Value = {{ 1, 1 }}, }}, UseFrameFormatSettings = Input {{ Value = 1, }},
\t\t\t\tClippingMode = Input {{ Value = FuID {{ "None" }}, }},
\t\t\t\tPolyOrder = Input {{ Value = ScriptVal {{ {{ [0] = {', '.join(order)} }} }}, }},
{chr(10).join(inputs)}
\t\t\t}},
{chr(10).join(definitions)}
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ {pos[0]}, {pos[1]} }} }},
\t\t}},'''


def _rgb(hex_color: str) -> tuple[float, float, float]:
    value = hex_color.lstrip("#")
    if len(value) != 6:
        return (22 / 255, 137 / 255, 1.0)
    return tuple(int(value[i:i + 2], 16) / 255 for i in (0, 2, 4))


def _key_lines(keys: list[dict], component: str) -> str:
    lines = []
    for index, key in enumerate(keys):
        value = key["zoom"] if component == "size" else index / max(1, len(keys) - 1)
        flag = ", Flags = { Linear = true }" if key["easing"] == "linear" else ""
        lines.append(f"\t\t\t\t[{key['frame']}] = {{ {value:.12g}{flag} }},")
    return "\n".join(lines)


def _path_points(keys: list[dict]) -> str:
    points = []
    for key in keys:
        center = key["fusion_center"]
        points.append("\t\t\t\t\t\t\t{ Linear = true, X = %.12g, Y = %.12g, LX = 0, LY = 0, RX = 0, RY = 0 },"
                      % (center["x"] - 0.5, center["y"] - 0.5))
    return "\n".join(points if len(points) > 1 else points * 2)


def generate(package: Path, metadata: dict, animation: dict) -> Path:
    out, native = animation["output"], metadata["output"]
    source_aspect = native["width"] / native["height"]
    output_aspect = out["width"] / out["height"]
    max_view_width = min(1.0, output_aspect / source_aspect)
    keys = []
    for key in animation["keyframes"]:
        z = key.get("zoom") or max_view_width / key["view_width"]
        center = key["center"]
        keys.append({**key, "zoom": z, "fusion_center": {
            "x": 0.5 + (0.5 - center["x"]) * z,
            "y": 0.5 + (0.5 - center["y"]) * z}})
    duration, width, height = out["duration_frames"] - 1, native["width"], native["height"]
    tools = [f'''\t\tMap_Wide = Loader {{ NameSet = true, Clips = {{ Clip {{ ID = "Clip1", Filename = "{_lua_path(package / 'satellite_wide.png')}", Length = 1, GlobalEnd = {duration}, TrimOut = 0, Loop = 1 }} }}, ViewInfo = OperatorInfo {{ Pos = {{ -700, 0 }} }}, }},''']
    # Detail remains a raster layer, geographically placed over the wide map.
    factor = float(native["wide_factor"])
    tools.append(f'''\t\tMap_Detail = Loader {{ NameSet = true, Clips = {{ Clip {{ ID = "Clip1", Filename = "{_lua_path(package / 'satellite_detail.png')}", Length = 1, GlobalEnd = {duration}, TrimOut = 0, Loop = 1 }} }}, ViewInfo = OperatorInfo {{ Pos = {{ -700, 130 }} }}, }},
\t\tPlace_Detail = Transform {{ Inputs = {{ Size = Input {{ Value = {1 / factor:.12g}, }}, Input = Input {{ SourceOp = "Map_Detail", Source = "Output", }} }}, ViewInfo = OperatorInfo {{ Pos = {{ -480, 130 }} }}, }},''')
    layers = ['''\t\t\t\t["Layer1.Foreground"] = Input { SourceOp = "Place_Detail", Source = "Output", },
\t\t\t\tLayerName1 = Input { Value = "Detailed satellite", },''']
    for number, country in enumerate(metadata.get("countries", []), 2):
        iso = _name(country["iso3"])
        base = f"Country_{iso}"
        row = (number - 2) * 180
        geometry = _geometry(package, country)
        tools.append(_country_mask(base + "_Fill", geometry, metadata["wide"]["bbox_mercator"], width, height,
                                   pos=(-460, 300 + row)))
        tools.append(_country_mask(base + "_Border", geometry, metadata["wide"]["bbox_mercator"], width, height,
                                   outline=True, pos=(-460, 370 + row)))
        red, green, blue = _rgb(country.get("color", "#1689ff"))
        border_red, border_green, border_blue = _rgb(country.get("border_color", "#ffffff"))
        tools.append(f'''\t\t{base}_Fill = Background {{
\t\t\tNameSet = true,
\t\t\tInputs = {{ EffectMask = Input {{ SourceOp = "{base}_Fill_Mask", Source = "Mask", }}, GlobalOut = Input {{ Value = {duration}, }}, Width = Input {{ Value = {width}, }}, Height = Input {{ Value = {height}, }}, UseFrameFormatSettings = Input {{ Value = 1, }}, TopLeftRed = Input {{ Value = {red:.12g}, }}, TopLeftGreen = Input {{ Value = {green:.12g}, }}, TopLeftBlue = Input {{ Value = {blue:.12g}, }}, TopLeftAlpha = Input {{ Value = 1, }} }},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ -180, {300 + row} }} }},
\t\t}},
\t\t{base}_Border = Background {{
\t\t\tNameSet = true,
\t\t\tInputs = {{ EffectMask = Input {{ SourceOp = "{base}_Border_Mask", Source = "Mask", }}, GlobalOut = Input {{ Value = {duration}, }}, Width = Input {{ Value = {width}, }}, Height = Input {{ Value = {height}, }}, UseFrameFormatSettings = Input {{ Value = 1, }}, TopLeftRed = Input {{ Value = {border_red:.12g}, }}, TopLeftGreen = Input {{ Value = {border_green:.12g}, }}, TopLeftBlue = Input {{ Value = {border_blue:.12g}, }}, TopLeftAlpha = Input {{ Value = 1, }} }},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ -180, {370 + row} }} }},
\t\t}},''')
        fill_layer, border_layer = number * 2 - 2, number * 2 - 1
        layers.append(f'''\t\t\t\t["Layer{fill_layer}.Foreground"] = Input {{ SourceOp = "{base}_Fill", Source = "Output", }},
\t\t\t\tLayerName{fill_layer} = Input {{ Value = "{country['iso3']} vector fill", }},
\t\t\t\t["Layer{border_layer}.Foreground"] = Input {{ SourceOp = "{base}_Border", Source = "Output", }},
\t\t\t\tLayerName{border_layer} = Input {{ Value = "{country['iso3']} vector border", }},''')
    tools.append(f'''\t\tMap_Layers = MultiMerge {{
\t\t\tNameSet = true,
\t\t\tInputs = {{ Background = Input {{ SourceOp = "Map_Wide", Source = "Output", }},
{chr(10).join(layers)}
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ 120, 0 }} }},
\t\t}},''')
    tools.append(f'''\t\tMap_AnimationDisplacement = BezierSpline {{ KeyFrames = {{
{_key_lines(keys, 'displacement')}
\t\t\t}} }},
\t\tMap_AnimationSize = BezierSpline {{ KeyFrames = {{
{_key_lines(keys, 'size')}
\t\t\t}} }},
\t\tMap_AnimationPath = PolyPath {{ Inputs = {{ Displacement = Input {{ SourceOp = "Map_AnimationDisplacement", Source = "Value", }}, PolyLine = Input {{ Value = Polyline {{ Points = {{
{_path_points(keys)}
\t\t\t\t\t\t}} }}, }} }}, }},
\t\tMap_Animation = Transform {{ NameSet = true, Inputs = {{ Center = Input {{ SourceOp = "Map_AnimationPath", Source = "Position", }}, Size = Input {{ SourceOp = "Map_AnimationSize", Source = "Value", }}, Input = Input {{ SourceOp = "Map_Layers", Source = "Output", }} }}, ViewInfo = OperatorInfo {{ Pos = {{ 600, 0 }} }}, }},
\t\tMediaOut1 = MediaOut {{ Inputs = {{ Input = Input {{ SourceOp = "Map_Animation", Source = "Output", }} }}, ViewInfo = OperatorInfo {{ Pos = {{ 820, 0 }} }}, }},''')
    content = f'''Composition {{
\tCurrentTime = 0, RenderRange = {{ 0, {duration} }}, GlobalRange = {{ 0, {duration} }},
\tTools = {{
{chr(10).join(tools)}
\t}}
}}
'''
    fusion_dir = package / "fusion"
    fusion_dir.mkdir(exist_ok=True)
    versions = [int(m.group(1)) for path in fusion_dir.glob("scene_v*.comp")
                if (m := re.fullmatch(r"scene_v(\d+)\.comp", path.name))]
    target = fusion_dir / f"scene_v{max(versions, default=0) + 1:03d}.comp"
    target.write_text(content, encoding="utf-8")
    return target
