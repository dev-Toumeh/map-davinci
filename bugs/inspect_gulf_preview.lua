-- Read-only native snapshot: no tool settings, timing, or wiring changes.
local ok,err=pcall(function()
 local p=assert(resolve:GetProjectManager():GetCurrentProject())
 assert(p:GetName()=='gulf_trains','Unexpected project')
 local timeline=assert(p:GetCurrentTimeline())
 local item=assert(timeline:GetCurrentVideoItem(),'No current video item')
 local c=assert(item:GetFusionCompByIndex(1),'No Fusion comp on current item')
 assert(c:FindTool('Map_3D_Scene'),'Not the map composition')
 local report={}
 local function link(input,localTools)
  local output=input:GetConnectedOutput()
  if not output then return 'DISCONNECTED'end
  local source=output:GetTool();local name=source.Name
  local scope=localTools[name] and (localTools[name]==source and 'LOCAL:' or 'WRONG_GROUP:') or 'EXTERNAL:'
  return scope..name..'.'..tostring(output:GetAttrs().OUTS_ID)
 end
 for _,iso in ipairs({'SAU','QAT','ARE','KWT','BHR','OMN'})do
  local group=c:FindTool(iso..'_Border_Highlight_Group')
  if group then
   local entry={outputs={},children={}}
   local localTools={}
   for _,tool in pairs(group:GetChildrenList())do localTools[tool.Name]=tool end
   for _,output in pairs(group:GetOutputList())do entry.outputs[#entry.outputs+1]=output:GetAttrs().OUTS_ID end
   for _,tool in pairs(group:GetChildrenList())do
    local child={}
    for _,input in pairs(tool:GetInputList())do
     if input:GetAttrs().INPS_DataType=='Image' or input:GetAttrs().INPS_DataType=='Mask'then
      child[input:GetAttrs().INPS_ID]=link(input,localTools)
     end
    end
    entry.children[tool.Name]=child
   end
   report[iso]=entry
  end
 end
 local old=c:GetData('CountryPreviewInspection')
 c:SetData('CountryPreviewInspection',report)
 item:ExportFusionComp('/Users/naseemtoumeh/edit-projects/davinvi-resolve/bugs/gulf-preview-native-inspection.comp',1)
 c:SetData('CountryPreviewInspection',old)
 print('GULF_PREVIEW_SNAPSHOT_EXPORTED')
end)
if not ok then print('GULF_PREVIEW_INSPECTION_FAILED',err)end
