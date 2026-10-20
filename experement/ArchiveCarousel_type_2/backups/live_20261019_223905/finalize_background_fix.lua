local base='/Users/naseemtoumeh/edit-projects/davinvi-resolve/experement/ArchiveCarousel_type_2/backups/live_20261019_223905/'
local pm=resolve:GetProjectManager();local p=assert(pm:GetCurrentProject());assert(p:GetName()=='china sv usa')
local item=assert(p:GetTimelineByIndex(1):GetItemListInTrack('video',2)[14]);assert(item:GetName()=='china-wrong-1-child-old')
local c=assert(item:GetFusionCompByIndex(1));local main=assert(c:FindTool('MultiMerge1'))
c:Lock();c:StartUndo('Finalize main canvas and foregrounds with all original modifiers')
main:LoadSettings(base..'main_native_layers_complete.setting')
main=assert(c:FindTool('MultiMerge1'))
local paths={['Layer3.Center']='object1_right',['Layer4.Center']='object1_left',['Layer8.Center']='left_path'}
for id,name in pairs(paths)do
 local out=assert(main[id]:GetConnectedOutput());local modifier=out:GetTool()
 modifier:SetAttrs({TOOLS_Name=name,TOOLB_NameSet=true})
end
local driver=assert(c:FindTool('object1_left'))
driver:ConnectInput('PolyLine',assert(c:FindTool('Publish1')):FindMainOutput(1))
local canvas=assert(c:FindTool('Main_Transparent_Background'))
main:ConnectInput('Background',canvas)
main:ConnectInput('Layer6.Foreground',assert(c:FindTool('Left_Stack2_Main_Placement')))
c:FindTool('Left_Blur_Depth_Placement'):ConnectInput('Background',assert(c:FindTool('Left_Stack1_Background')))
c:FindTool('Left_Stack2_Blur_Placement'):ConnectInput('Background',c:FindTool('Left_Blur_Depth_Placement'))
c:FindTool('Left_Stack2_Main_Placement'):ConnectInput('Background',c:FindTool('Left_Stack2_Blur_Placement'))
local order=main:GetInput('LayerOrder',c.CurrentTime)
assert(order[0]==6 and order[1]==1 and order[6]==5,'Native layer order invalid')
for _,frame in ipairs({0,10,74,84})do
 local expected=frame==0 and 0.25 or frame==84 and 0.75 or 0.50
 assert(math.abs(driver:GetInput('Displacement',frame)-expected)<0.00001,'Original motion changed')
end
local flow=c.CurrentFrame.FlowView;flow:Select();c:SetActiveTool(nil)
local x,y=flow:GetPos(main);flow:SetPos(canvas,x-1.5,y-1.5)
canvas:SetAttrs({TOOLS_Comments='Transparent canvas for main MultiMerge only.'})
c:SetData('BackgroundFixError',nil);c:SetData('BackgroundFixStage','complete verified')
c:EndUndo(true);c:Unlock()
assert(item:ExportFusionComp(base..'after_background_fix.comp',1))
assert(pm:SaveProject())
print('BACKGROUND_FIX_VERIFIED_AND_SAVED')
