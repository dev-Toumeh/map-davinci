local base='/Users/naseemtoumeh/edit-projects/davinvi-resolve/experement/ArchiveCarousel_type_2/backups/live_20261019_223905/'
local pm=resolve:GetProjectManager();local p=assert(pm:GetCurrentProject());assert(p:GetName()=='china sv usa')
local item=assert(p:GetTimelineByIndex(1):GetItemListInTrack('video',2)[14]);assert(item:GetName()=='china-wrong-1-child-old')
local c=assert(item:GetFusionCompByIndex(1));local flow=c.CurrentFrame.FlowView
assert(item:ExportFusionComp(base..'before_template_alignment_apply.comp',1))
local layout={
 Left_Stack1_Background={0,-1.5},Left_Stack1_Vintage8mm={1.5,-1.5},
 MediaIn4={0,0},t1_left={1.5,0},object_1_left={3,0},Left_Blur_Depth={4.5,0},Left_Blur_Depth_Placement={4.5,1.5},
 Left_Stack2_Background={0,2.5},Left_Stack2_Vintage8mm={1.5,2.5},
 Media_file2={0,4},Media_file2_Frame={1.5,4},object_2_left={3,4},Left_Stack2_Blur={4.5,4},
 Left_Stack2_Blur_Placement={4.5,5.5},Left_Stack2_Main_Placement={4.5,7},
 Background2={13,-1.5},Right_Stack1_Vintage8mm={11.5,-1.5},
 MediaIn3={13,0},t1_right={11.5,0},object_1_right={10,0},Right_Stack1_Blur={8.5,0},Right_Stack1_Blur_Placement={8.5,1.5},
 Right_Stack2_Background={13,2.5},Right_Stack2_Vintage8mm={11.5,2.5},
 Media_file4={13,4},Media_file4_Frame={11.5,4},object_2_right={10,4},Right_Stack2_Blur={8.5,4},
 Right_Stack2_Blur_Placement={8.5,5.5},Right_Stack2_Main_Placement={8.5,7},
 p_left={0,7},Background1_1={1.5,7},p_right={13,7},Background1={11.5,7},
 -- Retained original placeholder stacks, separated from the active right cards.
 MediaIn1={0,8.5},MultiMerge3={1.5,8.5},MultiMerge2={3,8.5},MediaIn2={0,10},
 Main_Transparent_Background={6.5,8.5},MultiMerge1={6.5,10},MediaOut1={6.5,11.5},
}
for name in pairs(layout)do assert(c:FindTool(name),'Missing expected tool: '..name)end
c:StartUndo('Align template stacks only');flow:Select();c:SetActiveTool(nil)
for name,pos in pairs(layout)do flow:SetPos(c:FindTool(name),pos[1],pos[2])end
c:EndUndo(true);flow:FrameAll()
assert(item:ExportFusionComp(base..'aligned_template.comp',1));assert(pm:SaveProject())
print('TEMPLATE_ALIGNED: positions only; all existing nodes, links and animation retained')
