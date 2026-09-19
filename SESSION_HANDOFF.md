# Map video automation — session handoff

Updated 18 September 2026. Read this before continuing. This records the previous conversation and checks performed; it is not evidence that the generated Fusion shot works correctly.

## Goal and current state

The user wants a repeatable approach for generating map videos with GPT and DaVinci Resolve Fusion, using their existing work as references. The goal is a useful production workflow, not a series of scripting demonstrations. They can share more Fusion projects and media so the assistant can understand their style and node construction.

The user is very dissatisfied with the delivered Louisiana draft and the repeated troubleshooting. They described the output as rubbish and worse than their expectations. Do not present that draft as successful, extend its design automatically, or push a paid upgrade. Their latest substantive clarification was: “the goal is to create approach we can follow to generate videos.” They now requested this handoff to start a different session.

No reliable end-to-end video generation workflow has been demonstrated. A manually connected zoom preview worked. A native composition draft was generated and syntax checked, but the assistant never rendered or visually verified it in Resolve. Its MP4 was an offline approximation and did not satisfy the user.

## Preferences and authorization

- Arabic labels and narration are preferred. No final voiceover had been supplied; use the script timestamps provisionally and make later retiming practical.
- The user initially chose an illustrative map using existing assets, then asked to find historical borders and authorized a Louisiana test shot.
- Modern country borders in their compositions were manually drawn. Historical acquisition masks were not already available.
- Reading compositions, modifying copies, collecting related assets, and downloading relevant map data were authorized.
- The user considered paying approximately $30 to test Studio, but wants useful proof with Free first. Do not assume purchase approval.
- Repeated console copy/paste is unacceptable as the intended workflow. The user preferred reading and updating exported project files and asked about MCP.
- A Snazzy Maps API key was posted in the conversation. It is intentionally omitted here; it was not saved or used. Do not expose or commit it.

## Environment and access

macOS; current project root: `/Users/naseemtoumeh/edit-projects/davinvi-resolve` (the spelling is intentional).

Installed Resolve was reported by the user's console as Free **21.1.0.15**. Internal Lua Console scripting worked for inspection. External scripting/MCP access was understood to require Studio; verify the installed documentation before making any new capability claims. Building an MCP server does not itself remove Resolve edition restrictions.

Bundled scripting documentation: `/Applications/DaVinci Resolve.app/Contents/Resources/Developer/Scripting/README.md`.

Previous session briefly had unrestricted access. Current session has sandboxed writes within this project and temporary directories; network and GUI commands can require escalation. Do not assume “full access” persists across sessions. Native desktop CUA control was unavailable.

## Files and what they mean

### Originals and linked assets

- `usa/Fusion usa.comp`: original USA composition. Do not overwrite. SHA-256: `3b00dc54f84ec9bc765b2ef5fd30d28f259b1cbd493c4a8b5745bee85c7ca17c`.
- `/Users/naseemtoumeh/MapVideoLab/Fusion usa.comp`: matching original export. The two hashes were checked again when writing this handoff.
- `/Users/naseemtoumeh/MapVideoLab/Fusion Clip 6_1 - Composition 1.comp`: original China-versus-USA export, about 5.55 MB and 375 tools. Contains the earlier test preview node.
- `usa/us-4k.png`: original 3840×2160 map image.
- `usa/USA_linked_media.comp`: copy of USA composition with its timeline-bound map Loader changed to an explicit map image and image assets relinked under `usa/assets`. Intended to preserve original animation and effects. Native visual verification remains outstanding.
- `usa/assets/us-4k.png`, `usa/assets/شفاف-أفضل.webp`, `usa/fonts/Damascus.ttc`: collected source assets/font.
- `usa/assets_manifest.json`: original paths and content hashes. Country masks and animation are embedded in the composition; old template/cache paths are not necessarily missing media.
- `usa/Why Is The U.S So Big 🤔 #shorts.txt`: supplied English script with timestamps; authoritative input for adaptation, subject to factual corrections below.
- `/Users/naseemtoumeh/MapVideoLab/usa.wav`: audio file present, about 8.8 MB. Not inspected; do not assume it is the final voiceover.

Older source assets: `/Users/naseemtoumeh/edit-projects/project2/Aj+/`. Includes USA/China/Canada map images, GIFs, video, and narration files. The related WebP was copied from `/Users/naseemtoumeh/edit-projects/general/graphics/شفاف-أفضل.webp`.

### Rejected Louisiana draft

