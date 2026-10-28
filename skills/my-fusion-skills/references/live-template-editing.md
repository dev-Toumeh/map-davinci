# Live Fusion templates: preservation and verification

## User's carousel/template conventions

- Treat the existing working design as the baseline. Replicate its native stack when asked for the opposite side; do not invent a different architecture, phase offset, or duration. Inspect fresh live state because the user edits paths and controls manually.
- The user explicitly rejected custom nodes/controls for these stacks after persistence/editability problems. Use directly editable native tools; do not solve this by hiding the graph in a macro.
- Keep screen-left stacks on the graph's left and screen-right stacks on its right. Align equivalent nodes on the same rows, use compact regular spacing, and keep final MultiMerge and MediaOut below. Each card retains its own background/film sources where requested. Do not leave experimental nodes interleaved with active stacks.
- A request to align is positions-only, not permission to delete nodes, rename controls, change wiring, or retime animation. Separate retained original branches from active stacks without removing them unless cleanup is requested and dependencies checked.
- Use neutral reusable labels for new template content, not subject/religion-specific names. Preserve existing expression-referenced names unless a coordinated rename is explicitly needed.

## Canvas and branch ownership

- Main MultiMerge Background is a dedicated transparent native Background, not a card stack or a completed branch.
- Composite left/right card-and-blur branches through foreground slots. Do not borrow the other side's card background (notably Background2 belonged to the original right stack in the inspected experiment).
- Blur the complete card, including film artwork, when that is the reference design. Keep independent sharp and blurred placement paths.
- Closed-path displacement is a spatial phase, not a time delay. Check evaluated Center positions and visibility during the actual keyframe range. For the inspected two-sided experiment, right phase = corresponding left phase − 0.50 correctly mirrored its curves and existing timing. This is specific to those curves; do not apply that constant to unrelated paths.

## Native scripting pitfalls verified in this workspace

- Free/Lite Resolve: use native Workspace → Scripts runners. External Resolve Python access was unavailable in this installation. Reuse an existing guarded runner rather than repeatedly installing more menus; keep one task-specific implementation and fresh backup.
- New MediaIn tools can default to Timeline. Set and verify MediaSource=MediaPool and the actual MediaID; a serialized filename or thumbnail is insufficient proof of a usable source.
- AddTool may auto-insert into selected connections. Clear selection/active tool first and verify original wiring afterward.
- FlowView SetPos uses grid coordinates; exported ViewInfo positions use different units (110 horizontally, 33 vertically in this installation). Do not pass raw exported coordinates directly to SetPos.
- Main MultiMerge settings must include owned modifiers when reloaded. Loading only the main tool can lose its attached paths/splines. Plain-table SetInput of LayerOrder serialized an empty ScriptVal in this experiment; preserve full native settings and verify order.
- A reloaded path expression may serialize correctly but evaluate nil. If confirmed, clear with SetExpression(nil), restore it, then evaluate numeric results at several frames. Merely writing the same expression again did not repair the binding here.
- Native tool deletion used tool:Delete(), not comp:DeleteTool(). Back up first and limit deletion to confirmed task-created extras. Do not delete just to tidy an alignment request.

## Evidence required before claiming fixed

- Export fresh before/after compositions and save the native project. For layout-only work, compare every tool and its inputs, keys, and connections, allowing only ViewInfo/editor metadata changes. Do not use a test that ignores newly added nodes when validating their rendering.
- View the actual final composite at entrance, hold, and second-row frames. A correct displacement expression or local image preview does not prove the sharp image appears in final output.
- Check viewer assignment before treating a blank viewer as a failed render. In this experiment, assigning the final MultiMerge to viewer 2 restored the picture without any graph change. Do not claim this explains every black-output failure.
- Recheck after the last mutation, including cleanup. Visual success before deleting extra tools is not post-cleanup verification. State separately whether save/reopen and full-render tests were performed.

- **Never add tools at AddTool's default position from a script** (`comp:AddTool(id, -32768, -32768)`)
  while something may be selected: Fusion then wires the new tool to the selected one, as a
  toolbar click does, and for a MediaIn also creates a Merge. On 2026-10-25 this silently
  re-fed `SAU_Haramain_Track_Plane` from the new Landbridge colour node and added a stray
  `Merge1`. Add at real coordinates (then `FlowView:SetPos`), and count the comp's tools
  before and after to catch anything extra (`(~/edit-projects/davinvi-resolve/naseem-local/archive-claude-codex-bridge-20261026.tar.gz; archived) mkline.py`).
- **Lay out every node a script adds; never leave them piled up** (user, 2026-10-25: "make sure to
  sort the nodes … not just throw them"). Follow the comp's existing pattern. In gulf_trains each
  map line is one horizontal row, left to right `Track_Image → Track_Color → Track_Plane → Merge3D`,
  columns aligned with the other line rows (x ≈ 15.5 / 16.8 / 18.1 / 19.5), rows stacked
  vertically, all feeding `Merge3D1` on the right. Read the neighbours' `FlowView:GetPos`, place
  the new row on the first free band, then take a window screenshot of the Nodes panel to check.

