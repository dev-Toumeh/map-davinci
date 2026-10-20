from pathlib import Path
import json
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
w,h=Image.open(ROOT/'images/satellite_detail.png').size
def val(k,v):return f'{k} = Input {{ Value = {json.dumps(v)}, }},'
def ref(k,n,p='Output'):return f'{k} = Input {{ SourceOp = "{n}", Source = "{p}", }},'
def node(n,t,i,x,y):return f'{n} = {t} {{ Inputs = {{ {i} }}, ViewInfo = OperatorInfo {{ Pos = {{ {x}, {y} }} }}, }},'
def loader(n,file,x,y):return f'{n} = Loader {{ Clips = {{ Clip {{ ID = "Clip1", Filename = {json.dumps(str(ROOT/"images"/file))}, Length = 1, GlobalStart = 0, GlobalEnd = 1000000, TrimIn = 0, TrimOut = 0, Loop = 1, }} }}, ViewInfo = OperatorInfo {{ Pos = {{ {x}, {y} }} }}, }},'

grade=val('NumberIn1',1.06)+val('NumberIn2',.018)
for channel,c,warm in [('Red','r1',1),('Green','g1',.2),('Blue','b1',-.55)]:
    grade+=val(channel+'Expression',f'min(1,max(0,({c}-.5)*n1+.5+n2*{warm}))')
grade+=val('AlphaExpression','a1')

# Esri hillshade is near-white on flat terrain. Multiply adds relief shadows.
# Mode 1 offers Soft Light instead, with white terrain centered around neutral gray.
relief=ref('Image1','TB_Base_Colour')+ref('Image2','TB_Hillshade')+val('NumberIn1',.65)+val('NumberIn2',0)+val('NumberIn3',4)
relief+=val('Intermediate1','min(1,max(0,(r2+g2+b2)/3))')
relief+=val('Intermediate2','min(1,max(0,((r2+g2+b2)/3-.97)*4+.5))')
for channel,c in [('Red','r1'),('Green','g1'),('Blue','b1')]:
    soft=f'if(i2<.5,{c}-(1-2*i2)*{c}*(1-{c}),{c}+(2*i2-1)*(sqrt(max({c},0))-{c}))'
    relief+=val(channel+'Expression',f'{c}*(1-n1)+n1*if(n2<.5,{c}*(i1^n3),{soft})')
relief+=val('AlphaExpression','a1')

paper=ref('Image1','TB_Relief_Blend')+ref('Image2','TB_Paper_Fit')+val('NumberIn1',.28)+val('NumberIn2',1)
paper+=val('Intermediate1','min(1,max(0,((r2+g2+b2)/3-.9)*7+.5))')
for channel,c in [('Red','r1'),('Green','g1'),('Blue','b1')]:
    soft=f'if(i1<.5,{c}-(1-2*i1)*{c}*(1-{c}),{c}+(2*i1-1)*(sqrt(max({c},0))-{c}))'
    paper+=val(channel+'Expression',f'{c}*(1-n1)+n1*if(n2<.5,{c}*((r2+g2+b2)/3),{soft})')
