local base='/Users/naseemtoumeh/edit-projects/davinvi-resolve/experement/ArchiveCarousel_type_2/backups/live_20261019_223905/'
local pm=resolve:GetProjectManager();local p=assert(pm:GetCurrentProject());assert(p:GetName()=='china sv usa')
local item=p:GetTimelineByIndex(1):GetItemListInTrack('video',2)[14];local c=item:GetFusionCompByIndex(1)
local ids={Media_file4='6c9d219b-1394-4918-a2d5-fb65711b2bc3',Right_Stack1_Vintage8mm='85583b41-424d-4433-9be0-3060e9420f5d',Right_Stack2_Vintage8mm='85583b41-424d-4433-9be0-3060e9420f5d'}
local data={}
for name,id in pairs(ids)do
 local t=assert(c:FindTool(name))
 t:SetInput('MediaSource','MediaPool')
 t:SetInput('MediaID',id)
 t:SetInput('Layer','')
 t:SetInput('Loop',1)
 t:SetInput('GlobalIn',0);t:SetInput('GlobalOut',837)
 t:SetInput('ClipTimeStart',0);t:SetInput('ClipTimeEnd',0)
 data[name]={source=t:GetInput('MediaSource',0),id=t:GetInput('MediaID',0),attrs=t:GetAttrs()}
end
c:SetData('RightRowsRelink',data)
assert(item:ExportFusionComp(base..'right_rows_relinked.comp',1))
c.CurrentTime=36;c.CurrentFrame:ViewOn(c:FindTool('MediaOut1'),2)
assert(pm:SaveProject())
