# Text-down templates: 2D and 3D

Use these user-saved templates for text moving along a vertical path through a rectangular mask. Inspect the current files before adapting them. Keep their saved structure and keyframes unless a requested change requires editing them.

## 2D: text_down

Asset: [text_down.setting](/Users/naseemtoumeh/edit-projects/davinvi-resolve/skills/my-fusion-skills/assets/text_down.setting).

- `MacroTool1` is a `GroupOperator`. Its main image output is `DropShadow1.Output`; the additional `Path2.Heading` output is path data, not the rendered text.
- `Text2_1` is a masked TextPlus. The saved text is two lines, `50 %` and `10 مليارات`, in Tahoma Bold, size 0.0611. Change `StyledText` for the requested content; preserve Arabic text where appropriate and check shaping in Resolve.
- `Rectangle1_1` connects to the text's EffectMask. `Path2.Position` drives `Text2_1.CharacterOffset`; it does not animate the TextPlus Center.
- `Path2Displacement` has keys at 410 → 0, 428 → 0.42, 458 → 0.42, 471 → 0.72, 497 → 0.72, and 513 → 1. These include staged holds; preserve their relative timing when retiming.
- `Text2_1` feeds ResolveFX `DropShadow1`. Saved shadow settings include strength 1, angle 80, distance 0.0315, blur approximately 0.55, and black color. The saved effect also contains `blend = 0`; inspect actual rendering before assuming the shadow is visible.

Import the setting, open the group, edit the text/mask/path as needed, and connect the main output to a 2D Merge foreground or a MultiMerge layer. Move the full output together with a Transform or the containing merge layer. Match text placement to the mask when adjusting internal layout. The ResolveFX DropShadow tool must be available in the target installation.

## 3D: 3d_text_down

Asset: [3d_text_down.setting](/Users/naseemtoumeh/edit-projects/davinvi-resolve/skills/my-fusion-skills/assets/3d/3d_text_down.setting).

- `MacroTool1` is a `MacroOperator`, not a group. Keep this saved form. Its main output is `ImagePlane3D2.Output`, a 3D scene object. The separate `Path4.Heading` output is path data.
- `Text3` is masked by `Rectangle1`; its saved text is `60%`, Poppins Bold, size 0.5. `Path4.Position` drives CharacterOffset.
- `Path4Displacement` keys are 1075 → 0, 1103 → approximately 0.37534626, 1118 → the same value, and 1149 → 1. The matching middle values do not prove a perfectly flat hold: their saved spline handles differ. Preserve the actual curve when retiming.
- The secondary branch uses `Instance_Text3` and `Instance_Rectangle1`, then `Instance_Background15 → Blur1`. `MultiMerge4` composites that branch behind `Text3` over a transparent 3840×2160 `Background15`, then feeds the ImagePlane3D material. Preserve instance relationships when editing the main text or mask.
- `Background15` has alpha 0; the instance inherits its source with no explicit alpha value saved. Check the secondary branch's alpha/rendered appearance before describing it as a confirmed working shadow.
- The plane's saved translation is X −0.128, Y 0.152, Z 0.02; Z rotation links to a spline with a 0 key at 1104. These are saved example placement/timing, not universal defaults.

Connect the main output directly to a Merge3D scene input, then preview through the existing Renderer3D. It is already on an ImagePlane3D; do not add a second image plane or connect its scene output to a 2D Merge. No top-level text controls are published in the saved macro; edit the internal `Text3` via the existing macro-edit workflow or adapt the source setting when requested.

## Verification

Both files were inspected directly on 2026-10-06. This documentation update did not change them or perform a Resolve playback test. Check the main output, mask, Arabic shaping where used, secondary/shadow branch, and loop-free animation at the intended frames before treating the rendered behavior as verified. Shift the relevant spline keys deliberately when reusing a template at another time.
