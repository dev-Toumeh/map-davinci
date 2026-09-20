"""
map-asset-app / exporter.py

Deterministic map-asset exporter for DaVinci Resolve Fusion map animations.

Reproduces the QGIS tutorial workflow programmatically:
  1. Country boundary geometry comes from Natural Earth 10m admin-0 countries.
  2. Satellite background is stitched from XYZ map tiles (Google Satellite by
     default, the same basemap the tutorial uses via QuickMapServices).
  3. All assets for a shot are rendered onto ONE shared grid:
     - same CRS (EPSG:3857 Web Mercator)
     - same center, same pixel dimensions
     - masks share the exact extent of the detailed background
     - the wide background keeps the same center but covers
       `wide_factor` x the projected width/height of the detail extent
  4. Exports a package: satellite_detail.png, satellite_wide.png,
     mask_<ISO>.png per country, alignment_check.jpg, metadata.json

No screenshots of the UI are involved: every export is rendered from raw
tiles + raw geometry through explicit, recorded math.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import requests
from PIL import Image, ImageDraw

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------

R_EARTH = 6378137.0
MERC_MAX = 20037508.342789244          # Web Mercator half-size (meters)
TILE_SIZE = 256
TILE_THREADS = 8
TILE_RETRIES = 3
SUPERSCALE = 2                          # mask supersampling for smooth edges
# Editable defaults used consistently by browser preview, exported masks, and
# native Fusion fills. Add national/flag-derived colors here as they are agreed.
DEFAULT_COUNTRY_COLOR = "#1689ff"
NATIONAL_FILL_COLORS = {
    "SAU": "#005430",  # Saudi Arabia flag green: RGB(0, 84, 48)
    "USA": "#3c3b6e", "FRA": "#0055a4", "DEU": "#dd0000",
    "ITA": "#009246", "JPN": "#bc002d", "GBR": "#012169",
    "CAN": "#ff0000", "BRA": "#009c3b", "IND": "#ff9933",
}
DEFAULT_BORDER_COLOR = "#ffffff"


def country_default_color(iso3: str) -> str:
    """Default fill color for a country; generic blue remains a safe fallback."""
    return NATIONAL_FILL_COLORS.get(str(iso3).upper(), DEFAULT_COUNTRY_COLOR)

APP_ROOT = Path(__file__).resolve().parent
DATA_DIR = APP_ROOT / "data"
TILE_CACHE = APP_ROOT / "tilecache"
EXPORTS_DIR = APP_ROOT / "exports"

COUNTRIES_FILE = DATA_DIR / "ne_10m_admin_0_countries.geojson"
COUNTRIES_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
    "master/geojson/ne_10m_admin_0_countries.geojson"
)

RESOLUTIONS = {
    "4k":  {"landscape": (3840, 2160), "vertical": (2160, 3840)},
    "fhd": {"landscape": (1920, 1080), "vertical": (1080, 1920)},
    "hd":  {"landscape": (1280, 720),  "vertical": (720, 1280)},
}

SOURCES: Dict[str, dict] = {
    "google_satellite": {
        "url": "https://mt{i}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
        "subdomains": [0, 1, 2, 3],
        "max_zoom": 19,
        "attribution": "Imagery (c) Google",
        "note": "Same basemap used by the QGIS QuickMapServices tutorial.",
    },
    "esri_world_imagery": {
        "url": (
            "https://server.arcgisonline.com/ArcGIS/rest/services/"
            "World_Imagery/MapServer/tile/{z}/{y}/{x}"
        ),
        "subdomains": [None],
        "max_zoom": 19,
        "attribution": "Esri, Maxar, Earthstar Geographics",
        "note": "Max zoom varies by area; tiles may be missing in remote regions.",
    },
}

HTTP_HEADERS = {
    "User-Agent": "map-asset-app/0.1 (local personal tool for Fusion map animations)",
}

ProgressFn = Callable[[str, float, str], None]


# --------------------------------------------------------------------------
# Web Mercator math
# --------------------------------------------------------------------------

def ll_to_merc(lon: float, lat: float) -> Tuple[float, float]:
    """WGS84 lon/lat (degrees) -> EPSG:3857 meters. Latitude clamped."""
    lat = max(-85.05112878, min(85.05112878, lat))
    x = R_EARTH * math.radians(lon)
    y = R_EARTH * math.log(math.tan(math.pi / 4.0 + math.radians(lat) / 2.0))
    return x, y


def merc_to_ll(x: float, y: float) -> Tuple[float, float]:
    """EPSG:3857 meters -> WGS84 lon/lat (degrees)."""
    lon = math.degrees(x / R_EARTH)
    lat = math.degrees(2.0 * math.atan(math.exp(y / R_EARTH)) - math.pi / 2.0)
    return lon, lat


def mercator_meters_per_pixel(zoom: float) -> float:
    """EPSG:3857 projected meters per pixel for a 256px XYZ zoom.

    This is the scale Leaflet uses to place tiles and geometry. It must be
    used for export extents so the browser's yellow frame and generated image
    cover the identical geographic area.
    """
    return 156543.03392804097 / (2.0 ** zoom)


def ground_meters_per_pixel(zoom: float, lat: float) -> float:
    """Local ground resolution (m/px), useful for imagery-detail reporting."""
    return mercator_meters_per_pixel(zoom) * math.cos(math.radians(lat))


def global_pixel(merc_x: float, merc_y: float, zoom: float) -> Tuple[float, float]:
    """Mercator meters -> global pixel coordinates (top-left origin)."""
    world = TILE_SIZE * (2.0 ** zoom)
    px = (merc_x + MERC_MAX) / (2.0 * MERC_MAX) * world
    py = (MERC_MAX - merc_y) / (2.0 * MERC_MAX) * world
    return px, py


def choose_tile_zoom(target_mpp: float, lat: float, max_zoom: int) -> Tuple[int, bool]:
    """
    Highest tile zoom whose native ground resolution is at least as detailed
    as the target. Returns (zoom, upscaled) where upscaled=True means even the
    source's max zoom is coarser than requested (imagery will be enlarged).
    """
    if target_mpp <= 0:
        raise ValueError("target_mpp must be positive")
    need = math.log2(156543.03392804097 * math.cos(math.radians(lat)) / target_mpp)
    z = int(math.ceil(need - 1e-9))
    z = max(0, min(z, max_zoom))
    native = ground_meters_per_pixel(z, lat)
    upscaled = native > target_mpp * (1.0 + 1e-6)
    return z, upscaled


def parse_hex_color(value: str) -> Tuple[str, Tuple[int, int, int]]:
    """Validate a UI color and return canonical #rrggbb plus its RGB tuple."""
    value = str(value).strip()
    if not value.startswith("#") or len(value) != 7:
        raise ValueError(f"country color must use #RRGGBB format, got {value!r}")
    try:
        rgb = tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))
    except ValueError as exc:
        raise ValueError(f"country color must use #RRGGBB format, got {value!r}") from exc
    return value.lower(), rgb


