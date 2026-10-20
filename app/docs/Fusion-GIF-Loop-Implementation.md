# Fusion GIF Loop: App Implementation

## App workflow

Open `/gif`, or click **GIF → Fusion** beside Settings on the landing page.
Upload a local GIF, enter a group name and timeline FPS (default 24, matching
map-animation exports), and generate the group.
The page previews the original GIF and provides the setting download, its local
path, and a ZIP containing the PNG assets. All packages are saved under the
Exports location configured in Settings, in `gif-loops/<unique-name>/`, unless
the GIF page's export-folder override is saved. That override is independent of
map exports and is stored as `gif_exports_path` in app settings. Use default
removes the override. A folder change applies to future conversions only.

The generated editable group follows `references/nodes/gif-reference.setting`
with one GIF branch: Loader → TimeStretcher → MultiMerge, over a transparent
3840×2160 Background. Its sole output is the MultiMerge composite. Position,
Size, Angle, Blend, and canvas Width/Height are published native controls alongside
Speed, Timeline FPS, and Offset. The single GIF layer starts centered, enabled,
with full Blend; reference copies, country placements, and fades are omitted.

`POST /api/gif?name=<group-name>&fps=<timeline-fps>` accepts the raw GIF body.
It returns `setting_url`, `setting_path`, `zip_url`, `output_dir`, `group_name`,
`frame_count`, `width`, `height`, `durations_ms`, `loop_ms`, and `timeline_fps`.
`GET/POST /api/gif/settings` reads/saves the GIF destination (`path` or
`use_default`). Generated files are served under `/api/gif/files/` from that
configured destination, with path containment checks. The page reuses the native
folder picker and can also save a typed path during export.
Conversion is implemented in `app/core/gif_loop.py`. Each output has its own
directory and internal Fusion identifiers. The setting references the absolute
path of the completed PNG package; no installer is needed on the generating
machine. Moving the assets requires relinking the Loader.

The converter sequentially decodes full RGBA frames, substitutes 100 ms for
missing/zero frame durations, and always repeats regardless of the source GIF's
embedded loop count. Balanced `iif` comparisons select the source frame without
linear expression nesting. Loader Loop is enabled and GlobalEnd is 1000000,
so the animation can repeat through long compositions.

Limits: 25 MB per upload, 512 frames, 4096 pixels per side, and 128 million total
decoded pixels. Timeline FPS accepts finite values from 1 through 240, including
fractional rates. Failed conversions remove their temporary package, and repeated
conversions create unique packages. The tests cover pixel/alpha fidelity,
duration boundaries, repeated playback, Lua syntax/links, ZIP contents, limits,
and HTTP integration. Live Resolve import/playback remains a separate check.

The generated group uses a **PNG sequence → Loader → TimeStretcher**, wrapped in a **GroupOperator**. It exposes animation speed, timeline FPS, and animation offset.

This describes the Swipe Up example and how to generalize it into a local function. It does not depend on importing GIFs directly into Fusion.

## 1. Extract the GIF into transparent PNGs

Use Python's Pillow library to extract each frame as a full RGBA image and record its duration. Read the GIF sequentially so Pillow processes its frame disposal and compositing state.

```python
from pathlib import Path
from PIL import Image

def extract_gif(gif_path, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    durations_ms = []

    with Image.open(gif_path) as gif:
        for index in range(gif.n_frames):
            gif.seek(index)
            durations_ms.append(gif.info.get("duration", 100))
            gif.convert("RGBA").save(
                output_dir / f"frame_{index:04d}.png"
            )

    return durations_ms
```

The Swipe Up GIF produced **12 PNGs at 480 × 480**, with these durations:

```python
[70, 60, 70, 70, 60, 70, 70, 60, 70, 70, 60, 60]
```

Its complete loop lasts **790 milliseconds**. The shipped package uses the filename prefix `swipe_`; the generalized extraction function above uses `frame_`.

For a production function, explicitly handle missing or zero durations according to your chosen policy, and reject a sequence whose total duration is zero. Use a separate output directory per animation to avoid leftover frames from earlier conversions.

## 2. Load the numbered PNG sequence

The Loader references the first PNG. Its clip settings describe the complete sequence:

