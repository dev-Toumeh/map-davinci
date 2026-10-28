---
name: my-fusion-skills
description: Project-specific DaVinci Resolve Fusion knowledge for this map-animation workspace, including reusable node groups, composition editing, 2D/3D integration, and saved workflows such as moving icons and GIF-to-PNG animation loops. Use for Fusion work in this project; use davinci-resolve-fusion for general API and macro mechanics.
---

# My Fusion skills

This is the shared knowledge base for Fusion work in the `davinvi-resolve` project, not a skill limited to one animation. Add verified, reusable project lessons here as the work evolves. For general Fusion scripting and `.setting` mechanics, also use `davinci-resolve-fusion` when available.

## Project workflow

- To create a new map-animation project, read [creating-a-project.md](references/creating-a-project.md). Generate the base composition through the app, then extend its existing node structure and layout. Map-asset export alone is not composition generation.

- The user's local DaVinci Resolve project-library root (free/Lite macOS installation) is `/Users/naseemtoumeh/Library/Containers/com.blackmagic-design.DaVinciResolveLite/Data/Library/Application Support/Resolve Project Library/Resolve Projects/Users/guest/Projects`. Use this user-provided location when locating native Resolve projects. It is separate from the map-animation app workspace and generated `.comp`/`.setting` exports. Inspect the relevant project before assuming its contents; a root path alone does not identify the active project or authorize database edits.

- The user runs free DaVinci Resolve 21.1.1 (App Store build) and uses the Edit page heavily, not only Fusion. The `samuelgursky/davinci-resolve-mcp` stack is installed at `/Users/naseemtoumeh/tools/davinci-resolve-mcp` (added 2026-10-24) with two MCP servers, `davinci-resolve` (live) and `davinci-resolve-advanced` (offline `.drp/.drt/.drx`, Project.db, Fusion `.comp` authoring), plus the `resolve-*` skills. Paths those skills cite (`docs/...`, `resolve-advanced/...`) are relative to that folder. External scripting is Studio-only, and free 21.1 has no Python scripting at all (verified 2026-10-24), so that stack's live server and its Python `resolve_bridge` cannot work here; use its offline server for files. To read the project that is open live, and to edit its Fusion compositions (undoable, with a database backup first), use the Lua mailbox bridge (Workspace ▸ Scripts ▸ `claude_bridge`, client `~/Projects/resolve-bridge/bridge/claude_bridge_client.py`): read [lua-mailbox-bridge.md](references/lua-mailbox-bridge.md) first, since this Resolve's Lua has no `io` and script output never reaches the Console. Say which path (live bridge or offline files) a fact came from.
- Inspect the current composition or template before changing it. The user makes manual edits in Fusion; saved files can differ from earlier versions and may contain work that must be preserved.
- For live composition repairs, native carousel stacks, and reusable-template layout, read [live-template-editing.md](references/live-template-editing.md) before making changes. It records the user's native-node preference, layout conventions, and verified scripting pitfalls.
- Keep editable node stacks as `GroupOperator` settings. A `MacroOperator` is a closed tool; choose it only when a macro with intentionally exposed controls is requested. Drag a saved `.setting` into an empty part of Fusion's Node Editor, then open a group to edit its internal nodes. Add a fresh node after changing a saved setting; an already-loaded instance will not automatically become the new file.
- Check the output type before connecting stacks. A 2D image output cannot connect directly to `map_3d_scene` or another 3D Merge. Composite it after a Renderer3D in 2D, or put it on an ImagePlane3D when it must live in the 3D scene.
- For expanded groups in the Node Editor, **Fusion Settings → Flow → Group Opacity** controls how much of the nodes behind the group remain visible. This is an editor display setting, not rendered alpha.
- Validate `.setting` syntax and internal `SourceOp` links after edits. Such static checks do not replace a Resolve preview; say clearly when a live preview was not possible.

## Current video

