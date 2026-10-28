# GIF files as looping Fusion groups

Use this method when adding a `.gif` animation to this project's Fusion composition or creating a reusable GIF node. Convert it into PNG frames and drive their timing with a TimeStretcher.

## Sources and example node

Workspace: `/Users/naseemtoumeh/edit-projects/davinvi-resolve`.

- Example package: [gif_to_png_loop](/Users/naseemtoumeh/edit-projects/davinvi-resolve/skills/my-fusion-skills/assets/gif_to_png_loop).
- Example node: [SwipeUpLoop.setting](/Users/naseemtoumeh/edit-projects/davinvi-resolve/skills/my-fusion-skills/assets/gif_to_png_loop/SwipeUpLoop.setting), with `Frames/`, `timing.json`, and `Install_SwipeUpLoop.lua` beside it.
- Full method and app workflow: [Fusion-GIF-Loop-Implementation.md](/Users/naseemtoumeh/edit-projects/davinvi-resolve/app/docs/Fusion-GIF-Loop-Implementation.md).
- Existing converter: `app/core/gif_loop.py`, especially `create_gif_loop_group(data, exports_dir, group_name="GIFLoop", timeline_fps=24, output_dir=None)`. `data` is GIF bytes. Reuse its extraction and timing-expression generation.
- App export layout reference: `references/nodes/gif-reference.setting`.

The example contains 12 RGBA frames at 480×480 with a 790 ms loop. These values belong to this GIF only. Regenerate frame count, durations, and timing expression for each new GIF.

## Adding a GIF

1. Use the app's `/gif` page (GIF → Fusion beside Settings), or its existing converter for programmatic work. Match Timeline FPS to the target composition; the project default is 24.
2. Decode frames sequentially with Pillow so disposal/compositing is respected. Save full RGBA numbered PNGs in a unique permanent `Frames/` directory and record each frame duration. The converter substitutes 100 ms for missing/zero durations.
3. Build an editable `GroupOperator` containing `Loader → TimeStretcher`. Point the Loader to the absolute path of the first PNG and load the complete sequence: `Length = frame_count`, `TrimIn = 0`, `TrimOut = frame_count - 1`, `GlobalStart = 0`, `GlobalEnd = 1000000`, and `Loop = 1`. Extend the range further if the target comp requires it.
4. Preserve unequal frame durations with integer source-frame selection in `TimeStretcher.SourceTime`. Calculate `phase_ms = (((time - comp.RenderStart) * 1000 / TimelineFPS * Speed) + Offset * 1000) % loop_ms` and select the frame containing that phase from cumulative duration boundaries. The converter uses balanced `iif` branches. Update expression tool references when renaming internal nodes.
5. Publish Speed, Timeline FPS, and Offset (source seconds). Speed 1 preserves source timing, 2 doubles it, 0.5 halves it, and 0 freezes at the phase selected by Offset. The loop repeats regardless of the GIF's embedded loop count.
6. Generate escaped Lua asset paths and valid, unique tool identifiers. Keep the PNG assets with the setting; pixels are not embedded. Import a fresh setting into empty Node Editor space, or paste its full settings text.

The app exports one centered GIF branch over a transparent 3840×2160 Background using a MultiMerge. Its group output is the MultiMerge composite, with Position, Size, Angle, Blend, and canvas dimensions exposed. The simpler example outputs the TimeStretcher directly. Use the appropriate existing layout without duplicating GIF copies.

App packages go to the configured Exports folder under `gif-loops/<unique-name>/`, unless the GIF page's saved export-folder override is set. That override is independent of map exports and affects future conversions only.

## Example import and relinking

On 2026-10-24, `PNGFrames` in the example setting and its README were relinked from the old `app/fusion/templates/nodes/SwipeUpLoop/Frames` location to the package in this skill:

`/Users/naseemtoumeh/edit-projects/davinvi-resolve/skills/my-fusion-skills/assets/gif_to_png_loop/Frames/swipe_0000.png`

This was a file edit only; confirm the Loader resolves in Resolve. Ensure it loads all 12 frames, rather than a still. Alternatively use the package's installer and choose the current first PNG. The example currently stores 30 FPS; set it to the composition rate (24 for default project exports). Reinspect these values before future edits in case the template has changed.

## Connections and validation

- In 2D, connect the group to a Merge foreground input or a local MultiMerge foreground layer.
- For 3D, connect its 2D image output to an ImagePlane3D, then connect the plane to Merge3D. Check plane visibility at the preview frames.
- For groups containing Background/MultiMerge, output the actual GIF composite. Outputting only the Background hides the GIF. Keep Background alpha 0 for a transparent canvas.
- Check asset existence, frame count, timing boundaries, Lua syntax, and internal `SourceOp` links. Preview the group output in Resolve across multiple loop boundaries, at the target FPS and two speed values; check alpha and placement.

Earlier extraction, timing, Lua, and app tests passed, but live Resolve import/playback was not verified in that work. Static checks do not establish Resolve playback compatibility; record the actual preview result when available.