```lua
PNGFrames = Loader {
    Clips = {
        Clip {
            ID = "Clip1",
            Filename = "/absolute/path/Frames/frame_0000.png",
            FormatID = "PNGFormat",

            StartFrame = 0,
            Length = 12,
            LengthSetManually = true,

            TrimIn = 0,
            TrimOut = 11,
            GlobalStart = 0,
            GlobalEnd = 1000000,

            ExtendFirst = 0,
            ExtendLast = 0,
            Loop = 1,
        },
    },
    Inputs = {
        ["Clip1.PNGFormat.PostMultiply"] = Input {
            Value = 1,
        },
    },
}
```

Parameterize `Filename`, `Length`, `TrimOut`, and `GlobalEnd`:

| Setting | Value |
|---|---|
| Filename | Absolute path to the first extracted PNG |
| Length | Number of extracted frames |
| TrimIn | 0 |
| TrimOut | Frame count − 1 |
| GlobalStart | 0 |
| GlobalEnd | 1000000 (extended playback range; TrimOut still limits the source frames) |

The files must load as a sequence rather than a single still image. Source frame indices are zero-based even if filenames use a different numbering convention.

## 3. Select the correct frame using TimeStretcher

A GIF can give each frame a different duration. Advancing one PNG per timeline frame would change the animation's timing.

Calculate the position within the GIF loop:

```text
phase_ms = (
    (time - comp.RenderStart)
    * 1000
    / TimelineFPS
    * Speed
    + Offset * 1000
) % total_duration_ms
```

Select the image whose time interval contains that position:

| Position within loop | PNG index |
|---|---:|
| 0–69 ms | 0 |
| 70–129 ms | 1 |
| 130–199 ms | 2 |
| 200–269 ms | 3 |
| 270–329 ms | 4 |
| 330–399 ms | 5 |
| 400–469 ms | 6 |
| 470–529 ms | 7 |
| 530–599 ms | 8 |
| 600–669 ms | 9 |
| 670–729 ms | 10 |
| 730–789 ms | 11 |

Modulo repeats the animation indefinitely. The expression returns an integer image index, switching between source frames without fractional interpolation. Playback is sampled at the timeline FPS; GIF boundaries cannot always fall exactly on a timeline frame.

Generate the nested Fusion expression with this Python function:

```python
def build_source_time_expression(durations_ms, tool="LoopTiming"):
    if not durations_ms or any(d <= 0 for d in durations_ms):
        raise ValueError("Frame durations must be positive")

    total_ms = sum(durations_ms)

    phase = (
        f"(((time-comp.RenderStart)*1000/"
        f"{tool}.TimelineFPS*{tool}.Speed"
        f"+{tool}.Offset*1000)%{total_ms})"
    )

    boundaries = []
    elapsed = 0

    for duration in durations_ms:
        elapsed += duration
        boundaries.append(elapsed)

    expression = str(len(durations_ms) - 1)

    for index in reversed(range(len(durations_ms) - 1)):
        expression = (
            f"iif({phase}<{boundaries[index]},"
            f"{index},{expression})"
        )

    return expression
```

Put the generated expression into the TimeStretcher's `SourceTime` input:

```lua
LoopTiming = TimeStretcher {
    Inputs = {
        Input = Input {
            SourceOp = "PNGFrames",
            Source = "Output",
        },
        SourceTime = Input {
            Expression = "...generated expression...",
        },

        Speed = Input { Value = 1 },
        TimelineFPS = Input { Value = 24 },
        Offset = Input { Value = 0 },
    },

    -- Define the numeric custom controls in UserControls:
    -- Speed, TimelineFPS, Offset.
}
```

## 4. Wrap both nodes in a group

Expose the TimeStretcher's custom controls through `InstanceInput`. Export its image through `InstanceOutput`:

```lua
SwipeUpLoop = GroupOperator {
    Inputs = ordered() {
        Speed = InstanceInput {
            SourceOp = "LoopTiming",
            Source = "Speed",
            Name = "Speed",
        },
        TimelineFPS = InstanceInput {
            SourceOp = "LoopTiming",
            Source = "TimelineFPS",
            Name = "Timeline FPS",
        },
        Offset = InstanceInput {
            SourceOp = "LoopTiming",
            Source = "Offset",
            Name = "Offset (seconds)",
        },
    },

    Outputs = {
        MainOutput1 = InstanceOutput {
            SourceOp = "LoopTiming",
            Source = "Output",
        },
    },

    Tools = ordered() {
        -- PNGFrames Loader definition
        -- LoopTiming TimeStretcher definition
    },
}
```

The snippets above illustrate the structure; the complete generated `.setting` is included below with its `UserControls` definitions.

The group references external PNG assets. It does not embed image pixels in the `.setting` file.

## 5. Local function interface

```python
def create_gif_loop_group(
    gif_path,
    output_dir,
    group_name="GIFLoop",
    timeline_fps=24,
    speed=1.0,
):
    # 1. Extract RGBA PNGs and collect durations.
    # 2. Generate the SourceTime expression.
    # 3. Fill a reusable .setting template.
    # 4. Write the .setting beside its Frames directory.
    # 5. Return the setting path and asset directory.
    ...
```

Suggested output structure:

- `AnimationName/Frames/frame_0000.png` through the final PNG.
- `AnimationName/AnimationName.setting`.
- Optional `AnimationName/timing.json`, containing frame durations and total loop duration.

Validate FPS as positive and finite, and use valid Fusion identifiers for generated node names. If changing the internal TimeStretcher name, update the expression's tool references too. Quote asset paths as Lua string literals, escaping quotes and backslashes; do not insert an unescaped path into the settings text.

The original installer asks for the first PNG and timeline FPS, substitutes them into the settings text, then calls `comp:Paste(settings)` inside an undo operation. For application integration, generate the correct path directly and omit that dialog. Include all PNG assets when transferring the group to another computer and relink paths there.

## 6. Controls and connections

| Control | Behavior |
|---|---|
| Speed = 1 | Original GIF timing |
| Speed = 2 | Twice as fast |
| Speed = 0.5 | Half speed |
| Speed = 0 | Freeze at the phase selected by Offset |
| Timeline FPS | Match the composition/timeline rate, including fractional rates such as 29.97 |
| Offset | Starting phase in source-animation seconds |

The generated loop is anchored to `comp.RenderStart`. To start at a chosen frame instead, add a StartFrame control and replace `comp.RenderStart` in the expression with that control.

Connect the group's output to a 2D Merge's foreground input. For a 3D scene, connect it to an ImagePlane3D, then connect the plane into the scene's Merge3D.

## 7. Validation performed and remaining check

- All 12 extracted RGBA frames matched the decoded GIF frames byte for byte, including alpha.
- The installer and generated settings passed Lua syntax/table parsing checks using Lua 5.4 with mocked Fusion constructors and composition methods.
- The timing expression selected the expected frames at interval boundaries and repeated at 790 and 1580 ms.
- Actual import and playback have **not** been tested in Resolve/Fusion, which was unavailable in the execution environment. Mocked Lua checks do not establish compatibility with Fusion's expression engine or Loader behavior.

Before integrating the template as verified, import it into your Fusion installation, inspect the Loader's 12-frame sequence, and test playback at your target timeline FPS, two speed values, and across a loop boundary.

## 8. Complete generated example

The following is the original Swipe Up `.setting`, including its full timing expression and custom controls. Replace `__FIRST_PNG__` with a correctly escaped path to `Frames/swipe_0000.png`, or substitute it through the installer. For other GIFs, regenerate the expression and update clip length settings.