- The Gulf trains explainer (Resolve project `gulf_trains`): its Arabic script, how the main composition is built (map, country shapes and flags, the North Train Network started), the assets and the progress per section are in [gulf-trains-video.md](references/gulf-trains-video.md). Read it before working on that project, then check the live composition through the bridge.
- **PNG generation is always Codex's job** (the user's rule, 2026-10-25). Claude, as lead, writes a precise task (frame, size, coordinates, style, outputs) and runs it with `~/.agents/skills/codex-delegation/ask_codex.sh <task.md>` (see `~/Projects/resolve-bridge/README.md`), checks the result, and does the Resolve side. Claude does not render PNGs itself.

## Saved workflows

- For archive footage or images entering, holding, and exiting along a shared carousel route, use [ArchiveCarousel.comp](assets/ArchiveCarousel.comp) and read [archive-carousel.md](references/archive-carousel.md). It contains four independently timed 2D cards, shared film-frame artwork, and a published path; it is a composition reference, not yet a portable group setting.

- For the two planned 2D entrance trials—Flicker Entrance and Ink Reveal—read [planned-2d-entrances.md](references/planned-2d-entrances.md). These are saved ideas to implement and test later, not completed templates.

- For masked text movement, use [text_down.setting](/Users/naseemtoumeh/edit-projects/davinvi-resolve/skills/my-fusion-skills/assets/text_down.setting) in 2D or [3d_text_down.setting](/Users/naseemtoumeh/edit-projects/davinvi-resolve/skills/my-fusion-skills/assets/3d/3d_text_down.setting) inside a 3D scene. Read [text-down.md](references/text-down.md) for their different outputs, text controls, and saved timing.

- When marking a city or capital on a map with an Arabic label, use [city_label.setting](/Users/naseemtoumeh/edit-projects/davinvi-resolve/skills/my-fusion-skills/assets/city_label.setting) and read [arabic-city-label.md](references/arabic-city-label.md). It is a city-reference marker, not limited to capitals.

- For a masked 3D icon with a separate soft shadow, use [3d_masked_icon_with_shadow.setting](/Users/naseemtoumeh/edit-projects/davinvi-resolve/skills/my-fusion-skills/assets/3d/3d_masked_icon_with_shadow.setting) and read [3d-masked-icon-with-shadow.md](references/3d-masked-icon-with-shadow.md). Inspect the current user-updated asset before adapting it; preserve its saved macro and animation.

- When adding a GIF animation, read [gif-to-png-loop.md](references/gif-to-png-loop.md) and follow the PNG sequence → Loader → TimeStretcher method. Use [SwipeUpLoop.setting](/Users/naseemtoumeh/edit-projects/davinvi-resolve/skills/my-fusion-skills/assets/gif_to_png_loop/SwipeUpLoop.setting) as the example node.

- For the user-confirmed working curved-arrow reveal, use [curved_Reveal_arrow.setting](/Users/naseemtoumeh/edit-projects/davinvi-resolve/skills/my-fusion-skills/assets/curved_Reveal_arrow.setting) and read [2d-png-entrances.md](references/2d-png-entrances.md) for its wiring, timing, and reuse.

