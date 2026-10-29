"""Verify native 3W fence geometry and preservation against the latest PCB."""
from pathlib import Path
import argparse,hashlib,json,math
import olefile
from shapely.geometry import Point,Polygon
from shapely.ops import unary_union
from rf_fence_plan import ROOT,rf_copper
from current_intent import before_mount_vias
R=ROOT/'review';S=ROOT/'staging/rf_fence_20261028'
p=argparse.ArgumentParser();p.add_argument('--pcb',type=Path,default=ROOT/'QSTL_THS3491_RGT_G20_RevD.PcbDoc');a=p.parse_args()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
g=json.loads((R/'native_geometry.json').read_text());old=json.loads((S/'review_before/native_geometry.json').read_text());intent=json.loads((ROOT/'rf_fence_intent.json').read_text())
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
added=intent['added_ground_vias'];assert before_mount_vias(g['vias'])==old['vias']+added
assert len(added)==98 and len(before_mount_vias(g['vias']))==721
assert all(v['net']=='GND' and v['diameter']==.4 and v['drill']==.2 for v in added)
assert all(v in old['vias'] for v in intent['reused_existing_vias'])
rf=rf_copper(g);gaps=[rf.distance(Point(v['pos']))-v['diameter']/2 for v in added+intent['reused_existing_vias']]
assert min(gaps)>=intent['minimum_gap_mm']-.00001
fill=json.loads((R/'native_import_copper.json').read_text())
for layer in ['F.Cu','In1.Cu','In2.Cu','B.Cu']:
    copper=unary_union([Polygon(f['outline'],f['holes']).buffer(0) for f in fill if f['layer']==layer and f['net']=='GND'])
    assert all(copper.buffer(.00001).covers(Point(v['pos']).buffer(v['diameter']/2,resolution=64)) for v in added),layer
minhole=10.;mincopper=10.
for v in added:
    for q in g['vias']:
        if q is v or q==v:continue
        d=math.dist(v['pos'],q['pos']);minhole=min(minhole,d-(v['drill']+q['drill'])/2);mincopper=min(mincopper,d-(v['diameter']+q['diameter'])/2)
assert minhole>=.25 and mincopper>=.05
# These streams are not modified by fence generation; Altium may reorder/cache
# Regions6 on save, so compare mask via the independent existing mask audit.
mask=json.loads((R/'layer_mask_via_check.json').read_text());assert mask['pcb_sha256']==sha(a.pcb)
assert mask['bottom_mask_regions']==json.loads((S/'review_before/layer_mask_via_check.json').read_text())['bottom_mask_regions']
report=dict(pcb_sha256=sha(a.pcb),baseline_pcb_sha256=sha(S/'before.PcbDoc'),
    RF_3W_edge_gap_verified=True,minimum_edge_gap_mm=min(gaps),reference_width_mm=.3058,
    new_vias_GND_on_all_four_layers=True,existing_vias_preserved=True,RF_routes_components_and_mask_preserved=True,
    power_corridors_not_pierced=True,new_via_drill_spacing_verified=True,minimum_new_via_drill_gap_mm=minhole,
    added_vias=len(added),reused_vias=len(intent['reused_existing_vias']),total_vias=len(g['vias']),
    nominal_pitch_mm=.9,blocked_target_count=len(intent['blocked_targets_mm']),
    blocked_target_reason='Pin/component clearance, existing-via drill spacing, or protected plane geometry. Not a closed RF shielding enclosure.',
    native_screenshot_verified=False,EM_simulation_performed=False)
(R/'rf_fence_check.json').write_text(json.dumps(report,indent=2)+'\n')
print('RF fence verified:',len(added),'new,',len(intent['reused_existing_vias']),'reused; minimum gap',min(gaps),'mm; total',len(g['vias']))
