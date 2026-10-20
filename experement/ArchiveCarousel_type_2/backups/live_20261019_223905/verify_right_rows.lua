local env=setmetatable({ordered=function()return function(t)return t end end},{__index=function(_,k)return function(t)t.kind=k;return t end end})
local function read(path)
 local f=assert(io.open(path));local s=f:read('*a'):gsub('ofx%.com%.blackmagicdesign%.resolvefx%.Transform','OFXTransform');f:close()
 local fn=assert(loadstring('return '..s));setfenv(fn,env);return fn().Tools
end
local b,a=read(arg[1]),read(arg[2])
local function equal(x,y,path)
 assert(type(x)==type(y),'Type changed '..path)
 if type(x)~='table'then assert(x==y,'Changed '..path..' '..tostring(x)..' -> '..tostring(y));return end
 for k,v in pairs(x)do if k~='CtrlWZoom'then equal(v,y[k],path..'.'..tostring(k))end end
 for k in pairs(y)do if k~='CtrlWZoom'then assert(x[k]~=nil,'Added '..path..'.'..tostring(k))end end
end
assert(a.Media_file4.Inputs.MediaID.Value=='6c9d219b-1394-4918-a2d5-fb65711b2bc3')
assert(a.Media_file4.Inputs.MediaSource.Value[1]=='MediaPool')
assert(a.object_2_right.Inputs.Background.SourceOp=='Right_Stack2_Background')
assert(a.MultiMerge1.Inputs.Background.SourceOp=='Main_Transparent_Background')
assert(a.MultiMerge1.Inputs['Layer7.Foreground'].SourceOp=='Right_Stack2_Main_Placement')
local order=a.MultiMerge1.Inputs.LayerOrder.Value[1];local old=b.MultiMerge1.Inputs.LayerOrder.Value[1]
assert(order[0]==6 and order[1]==7)
for i=1,#old do assert(order[i+1]==old[i])end
a.MultiMerge1.Inputs.LayerOrder=b.MultiMerge1.Inputs.LayerOrder
a.MultiMerge1.Inputs.LayerName7=b.MultiMerge1.Inputs.LayerName7;a.MultiMerge1.Inputs['Layer7.Foreground']=nil
a.object_1_right.Inputs['Layer2.Foreground']=b.object_1_right.Inputs['Layer2.Foreground']
-- Native settings reload may rename attached displacement splines; normalize by their owners.
for _,owner in ipairs({'object1_left','object1_right'})do
 local beforeName=b[owner].Inputs.Displacement.SourceOp;local afterName=a[owner].Inputs.Displacement.SourceOp
 a[beforeName]=a[afterName];a[owner].Inputs.Displacement.SourceOp=beforeName
end
for name,t in pairs(b)do
 local current=assert(a[name],'Missing original tool '..name)
 if t.Inputs then equal(t.Inputs,current.Inputs,name..'.Inputs')end
 if t.KeyFrames then equal(t.KeyFrames,current.KeyFrames,name..'.KeyFrames')end
end
print('PASS: all original inputs and motion keys preserved except right film clone and one foreground slot/order extension; image4 and main canvas correct.')
