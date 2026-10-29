"""Stage the user-requested L2-only RF voids, VIN_P via cleanup and B.Mask exposure."""
from pathlib import Path
import argparse, hashlib, json, math, shutil, struct, uuid
import olefile
from shapely.geometry import Point, Polygon, box
from shapely.affinity import rotate
from shapely.ops import unary_union
from shapely import set_precision
from native_update import ROOT, blocks, parse, props, records, rec, point, mil, update_copy

S=ROOT/'staging/layer_mask_via_fix_20261028';R=ROOT/'review'
INTENT=ROOT/'layer_mask_via_intent.json'

def padshape(p):
    x,y=p['pos'];w,h=p['size']
    q=Point(x,y).buffer(w/2,resolution=48) if p['shape']==0 else box(x-w/2,y-h/2,x+w/2,y+h/2)
    return rotate(q,-p['angle'],origin=(x,y))

def protection(g):
    # Preserve independent solder openings on actual pads. Exclude their vicinity
    # from the new large opening, including top pin projections except the EP.
    pins=[padshape(p).buffer(.30,join_style=2) for p in g['pads'] if (p['ref'],p['num'])!=('U1','17')]
    vias=[Point(v['pos']).buffer(v['diameter']/2+.30,resolution=32) for v in g['vias'] if v['net']!='GND']
    return unary_union(pins+vias)

def polygons(q):return list(q.geoms) if q.geom_type=='MultiPolygon' else [q]
def serialize(q):return dict(outline=[list(p) for p in list(q.exterior.coords)[:-1]],holes=[[list(p) for p in list(h.coords)[:-1]] for h in q.interiors])

def put(updates,name,rows):
    updates[name+'/Data']=b''.join(rows);updates[name+'/Header']=struct.pack('<I',len(rows))

def reindex(streams,updates,changed):
    old=streams['PrimitiveGuids/Data'];tags={'Vias6':3843,'Regions6':4953,'ShapeBasedRegions6':5209}
    rows=[old[i:i+24] for i in range(0,len(old),24) if struct.unpack_from('<I',old,i)[0] not in {tags[n] for n in changed}]
    for name,n in changed.items():
        rows += [struct.pack('<II',tags[name],i)+uuid.uuid5(uuid.NAMESPACE_URL,f'qstl/layer-mask-vias/{name}/{i}').bytes_le for i in range(n)]
    put(updates,'PrimitiveGuids',rows)

def streams_of(path):
    with olefile.OleFileIO(path) as o:return {'/'.join(k):o.openstream(k).read() for k in o.listdir()}

def plan():
    S.mkdir(exist_ok=False)
    pcb=ROOT/'QSTL_THS3491_RGT_G20_RevD.PcbDoc'
    shutil.copy2(pcb,S/'before.PcbDoc');shutil.copy2(pcb.with_suffix('.SchDoc'),S/'before.SchDoc')
    shutil.copytree(R,S/'review_before',ignore=shutil.ignore_patterns('*.png','*.svg'))
    g=json.loads((R/'native_geometry.json').read_text())
    removed_z=[z for z in g['zones'] if z['keepout'] and z['layer'] in ['In2.Cu','B.Cu']]
    assert len(removed_z)==6
    g['zones']=[z for z in g['zones'] if z not in removed_z]
    vin=Polygon(next(z['outline'] for z in g['zones'] if z['name']=='L1_POSITIVE_INPUT'))
    removed_v=[v for v in g['vias'] if v['net']=='GND' and vin.distance(Point(v['pos']))<v['diameter']/2+.205-1e-5]
    assert len(removed_v)==12
    g['vias']=[v for v in g['vias'] if v not in removed_v]
    intent=dict(request='Remove RF cutouts on L3/L4 only, remove GND vias clipping VIN_P, expose broad bottom GND except component/connector pin vicinity.',
        baseline_pcb_sha256=hashlib.sha256(pcb.read_bytes()).hexdigest(),
        removed_cutouts=[{k:v for k,v in z.items() if k!='filled'} for z in removed_z],removed_ground_vias=removed_v,
        pin_mask_margin_mm=.30,non_GND_via_mask_margin_mm=.30,board_mask_border_mm=.50,
        mask_scope='Broad bottom GND; project component pins except U1 EP; retain existing pad solder openings and H9 solder pad.')
    INTENT.write_text(json.dumps(intent,indent=2)+'\n');(S/'geometry.json').write_text(json.dumps(g,indent=2))
    streams=streams_of(pcb);updates={};changed={}
    via_rows=[]
    for raw in records(streams['Vias6/Data'],3):
        xy=struct.unpack_from('<ii',raw,13)
        if any(math.dist(xy,point(v['pos']))<10 for v in removed_v):continue
        via_rows.append(rec(3,raw))
    assert len(via_rows)==len(g['vias']);put(updates,'Vias6',via_rows);changed['Vias6']=len(via_rows)
    for name in ['Regions6','ShapeBasedRegions6']:
        rows=[];count=0
        for raw in records(streams[name+'/Data'],11):
            n=struct.unpack_from('<I',raw,18)[0];p=parse(raw[22:22+n])
            if raw[0] in [3,32] and p.get('KIND')=='1' and struct.unpack_from('<H',raw,5)[0]==65535:
                count+=1;continue
            rows.append(rec(11,raw))
        assert count==6,(name,count)
        put(updates,name,rows);changed[name]=len(rows)
    reindex(streams,updates,changed);update_copy(pcb,S/'hardware.PcbDoc',updates)
    print('Staged 6 cutout removals and 12 VIN_P GND via removals')

