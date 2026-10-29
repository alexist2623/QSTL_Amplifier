"""Validate TP1 removal against the fully verified immediately preceding PCB.

Earlier feature reports remain historical hash-bound evidence. This audit
compares every other object to that exact baseline, audits the local copper and
mask repair, and checks the complete current native import and DRC.
"""
from pathlib import Path
from collections import Counter
import argparse,csv,hashlib,json,math,re,struct
import olefile
from shapely.geometry import Point,Polygon
from shapely.ops import unary_union
from native_update import ROOT,blocks,parse,records
R=ROOT/'review';S=ROOT/'review/tp1_removal_baseline'
p=argparse.ArgumentParser();p.add_argument('--pcb',type=Path,default=ROOT/'QSTL_THS3491_RGT_G20_RevD.PcbDoc');p.add_argument('--schematic',type=Path,default=ROOT/'QSTL_THS3491_RGT_G20_RevD.SchDoc');p.add_argument('--package',action='store_true');a=p.parse_args()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
checks={}
def check(name,value):checks[name]=bool(value);assert value,name
intent=json.loads((ROOT/'remove_tp1_intent.json').read_text());old=json.loads((S/'review_before/native_geometry.json').read_text());g=json.loads((R/'native_geometry.json').read_text())
baseline=json.loads((S/'review_before/validation_summary.json').read_text())
check('baseline_matches_previous_verified_file',sha(S/'before.PcbDoc')==intent['baseline_pcb_sha256']==baseline['sha256']['QSTL_THS3491_RGT_G20_RevD.PcbDoc'] and all(baseline['checks'].values()))
check('baseline_schematic_preserved_for_comparison',sha(S/'before.SchDoc')==intent['baseline_schematic_sha256'])
native=json.loads((R/'native_import_check.json').read_text())
check('complete_native_import_matches_saved_file',native['source_sha256']==sha(a.pcb) and not native['errors'])
for key in g:
    if key=='zones':continue
    expected=[q for q in old[key] if q['ref']!='TP1'] if key in ['parts','pads'] else old[key]
    check(key+'_only_authorized_change',g[key]==expected)
check('component_pad_via_counts',len(g['parts'])==31 and len(g['pads'])==83 and len(g['vias'])==965)
center=Point(intent['position_mm']);local=center.buffer(1.1)
fill=json.loads((R/'native_import_copper.json').read_text());prior=json.loads((S/'review_before/native_import_copper.json').read_text())
check('zone_count_preserved',len(g['zones'])==len(old['zones']))
check('zone_outlines_and_cutouts_preserved',all({k:v for k,v in z.items() if k!='filled'}=={k:v for k,v in previous.items() if k!='filled'} for z,previous in zip(g['zones'],old['zones'])))
def copper(fs,layer,net):return unary_union([Polygon(f['outline'],f['holes']).buffer(0) for f in fs if f['layer']==layer and f['net']==net])
keys={(f['layer'],f['net']) for f in prior};check('copper_layer_net_sets_preserved',keys=={(f['layer'],f['net']) for f in fill})
deltas={}
for layer,net in sorted(keys):
    before,after=copper(prior,layer,net),copper(fill,layer,net);change=before.symmetric_difference(after)
    check(layer+'_'+net+'_copper_preserved_outside_TP1',change.difference(local).area<.00001 and before.difference(after).area<.00001)
    if net!='GND':check(layer+'_'+net+'_unchanged',change.area<.00001)
    else:check(layer+'_TP1_fully_restored_to_GND',after.buffer(.00001).covers(local))
    deltas[layer+'/'+net]=after.area-before.area

def mask(path):
    result=[]
    with olefile.OleFileIO(path) as o:
        for raw in records(o.openstream('Regions6/Data').read(),11):
            if raw[0]!=38:continue
            n=struct.unpack_from('<I',raw,18)[0];q=parse(raw[22:22+n]);off=22+n;assert q['NAME'].startswith('BOTTOM_GND_EXPOSURE_')
            loops=[]
            for _ in range(1+struct.unpack_from('<H',raw,14)[0]):
                size=struct.unpack_from('<I',raw,off)[0];off+=4;points=[]
                for _ in range(size):
                    x,y=struct.unpack_from('<2d',raw,off);off+=16;points.append([x*.00000254,68.58-y*.00000254])
                loops.append(points)
            result.append(Polygon(loops[0],loops[1:]))
    return unary_union(result)
before_mask=mask(S/'before.PcbDoc');after_mask=mask(a.pcb);expected_mask=unary_union([Polygon(f['outline'],f['holes']) for f in intent['bottom_mask_regions']])
check('only_TP1_mask_island_removed',after_mask.symmetric_difference(expected_mask).area<.00001 and after_mask.symmetric_difference(before_mask).difference(local).area<.00001 and before_mask.difference(after_mask).area<.00001)
check('TP1_bottom_GND_exposed',after_mask.covers(center.buffer(1.0)))
check('bottom_opening_only_over_GND',after_mask.difference(copper(fill,'B.Cu','GND').buffer(.00001)).area<.00001)
def pad_masks(path):
    with olefile.OleFileIO(path) as o:
        cs=[parse(b)['SOURCEDESIGNATOR'] for b in blocks(o.openstream('Components6/Data').read())];data=o.openstream('Pads6/Data').read()
    off=0;result={}
    while off<len(data):
        assert data[off]==2;off+=1;bs=[]
        for _ in range(6):n=struct.unpack_from('<I',data,off)[0];off+=4;bs.append(data[off:off+n]);off+=n
        raw=bs[4];ref=cs[struct.unpack_from('<H',raw,7)[0]]
        if ref!='TP1':result[(ref,bs[0])]=(raw[86:94],raw[101:103])
    return result
