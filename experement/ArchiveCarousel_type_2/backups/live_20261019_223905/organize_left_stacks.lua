local base='/Users/naseemtoumeh/edit-projects/davinvi-resolve/experement/ArchiveCarousel_type_2/backups/live_20261019_223905/'
local pm=resolve:GetProjectManager();local p=assert(pm:GetCurrentProject())
assert(p:GetName()=='china sv usa')
local item=assert(p:GetTimelineByIndex(1):GetItemListInTrack('video',2)[14])
assert(item:GetName()=='china-wrong-1-child-old')
local c=assert(item:GetFusionCompByIndex(1))
assert(not c:FindTool('Left_Stack1_Background'))
local flow=c.CurrentFrame.FlowView
local links,positions={},{}
for _,tool in pairs(c:GetToolList(false)) do
 local x,y=flow:GetPos(tool);positions[#positions+1]={tool,x,y}
 for _,inp in pairs(tool:GetInputList()) do
  if inp:GetAttrs().INPS_DataType=='Image' then links[#links+1]={inp,inp:GetConnectedOutput()} end
 end
end
local function restoreLinks() for _,v in ipairs(links) do v[1]:ConnectTo(v[2]) end end
local function copySettings(name)
 local settings=assert(c:FindTool(name)):SaveSettings()
 return assert(settings.Tools[name])
end
local tools={
 Left_Stack1_Background=copySettings('Background2'),
 Left_Stack2_Background=copySettings('Background2'),
 Left_Stack1_Vintage8mm=copySettings('MediaIn1'),
 Left_Stack2_Vintage8mm=copySettings('MediaIn1'),
}
for _,t in pairs(tools) do
 t.NameSet=true;t.SourceOp=nil
 if t.Inputs then t.Inputs.LeftAudio=nil;t.Inputs.RightAudio=nil end
end
c:Lock();c:StartUndo('Independent left card backgrounds and film, organized flow')
local ok,err=pcall(function()
 flow:Select();c:SetActiveTool(nil)
 assert(c:Paste({Tools=tools}))
 restoreLinks()
 for i,name in ipairs({'object_1_left','object_2_left'}) do
  local card=assert(c:FindTool(name))
  card:ConnectInput('Background',assert(c:FindTool('Left_Stack'..i..'_Background')))
  card:ConnectInput('Layer2.Foreground',assert(c:FindTool('Left_Stack'..i..'_Vintage8mm')))
 end
 -- Clear selection before positioning to avoid moving selected nodes together.
 flow:Select();c:SetActiveTool(nil)
 local layout={
  -- Shared sources and visible route artwork, upstream of all card stacks.
  Background2={-5,0},MediaIn1={-5,3},
  Background1_1={-5,7},p_left={-7,7},Background1={-5,10},p_right={-7,10},
  -- Left stack 1: dedicated inputs, sharp card, complete-card blur.
  Left_Stack1_Background={0,0},Left_Stack1_Vintage8mm={3,0},
  MediaIn4={0,3},t1_left={3,3},object_1_left={6,3},
  Left_Blur_Depth={9,3},Left_Blur_Depth_Placement={12,3},
  -- Left stack 2: same columns and spacing as stack 1.
  Left_Stack2_Background={0,7},Left_Stack2_Vintage8mm={3,7},
  Media_file2={0,10},Media_file2_Frame={3,10},object_2_left={6,10},
  Left_Stack2_Blur={9,10},Left_Stack2_Blur_Placement={12,10},
  Left_Stack2_Main_Placement={15,10},
  -- Existing right card remains separate; shared sources stay left.
  MediaIn3={0,17},t1_right={3,17},object_1_right={6,17},
  -- Retained placeholder cards and unused source, not deleted.
  MultiMerge3={12,17},MultiMerge2={15,17},MediaIn2={0,22},
  -- Composite/output are downstream at the right edge.
  MultiMerge1={18,10},MediaOut1={18,15},
 }
 for name,pos in pairs(layout) do
  local tool=c:FindTool(name);if tool then flow:SetPos(tool,pos[1],pos[2]) end
 end
 c:FindTool('Left_Stack1_Background'):SetAttrs({TOOLS_Comments='Dedicated transparent canvas for LEFT STACK 1 only.'})
 c:FindTool('Left_Stack2_Background'):SetAttrs({TOOLS_Comments='Dedicated transparent canvas for LEFT STACK 2 only.'})
 for i=1,2 do
  c:FindTool('Left_Stack'..i..'_Vintage8mm'):SetAttrs({TOOLS_Comments='Independent Vintage 8mm Film source for LEFT STACK '..i..'. Same asset, no instance link.'})
 end
 flow:FrameAll()
end)
if not ok then
 restoreLinks();flow:Select()
 for _,v in ipairs(positions) do if v[2] and v[3] then flow:SetPos(v[1],v[2],v[3]) end end
end
c:EndUndo(true);c:Unlock();assert(ok,err)
assert(item:ExportFusionComp(base..'after_left_layout.comp',1))
assert(pm:SaveProject())
print('LEFT_STACKS_ORGANIZED_AND_SAVED: dedicated backgrounds and film sources; shared inputs at left; existing motion unchanged')
