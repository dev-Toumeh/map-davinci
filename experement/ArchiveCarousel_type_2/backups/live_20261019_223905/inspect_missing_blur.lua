local p=resolve:GetProjectManager():GetCurrentProject();assert(p:GetName()=='china sv usa')
local item=p:GetTimelineByIndex(1):GetItemListInTrack('video',2)[14]
local c=item:GetFusionCompByIndex(1);local data={}
local values={}
for _,name in ipairs({'object1_left','Left_Blur_Depth_Path','object2_left','Left_Stack2_Blur_Path'})do
 local t=assert(c:FindTool(name));values[name]=t:GetInput('Displacement',0)
end
c:SetData('LivePathValuesBefore',values)
local expressions={Left_Blur_Depth_Path='object1_left.Displacement + 0.25',object2_left='object1_left.Displacement - 0.50',Left_Stack2_Blur_Path='object1_left.Displacement - 0.25'}
for name,expr in pairs(expressions)do
 local input=c:FindTool(name).Displacement
 input:SetExpression(nil)
 input:SetExpression(expr)
end
values={}
for _,name in ipairs({'object1_left','Left_Blur_Depth_Path','object2_left','Left_Stack2_Blur_Path'})do
 values[name]=c:FindTool(name):GetInput('Displacement',0)
end
c:SetData('LivePathValuesAfter',values)
for _,name in ipairs({'MultiMerge1','Left_Blur_Depth_Placement','Left_Stack2_Blur_Placement','Left_Stack2_Main_Placement'})do
 local t=assert(c:FindTool(name));local d={}
 for _,inp in pairs(t:GetInputList())do
  local a=inp:GetAttrs();local id=a.INPS_ID
  if id and (name~='MultiMerge1' or id:find('Layer6',1,true) or id=='LayerOrder') then
   local value=t:GetInput(id,0)
   if type(value)=='number' or type(value)=='string' or type(value)=='table' or type(value)=='boolean' then d[id]=value end
  end
 end
 data[name]=d
end
c:SetData('BlurDiagnostics',data)
assert(item:ExportFusionComp('/Users/naseemtoumeh/edit-projects/davinvi-resolve/experement/ArchiveCarousel_type_2/backups/live_20261019_223905/before_blur_restore.comp',1))
