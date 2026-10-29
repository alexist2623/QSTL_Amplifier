"""Audit native L3 local power and GND, with all earlier mask/geometry constraints."""
from pathlib import Path
import argparse,hashlib,json,math
import olefile
from shapely.geometry import Polygon,Point,LineString
from shapely.ops import unary_union
from current_intent import l3_intent,before_rf_vias
from native_update import ROOT,blocks,parse
R=ROOT/'review';S=ROOT/'staging/l3_local_power_20261028'
p=argparse.ArgumentParser();p.add_argument('--pcb',type=Path,default=ROOT/'QSTL_THS3491_RGT_G20_RevD.PcbDoc');a=p.parse_args()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
intent=l3_intent();g=json.loads((R/'native_geometry.json').read_text());old=json.loads((S/'review_before/native_geometry.json').read_text())
fill=json.loads((R/'native_import_copper.json').read_text());before=json.loads((S/'review_before/native_import_copper.json').read_text())
native=json.loads((R/'native_import_check.json').read_text());mask=json.loads((R/'layer_mask_via_check.json').read_text())
assert native['source_sha256']==mask['pcb_sha256']==sha(a.pcb) and not native['errors']
assert sha(S/'before.PcbDoc')==intent['baseline_pcb_sha256']
assert sha(S/'before.SchDoc')==sha(ROOT/'QSTL_THS3491_RGT_G20_RevD.SchDoc')
for k in ['parts','pads','tracks','arcs','draw','board_width','board_height']:assert g[k]==old[k],k
removed=intent['removed_ground_vias'];assert len(removed)==7 and all(v['net']=='GND' for v in removed)
assert before_rf_vias(g['vias'])==[v for v in old['vias'] if v not in removed] and len(before_rf_vias(g['vias']))==623
assert [z for z in g['zones'] if z['layer']!='In2.Cu']==[z for z in old['zones'] if z['layer']!='In2.Cu']
def copper(fs,layer,net=None):return unary_union([Polygon(q['outline'],q['holes']).buffer(0) for q in fs if q['layer']==layer and (net is None or q['net']==net)])
for layer in ['F.Cu','In1.Cu','B.Cu']:
    nets={q['net'] for q in before if q['layer']==layer}
    assert nets=={q['net'] for q in fill if q['layer']==layer}
    for net in nets:assert copper(fill,layer,net).symmetric_difference(copper(before,layer,net)).area<.00001,(layer,net)
with olefile.OleFileIO(a.pcb) as o:polys=[parse(b) for b in blocks(o.openstream('Polygons6/Data').read())]
specs=[s['new_zone'] for s in intent['planes']]+[intent['added_ground_zone']]
for spec in specs:
    q=next(q for q in polys if ''.join(chr(int(c)) for c in q['NAME'].split(','))==spec['name'])
    points=[];i=0
    while 'VX'+str(i) in q:
        points.append([float(q['VX'+str(i)][:-3])*.0254,68.58-float(q['VY'+str(i)][:-3])*.0254]);i+=1
    actual_outline=Polygon(points);expected_outline=Polygon(spec['outline'])
    assert q['LAYER']=='MID2' and actual_outline.hausdorff_distance(expected_outline)<.000003
    assert actual_outline.symmetric_difference(expected_outline).area<expected_outline.length*.000003
areas={};clearances={}
for net in ['VCC','VEE']:
    c=copper(fill,'In2.Cu',net);assert c.geom_type=='Polygon',(net,c.geom_type)
    vs=[v for v in g['vias'] if v['net']==net]
    assert all(c.buffer(.00001).covers(Point(v['pos'])) for v in vs),net
    assert c.buffer(.00001).covers(Point(24.9,30.8 if net=='VCC' else 32.2))
    areas[net]=dict(before_mm2=copper(before,'In2.Cu',net).area,after_mm2=c.area,supply_vias_connected=len(vs))
    assert c.area<150 and c.area<areas[net]['before_mm2']*.12
ground=copper(fill,'In2.Cu','GND');assert ground.area>2400
for net in ['VCC','VEE']:
    clearances[net+'_GND']=copper(fill,'In2.Cu',net).distance(ground)
    assert clearances[net+'_GND']>=.199
clearances['VCC_VEE']=copper(fill,'In2.Cu','VCC').distance(copper(fill,'In2.Cu','VEE'));assert clearances['VCC_VEE']>=.199
bridge=LineString(intent['bridge_line_mm']).buffer(intent['minimum_bridge_width_mm']/2,cap_style=2)
assert copper(fill,'In2.Cu','VCC').buffer(.00001).covers(bridge)
assert all(bridge.distance(Point(v['pos']))>=v['diameter']/2+.205 for v in g['vias'] if v['net']=='GND')
assert mask['exposure_area_mm2']==json.loads((S/'review_before/layer_mask_via_check.json').read_text())['exposure_area_mm2']
report=dict(pcb_sha256=sha(a.pcb),baseline_pcb_sha256=sha(S/'before.PcbDoc'),
    filtered_power_corridors_continuous=True,all_supply_vias_connected=True,GND_fills_remaining_L3=True,
    C7_both_rails_connected=True,bottom_mask_unchanged=True,non_L3_copper_preserved=True,
    bridge_0p8mm_clear=True,exactly_seven_bridge_ground_vias_removed=True,remaining_vias=len(g['vias']),
    components_pads_tracks_arcs_preserved=True,schematic_unchanged=True,
    L3_GND_area_mm2=ground.area,power_areas_mm2=areas,clearance_mm=clearances,
    C7_branch_width_mm=.30,native_screenshot_verified=False)
(R/'l3_local_power_check.json').write_text(json.dumps(report,indent=2)+'\n')
print('L3 verified:',areas,'GND area',ground.area,'clearances',clearances)
