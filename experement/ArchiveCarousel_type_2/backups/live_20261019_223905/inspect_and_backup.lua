local r = resolve or fu:GetResolve()
local pm = assert(r:GetProjectManager())
local p = assert(pm:GetCurrentProject())
assert(p:GetName() == 'china sv usa', 'Wrong active project; stopped')
assert(not p:IsRenderingInProgress(), 'Stop rendering first')
local base = '/Users/naseemtoumeh/edit-projects/davinvi-resolve/experement/ArchiveCarousel_type_2/backups/live_20261019_223905/'
-- The full project backup above was already completed on the first invocation.
-- Keep it untouched; Resolve's console does not expose the standard io library.
local found = 0
for ti = 1, p:GetTimelineCount() do
 local tl = p:GetTimelineByIndex(ti)
 for track = 1, tl:GetTrackCount('video') do
  for index, item in ipairs(tl:GetItemListInTrack('video', track) or {}) do
   for ci = 1, item:GetFusionCompCount() do
    local c = item:GetFusionCompByIndex(ci)
    if c and c:FindTool('object_1_left') and c:FindTool('object1_left') then
     found = found + 1
     local prefix = 'Timeline' .. ti .. '_Track' .. track .. '_Item' .. index .. '_Comp' .. ci
     assert(item:ExportFusionComp(base .. prefix .. '_before.comp', ci), 'Comp backup failed')
     print('MATCH', ti, tl:GetName(), track, index, item:GetName(), ci, prefix)
    end
   end
  end
 end
end
print('CHINA_CAROUSEL_BACKUP_AND_INSPECTION_OK', found, base)