- For a PNG ship or other icon moving along a visible, editable route, use the user-built [moving-icon-with-path.setting](/Users/naseemtoumeh/edit-projects/davinvi-resolve/skills/my-fusion-skills/assets/moving-icon-with-path.setting) and read [moving-icon-with-path.md](references/moving-icon-with-path.md). Its line and icon share a published path; the line reveal and icon travel have separate timing.
- For displaying a pair of icons, read [moving-icons.md](references/moving-icons.md) before editing. It covers two display types: 2D icons growing along opposite ellipse paths ([moving-icons.setting](/Users/naseemtoumeh/edit-projects/davinvi-resolve/skills/my-fusion-skills/assets/moving-icons.setting)) and a 3D pair of masked icons with shadows merged into the map scene ([3d_two_icons_merge.setting](/Users/naseemtoumeh/edit-projects/davinvi-resolve/skills/my-fusion-skills/assets/3d/3d_two_icons_merge.setting)).
- For camera moves on the 3D map, use the **map-camera-moves** skill (`~/Projects/resolve-bridge/skills/map-camera-moves`); [camera-moves.md](references/camera-moves.md) holds the history: the user's own style (one Camera3D with Use Target, holds, big zoom range, ±15–40° roll, smooth keys) read from their projects.
- For drawing a real route (railway, road, border) on the 3D map, read [map-route-overlay.md](references/map-route-overlay.md) first: railways as stroked vector shapes (sleepers, rail edge, rail centre; one colour control per line), or PNGs at most 3840×2160 cropped to the line, placed with the map package's pixel transform.
- For a number counting up on the map (distances, speeds, money): **copy a counter that already works, never build one from zero** (user, 2026-10-28). Template: [map_counter.setting](assets/3d/map_counter.setting) (the user's own `ARE_Counter` group, 2026-10-28: UAE 900 كم; gulf_trains also has `SAU_North_Counter`, `SAU_East_Counter`, `SAU_Haramain_Counter` live). **The user's requirements:** the number column starts with an empty line, **no 0** (` \n75\n150 … 900`); inside the group the nodes sit in a grid right beside the group's own position (open the group and they're in view: columns 110 apart, rows 33 apart, Numbers/Join/Gate/TextShadow/Plane in one row, Unit/Blur/ShadowPlane under it, Window/Empty above, Move at the end); never leave nodes at their old flow positions or stacked on each other (`group_counter.py` LAYOUT does this). Copy the group, rename the prefix, then change only: `_Numbers` StyledText (a column of round numbers, 13 lines, the first one empty), `_Unit` text, the keys of `_ScrollY` (count start → end), `_PlaneOpacity`/`_ShadowPlaneOpacity` (fade, now on the BrightnessContrast `_FadeImg`/`_ShadowFadeImg` Gain) and `_GateBackgroundForeground` (gate), and the group's Move X/Y. Plug the group's one output into the country's Merge3D (`Merge3D1` Saudi, `ARE_Merge3D` UAE, `KWT_Merge3D` Kuwait) **and put the group node beside that merge, with the country's other inputs**: a Kuwait counter left next to `Merge3D1` looked wired to Saudi (user, 2026-10-28). Check the node's position, not only the link. No link to any other counter. Damascus has no "/" (use Arial Bold for "كم/س"). **Known issue:** the soft shadow plane cuts holes in the flag planes while `Map_3D_Renderer` Transparency Sorting is Z-buffer (0); sorted (1) fixes it (tested 2026-10-28, slower render). Generators (`counter.py`, `build_counter.lua`) only when no counter exists yet; not the odometer in counter3d.md or the 2D `mkcounter.py`.
- For moving dots along an editable route, use [doted-moving-line.setting](/Users/naseemtoumeh/edit-projects/davinvi-resolve/skills/my-fusion-skills/assets/doted-moving-line.setting) and read [doted-moving-line.md](references/doted-moving-line.md) for controls and validation status.

Add new topic-specific references only when there is concrete project knowledge worth preserving. Keep this entrypoint short enough to remain useful as more workflows are added.

## Viewer looks wrong but the render is fine: check the viewer first

- **Everything white in a viewer** (every plane, even with inputs disconnected) while the renderer
  output is correct: the viewer is showing the **alpha channel** (key `A`; `C` returns to colour;
  or the channel button in the viewer toolbar). Not a comp problem: don't change nodes for it.
  (2026-10-26: cost several rounds of checks on Map_3D_Scene.)
- **A plane missing in a Merge3D view but visible through the camera** (or flickering): it sits at the
  same Z as another plane (z-fighting). Lift overlays above what's under them. gulf_trains layers:
  country plane 0, `<CC>_Tracks_Plane` Translate Z **0.002** (user fix for UAE_Tracks_Plane,
  2026-10-26), city dot 0.00207, label 0.01. Every new country's tracks plane gets Z 0.002.
- **Write-on keys: two keys, not one per frame.** A track's reveal is the `Write Length` of
  `<CC>_<Line>_Rail_Edge_<i>`; key it 0 → 1 with flat handles at 1/3 of the span (same as
  smoothstep). The user deleted per-frame keys by hand (2026-10-26); generators now write two keys
  (branches: keys where their own length leaves 0 and reaches 1).
