"""Add equally spaced GND via rings around the four existing mounting holes."""
from pathlib import Path
import hashlib,json,math,shutil,struct,uuid
import olefile
from shapely.geometry import Polygon,Point
from shapely.ops import unary_union
from native_update import ROOT,blocks,parse,records,rec,point,unit,update_copy
R=ROOT/'review';S=ROOT/'staging/mount_hole_rings_20261028'

def build():
    S.mkdir(exist_ok=False);pcb=ROOT/'QSTL_THS3491_RGT_G20_RevD.PcbDoc'
    shutil.copy2(pcb,S/'before.PcbDoc');shutil.copy2(pcb.with_suffix('.SchDoc'),S/'before.SchDoc')
    shutil.copytree(R,S/'review_before',ignore=shutil.ignore_patterns('*.png','*.svg'))
    g=json.loads((R/'native_geometry.json').read_text())
    holes=sorted([p for p in g['pads'] if p['npth']],key=lambda p:p['ref'])
    assert [p['ref'] for p in holes]==['H1','H2','H3','H4']
    ground={l:unary_union([Polygon(f['outline'],f['holes']).buffer(0) for z in g['zones'] if z['layer']==l and z['net']=='GND' and not z['keepout'] for f in z['filled']]) for l in ['F.Cu','In1.Cu','In2.Cu','B.Cu']}
    added=[];rings=[]
    for h in holes:
        positions=[]
        for i in range(24):
            angle=2*math.pi*i/24
            pos=[round(h['pos'][0]+3.4*math.cos(angle),6),round(h['pos'][1]+3.4*math.sin(angle),6)]
            assert all(c.covers(Point(pos).buffer(.201)) for c in ground.values())
            assert all(math.dist(pos,v['pos'])>v['diameter']/2+.2+.052 for v in g['vias']+added)
            positions.append(pos);added.append(dict(net='GND',pos=pos,diameter=.4,drill=.2))
        rings.append(dict(ref=h['ref'],center_mm=h['pos'],hole_diameter_mm=h['drill'][0],radius_mm=3.4,positions_mm=positions,count=24,angle_step_degrees=15))
    g['vias']+=added
    intent=dict(request='Circular ground via arrays around mechanical mounting holes.',
        baseline_pcb_sha256=hashlib.sha256(pcb.read_bytes()).hexdigest(),rings=rings,added_ground_vias=added,
        diameter_mm=.4,drill_mm=.2,radius_mm=3.4,screw_head_review_diameter_mm=6.0,
        screw_head_to_via_copper_clearance_mm=.2,adjacent_via_center_pitch_mm=6.8*math.sin(math.pi/24),
        unchanged=['mounting holes and board outline','all existing vias','RF fence','components and pads','tracks and arcs','all copper polygons and cutouts','bottom mask','schematic','3D models'])
    (ROOT/'mount_hole_ring_intent.json').write_text(json.dumps(intent,indent=2)+'\n');(S/'geometry.json').write_text(json.dumps(g,indent=2))
    with olefile.OleFileIO(pcb) as o:streams={'/'.join(k):o.openstream(k).read() for k in o.listdir()}
    nets={parse(b)['NAME']:i for i,b in enumerate(blocks(streams['Nets6/Data']))};vs=list(records(streams['Vias6/Data'],3))
    sample=next(v for v in vs if struct.unpack_from('<H',v,3)[0]==nets['GND'] and abs(struct.unpack_from('<i',v,21)[0]*.00000254-.4)<.00001)
    rows=[rec(3,v) for v in vs]
    for v in added:
        raw=bytearray(sample);struct.pack_into('<5H',raw,3,nets['GND'],65535,65535,65535,65535)
        struct.pack_into('<4i',raw,13,*point(v['pos']),unit(.4),unit(.2));rows.append(rec(3,raw))
    updates={'Vias6/Data':b''.join(rows),'Vias6/Header':struct.pack('<I',len(rows))}
    ids=streams['PrimitiveGuids/Data'];rr=[ids[i:i+24] for i in range(0,len(ids),24)]
    rr += [struct.pack('<II',3843,i)+uuid.uuid5(uuid.NAMESPACE_URL,f'qstl/mount-ring/via/{i}').bytes_le for i in range(len(vs),len(rows))]
    updates.update({'PrimitiveGuids/Data':b''.join(rr),'PrimitiveGuids/Header':struct.pack('<I',len(rr))})
    update_copy(pcb,S/'candidate.PcbDoc',updates)
    (R/'native_geometry.json').write_text(json.dumps(g,indent=2));(R/'intended_geometry.json').write_text(json.dumps(g,indent=2))
    print('Added 4 rings x 24 GND vias, radius 3.4 mm; total',len(g['vias']))

if __name__=='__main__':build()
