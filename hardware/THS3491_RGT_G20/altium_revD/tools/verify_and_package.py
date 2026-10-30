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

if (ROOT/'rf_resistor_windows_intent.json').exists():
    import subprocess,sys
    subprocess.run([sys.executable,str(ROOT/'tools/audit_rf_resistor_windows.py'),'--package'],check=True)
    raise SystemExit(0)

if (ROOT/'l3_cleanup_intent.json').exists():
    import subprocess,sys
    subprocess.run([sys.executable,str(ROOT/'tools/audit_l3_cleanup.py'),'--package'],check=True)
    raise SystemExit(0)

# TP1 removal has a stricter comparison against the complete verified 965-via
# board. Historical feature reports describe their original file hashes;
# do not relabel those reports as fresh checks of this later revision.
if (ROOT/'remove_tp1_intent.json').exists():
    import subprocess,sys
    subprocess.run([sys.executable,str(ROOT/'tools/audit_remove_tp1.py'),'--package'],check=True)
    raise SystemExit(0)
g=json.loads((R/'native_geometry.json').read_text())
old=json.loads((C/'review/native_geometry.json').read_text())
removed=set(json.loads((ROOT/'output_load_intent.json').read_text())['removed_components'])
dc=json.loads((ROOT/'dc_inputs_intent.json').read_text())
removed.update(dc['removed_components'])
new_refs={q['ref'] for q in dc['connectors']}
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
pdtracks=[t for t in powertracks if t['net']=='VCC']
check('PD16_power_tracks_preserved',len(pdtracks)==2 and all(t['width']==.15 for t in pdtracks))
check('DC_input_routes_match_intent',[t for t in powertracks if t['net'] in ['VIN_P','VIN_N']]==dc['added_tracks'])
check('RF_arcs_unchanged',g['arcs']==old['arcs'])
check('signal_net_assignments_unchanged',sorted((p['ref'],p['num'],p['net']) for p in g['pads'] if p['ref'] not in new_refs)==
      sorted((p['ref'],p['num'],p['net']) for p in old['pads'] if p['ref'] not in removed))
allowed_moves=set(json.loads((R/'change_manifest.json').read_text())['moves'])
check('RF_component_placement_unchanged',all(parts[p['ref']]==p for p in old['parts'] if p['ref'] not in allowed_moves|removed))
check('R15_output_load_removed',not (set(parts)&removed) and all(p['ref'] not in removed for p in g['pads']))
check('C3_C4_180_degree_symmetry',math.dist(parts['C4']['pos'],[37.59202-parts['C3']['pos'][0],55.88-parts['C3']['pos'][1]])<.00001)
intent=json.loads((ROOT.parent/'planning/power_plan_intent.json').read_text())
for ref in ['C5','C6']:
    check(ref+'_TI_position_and_rotation',parts[ref]['pos']+[parts[ref]['angle']]==intent[ref+'_TI_original'])

entry=json.loads((ROOT/'input_rectangle_intent.json').read_text())
plane=json.loads((ROOT/'dc_plane_intent.json').read_text()) if (ROOT/'dc_plane_intent.json').exists() else None
plane_specs={q['zone']:q for q in plane.get('planes',[plane])} if plane else {}
for name,bounds in entry['zone_rectangles_mm'].items():
    polygon=Polygon(zones[name]['outline'])
    if name in plane_specs:
        check(name+'_user_L_shape',polygon.symmetric_difference(Polygon(plane_specs[name]['outline_mm'])).area<1e-9 and polygon.area>box(*bounds).area)
        check(name+'_original_filter_region_preserved',polygon.covers(box(*bounds)))
    else:check(name+'_rectangular',len(zones[name]['outline'])==4 and polygon.symmetric_difference(box(*bounds)).area<1e-9)
