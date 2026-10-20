local base='/Users/naseemtoumeh/edit-projects/davinvi-resolve/experement/ArchiveCarousel_type_2/backups/live_20261019_223905/'
local pm=resolve:GetProjectManager();local p=assert(pm:GetCurrentProject());assert(p:GetName()=='china sv usa')
local item=assert(p:GetTimelineByIndex(1):GetItemListInTrack('video',2)[14]);assert(item:GetName()=='china-wrong-1-child-old')
local c=assert(item:GetFusionCompByIndex(1))
c:StartUndo('Restore blur offset path dependency bindings')
local offsets={Left_Blur_Depth_Path=0.25,object2_left=-0.5,Left_Stack2_Blur_Path=-0.25}
for name,offset in pairs(offsets)do
 local inp=assert(c:FindTool(name)).Displacement
 inp:SetExpression(nil)
 inp:SetExpression('object1_left.Displacement '..(offset<0 and '- ' or '+ ')..string.format('%.2f',math.abs(offset)))
end
local checks={}
for _,frame in ipairs({0,5,10,36,74,84})do
 local d=c:FindTool('object1_left'):GetInput('Displacement',frame)
 local values={main=d}
 for name,offset in pairs(offsets)do
  local value=c:FindTool(name):GetInput('Displacement',frame)
  assert(type(value)=='number' and math.abs(value-d-offset)<0.00001,'Invalid blur path '..name..' frame '..frame)
  values[name]=value
 end
 checks[tostring(frame)]=values
end
local main=c:FindTool('MultiMerge1')
assert(main.Background:GetConnectedOutput():GetTool()==c:FindTool('Main_Transparent_Background'))
assert(c:FindTool('Left_Blur_Depth_Placement').Background:GetConnectedOutput():GetTool()==c:FindTool('Left_Stack1_Background'))
c:SetData('BlurBindingVerification',checks)
c:EndUndo(true)
assert(item:ExportFusionComp(base..'after_blur_restore.comp',1))
assert(pm:SaveProject())
print('BLUR_RESTORED_VERIFIED_AND_SAVED: all offset paths evaluated correctly at frames 0/5/10/36/74/84')
