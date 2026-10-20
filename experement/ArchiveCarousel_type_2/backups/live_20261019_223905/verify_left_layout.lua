local env=setmetatable({ordered=function()return function(t)return t end end},{__index=function(_,k)return function(t)t.kind=k;return t end end})
local function read(path)
 local f=assert(io.open(path));local s=f:read('*a'):gsub('ofx%.com%.blackmagicdesign%.resolvefx%.Transform','OFXTransform');f:close()
 local fn=assert(loadstring('return '..s));setfenv(fn,env);return fn().Tools
end
local b,a=read(arg[1]),read(arg[2])
local function equal(x,y,path)
 assert(type(x)==type(y),'Type changed '..path)
 if type(x)~='table' then assert(x==y,'Changed '..path);return end
 for k,v in pairs(x) do if k~='ViewInfo' and k~='CtrlWZoom' then equal(v,y[k],path..'.'..tostring(k)) end end
 for k in pairs(y) do if k~='ViewInfo' and k~='CtrlWZoom' then assert(x[k]~=nil,'Added '..path..'.'..tostring(k)) end end
end
for i,name in ipairs({'object_1_left','object_2_left'}) do
 local card=assert(a[name])
 assert(card.Inputs.Background.SourceOp=='Left_Stack'..i..'_Background')
 assert(card.Inputs['Layer2.Foreground'].SourceOp=='Left_Stack'..i..'_Vintage8mm')
 card.Inputs.Background=b[name].Inputs.Background
 card.Inputs['Layer2.Foreground']=b[name].Inputs['Layer2.Foreground']
 local bg,film=a['Left_Stack'..i..'_Background'],a['Left_Stack'..i..'_Vintage8mm']
 assert(not bg.SourceOp and not film.SourceOp,'Instances not independent')
 equal(b.Background2.Inputs,bg.Inputs,'Background clone '..i)
 local original=b.MediaIn1.Inputs
 local l,r=original.LeftAudio,original.RightAudio;original.LeftAudio=nil;original.RightAudio=nil
 equal(original,film.Inputs,'Film clone '..i)
 original.LeftAudio=l;original.RightAudio=r
end
for name,t in pairs(b) do equal(t,assert(a[name]),name) end
print('PASS: independent matching background/film nodes; all original settings, keyframes, paths and other connections preserved. Only four card source links and flow layout changed.')
