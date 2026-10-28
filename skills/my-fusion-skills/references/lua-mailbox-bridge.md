# Lua mailbox bridge: reading and editing the live Resolve project (Studio direct since 2026-10-28; mailbox for the old App Store build)

Verified working on 2026-10-24 against the gulf_trains project. Use it when you
need facts from the project that is open right now in Resolve (timelines,
tracks, clips, markers, media pool, settings) instead of guessing from saved
files.


> **Resolve Studio 21.1.2 (since 2026-10-28): no mailbox, no Scripts menu.** The user moved to
> Studio (website build). `claude_bridge_client.py` (and so every `resolve-bridge` MCP tool) now
> connects with Python external scripting, runs the same `claude_bridge.lua` OPS through
> `fusion:Execute` with `CLAUDE_BRIDGE_CALL = {id, op, args}`, and reads the answer from
> `fusion:GetData("ClaudeBridge.Response")`: ~0.15 s per request, stills ~4 s. Nothing needs starting
> in Resolve; Studio only has to be open. Studio's Lua has `io` and `SavePrefs` again. Files (stills,
> exports) go to `~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/.claude_lua_bridge`.
> `CLAUDE_BRIDGE_DIRECT=0` forces the old mailbox (tests do, via the repo's `conftest.py`).
> Pitfall: `dofile` of the bridge without `CLAUDE_BRIDGE_CALL` used to start the mailbox loop inside
> Studio and block Fusion's script thread; a guard now returns early. To free a stuck loop, set
> `fu.SetPrefs("Global.ClaudeBridge.Instance", "x")` from Python. The App Store notes below are history.

> **Use the `resolve-bridge` MCP tools (2026-10-26).** Every op below is an MCP tool
> (`~/Projects/resolve-bridge/mcp/server.py`, registered for Claude Code and Codex): `bridge_status`,
> `read_values`, `sample` (jump check), `links`, `fusion_run`, `fusion_paste`, `set_keys`, `still`,
> `stills` (contact sheet), markers, media, render (`render_start` only with `confirm=true`). Safety is
> built in (backups before edits, safe reads only, one session at a time, absolute handles converted).
> Use the shell client only if the MCP server is unavailable.

## Why it exists (read before trying anything else)

The user runs **DaVinci Resolve 21.1.1, free, Mac App Store build**
(`com.blackmagic-design.DaVinciResolveLite`). It is sandboxed, and a probe
script established what its scripting can do:

| Route | Works? |
| --- | --- |
| External scripting (`fuscript`, Python `DaVinciResolveScript` from a terminal) | **No**: Studio-only |
| Python scripts in Workspace ▸ Scripts (incl. `davinci-resolve-mcp`'s `resolve_bridge.py`) | **No**: free 21.1 has no Python scripting |
| Lua scripts in Workspace ▸ Scripts | **Yes**, with the full Resolve API (`resolve`, `fusion`, `bmd`) |
| Lua `io` library, `os.remove`, `os.rename`, `os.execute`, `package`/`require` | **No** (nil) |
| `bmd.readfile`, `bmd.writefile`, `bmd.createdir` | **No** (nil) |
| `dofile`, `loadfile`, `load`, `loadstring` | **Yes**: a script can run a Lua file from disk |
| `bmd.fileexists`, `bmd.direxists`, `bmd.wait` | **Yes** |
| Fusion preferences: `fusion:SetPrefs` + `fusion:SavePrefs`, `GetPrefs` | **Yes**: saved to `Fusion.prefs` on disk |
| `print` output in Workspace ▸ Console | **Never shows**, even when the script runs fine |

So a script inside Resolve can *read* files (by running them) and *write* only
through Fusion's preferences. The bridge is built on exactly those two.

## Where things run

- **Inside Resolve, always:** `claude_bridge.lua`. Free Resolve (and this
  sandboxed App Store build) refuses scripting connections from outside the
  app, so nothing in a terminal can talk to Resolve directly. The user starts
  it once: Workspace ▸ Scripts ▸ claude_bridge.
- **Anywhere, any terminal, any agent:** `claude_bridge_client.py`. Once the
  bridge runs, every request goes through the client; nothing more needs
  doing in Resolve.
- The bridge keeps running until a `stop`, 2 hours without requests, or
  Resolve quitting. Each request asks Resolve for the *current* project and
  timeline, so switching projects needs no restart. After installing a new
  version of the script, `stop` the running one and have the user start it
  again: a running bridge keeps its old code.

## How it works

```
agent ──writes──▶ mailbox/req_000001.lua   (return { op = "clips", args = { track = 1 } })
                        │
Resolve: claude_bridge.lua polls (bmd.fileexists every 0.25 s), dofile()s it,
         runs the op, then SetPrefs("Global.ClaudeBridge.Response", <JSON>) + SavePrefs()
                        │
agent ◀──reads── Fusion.prefs ▸ Global.ClaudeBridge.Response   ({"id":1,"ok":true,"result":...})
```

- Requests are numbered `req_000001.lua`, `req_000002.lua`, … and handled
  strictly in order. The next number is `Global.ClaudeBridge.Next` (persisted
  in the prefs, so numbering continues across bridge restarts). Write the
  request file whole and rename it into place, so the bridge never reads half
  a file.
- One answer slot: `Global.ClaudeBridge.Response` holds the latest answer as
  JSON with its `id`. Wait until that `id` equals your request number.
- `Global.ClaudeBridge.Status` is `running` / `stopped`; `Global.ClaudeBridge.Beat`
  is a Unix time saved every 10 s. Beat older than ~35 s means it isn't
  running.
- The bridge cannot delete files (no `os.remove`), so the **agent** deletes
  answered requests (numbers below `Next`). The client does this.
- It stops on a `{ op = "stop" }` request or after 2 hours without requests.
- A Scripts-menu script runs as its own process, so the polling loop does not
  freeze Resolve's interface.

## Files and paths

All in the user's Resolve repo, `~/Projects/resolve-bridge/bridge/`:

- `claude_bridge.lua`: the bridge (runs inside Resolve). **Source of truth**;
  copy it into both Scripts folders below after any change.
- `claude_bridge_client.py`: send one request, print the result.
- `bridge_test.lua`: offline test with a fake Resolve/Fusion (see Testing).
- `README.md`: short summary.

Inside the App Store container
(`C=~/Library/Containers/com.blackmagic-design.DaVinciResolveLite/Data/Library/Application Support`):

- Scripts menu (install the bridge in **both**; Resolve reads them):
  `$C/Fusion/Scripts/Utility/` and `$C/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility/`
- Mailbox: `$C/Blackmagic Design/DaVinci Resolve/Fusion/.claude_lua_bridge/`
- Answers: `$C/Fusion/Profiles/Default/Fusion.prefs` (a Lua table; key
  `Global.ClaudeBridge`)
- Errors from scripts: `$C/logs/ResolveDebug.txt` (look for
  `claude_bridge.lua:<line>:`). This is the only place a script failure shows.

## Using it

1. Ask the user to open the project and start the bridge: **Workspace ▸
   Scripts ▸ claude_bridge**. Tell them the Console stays empty; that is
   normal here.
2. Check it is alive, then send requests:

```sh
cd ~/edit-projects/davinvi-resolve/claude-bridge
python3 claude_bridge_client.py status          # {"running": true, ...}
python3 claude_bridge_client.py info
python3 claude_bridge_client.py clips '{"type": "audio", "track": 1}'
```

The client needs `luajit` (Homebrew) to read `Fusion.prefs`. Exit codes: 0
result printed as JSON, 1 the op failed (`{"error": ...}`), 2 bridge not
running / no answer. Default timeout 20 s (`--timeout S`).

### Operations

`timeline` (in any op's args) picks a timeline by name or 1-based index;
default is the current one.

| op | args | returns |
| --- | --- | --- |
| `ping` | | `{pong, time}` |
| `info` | | product, version, project, timelineCount, current timeline (name, start/end frame, start timecode, playhead, frameRate, width, height, track counts) |
| `projects` | | projects in the project manager's current folder, current one |
| `timelines` | | `[{index, name, current, startTimecode}]` |
| `tracks` | `timeline` | per type (video/audio/subtitle): `[{index, name, items}]` |
| `clips` | `type` ("video"), `track` (1), `timeline` | `{count, items: [{index, name, start, end, duration, sourceStart, sourceEnd, enabled, color, file, media}]}` (timeline frames; max 2000) |
| `markers` | `timeline` | `[{frame, color, name, note, duration, customData}]` |
| `media` | `depth` (3) | media pool tree: `{name, clips: [{name, file, duration}], folders: [...]}` |
| `settings` | `name` (optional) | one project setting, or all of them |
| `stop` | | ends the bridge |

Fusion compositions are picked by `item` (a timeline item's name, or its
index on `type`/`track`, default video 1) and `comp` (name or index, default
1). Without `item`, the composition open on the Fusion page is used.

| op | args | does |
| --- | --- | --- |
| `fusion_comps` | `item` | `{item, count, names}` |
| `fusion_tools` | `item`, `comp` | every tool: `{name, type, group, links: [{input, from}]}` |
| `fusion_export` | `item`, `comp`, `name` | Resolve's `ExportFusionComp` writes `mailbox/export_<name>.comp` (the whole composition, readable as a .comp); returns `{path}` |
| `fusion_paste` | `item`, `comp`, `settings` (.setting text), `label` | `comp:Paste()`, **one undo step**. Works since 2026-10-25: the bridge parses the text itself (see below) |
| `fusion_run` | `item`, `comp`, `run` (Lua `function(ctx)`), `label` | runs `run(ctx)` with `ctx.comp`, `fusion`, `resolve`, `project`, `timeline`, `item`, `args`, inside `StartUndo`/`EndUndo` and `Lock`/`Unlock`: **one undo step**; returns what `run` returns (plain values) |

Anything else answers `unknown op`.

### Editing compositions

The user asked for real Fusion access (2026-10-24). Edits go through
`fusion_paste` and `fusion_run` only:

- Each is one named undo step (`label`): Cmd+Z in Fusion takes it back.
- Before the first edit in 30 minutes, the client copies the open project's
  `Project.db` (Resolve's last saved state) to `~/Projects/resolve-bridge/bridge/backups/`.
- Inspect first (`fusion_export` or `fusion_tools`): the user edits by hand
  too, and the saved state may differ from what you remember.
- Pass code and node files with the client's file values: `"@lua:<file>"`
  inserts Lua code (the `run` function), `"@text:<file>"` a file's text (a
  `.setting` for `settings`). Strings are sent as Lua long strings, so
  Arabic and any other text arrive verbatim.

```sh
# Set one input on a tool of the "main" composition.
cat > /tmp/edit.lua <<'LUA'
function(ctx)
  local t = ctx.comp:FindTool("Map_Wide")
  t:SetInput("Blend", 0.5)
  return { ok = true }
end
LUA
python3 claude_bridge_client.py fusion_run '{"item": "main", "label": "Claude: map blend", "run": "@lua:/tmp/edit.lua"}'
```

**Resolve 21.1.2 broke the bridge (App Store auto-update, 2026-10-28 08:35):** `fusion:SavePrefs` is gone,
so answers never reach disk. Also gone: `io`, `os.execute/rename/remove`, FFI (`require "ffi"` fails),
`bmd.writefile/readfile`, `comp:Save`; `tool:SaveSettings(path)` fails. Still there: `SetPrefs/GetPrefs` (memory
only), `dofile`, `bmd.fileexists`, `bmd.wait`, and Resolve's own exports, which still write files:
`item:ExportFusionComp(path)` (carries `comp:SetData` custom data), `MediaPool:ExportMetadata`, `Timeline:Export` (EDL).
Planned fix: answers through a comp export of a tiny dedicated mailbox comp. The user plans to switch to the
Blackmagic-website free Resolve instead of the App Store build. Turn App Store auto-updates off.
**The Scripts folder Resolve reads** is `~/Library/Containers/com.blackmagic-design.DaVinciResolveLite/Data/Library/
Application Support/Fusion/Scripts/Utility/`, NOT `.../Blackmagic Design/DaVinci Resolve/Fusion/Scripts/` (that one is
unused: bridge edits and autostart hooks put there never ran). Check the Console error's path. Only the menu
click starts the bridge; autostart hooks never fired (but they were in the wrong folder, so untested).
Leftover: a probe left `CustomData ClaudeProbe = "savesettings works"` on `MediaOut1` of the comp open in the
Egypt project (harmless; remove with `MediaOut1:SetData("ClaudeProbe", nil)`).

**Adding nodes: paste a table parsed in Lua (works, 2026-10-25).** Only
Fusion's *text parser* is broken here: `bmd.readstring` errors with "attempt
to index a string value", but `comp:Paste(table)` works. A .setting is a Lua
table, so read it with `loadstring` in an environment where every unknown
name is a constructor: `Name{...}` → that table with `__ctor = "Name"`, and
`ordered()` → the table. The bridge's `fusion_paste` does this now
(`readsetting`); inside a `fusion_run`, copy it (see
`~/Projects/resolve-bridge/generators/stroke_tracks/build.lua`, which pastes 24 shape tools
with expressions and an instanced tool in one step). Paste keeps names, inputs,
expressions, `SourceOp` instances, groups (nested too) and their published
inputs/outputs, **but not links to another group's outputs**. **Clear the selection first**
(`FlowView:Select()`): pasting a 3D node while another 3D node is selected makes
Fusion add a Merge3D joining them (a stray `Merge3D4` on 2026-10-25), like `AddTool`
at the default position. Connect links to group outputs with `ConnectInput`
after the paste (`FindTool` and `ConnectInput` work across group borders). Set
positions afterwards with
`FlowView:SetPos`. Check every expected name exists and the tool count grew by
exactly that many; delete what arrived if not.
**Grouping loose nodes after the fact (2026-10-27, both Saudi counters):** Fusion can't move
nodes into a group by script, so export the comp, cut the nodes' blocks out of the text, wrap them
in a `GroupOperator` (drop inner `Input`s whose `SourceOp` is outside; publish image inputs and
controls as `InstanceInput`s), then in one `fusion_run` delete the loose nodes, paste the group and
reconnect the outside links to the inner tools with `ConnectInput`. Keyframes, splines and modifiers
come along. Tool: `~/Projects/resolve-bridge/generators/counter/group_counter.py` + `group_counter.lua`.
`fusion_run` hands the request's own fields to `ctx.args` (put extra args at the top level, not in
an `args` object).
**`fusion_paste` can answer `pasted: true` and add nothing** (UAE_Train, 2026-10-26; the
same paste worked on retry). Always look the names up right after, and retry once. Separately,
`comp:CopySettings`, `tool:SaveSettings()` (no path) and `comp:Paste` of `bmd.readstring` output
still fail in the bridge ("attempt to index a string value") while they work in the Console and by
hand: a limit of menu scripts in free 21.1, not a broken comp.

**Keyframes by script:** `spline:SetKeyFrames({ [f] = { v, LH = {...}, RH = {...} } }, true)`
takes the handles **relative to the key** (frames, value), unlike the absolute handles in
.comp/.setting text (which a paste takes as written). Absolute values there make each
segment bulge and jump at the next key (see camera-moves.md). Read back per frame.
**Moving keys in time:** `GetKeyFrames()` returns handles as absolute `{frame, value}`;
`SetKeyFrames` reads them as relative. Copying keys unchanged works, but shifting a key by `d`
and adding `d` to its handles sends them `d` frames away (2026-10-27: Oman pops became a 0 → 1.15
jump in one frame). To move keys, write fresh relative handles (pop: `[f-6]={0,RH={2,0}}`,
`[f]={1.15,LH={-2,0},RH={1.33,0}}`, `[f+4]={1,LH={-1.33,0}}`), then sample the curve.
`DeleteKeyFrames(-1e6, 1e6)` deletes nothing; use the real frame range. `DeleteKeyFrames(lo, hi)`
keeps the key at `lo`: delete one key with `(f - 0.5, f + 0.5)`.
**Animating a static input:** `tool:AddModifier(id, "BezierSpline")` also adds a key **at the playhead**
with the old value; `SetKeyFrames` then merges with it (2026-10-27: Saudi lines turned green, then
back to red at the playhead key 1674). Delete every key you didn't set, then sample a frame after
the last key. A `GetInput(id, f)` in the same run can read stale values; check in a new run.

**Older route: `AddTool` + `LoadSettings` from a file.** On the
free App Store Resolve 21.1, Fusion's settings text parser fails in the sandbox:
`bmd.readstring`, `comp:Paste(text)` and `comp:CopySettings` error with
"attempt to index a string value" (found 2026-10-24); pasting a table parsed
in Lua (above) avoids it. The file route works, because Fusion's C++ side
does the reading and writing:

1. Write one `.setting` file per tool into the mailbox folder
   (`{ Tools = ordered() { Name = Type { Inputs = { ... } } } }`, the format
   `tool:SaveSettings(path)` writes). Leave out links (`SourceOp`) and
   `ViewInfo`.
2. In one `fusion_run`: `t = comp:AddTool("Type", -32768, -32768)`,
   `t:LoadSettings(mailbox .. "/Name.setting")`,
   `t:SetAttrs({ TOOLS_Name = "Name" })`, and then wire with
   `t:ConnectInput("Input", other)`. Delete what you made if a step fails.
3. Check with `fusion_export`: the tools, their values and links.

A MediaIn made this way loses `MediaID` in `LoadSettings`: set it after with
`t:SetInput("MediaID", id)`. New media goes into the pool from `fusion_run`
with `ctx.project:GetMediaPool():ImportMedia({ path })` (works in the
sandbox for the user's media folders); `item:GetMediaId()` gives the id.

`tool:SaveSettings(path)` into the mailbox is also how to read one tool's
full settings. Worked example: the East Train track in `~/edit-projects/project2/shorts/gulf_trains_lines/kit/` (fit.py → routes.py → make_setting.py → split.py → build.lua) and
[gulf-trains-video.md](gulf-trains-video.md).

Inside `run`, use Fusion's object API (`comp:FindTool`, `comp:AddTool`,
`tool:SetInput`, `tool:ConnectInput`, `tool.Input = other.Output`, keyframes
via a `BezierSpline` modifier); see the `davinci-resolve-fusion` skill.

### Reading a whole composition without the bridge

`Project.db` in the project folder (above) is SQLite. Table
`Sm2TiCompositionTable`, column `CompositionBA`: 4-byte big-endian size +
zlib → a Qt map whose `0_data` value is a header text (`Composition { … ,
Compressed = true, }`), a NUL, a 4-byte little-endian size and a second zlib
stream: the tools table (`{ ToolName = Type { … }, … }`, with a trailing
NUL). Copy the database first; this is the last *saved* state.

## Verified live (2026-10-24, gulf_trains)

- `info`, `timelines`, `tracks`, `clips`, `markers`, `media` answered from
  the open project.
- `fusion_comps {"item":"main"}`: one composition, "Composition 1".
- `fusion_tools {"item":"main"}`: all 282 tools, matching an offline read
  of `Project.db`.
- `fusion_export {"item":"main","name":"main"}`: Resolve wrote
  `mailbox/export_main.comp` (272 KB, a normal `.comp` text file; the
  sandbox allows it inside the mailbox).
- `fusion_run` with a function that only reads: ran inside the comp, and
  the client made `backups/gulf_trains-<time>.db` first. Note: even a run
  that changes nothing leaves an (empty) named step in Fusion's undo history.
- Resolve tags some returned lists with an internal `__flags` key; the
  bridge's JSON drops it.

## Changing or extending it

- Add an operation as a function in the `OPS` table of `claude_bridge.lua`.
  Wrap API calls that can fail per item in `safe(...)`, return plain tables
  (no Resolve objects; they can't be serialized), and keep answers small:
  everything goes into `Fusion.prefs`.
- Fusion edits exist (`fusion_paste`, `fusion_run`, see above). Other
  operations that change the project (add markers, move/trim clips, import
  media) are not there on purpose: add them one at a time, only with the
  user's explicit OK, and say what each changes.
- After editing: run the offline test, check syntax with `luajit -bl
  claude_bridge.lua >/dev/null`, copy the file into both Scripts folders, and
  ask the user to restart the bridge from the menu (a running bridge keeps
  the old code; send `stop` first).

## Testing offline

```sh
cd ~/edit-projects/davinvi-resolve/claude-bridge
luajit bridge_test.lua claude_bridge.lua     # every op, 3 bad requests, stop
python3 -c "import json; [json.loads(l) for l in open('answers.txt')]"
```

It must print `answers 20 … status stopped next 21` and `undo opened 3
closed 3 locks 0`, and every answer must be valid JSON. Keep the fakes faithful to the real API: the first live run
failed because the fake `GetPrefs` returned `nil` where real Fusion returns
**no value at all** for an unset key (`tonumber(fu:GetPrefs(k))` then
errors). Also covered: a malformed request (not a table) must produce an
error answer, not crash the loop.

## Troubleshooting

- **"No output" from the user**: expected; never ask them to read the
  Console. Check `client.py status` and `ResolveDebug.txt` instead.
- **status says not running**: the bridge stopped (2 h idle, a `stop`, a
  Resolve restart) or crashed; look for `claude_bridge.lua:` in
  `ResolveDebug.txt`, fix, reinstall, ask the user to start it again.
- **No answer, beat fresh**: the request number may be wrong; compare the
  file name with `Global.ClaudeBridge.Next`.
- **Script missing from Workspace ▸ Scripts**: it must be a `.lua` file in
  one of the two `Utility` folders above.
- The probe used to discover all this, `claude_lua_probe.lua`, and its
  `ClaudeBridge.Report` / `Started` prefs entries can be deleted once not
  needed.
- **Resolve quits every time the bridge starts**: a request in the mailbox is
  crashing it and, before 2026-10-25, was re-run on each start. Move the
  `req_NNNNNN.lua` numbered `Next` out of the mailbox. Since 2026-10-25 the bridge
  marks `Global.ClaudeBridge.Busy` before running a request and skips it on the next
  start if Resolve died during it (answer: "skipped: … crash?"). If you removed the
  file by hand instead, the next request with that number is skipped once; resend it.
- **"skipped: … crash?" but Resolve didn't crash** (same process, no crash report; the work
  sometimes still happens, e.g. a still file appears): two bridge loops are running, and both take
  each request. Pastes then also fail ("paste added nothing"). Seen 2026-10-27 three times. Since
  then each start writes a `Global.ClaudeBridge.Instance` token and an older loop stops when it sees a
  newer one, so starting the bridge again replaces the old copy. Copies started before that fix
  ignore the token: stop them with `claude_bridge_client.py stop` (once per copy), then start the
  bridge once.
- **Resolve freezes (deadlock) during a request**: the beat stops and Resolve
  sits at a few % CPU. Seen 2026-10-25: a probe called `tool:GetInput(id)` on
  *every* input of `Map_3D_Renderer` and the Merge3D tools, including image and
  3D-scene inputs. `sample <pid>` showed the main thread stuck in
  `Input::GetSourceTagList` → `MsgPort::Wait` for good: it never recovers, so
  force quit. **Only `GetInput` inputs whose `INPS_DataType` is Number, Point,
  Text or FuID**; to see what feeds an image/scene input use
  `inp:GetConnectedOutput()`, never its value.
- **macOS keeps asking iTerm2 to access another app's data**: the client reads
  `Fusion.prefs` inside Resolve's sandbox. Give iTerm2 Full Disk Access once
  (Privacy & Security ▸ Full Disk Access), or every read is blocked
  ("Operation not permitted").

## Getting a frame image (2026-10-25)

- **Never call `Save` on a Fusion image object** (`output:GetValue(t):Save(path)`):
  it exists, but it crashed free Resolve 21.1.1 (wrote a 0-byte PNG, then Resolve quit,
  and again on every bridge restart until the request was removed).
- A temporary Saver + `comp:Render{Start=t, End=t, Tool=saver, Wait=true}` returns
  false and writes nothing; Savers don't render from scripts here.
- **Full-resolution frame: the `still` op** (2026-10-25, verified):
  `claude_bridge_client.py still '{"frame": 420, "item": "main"}'`. It switches to the
  Color page (stills and playhead moves only work there), reads the playhead *there*
  (on the Fusion page timecode calls don't reflect it), moves, exports the whole
  timeline frame (all tracks), then restores playhead and page (~3 s flick). `frame`
  counts from the timeline start, or with `item` from that clip's start in comp frames;
  no `frame` = where the playhead is. The client moves the PNG to `~/Projects/resolve-bridge/bridge/snaps/`
  and adds a 1600 px JPEG (`preview`) to look at. Replaces `examples/gulf_trains_east/still.lua`.
- **What the user sees**: a macOS screenshot of the Resolve window only,
  `~/Projects/resolve-bridge/bridge/snap_window.sh` (iTerm2 needs Screen Recording permission); no change in Resolve.

## Never save Fusion prefs while idle (2026-10-26)

The bridge answers through Fusion.prefs. It used to save a "still here" beat every 10 s for up to
2 h. Resolve crashed three times in Fusion's prefs/script code (colour picker, quitting, waking from
sleep) while it ran. Now it saves only on start, on each answer and on stop, and quits after 2 h
idle (no saves while idle, so a long limit is harmless). The client decides it is running when it picks a request up (`Busy` = id) within 5 s, and
deletes the request if not. Separately, an MCP server that imports `DaVinciResolveScript` wrote a
`__pycache__` into the app bundle and broke the App Store signature: run such servers with
`PYTHONDONTWRITEBYTECODE=1`.

## Did Resolve crash? (crash_check.py)

`python3 ~/Projects/resolve-bridge/bridge/crash_check.py` lists Resolve crashes since its last run
(`--all`: every one still in Resolve's logs), with the Fusion/Lua/Qt frames of the crashing stack.
Run it at the start of a session. A crash in `PrefsChanged`, `CustomColor`, `PrintF` or a script
thread while the bridge ran points at the bridge; anything else is probably Resolve itself.

**No Console print per request (2026-10-27).** Resolve crashed (signal 10) in
`FusionDoc::PrintF` → `ObtainMutex` from the bridge's script thread: it printed one Console line per
answered request, and after hundreds of requests a print collided with Fusion's own work. The bridge
now prints only once at start and once at stop. Don't add per-request `print`s back (the answer is
in the prefs, and `claude_bridge_client.py status` shows the progress). A separate crash the same day,
signal 11 in `CopyImageToGTexture` (a GPU texture upload), happened while large 3840×2160 RGBA
textures (the Bahrain close-up, extra track renders) were on screen. Watch for it if it comes back.
