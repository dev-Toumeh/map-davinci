local r=resolve or fu:GetResolve()
local pm=assert(r:GetProjectManager())
local p=assert(pm:GetCurrentProject())
assert(p:GetName()=='china sv usa','Wrong project')
local item=assert(p:GetTimelineByIndex(1):GetItemListInTrack('video',2)[14])
assert(item:GetName()=='china-wrong-1-child-old','Clip changed')
assert(item:ExportFusionComp('/Users/naseemtoumeh/edit-projects/davinvi-resolve/experement/ArchiveCarousel_type_2/backups/live_20261019_223905/before_stack2.comp',1))
local function visit(folder,path)
 local current=path..'/'..folder:GetName()
 if current:lower():find('one%-chiled') then
  for _,clip in ipairs(folder:GetClipList() or {}) do
   print('IMAGE_CANDIDATE',current,clip:GetName(),clip:GetMediaId(),clip:GetClipProperty('File Path'),clip:GetClipProperty('Resolution'))
  end
 end
 for _,child in ipairs(folder:GetSubFolderList() or {}) do visit(child,current) end
end
visit(p:GetMediaPool():GetRootFolder(),'')
local c=item:GetFusionCompByIndex(1)
print('STACK_DRIVER',c:FindTool('object1_left'):GetInput('Displacement',0))
print('STACK2_BACKUP_AND_MEDIA_INSPECTION_OK')
