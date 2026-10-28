# Gulf trains video (Resolve project `gulf_trains`)

A short Arabic explainer: what the Gulf states' railway networks look like.
Started October 2026; this page records its script, how the main composition
is built and how far it is (state as of 2026-10-24, read live through the
bridge, see [lua-mailbox-bridge.md](lua-mailbox-bridge.md)). Inspect the live
composition before changing it; the user keeps building it by hand.

## Project

- Resolve project **gulf_trains** (free App Store Resolve 21.1): Timeline 1,
  1920×1080, 24 fps, starts 01:00:00:00 (frame 86400), ends frame 90193
  (~2 min 38 s).
- Video 1: `main` (Fusion composition clip, frames 86400–89523, 3123 frames)
  and `Fusion Composition 1` (frames 90073–90193, 5 s). There is a ~23 s gap
  between them (89523–90073); ask whether it is intended.
- Audio 1: 9 pieces of ElevenLabs voice-over (the "Abdullah – Professional,
  and Energetic" voice and three other takes, 2026-10-20), back to back from
  frame 86400 to 89577.
- Media pool: `fusion` (the comps, sky photo, a diesel train FBX,
  `colormap.png`), `records` (the 4 voice-over files), `3d` (Kenney
  `train-electric-bullet-a/b/c.fbx` + `colormap.png`), `flags` (6 Gulf flags,
  `<ISO3>_cover_*.png`), `maps` (`satellite_wide.png`, `satellite_detail.png`).
  Source folder for the shorts: `~/edit-projects/project2/shorts/gulf_trains_lines`;
  train models: `~/edit-projects/general/3d-objects/kenney_train-kit*`.

## The main composition (`main`, "Composition 1", 282 tools)

- **Map**: `Map_Wide` and `Map_Detail` (MediaIn) on `Map_3D_Satellite` and
  `Map_3D_Detail` (ImagePlane3D) in `Map_3D_Scene` (Merge3D), seen by
  `Map_3D_Camera` (keyframed roughly frames 0–470), rendered by
  `Map_3D_Renderer` into `Vector_Layers` (MultiMerge) → `MediaOut1`.
- **Countries** (ISO3 prefixes `SAU`, `ARE`, `QAT`, `KWT`, `OMN`, `BHR`), all
  built the same way:
  - shape: `<CC>_Entire_Ring_NN_Fill` / `_Border` (sPolygon) → `<CC>_Entire_Shapes`
    (sMerge) → `<CC>_Local` (sTransform) → `<CC>_Render` (sRender). Countries
    with several pieces keep the rings in `<CC>_Entire_Optional_Group`
    (Saudi Arabia has 11); Qatar has one ring, so it has no such group;
  - flag: `<CC>_Flag_Loader` (MediaIn) masked by the shape
    (`<CC>_Flag_Masked_On_Working_Canvas`) with its border render on top
    (`<CC>_Flag_With_Border`); `<CC>_Flag_Color_Flag` and `<CC>_Enabled`
    (Switch) choose flag, plain shape or nothing;
  - border highlight: `<CC>_Border_Highlight_Group` (a PolylineMask
    `<CC>_Path` on a Background, inner and outer Glow);
  - all merged in `<CC>_Local_Elements_MultiMerge` onto `<CC>_Plane`
    (ImagePlane3D) in the 3D scene.
- **North Train Network (started)**:
  - route: `saudi_north_railway_track_hd.png` (MediaIn2, cropped HD from OSM, k ≈ 4.4,
    2026-10-25; was the whole-map `saudi_north_railway_track.png`) on `ImagePlane3D1`
    (Scale 0.4503, Translate −0.2573/0.0353/0.00102, on the map's scale 2; the old plane's 2.006 was 0.3% off), in `Merge3D1` with `SAU_Plane`.
    North and East don't touch in Riyadh (North ends at Riyadh North station, East starts
    at the dry port ~20 km south; OSM has no link between them);
  - train: group `train_saudi_1`: the three Kenney bullet-train cars
    (`FBXMesh3D1–3`, textured by `MediaIn3` = `colormap.png`, two placed by
    `Transform3D2/3`), merged in `Merge3D2`; moved by `Transform3D1`
    (keyframed from frame 363 to about 480).
- **One Merge3D per line** (2026-10-24): `Merge3D1` = `SAU_Plane` +
  `SAU_North_Merge3D` (`ImagePlane3D1` route + `Transform3D1` train) +
  `SAU_East_Merge3D`. Each new line (Haramain next) gets its own
  `SAU_<Line>_Merge3D` holding its track plane and its train.
