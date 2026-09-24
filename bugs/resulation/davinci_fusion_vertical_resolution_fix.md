# DaVinci Resolve / Fusion Vertical Resolution Issue

## Goal

Fix a Fusion composition that is being used inside a **vertical 4K timeline**.

The intended project/timeline format is:

- **Resolution:** 2160 × 3840
- **Aspect ratio:** 9:16 vertical
- **Frame rate:** 24 fps

The timeline itself is already configured correctly. The problem is inside the Fusion node pipeline.

---

## Screenshots

Please inspect these screenshots together with this document:

1. `Screenshot 2026-09-20 at 19.55.50.png`
   - Shows the timeline settings.
   - Timeline resolution is correctly set to **2160 × 3840 Ultra HD**.
   - **Use vertical resolution** is enabled.
   - The Edit viewer shows a landscape image fitted inside the vertical frame, leaving large black areas above and below.

2. `Screenshot 2026-09-20 at 19.56.03.png`
   - Shows **Project Settings → Master Settings**.
   - Timeline resolution is also set to **2160 × 3840**.
   - Resolve displays the warning that the current timeline overrides these project-level settings.
   - This confirms that changing Master Settings again will not solve the problem.

3. `Screenshot 2026-09-20 at 19.55.04.png`
   - Shows the Fusion viewer on `MediaOut1`.
   - The important value is:

   ```text
   [Main]: 3840x2160 float32
   ```

   - This proves that the image currently reaching `MediaOut1` is still **3840 × 2160 landscape**, even though the timeline is **2160 × 3840 portrait**.

---

## Problem

The Resolve timeline is correctly configured as **2160 × 3840**, but the Fusion composition is outputting **3840 × 2160**.

So Resolve receives a landscape Fusion result and then fits/scales it into the portrait timeline.

This produces the black areas above and below the image.

The issue is therefore **not the timeline resolution**.

The issue is the **resolution of the image flowing through the Fusion node tree and reaching `MediaOut1`**.

---

## Important Fusion Behavior

Fusion does not have one universal fixed canvas resolution for every node.

Nodes can carry their own image resolution.

For a `Merge` node, the **Background input normally determines the output canvas dimensions**.

Therefore, if the node tree is based on a 3840 × 2160 source image, the Fusion result can remain 3840 × 2160 unless a portrait-sized image explicitly defines the final canvas.

---

## Required Fix

Create an explicit **2160 × 3840 Background node** and use it as the Background input of the final Merge.

Recommended structure:

```text
Map / Current Composition
        |
        v
   Transform1
        |
        v
   [Foreground]
       Merge1 ----------------> MediaOut1
   [Background]
        ^
        |
 Background1
 2160 × 3840
```

### Node configuration

#### `Background1`

Set:

```text
Width:  2160
Height: 3840
```

If necessary, disable any automatic/frame-format resolution option so the node explicitly stays at 2160 × 3840.

The Background can be:

- opaque, if the composition needs a real background, or
- alpha = 0, if transparency is required.

#### `Merge1`

Connect:

```text
Background1 -> Merge1 Background input (yellow)
```

Connect the existing map/composition:

```text
Existing composition -> Transform1 -> Merge1 Foreground input (green)
```

Then:

```text
Merge1 -> MediaOut1
```

---

## Do Not Stretch the Source Map

The existing map/source is 3840 × 2160 landscape.

Do **not** directly resize or distort it into 2160 × 3840.

Instead, keep the source at its natural resolution and use `Transform1` to control:

- zoom
- position
- framing
- animated movement

The portrait `Background1` should define the final 9:16 canvas.

This is especially important because the project will animate geographic areas and needs to preserve source detail during zoom/pan operations.

---

## Expected Result

After applying the fix, select `MediaOut1` in Fusion.

The Fusion viewer should report:

```text
[Main]: 2160x3840
```

instead of:

```text
[Main]: 3840x2160
```

The Edit page should then show the Fusion composition filling the correct **vertical 9:16 frame**, without Resolve treating the whole Fusion result as a landscape canvas.

---

## Verification Checklist

Codex should verify all of the following:

- Timeline resolution remains **2160 × 3840**.
- `Background1` is explicitly **2160 × 3840**.
- `Background1` is connected to the **Background/yellow input** of the final `Merge`.
- The map/composition is connected to the **Foreground/green input**.
- Any map scaling/repositioning happens with a `Transform` before the final `Merge`.
- Final `Merge` connects directly or through intentional downstream nodes to `MediaOut1`.
- `MediaOut1` reports **2160 × 3840**.
- No node after the portrait canvas is reintroducing a **3840 × 2160** output.

---

## Root Cause Summary

Current state:

```text
Timeline:  2160 × 3840
Fusion out: 3840 × 2160
```

Required state:

```text
Timeline:  2160 × 3840
Fusion out: 2160 × 3840
```

The fix is to make the final Fusion canvas deterministic by introducing a **2160 × 3840 Background node as the Background input of the final Merge**.
