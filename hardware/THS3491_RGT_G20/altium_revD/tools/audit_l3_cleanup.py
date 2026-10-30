"""Audit clean L3 planes against the preceding verified native PCB.

Only two L3 polygon outlines, listed GND vias, and three L2 trace windows change.
Prior feature audits remain hash-bound historical evidence.
"""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,math,re,struct
import olefile
from shapely.geometry import Point,Polygon,LineString,box
from shapely.affinity import rotate
from shapely.ops import unary_union
from native_update import ROOT,blocks,parse,records

R=ROOT/'review';B=R/'l3_cleanup_baseline'
p=argparse.ArgumentParser()
p.add_argument('--pcb',type=Path,default=ROOT/'QSTL_THS3491_RGT_G20_RevD.PcbDoc')
p.add_argument('--package',action='store_true');a=p.parse_args()
sha=lambda q:hashlib.sha256(q.read_bytes()).hexdigest()
read=lambda q:json.loads(q.read_text())
checks={}
def check(name,value):
    checks[name]=bool(value)
    assert value,name
intent=read(ROOT/'l3_cleanup_intent.json');old=read(B/'review_before/native_geometry.json')
correction=intent['L2_pad_only_correction']
removed_windows=correction['removed_trace_cutout_names']
old_zones=[z for z in old['zones'] if not (z['keepout'] and z['layer']=='In1.Cu' and z['name'] in removed_windows)]
restore_area=unary_union([Polygon(w['outline']) for w in correction['removed_outlines']])
g=read(R/'native_geometry.json');native=read(R/'native_import_check.json')
baseline=read(B/'review_before/validation_summary.json')
check('baseline_matches_previous_verified_PCB',sha(B/'before.PcbDoc')==intent['baseline_pcb_sha256']==baseline['sha256']['QSTL_THS3491_RGT_G20_RevD.PcbDoc'] and all(baseline['checks'].values()))
schematic=ROOT/'QSTL_THS3491_RGT_G20_RevD.SchDoc'
check('schematic_bytes_unchanged',sha(schematic)==sha(B/'before.SchDoc')==intent['baseline_schematic_sha256']==baseline['schematic_sha256'])
check('independent_native_import_matches_saved_PCB',native['source_sha256']==sha(a.pcb) and not native['errors'])
for key in g:
    if key not in ['zones','vias']:check(key+'_unchanged',g[key]==old[key])
removed=intent['removed_ground_vias'];remaining=[v for v in old['vias'] if v not in removed]
check('only_126_specified_GND_vias_removed',len(removed)==126 and all(v['net']=='GND' and v in old['vias'] for v in removed) and g['vias']==remaining)
check('component_pad_via_counts',len(g['parts'])==31 and len(g['pads'])==83 and len(g['vias'])==839)
check('all_supply_vias_preserved',[v for v in g['vias'] if v['net']!='GND']==[v for v in old['vias'] if v['net']!='GND'])
check('protected_GND_via_in_pad_preserved',all(any(math.dist(q['pos'],v['pos'])<.00001 and v['net']=='GND' for v in g['vias']) for q in intent['protected_ground_via_in_pad']))
ep=[[18.79601,27.94],[18.34601,27.49],[19.24601,27.49],[18.34601,28.39],[19.24601,28.39]]
check('five_U1_EP_thermal_vias_preserved',all(any(math.dist(q,v['pos'])<.00001 and v['net']=='GND' for v in g['vias']) for q in ep))
check('only_three_L2_trace_windows_removed',len(old['zones'])-len(g['zones'])==3 and len(g['zones'])==len(old_zones))
specs={s['name']:s for s in intent['planes']}
for z,previous in zip(g['zones'],old_zones):
    expected={k:v for k,v in previous.items() if k!='filled'}
    if z['name'] in specs:expected['outline']=specs[z['name']]['outline_mm']
    check(z['name']+'_authorized_outline', {k:v for k,v in z.items() if k!='filled'}==expected)
cutouts=read(R/'native_import_cutouts.json')
cutout_set=lambda items:Counter((c['layer'],tuple((round(x,5),round(y,5)) for x,y in c['outline'])) for c in items)
prior_cutouts=read(B/'review_before/native_import_cutouts.json')
removed_cutouts=cutout_set([dict(layer='In1.Cu',outline=w['outline']) for w in correction['removed_outlines']])
check('21_native_cutouts_only_L2_trace_windows_removed',cutout_set(cutouts)==cutout_set(prior_cutouts)-removed_cutouts and len(cutouts)==21)
pad_windows=[z for z in g['zones'] if z['keepout'] and z['layer']=='In1.Cu']
check('L2_only_18_pad_windows_remain',len(pad_windows)==18 and all(z['name'].startswith('L2_RF_PAD_') for z in pad_windows))
for z in pad_windows:
    ref,num=z['name'].removeprefix('L2_RF_PAD_').split('_')
    pad=next(q for q in g['pads'] if q['ref']==ref and q['num']==num)
    x,y=pad['pos'];w,h=pad['size'];margin=correction['pad_window_margin_mm']
    expected=rotate(box(x-w/2-margin,y-h/2-margin,x+w/2+margin,y+h/2+margin),-pad['angle'],origin=(x,y))
    check(z['name']+'_only_pad_plus_existing_margin',Polygon(z['outline']).symmetric_difference(expected).area<.00001)
