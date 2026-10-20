# Arabic city reference label

Template: [city_label.setting](/Users/naseemtoumeh/edit-projects/davinvi-resolve/skills/my-fusion-skills/assets/city_label.setting). Use the name `city_label.setting` for this city-reference template.

Use it when placing a reference marker for a city or capital on the map, with the city name in Arabic. Keep Arabic script and the saved visual style when adapting it, unless the user requests another language or design. Inspect the current file first because the user updates templates manually.

## Saved structure inspected on 2026-10-06

- `MacroTool1` is an editable `GroupOperator`, despite its name. Its 2D image output is `MultiMerge7_1_1_1.Output`.
- `text_1_1` is TextPlus, currently displaying `دمشق` (Damascus) in font `Damascus`, style `Bold`, size 0.0351. The label is light gray.
- `circle_1_1` is an EllipseMask for the city marker, feeding `Background3_2_1_1_2_1_3_1_1`.
- `Bacground_shape_1_1` is a RectangleMask for the label's gray backing, feeding `Background10_1_2_1_1_1`. Preserve the actual node spelling.
- MultiMerge composites the circle on Layer1 and Arabic text on Layer2 over the masked backing. Dimensions are saved at 1920×1080 with frame-format settings enabled.
- The marker Background's RGB channels have saved keys at frames 765 (0) and 781 (1), changing from black to white. Alpha is 1 at frame 765. This is a color animation, not a saved fade-in; retain or retime it intentionally.

## Using the marker

1. Drag the setting into empty Node Editor space and open the group.
2. Change `text_1_1.StyledText` to the desired Arabic city name. Keep the saved font/style; verify Arabic shaping and readability in Resolve. If the font is unavailable, use an Arabic-capable replacement and check the result visually.
3. Place the marker at the city's actual map location and keep the circle, text, and backing aligned. Their saved positions are separate internal Center values, not one published location control. To move the complete label together, transform the group output or position its containing MultiMerge layer. Adjust the text/backing locally when the new name needs more space.
4. Connect the group output to a 2D Merge foreground or a local MultiMerge layer. For use inside a 3D scene, put the image on an ImagePlane3D first, or composite it in 2D after the scene Renderer3D, according to the existing map layout.
5. If retaining the marker color animation at another time, shift the relevant RGB spline keys together. Imported nodes do not automatically reload when the saved template changes.

This documentation update inspected the saved structure only; it did not perform a new Resolve render or change the template.
