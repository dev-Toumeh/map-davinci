# Moving icon with a visible path

The user-built, working reference is `assets/moving-icon-with-path.setting`. Inspect that current file before reuse; the user may revise it in Fusion. It is a `GroupOperator` named `MacroTool1`, and its internal image chain is:

`Background1` → `MultiMerge1.Background`

`Publish1` → `Polygon1.Polyline` → `Background2.EffectMask` → `MultiMerge1.Layer1.Foreground` (visible line)

`Publish1` → `Path1.PolyLine`; `Path1.Position` → `MultiMerge1.Layer3.Center`; `MediaIn2` → `MultiMerge1.Layer3.Foreground` (ship)

The **same `PublishPolyLine`** supplies the rendered mask and the ship movement path. This is the core behavior to preserve when reshaping the route. The line is real output from a masked `Background`, connected to `MultiMerge`; a path modifier on its own is only a motion guide, not a rendered line. `MultiMerge1` composites its background and layers using the saved `LayerOrder` of 1, 3, 2.

## Timing and controls in the saved example

- `Polygon1.WriteLength` uses `Polygon1Length`, from **0 at frame 81** to **1 at frame 182**.
- `Path1.Displacement` uses `Path1Displacement`, from **0 at frame 107** to **1 at frame 211**. Line and ship timings differ; preserve this lag unless a new shot calls for another relation. To move backward, keyframe displacement from 1 toward 0. The line's WriteLength may also reverse if desired.
- `MultiMerge1.Layer3.Angle` has its own keyed spline at frames 143–210; the ship turns manually along the route. `Path1.Heading` is exposed as a second group output but does not drive the saved angle spline.
- The group's only exposed **image input** is `MainInput1` → `MultiMerge1.Layer2.Foreground`, which is an unused/empty extra layer in this export. The visible ship is `MediaIn2` on **Layer 3**. Do not tell the user to connect a replacement ship to the current group image input; it will appear on Layer 2 rather than replace the ship. To make the template reusable, repoint `MainInput1` to `Layer3.Foreground` or replace `MediaIn2` inside the group, then test.
- `MediaIn2` has a project Media Pool ID and references `/Users/naseemtoumeh/edit-projects/general/icons/Oil Tanker Ship.png`. This ID may not resolve in another project. `Background1` is 3840 × 2160 with alpha 0.331, so compositing it over a different map may change the map's look. Check aspect ratio, canvas size, and alpha when adapting it.

## Reuse

Drag a fresh copy of the setting into Fusion and open its group. Select `Polygon1` and edit its published `Publish1` polyline in the viewer/Modifiers to change the route; both line and ship path should follow. Adjust the two splines separately to control when the line draws and when the ship travels. Replace the Media Pool based ship source before using the group in a new project, and connect the group output to the 2D chain after the map renderer.

This note describes the saved user-built asset; do not rewrite or relocate that asset based on the earlier experimental `PNG_Move` / `Ship_Moving_Line` files in `exports/kuwait_opening_01/templates`. Those experiments had only static syntax checks and were not user-approved. When making a derived template, verify the visible line, image input, route shape edit, forward/backward travel, and render in Resolve before calling it working.
