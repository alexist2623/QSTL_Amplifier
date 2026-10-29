"""Validate perimeter vias in the reopened native PCB and unchanged baseline."""
from pathlib import Path
import argparse,hashlib,json,math
from shapely.geometry import Point,Polygon
from shapely.ops import unary_union
from rf_fence_plan import rf_copper,padshape
from native_update import ROOT
R=ROOT/'review';S=ROOT/'staging/edge_via_fence_20261028'
p=argparse.ArgumentParser();p.add_argument('--pcb',type=Path,default=ROOT/'QSTL_THS3491_RGT_G20_RevD.PcbDoc');a=p.parse_args()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
g=json.loads((R/'native_geometry.json').read_text());old=json.loads((S/'review_before/native_geometry.json').read_text());intent=json.loads((ROOT/'edge_via_intent.json').read_text())
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
added=intent['added_ground_vias'];assert len(added)==148 and g['vias']==old['vias']+added and len(g['vias'])==965
assert all(v['net']=='GND' and v['diameter']==.4 and v['drill']==.2 for v in added)
edge_gaps=[min(v['pos'][0],v['pos'][1],g['board_width']-v['pos'][0],g['board_height']-v['pos'][1])-.2 for v in added]
assert max(abs(q-.8) for q in edge_gaps)<.000002
assert {q['side'] for q in intent['targets'] if q['result']=='added'}=={'top','bottom','left','right'}
for q in intent['targets']:
    if q['result']=='added':assert any(v['pos']==q['pos'] for v in added)
    elif q['result']=='existing':assert any(v['pos']==q['via_pos'] and v['net']=='GND' for v in old['vias'])
    else:assert q in intent['protected_targets'] and q['side'] in ['left','right']
assert len(intent['protected_targets'])==16 and all(v in old['vias'] for v in intent['reused_existing_vias'])
fill=json.loads((R/'native_import_copper.json').read_text())
for layer in ['F.Cu','In1.Cu','In2.Cu','B.Cu']:
    copper=unary_union([Polygon(f['outline'],f['holes']).buffer(0) for f in fill if f['layer']==layer and f['net']=='GND'])
    assert all(copper.buffer(.00001).covers(Point(v['pos']).buffer(.2,resolution=64)) for v in added),layer
rf=rf_copper(g);rfgap=min(rf.distance(Point(v['pos']))-.2 for v in added)
assert rfgap>=.9174
padgap=min(padshape(q).distance(Point(v['pos']))-.2 for v in added for q in g['pads'])
assert padgap>=.2
minhole=min(math.dist(v['pos'],q['pos'])-(v['drill']+q['drill'])/2 for v in added for q in g['vias'] if q!=v)
assert minhole>=.25
mask=json.loads((R/'layer_mask_via_check.json').read_text());assert mask['pcb_sha256']==sha(a.pcb)
assert mask['bottom_mask_regions']==json.loads((S/'review_before/layer_mask_via_check.json').read_text())['bottom_mask_regions']
report=dict(pcb_sha256=sha(a.pcb),baseline_pcb_sha256=sha(S/'before.PcbDoc'),
    perimeter_vias_on_all_four_edges=True,edge_inset_and_dimensions_verified=True,edge_vias_GND_all_four_layers=True,
    existing_vias_and_mount_rings_preserved=True,edge_RF_and_pad_clearances_verified=True,edge_via_drill_clearance_verified=True,edge_copper_mask_parts_schematic_preserved=True,
    added_vias=len(added),reused_existing_vias=len(intent['reused_existing_vias']),protected_target_count=len(intent['protected_targets']),total_vias=len(g['vias']),
    center_inset_mm=1.,nominal_pitch_mm=1.,minimum_via_copper_to_edge_mm=min(edge_gaps),via_diameter_mm=.4,via_drill_mm=.2,
    minimum_new_via_to_via_drill_gap_mm=minhole,minimum_new_via_to_RF_copper_mm=rfgap,minimum_new_via_to_pad_copper_mm=padgap,
    native_screenshot_verified=False)
(R/'edge_via_check.json').write_text(json.dumps(report,indent=2)+'\n')
print('Edge vias verified:',len(added),'new; copper to edge %.3f mm; min drill gap %.4f mm; total %d'%(min(edge_gaps),minhole,len(g['vias'])))
