"""Generate an editable 2D Fusion composition for a map-video shot.

Satellite imagery remains raster. Country highlights remain native Fusion
Shape geometry until the final camera-aware render.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path
from core import package_layout
from . import closeup_lod
from . import flag_assets
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
MAX_CAMERA_TIMING_KEYS = 59
# Keep meaningful mainland/island rings connected by default. Smaller exterior
# rings stay in the composition as a disconnected optional Shape group, so an
# editor can reconnect them when a particular island matters to the story.
ESSENTIAL_RING_AREA_RATIO = 0.05
DEFAULT_BORDER_WIDTH = 0.0003
TINY_ISLAND_BORDER_WIDTH = 0.0001
# Shape coordinates are normalized against the exported wide map. Territories
# below this visible-area threshold need a thinner outline (for example,
# Hawaii); otherwise the outline overwhelms the land at the wide view.
TINY_TERRITORY_AREA = 0.00001

# Flow layout. Keep generated geometry on the left, its active output on the
# right, optional islands on the left, and the interactive edit controls in a
# separate column so large projects remain readable in Fusion.
SHAPE_GRID_X = -2000
SHAPE_GRID_COLUMNS = 4
SHAPE_COLUMN_STEP = 440
SHAPE_BORDER_OFFSET_X = 190
SHAPE_ROW_STEP = 90
SHAPE_OPTIONAL_MERGE_X = -250
SHAPE_ACTIVE_MERGE_X = 350
EDIT_CAMERA_X = 870
EDIT_SWITCH_X = 1570
EDIT_SELECTED_X = 1800
EDIT_CONTROLLER_X = 2020
EDIT_MODE_X = 2040
SWITCH_TILE_COLOR = (0.572549019608, 0.572549019608, 0.572549019608)


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


def _geometry_intersects_bbox(geometry: dict, bbox: tuple[float, float, float, float]) -> bool:
    """Cheap geographic filter used before emitting a local close-up mask."""
    xs, ys = [], []
    for polygon in _polygons(geometry):
        for ring in polygon:
            for lon, lat in ring:
                x, y = _merc(lon, lat)
                xs.append(x)
                ys.append(y)
    if not xs:
        return False
    minx, miny, maxx, maxy = bbox
    return not (max(xs) < minx or min(xs) > maxx or
                max(ys) < miny or min(ys) > maxy)


def _plan_opacity(plan: dict, frame: int) -> float:
    if frame <= plan["first"] or frame >= plan["last"]:
        return 0.0
    if frame < plan["full_first"]:
        return ((frame - plan["first"]) /
                max(1, plan["full_first"] - plan["first"]))
    if frame <= plan["full_last"]:
        return 1.0
    return ((plan["last"] - frame) /
            max(1, plan["last"] - plan["full_last"]))


def _global_country_visibility_lines(plans: list[dict], duration: int) -> str:
    frames = {0, duration}
    for plan in plans:
        frames.update((plan["first"], plan["full_first"],
                       plan["full_last"], plan["last"]))
    return "\n".join(
        f'\t\t\t\t[{frame}] = {{ {1 - max((_plan_opacity(plan, frame) for plan in plans), default=0):.12g}, '
        f'Flags = {{ Linear = true }} }},'
        for frame in sorted(frames)
    )


def _polyline(points: list[tuple[float, float]]) -> str:
    return " ".join(
        f"{{ Linear = true, X = {x:.12g}, Y = {y:.12g}, LX = 0, LY = 0, RX = 0, RY = 0 }},"
        for x, y in points)


def _country_mask(name: str, geometry: dict, wide_bbox: dict, width: int, height: int,
                  *, outline: bool = False, pos: tuple[int, int] = (0, 0),
                  x_scale: float = 1.0, y_scale: float = 1.0,
                  prepared_rings: list[tuple[int, list[tuple[float, float]]]] | None = None,
                  instance_source: str | None = None,
                  border_width: float = 0.0005,
                  border_width_source: str | None = None) -> str:
    rings = prepared_rings or _prepared_rings(
        geometry, wide_bbox, x_scale, y_scale)
    if not rings:
        raise ValueError(f"{name} has no valid polygon rings")
    inputs, definitions, order = [], [], []
    for index, (level, points) in enumerate(rings, 1):
        order.append(str(index))
        width_input = (f'Input {{ SourceOp = "{border_width_source}", Source = "Value", }}'
                       if border_width_source else f'Input {{ Value = {border_width:.12g}, }}')
        outline_inputs = (f'\n\t\t\t\t["PolyMask{index}.Solid"] = Input {{ Value = 0, }},'
                          f'\n\t\t\t\t["PolyMask{index}.BorderWidth"] = {width_input},') if outline else ""
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


def _switch_tool(name: str, inputs: list[tuple[str, str]], pos: tuple[int, int],
                 which_expression: str | None = None) -> str:
    """Serialize a native Fusion Switch with named image inputs."""
    if not inputs:
        raise ValueError(f"{name} requires at least one input")
    lines = [
        f"\t\t{name} = Switch {{",
        "\t\t\tNameSet = true,",
        "\t\t\tInputs = {",
        f"\t\t\t\tNumberOfInputs = Input {{ Value = {len(inputs)}, }},",
    ]
    if which_expression:
        lines.append(
            f'\t\t\t\tWhich = Input {{ Expression = "{which_expression}", }},')
    else:
        lines.append("\t\t\t\tWhich = Input { Value = 0, },")
    for index, (label, source) in enumerate(inputs, 1):
        safe_label = str(label).replace('"', "'")
        lines.extend([
            f'\t\t\t\tInput{index - 1} = Input {{ SourceOp = "{source}", Source = "Output", }},',
            f'\t\t\t\tName{index - 1} = Input {{ Value = "{safe_label}", }},',
        ])
    lines.extend([
        "\t\t\t},",
        f"\t\t\tViewInfo = OperatorInfo {{ Pos = {{ {pos[0]}, {pos[1]} }} }},",
        ("\t\t\tColors = { TileColor = { "
         f"R = {SWITCH_TILE_COLOR[0]:.12g}, G = {SWITCH_TILE_COLOR[1]:.12g}, "
         f"B = {SWITCH_TILE_COLOR[2]:.12g} }}, }}"),
        "\t\t},",
    ])
    return "\n".join(lines)


def _checkbox_controller(name: str, labels: list[str], pos: tuple[int, int]) -> str:
    """Serialize a CustomTool containing one independent territory checkbox."""
    inputs = "\n".join(
        f'\t\t\t\tShow_{index:02d} = Input {{ Value = {1 if index == 1 else 0}, }},'
        for index in range(1, len(labels) + 1))
    controls = []
    for index, label in enumerate(labels, 1):
        safe_label = str(label).replace('"', "'")
        controls.append(f'''\t\t\t\tShow_{index:02d} = {{
\t\t\t\t\tLINKID_DataType = "Number",
\t\t\t\t\tINPID_InputControl = "CheckboxControl",
\t\t\t\t\tLINKS_Name = "{safe_label}",
\t\t\t\t\tINP_Default = {1 if index == 1 else 0},
\t\t\t\t}},''')
    return f'''\t\t{name} = CustomTool {{
\t\t\tNameSet = true,
\t\t\tInputs = {{
{inputs}
\t\t\t}},
\t\t\tUserControls = ordered() {{
{chr(10).join(controls)}
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ {pos[0]}, {pos[1]} }} }},
\t\t}},'''


def _flag_adjust_controller(name: str, pos: tuple[int, int]) -> str:
    """Expose camera-relative flag placement and opacity in the Inspector."""
    return f'''\t\t{name} = CustomTool {{
\t\t\tNameSet = true,
\t\t\tInputs = {{
\t\t\t\tOffset_X = Input {{ Value = 0, }},
\t\t\t\tOffset_Y = Input {{ Value = 0, }},
\t\t\t\tScale = Input {{ Value = 1.02, }},
\t\t\t\tOpacity = Input {{ Value = 1, }},
\t\t\t}},
\t\t\tUserControls = ordered() {{
\t\t\t\tOffset_X = {{ LINKID_DataType = "Number", INPID_InputControl = "SliderControl", LINKS_Name = "Horizontal Position", INP_Default = 0, INP_MinScale = -0.25, INP_MaxScale = 0.25, INP_MinAllowed = -1, INP_MaxAllowed = 1, }},
\t\t\t\tOffset_Y = {{ LINKID_DataType = "Number", INPID_InputControl = "SliderControl", LINKS_Name = "Vertical Position", INP_Default = 0, INP_MinScale = -0.25, INP_MaxScale = 0.25, INP_MinAllowed = -1, INP_MaxAllowed = 1, }},
\t\t\t\tScale = {{ LINKID_DataType = "Number", INPID_InputControl = "SliderControl", LINKS_Name = "Flag Scale", INP_Default = 1.02, INP_MinScale = 0.5, INP_MaxScale = 2, INP_MinAllowed = 0.1, INP_MaxAllowed = 10, }},
\t\t\t\tOpacity = {{ LINKID_DataType = "Number", INPID_InputControl = "SliderControl", LINKS_Name = "Flag Opacity", INP_Default = 1, INP_MinScale = 0, INP_MaxScale = 1, INP_MinAllowed = 0, INP_MaxAllowed = 1, }},
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ {pos[0]}, {pos[1]} }} }},
\t\t}},'''


def _shape_territory(name: str, rings: list[tuple[int, list[tuple[float, float]]]],
                     fill: tuple[float, float, float],
                     border: tuple[float, float, float],
                     alpha_input: str, row: int,
                     group_optional: bool = False) -> tuple[str, str]:
    """Serialize one territory as a compact grid with instanced borders."""
    nodes = []
    exterior_areas = [_ring_area(points) for level, points in rings if level > 0]
    largest_exterior = max(exterior_areas, default=0.0)
    territory_is_tiny = sum(exterior_areas) < TINY_TERRITORY_AREA
    essential_indexes = [
        index for index, (level, points) in enumerate(rings, 1)
        if level < 0 or largest_exterior <= 0 or
        _ring_area(points) / largest_exterior >= ESSENTIAL_RING_AREA_RATIO
    ]
    optional_indexes = [
        index for index, (level, _points) in enumerate(rings, 1)
        if level > 0 and index not in essential_indexes
    ]
    compact_group = group_optional and bool(optional_indexes)
    compact_rows_per_column = 4
    compact_column_step = 160
    compact_row_step = 55
    compact_fill_offset_y = 22
    essential_rank = {index: rank for rank, index in enumerate(essential_indexes)}
    optional_rank = {index: rank for rank, index in enumerate(optional_indexes)}
    essential_columns = max(
        1, math.ceil(len(essential_indexes) / compact_rows_per_column))
    optional_columns = max(
        1, math.ceil(len(optional_indexes) / compact_rows_per_column))
    # All country groups share the same right edge. Wider groups grow leftward.
    # Essentials come first, followed by a visible lane and optional columns.
    compact_group_right_x = 50
    compact_merge_x = compact_group_right_x - 180
    optional_start_x = (compact_merge_x -
                        optional_columns * compact_column_step - 160)
    essential_start_x = (optional_start_x - 100 -
                         essential_columns * compact_column_step)
    for index, (_level, points) in enumerate(rings, 1):
        fill_name = f"{name}_Ring_{index:02d}_Fill"
        border_name = f"{name}_Ring_{index:02d}_Border"
        border_width = (TINY_ISLAND_BORDER_WIDTH
                        if territory_is_tiny or index in optional_indexes
                        else DEFAULT_BORDER_WIDTH)
        if compact_group:
            is_optional = index in optional_rank
            grid_index = optional_rank[index] if is_optional else essential_rank[index]
            column = grid_index // compact_rows_per_column
            grid_row = grid_index % compact_rows_per_column
            fill_x = ((optional_start_x if is_optional else essential_start_x) +
                      column * compact_column_step)
            border_x = fill_x
            border_y = row + grid_row * compact_row_step
            fill_y = border_y + compact_fill_offset_y
        else:
            # Keep disconnected land rings in a grid. A long vertical strip
            # made countries overlap in the Flow even when rendering correctly.
            grid_index = index - 1
            column = grid_index % SHAPE_GRID_COLUMNS
            grid_row = grid_index // SHAPE_GRID_COLUMNS
            fill_x = SHAPE_GRID_X + column * SHAPE_COLUMN_STEP
            border_x = fill_x + SHAPE_BORDER_OFFSET_X
            fill_y = border_y = row + grid_row * SHAPE_ROW_STEP
        nodes.append(f'''\t\t{fill_name} = sPolygon {{
\t\t\tNameSet = true,
\t\t\tInputs = {{
\t\t\t\tPolyline = Input {{ Value = Polyline {{ Closed = true, Points = {{ {_polyline(points)} }} }}, }},
\t\t\t\tRed = Input {{ Value = {fill[0]:.12g}, }},
\t\t\t\tGreen = Input {{ Value = {fill[1]:.12g}, }},
\t\t\t\tBlue = Input {{ Value = {fill[2]:.12g}, }},
\t\t\t\tAlpha = {alpha_input}
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ {fill_x}, {fill_y} }} }},
\t\t}},
\t\t{border_name} = sPolygon {{
\t\t\tNameSet = true,
\t\t\tSourceOp = "{fill_name}",
\t\t\tInputs = {{
\t\t\t\tSolid = Input {{ Value = 0, }},
\t\t\t\tBorderWidth = Input {{ Value = {border_width:.12g}, }},
\t\t\t\tRed = Input {{ Value = {border[0]:.12g}, }},
\t\t\t\tGreen = Input {{ Value = {border[1]:.12g}, }},
\t\t\t\tBlue = Input {{ Value = {border[2]:.12g}, }}
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ {border_x}, {border_y} }} }},
\t\t}},''')
    essential_sources = [source for index in essential_indexes
                         for source in (f"{name}_Ring_{index:02d}_Fill",
                                        f"{name}_Ring_{index:02d}_Border")]
    inputs = "\n".join(
        f'\t\t\t\tInput{index} = Input {{ SourceOp = "{source}", Source = "Output", }},'
        for index, source in enumerate(essential_sources, 1))
    output = name + "_Shapes"
    active_merge_x = compact_merge_x if compact_group else SHAPE_ACTIVE_MERGE_X
    active_merge_y = (row + 25 if compact_group else
                      row + ((len(rings) - 1) // SHAPE_GRID_COLUMNS) * 45)
    nodes.append(f'''\t\t{output} = sMerge {{
\t\t\tNameSet = true,
\t\t\tInputs = {{
{inputs}
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ {active_merge_x}, {active_merge_y} }} }},
\t\t}},''')
    if optional_indexes:
        optional_sources = [source for index in optional_indexes
                            for source in (f"{name}_Ring_{index:02d}_Fill",
                                           f"{name}_Ring_{index:02d}_Border")]
        optional_inputs = "\n".join(
            f'\t\t\t\tInput{index} = Input {{ SourceOp = "{source}", Source = "Output", }},'
            for index, source in enumerate(optional_sources, 1))
        optional_merge_x = compact_merge_x if compact_group else SHAPE_OPTIONAL_MERGE_X
        optional_merge_y = (row + 140 if compact_group else
                            row + ((len(rings) - 1) // SHAPE_GRID_COLUMNS) * 45)
        nodes.append(f'''\t\t{name}_Optional_Islands = sMerge {{
\t\t\tNameSet = true,
\t\t\tInputs = {{
{optional_inputs}
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ {optional_merge_x}, {optional_merge_y} }} }},
\t\t}},''')
        if group_optional:
            output_sources = ([f"{name}_Ring_{index:02d}_Border"
                               for index in essential_indexes] +
                              [output, f"{name}_Optional_Islands"])
            group_outputs = "\n".join(
                f'''\t\t\t\tOutput{index} = InstanceOutput {{
\t\t\t\t\tSourceOp = "{source}",
\t\t\t\t\tSource = "Output",
\t\t\t\t}},'''
                for index, source in enumerate(output_sources, 1))
            inner_tools = "\n".join(
                "\t" + line for line in "\n".join(nodes).splitlines())
            group_top_y = row - 20
            group_height = 330
            group_left_x = essential_start_x - 90
            group_right_x = compact_group_right_x
            group_width = group_right_x - group_left_x
            group_pos_x = (group_left_x + group_right_x) / 2
            group_name = f"{name}_Optional_Group"
            grouped = f'''\t\t{group_name} = GroupOperator {{
\t\t\tNameSet = true,
\t\t\tOutputs = {{
{group_outputs}
\t\t\t}},
\t\t\tViewInfo = GroupInfo {{
\t\t\t\tPos = {{ {group_pos_x:.12g}, {group_top_y} }},
\t\t\t\tFlags = {{ Expanded = true, AllowPan = false, AutoSnap = true, RemoveRouters = true }},
\t\t\t\tSize = {{ {group_width}, {group_height}, {group_width / 2:.12g}, 24 }},
\t\t\t\tDirection = "Horizontal",
\t\t\t\tPipeStyle = "Direct",
\t\t\t\tScale = 1,
\t\t\t\tOffset = {{ {-group_pos_x:.12g}, {-group_top_y} }},
\t\t\t}},
\t\t\tTools = ordered() {{
{inner_tools}
\t\t\t}},
\t\t}},'''
            return grouped, output
    return "\n".join(nodes), output


def _shape_camera_render(name: str, source: str, duration: int,
                         canvas_width: int, canvas_height: int,
                         y_aspect: float, pos: tuple[int, int]) -> tuple[str, str]:
    """Move Shape geometry with the map camera, then rasterize it once."""
    camera, render = name + "_Camera", name + "_Render"
    return f'''\t\t{camera} = sTransform {{
\t\t\tNameSet = true,
\t\t\tInputs = {{
\t\t\t\tXOffset = Input {{ Expression = "Map_Animation.Center.X - 0.5", }},
\t\t\t\tYOffset = Input {{ Expression = "(Map_Animation.Center.Y - 0.5) * {y_aspect:.12g}", }},
\t\t\t\tXSize = Input {{ Expression = "Map_Animation.Size", }},
\t\t\t\tYSize = Input {{ Expression = "Map_Animation.Size * {y_aspect:.12g}", }},
\t\t\t\tInput = Input {{ SourceOp = "{source}", Source = "Output", }}
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ {pos[0]}, {pos[1]} }} }},
\t\t}},
\t\t{render} = sRender {{
\t\t\tNameSet = true,
\t\t\tInputs = {{
\t\t\t\tGlobalOut = Input {{ Value = {duration}, }},
\t\t\t\tWidth = Input {{ Value = {canvas_width}, }},
\t\t\t\tHeight = Input {{ Value = {canvas_height}, }},
\t\t\t\tUseFrameFormatSettings = Input {{ Value = 0, }},
\t\t\t\tInput = Input {{ SourceOp = "{camera}", Source = "Output", }}
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ {pos[0] + 220}, {pos[1]} }} }},
\t\t}},''', render


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
        if j - i < 2 or len(retained) >= max(MAX_CAMERA_TIMING_KEYS, len(authored_frames)):
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




def generate(package: Path, metadata: dict, animation: dict,
             warnings: list[str] | None = None) -> Path:
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
    wide_image = package / package_layout.asset_relative(
        metadata, "satellite_wide", str(package_layout.LEGACY_SATELLITE_WIDE_FILE))
    detail_image = package / package_layout.asset_relative(
        metadata, "satellite_detail", str(package_layout.LEGACY_SATELLITE_DETAIL_FILE))
    tools = [f'''\t\tMap_Wide = Loader {{ NameSet = true, Clips = {{ Clip {{ ID = "Clip1", Filename = "{_lua_path(wide_image)}", Length = 1, GlobalEnd = {duration}, TrimOut = 0, Loop = 1 }} }}, ViewInfo = OperatorInfo {{ Pos = {{ -700, 0 }} }}, }},''']
    # Detail remains a raster layer, geographically placed over the wide map.
    factor = float(native["wide_factor"])
    tools.append(f'''\t\tMap_Detail = Loader {{ NameSet = true, Clips = {{ Clip {{ ID = "Clip1", Filename = "{_lua_path(detail_image)}", Length = 1, GlobalEnd = {duration}, TrimOut = 0, Loop = 1 }} }}, ViewInfo = OperatorInfo {{ Pos = {{ -700, 130 }} }}, }},
\t\tPlace_Detail = Transform {{ Inputs = {{ Size = Input {{ Value = {1 / factor:.12g}, }}, Input = Input {{ SourceOp = "Map_Detail", Source = "Output", }} }}, ViewInfo = OperatorInfo {{ Pos = {{ -480, 130 }} }}, }},''')
    vector_layers = []
    country_shape_sources: list[str] = []
    country_edit_inputs: list[tuple[str, str, int]] = []
    flag_plans: list[dict] = []
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
    # One detail-quality vector geometry replaces the former wide/detail mask
    # pair. It remains resolution independent until the final sRender.
    static_tolerance = GEOMETRY_TOLERANCE_PX / (max(width, height) * factor)
    row_cursor = 360
    for group in groups:
        country = countries[group["iso3"]]
        red, green, blue = _rgb(country.get("color", "#1689ff"))
        border_red, border_green, border_blue = _rgb(country.get("border_color", "#ffffff"))
        for child in group.get("children", []):
            child_base = _territory_base(group["iso3"], child)
            geometry = _child_geometry(package, country, child)
            row = row_cursor
            ring_limit = RING_LIMITS.get(child["id"], DEFAULT_RING_LIMIT)
            rings = _prepared_rings(
                geometry, wide_bbox, 1.0, 1.0, static_tolerance, ring_limit)
            largest = max((_ring_area(points) for level, points in rings if level > 0),
                          default=0)
            active_indexes = [
                index for index, (level, points) in enumerate(rings, 1)
                if level < 0 or largest <= 0 or
                _ring_area(points) / largest >= ESSENTIAL_RING_AREA_RATIO
            ]
            grouped_optional = (child.get("category") == "country" and
                                len(active_indexes) < len(rings))
            shape_nodes, shape_output = _shape_territory(
                child_base, rings, (red, green, blue),
                (border_red, border_green, border_blue),
                "Input { Value = 1, }", row,
                group_optional=child.get("category") == "country")
            tools.append(shape_nodes)
            country_shape_sources.append(shape_output)
            if child.get("category") == "country":
                code = flag_assets.flag_code(group["iso3"], country.get("iso2"))
                if code:
                    active = [rings[index - 1] for index in active_indexes]
                    texture, placement, flag_warnings = flag_assets.make_texture(
                        package, group["iso3"], code, active, width, height,
                        max(sample["zoom"] for sample in samples))
                    flag_plans.append({"iso3": group["iso3"], "base": child_base,
                                       "texture": texture, "placement": placement,
                                       "warnings": flag_warnings,
                                       "border_sources": [f"{child_base}_Ring_{index:02d}_Border"
                                                          for index in active_indexes],
                                       "edit_index": len(country_edit_inputs) + 1,
                                       "layout_y": row})
                    if warnings is not None:
                        warnings.extend(flag_warnings)
                elif warnings is not None:
                    warnings.append(f"{group['iso3']}: no matching flag asset; using color fill")
            safe_name = _territory_label(child).replace('"', "'")
            country_edit_inputs.append(
                (f"{group['iso3']} - {safe_name}", shape_output, row))
            ring_rows = max(1, math.ceil(len(rings) / SHAPE_GRID_COLUMNS))
            row_cursor += 360 if grouped_optional else ring_rows * SHAPE_ROW_STEP + 140
        row_cursor += 80
    has_country_layers = bool(country_shape_sources)
    layer_number = 1
    incomplete = [connection["name"] for connection in animation.get("connections", [])
                  if not connection.get("start") or not connection.get("end")]
    if incomplete:
        raise ValueError("Complete or delete these connections before generating Fusion: " + ", ".join(incomplete))
    closeup_plans = closeup_lod.ensure_images(
        package, metadata, animation, closeup_lod.plan_closeups(metadata, animation))
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
    lod_nodes = []
    lod_source = "Map_Animation"
    for index, plan in enumerate(closeup_plans, 1):
        local_samples = closeup_lod.local_samples(
            animation, plan["normalized_bbox"], plan["first"], plan["last"])
        local_keys = _camera_timing_keys(
            local_samples, {plan["first"], plan["frame"], plan["last"]})
        node = f'Closeup_{index:02d}_{plan["frame"]:04d}'
        plan["node"] = node
        plan["local_keys"] = local_keys
        visibility = {0: 0, plan["first"]: 0, plan["full_first"]: 1,
                      plan["full_last"]: 1, plan["last"]: 0, duration: 0}
        visibility_lines = "\n".join(
            f'\t\t\t\t[{frame}] = {{ {value}, Flags = {{ Linear = true }} }},'
            for frame, value in sorted(visibility.items()))
        lod_nodes.append(f'''\t\t{node}_Loader = Loader {{ NameSet = true, Clips = {{ Clip {{ ID = "Clip1", Filename = "{_lua_path(plan["image_path"])}", Length = 1, GlobalEnd = {duration}, TrimOut = 0, Loop = 1 }} }}, ViewInfo = OperatorInfo {{ Pos = {{ 1930, {-260 - index * 130} }} }}, }},
\t\t{node}_Displacement = BezierSpline {{ KeyFrames = {{
{_key_lines(local_keys, local_samples, 'displacement')}
\t\t\t}} }},
\t\t{node}_Size = BezierSpline {{ KeyFrames = {{
{_key_lines(local_keys, local_samples, 'size')}
\t\t\t}} }},
\t\t{node}_Path = PolyPath {{ Inputs = {{ Displacement = Input {{ SourceOp = "{node}_Displacement", Source = "Value", }}, PolyLine = Input {{ Value = Polyline {{ Points = {{
{_path_points(local_samples)}
\t\t\t\t\t\t}} }}, }} }}, }},
\t\t{node}_Animation = Transform {{ NameSet = true, Inputs = {{ Center = Input {{ SourceOp = "{node}_Path", Source = "Position", }}, Size = Input {{ SourceOp = "{node}_Size", Source = "Value", }}, ClippingMode = Input {{ Value = FuID {{ "None" }}, }}, Input = Input {{ SourceOp = "{node}_Loader", Source = "Output", }} }}, ViewInfo = OperatorInfo {{ Pos = {{ 2160, {-260 - index * 130} }} }}, }},
\t\t{node}_Visibility = BezierSpline {{ KeyFrames = {{
{visibility_lines}
\t\t\t}} }},
\t\t{node}_Composite = Merge {{ NameSet = true, Inputs = {{ Background = Input {{ SourceOp = "{lod_source}", Source = "Output", }}, Foreground = Input {{ SourceOp = "{node}_Animation", Source = "Output", }}, Blend = Input {{ SourceOp = "{node}_Visibility", Source = "Value", }} }}, ViewInfo = OperatorInfo {{ Pos = {{ {2390 + index * 120}, {-130 - index * 80} }} }}, }},''')
        lod_source = node + "_Composite"
    if closeup_plans:
        lod_nodes.append(_switch_tool("Map_Quality_Switch", [
            ("EDIT - base map only", "Map_Animation"),
            ("RENDER - enable close-up imagery", lod_source),
        ], (2580, -125)))
        map_source = "Map_Quality_Switch"
    else:
        map_source = "Map_Animation"
    if has_country_layers:
        canvas_width, canvas_height = vector_width, vector_height
        y_aspect = height / width
        edit_render_inputs = []
        deployment_render_inputs = []
        country_nodes = []
        country_nodes.append(f'''\t\tCountry_Vector_Canvas = Background {{
\t\t\tNameSet = true,
\t\t\tInputs = {{ GlobalOut = Input {{ Value = {duration}, }}, Width = Input {{ Value = {canvas_width}, }}, Height = Input {{ Value = {canvas_height}, }}, UseFrameFormatSettings = Input {{ Value = 0, }}, TopLeftAlpha = Input {{ Value = 0, }} }},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ 1640, 150 }} }},
\t\t}},''')
        country_nodes.append(_checkbox_controller(
            "Country_Edit_Controller", [label for label, _source, _row in country_edit_inputs],
            (EDIT_CONTROLLER_X, 530)))
        for flag_index, plan in enumerate(flag_plans):
            iso = plan["iso3"]
            prefix = f"{iso}_Flag"
            flag_y = plan["layout_y"]
            placement = plan["placement"]
            center_x = placement["center_x"]
            center_y = placement["center_y"]
            texture_scale = placement["scale"]
            center_expression = (
                "Point(0.5 + (Map_Animation.Center.X - 0.5) + "
                f"({center_x:.12g} - 0.5 + {prefix}_Adjust.Offset_X) * Map_Animation.Size, "
                "0.5 + (Map_Animation.Center.Y - 0.5) * "
                f"{y_aspect:.12g} + (0.5 - {center_y:.12g} + {prefix}_Adjust.Offset_Y) * "
                f"{y_aspect:.12g} * Map_Animation.Size)"
            )
            country_nodes.append(_flag_adjust_controller(
                f"{prefix}_Adjust", (650, flag_y + 180)))
            country_nodes.append(f'''\t\t{prefix}_Loader = Loader {{ NameSet = true, Clips = {{ Clip {{ ID = "Clip1", Filename = "{_lua_path(plan['texture'])}", Length = 1, GlobalEnd = {duration}, TrimOut = 0, Loop = 1 }} }}, ViewInfo = OperatorInfo {{ Pos = {{ 450, {flag_y + 80} }} }}, }},
\t\t{prefix}_Masked_On_Working_Canvas = Merge {{ NameSet = true, Inputs = {{ Background = Input {{ SourceOp = "Country_Vector_Canvas", Source = "Output", }}, Foreground = Input {{ SourceOp = "{prefix}_Loader", Source = "Output", }}, Center = Input {{ Expression = "{center_expression}", }}, Size = Input {{ Expression = "Map_Animation.Size / {texture_scale:.12g} * {prefix}_Adjust.Scale", }}, Blend = Input {{ Expression = "{prefix}_Adjust.Opacity", }}, EffectMask = Input {{ SourceOp = "Country_Edit_{plan['edit_index']:02d}_Render", Source = "Output", }} }}, ViewInfo = OperatorInfo {{ Pos = {{ 850, {flag_y + 100} }} }}, }},''')
            border_inputs = "\n".join(
                f'\t\t\t\tInput{index} = Input {{ SourceOp = "{source}", Source = "Output", }},'
                for index, source in enumerate(plan["border_sources"], 1))
            country_nodes.append(f'''\t\t{prefix}_Border_Geometry = sMerge {{ NameSet = true, Inputs = {{
{border_inputs}
\t\t\t}}, ViewInfo = OperatorInfo {{ Pos = {{ 450, {flag_y + 220} }} }}, }},''')
            border_nodes, border_output = _shape_camera_render(
                f"{prefix}_Border", f"{prefix}_Border_Geometry", duration,
                canvas_width, canvas_height, y_aspect, (670, flag_y + 220))
            country_nodes.append(border_nodes)
        for index, (label, shape_source, country_y) in enumerate(country_edit_inputs, 1):
            render_nodes, render_output = _shape_camera_render(
                f"Country_Edit_{index:02d}", shape_source, duration,
                canvas_width, canvas_height, y_aspect,
                (450, country_y))
            country_nodes.append(render_nodes)
            matching = next((plan for plan in flag_plans if plan["edit_index"] == index), None)
            if matching:
                prefix = f"{matching['iso3']}_Flag"
                flag_output = f"{prefix}_With_Border"
                country_nodes.append(f'''\t\t{flag_output} = Merge {{ NameSet = true, Inputs = {{ Background = Input {{ SourceOp = "{prefix}_Masked_On_Working_Canvas", Source = "Output", }}, Foreground = Input {{ SourceOp = "{prefix}_Border_Render", Source = "Output", }} }}, ViewInfo = OperatorInfo {{ Pos = {{ 1150, {country_y + 100} }} }}, }},''')
                switch_name = f"{prefix}_Color_Flag"
                country_nodes.append(_switch_tool(switch_name, [
                    ("Color", render_output),
                    ("Flag", flag_output),
                ], (1330, country_y)))
                render_output = switch_name
            deployment_render_inputs.append((label, render_output))
            select_name = f"Country_Edit_{index:02d}_Enabled"
            country_nodes.append(_switch_tool(select_name, [
                ("OFF", "Country_Vector_Canvas"),
                (label, render_output),
            ], (1550, country_y),
                f"Country_Edit_Controller.Show_{index:02d}"))
            edit_render_inputs.append((label, select_name))
        deployment_layers = "\n".join(
            f'''\t\t\t\t["Layer{index}.Foreground"] = Input {{ SourceOp = "{source}", Source = "Output", }},
\t\t\t\tLayerName{index} = Input {{ Value = "{label.replace(chr(34), chr(39))}", }},'''
            for index, (label, source) in enumerate(deployment_render_inputs, 1))
        country_nodes.append(f'''\t\tCountry_Deployment = MultiMerge {{
\t\t\tNameSet = true,
\t\t\tInputs = {{ Background = Input {{ SourceOp = "Country_Vector_Canvas", Source = "Output", }},
{deployment_layers}
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ 1920, 180 }} }},
\t\t}},''')
        deployment_output = "Country_Deployment"
        edit_layers = "\n".join(
            f'''\t\t\t\t["Layer{index}.Foreground"] = Input {{ SourceOp = "{source}", Source = "Output", }},
\t\t\t\tLayerName{index} = Input {{ Value = "{label.replace(chr(34), chr(39))}", }},'''
            for index, (label, source) in enumerate(edit_render_inputs, 1))
        country_nodes.append(f'''\t\tCountry_Edit_Selected = MultiMerge {{
\t\t\tNameSet = true,
\t\t\tInputs = {{
\t\t\t\tBackground = Input {{ SourceOp = "Country_Vector_Canvas", Source = "Output", }},
{edit_layers}
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ {EDIT_SELECTED_X}, 440 }} }},
\t\t}},''')
        country_nodes.append(_switch_tool("Country_Mode_Switch", [
            ("EDIT MODE - checked countries and territories", "Country_Edit_Selected"),
            ("DEPLOYMENT - all countries and territories", deployment_output),
        ], (EDIT_MODE_X, 445)))
        country_nodes.append(f'''\t\tMap_Working_Canvas = Merge {{
\t\t\tNameSet = true,
\t\t\tInputs = {{ Background = Input {{ SourceOp = "Country_Vector_Canvas", Source = "Output", }}, Foreground = Input {{ SourceOp = "{map_source}", Source = "Output", }} }},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ 2300, 50 }} }},
\t\t}},
\t\tMap_With_Countries = Merge {{
\t\t\tNameSet = true,
\t\t\tInputs = {{ Background = Input {{ SourceOp = "Map_Working_Canvas", Source = "Output", }}, Foreground = Input {{ SourceOp = "Country_Mode_Switch", Source = "Output", }} }},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ 2620, 15 }} }},
\t\t}},''')
        country_nodes = "\n".join(country_nodes)
        final_map_source = "Map_With_Countries"
    else:
        country_nodes = ""
        final_map_source = map_source
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
\t\tMap_Animation = Transform {{ NameSet = true, Inputs = {{ Center = Input {{ SourceOp = "Map_AnimationPath", Source = "Position", }}, Size = Input {{ SourceOp = "Map_AnimationSize", Source = "Value", }}, ClippingMode = Input {{ Value = FuID {{ "None" }}, }}, Input = Input {{ SourceOp = "Map_Raster_Layers", Source = "Output", }} }}, ViewInfo = OperatorInfo {{ Pos = {{ 2160, 0 }} }}, }},
{chr(10).join(lod_nodes)}
{country_nodes}
\t\tOutput_Canvas = Background {{ NameSet = true, Inputs = {{ GlobalOut = Input {{ Value = {duration}, }}, Width = Input {{ Value = {output_width}, }}, Height = Input {{ Value = {output_height}, }}, PixelAspect = Input {{ Value = {{ 1, 1 }}, }}, UseFrameFormatSettings = Input {{ Value = 0, }}, TopLeftAlpha = Input {{ Value = 0, }} }}, ViewInfo = OperatorInfo {{ Pos = {{ 2850, 130 }} }}, }},
\t\tFinal_Composite = Merge {{ NameSet = true, Inputs = {{ Background = Input {{ SourceOp = "Output_Canvas", Source = "Output", }}, Foreground = Input {{ SourceOp = "{final_map_source}", Source = "Output", }} }}, ViewInfo = OperatorInfo {{ Pos = {{ 2850, 0 }} }}, }},
\t\tVector_Layers = MultiMerge {{ NameSet = true, Inputs = {{ Background = Input {{ SourceOp = "Final_Composite", Source = "Output", }},
{chr(10).join(vector_layers)}
\t\t}}, ViewInfo = OperatorInfo {{ Pos = {{ 3080, 0 }} }}, }},
\t\tMediaOut1 = MediaOut {{ Inputs = {{ Input = Input {{ SourceOp = "Vector_Layers", Source = "Output", }} }}, ViewInfo = OperatorInfo {{ Pos = {{ 3310, 0 }} }}, }},''')
    content = f'''Composition {{
\tCurrentTime = 0, RenderRange = {{ 0, {duration} }}, GlobalRange = {{ 0, {duration} }},
\tTools = {{
{chr(10).join(tools)}
\t}}
}}
'''
    fusion_dir = package / package_layout.FUSION_DIR
    fusion_dir.mkdir(exist_ok=True)
    versions = [int(m.group(1)) for path in fusion_dir.glob("scene_v*.comp")
                if (m := re.fullmatch(r"scene_v(\d+)\.comp", path.name))]
    target = fusion_dir / f"scene_v{max(versions, default=0) + 1:03d}.comp"
    target.write_text(content, encoding="utf-8")
    return target
