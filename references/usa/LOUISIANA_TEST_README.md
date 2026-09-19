# Louisiana Purchase test shot

Import `USA_Louisiana_Arabic_Test.comp` into a duplicate/new Fusion composition. At 24 fps, view MediaOut1 over frames 240–527 (10–22 seconds). Full global range is 0–1439; only the Louisiana test shot is adapted, not the rest of the script.

New pipeline nodes use the `LP_` prefix. Original country groups and camera curves remain in the file; MediaOut1 displays the new test branch. `LP_HistoricalBoundary` is an editable PolylineMask aligned to the 4K map. `LP_CameraZoom` controls the camera. All titles are editable Damascus TextPlus nodes.

Timing and captions are also recorded in `louisiana_shot.json` for future voiceover adjustments. Original compositions were not changed. The companion MP4 is an offline approximation of the animation, not a render from Resolve. Native Fusion output still needs visual verification in Resolve.

Boundary source: National Atlas territorial-acquisition SVG, published as public domain in the U.S.: https://commons.wikimedia.org/wiki/File:Aquired_Lands_of_the_US.svg . SVG boundary was converted through an estimated Albers registration and fitted to the screenshot's Mercator projection. This is a small-scale educational visualization; alignment is approximate, not survey accuracy. Educational-use-only GIS was used as a registration reference, with no vertices copied into the output geometry. Natural Earth coastline was used for background projection alignment: https://www.naturalearthdata.com/about/terms-of-use/ .