# --------------------------------------------------------------------------
# Tile download + stitch
# --------------------------------------------------------------------------

def _tile_url(source: dict, z: int, x: int, y: int) -> str:
    sub = source["subdomains"][(x + y) % len(source["subdomains"])]
    return source["url"].format(i=sub, z=z, x=x, y=y)


def _fetch_tile(source: dict, z: int, x: int, y: int, cache_key: str) -> bytes:
    cache_path = TILE_CACHE / cache_key / str(z) / str(x) / f"{y}.img"
    if cache_path.exists():
        return cache_path.read_bytes()
    url = _tile_url(source, z, x, y)
    last_err: Optional[Exception] = None
    for attempt in range(TILE_RETRIES):
        try:
            r = requests.get(url, headers=HTTP_HEADERS, timeout=20)
            if r.status_code == 200 and r.content:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_bytes(r.content)
                return r.content
            last_err = RuntimeError(f"HTTP {r.status_code} for {url}")
        except Exception as exc:  # noqa: BLE001 - report to user as export error
            last_err = exc
        time.sleep(0.6 * (attempt + 1))
    raise RuntimeError(f"tile download failed after {TILE_RETRIES} tries: {last_err}")


def _bbox_tiles(z: int, bbox: Tuple[float, float, float, float]) -> Tuple[int, int, int, int]:
    """Tile index range (tx0, ty0, tx1, ty1) covering the mercator bbox."""
    minx, miny, maxx, maxy = bbox
    world = TILE_SIZE * (2.0 ** z)
    px0, py0 = global_pixel(minx, maxy, z)   # top-left
    px1, py1 = global_pixel(maxx, miny, z)   # bottom-right
    tx0 = max(0, int(math.floor(px0 / TILE_SIZE)))
    ty0 = max(0, int(math.floor(py0 / TILE_SIZE)))
    tx1 = min(int(2 ** z) - 1, int(math.floor((px1 - 1e-9) / TILE_SIZE)))
    ty1 = min(int(2 ** z) - 1, int(math.floor((py1 - 1e-9) / TILE_SIZE)))
    return tx0, ty0, tx1, ty1


