"""Administrative and historical sub-territory catalogs.

Administrative boundaries are cached from Natural Earth on first use.  The
small U.S. historical catalog is versioned with the application so saved shots
remain reproducible and never need the network.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable

import requests

from core import package_layout

APP_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DATA = APP_ROOT / "runtime" / "data"
ADMIN1_FILE = RUNTIME_DATA / "ne_10m_admin_1_states_provinces.geojson"
ADMIN1_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
    "master/geojson/ne_10m_admin_1_states_provinces.geojson"
)
HISTORICAL_FILE = APP_ROOT / "resources" / "us_historical_regions.geojson"
REGION_ID = re.compile(r"[a-z0-9][a-z0-9_.-]{0,119}")


def ensure_admin1_file() -> Path:
    if ADMIN1_FILE.exists() and ADMIN1_FILE.stat().st_size > 1_000_000:
        return ADMIN1_FILE
    RUNTIME_DATA.mkdir(parents=True, exist_ok=True)
    response = requests.get(ADMIN1_URL, timeout=180, headers={
        "User-Agent": "map-asset-app/0.1 (local personal map-video tool)",
    })
    response.raise_for_status()
    temporary = ADMIN1_FILE.with_suffix(".tmp")
    temporary.write_bytes(response.content)
    temporary.replace(ADMIN1_FILE)
    return ADMIN1_FILE


def _features(category: str) -> Iterable[dict]:
    path = ensure_admin1_file() if category == "administrative" else HISTORICAL_FILE
    return json.loads(path.read_text(encoding="utf-8")).get("features", [])


def _admin_country(properties: dict) -> str:
    return str(properties.get("adm0_a3") or properties.get("ADM0_A3") or "").upper()


def _admin_id(properties: dict) -> str:
    code = properties.get("iso_3166_2") or properties.get("code_hasc")
    if code:
        return "admin-" + re.sub(r"[^a-z0-9]+", "-", str(code).lower()).strip("-")
    name = properties.get("name_en") or properties.get("name") or "region"
    return "admin-" + re.sub(r"[^a-z0-9]+", "-", str(name).lower()).strip("-")


def catalog(country: str, category: str) -> list[dict]:
    country = str(country).upper()
    if category not in {"administrative", "historical"}:
        raise ValueError("category must be administrative or historical")
    if category == "historical" and country != "USA":
        return []
    result = []
    for feature in _features(category):
        properties = feature.get("properties") or {}
        if category == "administrative":
            if _admin_country(properties) != country:
                continue
            identifier = _admin_id(properties)
            name = properties.get("name_en") or properties.get("name") or identifier
            result.append({"id": identifier, "name": name, "category": category})
        else:
            result.append({
                "id": properties["id"], "name": properties["name"],
                "year": properties["year"], "category": category,
            })
    return sorted(result, key=lambda item: (item.get("year", 0), str(item["name"])))


def geometry(country: str, category: str, identifier: str) -> dict:
    if not REGION_ID.fullmatch(str(identifier)):
        raise KeyError("invalid sub-territory id")
    country = str(country).upper()
    for feature in _features(category):
        properties = feature.get("properties") or {}
        if category == "administrative":
            if _admin_country(properties) == country and _admin_id(properties) == identifier:
                return feature["geometry"]
        elif country == "USA" and properties.get("id") == identifier:
            if properties.get("admin1_iso"):
                return _admin_geometry_by_iso(str(properties["admin1_iso"]))
            return feature["geometry"]
    raise KeyError(f"sub-territory not found: {identifier}")


def _admin_geometry_by_iso(iso: str) -> dict:
    for feature in _features("administrative"):
        properties = feature.get("properties") or {}
        if str(properties.get("iso_3166_2") or "").upper() == iso.upper():
            return feature["geometry"]
    raise KeyError(f"administrative division not found: {iso}")


def materialize(package: Path, animation: dict) -> dict:
    """Copy selected source geometry into a package and record safe paths."""
    region_relative = package_layout.data_relative(package, "regions")
    folder = package / region_relative
    requested = [child for group in animation.get("region_groups", [])
                 for child in group.get("children", []) if child.get("category") != "country"]
    if requested:
        folder.mkdir(exist_ok=True)
    keep = set()
    for group in animation.get("region_groups", []):
        country = group["iso3"]
        for child in group.get("children", []):
            if child.get("category") == "country":
                child.pop("geometry_file", None)
                continue
            safe = re.sub(r"[^A-Za-z0-9_.-]", "_", child["id"])
            relative = region_relative / f"geometry_{safe}.geojson"
            target = package / relative
            payload = {"type": "Feature", "properties": {
                "id": child["id"], "name": child["name"],
                "category": child["category"], "country": country,
            }, "geometry": geometry(country, child["category"], child["id"])}
            temporary = target.with_suffix(".tmp")
            temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            temporary.replace(target)
            child["geometry_file"] = str(relative)
            keep.add(target.resolve())
    if folder.is_dir():
        for path in folder.glob("geometry_*.geojson"):
            if path.resolve() not in keep:
                path.unlink()
        if not any(folder.iterdir()):
            folder.rmdir()
    return animation
