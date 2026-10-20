local env=setmetatable({ordered=function()return function(t)return t end end},{__index=function(_,k)return function(t)t.kind=k;return t end end})
local function read(path)
 local f=assert(io.open(path));local s=f:read('*a'):gsub('ofx%.com%.blackmagicdesign%.resolvefx%.Transform','OFXTransform');f:close()
 local fn=assert(loadstring('return '..s));setfenv(fn,env);return fn().Tools
end
local b,a=read(arg[1]),read(arg[2])
assert(a.MultiMerge1.Inputs.Background.SourceOp=='Main_Transparent_Background')
assert(a.Main_Transparent_Background.Inputs.TopLeftAlpha.Value==0)
assert(a.MultiMerge1.Inputs['Layer6.Foreground'].SourceOp=='Left_Stack2_Main_Placement')
assert(a.Left_Blur_Depth_Placement.Inputs.Background.SourceOp=='Left_Stack1_Background')
assert(a.object_1_right.Inputs.Background.SourceOp=='Background2')
local order=a.MultiMerge1.Inputs.LayerOrder.Value[1]
assert(order[0]==6)
local originalOrder=b.MultiMerge1.Inputs.LayerOrder.Value[1]
for i=0,#originalOrder do assert(order[i+1]==originalOrder[i]) end
local changes={}
local ignored={ViewInfo=true,CtrlWZoom=true,Comments=true}
local function eq(x,y,path)
 if type(x)~=type(y) then changes[#changes+1]=path..' type';return end
 if type(x)~='table' then if x~=y then changes[#changes+1]=path..' '..tostring(x)..' -> '..tostring(y) end;return end
 for k,v in pairs(x)do if not ignored[k]then eq(v,y[k],path..'.'..tostring(k))end end
 for k in pairs(y)do if not ignored[k] and x[k]==nil then changes[#changes+1]=path..'.'..tostring(k)..' added'end end
end
-- Deliberate wiring/order changes; normalize native spline naming.
a.MultiMerge1.Inputs.Background=b.MultiMerge1.Inputs.Background
a.MultiMerge1.Inputs.LayerOrder=b.MultiMerge1.Inputs.LayerOrder
a.MultiMerge1.Inputs['Layer6.Foreground']=nil
a.MultiMerge1.Inputs.LayerName6=b.MultiMerge1.Inputs.LayerName6
a.Left_Blur_Depth_Placement.Inputs.Background=b.Left_Blur_Depth_Placement.Inputs.Background
local rs=a.object1_right.Inputs.Displacement.SourceOp
local oldrs=b.object1_right.Inputs.Displacement.SourceOp
a.object1_right.Inputs.Displacement.SourceOp=oldrs
a[oldrs]=a[rs]
for name,t in pairs(b)do eq(t,a[name],name)end
for _,s in ipairs(changes)do print(s)end
assert(#changes==0,'Unexpected changes: '..#changes)
print('PASS: main transparent canvas, left canvas, foreground composite and layer order correct; all original tools and motion parameters preserved.')