paper+=val('AlphaExpression','a1')
edge=ref('Image1','TB_Paper_Blend')+val('NumberIn1',.13)+val('Intermediate1','min(1,((x-.5)*(x-.5)+(y-.5)*(y-.5))*2)')
for channel,c in [('Red','r1'),('Green','g1'),('Blue','b1')]:edge+=val(channel+'Expression',f'{c}*(1-n1*i1)')
edge+=val('AlphaExpression','a1')
inner=loader('TB_Hillshade','esri_hillshade.png',0,-180)+loader('TB_Paper','paper_texture.png',240,-360)
inner+=node('TB_Paper_Canvas','Background',val('Width',w)+val('Height',h)+val('UseFrameFormatSettings',0)+val('TopLeftAlpha',0),0,-360)
inner+=node('TB_Paper_Fit','Merge',ref('Background','TB_Paper_Canvas')+ref('Foreground','TB_Paper')+val('Size',w/1254),460,-360)
inner+=node('TB_Base_Colour','Custom',grade,0,0)+node('TB_Relief_Blend','Custom',relief,240,0)+node('TB_Paper_Blend','Custom',paper,480,0)+node('TB_Final_Style','Custom',edge,720,0)
published='MainInput1 = InstanceInput { SourceOp = "TB_Base_Colour", Source = "Image1", },'
for i,(name,tool,port) in enumerate([('Base contrast','TB_Base_Colour','NumberIn1'),('Warmth','TB_Base_Colour','NumberIn2'),('Relief strength','TB_Relief_Blend','NumberIn1'),('Relief mode: 0 Multiply / 1 Soft Light','TB_Relief_Blend','NumberIn2'),('Relief shadow depth','TB_Relief_Blend','NumberIn3'),('Paper strength','TB_Paper_Blend','NumberIn1'),('Paper mode: 0 Multiply / 1 Soft Light','TB_Paper_Blend','NumberIn2'),('Edge shading','TB_Final_Style','NumberIn1')]):
    published+=f'Control{i} = InstanceInput {{ SourceOp = "{tool}", Source = "{port}", Name = "{name}", }},'
def group(source=None):
    contents=inner.replace('TB_Base_Colour = Custom { Inputs = { ','TB_Base_Colour = Custom { Inputs = { '+(ref('Image1',source) if source else ''),1)
    return 'Texture_Blend = GroupOperator { Inputs = { '+published+' }, Outputs = { MainOutput1 = InstanceOutput { SourceOp = "TB_Final_Style", Source = "Output", }, }, ViewInfo = GroupInfo { Pos = { 240, 0 } }, Tools = ordered() { '+contents+' }, },'
tools=loader('TB_Original','satellite_detail.png',0,0)+group('TB_Original')
credit=val('Width',w)+val('Height',h)+val('UseFrameFormatSettings',0)+val('StyledText','Imagery: Esri, Maxar, Earthstar Geographics | Relief: Esri and contributors')+val('Font','Arial')+val('Style','Regular')+val('Size',.008)+'Center = Input { Value = { 0.32, 0.025 }, },'
credit+=val('Red1',.18)+val('Green1',.13)+val('Blue1',.08)
tools+=node('TB_Attribution','TextPlus',credit,460,140)
tools+=node('TB_Credited_Map','Merge',ref('Background','TB_Final_Style')+ref('Foreground','TB_Attribution'),480,0)
flatten=ref('Image1','TB_Credited_Map')
for channel,c in [('Red','r1'),('Green','g1'),('Blue','b1'),('Alpha','a1')]:flatten+=val(channel+'Expression',c)
tools+=node('TB_Rendered_Image','Custom',flatten,720,0)
setting='{ Tools = ordered() { '+tools+' }, ActiveTool = "Texture_Blend", }'
(ROOT/'fusion/Texture_Blend_Nodes.setting').write_text(setting)
(ROOT/'fusion/Texture_Blend_Effect.setting').write_text('{ Tools = ordered() { '+group()+' }, ActiveTool = "Texture_Blend", }')
output=node('MediaOut1','MediaOut',ref('Input','TB_Rendered_Image'),960,0)
(ROOT/'fusion/Texture_Blend_Generated.comp').write_text('Composition { CurrentTime = 0, GlobalRange = { 0, 119 }, RenderRange = { 0, 119 }, Tools = ordered() { '+tools+output+' }, Prefs = { Comp = { FrameFormat = { Width = '+str(w)+', Height = '+str(h)+', Rate = 24, }, }, }, }')
(ROOT/'scripts/load_experiment.lua').write_text('comp:SetActiveTool(nil)\ncomp:Paste(bmd.readstring([==['+setting+']==]))\ncomp.CurrentTime=0\ncomp:FindTool("MediaOut1"):ConnectInput("Input",comp:FindTool("TB_Rendered_Image").Output)\nprint("Texture blend loaded")\n')
print('Built texture blend:',w,h)
