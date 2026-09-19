# Map DaVinci

Repository for a deterministic map-asset preparation app and the Fusion project
references that inform its future workflow.

## Structure

| Folder | Purpose |
| --- | --- |
| `app/` | The map-asset preparation application: server, exporter, UI, and its instructions. |
| `references/` | Existing Fusion compositions, USA reference assets, and archived scripts. These are reference material, not app source. |
| `docs/` | Project specification and handoff notes. |

Generated data stays local and is ignored by Git:

- `app/data/` — downloaded Natural Earth country data
- `app/tilecache/` — downloaded imagery tiles
- `app/exports/` — generated asset packages

## Run the app

```bash
cd /Users/naseemtoumeh/edit-projects/davinvi-resolve
.venv/bin/python app/server.py
```

Open <http://127.0.0.1:8787>.
