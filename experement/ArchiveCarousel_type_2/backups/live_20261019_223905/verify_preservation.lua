local env=setmetatable({ordered=function() return function(t) return t end end},{__index=function(_,k) return function(t) t.__kind=k;return t end end})
local function read(path)
 local f=assert(io.open(path));local source=f:read('*a'):gsub('ofx%.com%.blackmagicdesign%.resolvefx%.Transform','OFXTransform');f:close();local chunk=assert(loadstring('return '..source));setfenv(chunk,env);return chunk()
end
local before=read(arg[1]);local after=read(arg[2])
local function equal(a,b,path)
 assert(type(a)==type(b),'Type changed: '..path)
 if type(a)~='table' then assert(a==b,'Value changed: '..path);return end
 for k,v in pairs(a) do if k~='CtrlWZoom' then equal(v,b[k],path..'.'..tostring(k)) end end
 for k in pairs(b) do if k~='CtrlWZoom' then assert(a[k]~=nil,'Added field: '..path..'.'..tostring(k)) end end
end
for name,tool in pairs(before.Tools) do
 assert(after.Tools[name],'Original tool removed: '..name)
 if name~='object_1_left' and name~='MultiMerge1' then equal(tool,after.Tools[name],name) end
end
for _,name in ipairs({'object_1_left','MultiMerge1'}) do
 local b=before.Tools[name];local a=after.Tools[name]
 for key,value in pairs(b) do
  if key=='Inputs' then
   for id,input in pairs(value) do
    if not(name=='object_1_left' and id=='Layer3.Foreground') and not(name=='MultiMerge1' and id=='Background') then equal(input,a.Inputs[id],name..'.Inputs.'..id) end
   end
  elseif key~='CtrlWZoom' then equal(value,a[key],name..'.'..key) end
 end
end
local t=after.Tools
assert(not(t.object_1_left.Inputs['Layer3.Foreground'] or {}).SourceOp)
assert(t.MultiMerge1.Inputs.Background.SourceOp=='Left_Blur_Depth_Placement')
assert(t.MultiMerge1.Inputs['Layer4.Foreground'].SourceOp=='object_1_left')
assert(t.Left_Blur_Depth.Inputs.Input.SourceOp=='object_1_left')
assert(t.Left_Blur_Depth_Placement.Inputs.Background.SourceOp=='Background2')
assert(t.Left_Blur_Depth_Placement.Inputs.Foreground.SourceOp=='Left_Blur_Depth')
assert(t.Left_Blur_Depth_Placement.Inputs.Center.SourceOp=='Left_Blur_Depth_Path')
assert(t.Left_Blur_Depth_Path.Inputs.PolyLine.SourceOp=='Publish1')
assert(t.Left_Blur_Depth_Path.Inputs.Displacement.Expression=='object1_left.Displacement + 0.08')
print('PASS: all original tools and keyframes preserved; only two original connections changed; blurred full card has a separate shared-curve path behind the final composite.')
