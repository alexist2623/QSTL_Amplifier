"""Verify L2 resistor-body openings and restoration beneath U1 against a verified baseline."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,math,re,struct,uuid
import olefile
from shapely.geometry import Point,Polygon,LineString,box
from shapely.affinity import rotate
from shapely.ops import unary_union
from native_update import ROOT,records,parse
R=ROOT/'review';B=R/'rf_resistor_windows_baseline'
p=argparse.ArgumentParser();p.add_argument('--pcb',type=Path,default=ROOT/'QSTL_THS3491_RGT_G20_RevD.PcbDoc');p.add_argument('--package',action='store_true');a=p.parse_args()
sha=lambda q:hashlib.sha256(q.read_bytes()).hexdigest()
read=lambda q:json.loads(q.read_text())
checks={}
def check(name,value):
    checks[name]=bool(value);assert value,name
intent=read(ROOT/'rf_resistor_windows_intent.json');old=read(B/'review_before/native_geometry.json');g=read(R/'native_geometry.json')
baseline=read(B/'review_before/validation_summary.json');native=read(R/'native_import_check.json')
check('baseline_is_verified_previous_file',sha(B/'before.PcbDoc')==intent['baseline_pcb_sha256']==baseline['sha256']['QSTL_THS3491_RGT_G20_RevD.PcbDoc'] and all(baseline['checks'].values()))
sch=ROOT/'QSTL_THS3491_RGT_G20_RevD.SchDoc'
check('schematic_bytes_unchanged',sha(sch)==sha(B/'before.SchDoc')==intent['baseline_schematic_sha256'])
check('complete_native_import_matches_saved_file',native['source_sha256']==sha(a.pcb) and not native['errors'])
for key in g:
    if key!='zones':check(key+'_unchanged',g[key]==old[key])
check('counts_31_parts_83_pads_839_vias',len(g['parts'])==31 and len(g['pads'])==83 and len(g['vias'])==839)
def stable(z):return {k:v for k,v in z.items() if k!='filled'}
def target(z):return z['layer']=='In1.Cu' and z['keepout']
check('only_L2_window_definitions_changed',[stable(z) for z in g['zones'] if not target(z)]==[stable(z) for z in old['zones'] if not target(z)])
new=[z for z in g['zones'] if target(z)];previous=[z for z in old['zones'] if target(z)]
check('eight_RF_resistor_windows_replace_18_pad_windows',len(new)==8 and len(previous)==18 and {z['name'] for z in new}=={'L2_RF_RESISTOR_'+s['ref'] for s in intent['new_resistor_windows']})
check('five_U1_cutout_objects_removed',len([z for z in previous if z['name'].startswith('L2_RF_PAD_U1_')])==5 and not any('U1' in z['name'] for z in new))
cutouts=read(R/'native_import_cutouts.json')
check('eleven_native_cutouts_only_L1_and_L2',len(cutouts)==11 and sum(c['layer']=='F.Cu' for c in cutouts)==3 and sum(c['layer']=='In1.Cu' for c in cutouts)==8)
cutout_set=lambda items:Counter((c['layer'],tuple((round(x,5),round(y,5)) for x,y in c['outline'])) for c in items)
check('native_windows_match_requested_coordinates',cutout_set(cutouts)==cutout_set([z for z in g['zones'] if z['keepout']]))
fill=read(R/'native_import_copper.json');prior=read(B/'review_before/native_import_copper.json')
def copper(fs,layer,net):return unary_union([Polygon(f['outline'],f['holes']).buffer(0) for f in fs if f['layer']==layer and f['net']==net])
keys={(f['layer'],f['net']) for f in prior};check('copper_layer_net_sets_unchanged',keys=={(f['layer'],f['net']) for f in fill})
deltas={}
allowed=unary_union([Polygon(z['outline']) for z in previous+new]).buffer(.1)
for layer,net in sorted(keys):
    before,after=copper(prior,layer,net),copper(fill,layer,net);change=before.symmetric_difference(after)
    check(layer+'_'+net+'_authorized_copper_change',change.difference(allowed).area<.00001 if layer=='In1.Cu' else change.area<.00001)
    deltas[layer+'/'+net]=after.area-before.area
ground=copper(fill,'In1.Cu','GND');ground_tol=ground.buffer(.00001)
windows=unary_union([Polygon(z['outline']) for z in new])
check('L2_GND_remains_one_connected_plane',ground.geom_type=='Polygon')
def pad_shape(p):
    x,y=p['pos'];w,h=p['size'];return rotate(box(x-w/2,y-h/2,x+w/2,y+h/2),-p['angle'],origin=(x,y))
check('no_window_intersects_any_U1_pad',all(windows.disjoint(pad_shape(p)) for p in g['pads'] if p['ref']=='U1'))
for num in ['1','3','4','10','11']:
    q=pad_shape(next(p for p in g['pads'] if p['ref']=='U1' and p['num']==num))
    check('U1_'+num+'_now_has_GND_below',ground_tol.covers(q))
for spec in intent['new_resistor_windows']:
    ref=spec['ref'];poly=Polygon(spec['outline']);z=next(z for z in new if z['name']=='L2_RF_RESISTOR_'+ref)
    check(ref+'_window_outline_exact',z['outline']==spec['outline'])
    pads=[p for p in g['pads'] if p['ref']==ref];shapes=[pad_shape(p) for p in pads]
    body_gap=unary_union(shapes).convex_hull.difference(unary_union(shapes))
    check(ref+'_entire_pad_to_pad_gap_is_open',body_gap.intersection(ground).area<.00001 and poly.buffer(.00001).covers(body_gap))
    check(ref+'_signal_pads_have_openings',all(pad_shape(p).intersection(ground).area<.00001 for p in pads if p['net']!='GND'))
    if spec['grounded_pads']:
        gp=next(p for p in pads if p['net']=='GND');via=next(v for v in g['vias'] if math.dist(v['pos'],gp['pos'])<.00001)
        check(ref+'_GND_pad_via_connected',ground_tol.covers(Point(via['pos']).buffer(via['diameter']/2)))
check('all_GND_via_lands_remain_on_L2_GND',all(ground_tol.covers(Point(v['pos']).buffer(v['diameter']/2)) for v in g['vias'] if v['net']=='GND'))
rf={'FB','INV','inpt','AMP_OUT','RG_DRIVE','inm','inpt_raw','output'};traces=[]
for t in g['tracks']+g['arcs']:
    if t['net'] not in rf or t['layer']!='F.Cu':continue
    if 'radius' in t:
        cx,cy=t['center'];th=math.atan2(t['start'][1]-cy,t['start'][0]-cx)
        pts=[(cx+t['radius']*math.cos(th+math.radians(t['angle'])*i/400),cy+t['radius']*math.sin(th+math.radians(t['angle'])*i/400)) for i in range(401)]
    else:pts=[t['start'],t['end']]
    traces.append(LineString(pts).buffer(t['width']/2))
check('inter_component_RF_traces_keep_L2_GND',unary_union(traces).difference(windows.buffer(.00001)).difference(ground_tol).area<.00001)
power=unary_union([copper(fill,'In2.Cu',n) for n in ['VCC','VEE']]);power_gap=power.distance(windows)
check('L3_power_still_avoids_RF_windows',power_gap>=.2)
def unchanged_native_streams(path):
    with olefile.OleFileIO(path) as o:
        result={key:o.openstream(key).read() for key in ['Tracks6/Data','Arcs6/Data','Polygons6/Data']}
        # Native saves in a new application session regenerate these UUIDv4
        # payloads. Verify their type and compare every other byte, including
        # mask settings and layer/stack definitions, without normalization.
        def without_uuid(raw,index):
            assert uuid.UUID(bytes_le=raw[index:index+16]).version==4
            return raw[:index]+bytes(16)+raw[index+16:]
        result['vias']=tuple(without_uuid(raw,259) for raw in records(o.openstream('Vias6/Data').read(),3))
        data=o.openstream('Pads6/Data').read();off=0;pads=[]
        while off<len(data):
            assert data[off]==2;off+=1;parts=[]
            for k in range(6):
                n=struct.unpack_from('<I',data,off)[0];off+=4;raw=data[off:off+n];off+=n
                parts.append(without_uuid(raw,126) if k==4 else raw)
            pads.append(tuple(parts))
        result['pads']=tuple(pads)
        free=[]
        for raw in records(o.openstream('Regions6/Data').read(),11):
            n=struct.unpack_from('<I',raw,18)[0];q=parse(raw[22:22+n])
            if struct.unpack_from('<H',raw,5)[0]!=65535 or (raw[0]==2 and q.get('KIND')=='1'):continue
            free.append(raw)
        result['free_regions_except_L2_windows']=Counter(free)
        return result
check('native_pad_routing_via_polygon_and_other_free_regions_preserved',unchanged_native_streams(a.pcb)==unchanged_native_streams(B/'before.PcbDoc'))
drc={}
for name,file in [('geometry','geometry_drc.txt'),('native_copper','native_audit_drc.txt')]:
    text=(R/file).read_text();drc[name]=dict(errors=text.count('Severity: error'),warnings=text.count('Severity: warning'),unconnected=int(re.search(r'\*\* Found (\d+) unconnected pads',text).group(1)))
    check(name+'_DRC_no_errors_or_unconnected',drc[name]==dict(errors=0,warnings=1,unconnected=0))
    check(name+'_only_inherited_arc_warning','[track_dangling]' in text and '[RG_DRIVE]' in text and '0.0089 mm' in text)
if a.package:
    app=read(R/'altium_application_check.json');models=read(R/'component_3d_check.json')
    check('main_PCB_native_saved_and_reopened',app['pcb_sha256']==sha(a.pcb) and app['open_save_reopen_passed'])
    check('26_embedded_models_preserved',models['pcb_sha256']==sha(a.pcb) and models['model_count']==26 and models['embedded_step_bytes_verified'] and models['native_placement_verified'])
    summary=dict(release_status='REVIEW ONLY',checks=checks,drc=drc,native_import=native,sha256={q.name:sha(q) for q in ROOT.glob('*.P*')},schematic_sha256=sha(sch),Altium_application_open_save=True,Altium_application_reopen=True,Altium_application_ERC_DRC=False,SI_PI_EMC_thermal_validated=False,baseline_validation=str(B/'review_before/validation_summary.json'),baseline_validation_sha256=sha(B/'review_before/validation_summary.json'),baseline_check_count=len(baseline['checks']),validation_method='Current native import and DRC plus comparison against the verified 102-check baseline. Only L2 resistor/U1 window definitions and local L2 copper change. Other geometry and L1/L3/L4 copper are unchanged.',warning=baseline['warning'],latest_audit='rf_resistor_windows_check.json')
    (R/'validation_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
report=dict(pcb_sha256=sha(a.pcb),schematic_sha256=sha(sch),baseline_pcb_sha256=sha(B/'before.PcbDoc'),checks=checks,parts=31,pads=83,vias=839,L2_resistor_windows=8,U1_windows=0,grounded_resistor_pads_preserved=['R2.1','R5.1','R7.1'],L3_power_to_L2_window_gap_mm=power_gap,copper_area_changes_mm2=deltas,drc=drc,native_screenshot_verified=False)
(R/'rf_resistor_windows_check.json').write_text(json.dumps(report,indent=2)+'\n')
print('RF resistor windows verified:',len(checks),'checks;',drc)
