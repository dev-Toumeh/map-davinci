local p=assert(resolve:GetProjectManager():GetCurrentProject());assert(p:GetName()=='china sv usa')
local item=assert(p:GetTimelineByIndex(1):GetItemListInTrack('video',2)[14]);assert(item:GetName()=='china-wrong-1-child-old')
local c=assert(item:GetFusionCompByIndex(1));local media={}
local function walk(folder,path)
 local here=path..'/'..folder:GetName()
 if here:find('one-chiled',1,true) then
  for _,clip in ipairs(folder:GetClipList() or {})do
   media[#media+1]={name=clip:GetName(),id=clip:GetMediaId(),properties=clip:GetClipProperty(),folder=here}
  end
 end
 for _,child in ipairs(folder:GetSubFolderList()or{})do walk(child,here)end
end
walk(p:GetMediaPool():GetRootFolder(),'')
c:SetData('RightRowsMediaInspection',media)
assert(c:FindTool('MultiMerge1'):SaveSettings('/Users/naseemtoumeh/edit-projects/davinvi-resolve/experement/ArchiveCarousel_type_2/backups/live_20261019_223905/main_before_right_rows.setting'))
assert(item:ExportFusionComp('/Users/naseemtoumeh/edit-projects/davinvi-resolve/experement/ArchiveCarousel_type_2/backups/live_20261019_223905/before_right_rows.comp',1))
