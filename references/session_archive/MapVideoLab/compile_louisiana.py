from pathlib import Path
import json,re,math
import numpy as np
from lupa import LuaRuntime
ROOT=Path('/Users/naseemtoumeh/edit-projects/davinvi-resolve/usa'); HIST=ROOT/'assets/historical'
SOURCE=ROOT/'USA_linked_media.comp'; raw=SOURCE.read_text()
pts=np.array(json.loads((HIST/'louisiana_aligned_pixels.json').read_text())['coordinates'][0])[:-1]
W,H=3840,2160; END=1439
pivot=[(pts[:,0].min()+pts[:,0].max())/2/W,1-(pts[:,1].min()+pts[:,1].max())/2/H]
quote=lambda s:json.dumps(s,ensure_ascii=False)
val=lambda v:'Input { Value = '+v+', }'
connection=lambda op,out='Output':'Input { SourceOp = '+quote(op)+', Source = '+quote(out)+', }'
nodes=[]
def node(name,typ,inputs,pos=(0,0),extra=''):
 fields='\n'.join('\t\t\t\t'+k+' = '+v+',' for k,v in inputs.items())
 nodes.append(f'\n\t\t{name} = {typ} {{\n\t\t\tNameSet = true,\n\t\t\tInputs = {{\n{fields}\n\t\t\t}},\n\t\t\tViewInfo = OperatorInfo {{ Pos = {{ {pos[0]}, {pos[1]} }} }},\n{extra}\t\t}},')
def spline(name,keys,pos=(0,0)):
 # Smooth transitions use horizontal tangents; steady segments are linear.
 entries=[]
 for i,(f,v) in enumerate(keys):
  handles=[]
  if i: handles.append(f'LH = {{ {f-(f-keys[i-1][0])/3:.6f}, {v} }}')
  if i<len(keys)-1:handles.append(f'RH = {{ {f+(keys[i+1][0]-f)/3:.6f}, {v} }}')
  entries.append(f'[{f}] = {{ {v}, '+', '.join(handles)+' }')
 nodes.append(f'\n\t\t{name} = BezierSpline {{ KeyFrames = {{ '+', '.join(entries)+' } },')
def animated(name,keys):spline(name,keys);return connection(name,'Value')
common={'GlobalOut':val(str(END)),'Width':val(str(W)),'Height':val(str(H)),'UseFrameFormatSettings':val('1')}
clip=f'''\t\t\tClips = {{ Clip {{ ID = "Clip1", Filename = {quote(str(ROOT/'assets/us-4k.png'))}, Length = 1, GlobalEnd = {END}, TrimOut = 0, Loop = 1 }} }},\n'''
node('LP_Map','Loader',{'GlobalOut':val(str(END)),'ClipTimeEnd':val('0'),'Loop':val('1')},(-100,600),clip)
points=',\n'.join(f'{{ Linear = true, X = {x/W-.5:.10f}, Y = {.5-y/H:.10f}, LX = 0, LY = 0, RX = 0, RY = 0 }}' for x,y in pts)
poly='Polyline { Closed = true, Points = {\n'+points+'\n} }'
mask={'MaskWidth':val(str(W)),'MaskHeight':val(str(H)),'UseFrameFormatSettings':val('1'),'Solid':val('1'),'Polyline':val(poly)}
node('LP_HistoricalBoundary','PolylineMask',mask,(-100,450))
node('LP_GoldHighlight','Background',{**common,'TopLeftRed':val('.9568627'),'TopLeftGreen':val('.6196078'),'TopLeftBlue':val('.2039216'),'TopLeftAlpha':animated('LP_HighlightFade',[(0,0),(240,0),(276,.78),(504,.78),(527,0),(1439,0)]),'EffectMask':connection('LP_HistoricalBoundary','Mask')},(80,450))
node('LP_MapWithHighlight','Merge',{'Background':connection('LP_Map'),'Foreground':connection('LP_GoldHighlight')},(80,600))
node('LP_Camera','Transform',{'Input':connection('LP_MapWithHighlight'),'Pivot':val('{ '+','.join(map(str,pivot))+' }'),'Center':val('{ .5, .47 }'),'Size':animated('LP_CameraZoom',[(0,3.8),(240,3.8),(288,4.15),(480,4.2),(527,4.2),(1439,4.2)])},(280,600))
node('LP_TitlePanelMask','RectangleMask',{'MaskWidth':val(str(W)),'MaskHeight':val(str(H)),'UseFrameFormatSettings':val('1'),'Center':val('{ .5, .885 }'),'Width':val('.58'),'Height':val('.16'),'CornerRadius':val('.035')},(280,450))
node('LP_TitlePanel','Background',{**common,'TopLeftRed':val('.015'),'TopLeftGreen':val('.12'),'TopLeftBlue':val('.14'),'TopLeftAlpha':animated('LP_TitlePanelFade',[(0,0),(240,0),(258,.94),(504,.94),(527,0),(1439,0)]),'EffectMask':connection('LP_TitlePanelMask','Mask')},(460,450))
node('LP_PanelComposite','Merge',{'Background':connection('LP_Camera'),'Foreground':connection('LP_TitlePanel')},(460,600))
def text(name,words,size,center,fade,pos,color=(1,1,1)):
 inputs={**common,'StyledText':val(quote(words)),'Font':val('"Damascus"'),'Style':val('"Bold"'),'Size':val(str(size)),'Center':val('{ '+','.join(map(str,center))+' }'),'Red1':val(str(color[0])),'Green1':val(str(color[1])),'Blue1':val(str(color[2])),'Alpha1':animated(name+'Fade',fade),'HorizontalJustificationNew':val('3'),'VerticalJustificationNew':val('3')}
 node(name,'TextPlus',inputs,pos)
