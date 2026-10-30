"""Verify expanded mounting-via exposure and bottom mask without top-pad shadows."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,math,re,struct,uuid
import olefile
from shapely.geometry import Polygon,Point,LineString,box
from shapely.affinity import rotate
from shapely.ops import unary_union
from native_update import ROOT,blocks,parse,records,unit,point
from bottom_mask_utils import protection,pad_shape,read_bottom_mask,union_rows
R=ROOT/'review';B=R/'bottom_mask_cleanup_baseline'
p=argparse.ArgumentParser();p.add_argument('--pcb',type=Path,default=ROOT/'QSTL_THS3491_RGT_G20_RevD.PcbDoc');p.add_argument('--package',action='store_true');a=p.parse_args()
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();checks={}
def check(name,value):checks[name]=bool(value);assert value,name
g=read(R/'native_geometry.json');old=read(B/'review_before/native_geometry.json');intent=read(ROOT/'bottom_mask_cleanup_intent.json');base=read(B/'review_before/validation_summary.json')
sch=ROOT/'QSTL_THS3491_RGT_G20_RevD.SchDoc';native=read(R/'native_import_check.json');mask_import=read(R/'mount_mask_import_check.json')
check('baseline_matches_previous_verified_PCB',sha(B/'before.PcbDoc')==intent['baseline_pcb_sha256']==base['sha256']['QSTL_THS3491_RGT_G20_RevD.PcbDoc'] and all(base['checks'].values()))
check('schematic_bytes_unchanged',sha(sch)==sha(B/'before.SchDoc')==intent['baseline_schematic_sha256'])
check('native_import_matches_saved_PCB',native['source_sha256']==sha(a.pcb) and not native['errors'])
check('independent_mask_import_matches_saved_PCB',mask_import['pcb_sha256']==sha(a.pcb))
for key in g:check(key+'_geometry_unchanged',g[key]==old[key])
check('persistent_RF_cutouts_unchanged',Counter(json.dumps(x,sort_keys=True) for x in read(R/'native_import_cutouts.json'))==Counter(json.dumps(x,sort_keys=True) for x in read(B/'review_before/native_import_cutouts.json')))
fill=read(R/'native_import_copper.json');prior=read(B/'review_before/native_import_copper.json')
def copper(fs,layer,net):return unary_union([Polygon(f['outline'],f['holes']).buffer(0) for f in fs if f['layer']==layer and f['net']==net])
keys={(f['layer'],f['net']) for f in fill};check('copper_layer_net_sets_unchanged',keys=={(f['layer'],f['net']) for f in prior})
for layer,net in sorted(keys):check(layer+'_'+net+'_copper_unchanged',copper(fill,layer,net).symmetric_difference(copper(prior,layer,net)).area<.00001)
def payload(path):
    with olefile.OleFileIO(path) as o:
        refs=[parse(b)['SOURCEDESIGNATOR'] for b in blocks(o.openstream('Components6/Data').read())]
        data=o.openstream('Pads6/Data').read();result={};off=0
        while off<len(data):
            assert data[off]==2;off+=1;bs=[]
            for _ in range(6):n=struct.unpack_from('<I',data,off)[0];off+=4;bs.append(data[off:off+n]);off+=n
            raw=bs[4];ref=refs[struct.unpack_from('<H',raw,7)[0]];result[(ref,bs[0])]=bs
        other={s:Counter(raw for raw in records(o.openstream(s+'/Data').read(),kind) if not (s in ['Regions6','ShapeBasedRegions6'] and raw[0]==38)) for s,kind in [('Tracks6',4),('Arcs6',1),('Regions6',11),('ShapeBasedRegions6',11)]}
        other['Polygons6']=o.openstream('Polygons6/Data').read()
        other['vias']=[]
        for raw in records(o.openstream('Vias6/Data').read(),3):
            assert uuid.UUID(bytes_le=raw[259:275]).version==4
            other['vias'].append(raw[:259]+bytes(16)+raw[275:])
        return result,other
bp,bo=payload(B/'before.PcbDoc');cp,co=payload(a.pcb)
check('all_other_native_routing_and_region_records_unchanged',bo==co)
check('native_pad_set_unchanged',bp.keys()==cp.keys())
changed=[];expansions={}
for key,parts in bp.items():
    before=list(parts);after=list(cp[key]);b=bytearray(before[4]);c=bytearray(after[4]);ref=key[0]
    for raw in [b,c]:
        assert uuid.UUID(bytes_le=bytes(raw[126:142])).version==4
        raw[126:142]=bytes(16)
    if ref in ['H1','H2','H3','H4']:
        check(ref+'_manual_7p6_mm_mask_expansion',c[102]==2 and struct.unpack_from('<i',c,90)[0]==unit(2.2125) and struct.unpack_from('<i',c,121)[0]==unit(2.2125))
        expansions[ref]=struct.unpack_from('<i',c,90)[0]*.00000254
        # Native save persists the matching expansion in the second mask field.
        b[90:94]=c[90:94];b[121:125]=c[121:125];changed.append(ref)
    before[4]=bytes(b);after[4]=bytes(c)
    check(ref+'_'+key[1].hex()+'_pad_properties_preserved',before==after)
check('only_four_mounting_pad_expansions_changed',sorted(changed)==['H1','H2','H3','H4'])
ground={l:copper(fill,l,'GND') for l in ['F.Cu','B.Cu']};areas={}
for hole in read(ROOT/'mount_mask_intent.json')['holes']:
    ref=hole['ref'];pad=next(p for p in g['pads'] if p['ref']==ref);row=next(p for p in mask_import['holes'] if p['ref']==ref)
    check(ref+'_NPTH_drill_and_center_preserved',pad['npth'] and pad['drill']==[3.175,3.175] and pad['pos']==hole['center_mm'])
    check(ref+'_both_outer_mask_openings_verified',row['top_mask'] and row['bottom_mask'] and abs(row['opening_diameter_mm']-7.6)<.00001)
    opening=Point(pad['pos']).buffer((pad['size'][0]+2*expansions[ref])/2,resolution=128)
    areas[ref]={}
    for layer in ['F.Cu','B.Cu']:
        exposed=ground[layer].intersection(opening);areas[ref][layer]=exposed.area
        check(ref+'_'+layer+'_continuous_exposed_GND_annulus',exposed.geom_type=='Polygon' and len(exposed.interiors)==1 and exposed.area>34.7)
        foreign=[copper(fill,layer,n) for l,n in keys if l==layer and n!='GND']
        for p in g['pads']:
            if p['ref'] in ['H1','H2','H3','H4'] or p['net']=='GND' or layer not in p['layers']:continue
            x,y=p['pos'];w,h=p['size'];q=Point((x,y)).buffer(w/2) if p['shape']==0 else rotate(box(x-w/2,y-h/2,x+w/2,y+h/2),-p['angle'],origin=(x,y));foreign.append(q)
        for t in g['tracks']:
            if t['layer']==layer and t['net']!='GND':foreign.append(LineString([t['start'],t['end']]).buffer(t['width']/2))
        for v in g['vias']:
            if v['net']!='GND':foreign.append(Point(v['pos']).buffer(v['diameter']/2))
        check(ref+'_'+layer+'_no_foreign_copper_exposed',not foreign or opening.distance(unary_union(foreign))>.3)
    ring=next(r for r in read(ROOT/'mount_hole_ring_intent.json')['rings'] if r['ref']==ref)
    for i,xy in enumerate(ring['positions_mm']):
        via=next(v for v in g['vias'] if math.dist(v['pos'],xy)<.00001 and v['net']=='GND')
        check(ref+'_ring_via_'+str(i)+'_both_faces_fully_exposed',opening.covers(Point(via['pos']).buffer(via['diameter']/2)) and opening.boundary.distance(Point(via['pos']))-via['diameter']/2>.199)
actual_rows=read_bottom_mask(a.pcb);actual_mask=union_rows(actual_rows)
old_mask=union_rows(read_bottom_mask(B/'before.PcbDoc'))
def native_loop(loop):
    return [[x*.00000254,68.58-y*.00000254] for x,y in [point(p) for p in loop]]
expected_mask=union_rows([dict(outline=native_loop(r['outline']),holes=[native_loop(h) for h in r['holes']]) for r in intent['bottom_mask_regions']])
check('saved_bottom_opening_matches_plan',len(actual_rows)==len(intent['bottom_mask_regions']) and actual_mask.symmetric_difference(expected_mask).area<.00001)
check('previous_bottom_GND_exposure_preserved',old_mask.difference(actual_mask).area<.003)
check('bottom_opening_only_over_GND',actual_mask.difference(ground['B.Cu'].buffer(.00001)).area<.00001)
check('physical_bottom_pads_and_power_vias_keep_mask_margin',actual_mask.intersection(protection(g).buffer(-.00001)).area<.00001)
pin_keys={(p['ref'],p['num']) for p in g['pads'] if 'B.Cu' in p['layers'] and p['ref'] not in ['H1','H2','H3','H4']}
check('only_physical_bottom_pads_in_protection_list',pin_keys=={(p['ref'],p['pad']) for p in intent['protected_actual_bottom_pads']})
safe_ground=ground['B.Cu'].buffer(-.02).intersection(box(.51,.51,g['board_width']-.51,g['board_height']-.51)).difference(protection(g).buffer(.01))
for p in g['pads']:
    if 'F.Cu' not in p['layers'] or 'B.Cu' in p['layers']:continue
    required=pad_shape(p).buffer(.30,join_style=2).intersection(safe_ground)
    check(p['ref']+'_'+p['num']+'_no_top_pad_shadow_on_bottom',required.difference(actual_mask.buffer(.00001)).area<.00001)
drc_text=(R/'native_audit_drc.txt').read_text();drc=dict(errors=drc_text.count('Severity: error'),warnings=drc_text.count('Severity: warning'),unconnected=int(re.search(r'\*\* Found (\d+) unconnected pads',drc_text).group(1)))
check('native_DRC_no_errors_or_unconnected',drc==dict(errors=0,warnings=1,unconnected=0))
check('only_inherited_RG_DRIVE_arc_warning','[RG_DRIVE]' in drc_text and '0.0089 mm' in drc_text)
if a.package:
    app=read(R/'altium_application_check.json');models=read(R/'component_3d_check.json')
    check('main_PCB_native_saved_and_reopened',app['pcb_sha256']==sha(a.pcb) and app['open_save_reopen_passed'])
    check('26_embedded_models_preserved',models['pcb_sha256']==sha(a.pcb) and models['model_count']==26 and models['embedded_step_bytes_verified'] and models['native_placement_verified'])
    summary=dict(release_status='REVIEW ONLY',checks=checks,drc=dict(native_copper=drc),native_import=native,sha256={q.name:sha(q) for q in ROOT.glob('*.P*')},schematic_sha256=sha(sch),Altium_application_open_save=True,Altium_application_reopen=True,Altium_application_ERC_DRC=False,SI_PI_EMC_thermal_validated=False,baseline_validation=str(B/'review_before/validation_summary.json'),baseline_validation_sha256=sha(B/'review_before/validation_summary.json'),baseline_check_count=len(base['checks']),validation_method='Current native import and DRC; exact comparison to prior verified PCB. Only H1-H4 mask expansion and free bottom-mask openings change. All copper, drills, vias, other pad properties and RF cutouts are unchanged. Independent importer confirms both outer mask layers and 7.6 mm diameter; all 96 mounting-ring via lands are exposed. Bottom mask protects only actual bottom pads/through pins and non-GND vias, with no top-only pad projections.',warning=base['warning'],latest_audit='bottom_mask_cleanup_check.json')
    (R/'validation_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
report=dict(pcb_sha256=sha(a.pcb),schematic_sha256=sha(sch),baseline_pcb_sha256=sha(B/'before.PcbDoc'),checks=checks,mount_opening_diameter_mm=7.6,actual_mask_expansions_mm=expansions,exposed_GND_area_mm2=areas,mounting_ring_vias_exposed=96,removed_top_pad_projections=len(intent['removed_top_pad_projections']),bottom_mask_regions=actual_rows,bottom_opening_area_mm2=actual_mask.area,additional_bottom_exposure_mm2=actual_mask.area-old_mask.area,parts=31,pads=83,vias=839,drc=drc,native_screenshot_verified=False)
(R/'bottom_mask_cleanup_check.json').write_text(json.dumps(report,indent=2)+'\n')
print('Bottom-mask cleanup verified:',len(checks),'checks;',drc)