for ref,(name,edge) in entry['center_on_edge'].items():
    bounds=entry['zone_rectangles_mm'][name]; x,y=parts[ref]['pos']
    check(ref+'_center_on_filter_copper_edge',abs(y-bounds[1 if edge=='top' else 3])<.00001 and bounds[0]<x<bounds[2] and Polygon(zones[name]['outline']).boundary.distance(Point(x,y))<.00001)
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
check('all_pad_shapes_verified',native['all_pad_shapes_checked']==len(g['pads']))
check('all_19_sharp_rectangles_verified',len(native['rectangular_pads_verified'])==19
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
output_change=json.loads((R/'output_load_removal.json').read_text())
dc_check=json.loads((R/'dc_inputs_check.json').read_text())
check('R15_removal_preserved_through_DC_input_change',output_change['schematic_sha256']==dc_check['baseline_schematic_sha256'] and output_change['remaining_pin_properties_unchanged'] and output_change['only_two_R15_branch_wires_removed'] and dc_check['existing_schematic_preserved'])
check('DC_input_schematic_matches_delivered_file',dc_check['schematic_sha256']==sha(ROOT/'QSTL_THS3491_RGT_G20_RevD.SchDoc'))
check('review_silkscreen_notes_removed',dc_check['pcb_sha256']==sha(pcb) and dc_check['review_silkscreen_notes_removed'])
if plane:
    plane_check=json.loads((R/'dc_plane_check.json').read_text())
    for spec in plane_specs.values():
        check(spec['net']+'_plane_pin_clearances_verified',plane_check['pcb_sha256']==sha(pcb) and plane_check['rails'][spec['net']]['ground_and_switch_pads_isolated'])
models=json.loads((R/'component_3d_check.json').read_text())
if (ROOT/'layer_mask_via_intent.json').exists():
    layer_fix=json.loads((R/'layer_mask_via_check.json').read_text())
    check('layer_mask_via_audit_matches_delivered_file',layer_fix['pcb_sha256']==sha(pcb))
    for name in ['L3_L4_RF_cutouts_removed','L2_and_top_cutouts_preserved','VIN_P_no_ground_via_clearance_clipping',
                 'exposure_only_over_GND','pin_projection_protected','U1_EP_underneath_exposed','existing_pad_mask_parameters_preserved']:
        check(name,layer_fix[name])
    check('exactly_12_VIN_P_ground_vias_removed',layer_fix['removed_VIN_P_ground_vias']==12 and layer_fix['remaining_vias']==630-layer_fix.get('subsequent_L3_bridge_vias_removed',0)+layer_fix.get('subsequent_RF_shield_vias_added',0)+layer_fix.get('subsequent_mount_vias_added',0)+layer_fix.get('subsequent_edge_vias_added',0))
if (ROOT/'l3_local_power_intent.json').exists():
    l3_check=json.loads((R/'l3_local_power_check.json').read_text())
    check('L3_audit_matches_delivered_file',l3_check['pcb_sha256']==sha(pcb))
    for name in ['filtered_power_corridors_continuous','all_supply_vias_connected','GND_fills_remaining_L3','C7_both_rails_connected','bottom_mask_unchanged','non_L3_copper_preserved','bridge_0p8mm_clear','exactly_seven_bridge_ground_vias_removed']:
        check(name,l3_check[name])
if (ROOT/'rf_fence_intent.json').exists():
    rf_check=json.loads((R/'rf_fence_check.json').read_text())
    check('RF_fence_audit_matches_delivered_file',rf_check['pcb_sha256']==sha(pcb))
    for name in ['RF_3W_edge_gap_verified','new_vias_GND_on_all_four_layers','existing_vias_preserved','RF_routes_components_and_mask_preserved','power_corridors_not_pierced','new_via_drill_spacing_verified']:
        check(name,rf_check[name])
if (ROOT/'mount_hole_ring_intent.json').exists():
    mount_check=json.loads((R/'mount_hole_ring_check.json').read_text())
    check('mount_ring_audit_matches_delivered_file',mount_check['pcb_sha256']==sha(pcb))
    for name in ['four_complete_24_via_rings','mount_ring_radius_3p4mm','mount_ring_GND_all_four_layers','mount_holes_and_existing_vias_preserved','mount_ring_drill_clearance_verified','mount_ring_copper_and_mask_preserved']:
        check(name,mount_check[name])
if (ROOT/'edge_via_intent.json').exists():
    edge_check=json.loads((R/'edge_via_check.json').read_text())
    check('edge_via_audit_matches_delivered_file',edge_check['pcb_sha256']==sha(pcb))
    for name in ['perimeter_vias_on_all_four_edges','edge_inset_and_dimensions_verified','edge_vias_GND_all_four_layers','existing_vias_and_mount_rings_preserved','edge_RF_and_pad_clearances_verified','edge_via_drill_clearance_verified','edge_copper_mask_parts_schematic_preserved']:
        check(name,edge_check[name])
check('all_models_embedded_and_native_reopened',models['pcb_sha256']==sha(pcb) and models['model_count']==len(json.loads((ROOT/'models3d/placements.json').read_text())['placements']) and models['native_save_reopen_verified'] and models['embedded_step_bytes_verified'])
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
    with (C/'assembly'/name).open(newline='',encoding='utf-8-sig') as f:
        reader=csv.DictReader(f); fields=reader.fieldnames; rows=[q for q in reader if q['Designator'] not in removed]
    for q in rows:q['Note']=q['Note'].replace('stock not rechecked in Rev C','stock not rechecked in Rev C or Rev D')
    if name!='BOM_SMT_REVIEW.csv':
        for q in dc['connectors']:
            rows.append(dict(Designator=q['ref'],Value=q['value'],Footprint=q['pattern'],MPN=q['mpn'],LCSC='',Assembly='MANUAL THT',Note='Same Sky; 24VDC 5A; 5.5/2.1mm plug; center '+q['value'].split()[0]+' / sleeve GND; switched pin NC; procure exact MPN; JLC stocked supply not verified'))
    with (A/name).open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)
with (C/'assembly/CPL_SMT_REVIEW.csv').open(newline='',encoding='utf-8-sig') as f:
    reader=csv.DictReader(f); fieldnames=reader.fieldnames; rows=[row for row in reader if row['Designator'] not in removed]
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