def stitch_bbox(
    source: dict,
    source_key: str,
    z: int,
    bbox: Tuple[float, float, float, float],
    out_size: Tuple[int, int],
    progress: ProgressFn,
    stage: str,
) -> Image.Image:
    """Download all tiles covering the bbox, stitch, crop and resample to out_size."""
    tx0, ty0, tx1, ty1 = _bbox_tiles(z, bbox)
    nx, ny = tx1 - tx0 + 1, ty1 - ty0 + 1
    total = nx * ny

    cache_key = source_key

    def one(idx: int) -> Tuple[int, int, bytes]:
        dx, dy = idx % nx, idx // nx
        x, y = tx0 + dx, ty0 + dy
        return dx, dy, _fetch_tile(source, z, x, y, cache_key)

    mosaic = Image.new("RGB", (nx * TILE_SIZE, ny * TILE_SIZE))
    done = 0
    with ThreadPoolExecutor(max_workers=TILE_THREADS) as pool:
        futures = [pool.submit(one, i) for i in range(total)]
        for fut in as_completed(futures):
            dx, dy, data = fut.result()
            mosaic.paste(Image.open(io.BytesIO(data)).convert("RGB"),
                         (dx * TILE_SIZE, dy * TILE_SIZE))
            done += 1
            progress(stage, 100.0 * done / total,
                     f"{done}/{total} tiles (z{z})")

    # exact crop in mosaic pixel space
    minx, miny, maxx, maxy = bbox
    px0, py0 = global_pixel(minx, maxy, z)
    px1, py1 = global_pixel(maxx, miny, z)
    box = (
        px0 - tx0 * TILE_SIZE,
        py0 - ty0 * TILE_SIZE,
        px1 - tx0 * TILE_SIZE,
        py1 - ty0 * TILE_SIZE,
    )
    crop = mosaic.crop(tuple(int(round(v)) for v in box))
    if crop.size != out_size:
        crop = crop.resize(out_size, Image.LANCZOS)
    return crop


# --------------------------------------------------------------------------
# Country data
# --------------------------------------------------------------------------

def ensure_countries_file(progress: Optional[ProgressFn] = None) -> Path:
    if COUNTRIES_FILE.exists() and COUNTRIES_FILE.stat().st_size > 1_000_000:
        return COUNTRIES_FILE
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if progress:
        progress("boundaries", 10.0, "downloading Natural Earth country boundaries (~13 MB, once)")
    r = requests.get(COUNTRIES_URL, headers=HTTP_HEADERS, timeout=120)
    r.raise_for_status()
    tmp = COUNTRIES_FILE.with_suffix(".tmp")
    tmp.write_bytes(r.content)
    tmp.rename(COUNTRIES_FILE)
    if progress:
        progress("boundaries", 100.0, "country boundaries ready")
    return COUNTRIES_FILE


def load_countries() -> List[dict]:
    """Lightweight index of countries: [{iso3, iso2, name}]."""
    path = ensure_countries_file()
    geo = json.loads(path.read_text())
    out = []
    for feat in geo["features"]:
        p = feat.get("properties", {})
        iso3 = p.get("ADM0_A3") or p.get("adm0_a3") or ""
        iso2 = p.get("ISO_A2") or p.get("iso_a2") or ""
        name = p.get("NAME_LONG") or p.get("ADMIN") or p.get("name") or iso3
        if iso2 in ("-99", None, ""):
            iso2 = iso3
        out.append({"iso3": iso3, "iso2": iso2, "name": name})
    out.sort(key=lambda c: c["name"])
    return out


