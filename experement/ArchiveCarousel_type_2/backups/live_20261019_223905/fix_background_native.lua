local base='/Users/naseemtoumeh/edit-projects/davinvi-resolve/experement/ArchiveCarousel_type_2/backups/live_20261019_223905/'
local pm=resolve:GetProjectManager();local p=assert(pm:GetCurrentProject());assert(p:GetName()=='china sv usa')
local item=assert(p:GetTimelineByIndex(1):GetItemListInTrack('video',2)[14]);assert(item:GetName()=='china-wrong-1-child-old')
local c=assert(item:GetFusionCompByIndex(1));local main=assert(c:FindTool('MultiMerge1'))
local canvas=assert(c:FindTool('Main_Transparent_Background'))
local left=assert(c:FindTool('Left_Blur_Depth_Placement'))
local combined=assert(c:FindTool('Left_Stack2_Main_Placement'))
assert(main:LoadSettings(base..'main_native_layers.setting'))
for id,name in pairs({['Layer3.Center']='object1_right',['Layer4.Center']='object1_left',['Layer8.Center']='left_path'})do
 local tool=assert(c:FindTool(name))
 local output=tool.Position or tool.Value
 main:ConnectInput(id,output)
end
local order=main:GetInput('LayerOrder',c.CurrentTime)
c:SetData('BackgroundFixOrderType',type(order))
if type(order)=='table' then c:SetData('BackgroundFixOrder',order) end
assert(type(order)=='table','LayerOrder must be a native table')
local arr=type(order[1])=='table' and order[1] or order
assert(arr[0]~=nil,'Unexpected LayerOrder structure')
local result={[0]=6};local n=1
for i=0,#arr do if arr[i]~=6 then result[n]=arr[i];n=n+1 end end
local newOrder=result;if arr~=order then newOrder={[1]=result} end
local oldBg=main.Background:GetConnectedOutput()
local oldLeftBg=left.Background:GetConnectedOutput()
local old6=main['Layer6.Foreground']:GetConnectedOutput()
c:Lock();c:StartUndo('Correct main and left transparent backgrounds')
local ok,err=pcall(function()
 left:ConnectInput('Background',assert(c:FindTool('Left_Stack1_Background')))
 c:FindTool('Left_Stack2_Blur_Placement'):ConnectInput('Background',left)
 combined:ConnectInput('Background',c:FindTool('Left_Stack2_Blur_Placement'))
 assert(main:ConnectInput('Layer6.Foreground',combined))
 assert(main:GetInput('LayerOrder',c.CurrentTime)[0]==6,'LayerOrder did not load correctly')
 main:SetInput('LayerName6','Left cards and depth')
 assert(main:ConnectInput('Background',canvas))
 assert(main.Background:GetConnectedOutput():GetTool()==canvas)
 assert(left.Background:GetConnectedOutput():GetTool()==c:FindTool('Left_Stack1_Background'))
 assert(main['Layer6.Foreground']:GetConnectedOutput():GetTool()==combined)
 local flow=c.CurrentFrame.FlowView;flow:Select();c:SetActiveTool(nil)
 local x,y=flow:GetPos(main);flow:SetPos(canvas,x-1.5,y-1.5)
 canvas:SetAttrs({TOOLS_Comments='Transparent canvas for the main MultiMerge only.'})
 main:SetAttrs({TOOLS_Comments=''})
end)
if not ok then
 main:ConnectInput('Background',oldBg);left:ConnectInput('Background',oldLeftBg)
 main:ConnectInput('Layer6.Foreground',old6);main:SetInput('LayerOrder',order)
end
c:EndUndo(true);c:Unlock();assert(ok,err)
c:SetData('BackgroundFixError',nil);c:SetData('BackgroundFixStage','complete')
assert(item:ExportFusionComp(base..'after_background_fix.comp',1))
assert(pm:SaveProject())
print('BACKGROUND_FIX_SAVED: right canvas stays right; left blur has left canvas; main transparent background; left composite on foreground layer6')
