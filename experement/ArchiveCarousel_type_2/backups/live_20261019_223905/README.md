# Live China vs USA — left blurred depth layer

## Authorized legacy cleanup — 2026-10-20

Current result: `clean_template.comp`, saved in native project. Fresh recovery: `before_legacy_cleanup_apply.comp`. Removed obsolete `MultiMerge2`, `MultiMerge3`, `MediaIn1` (original shared film source), `MediaIn2` (disconnected original media input), and unused `Background2`. Main foreground connections to the two obsolete card branches are removed. The old cards contained film only, no main media. Active card film sources are independent. The user's fresh live edits use `Background2_1` for the active right branch; this is preserved along with every other remaining tool/input/key/connection. A live input-consumer scan confirmed old Background2 had no consumers after removing those branches. `verify_legacy_cleanup.lua` passes. Final composite remains visible at the user's frame 122. Removed nodes remain recoverable from the backup; no reopening or full rendering performed.

## Template alignment — 2026-10-20

Saved native project after a positions-only pass. Matching left/right stacks now share regular rows and reflected columns; each row retains its original media, background, film, sharp/blur branches, and animation. Original placeholder nodes were retained but moved below the active stacks, not deleted. Final MultiMerge and MediaOut stay centered below. Backup: `before_template_alignment_apply.comp`; result: `aligned_template.comp`. `verify_alignment.lua` passed a full semantic tool comparison ignoring only ViewInfo/editor metadata. Final output remains visible at frame 84; graph display set to 60%. Reusable lessons are saved in `skills/my-fusion-skills/references/live-template-editing.md` and routed from both workspace and installed skill entrypoints.

## Corrected exact right-hand mirror (supersedes previous right-row attempt)

Final saved result: `exact_right_mirror.comp`; pre-correction recovery: `before_exact_right_mirror.comp`. The previous half-loop right-row phases did not mirror the user's current left design and kept image4 off-screen. Corrected by linking corresponding right path values to **the corresponding current left path minus 0.50**:

- Right_Stack1_Blur_Path = Left_Blur_Depth_Path.Displacement − 0.50
- object2_right = object2_left.Displacement − 0.50
- Right_Stack2_Blur_Path = Left_Stack2_Blur_Path.Displacement − 0.50

This preserves the existing right path geometry and original first-row timing, reverses the side's vertical travel relative to the left, and mirrors the current left second-row visibility. No sequence extension is required; the earlier pending timing choice no longer applies. The left paths, including the user's static blur adjustment, are not rewritten.

Removed only the two added native fitting tools `Right_Stack2_Fit` and `Right_Stack2_CardCanvas` (recoverable from backup/Undo). image4 now connects directly to its native OFX framing tool, whose proportional zoom is 400/2000 = 0.20 to match the left second source's content width, without distorting or cropping image4. All right-side node positions are a reflected copy of corresponding live left positions, with the original right first card as anchor. Main MultiMerge remains below; original positions and left nodes are preserved.

Final post-cleanup visual check: assigning MultiMerge1 to viewer 2 restored its display; the apparent black output was an unassigned viewer, not a failed composite. At frame 5 the sharp first cards enter from opposite vertical directions with their blurred counterparts visibly separated. At frame 36 both first sharp cards are visible. At frames 84 and 226 both second sharp pictures are visible: image3 left, image4 right. These checks occurred after removing the two extra fitting tools. The project was saved again with the viewer at frame 84. Live right displacement values match each corresponding left displacement minus 0.50 at 0/5/10/36/74/84. `verify_right_rows.lua` again passes against `before_right_rows.comp`: original inputs/keyframes retained except intended right film clone and foreground/order extension. No reopen or full-render test.

## Native right-side counterpart / image4 second row

Current saved snapshot: `right_rows_verified.comp`. Fresh original backup: `before_right_rows.comp` plus `main_before_right_rows.setting` (includes every attached modifier). Existing right image retained in `object_1_right`; second row is `Media_file4 → Right_Stack2_Fit → Right_Stack2_CardCanvas → Media_file4_Frame → object_2_right`.

