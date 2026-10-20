"""Lifecycle bridge only: all carousel processing and UI are implemented in Go."""
from __future__ import annotations

import atexit
import json
import os
from pathlib import Path
import selectors
import shutil
import subprocess
import threading

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "app" / "tools" / "archive-carousel"
RUNTIME = ROOT / "app" / "runtime" / "archive-carousel"
_lock = threading.Lock()
_process = None
_url = None


def stop():
    global _process, _url
    with _lock:
        if _process is not None and _process.poll() is None:
            _process.terminate()
            try:
                _process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                _process.kill()
                _process.wait(timeout=3)
        _process = None
        _url = None


atexit.register(stop)


def start(exports_dir: Path, back_url: str) -> str:
    """Build stale sources, launch one owned service, and return its actual URL."""
    global _process, _url
    with _lock:
        if _process is not None and _process.poll() is None:
            return _url
        RUNTIME.mkdir(parents=True, exist_ok=True)
        binary = RUNTIME / "archive-carousel"
        sources = [p for p in MODULE.rglob("*") if p.is_file()]
        stale = not binary.is_file() or any(p.stat().st_mtime > binary.stat().st_mtime for p in sources)
        env = dict(os.environ)
        env["GOCACHE"] = str(ROOT / "app" / "runtime" / "go-build")
        env["GOTELEMETRY"] = "off"
        if stale:
            go = shutil.which("go")
            if not go:
                raise RuntimeError("Archive Carousel needs Go to build. Install Go, then reopen this tool.")
            temporary = binary.with_suffix(".building")
            result = subprocess.run([go, "build", "-o", str(temporary), "."], cwd=MODULE,
                                    env=env, capture_output=True, text=True, timeout=180)
            if result.returncode:
                raise RuntimeError("Carousel build failed: " + result.stderr[-3000:])
            temporary.replace(binary)
        with (RUNTIME / "service.log").open("ab") as log:
            process = subprocess.Popen(
                [str(binary), "--listen", "127.0.0.1:0", "--repo-root", str(ROOT),
                 "--exports-root", str(exports_dir.resolve() / "archive-carousels"),
                 "--back-url", back_url, "--parent-pid", str(os.getpid())],
                cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=log,
            )
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                if not selector.select(timeout=15):
                    raise RuntimeError("Carousel startup timed out; see app/runtime/archive-carousel/service.log")
                record = json.loads(process.stdout.readline())
            address = record["url"]
            if not address.startswith("http://127.0.0.1:"):
                raise RuntimeError("Carousel returned an unexpected local address")
        except Exception:
            process.terminate()
            process.wait(timeout=5)
            process.stdout.close()
            raise
        _process, _url = process, address
        return address
