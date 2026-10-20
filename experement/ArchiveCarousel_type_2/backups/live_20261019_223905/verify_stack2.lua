local env=setmetatable({ordered=function() return function(t) return t end end},{__index=function(_,k) return function(t) t.__kind=k;return t end end})
local function read(path)
 local f=assert(io.open(path));local s=f:read('*a'):gsub('ofx%.com%.blackmagicdesign%.resolvefx%.Transform','OFXTransform');f:close()
 local chunk=assert(loadstring('return '..s));setfenv(chunk,env);return chunk()
end
local before,after=read(arg[1]),read(arg[2])
local function equal(a,b,path)
 assert(type(a)==type(b),'Type changed: '..path)
 if type(a)~='table' then assert(a==b,'Changed: '..path);return end
 for k,v in pairs(a) do if k~='CtrlWZoom' and k~='ViewInfo' then equal(v,b[k],path..'.'..tostring(k)) end end
 for k in pairs(b) do if k~='CtrlWZoom' and k~='ViewInfo' then assert(a[k]~=nil,'Added: '..path..'.'..tostring(k)) end end
end
local t=after.Tools
assert(t.MultiMerge1.Inputs.Background.SourceOp=='Left_Stack2_Main_Placement')
local original=t.MultiMerge1.Inputs.Background
t.MultiMerge1.Inputs.Background=before.Tools.MultiMerge1.Inputs.Background
for name,tool in pairs(before.Tools) do equal(tool,assert(t[name]),name) end
t.MultiMerge1.Inputs.Background=original
assert(t.Media_file2.Inputs.MediaID.Value=='f4d15345-3ab0-4b34-abd3-13c63db99841')
assert(t.Media_file2_Frame.Inputs.Source.SourceOp=='Media_file2')
assert(t.object_2_left.Inputs['Layer1.Foreground'].SourceOp=='Media_file2_Frame')
assert(t.object_2_left.Inputs['Layer2.Foreground'].SourceOp=='MediaIn1')
assert(t.object2_left.Inputs.Displacement.Expression=='object1_left.Displacement - 0.50')
assert(t.Left_Stack2_Blur_Path.Inputs.Displacement.Expression=='object1_left.Displacement - 0.25')
assert(t.Left_Stack2_Blur_Placement.Inputs.Background.SourceOp=='Left_Blur_Depth_Placement')
assert(t.Left_Stack2_Main_Placement.Inputs.Background.SourceOp=='Left_Stack2_Blur_Placement')
local active={}
local function visit(name)
 assert(not active[name],'Cycle: '..name)
 local tool=assert(t[name],'Missing tool: '..name);active[name]=true
 for _,inp in pairs(tool.Inputs or {}) do
  if type(inp)=='table' and inp.SourceOp and t[inp.SourceOp] then visit(inp.SourceOp) end
 end
 active[name]=nil
end
visit('MediaOut1')
print('PASS: all original tools, image links, paths and timings unchanged except final background extension; image3 and both offsets correct; no output cycles.')
