local p=resolve:GetProjectManager():GetCurrentProject();assert(p:GetName()=='china sv usa')
local item=p:GetTimelineByIndex(1):GetItemListInTrack('video',2)[14];assert(item:GetName()=='china-wrong-1-child-old')
local c=item:GetFusionCompByIndex(1);local info={frame=c.CurrentTime}
for _,name in ipairs({'Media_file2','Media_file2_Frame','object_2_left','Left_Stack2_Main_Placement','object2_left','Left_Stack2_Blur_Path','Left_Blur_Depth_Path','object1_left','MultiMerge1'})do
 local t=c:FindTool(name);local d={exists=t~=nil}
 if t then
  d.attrs=t:GetAttrs()
  for _,id in ipairs({'Displacement','Blend','Size','Center','MediaID','LayerOrder','Layer6.Blend','Layer6.Size'})do
   local value=t:GetInput(id,c.CurrentTime)
   if type(value)=='number' or type(value)=='string' or type(value)=='table' then d[id]=value end
  end
 end
 info[name]=d
end
c:SetData('SecondObjectInspection',info)
assert(item:ExportFusionComp('/Users/naseemtoumeh/edit-projects/davinvi-resolve/experement/ArchiveCarousel_type_2/backups/live_20261019_223905/before_second_object_visibility.comp',1))
