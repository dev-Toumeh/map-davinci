"""Export one clean map image from the MapSnap frame."""
from __future__ import annotations

import math
import re
from pathlib import Path

from core import exporter, settings

ASPECTS = {
    "16:9": (16, 9), "9:16": (9, 16), "1:1": (1, 1),
    "4:3": (4, 3), "3:4": (3, 4), "3:2": (3, 2),
    "2:3": (2, 3), "4:5": (4, 5), "5:4": (5, 4),
}
LONG_EDGES = {"4k": 3840, "fhd": 1920, "hd": 1280, "750": 750}


def dimensions(aspect: str, resolution: str) -> tuple[int, int]:
    if aspect not in ASPECTS:
        raise ValueError("unsupported aspect ratio")
    if resolution not in LONG_EDGES:
        raise ValueError("unsupported resolution")
    x, y = ASPECTS[aspect]
    edge = LONG_EDGES[resolution]
    if x >= y:
        return edge, round(edge * y / x)
    return round(edge * x / y), edge


def validate(config: dict) -> dict:
    aspect = str(config.get("aspect", "16:9"))
    resolution = str(config.get("resolution", "4k")).lower()
    width, height = dimensions(aspect, resolution)
    source_key = str(config.get("source", "esri_world_imagery"))
    if source_key not in exporter.SOURCES:
        raise ValueError("unsupported map source")
    if source_key == "google_simple_map" and not settings.has_google_maps_api_key():
        raise ValueError("Ivory Teal Map requires a configured Google Maps API key")
    raw_name = str(config.get("name", "")).strip()
    name = re.sub(r"[^A-Za-z0-9_.-]+", "_", raw_name).strip("._-")[:100]
    if not name:
        raise ValueError("enter an image name")
    raw_folder = str(config.get("output_folder") or "").strip()
    if not raw_folder:
        raise ValueError("choose an output folder")
    folder = Path(raw_folder).expanduser()
    if not folder.is_absolute():
        raise ValueError("output folder must be an absolute path")
    folder = folder.resolve()
    if folder.exists() and not folder.is_dir():
        raise ValueError("output location is not a folder")
    box = config.get("bbox_mercator")
    if not isinstance(box, dict):
        raise ValueError("map frame is missing")
    try:
        minx, miny, maxx, maxy = (float(box[k]) for k in ("minx", "miny", "maxx", "maxy"))
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("map frame needs numeric bounds") from exc
    if not all(math.isfinite(v) for v in (minx, miny, maxx, maxy)):
        raise ValueError("map frame bounds must be finite")
    if not (-exporter.MERC_MAX <= minx < maxx <= exporter.MERC_MAX
            and -exporter.MERC_MAX <= miny < maxy <= exporter.MERC_MAX):
        raise ValueError("map frame is outside the supported map area")
    mpp_x = (maxx - minx) / width
    mpp_y = (maxy - miny) / height
    if abs(mpp_x - mpp_y) > mpp_x * .002:
        raise ValueError("map frame aspect does not match the selected image shape")
    return {"name": name, "folder": folder, "source": source_key,
            "bbox": (minx, miny, maxx, maxy), "size": (width, height)}


def export_image(config: dict, progress) -> dict:
    job = validate(config)
    minx, miny, maxx, maxy = job["bbox"]
    width, height = job["size"]
    _, lat = exporter.merc_to_ll((minx + maxx) / 2, (miny + maxy) / 2)
    ground_mpp = (maxx - minx) / width * math.cos(math.radians(lat))
    source = exporter.SOURCES[job["source"]]
    zoom, _ = exporter.choose_tile_zoom(ground_mpp, lat, source["max_zoom"])
    progress("tiles", 0, "fetching map imagery")
    image = exporter.stitch_bbox(source, job["source"], zoom, job["bbox"],
                                 job["size"], progress, "tiles")
    folder = job["folder"]
    folder.mkdir(parents=True, exist_ok=True)
    for suffix in range(1, 10000):
        filename = f"{job['name']}{'' if suffix == 1 else '_' + str(suffix)}.png"
        path = folder / filename
        try:
            with path.open("xb") as target:
                image.save(target, format="PNG")
            break
        except FileExistsError:
            continue
        except Exception:
            path.unlink(missing_ok=True)
            raise
    else:
        raise ValueError("too many images with this name")
    progress("done", 100, f"saved {filename}")
    return {"path": str(path), "filename": filename,
            "width": width, "height": height}