- `usa/USA_Louisiana_Arabic_Test.comp`: generated native composition. Preserves the original tools in the file but routes MediaOut1 through a new `LP_` branch. It does **not** faithfully preserve the original shot's appearance.
- `usa/louisiana_shot.json`: 24 fps, frames 240–527, 10–22 seconds, Arabic captions and event timings.
- `usa/Louisiana_Arabic_Preview.mp4`: 1280×720, 24 fps, 288 frames/12 seconds. Generated with Pillow/FFmpeg, **not rendered in Resolve**.
- `usa/Louisiana_Arabic_Preview.png`, `usa/Louisiana_Storyboard.jpg`: prototype previews.
- `usa/LOUISIANA_TEST_README.md`: import instructions and geometry/source limitations. Read its verification caveat; it is not a completion report.

The draft used a strongly zoomed raster map, orange region fill, and dark title/subtitle plates. It departed from the user's existing design and looked poor. Existing camera/country groups remain in the file but are bypassed by the new output branch. Full range is 0–1439; only the Louisiana interval was adapted. The rest of the script was **not** implemented.

### Scripts and diagnostics

Original working files live in `/Users/naseemtoumeh/MapVideoLab/`. Copies of all its `.lua`, `.py`, and `.diff` files were collected into `session_archive/MapVideoLab/` for this handoff. Large original compositions/audio and the virtual environment were not duplicated.

- `check_resolve.lua`: read-only environment/tool check.
- `export_current_comp.lua`: attempted settings export; filesystem/settings APIs failed. Fallback snapshot printed empty Tools and did not export a useful graph.
- `inspect_map_controls.lua`: successful inspection of inputs and spline keyframe times.
- `test_map_zoom.lua`: eventually created a native Transform preview; final version requires manual image connection. Earlier versions failed.
- `check_zoom_preview.lua`: diagnosed disconnected preview input.
- `Map_Test_Zoom_Output.comp` in the original folder: trivial earlier China zoom routing test, not new video production.
- `build_louisiana.py`: approximate historical polygon registration to raster map.
- `compile_louisiana.py`: appends prototype `LP_` tools and rewires output.
- `render_louisiana_preview.py`: offline animation approximation.

Python environment: `/Users/naseemtoumeh/MapVideoLab/.venv`; dependencies included Pillow, NumPy, Shapely, PyProj, Lupa, svgpathtools, CairoSVG, arabic-reshaper, python-bidi. Cairo required `DYLD_FALLBACK_LIBRARY_PATH=/opt/local/lib`. Scripts contain local paths; archived copies are references, not a portable package.

## What we learned from the existing compositions

Original USA composition runs frames 0–806 at 24 fps (~33.6 seconds). It contains manually drawn modern USA, Canada, Mexico, and Cuba groups; Damascus Arabic labels; ocean labels; camera and layer reveal animation.

The original USA fill is blue, approximately RGB `(0, 0.443, 1)`. Camera uses `Transform1`, an OFX Resolve Transform, fed by `MultiMerge1.Output`. Animated inputs are `posX`, `posY`, and `zoom`, driven by `Transform1PositionX`, `Transform1PositionY`, and `Transform1Zoom`. Original camera keyframe times include 34, 81, 185, 201, 299, 337, 417, 529, 644, 734. This graph and style should be understood before adapting it.

The original `MediaIn1` exports as a Loader with timeline MediaProps but no standalone image filename. `MediaIn2` is another image Loader. `MediaOut1` exports as a Saver fed by Transform1.Output. Exported tool names/classes can differ from UI labels; avoid assuming generic node APIs.

China composition had country groups and many polygon masks, animated color/visibility controls, Arabic chapter titles, and an OFX camera. It supplied useful node examples but was never converted into a robust reusable template.

## Scripting failures and narrow successes

User console errors included:

1. Fusion settings writer unavailable.
2. `io` nil in Console.
3. `GetMainOutput` nil.
4. `comp:DeleteTool` nil.
5. Created zoom Transform had a disconnected Input and no image.
6. Automated input connection attempts reported failure.

Do not repeat these unverified calls. `FindMainOutput`/`FindMainInput` were identified as alternatives to `GetMainOutput`/`GetMainInput`. Tool deletion was not reliably demonstrated. `FindTool`, `GetToolList`, `GetAttrs`, `GetInputList`, `GetInput`, and spline inspection worked in the user's Console.

The check at frame 30 showed `MapVideoLab_ZoomPreview.Input` disconnected, while OFX `Transform1.Source` was connected to MultiMerge3 and produced an image. `SourceTo` was disconnected; it was not the desired source connector. MediaOut1 also produced an image. The user manually connected the preview and confirmed they saw the map and zoom.

Earlier spline handling produced an unexpected Size (~1.78265 at frame 30), rather than the planned interpolation from 1 to 1.35. Final approach used spline SetKeyFrames directly. This remains a demonstration, not a verified general automation layer.

