local env=setmetatable({ordered=function()return function(t)return t end end},{__index=function(_,k)return function(t)t.kind=k;return t end end})
local function read(path)
 local f=assert(io.open(path));local s=f:read('*a'):gsub('ofx%.com%.blackmagicdesign%.resolvefx%.Transform','OFXTransform');f:close()
 local fn=assert(loadstring('return '..s));setfenv(fn,env);return fn().Tools
end
local before,after=read(arg[1]),read(arg[2])
for _,name in ipairs({'MultiMerge2','MultiMerge3','MediaIn1','MediaIn2','Background2'})do
 assert(before[name]);assert(not after[name],'Legacy tool remains '..name);before[name]=nil
end
before.MultiMerge1.Inputs['Layer2.Foreground']=nil;before.MultiMerge1.Inputs['Layer5.Foreground']=nil
local function eq(a,b,path)
 assert(type(a)==type(b),'Type changed '..path)
 if type(a)~='table'then assert(a==b,'Value changed '..path);return end
 for k,v in pairs(a)do if k~='ViewInfo' and k~='CtrlWZoom'then eq(v,b[k],path..'.'..tostring(k))end end
 for k in pairs(b)do if k~='ViewInfo' and k~='CtrlWZoom'then assert(a[k]~=nil,'Added '..path..'.'..tostring(k))end end
end
eq(before,after,'Tools')
print('PASS: only five specified legacy nodes and two obsolete final foreground links removed; every remaining tool, parameter, key and connection preserved.')
