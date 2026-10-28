"""Always-visible, colour-matched region plates. Run with PYTHONPATH=app python -m fusion.region_closeup."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage, sparse
from scipy.optimize import milp, Bounds, LinearConstraint

from core import exporter, package_layout

MAX_SIZE = (3840, 2160)
FEATHER = 96


def smooth(x):
    x = np.clip(x, 0, 1)
    return x*x*(3-2*x)


def area_geometry(area, metadata):
    """Return Mercator polygon rings and buffered lines; paths files use detail pixels."""
    if isinstance(area, (str, Path)):
        area = json.loads(Path(area).expanduser().read_text())
    if 'file' in area:
        source = json.loads(Path(area['file']).expanduser().read_text())
        area = {**source, **{k: v for k, v in area.items() if k != 'file'}}
    t = metadata['detail']['pixel_transform']
    ox, oy = t['origin_top_left_mercator']
    def point(p, pixel=False):
        x, y = map(float, p[:2])
        if not math.isfinite(x+y):
            raise ValueError('Coordinates must be finite')
        if pixel:
            return (ox+x*t['meters_per_pixel_x'], oy-y*t['meters_per_pixel_y'])
        if not (-180 <= x <= 180 and -85.05 <= y <= 85.05):
            raise ValueError('Expected longitude/latitude coordinates')
        return exporter.ll_to_merc(x, y)
    polygons, lines = [], []
    def geometry(g):
        kind = g.get('type')
        if kind == 'FeatureCollection':
            for f in g['features']: geometry(f)
        elif kind == 'Feature': geometry(g['geometry'])
        elif kind == 'Polygon': polygons.append([[point(p) for p in ring] for ring in g['coordinates']])
        elif kind == 'MultiPolygon':
            for poly in g['coordinates']: polygons.append([[point(p) for p in ring] for ring in poly])
        elif kind == 'LineString': lines.append([point(p) for p in g['coordinates']])
        elif kind == 'MultiLineString': lines.extend([[point(p) for p in line] for line in g['coordinates']])
        else: raise ValueError('Use Polygon, MultiPolygon, LineString or MultiLineString GeoJSON')
    if 'type' in area: geometry(area)
    for poly in area.get('polygons', []):
        if isinstance(poly[0][0], (int, float)): poly = [poly]
        polygons.append([[point(p) for p in ring] for ring in poly])
    for line in area.get('polylines', []): lines.append([point(p) for p in line])
    for line in area.get('paths', []): lines.append([point(p, True) for p in line])
    if 'bbox' in area:
        x0, y0, x1, y1 = area['bbox']
        if x1 <= x0 or y1 <= y0: raise ValueError('bbox must be west,south,east,north')
        polygons.append([[point(p) for p in [(x0,y0),(x1,y0),(x1,y1),(x0,y1),(x0,y0)]]])
    if not polygons and not lines: raise ValueError('Area is empty')
    if any(len(ring) < 3 for poly in polygons for ring in poly) or any(len(line)<2 for line in lines):
        raise ValueError('A polygon needs three points; a line needs two')
    half = float(area.get('half_width_km', 25))
    if not 0 < half <= 500: raise ValueError('half_width_km must be in (0,500]')
    # A constant Mercator buffer using the region mean latitude.
    lat = np.mean([exporter.merc_to_ll(*p)[1] for line in lines for p in line]) if lines else 0
    return polygons, lines, half*1000/max(.087, math.cos(math.radians(lat)))


class Region:
    def __init__(self, area, metadata, resolution=500.):
        polygons, lines, half = area_geometry(area, metadata)
        pts = np.array([p for poly in polygons for ring in poly for p in ring] + [p for line in lines for p in line])
        pad = (half if lines else 0)+resolution*4
        lo, hi = pts.min(0)-pad, pts.max(0)+pad
        # Bound raster memory for continent-sized requests.
        self.r = max(resolution, math.sqrt(np.prod(hi-lo)/12_000_000))
        self.x0, self.y1 = lo[0], hi[1]
        size = tuple((np.ceil((hi-lo)/self.r).astype(int)+1))
        image = Image.new('1', size)
        def px(p): return ((p[0]-self.x0)/self.r, (self.y1-p[1])/self.r)
        for poly in polygons:
            part = Image.new('1',size); d = ImageDraw.Draw(part)
            d.polygon([px(p) for p in poly[0]], fill=1)
            for ring in poly[1:]: d.polygon([px(p) for p in ring],fill=0)
            image = Image.fromarray(np.asarray(image) | np.asarray(part))
        if lines:
            rail = Image.new('1',size); d=ImageDraw.Draw(rail)
            for line in lines: d.line([px(p) for p in line], fill=1, width=1)
            image = Image.fromarray(np.asarray(image) | (ndimage.distance_transform_edt(~np.asarray(rail))*self.r <= half))
        self.mask = np.asarray(image)
        self.distance = ndimage.distance_transform_edt(self.mask).astype(np.float32)*self.r
        yy, xx = np.where(self.mask)
        if not len(xx): raise ValueError('Area is smaller than the planning raster')
        self.targets = np.column_stack((self.x0+xx*self.r, self.y1-yy*self.r))

    def alpha(self, x, y, band):
        shape = np.broadcast_shapes(np.shape(x),np.shape(y))
        coords = np.array([np.broadcast_to((self.y1-y)/self.r,shape).ravel(),
                           np.broadcast_to((x-self.x0)/self.r,shape).ravel()])
        return smooth(ndimage.map_coordinates(self.distance, coords, order=1, mode='constant').reshape(shape)/band)


def tile_spec(cx, cy, mpp, size=MAX_SIZE):
    w,h = map(int,size)
    if not (0 < w <= 3840 and 0 < h <= 2160 and math.isfinite(mpp) and mpp > 0):
        raise ValueError('Invalid tile size or m/px')
    return {'bbox_mercator':[cx-w*mpp/2,cy-h*mpp/2,cx+w*mpp/2,cy+h*mpp/2],
            'size':[w,h], 'meters_per_pixel':float(mpp)}


def tile_weight(tile, x, y):
    x0,y0,x1,y1=tile['bbox_mercator']; band=FEATHER*tile['meters_per_pixel']
    return smooth(np.minimum(x-x0,x1-x)/band)*smooth(np.minimum(y-y0,y1-y)/band)


def plan_tiles(region, mpp):
    """Minimize tile count on a finite overlapping candidate grid (not a global proof)."""
    mpp=float(mpp)
    if not math.isfinite(mpp) or mpp <= 0: raise ValueError('m/px must be positive and finite')
    pts=region.targets
    # All pixels are checked after planning; use a modest sample for the integer solve.
    pts=pts[::max(1,len(pts)//12000)]
    lo,hi=pts.min(0),pts.max(0)
    w,h=(np.array(MAX_SIZE)-2*FEATHER)*mpp
    candidates=[]; rows=[]; cols=[]
    for cy in np.arange(lo[1]-h/4,hi[1]+h/2,h/4):
        for cx in np.arange(lo[0]-w/4,hi[0]+w/2,w/4):
            hits=np.where((abs(pts[:,0]-cx)<w/2-region.r)&(abs(pts[:,1]-cy)<h/2-region.r))[0]
            if len(hits):
                cols.extend([len(candidates)]*len(hits)); rows.extend(hits)
                candidates.append(tile_spec(cx,cy,mpp))
    matrix=sparse.csc_matrix((np.ones(len(rows)),(rows,cols)),shape=(len(pts),len(candidates)))
    result=milp(np.ones(len(candidates)),integrality=np.ones(len(candidates)),bounds=Bounds(0,1),
                constraints=LinearConstraint(matrix,1,np.inf), options={'time_limit':45,'mip_rel_gap':.01})
    if result.x is None: raise ValueError('Could not cover area at this resolution')
    tiles=[t for t,v in zip(candidates,result.x) if v>.5]
    # Repair any coverage missed by the sampled solve, without dropping any area.
    coverage=np.zeros(len(region.targets))
    for t in tiles: coverage=np.maximum(coverage,tile_weight(t,*region.targets.T))
    while np.any(coverage<.999):
        p=region.targets[np.where(coverage<.999)[0][0]]
        tile=tile_spec(*p,mpp); tiles.append(tile)
        coverage=np.maximum(coverage,tile_weight(tile,*region.targets.T))
    return tiles


def sample_detail(detail, metadata, bbox, size):
    t=metadata['detail']['pixel_transform']; ox,oy=t['origin_top_left_mercator']
    x0,y0,x1,y1=bbox
    box=((x0-ox)/t['meters_per_pixel_x'],(oy-y1)/t['meters_per_pixel_y'],
         (x1-ox)/t['meters_per_pixel_x'],(oy-y0)/t['meters_per_pixel_y'])
    return detail.transform(tuple(size),Image.Transform.EXTENT,box,Image.Resampling.BICUBIC)


def repair_match(plate, under, mpp, detail_mpp):
    """Bahrain black/Esri-grey repair, then replace low spatial frequencies with base colours."""
    a=np.asarray(plate.convert('RGB')).astype(np.float32)
    b=np.asarray(under.convert('RGB')).astype(np.float32)
    missing=(a.max(2)<=2) | (abs(a-np.array([78,95,103])).max(2)<=8)
    mask=Image.fromarray((missing*255).astype('uint8')).filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(10))
    k=np.asarray(mask,dtype=np.float32)[...,None]/255
    # Estimate imagery tone using valid samples only. Including the repaired holes
    # in the low-pass would create a dark/bright ring around no-data boundaries.
    small=(max(1,round(plate.width*mpp/(detail_mpp/2))),max(1,round(plate.height*mpp/(detail_mpp/2))))
    good=(~missing).astype(np.float32)
    def reduce_float(values):
        return np.asarray(Image.fromarray(values.astype(np.float32)).resize(small,Image.Resampling.BOX))
    valid=ndimage.gaussian_filter(reduce_float(good),.75)
    lows=[]
    for c in range(3):
        numerator=ndimage.gaussian_filter(reduce_float(a[:,:,c]*good),.75)
        fallback=reduce_float(b[:,:,c])
        low=np.divide(numerator,valid,out=fallback.copy(),where=valid>1e-5)
        lows.append(np.asarray(Image.fromarray(low).resize(plate.size,Image.Resampling.BILINEAR)))
    low=np.stack(lows,2)
    # Reinsert high-frequency imagery over the exact geographically sampled base.
    # Offshore Esri scene mosaics have hard colour blocks unrelated to geography.
    # Keep land texture at full strength, blend blue/green water texture toward the
    # package's water so those source scene boundaries do not become map seams.
    water=smooth((np.maximum(a[:,:,1],a[:,:,2])-a[:,:,0]-5)/20)
    water*=smooth((170-a.max(2))/70)
    texture=(1-.95*water)[...,None]
    out=(b+(a-low)*(1-k)*texture).clip(0,255)
    return out.astype('uint8'),float(missing.mean())


def overlap_weights(tiles, x, y):
    weights=[tile_weight(t,x,y) for t in tiles]
    finest=min(t['meters_per_pixel'] for t in tiles)
    sharp=np.clip(np.sum([w for t,w in zip(tiles,weights) if t['meters_per_pixel'] <= finest*1.01],axis=0),0,1)
    # Coarse plates may fill gaps, but must not reduce sharp railway/city detail.
    return [w*(1-sharp) if t['meters_per_pixel']>finest*1.01 else w for t,w in zip(tiles,weights)]


def tile_alpha(tiles, index, region, x, y, band):
    weights=overlap_weights(tiles,x,y)
    total=np.sum(weights,axis=0)
    # Desired premultiplied contributions sum to layer_alpha. Convert to over alphas
    # for back-to-front Z order so overlaps never accumulate opacity or darken.
    layer=region.alpha(x,y,band)*np.clip(total,0,1)
    above=np.sum(weights[index+1:],axis=0) if index+1<len(tiles) else np.zeros_like(total)
    return np.clip(layer*weights[index]/np.maximum(total-layer*above,1e-10),0,1)


def write_setting(name, tiles, path):
    nodes=[]; inputs=[]
    for i,t in enumerate(tiles):
        n=f'{name}_Tile_{i+1:02d}'; x=(i%5)*330; y=(i//5)*132
        filename=json.dumps(str(Path(t['image_path']).resolve()))
        nodes.append(f'{n}_Loader = Loader {{ Clips = {{ Clip {{ ID = "Clip1", Filename = {filename}, Length = 1, TrimOut = 0, ExtendFirst = 0, ExtendLast = 0, Loop = 1 }} }}, ViewInfo = OperatorInfo {{ Pos = {{ {x}, {y} }} }}, }},')
        wx,wy=t['world_center']; scale=t['world_width']
        values={'Transform3DOp.Translate.X':wx,'Transform3DOp.Translate.Y':wy,'Transform3DOp.Translate.Z':t['z'],
                'Transform3DOp.Scale.X':scale,'Transform3DOp.Scale.Y':scale,'Transform3DOp.Scale.Z':scale,'MtlStdInputs.UseTwoSidedLighting':1}
        ins=', '.join(f'[{json.dumps(k)}] = Input {{ Value = {v:.14g} }}' for k,v in values.items())
        nodes.append(f'{n}_Plane = ImagePlane3D {{ Inputs = {{ {ins}, MaterialInput = Input {{ SourceOp = "{n}_Loader", Source = "Output" }} }}, ViewInfo = OperatorInfo {{ Pos = {{ {x+110}, {y} }} }}, }},')
        inputs.append(f'SceneInput{i+1} = Input {{ SourceOp = "{n}_Plane", Source = "Output" }}')
    nodes.append(f'{name}_Merge = Merge3D {{ Inputs = {{ '+', '.join(inputs)+f' }}, ViewInfo = OperatorInfo {{ Pos = {{ 770, 462 }} }}, }},')
    path.write_text('{ Tools = ordered() { '+name+'_Closeup = GroupOperator { Outputs = { MainOutput1 = InstanceOutput { SourceOp = "'+name+'_Merge", Source = "Output" } }, ViewInfo = GroupInfo { Pos = { 0, 0 } }, Tools = ordered() {\n'+'\n'.join(nodes)+'\n} } }, ActiveTool = "'+name+'_Closeup" }\n')


def build_region_closeup(package, name, area, target_mpp, *, plan=None, progress=None):
    package=Path(package).resolve()
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,79}',name): raise ValueError('Name must be a Fusion identifier')
    target_mpp=float(target_mpp)
    if not math.isfinite(target_mpp) or target_mpp<=0: raise ValueError('m/px must be positive and finite')
    metadata=json.loads(package_layout.metadata_path(package).read_text())
    region=Region(area,metadata)
    tiles=([tile_spec(*c) for c in plan['centres']] if plan else plan_tiles(region,target_mpp))
    # Verify EVERY raster cell, not the capacity solver's downsampled targets.
    coverage=np.zeros(len(region.targets))
    for t in tiles: coverage=np.maximum(coverage,tile_weight(t,*region.targets.T))
    if np.any(coverage<.999):
        # A supplied capacity plan may miss raster boundary slivers. One extra tile is
        # preferable to silently omitting the requested corridor.
        pts=region.targets[coverage<.999]
        if np.ptp(pts[:,0])< (3840-2*FEATHER)*target_mpp and np.ptp(pts[:,1])<(2160-2*FEATHER)*target_mpp:
            tiles.append(tile_spec(*((pts.min(0)+pts.max(0))/2),target_mpp))
        else:
            raise ValueError(f'Plan leaves {len(pts)} raster cells uncovered; replan required')
    source_key=metadata.get('imagery',{}).get('source','esri_world_imagery')
    source=exporter.SOURCES[source_key]
    identity={'name':name,'area':area,'tiles':tiles,'source':source_key,'algorithm':1}
    signature=hashlib.sha256(json.dumps(identity,sort_keys=True,default=str).encode()).hexdigest()[:12]
    folder=package/package_layout.closeups_relative(package)/f'{name}_{signature}'
    folder.mkdir(parents=True,exist_ok=True)
    detail=Image.open(package/metadata.get('assets',{}).get('satellite_detail','images/satellite_detail.png')).convert('RGB')
    tr=metadata['detail']['pixel_transform']; ox,oy=tr['origin_top_left_mercator']; dm=tr['meters_per_pixel_x']
    world_per_m=2/(detail.width*dm)
    progress=progress or (lambda *args: None)
    band=FEATHER*target_mpp
    for i,t in enumerate(tiles):
        bbox=t['bbox_mercator']; x0,y0,x1,y1=bbox; w,h=t['size']; mpp=t['meters_per_pixel']
        t['world_center']=[((x0+x1)/2-ox)*world_per_m-1,(oy-(y0+y1)/2)*-world_per_m+detail.height/detail.width]
        t['world_width']=(x1-x0)*world_per_m
        t['bbox_world']=[(x0-ox)*world_per_m-1,(oy-y0)*-world_per_m+detail.height/detail.width,
                         (x1-ox)*world_per_m-1,(oy-y1)*-world_per_m+detail.height/detail.width]
        t['z']=.00049+i*.00002/max(1,len(tiles)-1)
        t['image_path']=str(folder/f'tile_{i+1:02d}.png')
        raw=folder/f'raw_{i+1:02d}.png'
        lat=exporter.merc_to_ll((x0+x1)/2,(y0+y1)/2)[1]
        zoom,_=exporter.choose_tile_zoom(mpp*math.cos(math.radians(lat)),lat,source['max_zoom'])
        t['tile_zoom']=zoom
        if not raw.exists():
            progress('fetch',100*i/len(tiles),f'Tile {i+1}/{len(tiles)} z{zoom}')
            plate=exporter.stitch_bbox(source,source_key,zoom,tuple(bbox),(w,h),progress,f'tile_{i+1}')
            plate.save(raw)
        else: plate=Image.open(raw).convert('RGB')
        under=sample_detail(detail,metadata,bbox,(w,h))
        rgb,t['missing_fraction']=repair_match(plate,under,mpp,dm)
        alpha=np.zeros((h,w),dtype=np.float32)
        for row in range(0,h,128):
            x=x0+(np.arange(w)[None,:]+.5)*mpp
            y=y1-(np.arange(row,min(h,row+128))[:,None]+.5)*mpp
            alpha[row:row+128]=tile_alpha(tiles,i,region,x,y,band)
        Image.fromarray(np.dstack((rgb,np.rint(alpha*255).astype('uint8')))).save(t['image_path'])
        progress('process',100*(i+1)/len(tiles),f'Tile {i+1}/{len(tiles)} repaired and feathered')
    setting=folder/f'{name}_Closeup.setting'
    write_setting(name,tiles,setting)
    manifest={'name':name,'source':source_key,'target_meters_per_pixel':target_mpp,'units':'EPSG:3857 Mercator metres; ground m/px = m/px * cos(latitude)',
              'area':area,'region_raster_m':region.r,'feather_m':band,'overlap':'normalized weights converted to back-to-front over alpha; ascending Z',
              'coverage_min_weight':float(min(np.maximum.reduce([tile_weight(t,*region.targets.T) for t in tiles]))),
              'tiles':tiles,'setting_path':str(setting),'manifest_path':str(folder/'manifest.json')}
    (folder/'manifest.json').write_text(json.dumps(manifest,indent=2,default=str))
    return manifest


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('package',type=Path);p.add_argument('name');p.add_argument('--area',required=True,type=Path)
    p.add_argument('--mpp',required=True,type=float);p.add_argument('--plan',type=Path)
    a=p.parse_args()
    result=build_region_closeup(a.package,a.name,json.loads(a.area.read_text()),a.mpp,
                               plan=json.loads(a.plan.read_text()) if a.plan else None,
                               progress=lambda s,p,m: print(f'{s} {p:.0f}% {m}',flush=True))
    print(result['manifest_path'])

if __name__=='__main__': main()
