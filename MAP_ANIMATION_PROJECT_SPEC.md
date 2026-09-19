# AI-Assisted Map Animation Pipeline — Project Notes

## Status

Brainstorming / architecture phase.

This document consolidates the current project idea, the existing DaVinci Resolve/Fusion work, and the QGIS-based map-animation workflow discussed in the session. It is intended to be handed to Codex/OpenCode/Astra as project context.

---

## 1. Project Goal

Build a repeatable system that can generate or prepare map-animation scenes for **DaVinci Resolve Fusion**.

The initial goal is **not** to build a general-purpose map editor. The goal is to reduce the manual work required to produce high-quality animated map videos, especially **YouTube Shorts / TikTok-style vertical videos**.

The system should eventually be able to take a high-level scene description such as:

- target country or countries
- geographic area
- aspect ratio
- map style
- colors/highlights
- camera start/end
- labels
- timing
- optional media

…and produce the assets and Fusion structure needed for the scene.

The first user of the system is the project author. If it becomes reliable and useful, it may later become an open-source project or reusable plugin/application.

---

## 2. Core Design Principle

Do **not** ask the LLM to improvise every technical detail from scratch.

The project should separate:

1. **Planning / interpretation**
   - LLM decides what scene should be built.
   - Example model split currently being tested:
     - Astra for planning/reasoning
     - a cheaper/faster model for implementation/building

2. **Deterministic asset generation**
   - map extent
   - country geometry
   - synchronized exports
   - resolution
   - projection
   - file naming
   - crop alignment

3. **Fusion composition generation**
   - predefined/proven node patterns
   - controlled parameters
   - camera animation
   - colors
   - labels
   - timing

An MCP layer may be useful later, especially to reduce repeated LLM context/token usage and to expose deterministic tools to the model, but MCP is **not** the first thing to build.

---

## 3. Existing Manual Reference Workflow

The current reference workflow comes from a QGIS → DaVinci Resolve Fusion tutorial.

### QGIS side

The tutorial workflow is approximately:

1. Create a new QGIS project.
2. Use the coordinate/location search and load a **World** map/vector layer.
3. Install/use **QuickMapServices**.
4. Add a basemap such as **Google Satellite**.
5. Use the World/vector layer to select a country with **Select Feature**.
6. Export selected country features.
7. Repeat for any additional countries.
8. Position the map at the desired geographic framing.
9. Open **Create Print Layout**.
10. Set the layout dimensions.
11. Add the map to the layout.
12. Export synchronized map assets.
13. Produce:
    - country layer/mask
    - satellite/background map
    - optionally a more zoomed-out version of the map

The important concept is that all exported assets must correspond to the **same geographic framing** unless a deliberately different zoom level is being created.

---

## 4. QuickMapServices — Current Idea

QuickMapServices is important as a reference/source for map services.

In the current QGIS workflow it is used to access basemaps such as Google Satellite.

For the future application, the goal is **not necessarily to embed QGIS itself**.

Instead, we should investigate whether we can reproduce only the functions we need:

- discover/use map-service endpoints
- request/render map tiles
- choose a geographic extent
- render a fixed-size map
- generate synchronized map assets

QGIS is currently the **reference UI/workflow**, not necessarily a required dependency of the final product.

This is still an architectural question and should be verified before implementation.

---

## 5. Country Geometry / Masks

The World/vector layer is useful because it gives us real country boundaries.

Required capability:

1. Select a country or region.
2. Extract its geometry.
3. Export it as an independent asset.
4. Preferably support **SVG/vector output** when practical.
5. Import the resulting vector geometry into Fusion as masks/polygons where possible.

The project must eventually manage cases where an SVG contains multiple paths/nodes.

That is a later implementation detail, but vector country geometry is a key part of the project.

---

## 6. Fixed Geographic Extent and Pixel-Perfect Alignment

This is one of the most important requirements.

All related assets for a shot must be generated from the same:

- geographic extent
- projection
- aspect ratio
- canvas size
- crop
- center
- orientation

Examples of synchronized assets:

