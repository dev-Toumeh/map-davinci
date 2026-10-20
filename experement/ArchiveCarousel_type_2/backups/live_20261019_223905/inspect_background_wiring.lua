local p=assert(resolve:GetProjectManager():GetCurrentProject());assert(p:GetName()=='china sv usa')
local item=assert(p:GetTimelineByIndex(1):GetItemListInTrack('video',2)[14]);assert(item:GetName()=='china-wrong-1-child-old')
local c=assert(item:GetFusionCompByIndex(1))
local base='/Users/naseemtoumeh/edit-projects/davinvi-resolve/experement/ArchiveCarousel_type_2/backups/live_20261019_223905/'
assert(item:ExportFusionComp(base..'before_background_fix.comp',1))
assert(c:FindTool('MultiMerge1'):SaveSettings(base..'main_multimerge_before.setting'))
print('BACKGROUND_WIRING_BACKUP_OK')
