# Map route overlays (railways, roads, borders on the 3D map)

How to put a real route (from OSM or any GeoJSON) on the 3D map as a sharp PNG that
lands exactly on the satellite map. Learned on the Saudi East railway (gulf_trains,
2026-10-24); applies to any line on any map package from the app.

## Railway track style: stroked vector shapes (current, 2026-10-25)

The user replaced the PNG tracks (sleeper sprites bent along the path: wedges on
curves, jittery paths, pigtails at the ends, one line's sleepers over another's
rails, all lines brown/silver) with this look, from a reference they chose:

- Each line is its path drawn three times: **sleepers** W wide, rigid rectangles
  0.19 W long every 0.57 W, colour darkened 45%; **rail edge** a solid 0.56 W stroke
  in the line colour; **rail centre** a solid 0.31 W stroke lightened 80% (reads as
  two rails). W = 16 px at 1080p, so 32 px on the 2160-wide gulf_trains frame.
- **Fusion can't dash a stroke** (sOutline/sPolygon have no dash; checked live),
  so sleepers are rectangles. Put a whole path's sleepers in **one filled
  sPolygon**: spine point → rectangle → back to the spine → next..., then back
  along the spine. The spine has no area, so only the rectangles fill, and they
  only rotate with the path, never bend.
- Rails: open sPolygon, `Solid` 0, `BorderWidth` = width / render width,
  `CapStyle` 0 (butt), `JoinStyle` 2 (round). The centre is an instance of the
  edge (`SourceOp`), with its own width and colour.
- **One colour control per line**: `SAU_<Line>_Rail_Edge_1` Red/Green/Blue; all
  other shapes of the line follow by expression (`X.Red * 0.55`,
  `X.Red + (1 - X.Red) * 0.8`). Published on the groups (below) as colour pickers.
- **Grouped like a function (user, 2026-10-25)**: everything is one group,
  `SAU_Tracks`, with one output (the plane → `Merge3D1`) and every line's colour
  published. Inside: one group per line (`SAU_<Line>_Rail`: its sleepers, edges and
  centres, merged per layer, three outputs), then `SAU_Tracks_Shapes`, the one
  `SAU_Tracks_Render`, `SAU_Tracks_Plane`. One render for all lines is the cheapest;
  a render per line would cost four 4K renders and break the junction layering.
  Cities are groups too (`SAU_City_<Name>`, one output; see below).
- **Layer order across all lines**: one sMerge with all sleepers, then all rail
  edges, then all rail centres (Input1 is the bottom). Junctions merge cleanly.
