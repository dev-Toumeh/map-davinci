-- Run in the current Fusion composition. No existing nodes are changed.
local composition = comp or (fu and fu:GetCurrentComp())
if not composition then error("Open a Fusion composition first.") end
local fps = composition:GetPrefs("Comp.FrameFormat.Rate") or 30
local answer = composition:AskUser("Add Swipe Up Loop", {
 { "FirstPNG", "FileBrowse", Name = "Select Frames/swipe_0000.png", Default = "", },
 { "FPS", "Slider", Name = "Timeline FPS", Default = fps, Min = 1, Max = 240, },
})
if not answer then return end
local filename = answer.FirstPNG
if not filename or filename == "" then error("Select swipe_0000.png from the extracted Frames folder.") end
local check = io.open(filename, "rb")
if not check then error("Cannot read selected PNG: " .. filename) end
check:close()
filename = filename:gsub("\\", "/")
if not filename:match("swipe_0000%.png$") then error("Select swipe_0000.png, the first frame.") end
local directory = filename:match("^(.*)/[^/]+$")
for index = 0, 11 do
 local path = directory .. "/" .. string.format("swipe_%04d.png", index)
 local frame = io.open(path, "rb")
 if not frame then error("Missing frame: " .. path) end
 frame:close()
end
local settings = [==[
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
      TimelineFPS = Input { Value = 30, },
      Offset = Input { Value = 0, },
     },
     UserControls = ordered() {
      Speed = { LINKS_Name = "Speed", LINKID_DataType = "Number", INPID_InputControl = "SliderControl", INP_Default = 1, INP_MinScale = 0, INP_MaxScale = 4, INP_MinAllowed = 0, INP_MaxAllowed = 100, ICS_ControlPage = "Controls", },
      TimelineFPS = { LINKS_Name = "Timeline FPS", LINKID_DataType = "Number", INPID_InputControl = "SliderControl", INP_Default = 30, INP_MinScale = 1, INP_MaxScale = 60, INP_MinAllowed = 1, INP_MaxAllowed = 240, ICS_ControlPage = "Controls", },
      Offset = { LINKS_Name = "Offset (seconds)", LINKID_DataType = "Number", INPID_InputControl = "SliderControl", INP_Default = 0, INP_MinScale = 0, INP_MaxScale = 0.79, INP_MinAllowed = 0, INP_MaxAllowed = 100000, ICS_ControlPage = "Controls", },
     },
     ViewInfo = OperatorInfo { Pos = { 220, 0 }, },
    },
   },
  },
 },
 ActiveTool = "SwipeUpLoop",
}

]==]
local quoted = string.format("%q", filename)
settings = settings:gsub('"__FIRST_PNG__"', function() return quoted end)
settings = settings:gsub("TimelineFPS = Input { Value = 30, }", function()
 return "TimelineFPS = Input { Value = " .. tostring(answer.FPS) .. ", }"
end)
composition:StartUndo("Add Swipe Up Loop")
composition:Lock()
local success, result = pcall(function() return composition:Paste(settings) end)
composition:Unlock()
composition:EndUndo(success)
if not success then error(result) end
print("SwipeUpLoop added. Connect its output to your Merge or ImagePlane3D. Speed 1 = original GIF timing.")
