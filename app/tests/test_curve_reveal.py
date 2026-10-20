"""Static Fusion validation; not a substitute for a Resolve render."""
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "app/fusion/templates/nodes/curve-reveal-2d.setting"
FUSION = ROOT / "exports/pakistan_iran_afghanistan_india_2/fusion"


@unittest.skipUnless(shutil.which("luajit"), "LuaJIT required")
class CurveRevealTests(unittest.TestCase):
    def test_template_and_demo_links_timing_and_preservation(self):
        script = r'''
local env=setmetatable({ordered=function() return function(t) return t end end},
 {__index=function(_,k) return function(t) t.__kind=k; return t end end})
local function read(path)
 local f=assert(io.open(path)); local chunk=assert(loadstring("return "..f:read("*a"))); f:close()
 setfenv(chunk,env); return chunk()
end
local template=read(arg[1])
local demo=read(arg[2])
local original=read(arg[3])
local g=template.Tools.Curve_Reveal_2D
assert(g.__kind=="GroupOperator")
assert(g.ViewInfo.Pos[1]==0 and g.ViewInfo.Pos[2]==0)
assert(g.Tools.Reveal_Path.Inputs.Solid.Value==0)
assert(g.Tools.Reveal_Path.Inputs.UseFrameFormatSettings.Value==0)
assert(g.Tools.Reveal_Canvas.Inputs.TopLeftAlpha.Value==0)
assert(g.Tools.Reveal_Path.Inputs.Polyline.Value.Closed==false)
for _,tool in pairs(g.Tools) do
 if type(tool)=="table" and tool.Inputs then
  for _,input in pairs(tool.Inputs) do
   if input.SourceOp then assert(g.Tools[input.SourceOp], input.SourceOp) end
  end
 end
end
for _,input in pairs(g.Inputs) do
 local tool=assert(g.Tools[input.SourceOp])
 assert(tool.Inputs[input.Source] or tool.UserControls[input.Source])
end
local dg=demo.Tools.Curve_Reveal_2D
assert(dg.Tools.Reveal_Image.Inputs.Input.SourceOp=="MediaIn7")
assert(dg.Tools.Reveal_Output.Inputs.StartFrame.Value==429)
assert(demo.Tools.IND_Local_Elements_MultiMerge.Inputs["Layer2.Foreground"].SourceOp=="Curve_Reveal_2D")
local function equal(a,b)
 if type(a)~=type(b) then return false end
 if type(a)~="table" then return a==b end
 for k,v in pairs(a) do if not equal(v,b[k]) then return false end end
 for k in pairs(b) do if a[k]==nil then return false end end
 return true
end
for name,tool in pairs(original.Tools) do
 if name~="IND_Local_Elements_MultiMerge" and name~="IND_Local_Elements_MultiMergeLayerOrder" then
  assert(equal(tool,demo.Tools[name]), "Unexpected changed tool: "..name)
 end
end
local before=original.Tools.IND_Local_Elements_MultiMerge.Inputs
local after=demo.Tools.IND_Local_Elements_MultiMerge.Inputs
for k,v in pairs(before) do
 if k~="Layer2.Foreground" then assert(equal(v,after[k]), k) end
end
local Reveal_Output={StartFrame=429,Duration=24,Reverse=0}
local Reveal_Path={}
local time=0
local iif=function(c,a,b) if c then return a else return b end end
local function evaluate(expression)
 local f=assert(loadstring("return "..expression))
 setfenv(f,{min=math.min,max=math.max,time=time,iif=iif,Reveal_Output=Reveal_Output,Reveal_Path=Reveal_Path})
 return f()
end
for _,sample in ipairs({{428,0},{429,0},{441,0.5},{453,1},{600,1}}) do
 time=sample[1]
 Reveal_Output.Progress=evaluate(dg.Tools.Reveal_Output.Inputs.Progress.Expression)
 assert(math.abs(Reveal_Output.Progress-sample[2])<0.00001)
 Reveal_Path.WriteLength=evaluate(dg.Tools.Reveal_Path.Inputs.WriteLength.Expression)
 assert(Reveal_Path.WriteLength>=0 and Reveal_Path.WriteLength<=1)
 for _,reverse in ipairs({0,1}) do
  Reveal_Output.Reverse=reverse
  local position=evaluate(dg.Tools.Reveal_Path.Inputs.WritePosition.Expression)
  assert(math.abs(position-(reverse==1 and 1-Reveal_Path.WriteLength or 0))<0.00001)
 end
 local mix=evaluate(dg.Tools.Reveal_Complete.Inputs.Mix.Expression)
 assert(mix>=0 and mix<=1)
 if time>=453 then assert(mix==1) end
end
'''
        result = subprocess.run(
            ["luajit", "-", str(TEMPLATE), str(FUSION / "gif-group-curve-reveal-demo.comp"),
             str(FUSION / "gif-group-backup.comp")],
            input=script, text=True, capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
