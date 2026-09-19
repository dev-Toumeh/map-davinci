from pathlib import Path
import json, math, xml.etree.ElementTree as ET
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from shapely.geometry import shape,Polygon,mapping
from shapely.ops import unary_union,transform
from scipy.optimize import differential_evolution,least_squares,minimize
from scipy.ndimage import distance_transform_edt, binary_erosion, map_coordinates
from pyproj import Transformer
from svgpathtools import parse_path
ROOT=Path('/Users/naseemtoumeh/edit-projects/davinvi-resolve/usa'); HIST=ROOT/'assets/historical'
# Registration only: the educational GIS layer is not used to generate masks.
reference=json.loads((HIST/'louisiana_purchase.geojson').read_text())
geo=max([shape(f['geometry']) for f in reference['features'] if f.get('geometry')],key=lambda s:s.area)
geo=max(geo.geoms,key=lambda s:s.area)
forward=Transformer.from_crs(4326,5070,always_xy=True); inverse=Transformer.from_crs(5070,4326,always_xy=True)
gp=transform(forward.transform,geo)
atlas=shape(json.loads((HIST/'louisiana_atlas_coordinates.json').read_text()))
atlas=max(atlas.geoms,key=lambda s:s.area)
a=np.array(atlas.exterior.coords)
g=np.array(gp.exterior.coords)
# Estimate map scale and origin by matching full outline distance, not copying GIS vertices.
from scipy.spatial import cKDTree
atree=cKDTree(a); sample=g[::max(1,len(g)//1800)]
s=(atlas.bounds[3]-atlas.bounds[1])/(gp.bounds[3]-gp.bounds[1]); off=np.array(atlas.centroid.coords[0])-np.array(gp.centroid.coords[0])*s
params=minimize(lambda p:np.mean(np.minimum(atree.query(sample*p[0]+p[1:3])[0],12)**2),[s,*off],method='Nelder-Mead',options={'maxiter':1000,'xatol':1e-10}).x
scale,ox,oy=params
lon,lat=inverse.transform((a[:,0]-ox)/scale,(a[:,1]-oy)/scale)
# Fit the base map's projection against public-domain Natural Earth coastlines.
coasts=json.loads((HIST/'ne_110m_coastline.geojson').read_text())
pts=[]
for f in coasts['features']:
 coords=f['geometry']['coordinates']; lines=coords if f['geometry']['type']=='MultiLineString' else [coords]
 for line in lines:pts.extend(line)
pts=np.array(pts); pts=pts[(pts[:,1]>-58)&(pts[:,1]<66)]
# Longitude unwrap: this image is centered on North America rather than Greenwich.
clon=pts[:,0].copy();clon[clon>80]-=360
im=Image.open(ROOT/'assets/us-4k.png').convert('RGB'); small=im.resize((1600,900)); ar=np.array(small)
water=(ar[:,:,1]>40)&(ar[:,:,1]<150)&(ar[:,:,0]<60)&(ar[:,:,2]>40)&(ar[:,:,2]<150)
edge=water ^ binary_erosion(water); dist=distance_transform_edt(~edge)
x=clon; ym=np.log(np.tan(np.pi/4+np.radians(pts[:,1])/2)); ye=pts[:,1]
results=[]
for mode,y in [('mercator',ym),('equirectangular',ye)]:
 def objective(p):
  px=x*p[0]+p[1]; py=p[3]-y*p[2];valid=(px>2)&(px<1597)&(py>2)&(py<897)
  ds=map_coordinates(dist,[py[valid],px[valid]],order=1,mode='nearest')
  return np.mean(np.minimum(ds,35)**2)+max(0,.75-valid.mean())*1000
 bounds=[(3.8,5.1),(1120,1350),(180,360) if mode=='mercator' else (3,9),(340,620)]
 fit=differential_evolution(objective,bounds,seed=21,popsize=12,maxiter=130,tol=1e-8,polish=True)
 results.append((fit.fun,mode,fit.x))
score,mode,best=min(results,key=lambda t:t[0]); sx,xx,sy,yy=best
Y=lambda t:np.log(np.tan(np.pi/4+np.radians(t)/2)) if mode=='mercator' else t
px=(lon*sx+xx)*2.4;py=(yy-Y(lat)*sy)*2.4
aligned=Polygon(np.column_stack([px,py])).simplify(1.5,preserve_topology=True)
coords=np.array(aligned.exterior.coords)
# Store native, map-aligned editable geometry derived exclusively from the Atlas SVG.
(HIST/'louisiana_aligned_pixels.json').write_text(json.dumps(mapping(aligned)))
(HIST/'alignment.json').write_text(json.dumps({'atlas_scale':scale,'atlas_offset':[ox,oy],'base_projection':mode,'base_parameters':best.tolist(),'coastline_fit_rms_pixels_at_1600':math.sqrt(score),'geometry_source':'National Atlas public-domain SVG','registration_reference':'Educational GIS used only to estimate map registration; no GIS vertices copied to output.'},indent=2))
overlay=im.convert('RGBA'); layer=Image.new('RGBA',im.size);d=ImageDraw.Draw(layer);d.polygon([tuple(v) for v in coords],fill=(244,158,52,165),outline=(160,65,10,255));overlay=Image.alpha_composite(overlay,layer);overlay.resize((1600,900)).save(HIST/'louisiana_alignment_preview.png')
print('Atlas registration',params,'Base fit',score,mode,best,'Mask vertices',len(coords),'bounds',aligned.bounds)