```lua
{
 Tools = ordered() {
  SwipeUpLoop = GroupOperator {
   NameSet = true,
   Inputs = ordered() {
    Speed = InstanceInput { SourceOp = "LoopTiming", Source = "Speed", Name = "Speed", },
    TimelineFPS = InstanceInput { SourceOp = "LoopTiming", Source = "TimelineFPS", Name = "Timeline FPS", },
    Offset = InstanceInput { SourceOp = "LoopTiming", Source = "Offset", Name = "Offset (seconds)", },
   },
   Outputs = { MainOutput1 = InstanceOutput { SourceOp = "LoopTiming", Source = "Output", }, },
   ViewInfo = GroupInfo { Pos = { 0, 0 }, },
   Tools = ordered() {
    PNGFrames = Loader {
     Clips = {
      Clip {
       ID = "Clip1", Filename = "__FIRST_PNG__", FormatID = "PNGFormat",
       StartFrame = 0, Length = 12, LengthSetManually = true,
       TrimIn = 0, TrimOut = 11, ExtendFirst = 0, ExtendLast = 0,
       Loop = 1, AspectMode = 0, Depth = 0, TimeCode = 0,
       GlobalStart = 0, GlobalEnd = 1000000,
      },
     },
     Inputs = { ["Clip1.PNGFormat.PostMultiply"] = Input { Value = 1, }, },
     ViewInfo = OperatorInfo { Pos = { 0, 0 }, },
    },
    LoopTiming = TimeStretcher {
     Inputs = {
      Input = Input { SourceOp = "PNGFrames", Source = "Output", },
      SourceTime = Input { Expression = "iif((((time-comp.RenderStart)*1000/LoopTiming.TimelineFPS*LoopTiming.Speed+LoopTiming.Offset*1000)%790)<70,0,iif((((time-comp.RenderStart)*1000/LoopTiming.TimelineFPS*LoopTiming.Speed+LoopTiming.Offset*1000)%790)<130,1,iif((((time-comp.RenderStart)*1000/LoopTiming.TimelineFPS*LoopTiming.Speed+LoopTiming.Offset*1000)%790)<200,2,iif((((time-comp.RenderStart)*1000/LoopTiming.TimelineFPS*LoopTiming.Speed+LoopTiming.Offset*1000)%790)<270,3,iif((((time-comp.RenderStart)*1000/LoopTiming.TimelineFPS*LoopTiming.Speed+LoopTiming.Offset*1000)%790)<330,4,iif((((time-comp.RenderStart)*1000/LoopTiming.TimelineFPS*LoopTiming.Speed+LoopTiming.Offset*1000)%790)<400,5,iif((((time-comp.RenderStart)*1000/LoopTiming.TimelineFPS*LoopTiming.Speed+LoopTiming.Offset*1000)%790)<470,6,iif((((time-comp.RenderStart)*1000/LoopTiming.TimelineFPS*LoopTiming.Speed+LoopTiming.Offset*1000)%790)<530,7,iif((((time-comp.RenderStart)*1000/LoopTiming.TimelineFPS*LoopTiming.Speed+LoopTiming.Offset*1000)%790)<600,8,iif((((time-comp.RenderStart)*1000/LoopTiming.TimelineFPS*LoopTiming.Speed+LoopTiming.Offset*1000)%790)<670,9,iif((((time-comp.RenderStart)*1000/LoopTiming.TimelineFPS*LoopTiming.Speed+LoopTiming.Offset*1000)%790)<730,10,11)))))))))))", },
      Speed = Input { Value = 1, },
      TimelineFPS = Input { Value = 24, },
      Offset = Input { Value = 0, },
     },
     UserControls = ordered() {
      Speed = { LINKS_Name = "Speed", LINKID_DataType = "Number", INPID_InputControl = "SliderControl", INP_Default = 1, INP_MinScale = 0, INP_MaxScale = 4, INP_MinAllowed = 0, INP_MaxAllowed = 100, ICS_ControlPage = "Controls", },
      TimelineFPS = { LINKS_Name = "Timeline FPS", LINKID_DataType = "Number", INPID_InputControl = "SliderControl", INP_Default = 24, INP_MinScale = 1, INP_MaxScale = 60, INP_MinAllowed = 1, INP_MaxAllowed = 240, ICS_ControlPage = "Controls", },
      Offset = { LINKS_Name = "Offset (seconds)", LINKID_DataType = "Number", INPID_InputControl = "SliderControl", INP_Default = 0, INP_MinScale = 0, INP_MaxScale = 0.79, INP_MinAllowed = 0, INP_MaxAllowed = 100000, ICS_ControlPage = "Controls", },
     },
     ViewInfo = OperatorInfo { Pos = { 220, 0 }, },
    },
   },
  },
 },
 ActiveTool = "SwipeUpLoop",
}
```