Native `.comp` syntax was tested with Lupa by providing proxy constructors for Fusion's Lua-like settings syntax. That proves syntax/reference structure only; it does not prove Fusion renders the same result or correctly evaluates all inputs.

## Script coverage and factual issues

The supplied script is about US territorial expansion, approximately 58–60 seconds:

- 0–10 s: introduction and post-Revolutionary War territory (1783).
- 10–22 s: Louisiana Purchase (1803), $15 million, expansion.
- 22–27 s: Florida treaty (1819).
- 27–33 s: Texas annexation (1845).
- 33–40 s: Oregon Treaty (1846).
- 40–46 s: Mexican-American War and Treaty of Guadalupe Hidalgo.
- 46–54 s: Alaska purchase (1867), $7.2 million.
- 54–end: Hawaii; original script incorrectly associates annexation with 1893.

Corrections flagged: Hawaii annexation was 1898; 1893 was overthrow of the kingdom. Florida treaty signed 1819, transfer occurred 1821. Final wording and timing have not been agreed or fully translated. Sources previously consulted:

- https://www.archives.gov/milestone-documents/joint-resolution-for-annexing-the-hawaiian-islands
- https://history.state.gov/milestones/1801-1829/florida

## Historical data and limitations

Files under `usa/assets/historical/`:

- `national_atlas_acquisitions.svg`: public-domain-in-US National Atlas acquisition reference, downloaded from Wikimedia. Source page: https://commons.wikimedia.org/wiki/File:Aquired_Lands_of_the_US.svg . Download: https://upload.wikimedia.org/wikipedia/commons/4/4e/Aquired_Lands_of_the_US.svg
- `louisiana_purchase.geojson`, `dataset_metadata.json`: ArcGIS educational-only layer. It is **not** an unrestricted reusable geometry asset. Attribution recorded Dr Jesse Hong/National Atlas.
- `ne_110m_coastline.geojson`: Natural Earth public-domain coastline, used for projection fitting.
- `atlas_reference.png`, `atlas_detail.png`, `alignment_grid.jpg`, `louisiana_alignment_preview.png`: inspection images.
- `louisiana_atlas_coordinates.json`, `louisiana_aligned_pixels.json`, `alignment.json`: generated geometry/registration outputs.

ArcGIS endpoint used: `https://services1.arcgis.com/TQSFiGYN0xveoERF/ArcGIS/rest/services/territorial_expansion_17/FeatureServer` (Louisiana layer 5). Item metadata: `https://www.arcgis.com/sharing/rest/content/items/c9a0335b0a164a369e2a353a997dc7b7?f=pjson`.

Prototype pipeline extracted patterned SVG acquisition paths, unioned them, and kept the largest polygon. Smaller fragments were dropped. An estimated EPSG:5070 registration used educational GIS as a reference, then Natural Earth coastline fitting approximated the screenshot's Mercator projection. Output has 204 simplified vertices and approximate bounds x=1781–2062, y=628–937 on the 3840×2160 map. This is illustrative small-scale alignment, not survey-grade historic geometry. Do not claim an exact historical reconstruction or entirely unrestricted data lineage without addressing the registration reference.

Other references consulted: https://www.usgs.gov/centers/eros/science/usgs-eros-archive-digital-maps-national-atlas and https://www.census.gov/programs-surveys/sis/resources/maps/territorial-acquisitions.html . Source claims should be verified again before publishing.

Snazzy Maps supplied the original map appearance, but the exact style URL/projection was not established. Its style API does not supply historical borders.

## Recommended recovery approach — proposed, not yet implemented

1. Establish a visual baseline from an original Fusion shot and its actual Resolve output. Reading nodes alone did not capture the user's quality standard.
2. Reproduce that existing shot from the linked asset copy, with actual Fusion render verification. Resolve import/render is still the unproven integration step.
3. Make one useful, restrained change that follows the original composition's camera, typography, color, and reveal behavior. Have the user assess that concrete shot before scaling.
4. Define a small reusable shot specification: timing, region/mask, camera target, label, highlight, and caption. Keep asset/style choices explicit and make retiming possible after narration.
5. Generate composition copies from proven Fusion node patterns. Validate native renders; label any offline approximation honestly.
6. Only after this works, expand to the complete script and evaluate whether Studio/external scripting/MCP meaningfully reduces manual steps.

No new shot, MCP server, or full-script implementation was completed after the user rejected the prototype. Do not start another redesign merely because this handoff exists.

## Suggested message for the next session

“Read SESSION_HANDOFF.md in this workspace. My goal is a repeatable process for generating map videos using my existing Fusion work. The previous Louisiana prototype was rejected. Start by understanding and verifying an original shot, then establish an approach that preserves my style. Do not treat the offline preview as a Resolve render.”
