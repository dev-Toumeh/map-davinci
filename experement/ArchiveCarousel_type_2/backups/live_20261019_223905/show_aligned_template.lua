local pm=resolve:GetProjectManager();local p=assert(pm:GetCurrentProject());assert(p:GetName()=='china sv usa')
local item=assert(p:GetTimelineByIndex(1):GetItemListInTrack('video',2)[14]);assert(item:GetName()=='china-wrong-1-child-old')
local c=assert(item:GetFusionCompByIndex(1));local flow=c.CurrentFrame.FlowView
flow:FrameAll();flow:SetScale(0.60);assert(pm:SaveProject())
