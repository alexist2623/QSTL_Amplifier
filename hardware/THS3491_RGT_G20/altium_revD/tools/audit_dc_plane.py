"""Check both expanded DC supply pours and PJ-102AH pad isolation."""
from pathlib import Path
import argparse,json,hashlib,math,struct
import olefile
from shapely.geometry import Polygon,Point,box
from shapely.ops import unary_union
from native_update import ROOT,blocks,parse
from current_intent import l3_intent,l3_zones,before_rf_vias
R=ROOT/'review';S=ROOT/'staging/dc_plane_20261028'
p=argparse.ArgumentParser();p.add_argument('--pcb',type=Path,default=ROOT/'QSTL_THS3491_RGT_G20_RevD.PcbDoc');a=p.parse_args()
g=json.loads((R/'native_geometry.json').read_text());old=json.loads((S/'review_before/native_geometry.json').read_text());intent=json.loads((ROOT/'dc_plane_intent.json').read_text())
specs=intent.get('planes',[dict(intent,ref='J9')]);by_zone={s['zone']:s for s in specs}
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
native=json.loads((R/'native_import_check.json').read_text())
assert not native['errors'] and native['source_sha256']==sha(a.pcb)
layer_fix=json.loads((ROOT/'layer_mask_via_intent.json').read_text()) if (ROOT/'layer_mask_via_intent.json').exists() else {}
for key in ['board_width','board_height','parts','pads','tracks','arcs','draw']:assert g[key]==old[key],key
assert before_rf_vias(g['vias'])==[v for v in old['vias'] if v not in layer_fix.get('removed_ground_vias',[])+l3_intent().get('removed_ground_vias',[])]
oz={(z['name'],z['layer']):z for z in l3_zones(old['zones'])}
for z in g['zones']:
    expected={k:v for k,v in oz[z['name'],z['layer']].items() if k!='filled'}
    if z['name'] in by_zone:expected['outline']=by_zone[z['name']]['outline_mm']
    assert {k:v for k,v in z.items() if k!='filled'}==expected
with olefile.OleFileIO(a.pcb) as o:
    polygons=[parse(b) for b in blocks(o.openstream('Polygons6/Data').read())]
for spec in specs:
    q=next(q for q in polygons if ''.join(chr(int(c)) for c in q['NAME'].split(','))==spec['zone'])
    outline=[];i=0
    while 'VX'+str(i) in q:
        outline.append([float(q['VX'+str(i)][:-3])*.0254,68.58-float(q['VY'+str(i)][:-3])*.0254]);i+=1
    assert Polygon(outline).symmetric_difference(Polygon(spec['outline_mm'])).area<.0001
fill=json.loads((R/'native_import_copper.json').read_text())
def copper(layer,net):return unary_union([Polygon(f['outline'],f['holes']).buffer(0) for f in fill if f['layer']==layer and f['net']==net])
rails={}
for spec in specs:
    net=spec['net'];ref=spec['ref'];vin=copper('F.Cu',net);pads={q['num']:q for q in g['pads'] if q['ref']==ref}
    assert pads['1']['net']==net and pads['2']['net']=='GND' and pads['3']['net']==''
    clearances={}
    for num in ['2','3']:
        q=pads[num];disk=Point(q['pos']).buffer(q['size'][0]/2,resolution=128)
        clearances[num]=vin.distance(disk)
        assert clearances[num]>=.199,(net,num,clearances[num])
        assert vin.intersection(disk).area<1e-8
    p1=pads['1'];x,y=p1['pos'];s=p1['size'][0]/2
    assert vin.intersection(box(x-s,y-s,x+s,y+s)).area>.01
    assert vin.geom_type=='Polygon',(net,vin.geom_type)
    for layer in ['In1.Cu','B.Cu']:
        assert copper(layer,'GND').intersects(Point(pads['2']['pos']).buffer(1.3)),(net,layer)
    rails[net]=dict(ref=ref,ground_and_switch_pads_isolated=True,clearance_mm=clearances,
        continuous=True,pin2_GND_connected_L2_and_bottom=True,pin3_PCB_net='NC',
        polygon_area_before_mm2=Polygon(spec['old_outline_mm']).area,polygon_area_after_mm2=Polygon(spec['outline_mm']).area)
assert sha(ROOT/'QSTL_THS3491_RGT_G20_RevD.SchDoc')==sha(S/'before.SchDoc')
report=dict(pcb_sha256=sha(a.pcb),baseline_pcb_sha256=sha(S/'before.PcbDoc'),
    native_polygon_outline_verified=True,pins_components_tracks_models_not_moved=True,
    remaining_vias_not_moved=True,subsequent_ground_vias_removed=len(layer_fix.get('removed_ground_vias',[])),
    rails=rails,
    pin3_internal_switch='Normally closed to pin 2 without plug; opens on insertion',
    schematic_unchanged=True)
(R/'dc_plane_check.json').write_text(json.dumps(report,indent=2)+'\n')
print('Both input pours verified; pad-to-pour clearances (mm):',{n:d['clearance_mm'] for n,d in rails.items()})
