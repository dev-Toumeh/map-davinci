# Moving icons

There are two ways to display a pair of icons: the 2D moving-icons group below, and the [3D icon pair](#3d-icon-pair) further down. Choose by where the icons must live: a 2D Merge/MultiMerge stack, or the map's 3D scene.

## 2D moving icons group

Work on [moving-icons.setting](/Users/naseemtoumeh/edit-projects/davinvi-resolve/skills/my-fusion-skills/assets/moving-icons.setting). Read the current file before editing; the user also changes it in Fusion, and node names or values may have changed since these notes were written. Preserve unrelated user edits and do not alter a live composition unless requested.

The original `app/fusion/templates/nodes/moving-icons.setting` was lost. On 2026-10-24 the current file was extracted from the user's Resolve `pakistan` project (the newer of its two Fusion compositions), where the user had turned the 2026-10-04 `MacroOperator` (`MacroTool1`) into an editable `GroupOperator` named `MovingIconsOppositeStart`. Internal node names keep the `_1` suffix. The extraction was a file operation; it passed static link checks but has not been re-imported into Resolve.

### Current design

- The combined image output is the group's `MainOutput1`, from `MultiMerge3_1`, with `Background3_1` set to a transparent 800 × 800 canvas. Its active foreground layers are `Merge1_1` (first icon) and `Merge2_1` (second icon), each combining a 512 × 512 PNG with its original cream-colored 515 × 518 icon backplate. These labels describe roles only; do not carry the source project's icon names into reusable knowledge. **Do not remove or make the icon backplates transparent when the user asks to hide the path background.**
- The user-verified motion keeps both original closed `Publish1_1`/`Publish2_1` ellipse point sequences intact. `Path5_1Displacement` and `Path6_1Displacement` run from **-0.25 at frame 800 to the original 0.213 at frame 810** in the pakistan-project version (earlier notes recorded frame 821 with value handles `(807, -0.0957)` and `(814, 0.0587)`; the current flat handles sit at 803.33 and 806.67). The baseline started at 0; the negative start moves earlier along the same direction while preserving the original end. Do not cyclically reorder ellipse vertices or substitute 0.5 as the start: those earlier attempts failed in the user's Resolve preview.
- The size splines `Merge3_1Size` and `Merge4_1Size` grow both icons from 0.10 to 0.47 over frames 800–810 in the current version (821 in earlier notes). Look up each spline through its Merge's `Size` input rather than assuming a project-specific name. Treat these numbers as template values, not universal defaults. At final size, the complete backplates—not just the visible icon pixels—must remain inside the 800 × 800 canvas and not overlap.
- `Background8_1` and `Background9_1` have alpha 0, so the path/line masks (`Polygon2_1`/`Polygon3_1`) create no visible border. Their intermediate `Merge3_1`/`Merge4_1` branches remain but are not the active MultiMerge foregrounds.
- The two `MediaIn` nodes contain project-specific Media Pool IDs and absolute image paths. In another project, verify the images resolve; do not assume the saved IDs are portable.

### Editing and checking

When adapting one branch, trace its motion path and size, then mirror or adapt the other branch as requested. A `PolyPath` position is driven by its `Displacement` spline. Compare the actual start **and end** positions in Resolve before claiming a motion change works; checking only Lua syntax or keyframe text missed the previous failures. Check `MultiMerge3_1` layer connections and the group's `MainOutput1` after editing. For a transparent path, keep the path backgrounds at alpha 0 while leaving the icon backplates opaque. Do not change the path shape or shrink icons just to prevent overlap; first separate the paths while checking full-image bounds.

For `.setting` keyframes, Bezier handle coordinates are stored as **absolute** frame/value positions. If using Fusion's `SetKeyFrames()` API instead, handles are **relative** to their keyframes; consult the general `davinci-resolve-fusion` skill before scripting animation changes.

To test a changed template, drag a fresh `moving-icons.setting` into an empty area of Fusion's Node Editor. The current export appears as `MovingIconsOppositeStart`; an already-loaded instance does not update from the file. Use its `MainOutput1` for the combined 2D image, following the composition workflow in the main skill when integrating it with the map.

## 3D icon pair

Asset: [3d_two_icons_merge.setting](/Users/naseemtoumeh/edit-projects/davinvi-resolve/skills/my-fusion-skills/assets/3d/3d_two_icons_merge.setting). Extracted on 2026-10-24 from the user's Resolve `pakistan` project (the older of its two compositions, where both icons are still groups; the newer one only differs by node positions and has the second icon ungrouped). It passed static link checks; it has not been re-imported into Resolve.

- Two instances of the [3D masked icon with shadow](3d-masked-icon-with-shadow.md): `Map_3D_Icon_Shadow_Object` (output `Map_Icon_3D_Parent`) and `Map_3D_Icon_Shadow_Object_1` (output `Map_Icon_3D_Parent_1`). Each draws its icon from procedural masks, not image files.
- `islamvshindusm` (Merge3D) combines them: `Map_Icon_3D_Parent` on SceneInput1, `Map_Icon_3D_Parent_1` on SceneInput2. Its translation is keyframed at 148 → 156: X −0.003 → −0.021, Y 0, Z 0 → 0.536.
- `Override3D1` toggles the pair's visibility from `Override3D1Visible`: 0 at 133, 1 at 162–227, 0 at 247. Its output is the stack's single 3D scene output.
- Second icon motion follows the 3D-masked-icon notes (translation 148/156, Z rotation keys 148–241). The first icon's Z rotation is keyed at 200 → 0, 212 → 26.1, 226 → −13.
- The keyframe splines sit beside the groups at the top level of the setting, not inside them. Keep them together when copying; pasting a group alone drops its animation links.

Connect `Override3D1.Output` to a free SceneInput on the map's scene Merge3D (in the source project it was `Map_3D_Scene` SceneInput19). It is a 3D scene, not a 2D image, so it cannot feed the 2D moving-icons stack or a MultiMerge. All frame numbers are this example's timing; shift the keys together when retiming.

In the source composition, `MovingIconsOppositeStart` was not connected to any output, while the 3D pair was rendering through `Map_3D_Scene`. They are separate display types with no shared nodes.