- Media Pool image4 ID: `6c9d219b-1394-4918-a2d5-fb65711b2bc3`; 2000×1503 image fits at 328×246 inside a transparent 328×480 native Crop canvas without cropping the picture.
- Right row 1 uses its existing `Background2` and independent native `Right_Stack1_Vintage8mm`; right row 2 has `Right_Stack2_Background` and `Right_Stack2_Vintage8mm`.
- Native complete-card Blur and Merge placements added per row. `Right_Stack1_Blur_Path = object1_right.Displacement - 0.25`; `Right_Stack2_Blur_Path = object1_right.Displacement + 0.25`; sharp `object2_right = object1_right.Displacement + 0.50`. All share the existing right curve/geometry. Existing right sharp stays on main Layer3; new right composite uses main Layer7. Main canvas remains `Main_Transparent_Background`, never a card stack.
- New nodes arranged beside/below the existing right stack with short adjacent spacing. Existing original positions restored. No custom nodes or controls.
- `verify_right_rows.lua` passes: all original inputs/keyframes unchanged except independent right film source and added foreground/order entry. Actual path offsets numerically verified at 0/5/10/36/74/84. Original sharp left/right outputs visually verified at 36; image4's local card visually verified and left open in viewer.

**Second-row timing is not finished:** existing driver only covers the original first-row movement. With the distinct half-loop phase offset above, image4's sharp placement is off-screen in that interval. Asked user whether image4 should start visible and move out in reverse, or enter after the first image; no answer yet. Do not claim the second sharp card appears in final output until timing is chosen and checked.

Native creation caveat: bmd.readstring of the exported package errored before creating any nodes. Created native tools directly and loaded per-tool files instead. New MediaIn nodes initialized as Timeline inputs; explicit `SetInput('MediaSource','MediaPool')` followed by `SetInput('MediaID', id)`, Layer='', Loop=1, range and ClipTimeStart/End restored the correct sources. Media IDs and source selection checked live. Do not use the earlier unlinked `after_right_rows.comp` as the final result; use `right_rows_verified.comp`.

## Blur dependency repair after main modifier reload

Final current result: `after_blur_restore.comp` (2026-10-20). After the main motion modifier was reloaded, the three path expressions still serialized correctly but returned **nil** live; a static comparison alone missed this. Reapplying identical expression text did not refresh the broken binding. Explicitly clearing each expression with `SetExpression(nil)` and then restoring it repaired the dependencies.

`restore_blur_bindings.lua` verifies actual numeric displacement results at frames 0/5/10/36/74/84, retaining +0.25, −0.50, −0.25 offsets from the original driver. The main and left transparent canvases remain correct. The blurred first card was visibly verified at frame 0. Saved in the native project; no reopen test performed.

## Corrected canvas ownership and main foreground wiring

2026-10-20: live backup `before_background_fix.comp`, verified result `after_background_fix.comp`.

- `Background2` remains the right-card canvas (and its existing placeholder consumers); it no longer feeds a left placement.
- `Left_Blur_Depth_Placement.Background` now comes from `Left_Stack1_Background`.
- New native alpha-zero UHD `Main_Transparent_Background` feeds `MultiMerge1.Background` directly.
- The existing left-only composition chain ending in `Left_Stack2_Main_Placement` now feeds `MultiMerge1.Layer6.Foreground`, not Background. Existing unused layer 6 is ordered first underneath original layers; original relative order is unchanged.
- Left card assembly retains its dedicated backgrounds and film sources. Layout, media, sizes, blur values and animation match the fresh backup. No original tool was deleted in the final result. Native reload renamed the right displacement spline; its keyframes are identical.

`verify_background_fix.lua` passed a semantic comparison of all original tools, permitting only intended canvas/foreground/order changes and the equivalent native spline name. Original modifier references restored. Live output at frame 36 verified both sharp cards and surrounding transparency. Saved in the native project. No reopen or full render test.

Implementation caveats: direct SetInput of a plain LayerOrder table serialized an empty ScriptVal. Full native settings loading with all original attached modifiers restored valid layer order. Loading settings without modifier definitions removes those modifiers; do not use the intermediate incomplete settings files as templates. `finalize_background_fix.lua` and `main_native_layers_complete.setting` represent the completed fix; earlier attempted scripts/settings are diagnostic history, not reusable templates.

## Organized left stacks with independent sources

Fresh live backup: `before_left_layout.comp`; saved result: `after_left_layout.comp`. Ran `organize_left_stacks.lua` inside Resolve. Each left card now has its own independent `Left_Stack1_Background` / `Left_Stack2_Background` and `Left_Stack1_Vintage8mm` / `Left_Stack2_Vintage8mm` nodes. Film nodes reference the same asset but are independent copies, not instances. Existing shared sources remain for other cards.

Layout: shared sources/route artwork at the far left; first left card in the upper rows, second left card in matching columns below, existing right card below those, composite/output on the right. Original node names retained. No original tools deleted.

`verify_left_layout.lua` passed: only four card source connections and flow layout changed. All original rendering values, keyframes, path modifiers, other connections, and right-card settings were preserved. Background/film clone settings match their sources. Live output remained visible at the existing frame 125. Project saved. No close/reopen or full render test.

