#!/usr/bin/env python3
"""Build the small U.S. historical boundary bundle used by the editor.

The National Atlas is the cartographic source.  The public ArcGIS feature
service credited to the National Atlas supplies geographic registration for
the mainland polygons, matching the established Louisiana workflow.  Hawaii
is resolved from Natural Earth Admin-1 at runtime.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "resources" / "us_historical_regions.geojson"
SERVICE = "https://services1.arcgis.com/TQSFiGYN0xveoERF/arcgis/rest/services/territorial_expansion_17/FeatureServer"
LAYERS = [
    (0, "us-original-1783", "Original U.S. Territory", 1783),
    (5, "louisiana-purchase-1803", "Louisiana Purchase", 1803),
    (8, "florida-cession-1819", "Florida Cession", 1819),
    (4, "texas-annexation-1845", "Texas Annexation", 1845),
    (6, "oregon-territory-1846", "Oregon Territory", 1846),
    (7, "mexican-cession-1848", "Mexican Cession", 1848),
    (1, "alaska-purchase-1867", "Alaska Purchase", 1867),
]


def fetch(layer: int) -> list[dict]:
    query = urllib.parse.urlencode({
        "where": "1=1", "outFields": "*", "returnGeometry": "true",
        "outSR": "4326", "geometryPrecision": "4",
        "maxAllowableOffset": "0.02", "f": "geojson",
    })
    request = urllib.request.Request(f"{SERVICE}/{layer}/query?{query}", headers={
        "User-Agent": "map-asset-app historical-boundary builder",
    })
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response).get("features", [])


def combined(layer: int, identifier: str, name: str, year: int) -> dict:
    features = fetch(layer)
    if identifier == "texas-annexation-1845":
        features = [feature for feature in features
                    if (feature.get("properties") or {}).get("NAME") == "Texas Annexation"]
    geometries = [feature["geometry"] for feature in features if feature.get("geometry")]
    polygons = []
    for geometry in geometries:
        if geometry["type"] == "Polygon":
            polygons.append(geometry["coordinates"])
        elif geometry["type"] == "MultiPolygon":
            polygons.extend(geometry["coordinates"])
    return {"type": "Feature", "properties": {
        "id": identifier, "name": name, "year": year,
        "source": "National Atlas territorial acquisitions",
    }, "geometry": {"type": "MultiPolygon", "coordinates": polygons}}


features = [combined(*spec) for spec in LAYERS]
features.append({"type": "Feature", "properties": {
    "id": "hawaii-annexation-1898", "name": "Hawaii Annexation", "year": 1898,
    "admin1_iso": "US-HI", "source": "Natural Earth Admin-1",
}, "geometry": None})
OUTPUT.write_text(json.dumps({
    "type": "FeatureCollection",
    "metadata": {
        "cartographic_source": "U.S. Geological Survey, National Atlas Territorial Acquisitions",
        "registration_service": SERVICE,
        "registration_license": "For educational use only (service metadata)",
        "national_atlas_status": "U.S. government map; public domain in the United States",
        "usage_note": "Small-scale educational visualization; boundaries are not survey accurate.",
    },
    "features": features,
}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print(OUTPUT)