- **East Train Network** (2026-10-24): `saudi_east_railway_track_hd.png` (cropped HD, see below)
  (made by Codex through `~/edit-projects/project2/shorts/gulf_trains_lines/kit/`: real OSM route, the North PNG's
  rails-and-sleepers texture) in MediaIn `SAU_East_Track_Image` →
  `SAU_East_Track_Plane` → `SAU_East_Merge3D`. Its train is to do. Checked on
  a rendered still of frame 190: it starts at the Riyadh dry port (not joined to North, see above) and reaches Dammam
  on the coast.
- **Haramain high-speed** (2026-10-25): `saudi_haramain_railway_track_hd.png` (OSM main line
  Makkah – Jeddah – KAEC – Madinah, 448 km, airport branch left out; k ≈ 9.8) in MediaIn
  `SAU_Haramain_Track_Image` → `SAU_Haramain_Track_Plane` (Scale 0.2050, Translate
  −0.3734/−0.1521/0.00104, object/material ID 12) → `SAU_Haramain_Merge3D` → `Merge3D1`
  SceneInput4. Built by `~/edit-projects/project2/shorts/gulf_trains_lines/kit/haramain/` (route:
  `~/edit-projects/project2/shorts/gulf_trains_lines/kit/haramain/select_haramain.py`). Visible at frame 0 (whole map); no camera
  move or train yet. Copying a tool's settings by script (`LoadSettings(SaveSettings())`)
  fails here, so the nodes set East's values explicitly.
- **Saudi Landbridge** (planned, 2026-10-25): no geometry in OSM or published, so a schematic
  dashed great circle Riyadh → Jeddah (846 km, 26 dashes; `~/edit-projects/project2/shorts/gulf_trains_lines/kit/landbridge/make_landbridge.py`),
  `saudi_landbridge_track_hd.png` (3840×1875, k ≈ 8.3) → `SAU_Landbridge_Track_Color` purple
  (0.8, 0.4, 1.15) → `SAU_Landbridge_Track_Plane` (Z 0.00105, ID 13) → `SAU_Landbridge_Merge3D`
  → `Merge3D1` SceneInput5. New lines: `(~/edit-projects/davinvi-resolve/naseem-local/archive-claude-codex-bridge-20261026.tar.gz; archived) mkline.py`.
- **Stroked tracks (current, 2026-10-25)**: all four Saudi lines are native shapes now
  (method in [map-route-overlay.md](map-route-overlay.md)): rows `SAU_<Line>_Sleepers_N`,
  `_Rail_Edge_N`, `_Rail_Centre_N` (flow y −7.5 North, −6 East, −4.5 Haramain, −3 Landbridge)
  → `SAU_Tracks_Shapes` (sMerge) → `SAU_Tracks_Render` → `SAU_Tracks_Plane` (Z 0.00106, ID 14)
  → `Merge3D1` SceneInput6. **Colour of a line: `SAU_<Line>_Rail_Edge_1` Red/Green/Blue**:
  North (1, 0.22, 0.2), East (0.25, 0.42, 0.35), Haramain (0.2, 0.6, 1), Landbridge white.
  W = 32 px for `Camera3D1` (fixed: Z 2.53, rot −2.6/7.8; the renderer uses it, not
  `Map_3D_Camera`). The old PNG planes (`ImagePlane3D1`, `SAU_<Line>_Track_Plane`) are kept
  but Unseen by Cameras; their MediaIns and ColorGains no longer show.
  Built by `~/Projects/resolve-bridge/generators/stroke_tracks/` (`mktracks.py`, `build.lua`).
- **Line colours** (2026-10-25, old PNG tracks): a ColorGain between each track MediaIn and its plane:
  `SAU_North_Track_Color` red (1, 0.22, 0.2), `SAU_East_Track_Color` green (0.25, 0.95, 0.35),
  `SAU_Haramain_Track_Color` blue (0.2, 0.6, 1.15). Change Gain R/G/B in the Inspector.
