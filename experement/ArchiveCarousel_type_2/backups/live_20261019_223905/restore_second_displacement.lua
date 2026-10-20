local base='/Users/naseemtoumeh/edit-projects/davinvi-resolve/experement/ArchiveCarousel_type_2/backups/live_20261019_223905/'
local pm=resolve:GetProjectManager();local p=assert(pm:GetCurrentProject());assert(p:GetName()=='china sv usa')
local item=assert(p:GetTimelineByIndex(1):GetItemListInTrack('video',2)[14]);assert(item:GetName()=='china-wrong-1-child-old')
local c=assert(item:GetFusionCompByIndex(1))
assert(item:ExportFusionComp(base..'before_second_displacement_restore.comp',1))
local path=assert(c:FindTool('object2_left'))
c:StartUndo('Restore second left object linked displacement')
path.Displacement:SetExpression(nil)
path.Displacement:SetExpression('object1_left.Displacement - 0.50')
for _,frame in ipairs({0,10,36,74,84})do
 local value=path:GetInput('Displacement',frame)
 local expected=c:FindTool('object1_left'):GetInput('Displacement',frame)-0.50
 assert(type(value)=='number' and math.abs(value-expected)<0.00001,'Displacement failed at '..frame)
end
c:EndUndo(true)
assert(item:ExportFusionComp(base..'after_second_displacement_restore.comp',1))
assert(pm:SaveProject())
print('SECOND_OBJECT_LINKED_DISPLACEMENT_RESTORED_AND_SAVED')
