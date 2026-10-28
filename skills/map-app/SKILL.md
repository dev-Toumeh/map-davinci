---
name: map-app
description: The local Map Asset Prep app (http://127.0.0.1:8787, ~/edit-projects/davinvi-resolve/app) that exports satellite map packages, animates them and generates Fusion comps; also how to use its code from scripts, e.g. a sharp close-up satellite plate for a small area (Bahrain) placed on its own 3D plane. Use when a map video needs a new package, a close-up because the map goes soft at close zoom, the package's coordinates, or the app's API.
---

# Map app (Map Asset Prep)

Local app in this repo: `app/`. Start with `.venv/bin/python app/server.py` from the repo root, then
open http://127.0.0.1:8787 (`GET /api/health` returns ok). Full user docs: `app/README.md`; open
work: `app/docs/BACKLOG.md`. Check whether the app is already running before starting another one.

## What it makes
- **Export package** `exports/<name>/` (Workflow in the README: pick countries, frame the red EXPORT
  TARGET, choose orientation, resolution, wide factor and imagery, then Export).
  - `images/satellite_wide.png` and `images/satellite_detail.png` (detail 3840×2160 for 4K), plus
    country masks and flags.
  - `json/metadata.json`: CRS (EPSG:3857), `detail.pixel_transform`
    (`px = (merc_x - x0)/mpp ; py = (y0 - merc_y)/mpp`), `wide.bbox_mercator`, the imagery source,
    and per-country pixel bounds.
  - `data/geometry_<ISO3>.geojson`: country shapes. Use them for border filters; don't draw borders
    by hand.
- **Animation editor** `/static/animation.html`: camera keyframes saved to `json/animation.json`, with
  reference-video pan/zoom scan.
- **Fusion generation** (`POST /api/animation/<name>/fusion`): `fusion/scene_vNNN.comp` (2D) or
  `scene_vNNN_3d.comp` (3D scene with Map_3D_Satellite / Map_3D_Detail planes and a camera).
- Country stacks use ISO prefixes (`BHR_Plane`, `BHR_Local_Elements_MultiMerge`…). Every name stays
  unique.
- Other tools on the landing page: GIF → Fusion (`/gif`) and Archive Carousel (`/archive-carousel`).

## Coordinates (gulf_trains package and any app 3D comp)
- 3D world units: the detail plane is Scale 2 at Z 0.00025, so for detail px (x, y):
  `wx = (x/3840 - .5)*2`, `wy = (.5 - y/2160)*1.125` (16:9). Mercator → detail px uses the
  pixel_transform above.
- Z layers in gulf_trains: satellite 0, detail 0.00025, close-ups 0.0005, country flags ~0.00102–0.00107,
  links 0.0019, tracks 0.002, dots 0.00207, train 0.0025, labels 0.01. See [[check-plane-z]] in memory.
- gulf_trains package: `exports/saudi_arabia_qatar_united_arab_emirates_kuwait_bahrain_oman`, Esri
  World Imagery, about 1887 m per detail px. Small places (Bahrain is ~28 px wide) go soft when the
  camera is close.

## Close-ups (sharp local imagery)
- In the app: `app/fusion/closeup_lod.py`. `plan_closeups()` picks the views that zoom past
  `MAX_DETAIL_MAGNIFICATION` of the detail image (3.0 in 3D). `ensure_images()` fetches each plate
  with `core.exporter.choose_tile_zoom()` + `stitch_bbox(source, key, zoom, bbox_mercator,
  (w, h), progress, stage)` and caches it in the package's close-up folder.
  `fusion/generator.py` puts each one on its own `Map_Closeup_NN_FFFF_Plane` (Z 0.0005, full-res
  Loader → Fade merge with a Visibility spline → ImagePlane3D). The texture is not composited into the
  base map first, because that would throw away its pixels.
- **From a script, for a hand-built comp** (gulf_trains does this; its comp is not app-generated):
  1. Take the mercator bbox of the area (with margin) and keep the image aspect equal to the bbox
     aspect, so pixels are square. Max 3840×2160, the free Resolve limit.
  2. Run with `PYTHONPATH=app`: `zoom,_ = exporter.choose_tile_zoom(mpp_ground, lat, source['max_zoom'])`,
     then `exporter.stitch_bbox(...)`. Use the package's `metadata['imagery']['source']`, so the
     colours match the detail image.
  3. The plane: Translate = the bbox centre in world units, Scale = the bbox width in world units
     (ImagePlane3D takes its height from the image aspect), Z 0.0005, two-sided lighting.
  4. Check the alignment: draw `geometry_<ISO3>` on a copy of the plate. The coastlines must match.
  5. Ask the user for the frames where it fades in and out (frames page), because a different tile
     zoom can show a colour seam at its edge.

## Rules
- Don't edit the app while using it for a video task unless asked. Its tests are in `app/tests`
  (`.venv/bin/python -m pytest app/tests`).
- Generated comps are new versions (`scene_vNNN`); never overwrite one the user edited in Fusion.
- Overpass and tile fetches need network access. Use User-Agent "gulf-trains-map/1.0" for Overpass,
  and the mirror https://overpass.kumi.systems/api/interpreter when overpass-api.de answers 502.
