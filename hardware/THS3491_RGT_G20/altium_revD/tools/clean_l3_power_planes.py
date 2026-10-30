"""Replace perforated L3 supply shapes with clean planes and remove crossing GND vias."""
from pathlib import Path
import hashlib,json,math,re,shutil,struct,uuid
import olefile
from shapely.geometry import Polygon,Point,LineString
from shapely.ops import unary_union
from native_update import ROOT,blocks,parse,props,records,rec,point,mil,update_copy
R=ROOT/'review';S=ROOT/'staging/l3_plane_cleanup_20261030';B=R/'l3_cleanup_baseline'
OUTLINES={
 'VCC':[[19.2,8.9],[28.2,8.9],[28.2,12.8],[23.2,12.8],[23.2,25.5],[30.4,25.5],[30.4,31.25],[24.4,31.25],[24.4,30.35],[29.4,30.35],[29.4,26.7],[17.9,26.7],[17.35,26.15],[17.35,24.0],[20.2,24.0],[20.2,13.6]],
 'VEE':[[18.5,29.3],[22.0,29.3],[22.0,31.75],[25.7,31.75],[25.7,33.1],[22.0,33.1],[22.0,46.98],[9.39202,46.98],[9.39202,43.31861],[17.0,43.31861],[17.0,34.2],[20.3,34.2],[20.3,31.4],[18.5,31.4]]}
BRANCHES={
 'VCC':dict(centerline=[[21.0,26.1],[29.9,26.1],[29.9,30.8],[24.9,30.8]],minimum_width_mm=.90),
 'VEE':dict(centerline=[[19.4,30.7],[21.15,30.7],[21.15,32.425],[24.9,32.425]],minimum_width_mm=1.0)}

def build():
    pcb=ROOT/'QSTL_THS3491_RGT_G20_RevD.PcbDoc';g=json.loads((R/'native_geometry.json').read_text())
    digest=hashlib.sha256(pcb.read_bytes()).hexdigest();assert digest==json.loads((R/'native_import_check.json').read_text())['source_sha256']
    planes={n:Polygon(p) for n,p in OUTLINES.items()};power=unary_union(list(planes.values()))
    windows=unary_union([Polygon(z['outline']) for z in g['zones'] if z['keepout'] and z['layer']=='In1.Cu'])
    assert all(q.is_valid and not q.interiors for q in planes.values())
    assert power.distance(windows)>.20 and planes['VCC'].distance(planes['VEE'])>=.5-1e-6
    removed=[v for v in g['vias'] if v['net']=='GND' and power.distance(Point(v['pos']))<v['diameter']/2+.225]
    existing=json.loads((R/'vias.json').read_text())
    protected=[v for v in existing if v['net']=='GND' and 'via-in-pad' in v['group'] and any(math.dist(v['pos'],q['pos'])<.00001 for q in g['vias'])]
    assert not any(math.dist(v['pos'],q['pos'])<.00001 for v in protected for q in removed)
    for net,poly in planes.items():assert all(poly.covers(Point(v['pos']).buffer(v['diameter']/2+.01)) for v in g['vias'] if v['net']==net)
    S.mkdir(exist_ok=False);B.mkdir(exist_ok=False)
    for ext in ['PcbDoc','SchDoc']:shutil.copy2(pcb.with_suffix('.'+ext),B/('before.'+ext))
    (B/'review_before').mkdir()
    for name in ['native_geometry.json','native_import_copper.json','validation_summary.json','remove_tp1_check.json','native_import_cutouts.json']:
        shutil.copy2(R/name,B/'review_before'/name)
    (B/'README.md').write_text('Historical baseline before the 2026-10-30 L3 plane cleanup. Current CAD files are in the parent altium_revD directory.\n')
    specs=[]
    for net,outline in OUTLINES.items():
        z=next(z for z in g['zones'] if z['name']=='L3_'+net)
        specs.append(dict(net=net,name=z['name'],before_outline=z['outline'],outline_mm=outline,branch=BRANCHES[net]))
        z['outline']=outline;z.pop('filled',None)
    g['vias']=[v for v in g['vias'] if v not in removed]
    intent=dict(request='Clean L3 power planes, connect C7 using broad plane branches, avoid the L2 RF windows, and remove overlapping GND stitching vias.',
        baseline_pcb_sha256=digest,baseline_schematic_sha256=hashlib.sha256((B/'before.SchDoc').read_bytes()).hexdigest(),
        planes=specs,removed_ground_vias=removed,protected_ground_via_in_pad=protected,
        minimum_ground_via_copper_to_plane_outline_mm=.225,minimum_L2_RF_window_projection_clearance_mm=.20,
        minimum_plane_to_plane_outline_clearance_mm=.5,
        interpretation='Avoid the vertical projection of L2 RF copper windows. The outer VCC connection crosses the output trace only where uninterrupted L2 GND remains between L1 and L3.',
        preserved=['all parts and pads','all supply vias','U1 EP thermal vias and surviving GND via-in-pad','mounting rings and edge vias','L1 signal tracks and RF arcs','all L2 cutouts','bottom mask','schematic','26 embedded models'])
    (ROOT/'l3_cleanup_intent.json').write_text(json.dumps(intent,indent=2)+'\n');(S/'geometry.json').write_text(json.dumps(g,indent=2))
    with olefile.OleFileIO(pcb) as o:streams={'/'.join(k):o.openstream(k).read() for k in o.listdir()}
    polys=[parse(q) for q in blocks(streams['Polygons6/Data'])]
    for q in polys:
        name=''.join(chr(int(c)) for c in q['NAME'].split(','))
        if name not in ['L3_VCC','L3_VEE']:continue
        for k in list(q):
            if re.fullmatch(r'(KIND|VX|VY|CX|CY|SA|EA|R)\d+',k):del q[k]
        outline=OUTLINES[name[3:]]
        for i,(x,y) in enumerate(outline+[outline[0]]):q.update({f'KIND{i}':0,f'VX{i}':mil(x),f'VY{i}':mil(68.58-y),f'CX{i}':'0mil',f'CY{i}':'0mil',f'SA{i}':0,f'EA{i}':0,f'R{i}':'0mil'})
    updates={'Polygons6/Data':b''.join(props(q) for q in polys),'Polygons6/Header':struct.pack('<I',len(polys))}
    vias=[]
    for raw in records(streams['Vias6/Data'],3):
        xy=struct.unpack_from('<ii',raw,13)
        if any(math.dist(xy,point(v['pos']))<10 for v in removed):continue
        vias.append(rec(3,raw))
    assert len(vias)==len(g['vias']);updates.update({'Vias6/Data':b''.join(vias),'Vias6/Header':struct.pack('<I',len(vias))})
    ids=streams['PrimitiveGuids/Data'];rows=[ids[i:i+24] for i in range(0,len(ids),24) if struct.unpack_from('<I',ids,i)[0] not in [1034,3843]]
    for tag,items in [(1034,polys),(3843,vias)]:rows += [struct.pack('<II',tag,i)+uuid.uuid5(uuid.NAMESPACE_URL,f'qstl/l3-cleanup/{tag}/{i}').bytes_le for i in range(len(items))]
    updates.update({'PrimitiveGuids/Data':b''.join(rows),'PrimitiveGuids/Header':struct.pack('<I',len(rows))})
    update_copy(pcb,S/'outline.PcbDoc',updates)
    print('L3 outline cleanup: removed',len(removed),'GND vias; remaining',len(g['vias']),'RF window gap',power.distance(windows))

if __name__=='__main__':build()