def get_geometry(iso3: str) -> dict:
    """GeoJSON geometry dict (lon/lat) for one country."""
    path = ensure_countries_file()
    geo = json.loads(path.read_text())
    for feat in geo["features"]:
        p = feat.get("properties", {})
        if (p.get("ADM0_A3") or "").upper() == iso3.upper():
            return feat["geometry"]
    raise KeyError(f"country not found: {iso3}")


# --------------------------------------------------------------------------
# Mask rendering
# --------------------------------------------------------------------------

def _polygons_of_geometry(geom: dict) -> List[List[List[Tuple[float, float]]]]:
    """
    Normalize any GeoJSON polygonal geometry into a list of polygons, where
    each polygon is a list of rings: [outer, hole1, hole2, ...].
    Rings are lists of (lon, lat) tuples.
    """
    if geom["type"] == "Polygon":
        return [[[tuple(pt) for pt in ring] for ring in geom["coordinates"]]]
    if geom["type"] == "MultiPolygon":
        return [
            [[tuple(pt) for pt in ring] for ring in poly]
            for poly in geom["coordinates"]
        ]
    if geom["type"] == "GeometryCollection":
        polys = []
        for g in geom.get("geometries", []):
            polys.extend(_polygons_of_geometry(g))
        return polys
    raise ValueError(f"unsupported geometry type: {geom['type']}")


def render_mask(
    geometry: dict,
    bbox: Tuple[float, float, float, float],
    out_size: Tuple[int, int],
    color: Tuple[int, int, int] = (22, 137, 255),
) -> Tuple[Image.Image, Tuple[int, int, int, int]]:
    """
    Render one country as an RGBA image (opaque white shape, transparent
    elsewhere) exactly aligned to the given mercator bbox / pixel grid.

    Returns (mask_rgba, bounds_px) where bounds_px is (x0, y0, x1, y1)
    of the country's geographic bbox on the canvas (may be partially outside).
    """
    minx, miny, maxx, maxy = bbox
    W, H = out_size
    span_x = maxx - minx
    span_y = maxy - miny

    def to_px(lon: float, lat: float) -> Tuple[float, float]:
        mx, my = ll_to_merc(lon, lat)
        # supersampled canvas coordinates
        return ((mx - minx) / span_x * W * SUPERSCALE,
                (maxy - my) / span_y * H * SUPERSCALE)

    layer = Image.new("L", (W * SUPERSCALE, H * SUPERSCALE), 0)
    draw = ImageDraw.Draw(layer)

    # draw polygon-by-polygon: outer ring filled, holes erased
    for rings in _polygons_of_geometry(geometry):
        if not rings:
            continue
        outer = [to_px(lon, lat) for lon, lat in rings[0]]
        if len(outer) < 3:
            continue
        draw.polygon(outer, fill=255)
        for hole in rings[1:]:
            pts = [to_px(lon, lat) for lon, lat in hole]
            if len(pts) >= 3:
                draw.polygon(pts, fill=0)

    # geographic bounds in pixels (before supersampling)
    lons, lats = [], []
    for rings in _polygons_of_geometry(geometry):
        for ring in rings:
            for lon, lat in ring:
                lons.append(lon)
                lats.append(lat)
    if lons:
        # precise transform (bbox is axis-aligned in mercator):
        x0 = (ll_to_merc(min(lons), 0)[0] - minx) / span_x * W
        x1 = (ll_to_merc(max(lons), 0)[0] - minx) / span_x * W
        y0 = (maxy - ll_to_merc(0, max(lats))[1]) / span_y * H
        y1 = (maxy - ll_to_merc(0, min(lats))[1]) / span_y * H
        bounds_px = (round(x0), round(y0), round(x1), round(y1))
    else:
        bounds_px = (0, 0, W, H)

    alpha = layer.resize(out_size, Image.LANCZOS)
    # RGB is the selected highlight color; alpha remains the actual mask.
    # Fusion can therefore use this as a direct color layer or only its alpha.
    rgba = Image.new("RGBA", out_size, (*color, 0))
    rgba.putalpha(alpha)
    return rgba, bounds_px