def mask(output):
    g=json.loads((R/'native_geometry.json').read_text());intent=json.loads(INTENT.read_text())
    ground=unary_union([Polygon(f['outline'],f['holes']).buffer(0) for z in g['zones'] if not z['keepout'] and z['layer']=='B.Cu' and z['net']=='GND' for f in z['filled']])
    # A small inward margin prevents numerical overshoot into non-copper after native coordinate quantization.
    q=ground.buffer(-.01).intersection(box(.5,.5,g['board_width']-.5,g['board_height']-.5)).difference(protection(g).buffer(.002,join_style=2))
    # Quantize to 1 um before the 2.54 nm Altium grid. This removes zero-width
    # slivers at tangencies while the 2 um guard preserves >=0.30 mm mask webs.
    q=set_precision(q,.001)
    ps=[p for p in polygons(q) if p.area>.05]
    assert sum(p.area for p in ps)>2000
    intent['bottom_mask_regions']=[serialize(p) for p in ps]
    intent['exposed_ground_area_mm2']=sum(p.area for p in ps)
    INTENT.write_text(json.dumps(intent,indent=2)+'\n')
    source=S/'filled.PcbDoc';streams=streams_of(source);updates={};changed={}
    # Free shapes belong only in ShapeBasedRegions6. Altium creates Regions6
    # cache records on save; placing free solids in both streams duplicates them.
    for name,extended in [('ShapeBasedRegions6',True)]:
        rows=[rec(11,raw) for raw in records(streams[name+'/Data'],11)]
        for i,f in enumerate(intent['bottom_mask_regions']):
            h=bytearray(18);h[0]=38;h[1]=12
            struct.pack_into('<5H',h,3,65535,65535,65535,65535,65535);struct.pack_into('<H',h,14,len(f['holes']))
            p=dict(V7_LAYER='BOTTOMSOLDER',NAME='BOTTOM_GND_EXPOSURE_'+str(i),KIND=0,SUBPOLYINDEX=65535,UNIONINDEX=0,ARCRESOLUTION=mil(.02),ISSHAPEBASED='TRUE' if extended else 'FALSE',ISBOARDCUTOUT='FALSE')
            raw=bytes(h)+props(p)+struct.pack('<I',len(f['outline']))
            if extended:raw+=b''.join(struct.pack('<B5i2d',0,*point(v),0,0,0,0.,0.) for v in f['outline']+[f['outline'][0]])
            else:raw+=b''.join(struct.pack('<2d',*point(v)) for v in f['outline'])
            for hole in f['holes']:raw+=struct.pack('<I',len(hole))+b''.join(struct.pack('<2d',*point(v)) for v in hole)
            rows.append(rec(11,raw))
        put(updates,name,rows);changed[name]=len(rows)
    reindex(streams,updates,changed);update_copy(source,output,updates)
    print('Broad bottom GND opening:',len(ps),'regions,',sum(len(p.interiors) for p in ps),'protected islands,',intent['exposed_ground_area_mm2'],'mm2')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['plan','mask']);p.add_argument('--output',type=Path,default=S/'candidate.PcbDoc');a=p.parse_args()
    plan() if a.mode=='plan' else mask(a.output)