check('remaining_pad_mask_paste_settings_preserved',pad_masks(a.pcb)==pad_masks(S/'before.PcbDoc'))

def sch(path):
    with olefile.OleFileIO(path) as o:return [{k.upper():v for k,v in parse(b).items()} for b in blocks(o.openstream('FileHeader').read())]
b=sch(S/'before.SchDoc');s=sch(a.schematic)
removed={i for i,q in enumerate(b) if q.get('UNIQUEID') in intent['schematic_top_level_unique_ids']}
while True:
    more=removed|{i for i,q in enumerate(b) if int(q.get('OWNERINDEX','-2'))+1 in removed}
    if more==removed:break
    removed=more
check('only_TP1_schematic_object_count_removed',len(removed)==15 and len(s)==len(b)-15)
def canonical_sch(rs,drop=()):
    def owner(i):
        q=rs[i];index=int(q.get('OWNERINDEX','-2'))+1
        return (owner(index) if index>=1 else [])+[(q.get('RECORD',''),q.get('UNIQUEID',''),q.get('NAME',''))]
    result=[]
    for i,q in enumerate(rs):
        if i in drop or i==0:continue
        d={k:v for k,v in q.items() if k not in ['OWNERINDEX','INDEXINSHEET']}
        # Altium regenerates the hidden parameter object's own ID on save;
        # its pin ID value, owning pin, coordinates and all properties remain checked.
        if d.get('RECORD')=='41' and d.get('NAME')=='PinUniqueId':d.pop('UNIQUEID',None)
        if 'OWNERINDEX' in q:d['PARENT']=owner(int(q['OWNERINDEX'])+1)
        result.append(json.dumps(d,sort_keys=True))
    return Counter(result)
check('all_remaining_schematic_objects_preserved',canonical_sch(s)==canonical_sch(b,removed))
check('schematic_header_preserved', {k:v for k,v in s[0].items() if k!='WEIGHT'}=={k:v for k,v in b[0].items() if k!='WEIGHT'})
check('TP1_absent_from_schematic',not any(q.get('RECORD')=='34' and q.get('TEXT')=='TP1' for q in s))

drc={}
for name,file in [('geometry','geometry_drc.txt'),('native_copper','native_audit_drc.txt')]:
    text=(R/file).read_text();drc[name]=dict(errors=text.count('Severity: error'),warnings=text.count('Severity: warning'),unconnected=int(re.search(r'\*\* Found (\d+) unconnected pads',text).group(1)))
    check(name+'_DRC_no_errors_or_unconnected',drc[name]==dict(errors=0,warnings=1,unconnected=0))
report=dict(pcb_sha256=sha(a.pcb),schematic_sha256=sha(a.schematic),baseline_pcb_sha256=sha(S/'before.PcbDoc'),checks=checks,removed_ref='TP1',removed_drill_diameter_mm=.9779,removed_pad_diameter_mm=1.4779,parts=31,pads=83,vias=965,copper_added_mm2=deltas,bottom_exposure_mm2=after_mask.area,drc=drc,native_screenshot_verified=False)
if a.package:
    app=json.loads((R/'altium_application_check.json').read_text());models=json.loads((R/'component_3d_check.json').read_text())
    check('current_PCB_native_save_reopen',app['pcb_sha256']==sha(a.pcb) and app['open_save_reopen_passed'])
    schlog=(S/'final_schematic.txt').read_text().splitlines();check('current_schematic_native_save_reopen','SCH='+str(a.schematic.resolve()) in schlog and schlog[-1]=='SCH REOPENED' and (S/'final_schematic.txt').stat().st_mtime>=a.schematic.stat().st_mtime)
    check('all_26_models_preserved',models['pcb_sha256']==sha(a.pcb) and models['model_count']==26 and models['embedded_step_bytes_verified'])
    for name in ['BOM_REVIEW.csv','BOM_MANUAL_REVIEW.csv','BOM_SMT_REVIEW.csv']:
        with (S/'assembly_before'/name).open(newline='',encoding='utf-8-sig') as f:reader=csv.DictReader(f);fields=reader.fieldnames;rows=[q for q in reader if q['Designator']!='TP1']
        with (ROOT/'assembly'/name).open('w',newline='',encoding='utf-8') as f:writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    check('TP1_removed_from_BOM',all('TP1' not in (ROOT/'assembly'/n).read_text() for n in ['BOM_REVIEW.csv','BOM_MANUAL_REVIEW.csv','BOM_SMT_REVIEW.csv']))
    summary=dict(release_status='REVIEW ONLY',checks=checks,drc=drc,native_import=native,sha256={q.name:sha(q) for q in ROOT.glob('*.P*')},schematic_sha256=sha(a.schematic),Altium_application_open_save=True,Altium_application_reopen=True,Altium_application_ERC_DRC=False,SI_PI_EMC_thermal_validated=False,
        baseline_validation=str(S/'review_before/validation_summary.json'),baseline_validation_sha256=sha(S/'review_before/validation_summary.json'),baseline_check_count=len(baseline['checks']),validation_method='Full independent current native import and DRC; exact object comparison to the previous verified PCB, allowing only TP1 removal and local GND/mask restoration. Prior 168 feature checks are historical baseline evidence, not claimed rerun.',warning=baseline['warning'],latest_audit='remove_tp1_check.json')
    (R/'validation_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
(R/'remove_tp1_check.json').write_text(json.dumps(report,indent=2)+'\n')
print('TP1 removal verified:',len(checks),'checks;',drc,'31 parts, 83 pads, 965 unchanged vias')
