"""
map-asset-app / server.py

Local web app server (stdlib only). Binds to 127.0.0.1 only.

  python3 server.py            -> http://127.0.0.1:8787

Endpoints:
  GET  /                          -> static/index.html
  GET  /static/*                  -> UI assets
  GET  /exports/*                 -> exported files (for inspection)
  GET  /api/health                -> ok
  GET  /api/countries             -> country index (downloads NE file on first call)
  GET  /api/country/<ISO3>        -> GeoJSON geometry for preview outline
  POST /api/export                -> start export job {json body}
   GET  /api/export/status/<id>    -> job progress/result
   GET  /api/exports                -> available export packages
   GET/POST /api/animation/<name>   -> read/save a shot animation
   POST /api/animation/<name>/fusion -> generate scene.comp
   POST /api/export/<name>/delete     -> permanently remove one package
"""

from __future__ import annotations

import json
import re
import shutil
import threading
import traceback
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import exporter
import animation_schema
import fusion_generator

APP_ROOT = Path(__file__).resolve().parent
STATIC_DIR = APP_ROOT / "static"
EXPORTS_DIR = APP_ROOT / "exports"

HOST = "127.0.0.1"
PORT = 8787

JOBS: dict = {}          # job_id -> {"status": {...}, "result": {...} | None}
JOBS_LOCK = threading.Lock()
EXPORT_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,119}")

MIME = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".json": "application/json",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
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
            if not str(resolved).startswith(str(root.resolve())):
                self._json({"error": "forbidden"}, 403)
                return
            if not resolved.is_file():
                self._json({"error": "not found"}, 404)
                return
            data = resolved.read_bytes()
            self._send(200, data, MIME.get(resolved.suffix.lower(), "application/octet-stream"))
        except Exception as exc:  # noqa: BLE001
            self._json({"error": str(exc)}, 500)

    def log_message(self, fmt, *args):  # quieter console
        pass

    def _package(self, name: str) -> Path:
        if not EXPORT_NAME.fullmatch(name):
            raise ValueError("invalid export package name")
        package = (EXPORTS_DIR / name).resolve()
        if package.parent != EXPORTS_DIR.resolve() or not (package / "metadata.json").is_file():
            raise FileNotFoundError("export package not found")
        return package

    def _metadata(self, package: Path) -> dict:
        return json.loads((package / "metadata.json").read_text(encoding="utf-8"))

    def _animation_response(self, package: Path) -> dict:
        path = package / "animation.json"
        return {"export": package.name, "metadata": self._metadata(package),
                "animation": json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None}

    def _normalize_animation(self, package: Path, config: dict) -> dict:
        """Normalize a browser save without losing saved Fusion calibration.

        A browser tab opened before a calibration was added has no fusion_path
        field. Preserve the existing per-frame calibration in that case rather
        than silently replacing it with the old browser payload.
        """
        animation = animation_schema.normalize_animation(config, self._metadata(package))
        target = package / "animation.json"
        if not target.is_file():
            return animation
        existing = animation_schema.normalize_animation(
            json.loads(target.read_text(encoding="utf-8")), self._metadata(package))
        paths = {key["frame"]: key["fusion_path"] for key in existing["keyframes"]
                 if key.get("fusion_path")}
        for key in animation["keyframes"]:
            if "fusion_path" not in key and key["frame"] in paths:
                key["fusion_path"] = paths[key["frame"]]
        return animation

    # ---- routing ---------------------------------------------------------

    def do_GET(self):  # noqa: N802
        path = self.path.split("?", 1)[0]
        try:
            if path in ("/", "/index.html"):
                self._file(STATIC_DIR / "index.html", STATIC_DIR)
            elif path.startswith("/static/"):
                self._file(STATIC_DIR / path[len("/static/"):], STATIC_DIR)
            elif path.startswith("/exports/"):
                self._file(EXPORTS_DIR / path[len("/exports/"):], EXPORTS_DIR)
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
            elif (m := re.fullmatch(r"/api/export/status/([a-f0-9-]+)", path)):
                with JOBS_LOCK:
                    job = JOBS.get(m.group(1))
                    if not job:
                        self._json({"error": "unknown job"}, 404)
                        return
                    self._json({"status": job["status"], "result": job["result"]})
            elif path == "/api/exports":
                packages = []
                for candidate in sorted(EXPORTS_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
                    if not candidate.is_dir() or not (candidate / "metadata.json").is_file():
                        continue
                    metadata = self._metadata(candidate)
                    packages.append({"name": candidate.name, "generated_at": metadata.get("generated_at"),
                                     "output": metadata.get("output"),
                                     "countries": [c.get("iso3") for c in metadata.get("countries", [])],
                                     "has_animation": (candidate / "animation.json").is_file()})
                self._json({"exports": packages})
            elif (m := re.fullmatch(r"/api/animation/([A-Za-z0-9_.-]+)", path)):
                self._json(self._animation_response(self._package(m.group(1))))
            else:
                self._json({"error": "not found"}, 404)
        except Exception as exc:  # noqa: BLE001
            self._json({"error": str(exc)}, 500)

    def do_POST(self):  # noqa: N802
        path = self.path.split("?", 1)[0]
        try:
            length = int(self.headers.get("Content-Length", 0))
            config = json.loads(self.rfile.read(length) or b"{}")
            if (m := re.fullmatch(r"/api/animation/([A-Za-z0-9_.-]+)", path)):
                package = self._package(m.group(1))
                animation = self._normalize_animation(package, config)
                target = package / "animation.json"
                temporary = target.with_suffix(".json.tmp")
                temporary.write_text(json.dumps(animation, indent=2) + "\n", encoding="utf-8")
                temporary.replace(target)
                self._json({"ok": True, "animation": animation})
                return
            if (m := re.fullmatch(r"/api/animation/([A-Za-z0-9_.-]+)/fusion", path)):
                package = self._package(m.group(1))
                metadata = self._metadata(package)
                animation = self._normalize_animation(package, config)
                (package / "animation.json").write_text(json.dumps(animation, indent=2) + "\n", encoding="utf-8")
                target = fusion_generator.generate(package, metadata, animation)
                relative = target.relative_to(EXPORTS_DIR)
                self._json({"ok": True, "file": str(relative), "url": "/exports/" + str(relative)})
                return
            if (m := re.fullmatch(r"/api/export/([A-Za-z0-9_.-]+)/delete", path)):
                package = self._package(m.group(1))
                # _package verifies this is one direct child of EXPORTS_DIR;
                # never accept a client-supplied filesystem path here.
                shutil.rmtree(package)
                self._json({"ok": True, "deleted": m.group(1)})
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
            self._json({"error": str(exc)}, 500)

    # ---- job runner ------------------------------------------------------

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
    EXPORTS_DIR.mkdir(exist_ok=True)
    print(f"map-asset-app running at http://{HOST}:{PORT}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
