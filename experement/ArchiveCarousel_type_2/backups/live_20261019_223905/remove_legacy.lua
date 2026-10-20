local base='/Users/naseemtoumeh/edit-projects/davinvi-resolve/experement/ArchiveCarousel_type_2/backups/live_20261019_223905/'
local pm=resolve:GetProjectManager();local p=assert(pm:GetCurrentProject());assert(p:GetName()=='china sv usa')
local item=assert(p:GetTimelineByIndex(1):GetItemListInTrack('video',2)[14]);assert(item:GetName()=='china-wrong-1-child-old')
local c=assert(item:GetFusionCompByIndex(1));local main=assert(c:FindTool('MultiMerge1'))
local names={'MultiMerge2','MultiMerge3','MediaIn1','MediaIn2'}
for _,name in ipairs(names)do assert(c:FindTool(name),'Missing legacy tool '..name)end
assert(main['Layer2.Foreground']:GetConnectedOutput():GetTool()==c:FindTool('MultiMerge3'))
assert(main['Layer5.Foreground']:GetConnectedOutput():GetTool()==c:FindTool('MultiMerge2'))
for _,name in ipairs({'MultiMerge2','MultiMerge3'})do
 assert(not c:FindTool(name)['Layer1.Foreground']:GetConnectedOutput(),'Legacy card gained content; stop')
end
assert(item:ExportFusionComp(base..'before_legacy_cleanup_apply.comp',1))
c:StartUndo('Remove obsolete empty card branches');c:Lock()
local ok,err=pcall(function()
 main:ConnectInput('Layer2.Foreground',nil);main:ConnectInput('Layer5.Foreground',nil)
 for _,name in ipairs(names)do c:FindTool(name):Delete()end
end)
c:Unlock();c:EndUndo(true);assert(ok,err)
assert(c:FindTool('Background2'))
assert(c:FindTool('object_1_right').Background:GetConnectedOutput():GetTool()==c:FindTool('Background2'))
c.CurrentFrame.FlowView:Select();c:SetActiveTool(main)
assert(item:ExportFusionComp(base..'clean_template.comp',1));assert(pm:SaveProject())
print('LEGACY_REMOVED: four obsolete nodes; original right canvas and all active stacks retained')