- satellite/background image
- selected-country mask
- country border layer
- Blue Marble replacement crop
- overlays
- labels or geographic reference layers

Even a small mismatch can break the Fusion composition.

The system should therefore treat the shot extent as a first-class object/parameter rather than allowing every export to choose its own framing.

---

## 7. Resolution Strategy

### Final target

The production pipeline should be **4K from the beginning**.

For standard landscape UHD:

- **3840 × 2160**
- aspect ratio: **16:9**

For vertical Shorts/TikTok:

- **2160 × 3840**
- aspect ratio: **9:16**

The aspect ratio should be a project/scene input, not hard-coded.

### Important rule

The map layout/export should already use the final output dimensions.

Do not create HD assets and upscale them later.

The Fusion composition/output should also use the corresponding 4K canvas.

Primary background/media assets should be generated at matching resolution whenever practical.

---

## 8. Editing Map vs. High-Resolution Production Map

The normal map source used during editing may not have enough detail for aggressive zooming.

A separate high-resolution source can therefore be used for final quality.

### Blue Marble idea

The project currently uses/considers **NASA Blue Marble** imagery because the full image is extremely large and high-resolution.

The plan is **not** to load the entire Blue Marble image directly into the editing workflow.

Instead:

1. Define the shot extent.
2. Generate the normal editing/background asset.
3. Extract only the matching section from Blue Marble.
4. Make that crop correspond exactly to the same geographic extent.
5. Use a manageable crop rather than the entire huge image.
6. Use the normal/light asset for editing if needed.
7. Replace or upgrade it with the higher-quality Blue Marble crop for final rendering.

The replacement must preserve exact alignment.

This is essentially a **proxy → high-resolution replacement** workflow.

---

## 9. Zoom Strategy

The tutorial creates two satellite/background versions:

- normal framing
- more zoomed-out framing

The zoomed-out map is created by changing the map scale before export.

In Fusion, this allows the 3D camera to begin farther away while still having image coverage outside the tighter/high-quality map area.

This idea should be preserved.

However, the final automation should define zoom/framing mathematically rather than rely on manual scale edits.

Detailed zoom limits can be decided later.

---

## 10. Fusion Reference Structure

The shared tutorial builds a scene approximately like this:

### 2D preparation

- country image/mask
- Background node for country fill/highlight
- DeltaKeyer or masking approach for outlines
- outline dilation
- optional Glow
- MultiMerge combining:
  - satellite/background
  - country fills
  - borders/outlines

### 3D scene

- MultiMerge output → ImagePlane3D
- additional zoomed-out background → ImagePlane3D
- Merge3D
- Camera3D
- Renderer3D
- MediaOut

The zoomed-out map plane is placed slightly behind the main map plane to avoid visible intersection/z-fighting.

The camera is then animated between:

- zoomed-out/start position
- closer/end position

Animation curves are eased in the Spline editor.

This tutorial is a **reference pattern**, not yet the final node architecture.

The project should eventually use proven reusable Fusion node templates instead of letting the LLM invent arbitrary graphs every time.

---

## 11. Fusion Automation Direction

Long-term idea:

The model receives a scene description and produces a structured scene specification.

Example conceptual input:

```yaml
scene:
  aspect_ratio: "9:16"
  resolution: [2160, 3840]
  target:
    countries: ["United Kingdom", "France"]
  camera:
    start: "wide"
    end: "fit-target-region"
  style:
    uk_fill: "white"
    france_fill: "red"
    border: "yellow"
    glow: true
  timing:
    duration_seconds: 7
```

The exact schema is not decided yet.

A deterministic generator should then turn that specification into:

- map assets
- metadata
- Fusion node structure
- parameters/keyframes

This is preferable to asking a model to directly edit hundreds of Fusion nodes without constraints.

---

## 12. Existing Fusion Work

The project already contains working/reference Fusion compositions.

Important lessons from previous work:

- existing projects should be treated as style and node-construction references
- do not overwrite originals
- a manually connected zoom preview previously worked
- previous automated experiments were not sufficiently visually verified
- an earlier Louisiana prototype was rejected and should not be treated as a successful template
- native Resolve/Fusion render verification is important

