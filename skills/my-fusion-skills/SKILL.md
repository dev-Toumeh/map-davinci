---
name: my-fusion-skills
description: Project-specific DaVinci Resolve Fusion knowledge for this map-animation workspace, including reusable node groups, composition editing, 2D/3D integration, and saved workflows such as moving icons and GIF-to-PNG animation loops. Use for Fusion work in this project; use davinci-resolve-fusion for general API and macro mechanics.
---

# My Fusion skills

This is the shared knowledge base for Fusion work in the `davinvi-resolve` project, not a skill limited to one animation. Add verified, reusable project lessons here as the work evolves. For general Fusion scripting and `.setting` mechanics, also use `davinci-resolve-fusion` when available.

## Project workflow

- To create a new map-animation project, read [creating-a-project.md](references/creating-a-project.md). Generate the base composition through the app, then extend its existing node structure and layout. Map-asset export alone is not composition generation.

- The user's local DaVinci Resolve project-library root (free/Lite macOS installation) is `/Users/naseemtoumeh/Library/Containers/com.blackmagic-design.DaVinciResolveLite/Data/Library/Application Support/Resolve Project Library/Resolve Projects/Users/guest/Projects`. Use this user-provided location when locating native Resolve projects. It is separate from the map-animation app workspace and generated `.comp`/`.setting` exports. Inspect the relevant project before assuming its contents; a root path alone does not identify the active project or authorize database edits.

- Inspect the current composition or template before changing it. The user makes manual edits in Fusion; saved files can differ from earlier versions and may contain work that must be preserved.
- For live composition repairs, native carousel stacks, and reusable-template layout, read [live-template-editing.md](references/live-template-editing.md) before making changes. It records the user's native-node preference, layout conventions, and verified scripting pitfalls.
- Keep editable node stacks as `GroupOperator` settings. A `MacroOperator` is a closed tool; choose it only when a macro with intentionally exposed controls is requested. Drag a saved `.setting` into an empty part of Fusion's Node Editor, then open a group to edit its internal nodes. Add a fresh node after changing a saved setting; an already-loaded instance will not automatically become the new file.
- Check the output type before connecting stacks. A 2D image output cannot connect directly to `map_3d_scene` or another 3D Merge. Composite it after a Renderer3D in 2D, or put it on an ImagePlane3D when it must live in the 3D scene.
- For expanded groups in the Node Editor, **Fusion Settings → Flow → Group Opacity** controls how much of the nodes behind the group remain visible. This is an editor display setting, not rendered alpha.
- Validate `.setting` syntax and internal `SourceOp` links after edits. Such static checks do not replace a Resolve preview; say clearly when a live preview was not possible.

## Saved workflows

- For archive footage or images entering, holding, and exiting along a shared carousel route, use [ArchiveCarousel.comp](assets/ArchiveCarousel.comp) and read [archive-carousel.md](references/archive-carousel.md). It contains four independently timed 2D cards, shared film-frame artwork, and a published path; it is a composition reference, not yet a portable group setting.

- For the two planned 2D entrance trials—Flicker Entrance and Ink Reveal—read [planned-2d-entrances.md](references/planned-2d-entrances.md). These are saved ideas to implement and test later, not completed templates.

- For masked text movement, use [text_down.setting](/Users/naseemtoumeh/edit-projects/davinvi-resolve/skills/my-fusion-skills/assets/text_down.setting) in 2D or [3d_text_down.setting](/Users/naseemtoumeh/edit-projects/davinvi-resolve/skills/my-fusion-skills/assets/3d/3d_text_down.setting) inside a 3D scene. Read [text-down.md](references/text-down.md) for their different outputs, text controls, and saved timing.

- When marking a city or capital on a map with an Arabic label, use [city_label.setting](/Users/naseemtoumeh/edit-projects/davinvi-resolve/skills/my-fusion-skills/assets/city_label.setting) and read [arabic-city-label.md](references/arabic-city-label.md). It is a city-reference marker, not limited to capitals.

- For a masked 3D icon with a separate soft shadow, use [3d_masked_icon_with_shadow.setting](/Users/naseemtoumeh/edit-projects/davinvi-resolve/skills/my-fusion-skills/assets/3d_masked_icon_with_shadow.setting) and read [3d-masked-icon-with-shadow.md](references/3d-masked-icon-with-shadow.md). Inspect the current user-updated asset before adapting it; preserve its saved macro and animation.

- When adding a GIF animation, read [gif-to-png-loop.md](references/gif-to-png-loop.md) and follow the PNG sequence → Loader → TimeStretcher method. Use `app/fusion/templates/nodes/example_gif_to_png_loop/SwipeUpLoop.setting` as the example node.

- For the user-confirmed working curved-arrow reveal, use [curved_Reveal_arrow.setting](/Users/naseemtoumeh/edit-projects/davinvi-resolve/skills/my-fusion-skills/assets/curved_Reveal_arrow.setting) and read [2d-png-entrances.md](references/2d-png-entrances.md) for its wiring, timing, and reuse.

- For a PNG ship or other icon moving along a visible, editable route, use the user-built [moving-icon-with-path.setting](/Users/naseemtoumeh/edit-projects/davinvi-resolve/skills/my-fusion-skills/assets/moving-icon-with-path.setting) and read [moving-icon-with-path.md](references/moving-icon-with-path.md). Its line and icon share a published path; the line reveal and icon travel have separate timing.
- For `app/fusion/templates/nodes/moving-icons.setting`, read [moving-icons.md](references/moving-icons.md) before editing its two-icon animation.
- For moving dots along an editable route, use `app/fusion/templates/nodes/flowing-dotted-line.setting` and read [flowing-dotted-line.md](references/flowing-dotted-line.md) for controls and validation status.

Add new topic-specific references only when there is concrete project knowledge worth preserving. Keep this entrypoint short enough to remain useful as more workflows are added.
