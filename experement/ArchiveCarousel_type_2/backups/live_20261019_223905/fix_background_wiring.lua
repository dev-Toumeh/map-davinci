do return dofile('/Users/naseemtoumeh/edit-projects/davinvi-resolve/bugs/inspect_gulf_preview.lua') end
local base='/Users/naseemtoumeh/edit-projects/davinvi-resolve/experement/ArchiveCarousel_type_2/backups/live_20261019_223905/'
local pm=resolve:GetProjectManager();local p=assert(pm:GetCurrentProject());assert(p:GetName()=='china sv usa')
local item=assert(p:GetTimelineByIndex(1):GetItemListInTrack('video',2)[14]);assert(item:GetName()=='china-wrong-1-child-old')
local c=assert(item:GetFusionCompByIndex(1));local main=assert(c:FindTool('MultiMerge1'))
c:SetData('BackgroundFixReaders',{readfile=type(readfile),readstring=type(readstring),bmdreadfile=type(bmd and bmd.readfile),bmdreadstring=type(bmd and bmd.readstring)})
local existingBackground=c:FindTool('Main_Transparent_Background')
assert(item:ExportFusionComp(base..'before_background_fix_apply.comp',1))
local original=base..'main_multimerge_before.setting'
c:SetData('BackgroundFixStage','snapshot links')
local links,positions={},{}
local flow=c.CurrentFrame.FlowView
for _,t in pairs(c:GetToolList(false)) do
 local x,y=flow:GetPos(t);positions[#positions+1]={t,x,y}
 for _,i in pairs(t:GetInputList()) do
  if i:GetAttrs().INPS_DataType=='Image' then links[#links+1]={i,i:GetConnectedOutput()} end
 end
end
local function restoreLinks()for _,v in ipairs(links)do v[1]:ConnectTo(v[2])end end
c:SetData('BackgroundFixStage','snapshot final inputs')
local originalFinalInputs={}
for _,i in pairs(main:GetInputList()) do
 if i:GetConnectedOutput() then originalFinalInputs[#originalFinalInputs+1]={i:GetAttrs().INPS_ID,i:GetConnectedOutput()} end
end
c:Lock();c:StartUndo('Separate right left and main transparent canvases')
local ok,err=pcall(function()
 c:SetData('BackgroundFixStage','paste background')
 flow:Select();c:SetActiveTool(nil)
 if not existingBackground then
  local bg=assert(c:AddTool('Background',-32768,-32768))
  bg:SetAttrs({TOOLS_Name='Main_Transparent_Background',TOOLB_NameSet=true})
  for _,id in ipairs({'Width','Height','UseFrameFormatSettings','GlobalIn','GlobalOut'})do
   bg:SetInput(id,c:FindTool('Background2'):GetInput(id,c.CurrentTime))
  end
  bg:SetInput('TopLeftAlpha',0)
 end
 restoreLinks()
 c:SetData('BackgroundFixStage','load main settings')
 assert(main:LoadSettings(assert(dofile(base..'main_background_fixed.lua'))))
 main=assert(c:FindTool('MultiMerge1'))
 for _,v in ipairs(originalFinalInputs)do if v[1]~='Background' then main:ConnectInput(v[1],v[2]) end end
 main:ConnectInput('Background',assert(c:FindTool('Main_Transparent_Background')))
 local independent={
  Left_Blur_Depth_Placement='Left_Stack1_Background',
  Left_Stack2_Blur_Placement='Left_Stack2_Background',
  Left_Stack2_Main_Placement='Left_Stack2_Background',
 }
 for name,bg in pairs(independent)do assert(c:FindTool(name)):ConnectInput('Background',assert(c:FindTool(bg)))end
 for n,name in pairs({[9]='Left_Blur_Depth_Placement',[10]='Left_Stack2_Blur_Placement',[11]='Left_Stack2_Main_Placement'})do
  assert(main:ConnectInput('Layer'..n..'.Foreground',assert(c:FindTool(name))))
 end
 flow:Select();c:SetActiveTool(nil)
 for _,v in ipairs(positions)do if v[2] and v[3]then flow:SetPos(v[1],v[2],v[3])end end
 local x,y=flow:GetPos(main);flow:SetPos(c:FindTool('Main_Transparent_Background'),x-1.5,y-1.5)
end)
if not ok then pcall(function()main:LoadSettings(original);restoreLinks()end)end
c:EndUndo(true);c:Unlock()
if not ok then
 c:SetData('BackgroundFixError',tostring(err))
 item:ExportFusionComp(base..'background_fix_error.comp',1)
 error(err)
end
assert(item:ExportFusionComp(base..'after_background_fix.comp',1))
assert(pm:SaveProject())
print('BACKGROUND_FIX_SAVED: right Background2 preserved; left canvases independent; main transparent canvas and foreground layers 9/10/11')
