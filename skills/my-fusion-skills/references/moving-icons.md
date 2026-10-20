# Moving icons group

Work on `app/fusion/templates/nodes/moving-icons.setting`. Read the current file before editing; the user also changes it in Fusion, and node names or values may have changed since these notes were written. Preserve unrelated user edits and do not alter a live composition unless requested. The user-verified version saved on 2026-10-04 is a 2D `MacroOperator` (`MacroTool1`) with internal node names suffixed `_1`; do not convert it to a Group merely to match an earlier draft.

## Current design

- The combined image output is `MainOutput2` from `MultiMerge3_1`, with `Background3_1` set to a transparent 800 × 800 canvas. Its active foreground layers are `Merge1_1` (first icon) and `Merge2_1` (second icon), each combining a 512 × 512 PNG with its original cream-colored 515 × 518 icon backplate. These labels describe roles only; do not carry the source project's icon names into reusable knowledge. **Do not remove or make the icon backplates transparent when the user asks to hide the path background.**
- The user-verified motion keeps both original closed `Publish1_1`/`Publish2_1` ellipse point sequences intact. `Path5_1Displacement` and `Path6_1Displacement` run from **-0.25 at frame 800 to the original 0.213 at frame 821**. Their value handles are `(807, -0.0956666666666667)` and `(814, 0.0586666666666666)`. The baseline started at 0; the negative start moves earlier along the same direction while preserving the original end. Do not cyclically reorder ellipse vertices or substitute 0.5 as the start: those earlier attempts failed in the user's Resolve preview.
- The size splines connected to `MultiMerge3_1` layer 2 and layer 3 grow both icon layers from 0.10 to 0.47 over frames 800–821, with the original size handles intact. Look up each spline through its layer's `Size` input rather than assuming a project-specific name. Treat these numbers as template values, not universal defaults. At final size, the complete backplates—not just the visible icon pixels—must remain inside the 800 × 800 canvas and not overlap.
- `Background8_1` and `Background9_1` have alpha 0, so the path/line masks (`Polygon2_1`/`Polygon3_1`) create no visible border. Their intermediate `Merge3_1`/`Merge4_1` branches remain but are not the active MultiMerge foregrounds.
- The two `MediaIn` nodes contain project-specific Media Pool IDs and absolute image paths. In another project, verify the images resolve; do not assume the saved IDs are portable.

## Editing and checking

When adapting one branch, trace its motion path and size, then mirror or adapt the other branch as requested. A `PolyPath` position is driven by its `Displacement` spline. Compare the actual start **and end** positions in Resolve before claiming a motion change works; checking only Lua syntax or keyframe text missed the previous failures. Check `MultiMerge3_1` layer connections and `MainOutput2` after editing. For a transparent path, keep the path backgrounds at alpha 0 while leaving the icon backplates opaque. Do not change the path shape or shrink icons just to prevent overlap; first separate the paths while checking full-image bounds.

For `.setting` keyframes, Bezier handle coordinates are stored as **absolute** frame/value positions. If using Fusion's `SetKeyFrames()` API instead, handles are **relative** to their keyframes; consult the general `davinci-resolve-fusion` skill before scripting animation changes.

To test a changed template, drag a fresh `moving-icons.setting` into an empty area of Fusion's Node Editor. The current export appears as `MacroTool1`; an already-loaded instance does not update from the file. Use its `MainOutput2` for the combined 2D image, following the composition workflow in the main skill when integrating it with the map.
