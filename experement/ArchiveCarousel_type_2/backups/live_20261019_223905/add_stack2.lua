local base='/Users/naseemtoumeh/edit-projects/davinvi-resolve/experement/ArchiveCarousel_type_2/backups/live_20261019_223905/'
local r=resolve or fu:GetResolve()
local pm=assert(r:GetProjectManager())
local p=assert(pm:GetCurrentProject())
assert(p:GetName()=='china sv usa')
local item=assert(p:GetTimelineByIndex(1):GetItemListInTrack('video',2)[14])
assert(item:GetName()=='china-wrong-1-child-old')
local c=assert(item:GetFusionCompByIndex(1))
assert(not c:FindTool('Media_file2'))
local final=assert(c:FindTool('MultiMerge1'))
local driver=assert(c:FindTool('object1_left'))
local oldBackground=assert(final.Background:GetConnectedOutput())
assert(item:ExportFusionComp(base..'before_stack2_apply.comp',1))
-- Snapshot all existing image links: Paste/AddTool may otherwise auto-insert.
local links={}
for _,t in pairs(c:GetToolList(false)) do
 for _,inp in pairs(t:GetInputList()) do
  if inp:GetAttrs().INPS_DataType=='Image' then
   links[#links+1]={input=inp,output=inp:GetConnectedOutput()}
  end
 end
end
local function restoreLinks()
 for _,v in ipairs(links) do v.input:ConnectTo(v.output) end
end
local media=assert(c:FindTool('MediaIn4'):SaveSettings().Tools.MediaIn4)
local transform=assert(c:FindTool('t1_left'):SaveSettings().Tools.t1_left)
local card=assert(c:FindTool('object_1_left'):SaveSettings().Tools.object_1_left)
local filename='/Users/naseemtoumeh/edit-projects/project2/Aj+/images/1neSxMQ8q2A5GCqER-YCnUOo1LwYny8YjEXTCXDWo6Tc_HJ3t0BGy510q30mG7T6GChFrjpP-jpWkGuyqyS8EB0Od1rJLWN_1aF6WfOfD8HHuUrohFuCfzZZkmjPKYVf2EwLDzPZqyJ66wpYvMnPJ4AVm8cZQPjiU2fx96gCdTuQ8_527kzP_j-IrOzP8vb8.jpeg'
local id='f4d15345-3ab0-4b34-abd3-13c63db99841'
media.CustomData.MEDIA_ID=id
local props=media.CustomData.MediaProps
props.MEDIA_ID=id;props.MEDIA_PATH=filename;props.MEDIA_NAME='image3';props.MEDIA_WIDTH=400
media.Inputs.MediaID.Value=id
if media.Clips then media.Clips[1].Filename=filename end
media.Inputs.LeftAudio=nil;media.Inputs.RightAudio=nil
media.NameSet=true
transform.Inputs.Source.SourceOp='Media_file2'
card.Inputs['Layer1.Foreground'].SourceOp='Media_file2_Frame'
card.Inputs.LayerName1.Value='image3'
local settings={Tools={Media_file2=media,Media_file2_Frame=transform,object_2_left=card}}
c:Lock();c:StartUndo('Add image3 left stack with half-loop spacing')
local ok,err=pcall(function()
 c:SetActiveTool(nil)
 assert(c:Paste(settings))
 local m=assert(c:FindTool('Media_file2'))
 local t=assert(c:FindTool('Media_file2_Frame'))
 local card2=assert(c:FindTool('object_2_left'))
 local function add(kind,name)
  c:SetActiveTool(nil)
  local tool=assert(c:AddTool(kind,-32768,-32768))
  tool:SetAttrs({TOOLS_Name=name,TOOLB_NameSet=true})
  return tool
 end
 local blur=add('Blur','Left_Stack2_Blur')
 local blurPlacement=add('Merge','Left_Stack2_Blur_Placement')
 local mainPlacement=add('Merge','Left_Stack2_Main_Placement')
 local function pathFor(placement,name,expression)
  assert(placement:AddModifier('Center','PolyPath'))
  local path=assert(placement.Center:GetConnectedOutput()):GetTool()
  path:SetAttrs({TOOLS_Name=name,TOOLB_NameSet=true})
  path:SetInput('Center',driver:GetInput('Center',0))
  path:SetInput('Size',driver:GetInput('Size',0))
  path:ConnectInput('PolyLine',driver.PolyLine:GetConnectedOutput())
  path:ConnectInput('Displacement',nil)
  path.Displacement:SetExpression(expression)
  return path
 end
 local mainPath=pathFor(mainPlacement,'object2_left','object1_left.Displacement - 0.50')
 local blurPath=pathFor(blurPlacement,'Left_Stack2_Blur_Path','object1_left.Displacement - 0.25')
 restoreLinks()
 t:ConnectInput('Source',m)
 card2:ConnectInput('Background',c:FindTool('Background2'))
 card2:ConnectInput('Layer1.Foreground',t)
 card2:ConnectInput('Layer2.Foreground',c:FindTool('MediaIn1'))
 card2:ConnectInput('Layer3.Foreground',nil)
 blur:ConnectInput('Input',card2);blur:SetInput('XBlurSize',12)
 blurPlacement:ConnectInput('Background',oldBackground)
 blurPlacement:ConnectInput('Foreground',blur)
 blurPlacement:SetInput('Size',2.898);blurPlacement:SetInput('Blend',0.6)
 mainPlacement:ConnectInput('Background',blurPlacement)
 mainPlacement:ConnectInput('Foreground',card2)
 mainPlacement:SetInput('Size',3.22)
 final:ConnectInput('Background',mainPlacement)
 assert(final['Layer4.Foreground']:GetConnectedOutput():GetTool()==c:FindTool('object_1_left'))
 for _,frame in ipairs({0,5,10,74,84}) do
  local d=driver:GetInput('Displacement',frame)
  assert(math.abs(mainPath:GetInput('Displacement',frame)-(d-0.5))<0.00001)
  assert(math.abs(blurPath:GetInput('Displacement',frame)-(d-0.25))<0.00001)
  print('STACK2_PHASE',frame,d,mainPath:GetInput('Displacement',frame),blurPath:GetInput('Displacement',frame))
 end
 local flow=c.CurrentFrame.FlowView
 local x,y=flow:GetPos(c:FindTool('object_1_left'))
 flow:SetPos(m,x-4,y+4);flow:SetPos(t,x-2,y+4);flow:SetPos(card2,x,y+4)
 flow:SetPos(blur,x+2,y+5);flow:SetPos(blurPlacement,x+4,y+5);flow:SetPos(mainPlacement,x+6,y+4)
end)
if not ok then restoreLinks() end
c:EndUndo(true);c:Unlock()
assert(ok,err)
assert(item:ExportFusionComp(base..'after_stack2.comp',1))
assert(pm:SaveProject())
print('STACK2_SAVED: image3, main = driver - 0.50, blur = driver - 0.25; original timings and layers retained')
