"""Record validated final supply-plane/via-array changes against the saved backup."""
from pathlib import Path
import hashlib
import json
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

ROOT=Path(__file__).resolve().parents[1]; R=ROOT/'review'
B=ROOT/'staging/pre_entry_via_array_20261022'
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def write(path,data):path.write_text(json.dumps(data,indent=2),encoding='utf-8')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
pcb=ROOT/'QSTL_THS3491_RGT_G20_RevD.PcbDoc'
digest=sha(pcb); audit=read(R/'native_import_check.json'); summary=read(R/'validation_summary.json')
assert not audit['errors'] and audit['source_sha256']==digest
assert all(summary['checks'].values()) and summary['Altium_application_reopen']
g=read(R/'native_geometry.json'); prior=read(B/'review/native_geometry.json')
assert all(g[key]==prior[key] for key in ['parts','pads','tracks','arcs'])
assert [z for z in g['zones'] if z['keepout']]==[z for z in prior['zones'] if z['keepout']]
previous_vias=read(B/'review/vias.json'); vias=read(R/'vias.json')
removed=[q for q in previous_vias if q not in vias]
added=[q for q in vias if q not in previous_vias]
assert len(removed)==3 and all(v['net']=='GND' for v in removed)
assert len(added)==32 and all(v['group']=='filtered entry via array' for v in added)
fills=read(R/'native_import_copper.json')
l2=unary_union([Polygon(f['outline'],f['holes']) for f in fills if f['layer']=='In1.Cu' and f['net']=='GND'])
clearances=[l2.distance(Point(v['pos']))-v['diameter']/2 for v in added]
assert min(clearances)>.199
intent=read(ROOT/'input_rectangle_intent.json')
report=dict(pcb_sha256=digest,previous_sha256=sha(B/pcb.name),
    application_open_save_reopen=True,design_checks_passed=len(summary['checks']),
    expanded_island_width_mm=dict(before=2.8,after=6.0),height_mm=3.66139,
    via_arrays=intent['filtered_via_arrays'],added_via_count=32,removed_GND_via_count=3,
    added_vias=added,removed_vias=removed,total_vias=len(vias),
    new_via_min_L2_GND_clearance_mm=min(clearances),
    components_pads_tracks_arcs_unchanged=True,L2_RF_pad_cutouts_unchanged=True,
    independent_DRC=summary['drc'],Altium_native_DRC_performed=False,
    VSS_interpretation='Opposite VCC (+15 V) rail; no VSS net exists in this PCB.',
    figure='entry_plane_via_arrays.png',figure_is_Altium_screenshot=False)
write(R/'entry_plane_array_check.json',report)

# Keep earlier current-file evidence linked to the delivered revision.
shape=read(R/'pad_shape_repair.json');shape['pcb_sha256']=digest
shape['rectangular_pad_details']=audit['rectangular_pads_verified'];shape['independent_DRC']=summary['drc']
write(R/'pad_shape_repair.json',shape)
regression=read(R/'shape_regression_check.json');regression['after_sha256']=digest
write(R/'shape_regression_check.json',regression)
earlier=read(R/'input_rectangle_and_L2_check.json')
earlier.update(pcb_sha256=digest,placement=intent,total_vias=len(vias),checks_passed=len(summary['checks']),
              subsequent_entry_array_changes='entry_plane_array_check.json',independent_DRC=summary['drc'])
write(R/'input_rectangle_and_L2_check.json',earlier)
print('Recorded 32 added vias, 3 removed GND vias; minimum L2 GND gap:',round(min(clearances),6),'mm')
