local base='/Users/naseemtoumeh/edit-projects/davinvi-resolve/experement/ArchiveCarousel_type_2/backups/live_20261019_223905/'
local ok,err=pcall(dofile,base..'fix_background_wiring.lua')
if not ok then
 local p=assert(resolve:GetProjectManager():GetCurrentProject())
 local item=assert(p:GetTimelineByIndex(1):GetItemListInTrack('video',2)[14])
 local c=assert(item:GetFusionCompByIndex(1))
 c:SetData('BackgroundFixError',tostring(err))
 local bg=c:FindTool('Main_Transparent_Background') or c:FindTool('MultiMerge1')
 bg:SetAttrs({TOOLS_Comments='BACKGROUND_FIX_ERROR: '..tostring(err)})
 item:ExportFusionComp(base..'background_fix_error.comp',1)
 print('BACKGROUND_FIX_ERROR',err)
end
