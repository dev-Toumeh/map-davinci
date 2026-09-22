# Map Asset Prep — for Fusion map animations

A local app that automates the **QGIS asset-preparation steps** from the map-animation
tutorial: pick countries, frame the shot on a live satellite map, and export
pixel-aligned assets ready to import into DaVinci Resolve Fusion.

## Run

```bash
# from the project root (one-time setup if .venv doesn't exist yet)
python3 -m venv .venv
.venv/bin/pip install Pillow numpy requests

# start the app
.venv/bin/python app/server.py
```

Then open **http://127.0.0.1:8787** in a browser.

## Workflow

1. **Select countries** — filter the list, click to add (multi-select supported).
   Saudi Arabia is preselected by default.
2. **Frame the shot** — pan/zoom the map underneath the fixed red **EXPORT TARGET**
   frame. The target shows exactly what the detailed background will cover.
3. Choose **orientation** (landscape or vertical), **resolution** (4K UHD,
   Full HD, or HD), **wide factor** (default 2 = the tutorial's zoomed-out export),
   and **imagery** (Google Satellite is the tutorial's basemap; Esri World Imagery
   as alternative).
4. Click **Highlight** to draw a country's outline on the map (click the row
   first, then Highlight; clicking Highlight again removes it — same as the ✕ chip).
5. Click **Export assets**.
6. In the completed-export panel, choose **Animate this export**. In the 2D editor,
   pan/zoom the real exported backgrounds, add timeline keyframes, select linear or
   smooth movement, save `animation.json`, then generate `fusion/scene.comp`.

## Output package (`app/exports/<name>/`)

| File | Content |
|---|---|
| `satellite_detail.png` | Background at the framed extent |
| `satellite_wide.png` | Same center, `wide_factor` × the extent, same pixel size |
| `mask_<ISO>.png` | One per country — selected highlight color on transparent, exact same grid as the detail image |
| `mask_<ISO>.svg` | Vector version of the same colored mask — viewBox matches the PNG pixels 1:1, holes and islands preserved |
| `geometry_<ISO>.geojson` | Original vector geometry saved with the package for editable native Fusion polygon masks |
| `alignment_check.jpg` | Detail background with masks overlaid 50% red — quick visual QA |
| `metadata.json` | CRS, extents, pixel transforms, tile zooms, per-country pixel bounds, SHA-256 hashes, attribution |
| `animation.json` | Saved 2D view keyframes, timing, FPS, and easing (created in the Animation Editor) |
| `fusion/scene_vNNN.comp` | Versioned editable 2D Fusion graph; every Generate action creates a new version |

## 2D animation editor

The editor is available after an export through **Animate this export**, or directly
at `http://127.0.0.1:8787/static/animation.html`. It supports source-matched
landscape output plus vertical Full HD (1080×1920) and 4K (2160×3840) targets.
The Fusion generator creates an explicit final canvas at the selected dimensions,
so the landscape source map cannot force a portrait timeline back to 16:9.

Keyframes store a time, view center, zoom, and easing *into* that keyframe. Smooth
uses the defined cubic `3t² − 2t³`; linear uses constant interpolation. The generated
Fusion composition uses per-frame camera keys to reproduce the browser's view-width
interpolation and easing at integer output frames. This produces denser editable
curves; subframe motion-blur samples are linearly approximated between those keys.
Camera position is converted in the landscape Transform's source coordinates before
the centered merge onto the output canvas. Import and render it
in Resolve to verify native node behaviour before using it in production.

## Using the assets in Fusion

- New generated compositions use `geometry_<ISO>.geojson` points to create editable
  Fusion `MultiPoly` masks and colored Background layers. PNG masks remain available
  for other workflows and old packages.
- In the 3D scene, set the wide ImagePlane3D scale to **wide_factor** (default 2)
  and nudge it back slightly on Z (e.g. −0.001) behind the detail plane — same
  trick as the tutorial. `metadata.json → fusion_notes` records this.
- `metadata.json → detail.pixel_transform` converts any lon/lat to detail-image
  pixels — used later by the Fusion generator for camera targets.

## Sources & notes

- Boundaries: [Natural Earth 10m admin-0 countries](https://www.naturalearthdata.com/)
  (public domain), downloaded once to `data/` (~13 MB).
- Country default fills: flag-inspired ISO3 palette in `national_colors.json`,
  derived from [Flag Icons](https://github.com/lipis/flag-icons) (MIT). Colors
  remain editable before export; saved export colors always take precedence.
- Imagery: Google Satellite tiles (no credentials; personal/educational use —
  check terms before publishing videos commercially) or Esri World Imagery
  (attribution recorded in metadata). Tiles are cached in `tilecache/`.
- Export resolution vs. zoom: the exporter picks the highest native tile zoom for
  your framing and records `tile_zoom_upscaled` if the source is coarser than
  requested. For deep zoom-ins, frame at a higher map zoom.
- Exports are rendered from raw tiles + raw geometry — never screenshots.
