# Map / Fusion editor session handoff

Created: 2026-09-23

## Repository state

- Repository: `/Users/naseemtoumeh/edit-projects/davinvi-resolve`
- Branch: `main`
- Remote: `origin` → `git@github.com:dev-Toumeh/map-davinci.git`
- `main` is synchronized with `origin/main`.
- Current latest commit: `26fd778 Animate solid connections with Polygon WriteLength instead of shape morphing`
- This handoff file is intentionally untracked; do not commit it unless the user asks.

### Important recent commits

```text
26fd778 Animate solid connections with Polygon WriteLength instead of shape morphing
c735a86 Gate animated connection lines at Fusion merge and active frame range
78c9b60 Merge fix/fusion-camera-projection
ea9c0db Keep sparse Fusion camera timing keys while preserving per-frame connection shapes
070979b Replace text connections with native geometry and consistent preview sizing
0a93d9c Fix Fusion camera coordinates and preserve browser interpolation
69c881f Refine connection controls and graphics
ed20b5c Improve commentary and connection editing
623811a Add editable commentary timeline
```

## Run the application

```bash
cd /Users/naseemtoumeh/edit-projects/davinvi-resolve
.venv/bin/python app/server.py
```

The local app uses `http://127.0.0.1:8787`.

The server is normally restarted after a pull using:

```bash
kill $(pgrep -f 'app/server.py') 2>/dev/null || true
.venv/bin/python app/server.py
```

## User requirements and working preferences

- Do not claim visual/Resolve behavior is fixed unless it was actually checked in Resolve or rendered and inspected.
- Do not commit new work unless the user explicitly asks.
- Do not delete/revert user files without explicit confirmation.
- Preserve editable Fusion controls and paths.
- Default new output is vertical 4K: `2160x3840`, 24 fps unless changed.
- User values direct evidence and gets frustrated by speculative diagnoses. Inspect the actual comp/render before explaining a cause.

## Major app features already implemented

### Animation / camera

- Browser map-video editor with editable camera keyframes and Fusion generation.
- Latest merged camera-projection work samples the browser camera for Fusion while retaining sparse Fusion timing keys.
- The browser and Fusion camera coordinate relationship is still an area requiring Resolve visual validation, especially for arbitrary countries.
- Country-specific saved `fusion_path` overrides remain relevant for historic calibrated exports (Saudi, Brazil, DZA); do not overwrite them from old browser tabs.

### Connections

- Connection editor supports start/end map points, straight/curved paths, line style, color, thickness, arrowhead, start/arrival/disappearance timings.
- Empty `Disappear frame` means visible through end of composition.
- `Use playhead` buttons exist for Start and Arrival frame fields.
- Fusion connection generation has recently changed from TextPlus glyph lines to native geometry (`app/fusion/connection_geometry.py`).
- Connection-line duplication/static-line behavior is actively being validated. The recent merged commits specifically try to gate lines by their active frame ranges and animate solid lines with Polygon WriteLength.
- Do **not** assume a duplicate seen in Resolve comes from multiple imported comps; inspect the exact generated `.comp` and Resolve result first.

### Commentary

- Commentary is stored as `commentary.clips`, supporting multiple uploaded sections.
- Clips support add, select, drag/move, trim via edges, split at playhead, delete, volume, save/reopen.
- WaveSurfer is vendored locally at `app/static/vendor/wavesurfer.min.js`.
- Commentary controls are in the left panel and hidden when Camera keyframes edit mode is selected.
- Audio files are served with audio MIME handling in `app/server.py`.

### UI

- Left panel was styled into section cards with yellow full-width headers. This is user-approved styling direction.
- Active export is preserved in URL (`?export=...`) and localStorage, so reload should return to the active package.

## Syria / Cyprus / Egypt package

Location:

```text
app/exports/syria_cyprus_egypt/
```

Archive created for the user:

```text
app/exports/syria_cyprus_egypt_assets.zip
```

It is approximately 144 MB and includes maps, masks, geometry, animation data, Fusion comps, commentary, and rendered video.

### Existing Fusion compositions (do not delete without permission)

```text
frame 212 bug Composition v003.comp
scene_v001.comp
scene_v002.comp
scene_v003.comp
scene_v003 after_manual_update.comp
scene_v004.comp
scene_v008.comp
scene_v009.comp
scene_v009_fix_keyframes.comp
scene_v010.comp
scene_v011.comp
scene_v012.comp
```

`scene_v008` and later files were generated/user-created during testing; treat them as user work.

### Known analysis from old render

`app/exports/syria_cyprus_egypt/video/export_scene_v002.mov` is a 2160x3840 / 24 fps / ~70 second render. It visibly contains old TextPlus glyph/arrow rendering defects. Do not use it to claim the latest native-geometry connection code is correct or incorrect.

At frame 212 in the old `scene_v002.comp`, there is no direct key at 212. Its camera is driven by `Map_AnimationPath` / `Map_AnimationSize`, interpolating between frame 187 and frame 239. This was inspected from the comp text, but it does **not** substitute for visual Resolve validation.

## Current working tree items to preserve

The following are untracked user/local items and must not be staged, deleted, or modified without permission:

```text
app/runtime/logs/
bugs/
features/
references/syria/
references/usa/original video/
text_down.setting
```

## Suggested next work

1. Generate a fresh Syria/Cyprus/Egypt Fusion composition from current `main`.
2. Import it alone into a fresh Resolve Fusion composition.
3. Check each connection before its start frame, during draw, after arrival, and at end of shot.
4. If a static duplicate still appears, save that exact Resolve composition into the package fusion folder and inspect its nodes/text. Do not guess.
5. Validate camera at selected authored frames against the browser preview/reference before changing projection math.