- One sRender (3840×2160, the lines' bbox widened to 16:9) on one ImagePlane3D,
  placed with the formulas below. At gulf_trains' fixed camera that is ~3
  texture px per detail px against ~2.3 screen px, so it stays sharp.
- W is set for the camera (screen px per detail px; `Camera3D1`: 2.31). If the
  camera moves or zooms, rerun the generator with the new scale; sleeper
  geometry is baked.
- **Path cleanup first** (`~/edit-projects/project2/shorts/gulf_trains_lines/kit/tracks/smooth_paths.py`): join sections
  into long paths, but only straight on through a junction (≤ 60° turn, or
  rounding the corner moves the track tens of km); drop dead-end sidings
  < 3 km; cut loops; straighten the last ~19 km of dead ends; Gaussian smooth
  ~6 km; round only curves tighter than 1 W, moving no point more than 4 px
  (1.5 W moved North 38 km off its track); snap branch ends onto their main
  path. Check: median shift from OSM 0.1 px, max ≤ 5 px.
- **Cities** (`~/Projects/resolve-bridge/generators/stroke_tracks/mkcity.py`): group
  `SAU_City_<Name>` = a station dot (ring in the line colour + white disc, on a plane
  at Z 0.00207 so it draws over the lines; the user raised it from 0.00107) and the
  `city_label` look (Damascus Bold 0.92 on a grey 0.47 pill box, CornerRadius 0.394;
  box ~0.36 em per Arabic letter + 31 px, its near edge 27 px past the station,
  113 px above it: the user's Riyadh) on a plane at Z 0.01;
  both pop in from the station (Transform `Pivot` at the station, `Center` left at
  0.5: Center moves the image) 0 → 1.15 → 1 over 10 frames. One canvas px = one
  screen px at the camera. Use a vector sRectangle for the box: a RectangleMask's
  Width and Height came out on different bases. `--side`/`--gap` keep it off lines. `build.lua` never re-pastes a city already in
  the comp (the user edits them by hand); it only adds missing ones (`replace` to
  rebuild named ones).
- **Placing all labels**: `layout_cities.py <still.png>` finds the station dots on a
  rendered frame, fits the map→frame homography (11 dots, ≤ 11 px; an affine was
  16 px off because the camera tilts), and picks spots that cover no track, label,
  dot or flag. A crowded corner (gulf_trains: Riyadh/Ras Al-Khair/Dammam/Al-Ahsa) needs
  free offsets: `mkcity.py --offset dx dy` places the box anywhere and draws a thin
  grey leader to the dot when the box is > 90 px away. Grid-search the offset.
- **Trains on the track** (`~/Projects/resolve-bridge/generators/stroke_tracks/mktrain.py`, `build_train.lua`):
  one group per train (`SAU_North_Train`, `SAU_North_Freight`), one output → `Merge3D1`.
  Each car has its own mover (Transform3D, keys on every frame) placed on the cleaned
  route a car length behind the one in front and turned to the track (heading from the
  track over the car's length), so cars stay on the rails through curves; a rigid
  train group would leave the rails. Kenney train models: origin at the base, +Z
  forward, +Y up, FBX = 100 × OBJ units (measure lengths from the OBJ files); lay
  them flat with Rotate X -90, Y 180, heading = Rotate Z = atan2(-dx, dy) in degrees
  (unwrapped). Scale 6e-05 → a car ~67 px long, ~34 px wide (track W 32 px). Timing:
  front car on each station at its frame, monotone cubic between, eased ends. Pop in
  0 → 1.15 → 1 and out on scale. Fusion can't move nodes into an existing group by
  script, so the train is a new group built from the same models as the user's.
- Tools: `~/edit-projects/project2/shorts/gulf_trains_lines/kit/tracks/smooth_paths.py` → `<line>_paths.json`;
  `~/edit-projects/project2/shorts/gulf_trains_lines/kit/tracks/preview_style.py` (preview on the satellite map, outside
  Resolve); `~/Projects/resolve-bridge/generators/stroke_tracks/mktracks.py` →
  `tracks.setting`; `build.lua` replaces the groups in the comp (keeps live colours
  and city names), pastes them (Lua-parsed table, see lua-mailbox-bridge.md), links
  the line groups into `SAU_Tracks_Shapes` (pasted links to another group's outputs
  are dropped), connects each group's output to `Merge3D1`, lays out the insides.

## Rules (each one fixed a real failure)

- **Never above 3840×2160.** Free Resolve caps media at UHD. A 5012×4128 East track
  was silently scaled and landed at the wrong size and place. Render every overlay
  at 3840×2160 or smaller.
- **Crop to the line, don't draw the whole map.** A route drawn in the full
  `satellite_detail.png` frame covers only a few hundred pixels (East: ~220 px wide),
  and the camera enlarges that into blur. Render only the line's bounding box,
  widened to 16:9, at 3840×2160, and scale the plane down to fit (East: 220 → 3840 px,
  k ≈ 12; the much longer North line, 2,268 km, only reaches k ≈ 4.4). Draw the
  rail/sleeper texture at output density; don't enlarge a small bitmap.
- **Draw all sleepers first, then all rails.** A route is several sections that meet at
  junctions; drawing section by section let one section's sleepers cover the other's rails
  (broken rails at every junction). The renderer now does two passes in crop mode.
- **Use the map plane's scale, not the old track plane's.** Read `Map_3D_Detail` live
  (gulf_trains: Scale 2). The old North plane sat at 2.006, 0.3% too big, so its line
  drifted ~5 km off the map at the far end; copying an old track plane copies its error.
- **Project with the map package's own transform**, never by eye: EPSG:3857 metres →
  detail pixels with `detail.pixel_transform` in the package's `json/metadata.json`:
  `px = (merc_x - origin_x) / meters_per_pixel_x`, `py = (origin_y - merc_y) / meters_per_pixel_y`.
- **Route geometry comes from data** (OSM Overpass `railway=rail`, or official GeoJSON);
  don't hand-draw it. Record source, date and length in a README next to the PNG.

## Placing the plane

Put the PNG on an ImagePlane3D built like `Map_3D_Detail` (the detail map plane is
2 wide, 1.125 high, centred). For a crop covering detail pixels `x0..x1`, `y0..y1`:

- `Transform3DOp.Scale` X/Y/Z = `2 * (x1 - x0) / 3840`
- `Transform3DOp.Translate.X` = `((x0 + x1) / 2 / 3840 - 0.5) * 2`
- `Transform3DOp.Translate.Y` = `(0.5 - (y0 + y1) / 2 / 2160) * 1.125`
- `Transform3DOp.Translate.Z` = just above the country planes (gulf_trains: 0.00103)

Colour a line without redrawing it: put a **ColorGain** (`<CC>_<Line>_Track_Color`) between
the track's MediaIn and its plane and set Gain Red/Green/Blue (it multiplies RGB and keeps
alpha, so rails and sleepers keep their shading). Draw every track in the neutral
silver-and-brown style and colour it in Fusion. Script: `(~/edit-projects/davinvi-resolve/naseem-local/archive-claude-codex-bridge-20261026.tar.gz; archived) add.lua`.

Give each line its own Merge3D holding its track plane and its train
(`<CC>_<Line>_Merge3D`), merged with the country plane.

## Tools (gulf_trains versions, Saudi-specific paths inside)

- Renderer: `(~/edit-projects/davinvi-resolve/naseem-local/archive-claude-codex-bridge-20261026.tar.gz; archived) make_east_track.py --route <line>.geojson --output <png> --frame crop`
  `--meta <placement.json> --report <report.json>` (run with `~/Projects/resolve-bridge/.venv/bin/python`;
  always pass both for a new line, or it overwrites the East files). The placement JSON has
  `x0 y0 x1 y1 W H k`. Its `MAP_PACKAGE`, `NORTH` style source and `CITIES` are
  hard-coded for the Gulf map; change them for another map.
- Route selection from OSM: `(~/edit-projects/davinvi-resolve/naseem-local/archive-claude-codex-bridge-20261026.tar.gz; archived) fetch_osm.py`, `select_route.py` (East);
  `~/edit-projects/project2/shorts/gulf_trains_lines/kit/north/select_north.py` (North: shortest paths between the old PNG's ends,
  Iraq/Iran ways excluded). Overpass needs a `User-Agent` header (406 without), see `try_fetch.py`.
- Live swap for North: `~/edit-projects/project2/shorts/gulf_trains_lines/kit/north/` (`read.lua`, `import.lua`,
  `mkswap.py <MediaID>`).
- Placement through the bridge: `(archived: ~/edit-projects/davinvi-resolve/naseem-local/archive-claude-codex-bridge-20261026.tar.gz) mkswap3.py <MediaID>`
  prints a `fusion_run` function that sets the media and the formulas above.

## Checking

A static check is not enough. Export a still of a frame where the camera is close to
the line (the bridge's `still` op, see lua-mailbox-bridge.md) and
confirm the line is sharp and meets its cities/other lines (North and East do not touch
in Riyadh: OSM has no link between their stations; reaches Dammam on the coast). See [lua-mailbox-bridge.md](lua-mailbox-bridge.md).
