# Map Asset Prep — for Fusion map animations

A local app that automates the **QGIS asset-preparation steps** from the map-animation
tutorial: pick countries, frame the shot on a live satellite map, and export
pixel-aligned assets ready to import into DaVinci Resolve Fusion.

## Run

```bash
# from the project root (one-time setup if .venv doesn't exist yet)
python3 -m venv .venv
.venv/bin/pip install Pillow numpy requests CairoSVG opencv-python

# start the app
.venv/bin/python app/server.py
```

Then open **http://127.0.0.1:8787** in a browser.

## Archive Carousel (Go)

Use **Archive Carousel** beside GIF → Fusion, or `/archive-carousel`, after restarting the app. Its Go backend starts automatically; Go is needed for the first build, with FFmpeg/ffprobe for media. Mix videos and photos, choose durations and a shared card ratio, then export one editable Fusion group with packaged media and film artwork. Defaults: UHD transparent output, 24fps, 4:3 cards, and **10 frames for every entrance and exit, including the first entrance**. See [Archive Carousel](tools/archive-carousel/README.md) for startup, timing, export, and testing details.

## GIF → Fusion

Use **GIF → Fusion** beside Settings on the landing page, or open
**http://127.0.0.1:8787/gif**. Select a GIF, name its group, set the timeline FPS,
and generate an editable looping Fusion setting. The **GIF export folder** field
lets you type or choose a saved destination, independent of map exports. **Use
default** restores `<configured map exports folder>/gif-loops/`. Each conversion
contains the source GIF, RGBA PNG sequence, timing metadata, and a ZIP package.

Download the setting and drag it into Fusion. Its Loader already references the
exported PNGs. Keep that asset folder in place; after moving a package, relink the
Loader to `Frames/frame_0000.png`. The group exposes Speed, Timeline FPS, and
Offset, preserving variable GIF frame durations. Following
`references/nodes/gif-reference.setting`, each setting contains one GIF layer in
a MultiMerge over a transparent 3840×2160 canvas, with one composite output.
Position, Size, Angle, Blend, and canvas dimensions are editable group controls.
No country-specific placements or visibility keyframes are copied. Upload limits are 25 MB,
512 frames, 4096 pixels per side, and 128 million decoded pixels.

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
   smooth movement, save `json/animation.json`, then generate a Fusion composition.

## Output package (`exports/<name>/`)

| Path | Content |
|---|---|
| `images/` | Satellite backgrounds, PNG/SVG masks, and the alignment-check image |
| `images/flags/` | Generated country flag textures and the Flag Icons MIT license notice |
| `json/metadata.json` | CRS, extents, pixel transforms, tile zooms, per-country pixel bounds, hashes, and attribution |
| `json/animation.json` | Saved 2D view keyframes, timing, FPS, easing, regions, and commentary references |
| `data/` | Country and sub-territory GeoJSON used by native Fusion polygon masks |
| `sounds/` | Uploaded narration, music, and other audio used by the animation |
| `fusion/scene_vNNN.comp` | Versioned editable 2D Fusion graph |
| `fusion/scene_vNNN_3d.comp` | Versioned Fusion scene with map planes and an animated 3D camera |
| `videos/` | Folder for rendered videos from the project |

Repeated names use numeric suffixes: `saudi_arabia`, `saudi_arabia_2`,
`saudi_arabia_3`, and so on. Existing flat packages remain supported.
Generated compositions have a Color/Flag switch for each whole country. Flag
is the default when an asset is available, and all native territory switches start
enabled (`Which = 0`; choose `OFF` to hide one). No custom country controllers,
custom controls, or custom flag/border setting nodes are generated. Country stacks
are split between the two sides of the main graph: first half left, remaining
half right (four countries = two per side; odd counts put one extra on the left).
The right-side stacks are mirrored: left stacks flow left-to-right and right
stacks flow right-to-left toward the central scene. Each country's sub-territories
stay with it, with aligned columns and measured vertical spacing. Expanded
native groups are mirrored with their contents. This changes only the node-editor layout, not map placement,
camera keyframes, or layer order. Existing compositions are not rewritten.
Sub-territories retain their saved colors. Flag textures
use the pinned Flag Icons v7.5.0 SVGs in `resources/flag_icons/` and are created
inside the package when a new composition is generated. If a flag is unavailable,
the generation result reports that its color fill was kept. On macOS, CairoSVG
also needs the Homebrew `cairo` library (`brew install cairo`).

