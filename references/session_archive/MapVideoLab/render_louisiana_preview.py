from pathlib import Path
import json,subprocess
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import arabic_reshaper
from bidi.algorithm import get_display
ROOT=Path('/Users/naseemtoumeh/edit-projects/davinvi-resolve/usa'); HIST=ROOT/'assets/historical'
config=json.loads((ROOT/'louisiana_shot.json').read_text());pivot=config['camera_pivot'];W,H=1280,720
base=Image.open(ROOT/'assets/us-4k.png').convert('RGBA').resize((W,H))
coords=np.array(json.loads((HIST/'louisiana_aligned_pixels.json').read_text())['coordinates'][0]);coords[:,0]*=W/3840;coords[:,1]*=H/2160
mask=Image.new('L',(W,H));ImageDraw.Draw(mask).polygon([tuple(p) for p in coords],fill=255)
fontfile=str(ROOT/'fonts/Damascus.ttc')
fonts={size:ImageFont.truetype(fontfile,size) for size in [47,32,25]}
def smooth(keys,f):
 if f<=keys[0][0]:return keys[0][1]
 for (a,va),(b,vb) in zip(keys,keys[1:]):
  if f<=b:
   t=(f-a)/(b-a);t=t*t*(3-2*t);return va+(vb-va)*t
 return keys[-1][1]
def overlay_text(im,words,center,size,alpha,color=(255,255,255)):
 if alpha<=0:return
 layer=Image.new('RGBA',im.size);d=ImageDraw.Draw(layer);s=get_display(arabic_reshaper.reshape(words));font=fonts[size]
 box=d.textbbox((0,0),s,font=font);width=box[2]-box[0];height=box[3]-box[1]
 d.text((center[0]-width/2-box[0],center[1]-height/2-box[1]),s,font=font,fill=(*color,round(alpha*255)))
 im.alpha_composite(layer)
def frame(f):
 a=smooth([(240,0),(276,.78),(504,.78),(527,0)],f)
 highlight=Image.new('RGBA',(W,H),(244,158,52,0));highlight.putalpha(mask.point(lambda p:round(p*a)))
 mapped=Image.alpha_composite(base,highlight)
 zoom=smooth([(240,3.8),(288,4.15),(480,4.2),(527,4.2)],f)
 # Fusion Transform maps its pivot to Center before scaling.
 px=pivot[0]*W;py=(1-pivot[1])*H;cx=.5*W;cy=(1-.47)*H
 im=mapped.transform((W,H),Image.Transform.AFFINE,(1/zoom,0,px-cx/zoom,0,1/zoom,py-cy/zoom),Image.Resampling.BICUBIC)
 title=smooth([(240,0),(258,1),(504,1),(527,0)],f)
 layer=Image.new('RGBA',(W,H));d=ImageDraw.Draw(layer)
 d.rounded_rectangle((.21*W,.035*H,.79*W,.195*H),radius=18,fill=(4,31,36,round(title*.94*255)))
 sub=smooth([(360,0),(378,1),(504,1),(527,0)],f)
 d.rounded_rectangle((.09*W,.84*H,.91*W,.94*H),radius=15,fill=(4,31,36,round(sub*.92*255)))
 im.alpha_composite(layer)
 overlay_text(im,config['captions']['title'],(.5*W,.075*H),47,title)
 overlay_text(im,config['captions']['date'],(.5*W,.154*H),32,title,(245,179,79))
 price=smooth([(360,0),(378,1),(456,1),(474,0)],f)
 expansion=smooth([(474,0),(486,1),(504,1),(527,0)],f)
 overlay_text(im,config['captions']['price'],(.5*W,.89*H),25,price)
 overlay_text(im,config['captions']['expansion'],(.5*W,.89*H),25,expansion)
 return im.convert('RGB')
frame(408).save(ROOT/'Louisiana_Arabic_Preview.png')
sheet=Image.new('RGB',(1280,800),'#082e35');d=ImageDraw.Draw(sheet)
for i,f in enumerate([246,276,408,492]):
 thumb=frame(f).resize((640,360));x=(i%2)*640;y=(i//2)*400;sheet.paste(thumb,(x,y));d.text((x+15,y+368),f'{f/24:.2f}s / frame {f}',fill='white')
sheet.save(ROOT/'Louisiana_Storyboard.jpg')
cmd=['/opt/local/bin/ffmpeg','-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r','24','-i','pipe:0','-an','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',str(ROOT/'Louisiana_Arabic_Preview.mp4')]
p=subprocess.Popen(cmd,stdin=subprocess.PIPE)
for f in range(240,528):p.stdin.write(frame(f).tobytes())
p.stdin.close();assert p.wait()==0
print('Created 12-second offline MP4 preview, still and storyboard.')
