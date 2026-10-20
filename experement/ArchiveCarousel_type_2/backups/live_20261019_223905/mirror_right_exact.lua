local base='/Users/naseemtoumeh/edit-projects/davinvi-resolve/experement/ArchiveCarousel_type_2/backups/live_20261019_223905/'
local pm=resolve:GetProjectManager();local p=assert(pm:GetCurrentProject());assert(p:GetName()=='china sv usa')
local item=assert(p:GetTimelineByIndex(1):GetItemListInTrack('video',2)[14]);assert(item:GetName()=='china-wrong-1-child-old')
local c=assert(item:GetFusionCompByIndex(1));local flow=c.CurrentFrame.FlowView
assert(item:ExportFusionComp(base..'before_exact_right_mirror_finish.comp',1))
local pairsToMirror={
 {'Left_Blur_Depth_Path','Right_Stack1_Blur_Path'},
 {'object2_left','object2_right'},
 {'Left_Stack2_Blur_Path','Right_Stack2_Blur_Path'},
}
c:Lock();c:StartUndo('Match right rows to existing left design with reverse motion')
local ok,err=pcall(function()
 for _,pair in ipairs(pairsToMirror)do
  local source=assert(c:FindTool(pair[1]));local target=assert(c:FindTool(pair[2]))
  target.Displacement:SetExpression(nil)
  target.Displacement:SetExpression(pair[1]..'.Displacement - 0.50')
 end
 local media=assert(c:FindTool('Media_file4'));local frame=assert(c:FindTool('Media_file4_Frame'))
 frame:ConnectInput('Source',media)
 -- Native OFX zoom keeps the complete wider photo proportional in the existing card stack.
 local sourceWidth=assert(media:GetAttrs().TOOLI_ImageWidth)
 local referenceWidth=assert(c:FindTool('Media_file2'):GetAttrs().TOOLI_ImageWidth)
 frame:SetInput('zoom',referenceWidth/sourceWidth)
 frame:SetInput('scaleX',1);frame:SetInput('scaleY',1)
 local right1=assert(c:FindTool('object_1_right'));local right2=assert(c:FindTool('object_2_right'))
 right2:ConnectInput('Background',assert(c:FindTool('Right_Stack2_Background')))
 right2:SetInput('LayerName1','image4')
 local blurs={{'Left_Blur_Depth','Right_Stack1_Blur'},{'Left_Stack2_Blur','Right_Stack2_Blur'}}
 for _,pair in ipairs(blurs)do c:FindTool(pair[2]):SetInput('XBlurSize',c:FindTool(pair[1]):GetInput('XBlurSize',c.CurrentTime))end
 local placements={{'Left_Blur_Depth_Placement','Right_Stack1_Blur_Placement'},{'Left_Stack2_Blur_Placement','Right_Stack2_Blur_Placement'},{'Left_Stack2_Main_Placement','Right_Stack2_Main_Placement'}}
 for _,pair in ipairs(placements)do
  for _,id in ipairs({'Size','Blend'})do c:FindTool(pair[2]):SetInput(id,c:FindTool(pair[1]):GetInput(id,c.CurrentTime))end
 end
 c:FindTool('Right_Stack1_Blur_Placement'):ConnectInput('Background',c:FindTool('Background2'))
 c:FindTool('Right_Stack2_Blur_Placement'):ConnectInput('Background',c:FindTool('Right_Stack1_Blur_Placement'))
 c:FindTool('Right_Stack2_Main_Placement'):ConnectInput('Background',c:FindTool('Right_Stack2_Blur_Placement'))
 -- Remove only the two fitting tools created during the previous attempt; backup and Undo retain recovery.
 for _,name in ipairs({'Right_Stack2_CardCanvas','Right_Stack2_Fit'})do local t=c:FindTool(name);if t then t:Delete()end end
 -- Match the left graph's spacing, mirrored about the screen center between the two first cards.
 flow:Select();c:SetActiveTool(nil)
 local left1=c:FindTool('object_1_left');local lx,ly=flow:GetPos(left1);local rx,ry=flow:GetPos(right1)
 local axis=lx+rx;local dy=ry-ly
 local layoutPairs={
  {'MediaIn4','MediaIn3'},{'t1_left','t1_right'},
  {'Left_Stack1_Background','Background2'},{'Left_Stack1_Vintage8mm','Right_Stack1_Vintage8mm'},
  {'Left_Blur_Depth','Right_Stack1_Blur'},{'Left_Blur_Depth_Placement','Right_Stack1_Blur_Placement'},
  {'Media_file2','Media_file4'},{'Media_file2_Frame','Media_file4_Frame'},{'object_2_left','object_2_right'},
  {'Left_Stack2_Background','Right_Stack2_Background'},{'Left_Stack2_Vintage8mm','Right_Stack2_Vintage8mm'},
  {'Left_Stack2_Blur','Right_Stack2_Blur'},{'Left_Stack2_Blur_Placement','Right_Stack2_Blur_Placement'},
  {'Left_Stack2_Main_Placement','Right_Stack2_Main_Placement'},
 }
 for _,pair in ipairs(layoutPairs)do
  local a=assert(c:FindTool(pair[1]));local b=assert(c:FindTool(pair[2]));local x,y=flow:GetPos(a)
  flow:SetPos(b,axis-x,y+dy)
 end
 local checks={}
 for _,f in ipairs({0,5,10,36,74,84})do
  local values={}
  for _,pair in ipairs(pairsToMirror)do
   local a=c:FindTool(pair[1]):GetInput('Displacement',f);local b=c:FindTool(pair[2]):GetInput('Displacement',f)
   assert(type(a)=='number' and type(b)=='number' and math.abs(b-(a-0.50))<0.00001,pair[2]..' mismatch')
   values[pair[2]]=b
  end
  checks[tostring(f)]=values
 end
 c:SetData('ExactRightMirrorVerification',checks)
 c:SetData('BackgroundFixError',nil)
 c:SetData('RightRowsStage','matched existing left design; image4 second row; no timing extension')
end)
c:EndUndo(true);c:Unlock();assert(ok,err)
c.CurrentTime=84;c.CurrentFrame:ViewOn(c:FindTool('MediaOut1'),2)
c:GetPreviewList().RightView.View:SetScale(0)
assert(item:ExportFusionComp(base..'exact_right_mirror.comp',1))
assert(pm:SaveProject())
print('EXACT_RIGHT_MIRROR_SAVED')
