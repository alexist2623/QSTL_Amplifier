"""Check filled copper and design intent, update placement/process tables.

Requires Python 3, shapely and olefile. Run after audit_native.py.
"""
from pathlib import Path
import csv
import hashlib
import json
import math
import re
import struct
import olefile
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union
from shapely.affinity import rotate, translate
from check_layer_encoding import check as check_layer_encoding

ROOT=Path(__file__).resolve().parents[1]
R=ROOT/'review'; C=ROOT.parent/'altium_revC'
g=json.loads((R/'native_geometry.json').read_text())
old=json.loads((C/'review/native_geometry.json').read_text())
imported=json.loads((R/'native_import_copper.json').read_text())
checks={}
def check(name,condition):
    checks[name]=bool(condition)
    assert condition,name
def shape(f): return Polygon(f['outline'],f['holes']).buffer(0)
expected={}; actual={}
for z in g['zones']:
    if not z['keepout']:
        expected.setdefault((z['layer'],z['net']),[]).extend(shape(f) for f in z['filled'])
for f in imported: actual.setdefault((f['layer'],f['net']),[]).append(shape(f))
check('imported_layer_net_sets_equal',set(expected)==set(actual))
copper_delta={}
for key in expected:
    a=unary_union(expected[key]); b=unary_union(actual[key])
    copper_delta['/'.join(key)]=a.symmetric_difference(b).area
    check('copper_area_'+str(key),copper_delta['/'.join(key)]<.01)
pads={(p['ref'],p['num']):p for p in g['pads']}
parts={p['ref']:p for p in g['parts']}
def padshape(p):
    x,y=p['pos']; w,h=p['size']
    return translate(rotate(box(-w/2,-h/2,w/2,h/2),-p['angle'],origin=(0,0)),x,y)
zones={z['name']:z for z in g['zones'] if z['layer']=='F.Cu'}
for cap,net,pinnums in [('C5','VCC',['13','14']),('C6','VEE',['7','8'])]:
    copper=unary_union([shape(f) for f in zones['L1_'+net+'_LOCAL_PIN_ISLAND']['filled']])
    check(cap+'_power_pad_connected_to_island',copper.intersects(padshape(pads[cap,'1'])))
    check(cap+'_ground_pad_outside_supply',not copper.intersects(padshape(pads[cap,'2'])))
    for pin in pinnums:
        check(cap+'_supply_pin_'+pin,copper.intersects(padshape(pads['U1',pin])))
vcc=Polygon(zones['L1_VCC_LOCAL_PIN_ISLAND']['outline'])
check('PD16_outside_VCC_island',not vcc.intersects(padshape(pads['U1','16'])))
check('NC15_outside_VCC_island',not vcc.intersects(padshape(pads['U1','15'])))
ground_shapes=[shape(f) for z in g['zones'] if z['layer']=='F.Cu' and z['net']=='GND' for f in z['filled']]
check('NC15_surrounding_L1_ground_continuity',any(
    f.covers(Point(18.54601,26.35)) and f.covers(Point(18.54601,25.70)) for f in ground_shapes))
powertracks=[t for t in g['tracks'] if t['net'] in ['VCC','VEE','VIN_P','VIN_N']]
check('only_PD16_uses_power_tracks',len(powertracks)==2 and all(t['net']=='VCC' and t['width']==.15 for t in powertracks))
check('RF_arcs_unchanged',g['arcs']==old['arcs'])
check('signal_net_assignments_unchanged',sorted((p['ref'],p['num'],p['net']) for p in g['pads'])==
      sorted((p['ref'],p['num'],p['net']) for p in old['pads']))
allowed_moves=set(json.loads((R/'change_manifest.json').read_text())['moves'])
check('RF_component_placement_unchanged',all(parts[p['ref']]==p for p in old['parts'] if p['ref'] not in allowed_moves))
check('C3_C4_180_degree_symmetry',math.dist(parts['C4']['pos'],[37.59202-parts['C3']['pos'][0],55.88-parts['C3']['pos'][1]])<.00001)
intent=json.loads((ROOT.parent/'planning/power_plan_intent.json').read_text())
for ref in ['C5','C6']:
    check(ref+'_TI_position_and_rotation',parts[ref]['pos']+[parts[ref]['angle']]==intent[ref+'_TI_original'])

entry=json.loads((ROOT/'input_rectangle_intent.json').read_text())
for name,bounds in entry['zone_rectangles_mm'].items():
    polygon=Polygon(zones[name]['outline'])
    check(name+'_rectangular',len(zones[name]['outline'])==4 and polygon.symmetric_difference(box(*bounds)).area<1e-9)
for ref,(name,edge) in entry['center_on_edge'].items():
    bounds=entry['zone_rectangles_mm'][name]; x,y=parts[ref]['pos']
    check(ref+'_center_on_rectangle_edge',abs(y-bounds[1 if edge=='top' else 3])<.00001 and bounds[0]<x<bounds[2])