fade=[(0,0),(240,0),(258,1),(504,1),(527,0),(1439,0)]
text('LP_ArabicTitle','شراء لويزيانا',.065,(.5,.925),fade,(640,450))
text('LP_Date','١٨٠٣',.045,(.5,.846),fade,(820,450),(.96,.70,.31))
node('LP_TitleComposite','Merge',{'Background':connection('LP_PanelComposite'),'Foreground':connection('LP_ArabicTitle')},(640,600))
node('LP_DateComposite','Merge',{'Background':connection('LP_TitleComposite'),'Foreground':connection('LP_Date')},(820,600))
node('LP_SubtitleMask','RectangleMask',{'MaskWidth':val(str(W)),'MaskHeight':val(str(H)),'UseFrameFormatSettings':val('1'),'Center':val('{ .5, .11 }'),'Width':val('.82'),'Height':val('.1'),'CornerRadius':val('.025')},(820,300))
node('LP_SubtitlePanel','Background',{**common,'TopLeftRed':val('.015'),'TopLeftGreen':val('.12'),'TopLeftBlue':val('.14'),'TopLeftAlpha':animated('LP_SubtitleFade',[(0,0),(360,0),(378,.92),(504,.92),(527,0),(1439,0)]),'EffectMask':connection('LP_SubtitleMask','Mask')},(1000,300))
node('LP_SubtitleComposite','Merge',{'Background':connection('LP_DateComposite'),'Foreground':connection('LP_SubtitlePanel')},(1000,600))
text('LP_Price','صفقة مع فرنسا مقابل ١٥ مليون دولار',.034,(.5,.11),[(0,0),(360,0),(378,1),(456,1),(474,0),(1439,0)],(1180,450))
node('LP_PriceComposite','Merge',{'Background':connection('LP_SubtitleComposite'),'Foreground':connection('LP_Price')},(1180,600))
text('LP_Expansion','تضاعفت مساحة الولايات المتحدة',.035,(.5,.11),[(0,0),(474,0),(486,1),(504,1),(527,0),(1439,0)],(1360,450))
node('LP_Final','Merge',{'Background':connection('LP_PriceComposite'),'Foreground':connection('LP_Expansion')},(1360,600))
# Find a balanced table region while honoring Lua strings.
def endbrace(s,start):
 depth=0; quotechar=None;escape=False
 for i in range(start,len(s)):
  ch=s[i]
  if quotechar:
   if escape:escape=False
   elif ch=='\\':escape=True
   elif ch==quotechar:quotechar=None
  elif ch in '\"\'':quotechar=ch
  elif ch=='{':depth+=1
  elif ch=='}':
   depth-=1
   if not depth:return i
 raise ValueError('Unbalanced composition')
