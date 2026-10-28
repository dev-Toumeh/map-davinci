import json
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

import numpy as np
from PIL import Image
import pytest

from fusion import region_closeup as rc


@pytest.fixture
def metadata():
    return {'detail': {'pixel_transform': {'origin_top_left_mercator': [0, 100000],
            'meters_per_pixel_x': 1000, 'meters_per_pixel_y': 1000}},
            'assets': {'satellite_detail': 'images/satellite_detail.png'},
            'imagery': {'source': 'esri_world_imagery'}}


def test_corridor_paths_and_geojson_agree(metadata):
    paths = {'paths': [[[10,20],[30,40]]], 'half_width_km': 3}
    _, lines, half = rc.area_geometry(paths, metadata)
    coords = [rc.exporter.merc_to_ll(*p) for p in lines[0]]
    geo = {'type': 'FeatureCollection', 'features': [{'type':'Feature', 'geometry':
            {'type':'LineString', 'coordinates': coords}}], 'half_width_km':3}
    a, b = rc.Region(paths,metadata), rc.Region(geo,metadata)
    assert np.allclose(a.targets,b.targets)
    assert half >= 3000
    assert np.max(a.distance) >= 3000


def test_polygon_holes_and_disjoint_polygons(metadata):
    area={'polygons': [
        [[[0,0],[1,0],[1,1],[0,1]], [[.3,.3],[.7,.3],[.7,.7],[.3,.7]]],
        [[[2,0],[2.1,0],[2.1,.1],[2,.1]]]]}
    r=rc.Region(area,metadata)
    assert r.alpha(*rc.exporter.ll_to_merc(.5,.5),1000)==0
    assert r.alpha(*rc.exporter.ll_to_merc(.1,.1),1000)==1
    assert r.alpha(*rc.exporter.ll_to_merc(2.05,.05),1000)==1


@pytest.mark.parametrize('area', [{'bbox':[1,0,0,1]}, {'paths':[]},
    {'polylines':[[[0,0],[181,1]]]}, {'polylines':[[[0,0]]]}])
def test_invalid_areas(area,metadata):
    with pytest.raises(ValueError): rc.Region(area,metadata)


def test_ordered_overlap_preserves_opacity_and_colour(metadata):
    r=rc.Region({'bbox':[-2,-2,2,2]},metadata)
    tiles=[rc.tile_spec(-20000,0,100),rc.tile_spec(20000,0,100),rc.tile_spec(0,0,100)]
    x=np.linspace(-205000,205000,1000)[None,:]; y=np.zeros_like(x)
    weights=np.array([rc.tile_weight(t,x,y) for t in tiles])
    total=weights.sum(0)
    expected=rc.smooth(np.minimum(total,1)) # only compare opaque interior below
    image=np.zeros(x.shape+(3,)); opacity=np.zeros(x.shape)
    colours=np.array([[50,100,150],[100,150,200],[150,200,250]])
    for i in range(len(tiles)):
        alpha=rc.tile_alpha(tiles,i,r,x,y,1000)
        image=image*(1-alpha[...,None])+colours[i]*alpha[...,None]
        opacity=opacity*(1-alpha)+alpha
    layer=np.clip(total,0,1)*r.alpha(x,y,1000)
    assert np.max(abs(opacity-layer)) < 1e-6
    desired=np.einsum('ijk,ic->jkc',weights,colours)/np.maximum(total[...,None],1e-10)*layer[...,None]
    assert np.max(abs(image-desired))<1e-4


def test_repair_fills_grey_and_black_and_matches_base():
    b=np.full((128,192,3),[100,130,150],dtype=np.uint8)
    a=np.full_like(b,[50,70,80]); a[:,:32]=0; a[:,32:64]=[78,95,103]
    out,fraction=rc.repair_match(Image.fromarray(a),Image.fromarray(b),62,1887)
    assert .32 < fraction < .35
    assert np.max(abs(out[:,:45].astype(int)-b[:,:45]))<=1
    assert np.max(abs(out[:,100:].astype(int)-b[:,100:]))<=2