The new approach should learn from the existing successful projects rather than redesigning their visual language from scratch.

---

## 13. Custom Hand-Made Map Style

The author also has a more specialized manually designed map style/workflow.

That workflow is attractive visually but is highly specific and manually built.

Decision for now:

- do **not** start with it
- treat it as a possible future add-on
- first solve the standard/repeatable map workflow
- revisit the custom map style after the core pipeline works

---

## 14. Asset Package Concept

Each generated map shot should eventually have a self-contained asset package.

Conceptual example:

```text
shot_001/
├── shot.json
├── background_editing.png
├── background_highres.png
├── background_zoomed_out.png
├── country_uk.svg
├── country_france.svg
├── borders.svg
├── metadata.json
└── fusion/
    └── scene.comp
```

`metadata.json` may later contain:

- extent / bounding box
- projection / CRS
- resolution
- aspect ratio
- source map/service
- scale
- center coordinates
- selected features
- generated file hashes
- timestamps

The purpose is reproducibility and exact alignment.

---

## 15. Initial Product Scope

The first practical version should focus on the author's own workflow.

Primary initial target:

- short-form map videos
- mostly **9:16**
- 4K vertical output
- one or a few countries/regions
- automatic asset preparation
- reusable Fusion composition generation
- easy manual adjustment afterward

A polished public library/plugin can come later.

The first success criterion is:

> Can the system reduce a map-animation scene that currently takes substantial manual work into a predictable, repeatable workflow while preserving quality?

---

## 16. Suggested First Prototype

Do **not** begin with a complete historical video.

Start with one small scene.

### Input

- aspect ratio: `9:16`
- output: `2160 × 3840`
- one or two countries
- one defined map extent
- one basemap style

### Generate

1. map/background
2. country geometry/mask
3. optional border asset
4. zoomed-out background
5. matching Blue Marble/high-resolution crop
6. metadata describing the exact geographic extent

### Verify

Before automating Fusion:

- verify that all assets align pixel-perfectly
- verify that high-res replacement preserves the exact framing
- verify that the assets can be imported into an existing Fusion composition successfully

Only after that should we automate the Fusion node tree.

---

## 17. Open Questions

These should be investigated rather than assumed:

1. Can QuickMapServices data/service definitions be consumed cleanly outside QGIS?
2. Which basemap providers are technically and legally suitable for automated rendering/distribution?
3. What vector dataset should be the canonical source for country boundaries?
4. What projection should be the default for the standard workflow?
5. What is the best method for exporting/importing country geometry as Fusion polygons?
6. Should SVG remain an intermediate format, or should the generator produce Fusion mask data directly?
7. How should historical borders be sourced and licensed?
8. What is the best way to generate the exact Blue Marble crop corresponding to a requested map extent?
9. How should the system calculate normal vs. zoomed-out map scales?
10. Which Fusion node patterns should be standardized as reusable templates?
11. At what stage does MCP become useful enough to justify building it?
12. Which parts belong in a CLI, local application, plugin, or MCP server?

---

## 18. Development Philosophy

For now:

- brainstorm first
- preserve working references
- solve one layer at a time
- keep geographic operations deterministic
- keep LLM decisions high-level
- use cheaper models for repetitive implementation where possible
- visually verify actual Resolve output
- avoid large redesigns before the basic pipeline works
- optimize token usage by giving models concise project/spec files rather than entire conversation histories

---

## 19. High-Level Pipeline

Target direction:

```text
Scene request
     ↓
LLM planner
     ↓
Structured scene specification
     ↓
Map/asset generator
     ├── basemap
     ├── country geometry
     ├── masks/borders
     ├── fixed extent
     ├── 4K exports
     ├── zoomed-out map
     └── high-resolution replacement crop
     ↓
Fusion composition generator
     ↓
DaVinci Resolve / Fusion
     ↓
Manual adjustment if needed
     ↓
4K Shorts / video render
```

This is the current big-picture direction. The internal implementation of each stage should be designed separately rather than prematurely combining everything into one large system.