- **How to make a line image that lands exactly** (general rules in [map-route-overlay.md](map-route-overlay.md); same as North): a
  3840×2160 transparent PNG in the frame of `satellite_detail.png`
  (`px = (merc_x - 2125832.66) / 1886.579`, `py = (5205055.88 - merc_y) / 1886.579`,
  EPSG:3857 metres, from the map package's `metadata.json` `detail.pixel_transform`),
  on an ImagePlane3D like `Map_3D_Detail`: Scale 2, Translate 0, Z just above
  the countries (0.00103). Renderer: `(~/edit-projects/davinvi-resolve/naseem-local/archive-claude-codex-bridge-20261026.tar.gz; archived) make_east_track.py --frame detail`.
  Don't use images above 3840×2160: free Resolve's 4K limit placed a
  5012×4128 version at the wrong size.
  **Sharper: crop to the line** (`--frame crop`). A whole-map PNG gives a line
  only ~200 px, which the camera enlarges into blur. Instead cover only the
  line's bbox (x0..x1, y0..y1 in detail px, 16:9) at 3840×2160 and place the
  plane at `Scale = 2*(x1-x0)/3840`, `Translate.X = ((x0+x1)/2/3840 - 0.5)*2`,
  `Translate.Y = (0.5 - (y0+y1)/2/2160)*1.125` (`(archived: ~/edit-projects/davinvi-resolve/naseem-local/archive-claude-codex-bridge-20261026.tar.gz) mkswap3.py`).
  The East line went from ~220 px to 3840 px this way (k ≈ 12).
- **Seeing a frame**: `fusion_run` with `(archived: ~/edit-projects/davinvi-resolve/naseem-local/archive-claude-codex-bridge-20261026.tar.gz) still.lua`
  (switches to the Color page, `SetCurrentTimecode`, `ExportCurrentFrameAsStill`
  into the mailbox, back to the page it was on; timecode functions do nothing
  on the Fusion page). Fusion's `comp:Render` returns false in Resolve.

## Timing (frames, from the user, 2026-10-25)

| What | Frame |
| --- | --- |
| North line writes on | 200 → 340 |
| North train appears on Riyadh | ~400 |
| Train at Al-Qassim / Ha'il / Al-Jouf / Al-Qurayyat | 430 / 470 / 490 / 540 |
| Ras Al-Khair (freight, spoken) | 706 |
| East line appears | 785 |
| Dammam / Al-Ahsa (spoken) | 948 / 973 |
| Haramain line appears | 1179 (given as "179") |
| Makkah / Madinah / Jeddah (spoken) | 1187 ("187") / 1228 / 1258 |
| Landbridge line appears | 1458 |

Trains (`~/Projects/resolve-bridge/generators/stroke_tracks/mktrain.py <kind>`, one group each, on `Merge3D1`):

| Group | Cars | Route | In / leaves / arrives / out |
| --- | --- | --- | --- |
| `SAU_North_Train` | electric double a-c | Riyadh → Al-Qurayyat (stations at 430/470/490) | 392 / 400 / 540 / 785 |
| `SAU_North_Freight` | diesel + 2 mineral hoppers | Al-Jalamid → Ras Al-Khair | 582 / 590 / 706 / 785 |
| `SAU_East_Train` | diesel-box a-c | Riyadh dry port → Al-Ahsa (via Al-Kharj) → Dammam | 788 / 796 / 973 / 1179 |
| `SAU_Haramain_Train` | electric bullet a-c | Makkah → Jeddah → Madinah | 1181 / 1189 / 1258 / 1458 |

East and Haramain follow the track (user's choice): stations in route order, the last
reached at its spoken frame; a city label may pop before the train gets there.
The user's `saudi_north_train` group is unused (a script can't add nodes into it).

City groups (`SAU_City_<Name>`) pop 6 frames before these so the overshoot lands on the
frame (keys in `SAU_City_<Name>_PopSize` or `_Dot_PopSize`: start, +6 at 1.15, +10 at 1).

## Before rendering (user, 2026-10-25)

- Add depth of field last, after everything else is final: Renderer3D OpenGL with
  Accumulation Effects (see camera-moves.md), focus tied to the camera target, as a
  switch the user can turn off. Expect renders about 4× slower.

## Script (Arabic voice-over) and progress

| # | Section | Visual so far |
| --- | --- | --- |
| 1 | Intro: what do the Gulf railway networks look like? | map, camera move |
| 2 | Saudi Arabia, three networks. **North Train**: ~2,750 km; passenger trains from Riyadh to Al-Qassim, Hail, Al-Jawf, up to Al-Qurayyat near the Jordanian border; freight from the northern mining areas to Ras Al-Khair on the Gulf | **in progress**: route image + moving train |
| 3 | **East Train**: ~1,775 km, Riyadh–Dammam via Al-Ahsa, passengers and freight | track PNG on the map; train and timing to do |
| 4 | **Haramain high-speed**: electric, passengers, Makkah–Madinah via Jeddah, 300 km/h | track PNG on the map; camera, train and timing to do |
| 4b | **Saudi Landbridge** (added by the user 2026-10-25): planned line joining east and west, Riyadh to Jeddah, built in stages before 2034 | – (planned: no OSM track; draw dashed or distinct) |
| 5 | **UAE, Etihad Rail**: 900 km, Al-Ghuwaifat (Saudi border) to Fujairah via Abu Dhabi and Dubai | – |
| 6 | **Oman, Hafeet Rail**: Sohar–UAE network via Al-Buraimi and Al-Ain, 238 km, 40% built (April 2026) | – |
| 7 | **Kuwait**: national rail still in design; the Gulf link ~111 km, Kuwait City to the Saudi border | – |
| 8 | **Qatar**: no railway yet; a line planned from Doha to the Saudi border via Salwa | – |
| 9 | **Bahrain**: planned link to Dammam over the new King Hamad Causeway, two rail tracks beside the road | – |
| 10 | **Gulf Railway**: 2,117 km joining all six states, target 2030 | – |

The full Arabic text:

```
كيف تبدو شبكة القطارات في الخليج؟

لنبدأ بالمملكة العربية السعودية،

تضم المملكة ثلاث شبكات رئيسية. الأولى هي شبكة قطار الشمال، التي تمتد على مسافة تقارب 2,750 كيلومترًا

تنطلق قطارات الركاب من العاصمة الرياض باتجاه القصيم وحائل والجوف، وصولًا إلى القريات قرب الحدود الأردنية، بينما تمتد خطوط الشحن من مناطق التعدين شمال المملكة إلى ميناء رأس الخير على الخليج العربي.

أما الشبكة الثانية فهي قطار الشرق، الذي يبلغ طول شبكته نحو 1,775 كيلومترًا، ويربط الرياض بالدمام مرورًا بالأحساء، ويُستخدم لنقل الركاب والبضائع.

وهناك أيضًا قطار الحرمين السريع، وهو قطار كهربائي مخصص لنقل الركاب، يربط مكة المكرمة بالمدينة المنورة مرورًا بجدة، وتصل سرعته إلى 300 كيلومتر في الساعة.

ولربط شرق المملكة بغربها، تخطط السعودية لإنشاء مشروع الجسر البري، الذي سيصل الرياض بجدة، ومن المتوقع اكتماله على مراحل قبل عام 2034

أما في الإمارات العربية المتحدة، فقد أنجزت شبكة قطارات الاتحاد، التي تمتد على مسافة 900 كيلومتر، من الغويفات على الحدود السعودية غربًا إلى الفجيرة على الساحل الشرقي، مرورًا بأبوظبي ودبي.

وفي سلطنة عُمان، يجري العمل على مشروع حفيت للقطارات، الذي سيربط مدينة صحار بشبكة القطارات الإماراتية عبر البريمي والعين، بطول 238 كيلومترًا، وقد بلغت نسبة إنجازه 40% في أبريل 2026.

أما الكويت، فلا تزال في مرحلة تصميم شبكتها الوطنية للسكك الحديدية، ويبلغ طول الجزء المخصص للربط الخليجي نحو 111 كيلومترًا، ليربط مدينة الكويت بالحدود السعودية.

قطر لا تمتلك حتى الآن خطًا حديديًا لاكن من المخطط إنشاء سكة لربط الدوحة بالحدود السعودية عبر منفذ سلوى.

أما البحرين، فمن المخطط ربطها بمدينة الدمام السعودية عبر جسر الملك حمد الجديد، الذي سيضم خطين للسكك الحديدية إلى جانب الطريق البري.

وفي النهاية، من المخطط ربط هذه الشبكات جميعها ضمن مشروع سكة حديد الخليج، الذي سيمتد لمسافة 2,117 كيلومترًا، ويصل الدول الخليجية الست بعضها ببعض، مع استهداف اكتمال تشغيله بحلول عام 2030.
```

Typo in the text as received: "لاكن" (Qatar paragraph) is usually written "لكن".

Saved workflows likely to help: [arabic-city-label.md](arabic-city-label.md)
(city names), [moving-icon-with-path.md](moving-icon-with-path.md) and
[doted-moving-line.md](doted-moving-line.md) (routes), [text-down.md](text-down.md)
(figures such as "2,750 km").
