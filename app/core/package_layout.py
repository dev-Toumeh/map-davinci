"""Paths for structured export packages with legacy flat-package support."""
from __future__ import annotations

from pathlib import Path


VERSION = 2
IMAGES_DIR = Path("images")
JSON_DIR = Path("json")
DATA_DIR = Path("data")
SOUNDS_DIR = Path("sounds")
FUSION_DIR = Path("fusion")
VIDEOS_DIR = Path("videos")
CLOSEUPS_DIR = IMAGES_DIR / "closeups"
LEGACY_CLOSEUPS_DIR = Path("closeups")
STRUCTURED_DIRS = (IMAGES_DIR, JSON_DIR, DATA_DIR, SOUNDS_DIR, FUSION_DIR, VIDEOS_DIR)

METADATA_FILE = JSON_DIR / "metadata.json"
ANIMATION_FILE = JSON_DIR / "animation.json"
SATELLITE_DETAIL_FILE = IMAGES_DIR / "satellite_detail.png"
SATELLITE_WIDE_FILE = IMAGES_DIR / "satellite_wide.png"
ALIGNMENT_CHECK_FILE = IMAGES_DIR / "alignment_check.jpg"

LEGACY_METADATA_FILE = Path("metadata.json")
LEGACY_ANIMATION_FILE = Path("animation.json")
LEGACY_SATELLITE_DETAIL_FILE = Path("satellite_detail.png")
LEGACY_SATELLITE_WIDE_FILE = Path("satellite_wide.png")
LEGACY_ALIGNMENT_CHECK_FILE = Path("alignment_check.jpg")


def manifest() -> dict:
    return {
        "version": VERSION,
        "directories": {
            "images": str(IMAGES_DIR), "json": str(JSON_DIR),
            "data": str(DATA_DIR), "sounds": str(SOUNDS_DIR),
            "fusion": str(FUSION_DIR), "videos": str(VIDEOS_DIR),
        },
        "files": {"metadata": str(METADATA_FILE), "animation": str(ANIMATION_FILE)},
    }


def default_assets() -> dict:
    return {
        "satellite_detail": str(SATELLITE_DETAIL_FILE),
        "satellite_wide": str(SATELLITE_WIDE_FILE),
        "alignment_check": str(ALIGNMENT_CHECK_FILE),
    }


def legacy_manifest() -> dict:
    return {
        "version": 1,
        "directories": {"fusion": str(FUSION_DIR), "videos": str(VIDEOS_DIR)},
        "files": {"metadata": str(LEGACY_METADATA_FILE),
                  "animation": str(LEGACY_ANIMATION_FILE)},
    }


def legacy_assets() -> dict:
    return {
        "satellite_detail": str(LEGACY_SATELLITE_DETAIL_FILE),
        "satellite_wide": str(LEGACY_SATELLITE_WIDE_FILE),
        "alignment_check": str(LEGACY_ALIGNMENT_CHECK_FILE),
    }


def describe(package: Path, metadata: dict) -> dict:
    described = dict(metadata)
    if structured(package):
        described.setdefault("package_layout", manifest())
        described.setdefault("assets", default_assets())
    else:
        described.setdefault("package_layout", legacy_manifest())
        described.setdefault("assets", legacy_assets())
    return described


def mask_png(iso3: str) -> Path:
    return IMAGES_DIR / f"mask_{iso3}.png"


def mask_svg(iso3: str) -> Path:
    return IMAGES_DIR / f"mask_{iso3}.svg"


def country_geometry(iso3: str) -> Path:
    return DATA_DIR / f"geometry_{iso3}.geojson"


def create(package: Path) -> None:
    for name in STRUCTURED_DIRS:
        (package / name).mkdir(parents=True, exist_ok=True)


def structured(package: Path) -> bool:
    return (package / METADATA_FILE).is_file()


def metadata_path(package: Path) -> Path:
    nested = package / METADATA_FILE
    return nested if nested.is_file() else package / LEGACY_METADATA_FILE


def animation_path(package: Path) -> Path:
    return package / ANIMATION_FILE if structured(package) else package / LEGACY_ANIMATION_FILE


def data_relative(package: Path, *parts: str) -> Path:
    prefix = DATA_DIR if structured(package) else Path()
    return prefix.joinpath(*parts)


def sounds_relative(package: Path, filename: str) -> Path:
    return SOUNDS_DIR / filename if structured(package) else Path(filename)


def closeups_relative(package: Path) -> Path:
    return CLOSEUPS_DIR if structured(package) else LEGACY_CLOSEUPS_DIR


def asset_relative(metadata: dict, key: str, legacy_name: str) -> Path:
    return Path((metadata.get("assets") or {}).get(key) or legacy_name)