# --------------------------------------------------------------------------
# SVG mask rendering
# --------------------------------------------------------------------------

def render_mask_svg(
    geometry: dict,
    bbox: Tuple[float, float, float, float],
    out_size: Tuple[int, int],
    color: str = DEFAULT_COUNTRY_COLOR,
) -> str:
    """
    Vector version of the country mask, generated directly from the boundary
    geometry (not traced from the PNG). Aligned to the detail background:
    viewBox == detail image pixels, so SVG coordinates map 1:1 to the PNG.

    All polygons are kept (islands, enclaves); outer rings and holes are
    combined per polygon with fill-rule="evenodd" so holes stay transparent.
    """
    minx, miny, maxx, maxy = bbox
    W, H = out_size
    span_x = maxx - minx
    span_y = maxy - miny

    def to_px(lon: float, lat: float) -> Tuple[float, float]:
        mx, my = ll_to_merc(lon, lat)
        return ((mx - minx) / span_x * W, (maxy - my) / span_y * H)

    paths = []
    for rings in _polygons_of_geometry(geometry):
        parts = []
        for ring in rings:
            if len(ring) < 3:
                continue
            pts = [to_px(lon, lat) for lon, lat in ring]
            parts.append("M " + " L ".join(f"{x:.2f},{y:.2f}" for x, y in pts) + " Z")
        if parts:
            paths.append('<path d="' + " ".join(parts) + '"/>')

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}">\n'
        f'  <g fill="{color}" fill-rule="evenodd" stroke="none">\n    '
        + "\n    ".join(paths)
        + "\n  </g>\n</svg>\n"
    )


