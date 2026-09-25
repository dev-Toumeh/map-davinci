"""Generate an editable 2D Fusion composition for a map-video shot.

Satellite imagery remains raster. Country highlights are native Fusion
MultiPoly masks built from saved GeoJSON points and composed with MultiMerge.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path
from .connection_geometry import connection_tools

R = 6378137.0

# These limits were visually validated against the historical-USA prototype.
# Other countries use the same cartographic budget so a newly added country
# cannot silently return a composition to tens of megabytes.
RING_LIMITS = {
    "country-usa": 20,
    "us-original-1783": 20,
    "louisiana-purchase-1803": 10,
    "florida-cession-1819": 15,
    "texas-annexation-1845": 5,
    "oregon-territory-1846": 5,
    "mexican-cession-1848": 5,
    "hawaii-annexation-1898": 10,
    "alaska-purchase-1867": 40,
}
DEFAULT_RING_LIMIT = 40
GEOMETRY_TOLERANCE_PX = 4.0


def _name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", value)


def _territory_base(iso3: str, child: dict) -> str:
    """Return a short, readable Fusion prefix without repeated country words."""
    iso = _name(iso3.upper())
    if child.get("category") == "country":
        return f"{iso}_Entire"
    if child.get("id") == "us-original-1783":
        return f"{iso}_Territory_1783"
    label = re.sub(r"_+", "_", _name(str(child.get("name") or child["id"]))).strip("_")
    label = re.sub(r"^(?:USA|US|U_S|United_States)_", "", label, flags=re.IGNORECASE)
    year = re.search(r"(?:^|[-_])(\d{4})(?:$|[-_])", str(child.get("id", "")))
    if year and year.group(1) not in label:
        label += "_" + year.group(1)
    return f"{iso}_{label}"


def _territory_label(child: dict) -> str:
    if child.get("id") == "us-original-1783":
        return "Territory recognized in 1783"
    return str(child.get("name") or child.get("id") or "Territory")


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
    from core import exporter
    return exporter.get_geometry(country["iso3"])


def _child_geometry(package: Path, country: dict, child: dict) -> dict:
    if child.get("category") == "country":
        return _geometry(package, country)
    relative = child.get("geometry_file")
    if not relative:
        raise ValueError(f"Save sub-territory geometry before generating Fusion: {child.get('name')}")
    path = (package / relative).resolve()
    if package.resolve() not in path.parents or not path.is_file():
        raise ValueError(f"Missing package-local geometry for {child.get('name')}")
    return json.loads(path.read_text(encoding="utf-8"))["geometry"]


def _project_ring(ring: list[tuple[float, float]], bbox: dict,
                  x_scale: float = 1.0, y_scale: float = 1.0) -> list[tuple[float, float]]:
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
        px = ((x - minx) / (maxx - minx) - 0.5) * x_scale
        py = (0.5 - (maxy - y) / (maxy - miny)) * y_scale
        points.append((px, py))
    return points


def _point_distance(point: tuple[float, float], start: tuple[float, float],
                    end: tuple[float, float]) -> float:
    dx, dy = end[0] - start[0], end[1] - start[1]
    if dx == 0 and dy == 0:
        return math.hypot(point[0] - start[0], point[1] - start[1])
    return abs(dy * point[0] - dx * point[1] + end[0] * start[1] - end[1] * start[0]) / math.hypot(dx, dy)


def _rdp(points: list[tuple[float, float]], tolerance: float) -> list[tuple[float, float]]:
    if len(points) <= 2 or tolerance <= 0:
        return points
    keep = {0, len(points) - 1}
    stack = [(0, len(points) - 1)]
    while stack:
        first, last = stack.pop()
        largest, split = tolerance, None
        for index in range(first + 1, last):
            error = _point_distance(points[index], points[first], points[last])
            if error > largest:
                largest, split = error, index
        if split is not None:
            keep.add(split)
            stack.extend(((first, split), (split, last)))
    return [points[index] for index in sorted(keep)]


def _reduce_ring(points: list[tuple[float, float]], tolerance: float) -> list[tuple[float, float]]:
    """Reduce both arcs of a closed ring without collapsing a polygon."""
    if len(points) <= 3 or tolerance <= 0:
        return points
    second = max(range(len(points)), key=lambda index:
                 (points[index][0] - points[0][0]) ** 2 +
                 (points[index][1] - points[0][1]) ** 2)
    first = max(range(len(points)), key=lambda index:
                (points[index][0] - points[second][0]) ** 2 +
                (points[index][1] - points[second][1]) ** 2)
    if first > second:
        first, second = second, first
    reduced = (_rdp(points[first:second + 1], tolerance)[:-1] +
               _rdp(points[second:] + points[:first + 1], tolerance)[:-1])
    return reduced if len(reduced) >= 3 else points


def _ring_area(points: list[tuple[float, float]]) -> float:
    return abs(sum(
        points[index][0] * points[(index + 1) % len(points)][1] -
        points[(index + 1) % len(points)][0] * points[index][1]
        for index in range(len(points))
    ) / 2)


def _prepared_rings(geometry: dict, bbox: dict, x_scale: float, y_scale: float,
                    tolerance: float = 0.0,
                    ring_limit: int | None = None) -> list[tuple[int, list[tuple[float, float]]]]:
    rings = []
    for polygon in _polygons(geometry):
        for index, ring in enumerate(polygon):
            points = _project_ring(ring, bbox, x_scale, y_scale)
            if len(points) >= 3:
                rings.append((1 if index == 0 else -1, points))
    if ring_limit is not None and len(rings) > ring_limit:
        rings = sorted(rings, key=lambda item: _ring_area(item[1]), reverse=True)[:ring_limit]
    return [(level, _reduce_ring(points, tolerance)) for level, points in rings]


def _polyline(points: list[tuple[float, float]]) -> str:
    return " ".join(
        f"{{ Linear = true, X = {x:.12g}, Y = {y:.12g}, LX = 0, LY = 0, RX = 0, RY = 0 }},"
        for x, y in points)


def _country_mask(name: str, geometry: dict, wide_bbox: dict, width: int, height: int,
                  *, outline: bool = False, pos: tuple[int, int] = (0, 0),
                  x_scale: float = 1.0, y_scale: float = 1.0,
                  prepared_rings: list[tuple[int, list[tuple[float, float]]]] | None = None,
                  instance_source: str | None = None,
                  border_width: float = 0.0005) -> str:
    rings = prepared_rings or _prepared_rings(
        geometry, wide_bbox, x_scale, y_scale)
    if not rings:
        raise ValueError(f"{name} has no valid polygon rings")
    inputs, definitions, order = [], [], []
    for index, (level, points) in enumerate(rings, 1):
        order.append(str(index))
        outline_inputs = (f'\n\t\t\t\t["PolyMask{index}.Solid"] = Input {{ Value = 0, }},'
                          f'\n\t\t\t\t["PolyMask{index}.BorderWidth"] = Input {{ Value = {border_width:.12g}, }},') if outline else ""
        geometry_inputs = "" if instance_source else f'''\t\t\t\t["PolyMask{index}.Level"] = Input {{ Value = {level}, }},
\t\t\t\t["PolyMask{index}.Filter"] = Input {{ Value = FuID {{ "Fast Gaussian" }}, }},
\t\t\t\t["PolyMask{index}.Center"] = Input {{ Value = {{ 0.5, 0.5 }}, }},
\t\t\t\t["PolyMask{index}.Size"] = Input {{ Value = 1, }},
\t\t\t\t["PolyMask{index}.Polyline"] = Input {{ Value = Polyline {{ Closed = true, Points = {{ {_polyline(points)} }} }}, }},
\t\t\t\t["PolyMask{index}.Polyline2"] = Input {{ Value = Polyline {{ }}, Disabled = true, }},'''
        inputs.append(geometry_inputs + outline_inputs)
        definitions.append(f"\t\t\tPolyMask{index} = PolyMaskInputs {{ DrawMode = \"InsertAndModify\", DrawMode2 = \"InsertAndModify\" }},")
    source = f'\n\t\t\tSourceOp = "{instance_source}",' if instance_source else ""
    base_inputs = "" if instance_source else f'''\n\t\t\t\tMaskWidth = Input {{ Value = {width}, }}, MaskHeight = Input {{ Value = {height}, }},
\t\t\t\tPixelAspect = Input {{ Value = {{ 1, 1 }}, }}, UseFrameFormatSettings = Input {{ Value = 0, }},
\t\t\t\tClippingMode = Input {{ Value = FuID {{ "None" }}, }},
\t\t\t\tPolyOrder = Input {{ Value = ScriptVal {{ {{ [0] = {', '.join(order)} }} }}, }},'''
    return f'''\t\t{name}_Mask = MultiPoly {{
\t\t\tNameSet = true,
\t\t\t{source}
\t\t\tInputs = {{{base_inputs}
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


def _visibility_spline(name: str, start: int | None, end: int | None,
                       last_frame: int, fps: int) -> tuple[str, str]:
    """Return a Fusion visibility spline and its Input value."""
    if start is None and end is None:
        return "", "Input { Value = 1, }"
    fade = max(1, round(fps * .25))
    if start is not None and end is not None:
        fade = min(fade, max(1, (end - start) // 2))
    keys: dict[int, float] = {0: 1.0 if start is None else 0.0,
                              last_frame: 1.0 if end is None else 0.0}
    if start is not None:
        keys[start] = 0.0
        keys[min(last_frame, start + fade)] = 1.0
    if end is not None:
        keys[max(0, end - fade)] = 1.0
        keys[end] = 0.0
    lines = "\n".join(
        f'\t\t\t\t[{frame}] = {{ {value:.12g}, Flags = {{ Linear = true }} }},'
        for frame, value in sorted(keys.items()))
    node = f'''\t\t{name} = BezierSpline {{ KeyFrames = {{
{lines}
\t\t\t}} }},'''
    return node, f'Input {{ Value = 0, SourceOp = "{name}", Source = "Value", }}'


def _switch_tool(name: str, inputs: list[tuple[str, str]], pos: tuple[int, int]) -> str:
    """Serialize a native Fusion Switch with named image inputs."""
    if not inputs:
        raise ValueError(f"{name} requires at least one input")
    lines = [
        f"\t\t{name} = Switch {{",
        "\t\t\tNameSet = true,",
        "\t\t\tInputs = {",
        f"\t\t\t\tNumberOfInputs = Input {{ Value = {len(inputs)}, }},",
    ]
    for index, (label, source) in enumerate(inputs, 1):
        safe_label = str(label).replace('"', "'")
        lines.extend([
            f'\t\t\t\tInput{index - 1} = Input {{ SourceOp = "{source}", Source = "Output", }},',
            f'\t\t\t\tName{index - 1} = Input {{ Value = "{safe_label}", }},',
        ])
    lines.extend([
        "\t\t\t},",
        f"\t\t\tViewInfo = OperatorInfo {{ Pos = {{ {pos[0]}, {pos[1]} }} }},",
        "\t\t},",
    ])
    return "\n".join(lines)


def _fit_camera_handles(samples: list[dict], start: dict, end: dict,
                        component: str) -> tuple[float, float]:
    """Fit a cubic segment and constrain its handles to avoid reversals."""
    def value(key: dict) -> float:
        return key["zoom"] if component == "size" else key["displacement"]
    y0, y3 = value(start), value(end)
    if abs(y3 - y0) < 1e-12:
        return y0, y3
    a = b = c = d = e = 0.0
    first, last = start["frame"], end["frame"]
    offset = samples[0]["frame"]
    for sample in samples[first - offset + 1:last - offset]:
        t = (sample["frame"] - first) / (last - first)
        u = 1 - t
        b1, b2 = 3 * u * u * t, 3 * u * t * t
        residual = value(sample) - y0 * u ** 3 - y3 * t ** 3
        a += b1 * b1
        b += b1 * b2
        c += b2 * b2
        d += b1 * residual
        e += b2 * residual
    det = a * c - b * b
    if abs(det) < 1e-15:
        return y0 + (y3 - y0) / 3, y0 + (y3 - y0) * 2 / 3
    low, high = sorted((y0, y3))
    return (max(low, min(high, (d * c - e * b) / det)),
            max(low, min(high, (e * a - d * b) / det)))


def _camera_timing_keys(samples: list[dict], authored_frames: set[int]) -> list[dict]:
    """Keep authored keys; add a few only where a cubic is visibly inaccurate.

    The dense samples remain the spatial path and the input to connection
    geometry. Only the editable camera timing curves are simplified.
    """
    offset = samples[0]["frame"]
    retained = {frame - offset for frame in authored_frames}

    def split(i: int, j: int) -> None:
        if j - i < 2:
            return
        handles = {part: _fit_camera_handles(samples, samples[i], samples[j], part)
                   for part in ("size", "displacement")}
        travel = abs(samples[j]["displacement"] - samples[i]["displacement"])
        largest, worst = 0.0, None
        for k in range(i + 1, j):
            t, u = (k - i) / (j - i), (j - k) / (j - i)
            score = 0.0
            for part in ("size", "displacement"):
                field = "zoom" if part == "size" else "displacement"
                right, left = handles[part]
                predicted = (samples[i][field] * u**3 + 3 * right * u*u*t +
                             3 * left * u*t*t + samples[j][field] * t**3)
                allowed = .02 * samples[k]["zoom"] if part == "size" else max(.001, .01 * travel)
                score = max(score, abs(predicted - samples[k][field]) / allowed)
            if score > largest:
                largest, worst = score, k
        if largest > 1 and worst is not None:
            retained.add(worst)
            split(i, worst)
            split(worst, j)

    anchors = sorted(retained)
    for i, j in zip(anchors, anchors[1:]):
        split(i, j)
    return [samples[i] for i in sorted(retained)]


def _key_lines(keys: list[dict], samples: list[dict], component: str, multiplier: float = 1.0) -> str:
    def value(key: dict) -> float:
        raw = key["zoom"] if component == "size" else key["displacement"]
        return raw * multiplier
    handles = {}
    for a, b in zip(keys, keys[1:]):
        right, left = _fit_camera_handles(samples, a, b, component)
        right, left = right * multiplier, left * multiplier
        third = (b["frame"] - a["frame"]) / 3
        handles[a["frame"], "RH"] = (a["frame"] + third, right)
        handles[b["frame"], "LH"] = (b["frame"] - third, left)
    lines = []
    for key in keys:
        frame = key["frame"]
        parts = [f"{value(key):.12g}"]
        for side in ("LH", "RH"):
            if (frame, side) in handles:
                x, y = handles[frame, side]
                parts.append(f"{side} = {{ {x:.12g}, {y:.12g} }}")
        lines.append(f"\t\t\t\t[{frame}] = {{ {', '.join(parts)} }},")
    return "\n".join(lines)


def _path_points(keys: list[dict], x_scale: float = 1.0, y_scale: float = 1.0) -> str:
    points = []
    previous = None
    for key in keys:
        center = key.get("fusion_path") or {
            "x": key["fusion_center"]["x"] - 0.5,
            "y": key["fusion_center"]["y"] - 0.5,
        }
        if center == previous:
            continue
        previous = center
        points.append("\t\t\t\t\t\t\t{ Linear = true, X = %.12g, Y = %.12g, LX = 0, LY = 0, RX = 0, RY = 0 },"
                      % (center["x"] * x_scale, center["y"] * y_scale))
    return "\n".join(points if len(points) > 1 else points * 2)


def _camera_samples(animation: dict, native: dict) -> list[dict]:
    """Evaluate the browser camera before converting to source-space Transform values.

    The browser interpolates view width, not its reciprocal (Fusion Size).
    Sample every output frame so both linear and smooth shots match at render
    times. Linear Fusion segments also avoid implicit Bezier overshoot.
    """
    out = animation["output"]
    maximum = min(1.0, (out["width"] / out["height"]) /
                  (native["width"] / native["height"]))
    authored = sorted(animation["keyframes"], key=lambda key: key["frame"])

    def width(key: dict) -> float:
        return key.get("view_width") or maximum / key.get("zoom", 1.0)

    def offset(key: dict) -> tuple[float, float]:
        scale = out["width"] / native["width"] / width(key)
        return ((0.5 - key["center"]["x"]) * scale,
                (key["center"]["y"] - 0.5) * scale)

    def correction(key: dict) -> tuple[float, float]:
        if "fusion_path" not in key:
            return (0.0, 0.0)
        x, y = offset(key)
        return (key["fusion_path"]["x"] - x, key["fusion_path"]["y"] - y)

    samples = []
    index = 0
    for frame in range(authored[0]["frame"], authored[-1]["frame"] + 1):
        while index < len(authored) - 1 and frame > authored[index + 1]["frame"]:
            index += 1
        a, b = authored[index], authored[min(index + 1, len(authored) - 1)]
        t = (frame - a["frame"]) / (b["frame"] - a["frame"]) if b["frame"] != a["frame"] else 0.0
        if b.get("easing", "smooth") == "smooth":
            t = t * t * (3 - 2 * t)
        w = width(a) + (width(b) - width(a)) * t
        x = a["center"]["x"] + (b["center"]["x"] - a["center"]["x"]) * t
        y = a["center"]["y"] + (b["center"]["y"] - a["center"]["y"]) * t
        scale = out["width"] / native["width"] / w
        ca, cb = correction(a), correction(b)
        path = {"x": (0.5 - x) * scale + ca[0] + (cb[0] - ca[0]) * t,
                "y": (y - 0.5) * scale + ca[1] + (cb[1] - ca[1]) * t}
        samples.append({"frame": frame, "zoom": scale, "fusion_path": path})
    lengths = [0.0]
    for previous, current in zip(samples, samples[1:]):
        p, q = previous["fusion_path"], current["fusion_path"]
        lengths.append(lengths[-1] + math.hypot(q["x"] - p["x"], q["y"] - p["y"]))
    for sample, length in zip(samples, lengths):
        sample["displacement"] = length / lengths[-1] if lengths[-1] else 0.0
    return samples




def generate(package: Path, metadata: dict, animation: dict) -> Path:
    out, native = animation["output"], metadata["output"]
    samples = _camera_samples(animation, native)
    authored_frames = {key["frame"] for key in animation["keyframes"]}
    keys = _camera_timing_keys(samples, authored_frames)
    duration, width, height = out["duration_frames"] - 1, native["width"], native["height"]
    output_width, output_height = out["width"], out["height"]
    vector_width, vector_height = max(width, output_width), max(height, output_height)
    vector_x_scale, vector_y_scale = width / vector_width, height / vector_height
    vector_controller = ""
    if animation.get("connections"):
        vector_lengths = [0.0]
        for previous, current in zip(samples, samples[1:]):
            dx = ((current["fusion_path"]["x"] - previous["fusion_path"]["x"])
                  * vector_x_scale)
            dy = ((current["fusion_path"]["y"] - previous["fusion_path"]["y"])
                  * vector_y_scale)
            vector_lengths.append(vector_lengths[-1] + math.hypot(dx, dy))
        vector_total = vector_lengths[-1]
        vector_displacement_keys = "\n".join(
            f'\t\t\t\t[{sample["frame"]}] = {{ {length / vector_total if vector_total else 0:.12g}, Flags = {{ Linear = true }} }},'
            for sample, length in zip(samples, vector_lengths))
        vector_controller = f'''\t\tVector_AnimationDisplacement = BezierSpline {{ KeyFrames = {{
{vector_displacement_keys}
\t\t\t}} }},
\t\tVector_AnimationPath = PolyPath {{ Inputs = {{ Displacement = Input {{ SourceOp = "Vector_AnimationDisplacement", Source = "Value", }}, PolyLine = Input {{ Value = Polyline {{ Points = {{
{_path_points(samples, vector_x_scale, vector_y_scale)}
\t\t\t\t\t\t}} }}, }} }}, }},'''
    tools = [f'''\t\tMap_Wide = Loader {{ NameSet = true, Clips = {{ Clip {{ ID = "Clip1", Filename = "{_lua_path(package / 'satellite_wide.png')}", Length = 1, GlobalEnd = {duration}, TrimOut = 0, Loop = 1 }} }}, ViewInfo = OperatorInfo {{ Pos = {{ -700, 0 }} }}, }},''']
    # Detail remains a raster layer, geographically placed over the wide map.
    factor = float(native["wide_factor"])
    tools.append(f'''\t\tMap_Detail = Loader {{ NameSet = true, Clips = {{ Clip {{ ID = "Clip1", Filename = "{_lua_path(package / 'satellite_detail.png')}", Length = 1, GlobalEnd = {duration}, TrimOut = 0, Loop = 1 }} }}, ViewInfo = OperatorInfo {{ Pos = {{ -700, 130 }} }}, }},
\t\tPlace_Detail = Transform {{ Inputs = {{ Size = Input {{ Value = {1 / factor:.12g}, }}, Input = Input {{ SourceOp = "Map_Detail", Source = "Output", }} }}, ViewInfo = OperatorInfo {{ Pos = {{ -480, 130 }} }}, }},''')
    vector_layers = []
    country_final_wide_layers = []
    country_final_detail_layers = []
    country_edit_inputs: list[tuple[str, str]] = []
    countries = {country["iso3"]: country for country in metadata.get("countries", [])}
    groups = animation.get("region_groups")
    if groups is None:
        groups = [{"iso3": country["iso3"], "start_frame": None, "end_frame": None,
                   "children": [{"id": f"country-{country['iso3'].lower()}",
                                  "name": "Entire country", "category": "country",
                                  "start_frame": None, "end_frame": None}]}
                  for country in metadata.get("countries", [])]
    wide_bbox = metadata.get("wide", {}).get("bbox_mercator")
    if not wide_bbox:
        wide_bbox = {"minx": 0, "miny": 0, "maxx": 1, "maxy": 1}
    detail_bbox = metadata.get("detail", {}).get("bbox_mercator")
    if not detail_bbox:
        center_x = (wide_bbox["minx"] + wide_bbox["maxx"]) / 2
        center_y = (wide_bbox["miny"] + wide_bbox["maxy"]) / 2
        half_width = (wide_bbox["maxx"] - wide_bbox["minx"]) / (2 * factor)
        half_height = (wide_bbox["maxy"] - wide_bbox["miny"]) / (2 * factor)
        detail_bbox = {"minx": center_x - half_width, "miny": center_y - half_height,
                       "maxx": center_x + half_width, "maxy": center_y + half_height}
    static_tolerance = GEOMETRY_TOLERANCE_PX / max(width, height)
    row_cursor = 360
    for group_number, group in enumerate(groups, 1):
        country = countries[group["iso3"]]
        iso = _name(country["iso3"])
        group_base = iso
        red, green, blue = _rgb(country.get("color", "#1689ff"))
        border_red, border_green, border_blue = _rgb(country.get("border_color", "#ffffff"))
        wide_child_layers = []
        detail_child_layers = []
        parent_node, parent_input = _visibility_spline(
            group_base + "_Visibility", group.get("start_frame"), group.get("end_frame"),
            duration, int(out["fps"]))
        if parent_node:
            tools.append(parent_node)
        tools.append(f'''\t\t{group_base}_Wide_Canvas = Background {{ NameSet = true, Inputs = {{ GlobalOut = Input {{ Value = {duration}, }}, Width = Input {{ Value = {width}, }}, Height = Input {{ Value = {height}, }}, UseFrameFormatSettings = Input {{ Value = 0, }}, TopLeftAlpha = Input {{ Value = 0, }} }}, ViewInfo = OperatorInfo {{ Pos = {{ -1830, {row_cursor} }} }}, }},
\t\t{group_base}_Detail_Canvas = Background {{ NameSet = true, Inputs = {{ GlobalOut = Input {{ Value = {duration}, }}, Width = Input {{ Value = {width}, }}, Height = Input {{ Value = {height}, }}, UseFrameFormatSettings = Input {{ Value = 0, }}, TopLeftAlpha = Input {{ Value = 0, }} }}, ViewInfo = OperatorInfo {{ Pos = {{ -1830, {row_cursor + 120} }} }}, }},''')
        for child_number, child in enumerate(group.get("children", []), 1):
            child_base = _territory_base(group["iso3"], child)
            geometry = _child_geometry(package, country, child)
            row = row_cursor + (child_number - 1) * 240
            ring_limit = RING_LIMITS.get(child["id"], DEFAULT_RING_LIMIT)
            wide_rings = _prepared_rings(
                geometry, wide_bbox, 1.0, 1.0, static_tolerance, ring_limit)
            detail_rings = _prepared_rings(
                geometry, detail_bbox, 1.0, 1.0, static_tolerance, ring_limit)
            for resolution, bbox, rings, border_width, y_offset in (
                    ("Wide", wide_bbox, wide_rings, 0.0005, 0),
                    ("Detail", detail_bbox, detail_rings, 0.0005 * factor, 120)):
                prefix = f"{child_base}_{resolution}"
                tools.append(_country_mask(
                    prefix + "_Fill", geometry, bbox, width, height,
                    pos=(-1600, row + y_offset), prepared_rings=rings))
                tools.append(_country_mask(
                    prefix + "_Border", geometry, bbox, width, height,
                    outline=True, pos=(-1370, row + y_offset),
                    prepared_rings=rings, instance_source=prefix + "_Fill_Mask",
                    border_width=border_width))
            visibility_node, visibility_input = _visibility_spline(
                child_base + "_Visibility", child.get("start_frame"), child.get("end_frame"),
                duration, int(out["fps"]))
            if visibility_node:
                tools.append(visibility_node)
            for resolution, y_offset in (("Wide", 0), ("Detail", 120)):
                prefix = f"{child_base}_{resolution}"
                tools.append(f'''\t\t{prefix}_Fill = Background {{
\t\t\tNameSet = true,
\t\t\tInputs = {{ EffectMask = Input {{ SourceOp = "{prefix}_Fill_Mask", Source = "Mask", }}, GlobalOut = Input {{ Value = {duration}, }}, Width = Input {{ Value = {width}, }}, Height = Input {{ Value = {height}, }}, UseFrameFormatSettings = Input {{ Value = 0, }}, TopLeftRed = Input {{ Value = {red:.12g}, }}, TopLeftGreen = Input {{ Value = {green:.12g}, }}, TopLeftBlue = Input {{ Value = {blue:.12g}, }}, TopLeftAlpha = {visibility_input} }},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ -1140, {row + y_offset} }} }},
\t\t}},
\t\t{prefix}_Border = Background {{
\t\t\tNameSet = true,
\t\t\tInputs = {{ EffectMask = Input {{ SourceOp = "{prefix}_Border_Mask", Source = "Mask", }}, GlobalOut = Input {{ Value = {duration}, }}, Width = Input {{ Value = {width}, }}, Height = Input {{ Value = {height}, }}, UseFrameFormatSettings = Input {{ Value = 0, }}, TopLeftRed = Input {{ Value = {border_red:.12g}, }}, TopLeftGreen = Input {{ Value = {border_green:.12g}, }}, TopLeftBlue = Input {{ Value = {border_blue:.12g}, }}, TopLeftAlpha = {visibility_input} }},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ -910, {row + y_offset} }} }},
\t\t}},''')
            fill_layer, border_layer = child_number * 2 - 1, child_number * 2
            safe_name = _territory_label(child).replace('"', "'")
            for resolution, layers in (("Wide", wide_child_layers),
                                       ("Detail", detail_child_layers)):
                prefix = f"{child_base}_{resolution}"
                layers.append(f'''\t\t\t\t["Layer{fill_layer}.Foreground"] = Input {{ SourceOp = "{prefix}_Fill", Source = "Output", }},
\t\t\t\tLayerName{fill_layer} = Input {{ Value = "{safe_name} {resolution.lower()} fill", }},
\t\t\t\t["Layer{border_layer}.Foreground"] = Input {{ SourceOp = "{prefix}_Border", Source = "Output", }},
\t\t\t\tLayerName{border_layer} = Input {{ Value = "{safe_name} {resolution.lower()} border", }},''')
            edit_base = f"Edit_{child_base}"
            tools.append(f'''\t\t{edit_base}_Wide_Composite = MultiMerge {{ NameSet = true, Inputs = {{ Background = Input {{ SourceOp = "{group_base}_Wide_Canvas", Source = "Output", }}, ["Layer1.Foreground"] = Input {{ SourceOp = "{child_base}_Wide_Fill", Source = "Output", }}, ["Layer2.Foreground"] = Input {{ SourceOp = "{child_base}_Wide_Border", Source = "Output", }} }}, ViewInfo = OperatorInfo {{ Pos = {{ -670, {row} }} }}, }},
\t\t{edit_base}_Wide_Gate = Merge {{ NameSet = true, Inputs = {{ Background = Input {{ SourceOp = "{group_base}_Wide_Canvas", Source = "Output", }}, Foreground = Input {{ SourceOp = "{edit_base}_Wide_Composite", Source = "Output", }}, Blend = {parent_input} }}, ViewInfo = OperatorInfo {{ Pos = {{ -440, {row} }} }}, }},
\t\t{edit_base}_Detail_Composite = MultiMerge {{ NameSet = true, Inputs = {{ Background = Input {{ SourceOp = "{group_base}_Detail_Canvas", Source = "Output", }}, ["Layer1.Foreground"] = Input {{ SourceOp = "{child_base}_Detail_Fill", Source = "Output", }}, ["Layer2.Foreground"] = Input {{ SourceOp = "{child_base}_Detail_Border", Source = "Output", }} }}, ViewInfo = OperatorInfo {{ Pos = {{ -670, {row + 120} }} }}, }},
\t\t{edit_base}_Detail_Gate = Merge {{ NameSet = true, Inputs = {{ Background = Input {{ SourceOp = "{group_base}_Detail_Canvas", Source = "Output", }}, Foreground = Input {{ SourceOp = "{edit_base}_Detail_Composite", Source = "Output", }}, Blend = {parent_input} }}, ViewInfo = OperatorInfo {{ Pos = {{ -440, {row + 120} }} }}, }},
\t\t{edit_base}_Detail_Placed = Transform {{ NameSet = true, Inputs = {{ Size = Input {{ Value = {1 / factor:.12g}, }}, Input = Input {{ SourceOp = "{edit_base}_Detail_Gate", Source = "Output", }} }}, ViewInfo = OperatorInfo {{ Pos = {{ -210, {row + 120} }} }}, }},
\t\t{edit_base}_Combined_Layers = MultiMerge {{ NameSet = true, Inputs = {{ Background = Input {{ SourceOp = "{edit_base}_Wide_Gate", Source = "Output", }}, ["Layer1.Foreground"] = Input {{ SourceOp = "{edit_base}_Detail_Placed", Source = "Output", }}, LayerName1 = Input {{ Value = "{safe_name} detail", }} }}, ViewInfo = OperatorInfo {{ Pos = {{ 20, {row + 60} }} }}, }},''')
            country_edit_inputs.append((f"{group['iso3']} - {safe_name}", edit_base + "_Combined_Layers"))
        # Keep the group output in its own columns.  Wide and detail occupy
        # separate rows so the Flow remains readable even with many regions.
        for resolution, layers, y_offset in (("Wide", wide_child_layers, 0),
                                              ("Detail", detail_child_layers, 120)):
            tools.append(f'''\t\t{group_base}_{resolution}_Regions = MultiMerge {{
\t\t\tNameSet = true, Inputs = {{ Background = Input {{ SourceOp = "{group_base}_{resolution}_Canvas", Source = "Output", }},
{chr(10).join(layers)}
\t\t\t}}, ViewInfo = OperatorInfo {{ Pos = {{ 300, {row_cursor + y_offset} }} }},
\t\t}},
\t\t{group_base}_{resolution}_Gate = Merge {{ NameSet = true, Inputs = {{ Background = Input {{ SourceOp = "{group_base}_{resolution}_Canvas", Source = "Output", }}, Foreground = Input {{ SourceOp = "{group_base}_{resolution}_Regions", Source = "Output", }}, Blend = {parent_input} }}, ViewInfo = OperatorInfo {{ Pos = {{ 530, {row_cursor + y_offset} }} }}, }},''')
        country_final_wide_layers.append(f'''\t\t\t\t["Layer{group_number}.Foreground"] = Input {{ SourceOp = "{group_base}_Wide_Gate", Source = "Output", }},
\t\t\t\tLayerName{group_number} = Input {{ Value = "{group['iso3']} wide region group", }},''')
        country_final_detail_layers.append(f'''\t\t\t\t["Layer{group_number}.Foreground"] = Input {{ SourceOp = "{group_base}_Detail_Gate", Source = "Output", }},
\t\t\t\tLayerName{group_number} = Input {{ Value = "{group['iso3']} detail region group", }},''')
        row_cursor += max(360, len(group.get("children", [])) * 240 + 180)
    if country_edit_inputs:
        first_group_base = _name(groups[0]["iso3"])
        tools.append(f'''\t\tCountry_Final_Wide_Layers = MultiMerge {{ NameSet = true, Inputs = {{ Background = Input {{ SourceOp = "{first_group_base}_Wide_Canvas", Source = "Output", }},
{chr(10).join(country_final_wide_layers)}
\t\t\t}}, ViewInfo = OperatorInfo {{ Pos = {{ 780, 360 }} }}, }},
\t\tCountry_Final_Detail_Layers = MultiMerge {{ NameSet = true, Inputs = {{ Background = Input {{ SourceOp = "{first_group_base}_Detail_Canvas", Source = "Output", }},
{chr(10).join(country_final_detail_layers)}
\t\t\t}}, ViewInfo = OperatorInfo {{ Pos = {{ 780, 480 }} }}, }},
\t\tCountry_Final_Detail_Placed = Transform {{ NameSet = true, Inputs = {{ Size = Input {{ Value = {1 / factor:.12g}, }}, Input = Input {{ SourceOp = "Country_Final_Detail_Layers", Source = "Output", }} }}, ViewInfo = OperatorInfo {{ Pos = {{ 1010, 480 }} }}, }},
\t\tCountry_Final_Layers = MultiMerge {{ NameSet = true, Inputs = {{ Background = Input {{ SourceOp = "Country_Final_Wide_Layers", Source = "Output", }}, ["Layer1.Foreground"] = Input {{ SourceOp = "Country_Final_Detail_Placed", Source = "Output", }}, LayerName1 = Input {{ Value = "Detail territory polygons", }} }}, ViewInfo = OperatorInfo {{ Pos = {{ 1240, 420 }} }}, }},''')
        tools.append(_switch_tool("Country_Edit_Switch", country_edit_inputs, (1470, 540)))
        tools.append(_switch_tool("Country_Mode_Switch", [
            ("EDIT MODE - selected country or territory", "Country_Edit_Switch"),
            ("FINAL RENDER - all countries and territories", "Country_Final_Layers"),
        ], (1700, 480)))
        tools.append('''\t\tMap_Country_Layers = MultiMerge {
\t\t\tNameSet = true,
\t\t\tInputs = { Background = Input { SourceOp = "Map_Raster_Layers", Source = "Output", },
\t\t\t\t["Layer1.Foreground"] = Input { SourceOp = "Country_Mode_Switch", Source = "Output", },
\t\t\t\tLayerName1 = Input { Value = "Country performance mode", },
\t\t\t}, ViewInfo = OperatorInfo { Pos = { 1930, 420 } },
\t\t},''')
        map_animation_source = "Map_Country_Layers"
        layer_number = 1
    else:
        map_animation_source = "Map_Raster_Layers"
        layer_number = 1
    incomplete = [connection["name"] for connection in animation.get("connections", [])
                  if not connection.get("start") or not connection.get("end")]
    if incomplete:
        raise ValueError("Complete or delete these connections before generating Fusion: " + ", ".join(incomplete))
    for number, connection in enumerate(animation.get("connections", [])):
        connection_nodes, connection_layers = connection_tools(
            connection, width, height, duration, row_cursor + number * 180,
            layer_number, samples, out, vector_width, vector_height)
        tools.append(connection_nodes)
        vector_layers.append(connection_layers)
        layer_number += 2 if connection['line_style'] == 'solid' and connection['arrowhead'] else 1
    tools.append(f'''\t\tMap_Raster_Layers = MultiMerge {{
\t\t\tNameSet = true,
\t\t\tInputs = {{ Background = Input {{ SourceOp = "Map_Wide", Source = "Output", }},
\t\t\t\t["Layer1.Foreground"] = Input {{ SourceOp = "Place_Detail", Source = "Output", }},
\t\t\t\tLayerName1 = Input {{ Value = "Detailed satellite", }},
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ 120, 0 }} }},
\t\t}},''')
    tools.append(f'''\t\tMap_AnimationDisplacement = BezierSpline {{ KeyFrames = {{
{_key_lines(keys, samples, 'displacement')}
\t\t\t}} }},
\t\tMap_AnimationSize = BezierSpline {{ KeyFrames = {{
{_key_lines(keys, samples, 'size')}
\t\t\t}} }},
\t\tMap_AnimationPath = PolyPath {{ Inputs = {{ Displacement = Input {{ SourceOp = "Map_AnimationDisplacement", Source = "Value", }}, PolyLine = Input {{ Value = Polyline {{ Points = {{
{_path_points(samples)}
\t\t\t\t\t\t}} }}, }} }}, }},
{vector_controller}
\t\tMap_Animation = Transform {{ NameSet = true, Inputs = {{ Center = Input {{ SourceOp = "Map_AnimationPath", Source = "Position", }}, Size = Input {{ SourceOp = "Map_AnimationSize", Source = "Value", }}, ClippingMode = Input {{ Value = FuID {{ "None" }}, }}, Input = Input {{ SourceOp = "{map_animation_source}", Source = "Output", }} }}, ViewInfo = OperatorInfo {{ Pos = {{ 2160, 0 }} }}, }},
\t\tOutput_Canvas = Background {{ NameSet = true, Inputs = {{ GlobalOut = Input {{ Value = {duration}, }}, Width = Input {{ Value = {output_width}, }}, Height = Input {{ Value = {output_height}, }}, PixelAspect = Input {{ Value = {{ 1, 1 }}, }}, UseFrameFormatSettings = Input {{ Value = 0, }}, TopLeftAlpha = Input {{ Value = 0, }} }}, ViewInfo = OperatorInfo {{ Pos = {{ 2160, 130 }} }}, }},
\t\tFinal_Composite = Merge {{ NameSet = true, Inputs = {{ Background = Input {{ SourceOp = "Output_Canvas", Source = "Output", }}, Foreground = Input {{ SourceOp = "Map_Animation", Source = "Output", }} }}, ViewInfo = OperatorInfo {{ Pos = {{ 2390, 0 }} }}, }},
\t\tVector_Layers = MultiMerge {{ NameSet = true, Inputs = {{ Background = Input {{ SourceOp = "Final_Composite", Source = "Output", }},
{chr(10).join(vector_layers)}
\t\t}}, ViewInfo = OperatorInfo {{ Pos = {{ 2620, 0 }} }}, }},
\t\tMediaOut1 = MediaOut {{ Inputs = {{ Input = Input {{ SourceOp = "Vector_Layers", Source = "Output", }} }}, ViewInfo = OperatorInfo {{ Pos = {{ 2850, 0 }} }}, }},''')
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
