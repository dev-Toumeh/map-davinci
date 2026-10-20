# Reusable 2D PNG entrances: curved-arrow reveal

## Current status and source

The user confirmed on 2026-10-06 that the curved reveal **worked very well**. Use the saved [curved_Reveal_arrow.setting](/Users/naseemtoumeh/edit-projects/davinvi-resolve/skills/my-fusion-skills/assets/curved_Reveal_arrow.setting) as the current working reference. Earlier reports of an on/off appearance describe previous trials and no longer establish this template's status. This confirmation is from the user for the original macro. The wrapper conversion preserved the internal nodes and keyframes and passed static link checks; it has not yet had a new Resolve playback test.

Inspect the current saved asset before editing. Preserve its user-saved structure, route, and animation rather than reverting to earlier trial files.

## Saved structure

- `curved_arrow` is now an editable `GroupOperator`, converted from the user-confirmed working macro on 2026-10-09. The original macro is preserved beside it as `assets/curved_Reveal_arrow_macro_backup.setting`. Its main rendered output is `CurveReveal_Output.Output`. Additional `Left`/`Right` outputs are audio data, not image outputs.
- `MediaIn7` references `curved-arrow.png`, a 512×512 PNG in the Resolve Media Pool, with the source path `/Users/naseemtoumeh/edit-projects/general/icons/curved-arrow.png` recorded in its metadata.
- `CurveReveal_Path` is a nonsolid PolylineMask. Its curved stroke uses BorderWidth 0.65 and SoftEdge 0.006, with saved mask dimensions 512×512.
- `CurveReveal_Path.WriteLength` links to `CurveReveal_PathLength`: frame 479 → 0 and frame 503 → 1, with easing handles at (487, 0) and (495, 1). This progressively reveals the stationary image along the saved curve over 24 frame intervals.
- `CurveReveal_Output` is a Merge: `MediaIn7` connects to Foreground, the zero-alpha `CurveReveal_Transparent` Background to Background, and `CurveReveal_Path.Mask` to EffectMask.

## Use and adaptation

Import a fresh copy of the setting into empty Fusion Node Editor space, then open the group to edit `CurveReveal_Path`, its WriteLength spline, or the image source. An instance already in a composition remains the old macro until replaced with this new group. Connect its main image output to the intended 2D Merge/MultiMerge foreground layer, preserving that layer's existing placement, rotation, size, and flip. Keep this entrance in 2D; Page Curl was only an example of the user's broader transition goal.

Preview `CurveReveal_Output` across frames 479–503. Retiming means shifting or scaling the WriteLength spline keys and their handles. Do not use the older trial's 429–453 range for this saved version.

The template contains a MediaIn tied to a specific Resolve Media Pool ID. When using it in another project, ensure the image resolves, or reconnect the desired PNG/Loader to `CurveReveal_Output.Foreground` inside the group or by adapting the source setting when requested. Metadata alone does not make the Media Pool reference portable. Leave the transparent Background and mask connections intact.

For another arrow or image, adapt the PolylineMask route and stroke width to follow that image. Match mask/canvas dimensions as needed; a saved route for this arrow is not a universal reveal path. Check composition frame-format behavior if dimensions differ, rather than changing the confirmed working asset speculatively.

If the image appears instantly, preview the mask and final Merge separately at an intermediate frame (for example 491), and check whether the containing MultiMerge bypasses the reveal or shows a duplicate original image. Changes to a file do not update an already-imported instance automatically.

## Tutorial techniques and historical context

Source: `references/scripts/num/How To Edit Invasion Map Animations in DaVinci Resolve.txt` in the workspace.

- Slide Reveal: move an image behind a fixed mask and ease into position (11:28–12:10; portrait setup from 05:44).
- Flicker Entrance: animate Merge Blend, then optionally position (12:24–12:40).
- Ink Reveal: distort a mask with Displace and Fast Noise (03:11–04:54).
- Outline Draw was also discussed. The curved-arrow reveal adapts animated mask length; it is not explicitly demonstrated as this PNG effect in the transcript.

The earlier `curve-reveal-native.setting`, `curve-reveal-2d.setting`, and `gif-group-curve-reveal-demo.comp` were trial artifacts. Prefer the user-saved working asset above; do not treat old trial failures or speculative causes as current findings.