## Animation editor

The editor is available after an export through **Animate this export**, or directly
at `http://127.0.0.1:8787/static/animation.html`. It supports source-matched
landscape output plus vertical Full HD (1080×1920) and 4K (2160×3840) targets.
Choose **3D camera scene** (the default) or **2D map animation** beside Generate Fusion.
Both choices use the same saved map assets and create a new composition version.
The 3D scene places the saved wide and detail satellite images on separate
registered planes, followed by any close-up and locally rendered territory
planes. Each territory mask and border uses a canvas fitted to its own bounds;
the scene camera uses the shot's pan and zoom keys and adds a mild perspective orbit.
In Fusion Flow, all satellite images form one horizontal row above the territory
groups, even when a shot has many close-ups.
It supports the selected horizontal or vertical output dimensions. When a shot
zooms beyond the saved detail image's useful resolution, the 3D generator places
a locally cached close-up satellite image on its own registered 3D plane and
fades it in around that view. The 3D generator stops if the shot contains map
connections, which do not yet follow the 3D camera.
The 2D generator creates an explicit final canvas at the selected dimensions,
so the landscape source map cannot force a portrait timeline back to 16:9.

### Scan reference movement

The animation editor opens `videos/reference.mp4` automatically when it exists.
Otherwise the reference controls stay hidden. Use **Upload MP4** to add or replace
that file, or **Show** to choose another MP4, MOV, M4V, or WebM already in the
export package's `videos/` folder. **Hide** closes the reference video so you can
work on the camera manually. Click **Scan pan and zoom** when you want a movement
proposal. The editor compares sampled video frames with the saved
wide satellite image and previews editable camera keys for zoom and movement in
all four directions. Scrub the reference and map together, inspect any reported
low-confidence time ranges, then click **Apply draft** or **Discard**. Applying
changes only the editor draft; **Save shot** writes `animation.json`.

This first pass follows pan and zoom. Reference cuts, rotation, camera tilt, and
overlays may need manual camera adjustments. OpenCV is used only when a scan is
requested; other editing and Fusion generation remain available without it.

Keyframes store a time, view center, zoom, and easing *into* that keyframe. Smooth
uses the defined cubic `3t² − 2t³`; linear uses constant interpolation. The generated
2D Fusion composition retains the authored camera keys and adds keys where fitted
Bezier curves need them to reproduce the browser's motion. The 3D camera keeps
only the authored keyframe times, with fitted curves between them. Dense per-frame camera
samples still define the spatial path, while arrow geometry and dashed connections
retain their per-frame samples. The camera fit allows up to 2% zoom difference and a
small displacement difference at integer output frames; verify the resulting
motion in Resolve, especially with motion blur.
Camera position is converted in the landscape Transform's source coordinates before
the centered merge onto the output canvas. Import and render it
in Resolve to verify native node behaviour before using it in production.

## Using the assets in Fusion

Solid connections export as native Polygon strokes with animated WriteLength;
filled arrowheads and dashed connections retain polygon geometry. No fonts or
hyphen strings are used. The curved
path uses the browser's quadratic Bezier geometry and reveal timing. Line widths,
dash spacing and arrow sizes use a 1080-pixel output short edge as their reference,
scaled for other resolutions, and remain constant during camera zoom. The preview
uses the same units, so existing lines may look thinner than the older window-pixel
preview. Adjust the connection thickness/arrow controls if desired. Geometry is
sampled at integer frames where needed; native Resolve import/render remains a verification step.

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
  (public domain), downloaded once to `runtime/data/` (~13 MB).
- Country default fills: flag-inspired ISO3 palette in `resources/national_colors.json`,
  derived from [Flag Icons](https://github.com/lipis/flag-icons) (MIT). Colors
  remain editable before export; saved export colors always take precedence.
- Imagery: Google Satellite tiles (no credentials; personal/educational use —
  check terms before publishing videos commercially) or Esri World Imagery
  (attribution recorded in metadata). Tiles are cached in `runtime/tilecache/`.
- Export resolution vs. zoom: the exporter picks the highest native tile zoom for
  your framing and records `tile_zoom_upscaled` if the source is coarser than
  requested. For deep zoom-ins, frame at a higher map zoom.
- Exports are rendered from raw tiles + raw geometry — never screenshots.
