# Counter3D: rolling number counter on the 3D map

> **Replaced 2026-10-27** by the simple 10-node counter (`generators/counter/counter.py`): the user
> rejected this one as too heavy and not editable. Kept only for the lessons at the bottom.

A number that counts up on screen, e.g. "2,750 كم" for a rail network or "1.8 مليون" barrels.
Built 2026-10-27 from the user's original in the Resolve project **الكويت** (group
`kuait_oil_state` → `kuwait_oil_state_plan`, an ImagePlane3D on scene input 27). Codex's 2D
`mkcounter.py` was a basic copy of that original: it was flat, screen-fixed, swapped numbers by expression and had one
shadow. The user called it "the basic version". Use Counter3D instead.

- Generator: `~/Projects/resolve-bridge/generators/counter3d/counter3d.py`
  (`counter3d.py <Name> --value 2750 --start 280 --end 316 --out 380 --pos X Y [--unit كم]
  [--decimals 0] [--scale 0.25] [--accent R G B] [--camera Camera3D1] [--dest DIR]`).
- Example: [counter3d_example.setting](../assets/3d/counter3d_example.setting) (gulf_trains,
  `SAU_North_Counter3D`, live in that comp: camera `Camera3D1` → its Camera input, its output →
  `Counters_Over` (Merge over `Vector_Layers`) → `MediaOut1`).

## What it does

- **Rolling digits like an odometer.** Each digit is its own 0–9 column; a higher digit rolls
  only while every digit below it goes 9 → 0. Works for any value up to 9,999,999.99. Thousands
  separators and the leading digits slide in as the number grows, and the number re-centres.
  Only the columns the value needs are generated (2750 → 4): the Decimals control can lower the
  decimals, not raise them past `--decimals`, and a larger value needs a new build.
- **Ease-out count:** fast at first, then the last digits settle (control Settle, a power). It
  lands exactly on Value at Count End.
- **Landing flash:** the colour goes from Text Color to Flash Color as it lands, then back.
- **Floats above the map** (user, 2026-10-27: "make it float above the ground"). A tight soft
  shadow on the text keeps it readable. The real shadow is a second plane lying on the map: the
  counter's silhouette, black and blurred, pushed along Shadow Direction X/Y by the Float
  Height. As the camera moves, parallax opens the gap between counter and shadow. A shadow
  baked into the counter's own image can never look separate.
- **On a 3D plane in the map scene.** It zooms and pans with the map. Follow Heading turns it
  with the camera's heading (computed from Translate → Target when the camera uses a target).
  Face Camera (0–1) stands it up toward the camera, lifted so it doesn't sink into the map.
  Keep Screen Size (0–1) holds its screen size as the camera moves.
- **Optional icon:** the group's `Icon` image input, with its own place, size and fade-in.

## Node layout

All inside one group `<Name>_Counter3D`. The controls are published on the pages Counter, Look and 3D.

- `_Ctrl` (an unconnected Background) holds every control as a user control. It also holds the
  hidden maths: `CNow` (the amount in units of the last shown decimal), per digit `CQ` (whole
  part), `CR` (roll 0–1) and `CV` (visible 0–1), the layout `CW`/`CRight`/`CUnitX`, and
  `CFade`/`CFl`/`CDist`/`CHeading`/`CTilt`. Each Text+ only reads finished numbers.
- Two Text+ per digit (`D<p>` current, `D<p>n` next, one roll below) → MultiMerge `_Digits`
  → `_Windowed` (Merge with the `_Window` RectangleMask) → MultiMerge `_Marks` (separators,
  point, unit: outside the window so a comma's tail isn't cut) → `_Color` (ColorGain) →
  `_Shadow` → `_ShadowFar` → `_Icon` (Merge, Foreground = group input) → `_Gate` (Dissolve) → `_Plane`.
- `_ShadowFill` (BrightnessContrast, gain 0) → `_ShadowBlur` → `_ShadowPlane` (Z 0.0022, flat).
  `_Scene` (Merge3D: shadow plane, counter plane, group input **Camera**) → `_Render`
  (Renderer3D, OpenGL, frame size) → `_Over` (Dissolve gate) = output 1, a transparent
  full-frame image. Merge it over the map render in 2D. Output 2 = the flat counter image.
- Canvas 1200×600 (not full frame: every Text+ renders at this size, and it's a GPU texture).

## Lessons (verified live)

- **Light halo / holes in the flag (2026-10-27).** The map renderer is Z-buffer only
  (TransparencySorting 0). A soft-edged plane in the map scene writes depth even where it's
  nearly transparent, so the flag planes drawn after it fail the depth test there, and the bare
  satellite shows through as a beige outline. Merge3D input order didn't fix it, top scene or
  country stack. (It only seemed fixed once, when the counter was over desert.) Fix: give the
  counter **its own Renderer3D with the map's camera**, and merge that image over the map
  render in 2D. Use this for any soft or blurred element that floats over the map.

- **Playback weight (user, 2026-10-27: "very heavy to play the timeline").** A plane in the scene
  is evaluated on every frame, even at opacity 0, so its whole 2D chain rendered on all 3,479
  frames. `_Gate` is a Dissolve whose Mix is 1 only while the counter fades or shows (else 0):
  Dissolve renders only the side it shows, so outside that range nothing is built. Use this
  gate for any 3D-plane graphic that's only on screen briefly. Also generate only the
  needed digit columns and keep canvases small.

- A Text control read from another tool is already a Text object: `return Ctrl.CUnit`.
  `Text(Ctrl.CUnit)` prints `cdata<struct Text *>`.
- Mask Width/Height/SoftEdge are fractions of the image **width**. On a non-square canvas,
  multiply a height fraction by H/W, or the window covers everything.
- Roll travel must be about one digit height (0.22 of the canvas height on a 2:1 canvas at Size 0.2). With more,
  a digit caught mid-roll is outside the window on both copies and seems missing.
- Hide unused separators by returning `Text("")`, not only by setting their alpha to 0.
- Check expressions offline before pasting: `luajit check_setting.lua <file>` (compiles every
  `:` expression); the generator prints the file path.