## Added second left stack (image3)

Updated the live composition using Media Pool `images/one-chiled/image3` (ID `f4d15345-3ab0-4b34-abd3-13c63db99841`). Fresh pre-change snapshots: `before_stack2.comp` and `before_stack2_apply.comp`. Result: `after_stack2.comp`.

- `Media_file2 → Media_file2_Frame → object_2_left` duplicates the first card's editable framing and film overlay, using image3.
- `Left_Stack2_Main_Placement` uses modifier `object2_left`, expression `object1_left.Displacement - 0.50`.
- `Left_Stack2_Blur` blurs the complete second card; `Left_Stack2_Blur_Placement` uses `Left_Stack2_Blur_Path`, expression `object1_left.Displacement - 0.25` (blur 12, size 2.898, blend 0.6).
- Background chain: existing first blur placement → second blur placement → second main placement → existing MultiMerge1.Background. Existing MultiMerge layer order and original sharp inputs are untouched.
- Live evaluations at frames 0/5/10/74/84 verified the requested phase separation. At frame 0 second main/blur are −0.25/0.00. These are spatial offsets, not a newly staggered sequence or new looping keys. The existing curve takes some phases outside the canvas.
- `verify_stack2.lua` confirms original rendering settings, wiring (except the intentional final background extension), paths and timing are unchanged; image3 and expressions match, with no cycles. Original flow positions were restored after native Paste repositioning.
- Visually checked frame 84 (second blurred image3 visible) and frame 36 (both existing sharp cards preserved). Saved the project and left the viewer at frame 36. No full render or close/reopen test.

Recovery for this addition only: reconnect MultiMerge1.Background to Left_Blur_Depth_Placement. New nodes can remain disconnected for recovery.

## Latest adjustment: quarter-path separation

At the user's request, `Left_Blur_Depth_Path.Displacement` now uses `object1_left.Displacement + 0.25`, replacing the initial +0.08 described below. The real card's keyframes remain unchanged. Live evaluations verified frames 0/5/10/36/74/84: real 0.25 → blurred 0.50, real 0.375 → blurred 0.625, real 0.50 → blurred 0.75, real 0.75 → blurred 1.0. Saved in the project; before/after snapshots are `before_quarter_path_offset.comp` and `after_quarter_path_offset.comp`. No other values or connections were changed for this adjustment. The initial verification script below checks the earlier +0.08 snapshot, not this latest snapshot.

Updated the native Resolve project `china sv usa`, Timeline 1, video track 2, clip `china-wrong-1-child-old`, Fusion composition 1.

Before any composition edit, saved the project and exported `china_sv_usa_before_blur_update.drp` plus `Timeline1_Track2_Item14_Comp1_before.comp`. The original experiment `.comp` is unchanged.

## Final changes

- Disconnect `object_1_left.Layer3.Foreground` from the old raw-image blur branch. Keep its original nodes and all layer-order data for recovery.
- Feed the complete sharp left card, including film artwork, into the new native `Left_Blur_Depth` Blur (size 12).
- Place it using `Left_Blur_Depth_Placement` Merge: size 2.898 (90% of the original 3.22), blend 0.6, transparent `Background2` underneath.
- `Left_Blur_Depth_Path` shares `Publish1` and the original left path's center/size. Its displacement expression is `object1_left.Displacement + 0.08`, giving a spatial separation along the same curve, not a time delay.
- Connect that Merge to `MultiMerge1.Background`, placing the blurred copy behind the unchanged sharp cards. Keep `MultiMerge1.Layer4.Foreground` connected to `object_1_left`.

No original media, camera, path geometry, displacement keyframes, clip duration, layer ordering, or right-card controls were changed. Native AddTool auto-insertion was explicitly corrected and the final result re-exported and saved.

## Verification

`verify_preservation.lua` semantically compared every original tool against the before export. Only the two intended original image connections changed; optional Inspector zoom-state serialization (`CtrlWZoom`) is ignored. All original rendering parameters, keyframes, and node positions were preserved. New nodes are placed near the existing stack.

Verified the actual saved output in Resolve at frame 36: both sharp cards remain visible, transparency remains outside them, and the blurred duplicate appears behind/above the left card. The project is left open in Fusion at frame 36 with the output viewer fitted. Save was confirmed; no close/reopen or full render was performed.

Adjust blur in `Left_Blur_Depth`; size/opacity in `Left_Blur_Depth_Placement`; separation in the new path's displacement expression. To restore only the old wiring, reconnect `object_1_left.Layer3.Foreground` to `t1_left_1.Output` and `MultiMerge1.Background` to `Background2.Output`. The full DRP is also available for recovery.