- **City labels are cut in half:** a 2D node inside the label (`_Pop`, `_Text`, `_Box_Shape`) was
  moved past the edge of the label's fixed canvas (`_Box` 1000×600; e.g. `_Pop` Center y 1.295).
  Keep `_Pop` Center at 0.5, 0.5, `_Box` at 1000×600, text Size 0.11 and plane Scale 0.1647 for
  every city (a bigger canvas makes the label bigger and pop from elsewhere).
- **Placing labels: ask on the frames page, then rebuild (2026-10-27).** Read the live labels
  (`generators/stroke_tracks/read_city_labels.lua` via fusion_run, args `groups`, `frame`; save the
  result), post `frames/labels.py ask --data <read.json>`, and the user drags each box and sets
  appear / fade / leader on http://127.0.0.1:1745. Then `frames/labels.py get <id> > answer.json` and
  `generators/stroke_tracks/rebuild_labels.py answer.json`: it rebuilds each label with
  `kit/city_label.py` `build_city_label()` (the one label builder) and swaps it into the same merge
  input. A rebuilt label is clean: hand nudges inside the old one are not kept.
- **Label beside its dot: give a side, never a raw offset.** Each city's config `placement` is
  `{"side": "n|s|e|w|ne|nw|se|sw", "gap": 8}`; `kit/uae_native.py` `label_offset` puts the box edge
  (diagonal: its corner) `gap` px outside the dot ring (radius 26 px on the 1000 px label canvas),
  from the box's real size. For labels already in the comp, run
  `generators/stroke_tracks/place_city_labels.lua` (fusion_run, args `labels = {{group, side, gap}}`):
  it reads the live box size, rewrites the `_Plane` Translate expressions
  (`station + rot(camera roll) · offset`) and the `_Pop` Pivot, and resets a moved `_Pop` Center,
  `_Box_Shape` Translate or `_Text` CharacterOffset (it reports each reset). Why (2026-10-27): the
  old configs had `offset: [±180, ±180]` box centres whatever the box size, so short names floated
  a label-height away and long ones covered the dot; hand-moved 2D nodes (Al-Ghuwaifat `_Pop`
  Center, Dubai box + text) moved them further. To move a label, change its side, not the nodes.
- **Fade a 3D plane by its image's alpha, never by `MtlStdInputs.Diffuse.Opacity`** (2026-10-27):
  a plane at opacity 0 still blocks what's behind it, punching holes that show the raw satellite
  through the country flag. Put a Merge (transparent Background, the image as Foreground, Blend
  animated) between the image and the plane, as the app does for close-ups.
- **Labels float above their dots: close, tilted cameras show parallax** (2026-10-27, Bahrain):
  - labels at Z 0.01 over dots at 0.00207 shifted ~150 px at camera distance 0.19 with a 39° tilt,
    so the leaders missed the dots, although the map positions were exact;
  - labels that follow the camera (`follow_camera` in `kit/city_label.py`) come down to
    0.00207 + 0.00793·factor²;
  - check close shots on a still, not with the numbers alone.
- **Never add UserControls + `tool:Refresh()` from a script in Resolve 21's Fusion:** reading
  `tool.UserControls` errors, and Refresh rebuilds the tool; after an undo the tool vanished and the
  comp could no longer `CopySettings`/`Paste` until reopened (2026-10-26, two city label planes lost).
  `comp:CopySettings` still errored ("attempt to index a string value") after a reboot. To rebuild a
  tool, use `comp:AddTool(id, -32768, -32768)`, copy a sibling's unconnected Number/Point/FuID/Text
  inputs with `SetInput`, then rewire it and re-set its expressions. That worked for
  `UAE_City_AlGhuwaifat_Plane` (2026-10-26).
- **`comp:AddTool` with a tool selected splices the new tool in after it** (2026-10-28): a temporary
  Saver landed between `Vector_Layers` and `MediaOut1`, and deleting it relinked `MediaOut1` to the
  Saver's source (`ARE_Canvas`): the map output vanished. Before adding any tool from a script, call
  `comp:SetActiveTool(nil)`, check the new tool's `Output:GetConnectedInputs()` is empty, and after a
  script edit compare `MediaOut1`'s source with what it was. A Saver also reads trailing digits in its
  file name as the frame field (`node_123.png` wrote `node_000000001830.png`): name it `..._0000.png`.