a=raw.index('\n\t\tMediaOut1 = Saver {'); b=endbrace(raw,raw.index('{',a))
old=raw[a:b+1];assert old.count('SourceOp = "Transform1"')==1
s=raw[:a]+old.replace('SourceOp = "Transform1"','SourceOp = "LP_Final"')+raw[b+1:]
opening=s.index('{',s.index('\n\tTools = {'));closing=endbrace(s,opening)
s=s[:closing].rstrip()+','+''.join(nodes)+'\n\t'+s[closing:]
s=re.sub(r'CurrentTime = \d+,','CurrentTime = 360,',s,count=1)
s=re.sub(r'RenderRange = \{[^}]+\}','RenderRange = { 240, 527 }',s,count=1)
s=re.sub(r'GlobalRange = \{[^}]+\}','GlobalRange = { 0, 1439 }',s,count=1)
s=s.replace('GlobalEnd = 806\n','GlobalEnd = 1439\n')
OUT=ROOT/'USA_Louisiana_Arabic_Test.comp';OUT.write_text(s)
# Parse whole native file and check every new node reference.
L=LuaRuntime(unpack_returned_tuples=True)
L.execute('''local function proxy(name) return setmetatable({}, {__index=function(_,k) return proxy(name.."."..k) end, __call=function(_,t) if t==nil then return proxy(name) end return t end}) end; setmetatable(_G,{__index=function(_,k) return proxy(k) end})''')
c=L.execute('return '+s); tools=c['Tools']; names=set(tools.keys()); newnames={n for n in names if n.startswith('LP_')}
assert tools['MediaOut1']['Inputs']['Input']['SourceOp']=='LP_Final'
for n in newnames:
 t=tools[n];inp=t['Inputs']
 if inp:
  for _,v in inp.items():
   op=v['SourceOp']
   if op:assert op in names,(n,op)
assert len(list(tools['LP_HistoricalBoundary']['Inputs']['Polyline']['Value']['Points'].keys()))==len(pts)
assert SOURCE.read_text()==raw
config={'fps':24,'start_frame':240,'end_frame':527,'duration_seconds':12,'source_comp':SOURCE.name,'output_comp':OUT.name,'camera_pivot':pivot,'captions':{'title':'شراء لويزيانا','date':'١٨٠٣','price':'صفقة مع فرنسا مقابل ١٥ مليون دولار','expansion':'تضاعفت مساحة الولايات المتحدة'},'events':[{'time':10,'action':'Camera approaches region; title appears'},{'time':11.5,'action':'Historical region highlight fully visible'},{'time':15,'action':'Price caption fades in'},{'time':20,'action':'Expansion caption appears'},{'time':22,'action':'End of test shot'}]}
(ROOT/'louisiana_shot.json').write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n')
(ROOT/'LOUISIANA_TEST_README.md').write_text('''# Louisiana Purchase test shot

Import `USA_Louisiana_Arabic_Test.comp` into a duplicate/new Fusion composition. At 24 fps, view MediaOut1 over frames 240–527 (10–22 seconds). Full global range is 0–1439; only the Louisiana test shot is adapted, not the rest of the script.

New pipeline nodes use the `LP_` prefix. Original country groups and camera curves remain in the file; MediaOut1 displays the new test branch. `LP_HistoricalBoundary` is an editable PolylineMask aligned to the 4K map. `LP_CameraZoom` controls the camera. All titles are editable Damascus TextPlus nodes.

Timing and captions are also recorded in `louisiana_shot.json` for future voiceover adjustments. Original compositions were not changed. The companion MP4 is an offline approximation of the animation, not a render from Resolve. Native Fusion output still needs visual verification in Resolve.

Boundary source: National Atlas territorial-acquisition SVG, published as public domain in the U.S.: https://commons.wikimedia.org/wiki/File:Aquired_Lands_of_the_US.svg . SVG boundary was converted through an estimated Albers registration and fitted to the screenshot's Mercator projection. This is a small-scale educational visualization; alignment is approximate, not survey accuracy. Educational-use-only GIS was used as a registration reference, with no vertices copied into the output geometry. Natural Earth coastline was used for background projection alignment: https://www.naturalearthdata.com/about/terms-of-use/ .
''')
print('Created',OUT,'with',len(newnames),'new nodes; full Lua syntax and node references validated. Original unchanged.')
