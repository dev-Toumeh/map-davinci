"""Create package-local flag textures from the pinned Flag Icons SVGs."""
from __future__ import annotations

import io
import json
import os
from pathlib import Path

from PIL import Image

RESOURCE = Path(__file__).resolve().parents[1] / "resources" / "flag_icons"
MAX_TEXTURE_SIDE = 3072


def flag_code(iso3: str, iso2: str | None = None) -> str | None:
    code = str(iso2 or "").lower()
    if len(code) != 2 or not code.isalpha():
        mapping = json.loads((RESOURCE / "iso3_to_iso2.json").read_text())
        code = mapping.get(iso3.upper(), "")
    return code if (RESOURCE / "4x3" / f"{code}.svg").is_file() else None


def make_texture(package: Path, iso3: str, code: str,
                 rings: list[tuple[int, list[tuple[float, float]]]],
                 native_width: int, native_height: int, max_zoom: float) -> tuple[Path, dict, list[str]]:
    """Rasterize a flag across the active whole-country polygon bounds.

    Rings use the same projected points as Fusion's vector fill. The returned
    placement describes the exact country bounds so Fusion can move the cropped
    opaque flag with the same camera values as the vector polygon.
    """
    ext = [point for level, ring in rings if level > 0 for point in ring]
    if not ext:
        raise ValueError(f"{iso3} has no exterior flag polygon")
    x0, x1 = min(x for x, _ in ext) + .5, max(x for x, _ in ext) + .5
    y0, y1 = .5 - max(y for _, y in ext), .5 - min(y for _, y in ext)
    bounds_width = max(1.0, (x1 - x0) * native_width)
    bounds_height = max(1.0, (y1 - y0) * native_height)
    # Flag Icons uses a 4:3 canvas. Preserve that aspect and enlarge the flag
    # until it covers the complete country bounds. The polygon clips the excess
    # outside its border, matching Fusion's normal image-fill workflow.
    flag_aspect = 4 / 3
    if bounds_width / bounds_height >= flag_aspect:
        base_width = bounds_width
        base_height = bounds_width / flag_aspect
    else:
        base_height = bounds_height
        base_width = bounds_height * flag_aspect
    requested_scale = max(1.0, max_zoom)
    scale = min(requested_scale, MAX_TEXTURE_SIDE / max(base_width, base_height))
    texture_width = max(1, round(base_width * scale))
    texture_height = max(1, round(texture_width / flag_aspect))
    warnings = []
    if scale + 1e-6 < requested_scale:
        warnings.append(f"{iso3} flag texture capped at {MAX_TEXTURE_SIDE}px; details may soften at maximum zoom")

    # Homebrew's Cairo is outside macOS's default dynamic library search path.
    if (Path("/opt/homebrew/lib/libcairo.2.dylib").is_file()
            and not os.environ.get("DYLD_FALLBACK_LIBRARY_PATH")):
        os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = "/opt/homebrew/lib"
    import cairosvg
    svg = RESOURCE / "4x3" / f"{code}.svg"
    svg_text = svg.read_text(encoding="utf-8").replace(
        "<svg ", '<svg preserveAspectRatio="none" ', 1)
    png = cairosvg.svg2png(bytestring=svg_text.encode("utf-8"),
                           output_width=texture_width, output_height=texture_height)
    texture = Image.open(io.BytesIO(png)).convert("RGBA")
    texture.putalpha(255)
    target = (package / "images" / "flags" /
              f"{iso3.upper()}_cover_{texture_width}x{texture_height}.png")
    target.parent.mkdir(parents=True, exist_ok=True)
    texture.save(target)
    license_path = target.parent / "LICENSE.flag-icons.txt"
    if not license_path.is_file():
        license_path.write_bytes((RESOURCE / "LICENSE").read_bytes())
    return target, {"center_x": (x0 + x1) / 2, "center_y": (y0 + y1) / 2,
                    "size": 1.0, "scale": scale,
                    "width": texture_width, "height": texture_height}, warnings
