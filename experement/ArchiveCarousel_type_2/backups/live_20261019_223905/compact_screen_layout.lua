local base='/Users/naseemtoumeh/edit-projects/davinvi-resolve/experement/ArchiveCarousel_type_2/backups/live_20261019_223905/'
local pm=resolve:GetProjectManager();local p=assert(pm:GetCurrentProject());assert(p:GetName()=='china sv usa')
local item=assert(p:GetTimelineByIndex(1):GetItemListInTrack('video',2)[14]);assert(item:GetName()=='china-wrong-1-child-old')
local c=assert(item:GetFusionCompByIndex(1))
assert(item:ExportFusionComp(base..'before_compact_screen_layout.comp',1))
local flow=c.CurrentFrame.FlowView
c:StartUndo('Restore compact screen-side node layout')
flow:Select();c:SetActiveTool(nil)
local layout={
 Background2={-2.5,-1.5},MediaIn1={-2.5,1},
 Left_Stack1_Background={0,-1.5},Left_Stack1_Vintage8mm={1.5,-1.5},
 MediaIn4={0,0},t1_left={1.5,0},object_1_left={3,0},
 Left_Blur_Depth={4.5,0},Left_Blur_Depth_Placement={4.5,1.5},
 Left_Stack2_Background={0,3.5},Left_Stack2_Vintage8mm={1.5,3.5},
 Media_file2={0,5},Media_file2_Frame={1.5,5},object_2_left={3,5},
 Left_Stack2_Blur={4.5,5},Left_Stack2_Blur_Placement={4.5,6.5},
 Left_Stack2_Main_Placement={4.5,8},
 MediaIn3={12,0},t1_right={10.5,0},object_1_right={9,0},
 MultiMerge3={9,4},MultiMerge2={11,4},MediaIn2={12,6},
 p_left={0,8},Background1_1={1.5,8},p_right={11,8},Background1={9,8},
 MultiMerge1={6,10.5},MediaOut1={6,12.5},
}
for name,pos in pairs(layout) do local t=c:FindTool(name);if t then flow:SetPos(t,pos[1],pos[2]) end end
c:EndUndo(true)
flow:FrameAll()
assert(item:ExportFusionComp(base..'after_compact_screen_layout.comp',1))
assert(pm:SaveProject())
print('COMPACT_LAYOUT_SAVED: left-screen cards left, right-screen cards right, final MultiMerge below. Layout only; no image links or animation changed.')
