local base='/Users/naseemtoumeh/edit-projects/davinvi-resolve/experement/ArchiveCarousel_type_2/backups/live_20261019_223905/'
local pm=resolve:GetProjectManager();local p=pm:GetCurrentProject();assert(p:GetName()=='china sv usa')
local item=p:GetTimelineByIndex(1):GetItemListInTrack('video',2)[14];local c=item:GetFusionCompByIndex(1)
local media=c:FindTool('Media_file4');assert(media:GetInput('MediaID',36)=='6c9d219b-1394-4918-a2d5-fb65711b2bc3')
assert(media:GetInput('MediaSource',36)=='MediaPool')
assert(c:FindTool('object_2_right').Background:GetConnectedOutput():GetTool()==c:FindTool('Right_Stack2_Background'))
assert(c:FindTool('MultiMerge1').Background:GetConnectedOutput():GetTool()==c:FindTool('Main_Transparent_Background'))
assert(c:FindTool('MultiMerge1')['Layer7.Foreground']:GetConnectedOutput():GetTool()==c:FindTool('Right_Stack2_Main_Placement'))
local names={'Left_Blur_Depth_Path','object2_left','Right_Stack1_Blur_Path','Right_Stack2_Blur_Path','object2_right'}
for _,name in ipairs(names)do
 for _,f in ipairs({0,10,36,74,84})do assert(type(c:FindTool(name):GetInput('Displacement',f))=='number',name..' failed at '..f)end
end
c:SetData('RightRowsError',nil);c:SetData('RightRowsStage','built; second-row timing pending user choice')
c:SetData('BackgroundFixError',nil)
c.CurrentFrame:ViewOn(c:FindTool('object_2_right'),2)
c:SetActiveTool(c:FindTool('object_2_right'));c:GetPreviewList().RightView.View:SetScale(0)
assert(item:ExportFusionComp(base..'right_rows_verified.comp',1))
assert(pm:SaveProject())
