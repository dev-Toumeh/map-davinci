-- Preserve the current native design; repair only duplicate names and image links.
local ok,err=pcall(function()
 local p=assert(resolve:GetProjectManager():GetCurrentProject())
 assert(p:GetName()=='gulf_trains','Unexpected project')
 local item=assert(p:GetCurrentTimeline():GetCurrentVideoItem())
 local c=assert(item:GetFusionCompByIndex(1))
 assert(c:FindTool('Map_3D_Scene'),'Not the map composition')
 local base='/Users/naseemtoumeh/edit-projects/davinvi-resolve/bugs/'
 local stamp=os.date('%Y%m%d_%H%M%S')
 assert(item:ExportFusionComp(base..'gulf-highlight-before-'..stamp..'.comp',1)~=false,'Backup failed')
 local stacks={}
 local names={'Path','Core','Transparent','Inner_Glow','Outer_Glow','Outer_Merge','Inner_Merge','Layers','Merge'}
 for _,iso in ipairs({'SAU','QAT','ARE','KWT','BHR','OMN'})do
  local group=assert(c:FindTool(iso..'_Border_Highlight_Group'))
  local children={};for _,t in pairs(group:GetChildrenList())do children[t.Name]=t end
  local tools={}
  for _,name in ipairs(names)do
   tools[name]=assert(children['Highlight_'..name] or children[iso..'_'..name],iso..' missing '..name)
  end
  stacks[#stacks+1]={iso=iso,tools=tools,group=group,
   source=assert(c:FindTool(iso..'_Local_Elements_MultiMerge')),
   plane=assert(c:FindTool(iso..'_Plane'))}
 end
 c:StartUndo('Repair country highlight links')
 local success,failure=pcall(function()
  for _,s in ipairs(stacks)do
   local t=s.tools
   for _,name in ipairs(names)do t[name]:SetAttrs({TOOLS_Name=s.iso..'_'..name})end
   t.Core:ConnectInput('EffectMask',t.Path,'Mask')
   t.Inner_Glow:ConnectInput('Input',t.Core,'Output')
   t.Outer_Glow:ConnectInput('Input',t.Core,'Output')
   t.Outer_Merge:ConnectInput('Background',t.Transparent,'Output')
   t.Outer_Merge:ConnectInput('Foreground',t.Outer_Glow,'Output')
   t.Inner_Merge:ConnectInput('Background',t.Outer_Merge,'Output')
   t.Inner_Merge:ConnectInput('Foreground',t.Inner_Glow,'Output')
   t.Layers:ConnectInput('Background',t.Inner_Merge,'Output')
   t.Layers:ConnectInput('Foreground',t.Core,'Output')
   t.Merge:ConnectInput('Background',s.source,'Output')
   t.Merge:ConnectInput('Foreground',t.Layers,'Output')
   -- Link the actual final native Merge, avoiding stale published-port bindings
   -- in this already-imported group. All IDs are now globally unique.
   s.plane:ConnectInput('MaterialInput',t.Merge,'Output')
   assert(s.plane.MaterialInput:GetConnectedOutput():GetTool()==t.Merge)
   assert(t.Core.EffectMask:GetConnectedOutput():GetTool()==t.Path)
   assert(t.Merge.Background:GetConnectedOutput():GetTool()==s.source)
  end
 end)
 c:EndUndo(true)
 assert(success,failure)
 item:ExportFusionComp(base..'gulf-highlight-after-'..stamp..'.comp',1)
 print('GULF_HIGHLIGHT_REPAIRED',stamp)
end)
if not ok then print('GULF_HIGHLIGHT_REPAIR_FAILED',err)end
