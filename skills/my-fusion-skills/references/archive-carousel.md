# Archive carousel

## App generator (Go)

The app now provides `/archive-carousel`, backed by `app/tools/archive-carousel` (Go). The Python app manages its local process only. Read [generator usage](/Users/naseemtoumeh/edit-projects/davinvi-resolve/app/tools/archive-carousel/README.md) for build, API, export, and relinking details.

Start with three slots; add/remove/reorder videos or photos, choose source starts and section durations, a shared 4:3/16:9/1:1/9:16 card ratio, and fill/crop or fit. Defaults: 24fps, UHD transparent canvas, **10-frame first and subsequent entrances/exits**. Section durations include movement; handoffs overlap at boundaries, and the final card holds. Selected clips and film artwork are packaged with one editable native-node group setting.

Generated spline keys start at frame 0: set the target composition global start to 0, FPS to the chosen value, and end frame to total frames minus one. A nonzero global start needs a coordinated keyframe shift. Loaders reference the generated folder's absolute paths; moving a package requires relinking.

Verified: Go race/unit/integration tests, Lua table syntax/internal connections, exact timing schedule, mixed media extraction/FPS conversion, film asset dimensions/alpha for four ratios, HTTP/browser uploads/reordering/downloads and desktop/mobile layouts. This is **not** a Resolve visual or save/reopen verification. Keep that acceptance check explicit; do not promise the original asset has been modified or the generator has been visually approved in Fusion.

## Original reference composition

Baseline: [ArchiveCarousel.comp](../assets/ArchiveCarousel.comp). Inspect the current asset before adapting it; preserve the user's original file. This is an animated 2D composition, not a static carousel or a packaged `.setting` group. Inspection here was file-based, not a live Resolve playback test.

## Structure

The four cards use the same published closed curve (`Publish1`), but independent `PolyPath.Displacement` splines control their timing. Final output is `MultiMerge1 → MediaOut1`.

| Card | Internal stack | Final layer / path | Entrance frames | Hold frames | Exit frames |
| --- | --- | --- | --- | --- | --- |
| 1 | `v1 → t1 → MultiMerge5` | Layer3 / Path2 | 2–20 | 20–160 | 160–170 |
| 2 | `v2 → t2 → MultiMerge4` | Layer4 / Path3 | 159–170 | 170–320 | 320–330 |
| 3 | `v3 → t3 → MultiMerge3` | Layer2 / Path1 | 320–330 | 330–599 | 599–610 |
| 4 | `v4 → t4 → MultiMerge2` | Layer5 / Path4 | 599–610 | From 610 | No saved exit |

Saved composition rate: 24fps; render/global range: frames 2–837. These are frame numbers in this asset, not seconds or source-video FPS. Preserve fractional spline keys and easing handles when retiming.

- Each card merge combines transformed footage with `MediaIn1`, the shared `Vintage 8mm Film.png` overlay. Its blend is 0.37; its size is approximately 0.63. Change shared frame artwork there, not in each path.
- `Background2` supplies a transparent 3840×2160 canvas. Nodes use composition frame-format settings; verify dimensions in the target comp.
- Final card layer sizes are 3.22. Path centers are approximately (-1.000679, 1.64094), size 4.255. These offsets are intentional saved framing, not values to normalize automatically.
- Entrance displacement is approximately 0.75 → 0.5, hold at 0.5, exit toward 0.25. Path4 has only entrance keys. This is a staggered sequence, not an endless loop.
- `Polygon1 → Background1` draws a separate visible route layer in `MultiMerge1.Layer1`. Its write length animates 0.425 → 0 during frames 2–20. Hide that layer if only the cards are desired; retain `Publish1` and the path connections.

## Reuse and editing

Replace media at `v1`–`v4`; keep framing in `t1`–`t4`, card assembly in their respective merges, and motion in the `Path*Displacement` splines. Adjust the shared curve via `Publish1` only when changing the route for all cards. Separate content, framing, geometry, and timing so a media replacement does not rebuild the animation.

This source contains local file paths and Media Pool IDs. Relink footage and frame artwork in the target project; copying the comp does not package its media. `v1` has a saved `SourceOp = "v3"` instance relationship outside its inputs: inspect instance-linked controls before expecting fully independent edits. Some saved footage metadata and clip filenames differ, so use the actual Resolve media link as authority.

The final merge also retains layer names/order entries 6–8 without corresponding foreground inputs; these are not three additional cards. Do not clean up the original structure merely to document it. `MediaIn2` is not on the final image output chain.

For a reusable node, work on a new copy and create an editable `GroupOperator` setting with a 2D output; do not rename this `.comp` to `.setting`. Preserve internal published-path connections and verify first/mid/last frames plus each card handoff in Resolve. Avoid claiming portable or visually verified behavior from text inspection alone.
