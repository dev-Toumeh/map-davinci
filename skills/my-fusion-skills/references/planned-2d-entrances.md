# Planned 2D entrances: Flicker and Ink Reveal

Saved on 2026-10-06 at the user's request for a later session, possibly tomorrow. This note does not schedule a task or authorize immediate composition edits. Neither workflow below has a dedicated template implemented or tested in this work. The user-confirmed working curved-arrow template is documented separately in [2d-png-entrances.md](2d-png-entrances.md).

Source tutorial: `/Users/naseemtoumeh/edit-projects/davinvi-resolve/references/scripts/num/How To Edit Invasion Map Animations in DaVinci Resolve.txt`.

## Flicker Entrance

Tutorial section: 12:24–12:40. The tank PNGs flash into view by increasing and decreasing Merge Blend every two frames, then move after becoming fully visible.

Planned reusable behavior: place a PNG over a transparent background in a Merge and animate Blend through brief visibility flashes, ending at 1. Optionally follow the flicker with a position animation. Keep the effect in a 2D branch between the source image and its containing merge; preserve existing placement and unrelated animation.

When implementing, inspect the target PNG and current composition first. Use an editable node group with a replaceable image input and main image output. Consider Start Frame, flash count/spacing, and final visibility controls according to the actual request. Keep movement optional. Preview the output at each flash and after the entrance to confirm it stays visible and is not duplicated by an unmodified source branch.

## Ink Reveal

Tutorial section: 03:11–04:54. A Polygon mask is distorted by Displace driven by Fast Noise, giving the invasion reveal organic, ink-like edges. A linked secondary shape adds depth in the tutorial.

Planned reusable behavior: reveal a PNG through an animated, noise-distorted mask, using Polygon → Displace with Fast Noise as the distortion source. Apply the resulting mask to the image's reveal composite. Animate the mask's shape or placement so coverage grows over time; noise alone does not create the entrance.

When implementing, adapt the mask to the target image and preserve transparent output. Start with one mask branch; a linked second branch for depth is optional. Consider Start Frame, Duration, edge softness, and distortion controls according to the request. Preview the initial hidden state, intermediate coverage, and fully visible end state, checking that the image remains visible after the reveal. Match mask/canvas dimensions and confirm the final mask output is compatible with the composite's EffectMask input.

## Later-session validation

Build separate reusable settings only when the user resumes this work. Check Lua syntax, internal links, and image-output wiring, then import and preview in Resolve. Record the resulting asset filenames and user-confirmed behavior after testing. Until then, describe these as planned techniques rather than available or verified templates.
