# Flowing dotted line

Template: [doted-moving-line.setting](/Users/naseemtoumeh/edit-projects/davinvi-resolve/skills/my-fusion-skills/assets/doted-moving-line.setting).

The template is an editable `GroupOperator` named `Flowing_Dotted_Line`. Its 2D output comes from `Dots_On_Path`, a `TextPlus` with repeated circular glyphs and Path layout. The background is transparent; the route itself is an editing guide rather than a rendered stroke.

## Editing the template instance

- Open `Flowing_Dotted_Line`, select `Dots_On_Path`, and view its output. In the Inspector, open Layout with Type set to Path.
- Drag the route points and Bezier handles in the viewer. Use Insert and Modify to add bends. Select the inner TextPlus so its path controls are visible.
- Change TextPlus Size for dot size, Styled Text spacing or character tracking for gaps, and Shading element 1 for color.
- The saved `PositionOnPath` input contains `(time % 24) * 0.0015`: a repeating phase over 24 frames. Changes to dot spacing or path length may require adjusting this phase so the reset matches the dot spacing visually. A seamless loop has not been verified.
- Editing an imported instance changes that instance. Save the group back to the template file only when the user asks to update the reusable template; add a fresh instance when testing a changed file.

## Validation status

The setting passed Lua table syntax and internal output-link checks. Its rendered appearance, the serialized `PositionOnPath` control, and seamless motion have not been confirmed in Resolve. Verify these in a live preview before treating the animation as a tested workflow. Preserve this distinction when reusing or documenting it.

The output is a 2D image: merge it into a 2D map stack, or use the project's existing 2D-to-3D integration when needed.