for plus,minus in [('C1','C2'),('C3','C4'),('L1','L2')]:
    check(plus+'_'+minus+'_input_symmetry',math.dist(parts[minus]['pos'],[37.59202-parts[plus]['pos'][0],55.88-parts[plus]['pos'][1]])<.00001)
for ref,name in [('C1','L1_POSITIVE_INPUT'),('C2','L1_NEGATIVE_INPUT'),('C3','L1_VCC_ENTRY_VIA_ISLAND'),('C4','L1_VEE_ENTRY_VIA_ISLAND')]:
    area=Polygon(zones[name]['outline'])
    check(ref+'_power_inside_GND_outside',area.covers(padshape(pads[ref,'1'])) and not area.intersects(padshape(pads[ref,'2'])))

arrays=entry.get('filtered_via_arrays',[])
if arrays:
    check('both_filtered_supply_arrays_present',{q['net'] for q in arrays}=={'VCC','VEE'})
    for spec in arrays:
        net=spec['net']; positions=spec['positions_mm']; island=Polygon(zones[spec['zone']]['outline'])
        l1_copper=unary_union(actual['F.Cu',net]); l3_copper=unary_union(actual['In2.Cu',net])
        check(net+'_4x4_via_array',len(positions)==16 and len({x for x,y in positions})==4 and len({y for x,y in positions})==4)
        check(net+'_array_0p8mm_pitch',all(abs(b-a-.8)<.00001 for axis in range(2) for a,b in zip(sorted({q[axis] for q in positions}),sorted({q[axis] for q in positions})[1:])))
        check(net+'_array_via_size_0p4_0p2',all(any(v['net']==net and math.dist(v['pos'],pos)<.00002 and v['diameter']==.4 and v['drill']==.2 for v in g['vias']) for pos in positions))
        check(net+'_array_inside_widened_island',all(island.covers(Point(pos).buffer(.2)) for pos in positions))
        check(net+'_array_connected_L1_L3',all(l1_copper.buffer(.00002).covers(Point(pos)) and l3_copper.buffer(.00002).covers(Point(pos)) for pos in positions))
        check(net+'_filtered_island_width_6mm',abs(island.bounds[2]-island.bounds[0]-6)<.00001)
    by_net={q['net']:q for q in arrays}
    check('entry_via_arrays_180_degree_symmetry',all(any(math.dist([37.59202-x,55.88-y],pos)<.00001 for pos in by_net['VCC']['positions_mm']) for x,y in by_net['VEE']['positions_mm']))

rf_windows=json.loads((R/'rf_pad_windows.json').read_text())
l2=unary_union(actual['In1.Cu','GND'])
cutouts=json.loads((R/'native_import_cutouts.json').read_text())
expected_cutouts=[z for z in g['zones'] if z['keepout']]
check('native_cutout_count',len(cutouts)==len(expected_cutouts))
check('native_persistent_cutout_geometry',all(any(c['layer']==z['layer'] and Polygon(c['outline']).symmetric_difference(Polygon(z['outline'])).area<.00002 for c in cutouts) for z in expected_cutouts))
for win in rf_windows:
    footprint=Polygon(win['pad_outline_mm'])
    check('L2_no_GND_under_'+win['ref']+'_'+win['pad'],l2.intersection(footprint).area<.000001)
    check('L2_no_GND_via_under_'+win['ref']+'_'+win['pad'],all(footprint.distance(Point(v['pos']))>v['diameter']/2 for v in g['vias'] if v['net']=='GND'))
check('L2_GND_single_continuous_area',l2.geom_type=='Polygon')
check('U1_EP_L2_GND_retained',l2.intersection(padshape(pads['U1','17'])).area>2.0)

def parse_report(path):
    text=path.read_text()
    return dict(errors=len(re.findall(r'Severity: error',text)),
                warnings=len(re.findall(r'Severity: warning',text)),
                unconnected=int(re.search(r'Found (\d+) unconnected pads',text)[1]))
drc={key:parse_report(R/name) for key,name in [('geometry','geometry_drc.txt'),('native_copper','native_audit_drc.txt')]}
for key,d in drc.items(): check(key+'_no_errors_or_unconnected',d['errors']==0 and d['unconnected']==0)
native=json.loads((R/'native_import_check.json').read_text())
check('native_geometry_comparison_passed',not native['errors'])
check('all_84_pad_shapes_verified',native['all_pad_shapes_checked']==84)
check('all_21_sharp_rectangles_verified',len(native['rectangular_pads_verified'])==21
      and all(q['shape']=='rectangle' and q['radius_mm']==0 for q in native['rectangular_pads_verified']))
check('C7_redundant_power_polygons_removed',not any(z['name'] in ['L1_C7_VCC','L1_C7_VEE'] for z in g['zones']))
for pin,net in [('1','VCC'),('2','VEE')]:
    check('C7_'+net+'_via_in_pad_preserved',any(v['net']==net and math.dist(v['pos'],pads['C7',pin]['pos'])<.00002 for v in g['vias']))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