def test_offline_build_cache_manifest_and_group(tmp_path,metadata,monkeypatch):
    (tmp_path/'json').mkdir();(tmp_path/'images').mkdir()
    (tmp_path/'json/metadata.json').write_text(json.dumps(metadata))
    Image.new('RGB',(100,100),(100,130,150)).save(tmp_path/'images/satellite_detail.png')
    original=rc.tile_spec
    monkeypatch.setattr(rc,'tile_spec',lambda x,y,m:original(x,y,m,(128,72)))
    monkeypatch.setattr(rc,'FEATHER',4)
    calls=[]
    def fetch(*args):
        calls.append(args)
        return Image.new('RGB',args[4],(80,100,120))
    monkeypatch.setattr(rc.exporter,'stitch_bbox',fetch)
    area={'bbox':[.1,.1,.2,.2]}
    result=rc.build_region_closeup(tmp_path,'Test',area,1000,plan={'centres':[[17000,17000,1000]]})
    assert result['coverage_min_weight'] == 1
    tile=result['tiles'][0]
    assert Image.open(tile['image_path']).mode=='RGBA'
    assert tile['world_width']==pytest.approx(2*128/100)
    assert tile['world_center']==pytest.approx([-.66,-.66])
    text=Path(result['setting_path']).read_text()
    assert text.count('GroupOperator')==1 and text.count('InstanceOutput')==1
    assert 'BezierSpline' not in text and 'KeyFrames' not in text
    assert 'ImagePlane3D' in text and 'Merge3D' in text
    rc.build_region_closeup(tmp_path,'Test',area,1000,plan={'centres':[[17000,17000,1000]]})
    assert len(calls)==1
    for value in [0,-1,float('nan')]:
        with pytest.raises(ValueError): rc.build_region_closeup(tmp_path,'Test',area,value)


def test_planner_covers_every_cell(metadata,monkeypatch):
    r=rc.Region({'bbox':[0,0,1,.4]},metadata)
    tiles=rc.plan_tiles(r,62)
    assert len(tiles)==1
    coverage=np.maximum.reduce([rc.tile_weight(t,*r.targets.T) for t in tiles])
    assert coverage.min()>.999
    assert all(t['size']==[3840,2160] for t in tiles)


def test_endpoint_job_and_validation(tmp_path,metadata,monkeypatch):
    import server
    package=tmp_path/'pkg';(package/'json').mkdir(parents=True)
    (package/'json/metadata.json').write_text(json.dumps(metadata))
    monkeypatch.setattr(server.app_settings,'exports_dir',lambda:tmp_path)
    seen=[]
    def build(package,name,area,mpp,progress):
        seen.append((name,area,mpp))
        return {'tiles':[{}],'setting_path':str(package/'a.setting'),'manifest_path':str(package/'manifest.json')}
    monkeypatch.setattr(rc,'build_region_closeup',build)
    http=ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
    thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
    base=f'http://127.0.0.1:{http.server_port}'
    def post(payload):
        return urlopen(Request(base+'/api/closeups/pkg/region',json.dumps(payload).encode(),{'Content-Type':'application/json'}))
    try:
        for data in [{'name':'../bad'}, {'name':'Good','mpp':0,'area':{'bbox':[0,0,1,1]}},
                     {'name':'Good','mpp':62,'area':{'bbox':[1,0,0,1]}}]:
            with pytest.raises(HTTPError) as error: post(data)
            assert error.value.code==400
        with post({'name':'Good','mpp':62,'area':{'bbox':[0,0,1,1]}}) as response:
            assert response.status==202
            job=json.load(response)['job_id']
        # The job is tiny; join the worker through bounded status polling.
        import time
        for _ in range(100):
            with urlopen(base+'/api/export/status/'+job) as response: result=json.load(response)
            if result['status']['stage']=='done': break
            time.sleep(.01)
        assert result['result']['setting_url']=='/exports/pkg/a.setting'
        assert seen==[('Good',{'bbox':[0,0,1,1]},62)]
    finally:
        http.shutdown();http.server_close();thread.join()


def test_coarse_plate_cannot_blur_a_sharp_city(metadata):
    r=rc.Region({'bbox':[-2,-2,2,2]},metadata)
    tiles=[rc.tile_spec(0,0,62),rc.tile_spec(0,0,90)]
    x=np.array([[0.,117000.,130000.]]);y=np.zeros_like(x)
    weights=rc.overlap_weights(tiles,x,y)
    assert weights[1][0,0]==0
    assert weights[0][0,1]>0 and weights[1][0,1]>0
    assert weights[0][0,2]==0 and weights[1][0,2]==1
    alpha=[rc.tile_alpha(tiles,i,r,x,y,5000) for i in range(2)]
    opacity=1-(1-alpha[0])*(1-alpha[1])
    assert np.max(abs(opacity-1))<1e-6
