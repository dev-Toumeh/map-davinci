# Experiment 02 — Texture Blend

Native Resolve project: **Experiment 02 - Texture Blend**. Timeline: **Texture Blend - Static Map**. Saved and previewed in Resolve 21.

- `fusion/Texture_Blend_Test.comp`: native-saved composition with organized nodes and working MediaOut.
- `fusion/Texture_Blend_Effect.setting`: editable group with image input, relief strength, relief depth, paper strength, warmth, contrast and edge shading.
- `images/fusion_result.png`: actual Fusion render, 3840 × 2160, including attribution.
- `images/esri_hillshade.png`: geographic relief layer aligned to the source extent. Source details and full credit are in `json/hillshade_source.json`.

Base: a copy of the map exported in `../paper_textur`. Its composition and manual controls were not modified. The paper image is a reused blank paper texture; the map and relief were not AI-generated.

Default blends: hillshade Multiply (65%, shadow depth 4); paper Soft Light (28%). Group mode controls use 0 for Multiply and 1 for Soft Light. Custom tools implement these blend formulas so the controls remain editable. No country masks, camera movement or map resampling.

This is a visual test of the second suggested technique, not an exact reproduction of the AI reference and not yet integrated into the app. The relief overlay must be regenerated for each new geographic extent.
