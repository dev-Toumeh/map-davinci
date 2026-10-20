local base='/Users/naseemtoumeh/edit-projects/davinvi-resolve/experement/ArchiveCarousel_type_2/backups/live_20261019_223905/'
local pm=resolve:GetProjectManager();local p=assert(pm:GetCurrentProject());assert(p:GetName()=='china sv usa')
local item=assert(p:GetTimelineByIndex(1):GetItemListInTrack('video',2)[14]);assert(item:GetName()=='china-wrong-1-child-old')
local c=assert(item:GetFusionCompByIndex(1));local main=assert(c:FindTool('MultiMerge1'))
for _,name in ipairs({'MultiMerge2','MultiMerge3','MediaIn1','MediaIn2'})do assert(not c:FindTool(name),name..' unexpectedly remains')end
local old=c:FindTool('Background2')
if old then
 for _,tool in pairs(c:GetToolList(false))do
  for _,input in pairs(tool:GetInputList())do
   local output=input:GetConnectedOutput()
   assert(not output or output:GetTool()~=old,'Old background is still used by '..tool.Name)
  end
 end
 c:StartUndo('Remove unused original background');old:Delete();c:EndUndo(true)
end
assert(c:FindTool('object_1_right').Background:GetConnectedOutput():GetTool()==c:FindTool('Background2_1'))
c:FindTool('Main_Transparent_Background'):SetAttrs({TOOLS_Comments=''})
c:SetData('BackgroundFixError',nil)
c.CurrentFrame.FlowView:Select();c:SetActiveTool(main)
assert(item:ExportFusionComp(base..'clean_template.comp',1));assert(pm:SaveProject())
print('CLEAN_TEMPLATE_SAVED')
