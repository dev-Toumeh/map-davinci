# Creating a map-animation project

## Generate the base through the app

We can use the app to generate the maps, countries, and movement keyframes. It also generates close-up images at the points where we zoom in to keep the map sharp.

For new projects in this workspace, generate the base Fusion composition through the map-animation app before adding story-specific nodes. Exporting map assets alone does not generate the composition.

Use the app's Fusion export workflow, which calls `app/fusion/generator.py::generate`. The current API is `POST /api/animation/<package-name>/fusion`, with the animation configuration and `fusion_mode` set explicitly to `3d` or `2d`. When working programmatically, use the same app generator with normalized animation data rather than writing a replacement composition from scratch. Inspect the current app implementation before using its API.

Use **Esri World Imagery** as the default map source for this user's projects, including wide maps and zoom close-ups. Select it explicitly when working with an older app version whose default may still be Google. Keep the map assets, metadata, animation configuration, and generated composition together in the export package. Save the app-generated base before extending it so the original structure can be inspected.

## Extend the generated structure

Use labels for cities, not countries. Countries are identified by their flag fills; do not add country-name labels.

Do not show every country highlight from the beginning. Reveal each country’s flag fill and highlight when that country is mentioned in the narration; keep countries not yet mentioned unhighlighted on the satellite map. Time each reveal to its mention.

Story captions are added manually by the user as subtitles in Resolve. Do not generate `Story_Caption` nodes for them in Fusion. Keep city labels in the Fusion composition.

Preserve the app's node organization, country groups, camera setup, map registration, and existing `ViewInfo` positions. Add the story's labels, routes, icons, and captions to that generated graph using the current saved templates where appropriate. Inspect templates before adapting them because the user updates them manually.

Give each added visible node an intentional `ViewInfo = OperatorInfo { Pos = { x, y } }` position; use `GroupInfo` for groups. Arrange connected stages with readable spacing and place related nodes together. Do not omit positions or put every node at the same point. Preserve readable internal layouts when adding groups.

Place map-anchored graphics in the map's registered coordinates and connect their 3D output to the scene, using an ImagePlane3D for 2D graphics as needed. Composite screen-fixed captions after Renderer3D. Prefer editable saved node groups; disclose any rasterized fallback and its editing limitations.

## Check and deliver

Check syntax, SourceOp links, asset paths, frame ranges, and node positions before importing. Use supported Resolve import/scripting workflows; preserve existing timelines and back up an existing project before modifying it. Check the node layout and rendered result inside Resolve when access is available.

State which stages actually ran: app asset export, app composition generation, story-specific extensions, Resolve import, and native preview. If access is blocked, identify the unfinished stage. A separately rendered software preview does not establish that the native Fusion composition works.

The Kuwait opening exposed the distinction: assets were exported through the app, but a separately authored composition bypassed its generator and omitted node positions. Future projects must start from the app-generated composition and retain its structure.
