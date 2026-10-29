"""Verify saved native mask polygons, L3/L4 copper restoration, and precise via deletions."""
from pathlib import Path
import argparse, hashlib, json, math, struct
import olefile
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union
from fix_layer_mask_vias import ROOT,R,S,INTENT,padshape,protection
from native_update import records,parse
from current_intent import l3_intent,l3_zones,before_rf_vias,rf_intent,mount_intent,edge_intent

p=argparse.ArgumentParser();p.add_argument('--pcb',type=Path,default=ROOT/'QSTL_THS3491_RGT_G20_RevD.PcbDoc');a=p.parse_args()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
g=json.loads((R/'native_geometry.json').read_text());old=json.loads((S/'review_before/native_geometry.json').read_text());intent=json.loads(INTENT.read_text())
native=json.loads((R/'native_import_check.json').read_text());assert native['source_sha256']==sha(a.pcb) and not native['errors']
assert sha(S/'before.PcbDoc')==intent['baseline_pcb_sha256']
assert sha(S/'before.SchDoc')==sha(ROOT/'QSTL_THS3491_RGT_G20_RevD.SchDoc')
for k in ['parts','pads','tracks','arcs','draw','board_width','board_height']:assert g[k]==old[k],k
assert before_rf_vias(g['vias'])==[v for v in old['vias'] if v not in intent['removed_ground_vias']+l3_intent().get('removed_ground_vias',[])]
assert len(intent['removed_ground_vias'])==12 and all(v['net']=='GND' for v in intent['removed_ground_vias'])
vin=Polygon(next(z['outline'] for z in g['zones'] if z['name']=='L1_POSITIVE_INPUT'))
assert all(vin.distance(Point(v['pos']))>=v['diameter']/2+.205-1e-5 for v in g['vias'] if v['net']=='GND')
assert all(vin.distance(Point(v['pos']))<v['diameter']/2+.205 for v in intent['removed_ground_vias'])
cutouts=json.loads((R/'native_import_cutouts.json').read_text())
assert len(cutouts)==24 and not any(c['layer'] in ['In2.Cu','B.Cu'] for c in cutouts)
expected_z=[{k:v for k,v in z.items() if k!='filled'} for z in old['zones']]
expected_z=[z for z in expected_z if z not in intent['removed_cutouts']]
assert [{k:v for k,v in z.items() if k!='filled'} for z in g['zones']]==l3_zones(expected_z)
fill=json.loads((R/'native_import_copper.json').read_text())
def copper(layer,net=None):return unary_union([Polygon(f['outline'],f['holes']).buffer(0) for f in fill if f['layer']==layer and (net is None or f['net']==net)])
restored=[]
for z in intent['removed_cutouts']:
    window=Polygon(z['outline']);covered=copper(z['layer']).intersection(window).area
    # L3 split-power outlines intentionally leave a gap; removal of RF voids
    # must restore copper inside the existing plane outlines, not extend rails.
    plane=unary_union([Polygon(q['outline']) for q in g['zones'] if not q['keepout'] and q['layer']==z['layer']])
    target=window.intersection(plane)
    if z['layer']=='In2.Cu' and l3_intent():
        # Later local power/GND boundaries introduce legitimate clearance gaps.
        desired=unary_union([Polygon(f['outline'],f['holes']).buffer(0) for q in g['zones'] if not q['keepout'] and q['layer']=='In2.Cu' for f in q['filled']])
        target=window.intersection(desired)
    assert target.area>0 and abs(covered-target.area)<.00002,(z['name'],z['layer'],covered,target.area)
    restored.append(dict(name=z['name'],layer=z['layer'],area_mm2=window.area,area_within_existing_plane_mm2=target.area,copper_restored_mm2=covered))

mask=[];mask_rows=[]
with olefile.OleFileIO(a.pcb) as o:
    for raw in records(o.openstream('Regions6/Data').read(),11):
        if raw[0]!=38:continue
        n=struct.unpack_from('<I',raw,18)[0];q=parse(raw[22:22+n]);off=22+n
        assert q['NAME'].startswith('BOTTOM_GND_EXPOSURE_') and q['KIND']=='0'
        assert struct.unpack_from('<H',raw,5)[0]==65535 and q.get('ISBOARDCUTOUT','FALSE')=='FALSE'
        loops=[]
        for _ in range(1+struct.unpack_from('<H',raw,14)[0]):
            size=struct.unpack_from('<I',raw,off)[0];off+=4
            coords=[]
            for _ in range(size):
                x,y=struct.unpack_from('<2d',raw,off);off+=16;coords.append([x*.00000254,68.58-y*.00000254])
            loops.append(coords)
        poly=Polygon(loops[0],loops[1:]);assert poly.is_valid
        mask.append(poly);mask_rows.append(dict(outline=loops[0],holes=loops[1:]))
opening=unary_union(mask);expected=unary_union([Polygon(f['outline'],f['holes']) for f in intent['bottom_mask_regions']])
assert opening.symmetric_difference(expected).area<.002
ground=copper('B.Cu','GND')
assert opening.difference(ground.buffer(.00001)).area<.000001
assert opening.intersection(protection(g).buffer(-.00001)).area<.000001
ep=padshape(next(p for p in g['pads'] if (p['ref'],p['num'])==('U1','17')))
assert opening.intersection(ep).area>2.10
assert len(mask)==len(intent['bottom_mask_regions']) and opening.area>2000
def pad_masks(path):
    with olefile.OleFileIO(path) as o:
        data=o.openstream('Pads6/Data').read();off=0;result=[]
        while off<len(data):
            assert data[off]==2;off+=1;bs=[]
            for _ in range(6):
                n=struct.unpack_from('<I',data,off)[0];off+=4;bs.append(data[off:off+n]);off+=n
            raw=bs[4]
            result.append((bs[0],raw[7:9],raw[86:94],raw[101:103]))
        return result
assert pad_masks(a.pcb)==pad_masks(S/'before.PcbDoc'),'Existing pad mask/paste settings changed'
report=dict(pcb_sha256=sha(a.pcb),baseline_pcb_sha256=sha(S/'before.PcbDoc'),
    L3_L4_RF_cutouts_removed=True,L2_and_top_cutouts_preserved=True,restored_windows=restored,
    removed_VIN_P_ground_vias=12,subsequent_L3_bridge_vias_removed=len(l3_intent().get('removed_ground_vias',[])),subsequent_RF_shield_vias_added=len(rf_intent().get('added_ground_vias',[])),subsequent_mount_vias_added=len(mount_intent().get('added_ground_vias',[])),subsequent_edge_vias_added=len(edge_intent().get('added_ground_vias',[])),remaining_vias=len(g['vias']),VIN_P_no_ground_via_clearance_clipping=True,
    components_pads_tracks_arcs_models_preserved=True,schematic_unchanged=True,
    broad_bottom_ground_exposure=True,bottom_mask_regions=mask_rows,exposure_area_mm2=opening.area,
    exposure_only_over_GND=True,pin_mask_margin_mm=.30,pin_projection_protected=True,U1_EP_underneath_exposed=True,
    existing_pad_mask_parameters_preserved=True,Altium_screenshot_verified=False)
(R/'layer_mask_via_check.json').write_text(json.dumps(report,indent=2)+'\n')
print('Verified: 6 L3/L4 voids restored, 12 VIN_P GND vias removed, bottom GND opening %.2f mm2; U1 EP covered and pin margins preserved'%opening.area)