check('no_L3_or_L4_RF_cutouts',all(c['layer'] in ['F.Cu','In1.Cu'] for c in cutouts))

fill=read(R/'native_import_copper.json');prior=read(B/'review_before/native_import_copper.json')
def copper(fs,layer,net):
    return unary_union([Polygon(f['outline'],f['holes']).buffer(0) for f in fs if f['layer']==layer and f['net']==net])
keys={(f['layer'],f['net']) for f in prior}
check('copper_layer_net_sets_preserved',keys=={(f['layer'],f['net']) for f in fill})
deltas={}
for layer,net in sorted(keys):
    before,after=copper(prior,layer,net),copper(fill,layer,net)
    change=before.symmetric_difference(after)
    if layer=='In1.Cu':
        # Refill also restores the old window's 0.1 mm minimum-feature edge
        # slivers. No existing GND may disappear, or remote copper change.
        check('L2_GND_restored_only_at_removed_trace_windows',before.difference(after).area<.00001 and change.difference(restore_area.buffer(.1)).area<.00001 and after.area>before.area)
    elif layer!='In2.Cu':check(layer+'_'+net+'_filled_copper_unchanged',change.area<.00001)
    deltas[layer+'/'+net]=after.area-before.area
windows=unary_union([Polygon(c['outline']) for c in cutouts if c['layer']=='In1.Cu'])
planes={s['net']:copper(fill,'In2.Cu',s['net']) for s in intent['planes']}
outlines={s['net']:Polygon(s['outline_mm']) for s in intent['planes']}
power=unary_union(list(planes.values()));outline=unary_union(list(outlines.values()))
rf_gap=power.distance(windows)
check('power_avoids_L2_RF_window_projection',rf_gap>=intent['minimum_L2_RF_window_projection_clearance_mm']-.00001)
check('power_outlines_remain_separated',outlines['VCC'].distance(outlines['VEE'])>=.5-.00001)
branches={};ground_gaps={}
for spec in intent['planes']:
    net=spec['net'];poly=planes[net];ol=outlines[net]
    check(net+'_one_solid_plane_without_via_holes',poly.geom_type=='Polygon' and len(poly.interiors)==0)
    check(net+'_filled_plane_follows_intended_outline',poly.difference(ol.buffer(.00001)).area<.00001 and ol.buffer(-.02).difference(poly).area<.00001)
    vias=[v for v in g['vias'] if v['net']==net]
    check(net+'_every_supply_via_connected',all(poly.buffer(.00001).covers(Point(v['pos']).buffer(v['diameter']/2)) for v in vias))
    b=spec['branch'];strip=LineString(b['centerline']).buffer(b['minimum_width_mm']/2,cap_style=2,join_style=2)
    check(net+'_C7_connection_is_broad_plane',strip.difference(poly.buffer(.00001)).area<.00001)
    gap=min(poly.distance(Point(v['pos']))-v['diameter']/2 for v in g['vias'] if v['net']=='GND')
    check(net+'_GND_via_copper_does_not_overlap',gap>=.225-.00001)
    ground_gaps[net]=gap
    branches[net]=dict(minimum_connection_width_mm=b['minimum_width_mm'],supply_vias=len(vias),plane_area_mm2=poly.area,holes=len(poly.interiors))
check('removed_vias_all_conflicted_with_new_outlines',all(outline.distance(Point(v['pos']))<v['diameter']/2+.225 for v in removed))
ground=copper(fill,'In2.Cu','GND')
check('L3_GND_and_supply_copper_clearance',ground.distance(power)>=.199)
top_output=unary_union([LineString([t['start'],t['end']]).buffer(t['width']/2) for t in g['tracks'] if t['net']=='output' and t['layer']=='F.Cu'])
crossing=top_output.intersection(power)
check('output_crossing_has_continuous_L2_GND',not crossing.is_empty and copper(fill,'In1.Cu','GND').buffer(.00001).covers(crossing) and crossing.distance(windows)>.2)
check('L4_GND_copper_unchanged',copper(prior,'B.Cu','GND').symmetric_difference(copper(fill,'B.Cu','GND')).area<.00001)
rf_nets={'FB','INV','inpt','AMP_OUT','RG_DRIVE','inm','inpt_raw','output'}
trace_copper=[]
for t in g['tracks']+g['arcs']:
    if t['net'] not in rf_nets or t['layer']!='F.Cu':continue
    if 'radius' in t:
        cx,cy=t['center'];theta=math.atan2(t['start'][1]-cy,t['start'][0]-cx)
        points=[(cx+t['radius']*math.cos(theta+math.radians(t['angle'])*i/400),cy+t['radius']*math.sin(theta+math.radians(t['angle'])*i/400)) for i in range(401)]
    else:points=[t['start'],t['end']]
    trace_copper.append(LineString(points).buffer(t['width']/2))
