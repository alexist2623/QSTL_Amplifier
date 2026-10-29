"""Audit complete native mounting-hole via rings and unchanged prior geometry."""
from pathlib import Path
import argparse,hashlib,json,math
from shapely.geometry import Point,Polygon
from shapely.ops import unary_union
from native_update import ROOT
from current_intent import before_edge_vias
R=ROOT/'review';S=ROOT/'staging/mount_hole_rings_20261028'
p=argparse.ArgumentParser();p.add_argument('--pcb',type=Path,default=ROOT/'QSTL_THS3491_RGT_G20_RevD.PcbDoc');a=p.parse_args()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
g=json.loads((R/'native_geometry.json').read_text());old=json.loads((S/'review_before/native_geometry.json').read_text());intent=json.loads((ROOT/'mount_hole_ring_intent.json').read_text())
native=json.loads((R/'native_import_check.json').read_text());assert native['source_sha256']==sha(a.pcb) and not native['errors']
assert sha(S/'before.PcbDoc')==intent['baseline_pcb_sha256']
assert sha(S/'before.SchDoc')==sha(ROOT/'QSTL_THS3491_RGT_G20_RevD.SchDoc')
for k in g:
    if k not in ['vias','zones']:assert g[k]==old[k],k
assert len(g['zones'])==len(old['zones'])
for z,previous in zip(g['zones'],old['zones']):
    assert {k:v for k,v in z.items() if k!='filled'}=={k:v for k,v in previous.items() if k!='filled'}
    def filled(q):return unary_union([Polygon(f['outline'],f['holes']).buffer(0) for f in q.get('filled',[])])
    assert filled(z).symmetric_difference(filled(previous)).area<.000001,z['name']
added=intent['added_ground_vias'];assert len(added)==96 and before_edge_vias(g['vias'])==old['vias']+added and len(before_edge_vias(g['vias']))==817
assert all(v['net']=='GND' and v['diameter']==.4 and v['drill']==.2 for v in added)
assert {r['ref'] for r in intent['rings']}=={'H1','H2','H3','H4'}
for ring in intent['rings']:
    h=next(p for p in g['pads'] if p['ref']==ring['ref'])
    assert h['npth'] and h['drill']==[3.175,3.175] and h['pos']==ring['center_mm']
    assert len(ring['positions_mm'])==24
    for i,pos in enumerate(ring['positions_mm']):
        assert any(v['pos']==pos for v in added)
        expected=[h['pos'][0]+3.4*math.cos(i*math.pi/12),h['pos'][1]+3.4*math.sin(i*math.pi/12)]
        assert math.dist(pos,expected)<.000002
fill=json.loads((R/'native_import_copper.json').read_text())
for layer in ['F.Cu','In1.Cu','In2.Cu','B.Cu']:
    copper=unary_union([Polygon(f['outline'],f['holes']).buffer(0) for f in fill if f['layer']==layer and f['net']=='GND'])
    assert all(copper.buffer(.00001).covers(Point(v['pos']).buffer(.2,resolution=64)) for v in added),layer
minhole=min(math.dist(v['pos'],q['pos'])-(v['drill']+q['drill'])/2 for v in added for q in g['vias'] if q!=v)
assert minhole>=.25
minmount=min(math.dist(v['pos'],q['pos'])-v['drill']/2-q['drill'][0]/2 for v in added for q in g['pads'] if q['npth'])
assert minmount>1.71
mask=json.loads((R/'layer_mask_via_check.json').read_text());assert mask['pcb_sha256']==sha(a.pcb)
assert mask['bottom_mask_regions']==json.loads((S/'review_before/layer_mask_via_check.json').read_text())['bottom_mask_regions']
report=dict(pcb_sha256=sha(a.pcb),baseline_pcb_sha256=sha(S/'before.PcbDoc'),
    four_complete_24_via_rings=True,mount_ring_radius_3p4mm=True,mount_ring_GND_all_four_layers=True,
    mount_holes_and_existing_vias_preserved=True,mount_ring_drill_clearance_verified=True,mount_ring_copper_and_mask_preserved=True,
    added_vias=96,total_vias=len(g['vias']),ring_radius_mm=3.4,via_diameter_mm=.4,via_drill_mm=.2,
    angle_pitch_degrees=15,adjacent_via_pitch_mm=intent['adjacent_via_center_pitch_mm'],
    minimum_via_to_via_drill_gap_mm=minhole,minimum_mount_to_via_drill_gap_mm=minmount,
    nominal_6mm_screw_head_to_via_copper_gap_mm=.2,native_screenshot_verified=False)
(R/'mount_hole_ring_check.json').write_text(json.dumps(report,indent=2)+'\n')
print('Verified 4 x 24 GND via rings; min via drill gap %.4f mm; total %d'%(minhole,len(g['vias'])))