# --------------------------------------------------------------------------
# Export pipeline
# --------------------------------------------------------------------------

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run_export(config: dict, progress: ProgressFn) -> dict:
    """
    config keys:
      name         output folder name (sanitized)
      countries    list of ISO3 codes, e.g. ["SAU"]
      center       {"lat": float, "lng": float}
      zoom         Leaflet-style map zoom, recorded for reproducibility
      detail_bbox_mercator  optional exact visible target-frame bounds:
                            {minx, miny, maxx, maxy}; takes priority over
                            center/zoom and is used by the browser UI
      orientation  "landscape" (3840x2160) | "vertical" (2160x3840)
      wide_factor  float, default 2.0
      source       key in SOURCES, default google_satellite
    """
    t0 = time.time()
    name = "".join(c if (c.isalnum() or c in "-_") else "_" for c in str(config.get("name", "shot"))) or "shot"
    iso_list = [str(c).upper() for c in config.get("countries") or []]
    if not iso_list:
        raise ValueError("no countries selected")
    center = config.get("center") or {}
    lat = float(center.get("lat", 0.0))
    lng = float(center.get("lng", 0.0))
    zoom = float(config.get("zoom", 7.0))
    orientation = config.get("orientation", "landscape")
    resolution = str(config.get("resolution", "4k")).lower()
    if resolution not in RESOLUTIONS:
        raise ValueError(f"unknown resolution: {resolution}")
    if orientation not in RESOLUTIONS[resolution]:
        raise ValueError(f"unknown orientation: {orientation}")
    W, H = RESOLUTIONS[resolution][orientation]
    wide_factor = float(config.get("wide_factor", 2.0))
    if wide_factor <= 1.0:
        raise ValueError("wide_factor must be > 1")
    source_key = config.get("source", "google_satellite")
    if source_key not in SOURCES:
        raise ValueError(f"unknown imagery source: {source_key}")
    source = SOURCES[source_key]

    out_dir = EXPORTS_DIR / name
    if out_dir.exists():
        # keep every export reproducible & separate
        stamp = time.strftime("%Y%m%d-%H%M%S")
        out_dir = EXPORTS_DIR / f"{name}_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    progress("extents", 5.0, "computing shared grid")
    explicit_bbox = config.get("detail_bbox_mercator")
    if explicit_bbox:
        try:
            detail_bbox = tuple(float(explicit_bbox[k]) for k in ("minx", "miny", "maxx", "maxy"))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("detail_bbox_mercator must contain numeric minx, miny, maxx, maxy") from exc
        minx, miny, maxx, maxy = detail_bbox
        if not (minx < maxx and miny < maxy):
            raise ValueError("detail_bbox_mercator must have min values below max values")
        cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
        lng, lat = merc_to_ll(cx, cy)
        detail_span_x, detail_span_y = maxx - minx, maxy - miny
        detail_mpp = detail_span_x / W
        # The target frame's CSS aspect ratio must match the export ratio.
        if abs(detail_span_y / H - detail_mpp) > detail_mpp * 0.001:
            raise ValueError("target frame aspect ratio does not match output dimensions")
    else:
        # Legacy/API fallback: construct an extent from a Leaflet zoom level.
        cx, cy = ll_to_merc(lng, lat)
        detail_mpp = mercator_meters_per_pixel(zoom)
        detail_span_x = W * detail_mpp
        detail_span_y = H * detail_mpp
        detail_bbox = (cx - detail_span_x / 2, cy - detail_span_y / 2,
                       cx + detail_span_x / 2, cy + detail_span_y / 2)
    detail_ground_mpp = detail_mpp * math.cos(math.radians(lat))
    wide_mpp = detail_mpp * wide_factor
    wide_ground_mpp = detail_ground_mpp * wide_factor
    wide_span_x = detail_span_x * wide_factor
    wide_span_y = detail_span_y * wide_factor
    wide_bbox = (cx - wide_span_x / 2, cy - wide_span_y / 2,
                 cx + wide_span_x / 2, cy + wide_span_y / 2)

    z_detail, up_detail = choose_tile_zoom(detail_ground_mpp, lat, source["max_zoom"])
    z_wide, up_wide = choose_tile_zoom(wide_ground_mpp, lat, source["max_zoom"])

    # ---- satellite backgrounds ------------------------------------------
    progress("tiles", 0.0, "starting satellite downloads")
    detail_img = stitch_bbox(source, source_key, z_detail, detail_bbox, (W, H),
                             progress, "tiles_detail")
    progress("tiles", 60.0, "detail background stitched")
    wide_img = stitch_bbox(source, source_key, z_wide, wide_bbox, (W, H),
                           progress, "tiles_wide")
    progress("tiles", 100.0, "wide background stitched")

    detail_path = out_dir / "satellite_detail.png"
    wide_path = out_dir / "satellite_wide.png"
    detail_img.save(detail_path)
    wide_img.save(wide_path)

    # ---- masks -----------------------------------------------------------
    masks: List[dict] = []
    n = len(iso_list)
    for i, iso in enumerate(iso_list):
        progress("masks", 100.0 * i / n, f"rendering mask {iso}")
        colors = config.get("country_colors") or {}
        color, rgb = parse_hex_color(colors.get(iso, country_default_color(iso)))
        geometry = get_geometry(iso)
        mask_img, bounds_px = render_mask(geometry, detail_bbox, (W, H), rgb)
        mask_path = out_dir / f"mask_{iso}.png"
        mask_img.save(mask_path)
        svg_text = render_mask_svg(geometry, detail_bbox, (W, H), color)
        svg_path = out_dir / f"mask_{iso}.svg"
        svg_path.write_text(svg_text, encoding="utf-8")
        # Keep the original vector source with the package. Fusion generation
        # can use these points directly instead of rasterising the PNG mask.
        geometry_path = out_dir / f"geometry_{iso}.geojson"
        geometry_path.write_text(json.dumps({"type": "Feature", "properties": {
            "iso3": iso, "color": color}, "geometry": geometry}, indent=2), encoding="utf-8")
        masks.append({
            "iso3": iso,
            "color": color,
            "border_color": DEFAULT_BORDER_COLOR,
            "file": mask_path.name,
            "svg_file": svg_path.name,
            "geometry_file": geometry_path.name,
            "bounds_px": {"x0": bounds_px[0], "y0": bounds_px[1],
                          "x1": bounds_px[2], "y1": bounds_px[3]},
        })
    progress("masks", 100.0, "masks rendered")

    # ---- alignment check image ------------------------------------------
    progress("check", 50.0, "building alignment check image")
    bg = detail_img.convert("RGB")
    overlay = Image.new("RGB", bg.size, (255, 40, 40))
    alpha_all = Image.new("L", bg.size, 0)
    for m in masks:
        am = Image.open(out_dir / m["file"]).getchannel("A")
        a_np = np.asarray(am)
        cur = np.asarray(alpha_all)
        alpha_all = Image.fromarray(np.maximum(cur, a_np))
    half = alpha_all.point(lambda a: a // 2)
    check = Image.composite(overlay, bg, half)
    check_path = out_dir / "alignment_check.jpg"
    check.save(check_path, quality=90)

    # ---- metadata --------------------------------------------------------
    progress("metadata", 50.0, "writing metadata")
    files = {
        "satellite_detail.png": detail_path,
        "satellite_wide.png": wide_path,
        "alignment_check.jpg": check_path,
    }
    for m in masks:
        files[m["file"]] = out_dir / m["file"]
        files[m["svg_file"]] = out_dir / m["svg_file"]
        files[m["geometry_file"]] = out_dir / m["geometry_file"]
    file_info = {fn: {"sha256": _sha256(p), "bytes": p.stat().st_size}
                 for fn, p in files.items()}

    metadata = {
        "app": "map-asset-app 0.1",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "crs": "EPSG:3857",
        "output": {
            "width": W,
            "height": H,
            "orientation": orientation,
            "resolution": resolution,
            "wide_factor": wide_factor,
        },
        "center": {"lat": lat, "lng": lng},
        "zoom_requested": zoom,
        "detail": {
            "bbox_mercator": {"minx": detail_bbox[0], "miny": detail_bbox[1],
                              "maxx": detail_bbox[2], "maxy": detail_bbox[3]},
            "meters_per_pixel": detail_mpp,
            "ground_meters_per_pixel_at_center": detail_ground_mpp,
            "tile_zoom": z_detail,
            "tile_zoom_upscaled": up_detail,
            "pixel_transform": {
                "origin_top_left_mercator": [detail_bbox[0], detail_bbox[3]],
                "meters_per_pixel_x": detail_mpp,
                "meters_per_pixel_y": detail_mpp,
                "formula": "px = (merc_x - x0) / mpp ; py = (y0 - merc_y) / mpp",
            },
            "corner_latlng": {
                "top_left": merc_to_ll(detail_bbox[0], detail_bbox[3]),
                "bottom_right": merc_to_ll(detail_bbox[2], detail_bbox[1]),
            },
        },
        "wide": {
            "bbox_mercator": {"minx": wide_bbox[0], "miny": wide_bbox[1],
                              "maxx": wide_bbox[2], "maxy": wide_bbox[3]},
            "meters_per_pixel": wide_mpp,
            "ground_meters_per_pixel_at_center": wide_ground_mpp,
            "tile_zoom": z_wide,
            "tile_zoom_upscaled": up_wide,
            "covers_factor": wide_factor,
            "same_center_as_detail": True,
        },
        "fusion_notes": {
            "detail_plane_scale": 1.0,
            "wide_plane_scale": wide_factor,
            "wide_plane_z_offset_suggestion": -0.001,
            "note": ("If the detail ImagePlane3D is placed at scale 1, the wide "
                     "plane should be scaled by wide_factor so both cover the "
                     "correct geographic area; keep its center aligned."),
        },
        "countries": masks,
        "imagery": {
            "source": source_key,
            "attribution": source["attribution"],
            "note": source["note"],
        },
        "boundaries": {
            "dataset": "Natural Earth 10m Admin 0 - Countries",
            "url": COUNTRIES_URL,
            "license": "public domain (Natural Earth)",
        },
        "files": file_info,
    }
    meta_path = out_dir / "metadata.json"
    meta_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False))

    progress("done", 100.0, f"export complete -> {out_dir}")
    return {
        "output_dir": str(out_dir),
        "files": sorted(p.name for p in out_dir.iterdir()),
        "metadata": metadata,
        "elapsed_sec": round(time.time() - t0, 1),
    }
