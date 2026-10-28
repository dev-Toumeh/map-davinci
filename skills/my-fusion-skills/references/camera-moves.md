# Camera moves on the 3D map (the user's style)

Read from the user's own Resolve projects `pakistan` and `الكويت` (2026-10-25), out of
copies of their `Project.db` (comp blob in `Sm2TiCompositionTable.CompositionBA`: 4-byte
size + zlib → a Qt map; its `0_data` holds a second zlib stream = the .comp text).

## The user's style

- **Rig:** one `Camera3D` animated directly, **Use Target on**. Camera X/Y stays almost
  fixed above the map; framing comes from the **Target** (look-at point on the subject)
  and **Translate Z** (distance = zoom). AoV 19.26, aperture 0.263 × 0.468 (portrait).
- **Rhythm:** a key every ~30–110 frames (≈ one per sentence/subject), with deliberate
  **holds** of 25–100 frames (two equal keys) on the frames that matter.
- **Zoom:** wide range, close Z 0.5–1.1, wide 3.5–5.3, alternating in and out. Kuwait
  opens with a fast push 2.3 → 0.66 in 37 frames, then pulls out to 4.9 by frame 350.
- **Roll (Rotate Z):** the signature move, the map turns **±15–40°** between beats
  (Pakistan -39°, Kuwait -31°): keeps it alive and lines the subject up with the tall frame.
- **Tilt (Rotate X/Y):** mostly 0–5°, a few dramatic beats at 16–25°.
- **Easing:** smooth Bezier keys that keep moving through each key (sloped handles);
  flat handles only on holds. The camera rarely stops dead.

## Another approach (YouTube, "Master 3D Camera Movement in DaVinci Resolve (in 5 Minutes)")

Don't animate the camera itself: chain Transform3Ds after a still Camera3D, one per
movement (push-in Z, then pan/rotate), each new one inserted between the camera and the
previous transform; **overlap** the moves (the next starts while the last runs); smooth
keys (S) and shape the handles; a very light Perturb shake on Z rotation.

## Another approach (YouTube, koalanof, "Animate maps like Vox in Davinci Resolve", shared by the user)

- The line writes on (polyline Length 0 → 1); the camera gets a key each time the line's
  head reaches a city, with that point centred; keys far apart (~60 frames).
- Tilt the camera 20–30° (Rotate Y/X) so the map lies back in perspective.
- Never end still: a slow push-in after the journey, then pull back to reveal the route.
- Smooth keys one by one in the Spline editor; too many keys make it jiggle.
- Depth of field: Renderer3D OpenGL + Accumulation Effects (blur ~0.02, quality 4),
  camera focal plane keyed every second to keep the subject sharp. Motion blur optional
  (very heavy).

## Combined plan proposed for gulf_trains (2026-10-25, not yet approved)

The user's rig (Use Target, roll, holds, big zoom range) plus the Vox ideas: tilt 15–25°
on follow shots, the target follows the line's growing end during the write-on and the
train during the ride (keys at stations only), a reveal pull-back after an arrival.

## Built for gulf_trains 0-785 (2026-10-25)

`~/Projects/resolve-bridge/generators/stroke_tracks/mkcamera.py` (beats: frame, target, distance, tilt,
roll) → `camera.lua_table` → `build_camera.lua` keys `Camera3D1` (Use Target on, Rotate X/Y 0,
keys on Translate X/Y/Z, Target X/Y, Rotate Z; Catmull-Rom handles, flat on holds and ends).
Checked on stills:
- Use Target puts the target exactly mid-frame; tilt = camera south of the target
  (P = T + d·(0, -sin θ, cos θ)); **Rotate Z still works with Use Target** and a roll equal
  to a line's heading (degrees CCW from north) makes it run straight up the frame.
- Roll over a line's direction measured across ±0.1 world units; shorter spans swing it.
- From 785 the camera holds the user's framing (measured: target = the map point at the
  frame centre, from the station-dot homography on a frame without trains).
- **Labels upright while rolling:** each label plane's Rotate Z = the camera roll, and its
  Translate = station + its offset turned by the roll (cos/sin expressions), pivot 0
  (`upright_labels.lua`). A Transform3D pivot does not work for this: Fusion scales
  around the pivot too, so a non-zero pivot moves the plane even at roll 0.

## Continuity: what made it feel like cuts (user feedback, 2026-10-25)

Measured against the user's own cameras (screen motion per frame at 2160 wide):

| | speed median | roll °/frame | pan turns > 10°/frame |
| --- | --- | --- | --- |
| user Kuwait | 17 px | 0.12 | 13 frames |
| user Pakistan | 2.9 px | 0.15 | 0 |
| first build | 21 px | 0.29 | 20 (at every section change) |
| after fixes | 17 px | 0.09 | 1 |

Rules that fixed it:
- No holds and no flat handles mid-sequence (the camera parked); ~40–60 frames for big changes.
- **No fast U-turns:** a plain cubic spline through the keys rounds a direction reversal
  into a whip at section changes. Use monotone cubic slopes per value (PCHIP, no
  overshoot): a value then only stops where it turns back, and that key must have zoom or
  roll still moving, so the camera is never still and never whips.
- Roll as one slow drift, not following every line heading (that zig-zagged).
- Check before showing: compute speed, roll speed and sharp pan turns per frame from the keys.

**Pitfall (cost a round of "jumping between the points", 2026-10-25):** `spline:SetKeyFrames()`
from a script takes `LH`/`RH` **relative to their key** (`{ -frames, -value }`, `{ +frames,
+value }`), while a .comp/.setting file stores them **absolute**. Absolute handles passed to
`SetKeyFrames` made every segment bulge and snap onto the next key. After keying, read the
input back every frame (`GetInput(id, f)`) and check the largest one-frame step.

## Big moves and smooth-through keys (user feedback, 2026-10-26)

"The fast movement is big, not just like what we have" / "apply smoothness on all camera frames,
check my version keyframes". Measured:

- **Keys flow through, like Fusion's Smooth (S):** Kuwait distance keys 26 flow-through, 7 holds,
  1 flat at a turn; roll 24/8/0. So the slope at a key = next minus previous (Catmull-Rom), flat only
  on true holds and at the ends. The PCHIP version (flat at every turning point) made moves feel small
  and careful. (`kit/templates/mkcamera.py` and `generators/stroke_tracks/mkcamera.py` `handles()`.)
- **Zoom range:** the user's cameras go from ~0.5-0.66 (city close-up) to ~3.7-5.3 (region); use the
  same: close on subjects, wide on reveals, framing changes completely every 2-4 s.
- **Optical-flow motion of the user's own video** (`exports/pakistan_iran_afghanistan_india_2/videos/
  full-video.mp4`, 2160x3840 @24): median 4.9 px/frame, 90% 24, max 113; still only 1% of frames,
  medium (10-40 px) 28%, fast (>40) 5%. The reference it learned from (videoplayback.mp4): still 21%,
  fast 2%. So: always moving, with real bursts. (Measure with OpenCV Farneback on 270x480 gray frames.)
- Check close shots for labels at the frame edge (Ras Al-Khair needed the target moved toward its label).
