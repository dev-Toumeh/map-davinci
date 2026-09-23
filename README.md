# Map DaVinci

Repository for a deterministic map-asset preparation app and the Fusion project
references that inform its future workflow.

## Structure

| Folder | Purpose |
| --- | --- |
| `app/` | The map-asset preparation application: entry point, core services, Fusion generation, UI, tests, resources, and documentation. |
| `references/` | Existing Fusion compositions, USA reference assets, and archived scripts. These are reference material, not app source. |
| `docs/` | Project specification and handoff notes. |

Generated data stays local and is ignored by Git:

- `app/runtime/data/` — downloaded Natural Earth country data
- `app/runtime/tilecache/` — downloaded imagery tiles
- `app/runtime/logs/` and `app/runtime/settings.json` — local logs and settings
- `exports/` — generated asset packages

## Run the app

```bash
cd /Users/naseemtoumeh/edit-projects/davinvi-resolve
.venv/bin/python app/server.py
```

Open <http://127.0.0.1:8787>.
