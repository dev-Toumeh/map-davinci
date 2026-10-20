"""Persistent app settings shared by the HTTP server and the exporter.

Settings live in ``app/runtime/settings.json`` so custom choices survive restarts. With
no override, exports are stored in ``exports/`` at the application root. The
main page can select a different folder, and both pages use that shared path.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
SETTINGS_FILE = APP_ROOT / "runtime" / "settings.json"
DEFAULT_EXPORTS_DIR = APP_ROOT.parent / "exports"
DEFAULT_GOOGLE_MAPS_DAILY_WARNING = 3000


def load() -> dict:
    try:
        value = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save(settings: dict) -> None:
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = SETTINGS_FILE.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    temporary.replace(SETTINGS_FILE)


def has_exports_override() -> bool:
    """Return whether the user selected a custom export folder."""
    return bool(str(load().get("exports_path") or "").strip())


def exports_dir() -> Path:
    """Current export folder. Relative paths resolve against the repo root."""
    custom = str(load().get("exports_path") or "").strip()
    path = Path(custom).expanduser() if custom else DEFAULT_EXPORTS_DIR
    if not path.is_absolute():
        path = (APP_ROOT.parent / path)
    return path


def google_maps_api_key() -> str:
    """Server-side Map Tiles API key; never return this through the HTTP API."""
    return str(os.environ.get("GOOGLE_MAPS_API_KEY") or
               load().get("google_maps_api_key") or "").strip()


def gif_exports_dir() -> Path:
    """GIF-specific override; otherwise use the current map export folder."""
    raw = str(load().get("gif_exports_path") or "").strip()
    if not raw:
        return exports_dir().resolve() / "gif-loops"
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = APP_ROOT.parent / path
    return path.resolve()


def has_google_maps_api_key() -> bool:
    return bool(google_maps_api_key())


def google_maps_daily_warning() -> int:
    try:
        value = int(load().get("google_maps_daily_warning",
                               DEFAULT_GOOGLE_MAPS_DAILY_WARNING))
    except (TypeError, ValueError):
        value = DEFAULT_GOOGLE_MAPS_DAILY_WARNING
    return max(1, value)
