# 3D masked icon with shadow

Current template: [3d_masked_icon_with_shadow.setting](/Users/naseemtoumeh/edit-projects/davinvi-resolve/skills/my-fusion-skills/assets/3d/3d_masked_icon_with_shadow.setting).

This user-updated asset supersedes the earlier `app/fusion/templates/nodes/map_3d_icon_shadow_object.setting` for this workflow. Inspect the current asset before editing; do not replace it with the older file or move either template as part of a documentation update.

## Structure inspected on 2026-10-06

- The saved tool is `d_masked_icon_with_shadow`, a `MacroOperator`. The filename starts with `3d`, while the internal tool name starts with `d`; this is the actual saved naming. Preserve the macro rather than converting it to a GroupOperator.
- Its only published output is `Map_Icon_3D_Parent_1.Output`, a Merge3D scene. No top-level image input or Inspector controls are published in this saved macro.
- The icon is built from PolylineMask chains and their instances applied to two Background nodes, combined by `MultiMerge2` over transparent `Background6`. The saved canvas is 800×800. `MultiMerge2` feeds `Map_Icon_Plane_1.MaterialInput`.
- The same `MultiMerge2` output masks `Map_Icon_Shadow_Color_1`, whose saved alpha is 0.28. It feeds Gaussian `Map_Icon_Shadow_Blur_1` with X/Y blur size 12, then `Map_Icon_Shadow_Plane_1.MaterialInput`.
- The shadow plane has local X/Y offsets approximately +0.142857/−0.142857 and Z −0.000268119. These values are local to the saved object, not general world-space placement defaults.
- `Map_Icon_3D_Parent_1` combines the shadow plane on SceneInput1 and icon plane on SceneInput2. Its translation, rotation, and pivot inputs link to saved BezierSplines. Scale X is 0.1; Y/Z are approximately 0.03729685.

## Use and adaptation

For two of these icons merged and animated as a pair, see the [3D icon pair](moving-icons.md#3d-icon-pair).


Drag the setting into empty Fusion Node Editor space. Connect its output to a scene input on the target Merge3D (for example the map's scene merge), then use that scene's existing Renderer3D to view the rendered result. It is a 3D scene output, not a 2D foreground image for Merge/MultiMerge.

The current icon is procedural mask artwork, not a Loader-based PNG input. For a different shape, inspect the base `path12` and `path1_*` masks and their `Instance_path*` relationships; preserve shared shape relationships so the shadow still follows the icon. If adapting it for an image, explicitly redesign the icon/material and shadow mask connections rather than assuming a published image input exists.

Move/rotate the icon and shadow together using `Map_Icon_3D_Parent_1`. Adjust shadow alpha, blur, and local plane offsets on their corresponding internal nodes. Preserve the user's current mask shapes and animation unless the requested change requires altering them.

Saved animation is anchored to actual frame numbers: translation has keys at 148 and 156, with Y moving from −0.098 to −0.076. Z rotation is 0 at 148, 156, and 197; 10.4 at 214; −13.1 at 229; and 0 at 241. Y pivot is 0.087. These are this example's saved values, not automatic timing for a new composition. Retiming requires moving the relevant spline keys together; changing a static value does not remove its animation link.

## Validation status

The current file was inspected directly for node structure, output, connections, and saved animation. Live Resolve import and rendered appearance have not been verified in this documentation update. Do not claim a new playback test occurred.
