"""
map-asset-app / server.py

Local web app server (stdlib only). Binds to 127.0.0.1 only.

  python3 server.py            -> http://127.0.0.1:8787

Endpoints:
  GET  /                          -> static/index.html
  GET  /gif                       -> GIF-to-Fusion converter
  POST /api/gif?name=<name>&fps=<fps> -> raw GIF upload and loop package
  GET  /static/*                  -> UI assets
  GET  /exports/*                 -> exported files (for inspection)
  GET  /api/health                -> ok
  GET  /api/countries             -> country index (downloads NE file on first call)
  GET  /api/country/<ISO3>        -> GeoJSON geometry for preview outline
  GET  /api/subterritories/<ISO3>/<category> -> administrative/historical catalog
  GET  /api/subterritory/<ISO3>/<category>/<id> -> one region geometry
  GET  /api/map-tiles/google-simple/z/x/y -> styled Google roadmap tile
  POST /api/export                -> start export job {json body}
   GET  /api/export/status/<id>    -> job progress/result
   GET  /api/exports                -> available export packages
   GET/POST /api/animation/<name>   -> read/save a shot animation
   GET  /api/animation/<name>/reference-videos -> list package videos
   POST /api/animation/<name>/reference-video -> upload videos/reference.mp4
   POST /api/animation/<name>/scan-motion -> propose camera keyframes
   POST /api/animation/<name>/fusion -> generate scene.comp
   POST /api/export/<name>/delete     -> permanently remove one package
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import shutil
import subprocess
import threading
import traceback
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote, parse_qs, urlsplit

from core import animation_schema, exporter, map_snap, motion_scan, package_layout, regions, settings as app_settings
from fusion import generator as fusion_generator
from fusion import region_closeup
from core import gif_loop
from core import archive_carousel_service

APP_ROOT = Path(__file__).resolve().parent
STATIC_DIR = APP_ROOT / "static"
LOG_DIR = APP_ROOT / "runtime" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(filename=LOG_DIR / "animation-errors.log", level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger("map-asset-app")

HOST = "127.0.0.1"
PORT = 8787

JOBS: dict = {}          # job_id -> {"status": {...}, "result": {...} | None}
JOBS_LOCK = threading.Lock()
EXPORT_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,119}")
MAX_REFERENCE_UPLOAD_BYTES = 1024 * 1024 * 1024

MIME = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".png": "image/png",
    ".gif": "image/gif",
    ".setting": "application/octet-stream",
    ".zip": "application/zip",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".json": "application/json",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".m4v": "video/x-m4v",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".aac": "audio/aac",
    ".ogg": "audio/ogg",
    ".opus": "audio/ogg",
    ".webm": "audio/webm",
    ".flac": "audio/flac",
}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "map-asset-app/0.1"

    # ---- helpers ---------------------------------------------------------

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code: int = 200) -> None:
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"),
                   "application/json")

    def _file(self, path: Path, root: Path) -> None:
        try:
            resolved = path.resolve()
            if not resolved.is_relative_to(root.resolve()):
                self._json({"error": "forbidden"}, 403)
                return
            if not resolved.is_file():
                self._json({"error": "not found"}, 404)
                return
            content_type = MIME.get(resolved.suffix.lower(), "application/octet-stream")
            if resolved.suffix.lower() == ".webm" and resolved.parent.name == "videos":
                content_type = "video/webm"
            if content_type.startswith("video/"):
                size = resolved.stat().st_size
                requested = self.headers.get("Range", "")
                match = re.fullmatch(r"bytes=(\d+)-(\d*)", requested)
                if match:
                    start = int(match.group(1))
                    end = min(size - 1, int(match.group(2))) if match.group(2) else size - 1
                    if start >= size or end < start:
                        self.send_response(416)
                        self.send_header("Content-Range", f"bytes */{size}")
                        self.send_header("Content-Length", "0")
                        self.end_headers()
                        return
                    with resolved.open("rb") as source:
                        source.seek(start)
                        data = source.read(end - start + 1)
                    self.send_response(206)
                    self.send_header("Content-Type", content_type)
                    self.send_header("Content-Length", str(len(data)))
                    self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
                    self.send_header("Accept-Ranges", "bytes")
                    self.end_headers()
                    self.wfile.write(data)
                    return
            data = resolved.read_bytes()
            # Earlier uploads truncated long filenames, which also removed the
            # extension. Recognize existing MP3 files so their media elements
            # receive a playable content type.
            if content_type == "application/octet-stream" and (
                    data.startswith(b"ID3") or data[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2")):
                content_type = "audio/mpeg"
            self._send(200, data, content_type)
        except Exception as exc:  # noqa: BLE001
            self._json({"error": str(exc)}, 500)

    def log_message(self, fmt, *args):  # quieter console
        pass

    def _save_settings(self, config: dict) -> None:
        """Persist a new export folder, optionally migrating existing packages.

        Fusion comps embed absolute asset paths, so a move rewrites those
        references (with a .comp.bak backup next to each updated file).
        """
        use_default = bool(config.get("use_default"))
        raw = str(config.get("path") or "").strip()
        if use_default:
            target = app_settings.DEFAULT_EXPORTS_DIR.resolve()
        else:
            if not raw:
                raise ValueError("export folder path is required")
            target = Path(raw).expanduser()
            if not target.is_absolute():
                target = (APP_ROOT.parent / target)
            target = target.resolve()
        current = app_settings.exports_dir()
        if target != current and (target == APP_ROOT or APP_ROOT in target.parents):
            # The legacy default lives inside app/ and stays selectable; new
            # locations must move out so code and user data stay separated.
            raise ValueError("export folder cannot be inside the app folder")
        move = bool(config.get("move_existing"))
        moved = 0
        if move and current != target:
            if not current.is_dir():
                raise ValueError(f"current export folder does not exist: {current}")
            if target.exists() and any(target.iterdir()):
                raise ValueError(f"target folder is not empty: {target}")
            target.mkdir(parents=True, exist_ok=True)
            old_text = str(current)
            for child in sorted(current.iterdir()):
                shutil.move(str(child), str(target / child.name))
                moved += 1
            try:
                current.rmdir()
            except OSError:
                pass
            # Rewrite absolute asset paths inside moved Fusion compositions.
            for comp in target.rglob("*.comp"):
                try:
                    text = comp.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    continue
                if old_text in text:
                    backup = comp.with_suffix(comp.suffix + ".bak")
                    if not backup.exists():
                        backup.write_text(text, encoding="utf-8")
                    comp.write_text(text.replace(old_text, str(target)), encoding="utf-8")
        saved = app_settings.load()
        if use_default:
            saved.pop("exports_path", None)
        else:
            saved["exports_path"] = str(target)
        google_key = str(config.get("google_maps_api_key") or "").strip()
        if google_key:
            saved["google_maps_api_key"] = google_key
        if "google_maps_daily_warning" in config:
            try:
                warning_limit = int(config["google_maps_daily_warning"])
            except (TypeError, ValueError) as exc:
                raise ValueError("daily tile warning must be a whole number") from exc
            if warning_limit < 1:
                raise ValueError("daily tile warning must be at least 1")
            saved["google_maps_daily_warning"] = warning_limit
        app_settings.save(saved)
        LOGGER.info("Export folder set to %s (moved %d packages)", target, moved)
        self._json({"ok": True, "exports_path": str(target), "moved": moved,
                    "using_default": use_default})

    def _choose_exports_folder(self, prompt: str = "Choose exports folder") -> None:
        """Open the macOS folder picker for this local desktop application."""
        script = f'POSIX path of (choose folder with prompt "{prompt}")'
        result = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True, check=False
        )
        if result.returncode:
            if "User canceled" in result.stderr or "(-128)" in result.stderr:
                self._json({"cancelled": True})
                return
            raise RuntimeError(result.stderr.strip() or "Could not open the folder picker")
        selected = Path(result.stdout.strip()).expanduser().resolve()
        self._json({"path": str(selected)})

    def _package(self, name: str) -> Path:
        if not EXPORT_NAME.fullmatch(name):
            raise ValueError("invalid export package name")
        exports_dir = app_settings.exports_dir()
        package = (exports_dir / name).resolve()
        if (package.parent != exports_dir.resolve()
                or not package_layout.metadata_path(package).is_file()):
            raise FileNotFoundError("export package not found")
        return package

    def _metadata(self, package: Path) -> dict:
        metadata = json.loads(package_layout.metadata_path(package).read_text(encoding="utf-8"))
        return package_layout.describe(package, metadata)

    def _animation_response(self, package: Path) -> dict:
        path = package_layout.animation_path(package)
        return {"export": package.name, "metadata": self._metadata(package),
                "animation": json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None}

    def _normalize_animation(self, package: Path, config: dict) -> dict:
        """Normalize a browser save without losing saved Fusion calibration.

        A browser tab opened before a calibration was added has no fusion_path
        field. Preserve the existing per-frame calibration in that case rather
        than silently replacing it with the old browser payload.
        """
        # A shot duration can be shortened after connections were authored.
        # Keep those legacy connections editable by fitting their timing inside
        # the new valid frame range before schema validation.
        config = dict(config)
        duration = int((config.get("output") or {}).get("duration_frames", 0) or 0)
        if duration >= 3 and isinstance(config.get("connections"), list):
            repaired = []
            for connection in config["connections"]:
                connection = dict(connection)
                start = max(0, min(int(connection.get("start_frame", 0)), duration - 3))
                arrival = max(start + 1, min(int(connection.get("arrival_frame", start + 1)), duration - 2))
                pinned_to_end = connection.get("disappearance_frame") is None
                raw_disappearance = duration - 1 if pinned_to_end else connection.get("disappearance_frame")
                disappearance = max(arrival + 1, min(int(raw_disappearance), duration - 1))
                connection.update(start_frame=start, arrival_frame=arrival,
                                  disappearance_frame=None if pinned_to_end else disappearance)
                repaired.append(connection)
            config["connections"] = repaired
        if duration >= 1 and isinstance(config.get("region_groups"), list):
            repaired_groups = []
            for source_group in config["region_groups"]:
                group = dict(source_group)
                def fit_timing(item: dict) -> dict:
                    item = dict(item)
                    for key in ("start_frame", "end_frame"):
                        if item.get(key) not in (None, ""):
                            item[key] = max(0, min(int(item[key]), duration - 1))
                    if (item.get("start_frame") is not None and
                            item.get("end_frame") is not None and
                            item["start_frame"] >= item["end_frame"]):
                        if duration < 2:
                            item["end_frame"] = None
                        else:
                            item["start_frame"] = min(item["start_frame"], duration - 2)
                            item["end_frame"] = max(item["start_frame"] + 1,
                                                    item["end_frame"])
                    return item
                group = fit_timing(group)
                group["children"] = [fit_timing(child)
                                     for child in group.get("children", [])]
                repaired_groups.append(group)
            config["region_groups"] = repaired_groups
        animation = animation_schema.normalize_animation(config, self._metadata(package))
        target = package_layout.animation_path(package)
        if target.is_file():
            existing = animation_schema.normalize_animation(
                json.loads(target.read_text(encoding="utf-8")), self._metadata(package))
            paths = {key["frame"]: key["fusion_path"] for key in existing["keyframes"]
                     if key.get("fusion_path")}
            for key in animation["keyframes"]:
                if "fusion_path" not in key and key["frame"] in paths:
                    key["fusion_path"] = paths[key["frame"]]
            # A tab opened before commentary existed sends no commentary field; keep
            # the saved narration reference instead of erasing it.
            if "commentary" not in config:
                animation["commentary"] = existing["commentary"]
        return regions.materialize(package, animation)

    def _add_animation_country(self, package: Path, config: dict) -> dict:
        """Add one vector country to an existing animation package."""
        iso3 = str(config.get("iso3", "")).upper()
        if not re.fullmatch(r"[A-Z0-9]{3}", iso3):
            raise ValueError("select a valid country")
        catalog = {item["iso3"]: item for item in exporter.load_countries()}
        if iso3 not in catalog:
            raise ValueError(f"country not found: {iso3}")

        metadata = self._metadata(package)
        if any(str(item.get("iso3", "")).upper() == iso3
               for item in metadata.get("countries", [])):
            raise ValueError(f"{catalog[iso3]['name']} is already in this animation")

        color, _ = exporter.parse_hex_color(
            config.get("color") or catalog[iso3].get("default_color")
            or exporter.country_default_color(iso3))
        geometry = exporter.get_geometry(iso3)
        geometry_relative = package_layout.data_relative(package, f"geometry_{iso3}.geojson")
        geometry_payload = {
            "type": "Feature",
            "properties": {"iso3": iso3, "color": color},
            "geometry": geometry,
        }
        geometry_bytes = (json.dumps(geometry_payload, indent=2,
                                     ensure_ascii=False) + "\n").encode("utf-8")

        metadata.setdefault("countries", []).append({
            "iso3": iso3,
            "name": catalog[iso3]["name"],
            "color": color,
            "border_color": (catalog[iso3].get("default_border_color")
                             or exporter.country_default_border_color(iso3)),
            "geometry_file": str(geometry_relative),
        })
        metadata.setdefault("files", {})[str(geometry_relative)] = {
            "sha256": hashlib.sha256(geometry_bytes).hexdigest(),
            "bytes": len(geometry_bytes),
        }

        animation_path = package_layout.animation_path(package)
        if not animation_path.is_file():
            raise ValueError("create the animation before adding another country")
        source_animation = json.loads(animation_path.read_text(encoding="utf-8"))
        animation = animation_schema.normalize_animation(source_animation, metadata)
        animation = regions.materialize(package, animation)

        geometry_path = package / geometry_relative
        geometry_path.parent.mkdir(parents=True, exist_ok=True)
        geometry_temp = geometry_path.with_suffix(".geojson.tmp")
        metadata_path = package_layout.metadata_path(package)
        metadata_temp = metadata_path.with_suffix(".json.tmp")
        animation_temp = animation_path.with_suffix(".json.tmp")
        geometry_temp.write_bytes(geometry_bytes)
        metadata_temp.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
        animation_temp.write_text(json.dumps(animation, indent=2) + "\n", encoding="utf-8")
        geometry_temp.replace(geometry_path)
        metadata_temp.replace(metadata_path)
        animation_temp.replace(animation_path)
        return {"ok": True, "metadata": metadata, "animation": animation,
                "country": metadata["countries"][-1], "geometry": geometry}

    # ---- routing ---------------------------------------------------------

    def do_GET(self):  # noqa: N802
        path = self.path.split("?", 1)[0]
        try:
            if path in ("/", "/index.html"):
                self._file(STATIC_DIR / "index.html", STATIC_DIR)
            elif path in ("/MapSnap", "/MapSnap/"):
                self._file(STATIC_DIR / "mapsnap.html", STATIC_DIR)
            elif path in ("/gif", "/gif/"):
                self._file(STATIC_DIR / "gif.html", STATIC_DIR)
            elif path in ("/archive-carousel", "/archive-carousel/"):
                port = self.server.server_address[1]
                address = archive_carousel_service.start(
                    app_settings.exports_dir(), f"http://127.0.0.1:{port}/")
                self.send_response(302)
                self.send_header("Location", address + "/")
                self.send_header("Content-Length", "0")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
            elif path == "/api/gif/settings":
                self._json({"path": str(app_settings.gif_exports_dir()),
                            "default_path": str(app_settings.exports_dir().resolve() / "gif-loops"),
                            "using_default": not bool(app_settings.load().get("gif_exports_path"))})
            elif path.startswith("/api/gif/files/"):
                root = app_settings.gif_exports_dir()
                self._file(root / unquote(path[len("/api/gif/files/"):]), root)
            elif path.startswith("/static/"):
                self._file(STATIC_DIR / path[len("/static/"):], STATIC_DIR)
            elif path.startswith("/exports/"):
                exports_dir = app_settings.exports_dir()
                self._file(exports_dir / unquote(path[len("/exports/"):]), exports_dir)
            elif path == "/api/health":
                self._json({"ok": True})
            elif path == "/api/countries":
                try:
                    self._json({"countries": exporter.load_countries()})
                except Exception as exc:  # noqa: BLE001
                    self._json({"error": f"could not load country boundaries: {exc}"}, 500)
            elif (m := re.fullmatch(r"/api/country/([A-Za-z0-9]{3})", path)):
                try:
                    self._json({"iso3": m.group(1).upper(),
                                "geometry": exporter.get_geometry(m.group(1))})
                except KeyError as exc:
                    self._json({"error": str(exc)}, 404)
            elif (m := re.fullmatch(
                    r"/api/subterritories/([A-Za-z0-9]{3})/(administrative|historical)", path)):
                iso3, category = m.groups()
                self._json({"country": iso3.upper(), "category": category,
                            "regions": regions.catalog(iso3, category)})
            elif (m := re.fullmatch(
                    r"/api/subterritory/([A-Za-z0-9]{3})/(administrative|historical)/([A-Za-z0-9_.-]+)", path)):
                iso3, category, identifier = m.groups()
                try:
                    self._json({"country": iso3.upper(), "category": category,
                                "id": identifier,
                                "geometry": regions.geometry(iso3, category, identifier)})
                except KeyError as exc:
                    self._json({"error": str(exc)}, 404)
            elif (m := re.fullmatch(r"/api/export/status/([a-f0-9-]+)", path)):
                with JOBS_LOCK:
                    job = JOBS.get(m.group(1))
                    if not job:
                        self._json({"error": "unknown job"}, 404)
                        return
                    self._json({"status": job["status"], "result": job["result"]})
            elif (m := re.fullmatch(
                    r"/api/map-tiles/google-simple/(\d{1,2})/(\d+)/(\d+)", path)):
                tile = exporter.google_simple_tile(*(int(value) for value in m.groups()))
                self._send(200, tile, "image/png")
            elif path == "/api/map-tiles/usage":
                self._json(exporter.google_tile_usage())
            elif path == "/api/settings":
                self._json({"exports_path": str(app_settings.exports_dir()),
                            "default_exports_path": str(app_settings.DEFAULT_EXPORTS_DIR),
                            "using_default": not app_settings.has_exports_override(),
                            "google_maps_api_key_configured":
                                app_settings.has_google_maps_api_key(),
                            "google_maps_daily_warning":
                                app_settings.google_maps_daily_warning(),
                            "google_tile_usage": exporter.google_tile_usage()})
            elif path == "/api/mapsnap/settings":
                self._json({"default_output_folder": str((app_settings.exports_dir() / "MapSnap").resolve()),
                            "google_maps_api_key_configured": app_settings.has_google_maps_api_key()})
            elif path == "/api/exports":
                packages = []
                for candidate in sorted(app_settings.exports_dir().iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
                    if (not candidate.is_dir()
                            or not package_layout.metadata_path(candidate).is_file()):
                        continue
                    metadata = self._metadata(candidate)
                    packages.append({"name": candidate.name, "generated_at": metadata.get("generated_at"),
                                     "output": metadata.get("output"),
                                     "countries": [c.get("iso3") for c in metadata.get("countries", [])],
                                     "has_animation": package_layout.animation_path(candidate).is_file()})
                self._json({"exports": packages})
            elif (m := re.fullmatch(r"/api/animation/([A-Za-z0-9_.-]+)/reference-videos", path)):
                package = self._package(m.group(1))
                video_dir = package / package_layout.VIDEOS_DIR
                videos = []
                if video_dir.is_dir():
                    for item in sorted(video_dir.iterdir()):
                        if item.is_file() and item.suffix.lower() in (".mp4", ".mov", ".m4v", ".webm"):
                            videos.append({"name": item.name,
                                           "url": f"/exports/{quote(package.name)}/videos/{quote(item.name)}"})
                self._json({"videos": videos})
            elif (m := re.fullmatch(r"/api/animation/([A-Za-z0-9_.-]+)", path)):
                self._json(self._animation_response(self._package(m.group(1))))
            else:
                self._json({"error": "not found"}, 404)
        except Exception as exc:  # noqa: BLE001
            LOGGER.exception("GET %s failed", path)
            self._json({"error": str(exc)}, 500)

    def do_POST(self):  # noqa: N802
        path = self.path.split("?", 1)[0]
        try:
            if path == "/api/gif":
                try:
                    length = int(self.headers.get("Content-Length", 0))
                    if not 6 <= length <= gif_loop.MAX_UPLOAD_BYTES:
                        self.close_connection = True
                        self._json({"error": "Choose a GIF file up to 25 MB"}, 413)
                        return
                    query = parse_qs(urlsplit(self.path).query)
                    raw = self.rfile.read(length)
                    if len(raw) != length:
                        raise ValueError("GIF upload ended early")
                    result = gif_loop.create_gif_loop_group(
                        raw, app_settings.exports_dir(),
                        group_name=query.get("name", ["GIFLoop"])[0],
                        timeline_fps=query.get("fps", ["24"])[0],
                        output_dir=app_settings.gif_exports_dir())
                    result["setting_url"] = "/api/gif/files/" + quote(result.pop("setting_relative"), safe="/")
                    result["zip_url"] = "/api/gif/files/" + quote(result.pop("zip_relative"), safe="/")
                    self._json(result)
                except ValueError as exc:
                    self._json({"error": str(exc)}, 400)
                return
            if (m := re.fullmatch(r"/api/animation/([A-Za-z0-9_.-]+)/reference-video", path)):
                package = self._package(m.group(1))
                length = int(self.headers.get("Content-Length", 0))
                if not 12 <= length <= MAX_REFERENCE_UPLOAD_BYTES:
                    raise ValueError("reference MP4 must be between 12 bytes and 1 GB")
                video_dir = package / package_layout.VIDEOS_DIR
                video_dir.mkdir(parents=True, exist_ok=True)
                target = video_dir / "reference.mp4"
                temporary = video_dir / f".reference-{uuid.uuid4().hex}.tmp"
                try:
                    with temporary.open("wb") as destination:
                        header = self.rfile.read(12)
                        if len(header) != 12 or header[4:8] != b"ftyp":
                            raise ValueError("upload an MP4 video")
                        destination.write(header)
                        remaining = length - len(header)
                        while remaining:
                            chunk = self.rfile.read(min(1024 * 1024, remaining))
                            if not chunk:
                                raise ValueError("reference video upload ended early")
                            destination.write(chunk)
                            remaining -= len(chunk)
                    temporary.replace(target)
                finally:
                    temporary.unlink(missing_ok=True)
                self._json({"ok": True, "name": target.name})
                return
            length = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(length)
            # Audio uses multipart; the reference upload is streamed above.
            config = json.loads(raw_body or b"{}") if not path.endswith("/audio") else {}
            if (m := re.fullmatch(r"/api/closeups/([A-Za-z0-9_.-]+)/region", path)):
                package = self._package(m.group(1))
                # Parse and validate synchronously, report expensive work through existing jobs.
                name = config.get("name", "Region")
                if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,79}", name):
                    self._json({"error": "Name must be a Fusion identifier"}, 400)
                    return
                try:
                    import math
                    mpp = float(config["mpp"])
                    if not math.isfinite(mpp) or mpp <= 0:
                        raise ValueError("m/px must be positive and finite")
                    area = config["area"]
                    region_closeup.area_geometry(area, self._metadata(package))
                except (KeyError, TypeError, ValueError, OSError) as exc:
                    self._json({"error": str(exc)}, 400)
                    return
                job_id = str(uuid.uuid4())
                with JOBS_LOCK:
                    JOBS[job_id] = {"status": {"stage": "queued", "pct": 0, "message": "queued"}, "result": None}
                threading.Thread(target=self._run_region_job,
                                 args=(job_id, package, name, area, mpp), daemon=True).start()
                self._json({"job_id": job_id}, 202)
                return
            if path == "/api/gif/settings":
                saved = app_settings.load()
                if config.get("use_default"):
                    saved.pop("gif_exports_path", None)
                else:
                    raw = str(config.get("path") or "").strip()
                    if not raw:
                        self._json({"error": "GIF export folder path is required"}, 400)
                        return
                    target = Path(raw).expanduser()
                    if not target.is_absolute():
                        target = APP_ROOT.parent / target
                    target = target.resolve()
                    if target.exists() and not target.is_dir():
                        self._json({"error": "Choose a folder, not a file"}, 400)
                        return
                    target.mkdir(parents=True, exist_ok=True)
                    saved["gif_exports_path"] = str(target)
                app_settings.save(saved)
                self._json({"path": str(app_settings.gif_exports_dir()),
                            "default_path": str(app_settings.exports_dir().resolve() / "gif-loops"),
                            "using_default": not bool(saved.get("gif_exports_path"))})
                return
            if path == "/api/client-log":
                LOGGER.error("CLIENT package=%s message=%s stack=%s",
                             str(config.get("package", ""))[:120],
                             str(config.get("message", ""))[:1000],
                             str(config.get("stack", ""))[:4000])
                self._json({"ok": True})
                return
            if (m := re.fullmatch(r"/api/animation/([A-Za-z0-9_.-]+)/audio", path)):
                package = self._package(m.group(1))
                # Multipart upload: store the narration inside the package and
                # reference it from animation.json.
                content_type = self.headers.get("Content-Type", "")
                match = re.search(r'boundary="?([^";]+)"?', content_type)
                if not match:
                    raise ValueError("multipart boundary missing")
                boundary = ("--" + match.group(1)).encode()
                body = raw_body
                audio, filename = None, "commentary.mp3"
                for part in body.split(boundary):
                    if b"filename=" in part and b"\r\n\r\n" in part:
                        head, _, payload = part.partition(b"\r\n\r\n")
                        name_match = re.search(rb'filename="([^"]+)"', head)
                        if name_match:
                            filename = name_match.group(1).decode("utf-8", "replace") or filename
                        audio = payload.rstrip(b"\r\n")
                if not audio:
                    raise ValueError("audio file missing from upload")
                clean_name = re.sub(r"[^A-Za-z0-9_.-]", "_", filename)
                suffix = Path(clean_name).suffix.lower()
                # Keep a valid audio extension when shortening long filenames.
                # Without it, browsers receive a generic binary response and
                # cannot reliably play an otherwise valid upload.
                if suffix not in MIME or not MIME[suffix].startswith("audio/"):
                    suffix = ".mp3"
                safe_name = f"{Path(clean_name).stem[:80 - len(suffix)]}{suffix}"
                audio_relative = package_layout.sounds_relative(package, safe_name)
                audio_path = package / audio_relative
                audio_path.parent.mkdir(parents=True, exist_ok=True)
                audio_path.write_bytes(audio)
                # The editor adds this file as a clip, then saves the complete
                # clip list. Do not overwrite existing sections here.
                self._json({"ok": True, "file": str(audio_relative)})
                return
            if (m := re.fullmatch(r"/api/animation/([A-Za-z0-9_.-]+)/audio/remove", path)):
                package = self._package(m.group(1))
                animation_path = package_layout.animation_path(package)
                animation = animation_schema.normalize_animation(
                    json.loads(animation_path.read_text(encoding="utf-8")) if animation_path.is_file() else {},
                    self._metadata(package))
                removed = None  # Clip files may be shared by split sections.
                animation["commentary"] = {"clips": []}
                temporary = animation_path.with_suffix(".json.tmp")
                temporary.write_text(json.dumps(animation, indent=2) + "\n", encoding="utf-8")
                temporary.replace(animation_path)
                if removed and "/" not in removed and "\\" not in removed:
                    (package / removed).unlink(missing_ok=True)
                self._json({"ok": True, "animation": animation})
                return
            if (m := re.fullmatch(r"/api/animation/([A-Za-z0-9_.-]+)/country", path)):
                package = self._package(m.group(1))
                self._json(self._add_animation_country(package, config))
                return
            if (m := re.fullmatch(r"/api/animation/([A-Za-z0-9_.-]+)/scan-motion", path)):
                package = self._package(m.group(1))
                filename = str(config.get("video", ""))
                if (not filename or Path(filename).name != filename or
                        Path(filename).suffix.lower() not in (".mp4", ".mov", ".m4v", ".webm")):
                    raise ValueError("select a video from this export package")
                video_dir = (package / package_layout.VIDEOS_DIR).resolve()
                video = (video_dir / filename).resolve()
                if video.parent != video_dir or not video.is_file():
                    raise ValueError("reference video was not found in this export package")
                metadata = self._metadata(package)
                wide = package / package_layout.asset_relative(
                    metadata, "satellite_wide", str(package_layout.LEGACY_SATELLITE_WIDE_FILE))
                output = config.get("output") or {}
                result = motion_scan.scan(video, wide, metadata["output"], output)
                self._json({"ok": True, **result})
                return
            if (m := re.fullmatch(r"/api/animation/([A-Za-z0-9_.-]+)", path)):
                package = self._package(m.group(1))
                animation = self._normalize_animation(package, config)
                target = package_layout.animation_path(package)
                temporary = target.with_suffix(".json.tmp")
                temporary.write_text(json.dumps(animation, indent=2) + "\n", encoding="utf-8")
                temporary.replace(target)
                self._json({"ok": True, "animation": animation})
                return
            if (m := re.fullmatch(r"/api/animation/([A-Za-z0-9_.-]+)/fusion", path)):
                package = self._package(m.group(1))
                fusion_mode = str(config.get("fusion_mode", "3d"))
                if fusion_mode not in ("2d", "3d"):
                    raise ValueError("Fusion scene type must be 2d or 3d")
                metadata = self._metadata(package)
                animation = self._normalize_animation(package, config)
                package_layout.animation_path(package).write_text(
                    json.dumps(animation, indent=2) + "\n", encoding="utf-8")
                warnings = []
                target = fusion_generator.generate(
                    package, metadata, animation, warnings, mode=fusion_mode)
                relative = target.relative_to(app_settings.exports_dir())
                self._json({"ok": True, "mode": fusion_mode, "file": str(relative), "url": "/exports/" + str(relative),
                            "warnings": warnings})
                return
            if (m := re.fullmatch(r"/api/export/([A-Za-z0-9_.-]+)/delete", path)):
                package = self._package(m.group(1))
                # _package verifies this is one direct child of the export folder;
                # never accept a client-supplied filesystem path here.
                shutil.rmtree(package)
                self._json({"ok": True, "deleted": m.group(1)})
                return
            if path == "/api/settings":
                self._save_settings(config)
                return
            if path == "/api/settings/select-folder":
                self._choose_exports_folder()
                return
            if path == "/api/mapsnap/select-folder":
                self._choose_exports_folder("Choose MapSnap output folder")
                return
            if path == "/api/mapsnap/export":
                try:
                    map_snap.validate(config)
                except (TypeError, ValueError) as exc:
                    self._json({"error": str(exc)}, 400)
                    return
                job_id = str(uuid.uuid4())
                with JOBS_LOCK:
                    JOBS[job_id] = {"status": {"stage": "queued", "pct": 0.0, "message": "queued"},
                                    "result": None}
                threading.Thread(target=self._run_mapsnap_job,
                                 args=(job_id, config), daemon=True).start()
                self._json({"job_id": job_id}, 202)
                return
            if path != "/api/export":
                self._json({"error": "not found"}, 404)
                return
            job_id = str(uuid.uuid4())
            with JOBS_LOCK:
                JOBS[job_id] = {"status": {"stage": "queued", "pct": 0.0, "message": "queued"},
                                "result": None}
            t = threading.Thread(target=self._run_job, args=(job_id, config), daemon=True)
            t.start()
            self._json({"job_id": job_id})
        except Exception as exc:  # noqa: BLE001
            LOGGER.exception("POST %s failed", path)
            self._json({"error": str(exc)}, 500)

    # ---- job runner ------------------------------------------------------

    def _run_mapsnap_job(self, job_id: str, config: dict) -> None:
        def progress(stage: str, pct: float, message: str) -> None:
            with JOBS_LOCK:
                JOBS[job_id]["status"] = {"stage": stage, "pct": round(pct, 1), "message": message}
        try:
            result = map_snap.export_image(config, progress)
            with JOBS_LOCK:
                JOBS[job_id]["result"] = result
                JOBS[job_id]["status"] = {"stage": "done", "pct": 100.0,
                                          "message": "image export complete"}
        except Exception as exc:  # noqa: BLE001
            LOGGER.exception("MapSnap export failed")
            progress("error", 100.0, str(exc))

    def _run_region_job(self, job_id, package, name, area, mpp):
        def progress(stage, pct, message):
            with JOBS_LOCK:
                JOBS[job_id]["status"] = {"stage": stage, "pct": round(pct, 1), "message": message}
        try:
            result = region_closeup.build_region_closeup(package, name, area, mpp, progress=progress)
            for key in ("setting_path", "manifest_path"):
                relative = Path(result[key]).relative_to(app_settings.exports_dir().resolve())
                result[key.replace("_path", "_url")] = "/exports/" + quote(relative.as_posix(), safe="/")
            with JOBS_LOCK:
                JOBS[job_id]["result"] = result
                JOBS[job_id]["status"] = {"stage": "done", "pct": 100, "message": "region close-up complete"}
        except Exception as exc:
            LOGGER.exception("Region close-up failed")
            progress("error", 100, str(exc))

    def _run_job(self, job_id: str, config: dict) -> None:
        def progress(stage: str, pct: float, message: str) -> None:
            with JOBS_LOCK:
                JOBS[job_id]["status"] = {"stage": stage, "pct": round(pct, 1),
                                          "message": message}

        try:
            result = exporter.run_export(config, progress)
            with JOBS_LOCK:
                JOBS[job_id]["result"] = result
                JOBS[job_id]["status"] = {"stage": "done", "pct": 100.0,
                                          "message": "export complete"}
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            with JOBS_LOCK:
                JOBS[job_id]["status"] = {"stage": "error", "pct": 100.0,
                                          "message": str(exc)}


def main() -> None:
    app_settings.exports_dir().mkdir(parents=True, exist_ok=True)
    print(f"map-asset-app running at http://{HOST}:{PORT}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