required_GND=unary_union(trace_copper).difference(windows.buffer(.00001))
check('every_RF_trace_has_L2_GND_outside_pad_windows',required_GND.difference(copper(fill,'In1.Cu','GND').buffer(.00001)).area<.00001)

def mask(path):
    result=[]
    with olefile.OleFileIO(path) as o:
        for raw in records(o.openstream('Regions6/Data').read(),11):
            if raw[0]!=38:continue
            n=struct.unpack_from('<I',raw,18)[0];q=parse(raw[22:22+n]);off=22+n
            assert q['NAME'].startswith('BOTTOM_GND_EXPOSURE_')
            loops=[]
            for _ in range(1+struct.unpack_from('<H',raw,14)[0]):
                size=struct.unpack_from('<I',raw,off)[0];off+=4;points=[]
                for _ in range(size):
                    x,y=struct.unpack_from('<2d',raw,off);off+=16;points.append([x*.00000254,68.58-y*.00000254])
                loops.append(points)
            result.append(Polygon(loops[0],loops[1:]))
    return unary_union(result)
before_mask,after_mask=mask(B/'before.PcbDoc'),mask(a.pcb)
check('bottom_GND_exposure_unchanged',before_mask.symmetric_difference(after_mask).area<.00001)
check('bottom_exposure_still_only_over_GND',after_mask.difference(copper(fill,'B.Cu','GND').buffer(.00001)).area<.00001)
def pad_masks(path):
    with olefile.OleFileIO(path) as o:
        cs=[parse(b)['SOURCEDESIGNATOR'] for b in blocks(o.openstream('Components6/Data').read())];data=o.openstream('Pads6/Data').read()
    off=0;result={}
    while off<len(data):
        assert data[off]==2;off+=1;bs=[]
        for _ in range(6):n=struct.unpack_from('<I',data,off)[0];off+=4;bs.append(data[off:off+n]);off+=n
        raw=bs[4];ref=cs[struct.unpack_from('<H',raw,7)[0]];result[(ref,bs[0])]=(raw[86:94],raw[101:103])
    return result
check('pad_mask_paste_properties_unchanged',pad_masks(a.pcb)==pad_masks(B/'before.PcbDoc'))
drc={}
for name,file in [('geometry','geometry_drc.txt'),('native_copper','native_audit_drc.txt')]:
    text=(R/file).read_text();drc[name]=dict(errors=text.count('Severity: error'),warnings=text.count('Severity: warning'),unconnected=int(re.search(r'\*\* Found (\d+) unconnected pads',text).group(1)))
    check(name+'_DRC_no_errors_or_unconnected',drc[name]==dict(errors=0,warnings=1,unconnected=0))
    check(name+'_only_inherited_RG_DRIVE_arc_warning','[track_dangling]' in text and '[RG_DRIVE]' in text and '0.0089 mm' in text)
if a.package:
    app=read(R/'altium_application_check.json');models=read(R/'component_3d_check.json')
    check('native_main_PCB_saved_and_reopened',app['pcb_sha256']==sha(a.pcb) and app['open_save_reopen_passed'])
    check('all_26_embedded_models_preserved',models['pcb_sha256']==sha(a.pcb) and models['model_count']==26 and models['embedded_step_bytes_verified'] and models['native_placement_verified'])
    summary=dict(release_status='REVIEW ONLY',checks=checks,drc=drc,native_import=native,sha256={q.name:sha(q) for q in ROOT.glob('*.P*')},schematic_sha256=sha(schematic),Altium_application_open_save=True,Altium_application_reopen=True,Altium_application_ERC_DRC=False,SI_PI_EMC_thermal_validated=False,baseline_validation=str(B/'review_before/validation_summary.json'),baseline_validation_sha256=sha(B/'review_before/validation_summary.json'),baseline_check_count=len(baseline['checks']),validation_method='Full current native import and DRC; exact object comparison allowing only two L3 outlines, 126 specified GND vias, and removal of three L2 trace-spanning windows. All RF trace projections outside the 18 pad windows have continuous L2 GND. Historical audits are not claimed rerun.',warning=baseline['warning'],latest_audit='l3_cleanup_check.json')
    (R/'validation_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
report=dict(pcb_sha256=sha(a.pcb),schematic_sha256=sha(schematic),baseline_pcb_sha256=sha(B/'before.PcbDoc'),checks=checks,parts=31,pads=83,vias=839,removed_GND_vias=len(removed),branches=branches,L2_pad_windows=18,L2_trace_windows_removed=3,L2_RF_window_projection_clearance_mm=rf_gap,GND_via_copper_to_plane_mm=ground_gaps,copper_area_changes_mm2=deltas,bottom_exposure_mm2=after_mask.area,drc=drc,native_screenshot_verified=False)
(R/'l3_cleanup_check.json').write_text(json.dumps(report,indent=2)+'\n')
print('L3 cleanup verified:',len(checks),'checks;',drc,'; 839 vias, 126 removed; RF gap',rf_gap)