pcb=ROOT/'QSTL_THS3491_RGT_G20_RevD.PcbDoc'
encoding=check_layer_encoding(pcb)
check('legacy_and_extended_layer_encoding_consistent',not encoding['errors'])
check('native_import_matches_delivered_file',native['source_sha256']==sha(pcb))
altium=json.loads((R/'altium_application_check.json').read_text())
native_open_save=bool(altium['open_save_reopen_passed'] and altium['pcb_sha256']==sha(pcb))
check('Altium_open_save_reopen_matches_delivered_file',native_open_save)
old_validation=json.loads((C/'review/validation_summary.json').read_text())
for name,digest in old_validation['sha256'].items(): check('RevC_unchanged_'+name,sha(C/name)==digest)
check('schematic_electrically_unchanged',sha(ROOT/'QSTL_THS3491_RGT_G20_RevD.SchDoc')==sha(C/'QSTL_THS3491_RGT_G20_RevC.SchDoc'))
with olefile.OleFileIO(ROOT/'QSTL_THS3491_RGT_G20_RevD.PcbDoc') as ole:
    data=ole.openstream('Board6/Data').read()[4:].rstrip(b'\0').decode('cp1252')
    board=dict(s.split('=',1) for s in data.split('|') if '=' in s)
    check('rigid_stack_versions_consistent',board['LAYERMASTERSTACK_V8ISFLEX']==board['V9_MASTERSTACK_ISFLEX']=='FALSE'
          and board['LAYERMASTERSTACK_V8NAME']==board['V9_MASTERSTACK_NAME']=='JLC04161H-7628')
    check('no_flex_carrier_material',not any('Polyimide' in v or 'Two copper flex' in v for v in board.values()))
    check('legacy_negative_plane_slots_inactive',all(board[f'LAYER{i}NEXT']==board[f'LAYER{i}PREV']=='0' for i in range(39,55)))
    check('legacy_copper_chain',[(board[f'LAYER{i}PREV'],board[f'LAYER{i}NEXT']) for i in [1,2,3,32]]==[('0','2'),('1','3'),('2','32'),('3','0')])

A=ROOT/'assembly'; A.mkdir(exist_ok=True)
for name in ['BOM_REVIEW.csv','BOM_SMT_REVIEW.csv','BOM_MANUAL_REVIEW.csv']:
    content=(C/'assembly'/name).read_text(encoding='utf-8-sig')
    (A/name).write_text(content.replace('stock not rechecked in Rev C',
                                     'stock not rechecked in Rev C or Rev D'),encoding='utf-8')
with (C/'assembly/CPL_SMT_REVIEW.csv').open(newline='',encoding='utf-8-sig') as f:
    reader=csv.DictReader(f); fieldnames=reader.fieldnames; rows=list(reader)
for row in rows:
    q=parts[row['Designator']]
    row['Mid X']=f'{q["pos"][0]:.6f}mm'; row['Mid Y']=f'{68.58-q["pos"][1]:.6f}mm'
    row['Rotation']=f'{q["angle"]%360:.3f}'
with (A/'CPL_SMT_REVIEW.csv').open('w',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=fieldnames); writer.writeheader(); writer.writerows(rows)
vialist=json.loads((R/'vias.json').read_text())
with (A/'VIA_IN_PAD_PROCESS_REVIEW.csv').open('w',newline='') as f:
    writer=csv.writer(f); writer.writerow(['Connection','Net','X_mm','Y_mm_from_top','Diameter_mm','Drill_mm','Process'])
    for v in vialist:
        if 'via-in-pad' in v['group']:
            writer.writerow([v['group'],v['net'],*v['pos'],v['diameter'],v['drill'],'resin filled, planarized, copper capped'])
summary=dict(release_status='REVIEW ONLY',checks=checks,copper_area_delta_mm2=copper_delta,
             drc=drc,native_import=native,sha256={p.name:sha(p) for p in ROOT.glob('*.P*')},
             schematic_sha256=sha(ROOT/'QSTL_THS3491_RGT_G20_RevD.SchDoc'),
             Altium_application_open_save=native_open_save,Altium_application_reopen=native_open_save,
             Altium_application_ERC_DRC=False,layer_encoding=encoding,
             SI_PI_EMC_thermal_validated=False,
             warning='Inherited 0.0089 mm RG_DRIVE auxiliary arc endpoint; retained from TI reference',
             importer_limitation='Complete Altium-saved PCB imported, including Texts6; importer-specific pad connection rules reapplied for DRC',
             altium_native_evidence='altium_application_check.json and altium_native_check.txt')
(R/'validation_summary.json').write_text(json.dumps(summary,indent=2))
print('Passed',len(checks),'design/copper/preservation checks;',drc)
