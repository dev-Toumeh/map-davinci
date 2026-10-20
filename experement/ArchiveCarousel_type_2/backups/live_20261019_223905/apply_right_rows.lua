local base='/Users/naseemtoumeh/edit-projects/davinvi-resolve/experement/ArchiveCarousel_type_2/backups/live_20261019_223905/'
local pm=resolve:GetProjectManager();local p=assert(pm:GetCurrentProject());assert(p:GetName()=='china sv usa')
local item=assert(p:GetTimelineByIndex(1):GetItemListInTrack('video',2)[14]);assert(item:GetName()=='china-wrong-1-child-old')
local c=assert(item:GetFusionCompByIndex(1))
assert(item:ExportFusionComp(base..'before_right_rows_apply.comp',1))
local main=assert(c:FindTool('MultiMerge1'));local flow=c.CurrentFrame.FlowView
local oldTime=c.CurrentTime;local positions,links={},{}
for _,t in pairs(c:GetToolList(false))do
 local x,y=flow:GetPos(t);positions[#positions+1]={name=t:GetAttrs().TOOLS_Name,x=x,y=y}
 for _,inp in pairs(t:GetInputList())do if inp:GetAttrs().INPS_DataType=='Image'then links[#links+1]={inp,inp:GetConnectedOutput()}end end
end
local values={}
for _,f in ipairs({0,5,10,36,74,84})do
 values[f]={left=c:FindTool('object1_left'):GetInput('Displacement',f),right=c:FindTool('object1_right'):GetInput('Displacement',f)}
end
local leftBlurSize=c:FindTool('Left_Blur_Depth'):GetInput('XBlurSize',oldTime)
local leftBlur2Size=c:FindTool('Left_Stack2_Blur'):GetInput('XBlurSize',oldTime)
local leftBlurBlend=c:FindTool('Left_Blur_Depth_Placement'):GetInput('Blend',oldTime)
local leftBlur2Blend=c:FindTool('Left_Stack2_Blur_Placement'):GetInput('Blend',oldTime)
c:Lock();c:StartUndo('Mirror right-side sharp and blur rows using image4')
local ok,err=pcall(function()
 flow:Select();c:SetActiveTool(nil)
 local function add(kind,name)
  flow:Select();c:SetActiveTool(nil)
  local t=c:FindTool(name) or assert(c:AddTool(kind,-32768,-32768));t:SetAttrs({TOOLS_Name=name,TOOLB_NameSet=true});return t
 end
 for _,spec in ipairs({{'MediaIn','Media_file4'},{'Background','Right_Stack2_Background'},{'MediaIn','Right_Stack1_Vintage8mm'},{'MediaIn','Right_Stack2_Vintage8mm'},{'MultiMerge','object_2_right'}})do
  c:SetData('RightRowsStage','create '..spec[2])
  local t=add(spec[1],spec[2]);t:LoadSettings(base..'right_native_'..spec[2]..'.setting')
 end
 local fit=add('BetterResize','Right_Stack2_Fit');fit:SetInput('Width',328);fit:SetInput('Height',246)
 local crop=add('Crop','Right_Stack2_CardCanvas');crop:SetInput('XSize',328);crop:SetInput('YSize',480);crop:SetInput('KeepCentered',1)
 local frame4=add('ofx.com.blackmagicdesign.resolvefx.Transform','Media_file4_Frame')
 for _,id in ipairs({'edgeSoftness','edgeRounding','zoom','posX','posY','scaleX','scaleY','rotate'})do
  frame4:SetInput(id,c:FindTool('t1_right'):GetInput(id,oldTime))
 end
 local blur1=add('Blur','Right_Stack1_Blur')
 local placement1=add('Merge','Right_Stack1_Blur_Placement')
 local blur2=add('Blur','Right_Stack2_Blur')
 local placement2=add('Merge','Right_Stack2_Blur_Placement')
 local sharp2=add('Merge','Right_Stack2_Main_Placement')
 c:SetData('RightRowsStage','wire and reload main')
 for _,v in ipairs(links)do v[1]:ConnectTo(v[2])end
 -- Load all original attached modifiers with the one additional foreground slot.
 main:LoadSettings(base..'main_with_right_rows.setting')
 main=assert(c:FindTool('MultiMerge1'))
 for id,name in pairs({['Layer3.Center']='object1_right',['Layer4.Center']='object1_left',['Layer8.Center']='left_path'})do
  local modifier=assert(main[id]:GetConnectedOutput()):GetTool()
  modifier:SetAttrs({TOOLS_Name=name,TOOLB_NameSet=true})
 end
 local driver=assert(c:FindTool('object1_right'))
 local curve=assert(driver.PolyLine:GetConnectedOutput())
 curve:GetTool():SetAttrs({TOOLS_Name='right_path',TOOLB_NameSet=true})
 local leftCurve=assert(c:FindTool('Publish1')):FindMainOutput(1)
 c:FindTool('object1_left'):ConnectInput('PolyLine',leftCurve)
 -- Rebind existing left expressions after the native modifier reload; preserve user's static controls.
 local oldExpressions={Left_Blur_Depth_Path='object1_left.Displacement + 0.25',object2_left='object1_left.Displacement - 0.25'}
 for name,expression in pairs(oldExpressions)do
  local t=assert(c:FindTool(name));t:ConnectInput('PolyLine',leftCurve)
  t.Displacement:SetExpression(nil);t.Displacement:SetExpression(expression)
 end
 c:FindTool('Left_Stack2_Blur_Path'):ConnectInput('PolyLine',leftCurve)
 local function pathFor(placement,name,expression)
  assert(placement:AddModifier('Center','PolyPath'))
  local path=assert(placement.Center:GetConnectedOutput()):GetTool()
  path:SetAttrs({TOOLS_Name=name,TOOLB_NameSet=true})
  path:SetInput('Center',driver:GetInput('Center',oldTime))
  path:SetInput('Size',driver:GetInput('Size',oldTime))
  path:ConnectInput('PolyLine',curve)
  path:ConnectInput('Displacement',nil)
  path.Displacement:SetExpression(nil);path.Displacement:SetExpression(expression)
  return path
 end
 local path1=pathFor(placement1,'Right_Stack1_Blur_Path','object1_right.Displacement - 0.25')
 local path2=pathFor(placement2,'Right_Stack2_Blur_Path','object1_right.Displacement + 0.25')
 local pathSharp=pathFor(sharp2,'object2_right','object1_right.Displacement + 0.50')
 local card1=assert(c:FindTool('object_1_right'));local card2=assert(c:FindTool('object_2_right'))
 local bg1=assert(c:FindTool('Background2'));local bg2=assert(c:FindTool('Right_Stack2_Background'))
 card1:ConnectInput('Layer2.Foreground',assert(c:FindTool('Right_Stack1_Vintage8mm')))
 card2:ConnectInput('Background',bg2)
 card2:ConnectInput('Layer1.Foreground',assert(c:FindTool('Media_file4_Frame')))
 card2:ConnectInput('Layer2.Foreground',assert(c:FindTool('Right_Stack2_Vintage8mm')))
 c:FindTool('Right_Stack2_Fit'):ConnectInput('Input',assert(c:FindTool('Media_file4')))
 c:FindTool('Right_Stack2_CardCanvas'):ConnectInput('Input',c:FindTool('Right_Stack2_Fit'))
 c:FindTool('Media_file4_Frame'):ConnectInput('Source',c:FindTool('Right_Stack2_CardCanvas'))
 blur1:ConnectInput('Input',card1);blur1:SetInput('XBlurSize',leftBlurSize)
 placement1:ConnectInput('Background',bg1);placement1:ConnectInput('Foreground',blur1)
 placement1:SetInput('Size',2.898);placement1:SetInput('Blend',leftBlurBlend)
 blur2:ConnectInput('Input',card2);blur2:SetInput('XBlurSize',leftBlur2Size)
 placement2:ConnectInput('Background',placement1);placement2:ConnectInput('Foreground',blur2)
 placement2:SetInput('Size',2.898);placement2:SetInput('Blend',leftBlur2Blend)
 sharp2:ConnectInput('Background',placement2);sharp2:ConnectInput('Foreground',card2);sharp2:SetInput('Size',3.22)
 main:ConnectInput('Layer7.Foreground',sharp2)
 main:ConnectInput('Background',assert(c:FindTool('Main_Transparent_Background')))
 local order=main:GetInput('LayerOrder',oldTime);assert(order[0]==6 and order[1]==7)
 local checks={}
 for _,f in ipairs({0,5,10,36,74,84})do
  local d=driver:GetInput('Displacement',f)
  assert(math.abs(d-values[f].right)<0.00001,'Right timing changed')
  assert(math.abs(c:FindTool('object1_left'):GetInput('Displacement',f)-values[f].left)<0.00001,'Left timing changed')
  local v1=path1:GetInput('Displacement',f);local v2=path2:GetInput('Displacement',f);local v3=pathSharp:GetInput('Displacement',f)
  assert(type(v1)=='number' and math.abs(v1-(d-0.25))<0.00001)
  assert(type(v2)=='number' and math.abs(v2-(d+0.25))<0.00001)
  assert(type(v3)=='number' and math.abs(v3-(d+0.50))<0.00001)
  checks[tostring(f)]={main1=d,blur1=v1,main2=v3,blur2=v2}
 end
 c:SetData('RightRowsVerification',checks)
 flow:Select();c:SetActiveTool(nil)
 for _,v in ipairs(positions)do local t=c:FindTool(v.name);if t and v.x and v.y then flow:SetPos(t,v.x,v.y)end end
 local x,y=flow:GetPos(card1)
 local layout={Right_Stack1_Vintage8mm={x+1.4,y-1.5},Right_Stack1_Blur={x-1.4,y},Right_Stack1_Blur_Placement={x-1.4,y+1.7},
 Media_file4={x+7,y+5},Right_Stack2_Fit={x+5.6,y+5},Right_Stack2_CardCanvas={x+4.2,y+5},Media_file4_Frame={x+2.8,y+5},object_2_right={x+1.4,y+5},
 Right_Stack2_Background={x+7,y+3.5},Right_Stack2_Vintage8mm={x+2.8,y+3.5},Right_Stack2_Blur={x,y+5},
 Right_Stack2_Blur_Placement={x,y+6.7},Right_Stack2_Main_Placement={x,y+8.4}}
 for name,pos in pairs(layout)do flow:SetPos(c:FindTool(name),pos[1],pos[2])end
end)
c:EndUndo(true);c:Unlock()
if not ok then c:SetData('RightRowsError',tostring(err));item:ExportFusionComp(base..'right_rows_error.comp',1);error(err)end
assert(item:ExportFusionComp(base..'after_right_rows.comp',1))
assert(pm:SaveProject())
c.CurrentTime=36;c.CurrentFrame:ViewOn(c:FindTool('MediaOut1'),2)
c:GetPreviewList().RightView.View:SetScale(0)
print('RIGHT_ROWS_SAVED: image4 second row, native sharp/blur stacks, reversed-side path offsets; original timing and left controls retained')
