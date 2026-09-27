# Backlog

## Rebuild map assets without replacing manual Fusion work

The animation editor should be able to analyze an updated camera path and
regenerate only the affected Wide, Detail, and Close-up imagery and matching
mask assets. Existing Fusion compositions may contain substantial manual work,
so rebuilding assets must preserve node names, paths, styling, timing, and
unrelated user-created nodes.

Acceptance criteria:

- Detect which existing image levels no longer cover the edited camera path or
  no longer meet the configured resolution threshold.
- Regenerate only affected assets, using stable filenames and geographic
  extents where possible.
- Relink or update generated Fusion nodes without replacing unrelated or
  manually edited nodes.
- Create backups before modifying a composition.
- Report movements that exceed the rebuilt coverage margin and require a new
  Close-up level.

This is follow-up work. The initial adaptive-resolution implementation may
generate a new composition after camera movement is finalized.
