local r = resolve or fu:GetResolve()
local pm = assert(r:GetProjectManager())
local p = assert(pm:GetCurrentProject())
assert(p:GetName() == 'china sv usa', 'Wrong active project')
assert(not p:IsRenderingInProgress(), 'Stop render first')
local tl = assert(p:GetTimelineByIndex(1))
assert(tl:GetName() == 'Timeline 1', 'Timeline changed')
local item = assert(tl:GetItemListInTrack('video', 2)[14])
assert(item:GetName() == 'china-wrong-1-child-old', 'Clip index changed; nothing modified')
local c = assert(item:GetFusionCompByIndex(1))
local sharp = assert(c:FindTool('object_1_left'))
local mainPath = assert(c:FindTool('object1_left'))
local output = assert(c:FindTool('MultiMerge1'))
local bg = assert(c:FindTool('Background2'))
local oldBlur = assert(sharp['Layer3.Foreground']:GetConnectedOutput(), 'Legacy blur connection changed')
assert(oldBlur:GetTool():GetAttrs().TOOLS_Name == 't1_left_1', 'Unexpected legacy source')
local oldBackground = assert(output.Background:GetConnectedOutput())
assert(oldBackground:GetTool() == bg, 'Output background changed')
local route = assert(mainPath.PolyLine:GetConnectedOutput())
assert(not c:FindTool('Left_Blur_Depth'), 'Depth update already present; stopped')
local base = '/Users/naseemtoumeh/edit-projects/davinvi-resolve/experement/ArchiveCarousel_type_2/backups/live_20261019_223905/'
local created = {}
c:Lock()
c:StartUndo('Left card - separate blurred depth layer')
local ok, err = pcall(function()
 local blur = assert(c:AddTool('Blur', -32768, -32768))
 created[#created + 1] = blur
 blur:SetAttrs({TOOLS_Name='Left_Blur_Depth', TOOLB_NameSet=true})
 blur:SetInput('XBlurSize', 12)
 assert(blur:ConnectInput('Input', sharp), 'Connect complete card to blur failed')
 local merge = assert(c:AddTool('Merge', -32768, -32768))
 created[#created + 1] = merge
 merge:SetAttrs({TOOLS_Name='Left_Blur_Depth_Placement', TOOLB_NameSet=true})
 assert(merge:ConnectInput('Background', bg), 'Depth background failed')
 assert(merge:ConnectInput('Foreground', blur), 'Depth foreground failed')
 merge:SetInput('Size', output:GetInput('Layer4.Size', 36) * 0.9)
 merge:SetInput('Blend', 0.6)
 assert(merge:AddModifier('Center', 'PolyPath'), 'Depth path creation failed')
 local path = assert(merge.Center:GetConnectedOutput()):GetTool()
 path:SetAttrs({TOOLS_Name='Left_Blur_Depth_Path', TOOLB_NameSet=true})
 path:SetInput('Center', mainPath:GetInput('Center', 36))
 path:SetInput('Size', mainPath:GetInput('Size', 36))
 assert(path:ConnectInput('PolyLine', route), 'Share original curve failed')
 path:ConnectInput('Displacement', nil)
 path.Displacement:SetExpression('object1_left.Displacement + 0.08')
 -- Only these two original image connections change. Keep all LayerOrder data,
 -- original paths, keyframes, media, frame artwork, and legacy nodes untouched.
 assert(sharp:ConnectInput('Layer3.Foreground', nil), 'Detach raw duplicate failed')
 -- AddTool may auto-insert on the selected wire. Explicitly retain the sharp output.
 assert(output:ConnectInput('Layer4.Foreground', sharp), 'Restore sharp foreground failed')
 assert(output:ConnectInput('Background', merge), 'Connect depth behind final composite failed')
 assert(not sharp['Layer3.Foreground']:GetConnectedOutput(), 'Raw duplicate still connected')
 assert(output.Background:GetConnectedOutput():GetTool() == merge)
 assert(blur.Input:GetConnectedOutput():GetTool() == sharp)
 if c.CurrentFrame and c.CurrentFrame.FlowView then
  local x,y=c.CurrentFrame.FlowView:GetPos(sharp)
  c.CurrentFrame.FlowView:SetPos(blur, x+1.3, y-2.8)
  c.CurrentFrame.FlowView:SetPos(merge, x+3, y-1.8)
 end
end)
c:EndUndo(true)
c:Unlock()
if not ok then
 -- Restore original connections even if the API rejects a new modifier/input.
 sharp:ConnectInput('Layer3.Foreground', oldBlur)
 output:ConnectInput('Background', oldBackground)
 for i = #created, 1, -1 do pcall(function() created[i]:Delete() end) end
 error('Update rolled back: ' .. tostring(err))
end
assert(pm:SaveProject(), 'Save failed; use the named Undo action to revert')
assert(item:ExportFusionComp(base .. 'Timeline1_Track2_Item14_Comp1_after.comp', 1), 'Verification export failed')
c.CurrentTime = 36
print('LEFT_DEPTH_UPDATED_AND_SAVED', 'blur=12', 'size=90%', 'blend=0.6', 'path phase=+0.08', base)
