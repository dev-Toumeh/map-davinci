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
.venv/bin/python map-asset-app/server.py
```

Then open **http://127.0.0.1:8787** in a browser.

## Workflow

1. **Select countries** — filter the list, click to add (multi-select supported).
   Saudi Arabia is preselected by default.
2. **Frame the shot** — pan/zoom the map. The yellow rectangle shows exactly what
   the detailed background will cover (it always stays centered on the map).
3. Choose **orientation** (landscape or vertical), **resolution** (4K UHD,
   Full HD, or HD), **wide factor** (default 2 = the tutorial's zoomed-out export),
   and **imagery** (Google Satellite is the tutorial's basemap; Esri World Imagery
   as alternative).
4. Click **Highlight** to draw a country's outline on the map (click the row
   first, then Highlight; clicking Highlight again removes it — same as the ✕ chip).
5. Click **Export assets**.

## Output package (`map-asset-app/exports/<name>/`)

| File | Content |
|---|---|
| `satellite_detail.png` | Background at the framed extent |
| `satellite_wide.png` | Same center, `wide_factor` × the extent, same pixel size |
| `mask_<ISO>.png` | One per country — opaque white shape on transparent, exact same grid as the detail image |
| `mask_<ISO>.svg` | Vector version of the same mask — viewBox matches the PNG pixels 1:1, holes and islands preserved |
| `alignment_check.jpg` | Detail background with masks overlaid 50% red — quick visual QA |
| `metadata.json` | CRS, extents, pixel transforms, tile zooms, per-country pixel bounds, SHA-256 hashes, attribution |

## Using the assets in Fusion

- Load `satellite_detail.png` and `mask_<ISO>.png`; the mask's alpha drives the
  country fill/outline (e.g. Background node + mask, DeltaKeyer chain like the tutorial).
- In the 3D scene, set the wide ImagePlane3D scale to **wide_factor** (default 2)
  and nudge it back slightly on Z (e.g. −0.001) behind the detail plane — same
  trick as the tutorial. `metadata.json → fusion_notes` records this.
- `metadata.json → detail.pixel_transform` converts any lon/lat to detail-image
  pixels — used later by the Fusion generator for camera targets.

## Sources & notes

- Boundaries: [Natural Earth 10m admin-0 countries](https://www.naturalearthdata.com/)
  (public domain), downloaded once to `data/` (~13 MB).
- Imagery: Google Satellite tiles (no credentials; personal/educational use —
  check terms before publishing videos commercially) or Esri World Imagery
  (attribution recorded in metadata). Tiles are cached in `tilecache/`.
- Export resolution vs. zoom: the exporter picks the highest native tile zoom for
  your framing and records `tile_zoom_upscaled` if the source is coarser than
  requested. For deep zoom-ins, frame at a higher map zoom.
- Exports are rendered from raw tiles + raw geometry — never screenshots.
