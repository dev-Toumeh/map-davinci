# Archive Carousel

Local Go tool generating an editable, silent 2D Fusion group from videos and photos. No Go framework or external Go module dependencies. FFmpeg and ffprobe must be on PATH. The bundled film PNG is an existing user-provided project asset, not newly licensed stock.

## Open from the app

Restart the Python app after installing these changes, then open **Archive Carousel** beside GIF → Fusion, or `/archive-carousel`. The app builds the Go binary into `app/runtime/archive-carousel`, launches one localhost-only child on a free port, and redirects to it. The first build requires Go 1.24 or newer. Later launches use the binary unless source files change. Existing map and GIF functionality remains Python.

The app owns this child process. Normal shutdown stops it; the child also watches its parent to avoid being left behind after an unexpected exit. Source files are embedded in the binary, including UI and film artwork.

## Standalone

From this directory:

```sh
go run . --repo-root ../../.. --listen 127.0.0.1:8788
```

Or build a binary with `go build -o archive-carousel .` and launch it with an absolute `--repo-root` path. `--exports-root` overrides the default destination. It works without the Python app; the Back to map link is optional navigation, not a runtime dependency.

## Usage

1. Choose media in three initial slots; add, remove, or move items as needed. Uploads are streamed to temporary disk storage (2 GB maximum per file).
2. For videos, choose source start and section duration. Photos default to 2 seconds. Section durations include movement and sum to the total duration.
3. Choose one shared card ratio: 4:3, 16:9, 1:1, or 9:16. Fill crops centrally; Fit uses black padding. Native Resize/Crop nodes inside the group remain editable.
4. Set timeline FPS (default 24) and movement frames (default 10). Every entrance, including the first, is exactly this length. Internal exits and entrances overlap, centered on the section boundary. The last card holds through the end. Each section must contain at least twice the movement length.
5. Generate and drag the single `.setting` into Fusion. Set composition global start to **0**, FPS to the chosen value, and end frame to the displayed total minus one. This version generates frame-zero spline keys; insertion at another global start requires shifting the spline keys together.

The output is 3840×2160 and transparent outside the cards. Cards fit inside an 85% safe area. Artwork is composited at 0.37 blend; 4:3 uses the complete artwork, other ratios use uniformly scaled top/bottom strips. The shared route has no visible line.

Selected video ranges are extracted without source resizing, converted accurately to timeline FPS at normal speed, and saved without audio. Complete clips already matching FPS/frame count/container can be remuxed without re-encoding. Other opaque clips use H.264 CRF 16; alpha clips use ProRes 4444. Odd dimensions may receive one-pixel codec padding. Photos are converted to PNG; orientation is normalized by FFmpeg. Native TimeStretcher nodes hold the first/last selected frame for overlapping movement.

Exports contain one setting, `carousel.json`, `USAGE.txt`, selected media, the original/adapted film PNGs, and `package.zip`. Loaders use absolute paths to this generated folder; moving or unzipping elsewhere requires relinking the Loaders. The JSON records inputs, source metadata, and quantized timings; it is not yet an importable UI preset. Existing packages are never overwritten.

Export-folder preferences live independently in `app/runtime/archive-carousel/settings.json`. Uploaded originals are temporary and removed on clean service shutdown. They are not automatically included in the export—only selected ranges are.

## API

All endpoints are on the Go service origin. Cross-origin browser writes and non-loopback Host headers are rejected.

- `GET/POST /api/settings`: destination and navigation; POST `{path, useDefault}`.
- `POST /api/media?name=<filename>`: raw streamed file; returns media ID/type/dimensions/duration/FPS.
- `GET /api/media/<id>/thumbnail`: PNG thumbnail.
- `POST /api/generate`: `{name, aspect, fps, movementFrames, items:[{mediaId,start,duration,fit}]}`; returns job ID.
- `GET /api/jobs/<id>`: running/done/error, progress, result paths. One export runs at a time.
- `GET /files/<package>/<file>`: downloads restricted to registered generated packages, with symlink escape checks.

Media IDs, job records, and download registrations are session-local. Files survive restart and can be opened directly; old browser download URLs do not.

## Tests

```sh
go test ./...
go test -race ./...
go vet ./...
```

Integration tests use synthetic FFmpeg media. LuaJIT checks Fusion table syntax and internal links when installed; this does not prove playback in Resolve. No active Resolve project is opened or changed automatically. Check a generated group visually in Resolve, including save/reopen, before using a long production sequence.
