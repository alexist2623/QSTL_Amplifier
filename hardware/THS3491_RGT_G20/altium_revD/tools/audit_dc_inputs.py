"""Verify DC-only input changes against the backed-up, previously checked board."""
from pathlib import Path
from collections import Counter
import argparse, hashlib, json, math, struct
import olefile
from native_update import blocks, parse, records
from current_intent import l3_intent,l3_zones,before_rf_vias
from shapely.geometry import Point, LineString

ROOT=Path(__file__).resolve().parents[1];S=ROOT/'staging/dc_inputs_20261028';R=ROOT/'review'
p=argparse.ArgumentParser();p.add_argument('--pcb',type=Path,default=ROOT/'QSTL_THS3491_RGT_G20_RevD.PcbDoc')
p.add_argument('--schematic',type=Path,default=ROOT/'QSTL_THS3491_RGT_G20_RevD.SchDoc');a=p.parse_args()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
dc=json.loads((ROOT/'dc_inputs_intent.json').read_text());removed=set(dc['removed_components']);new={'J9','J10'}
old=json.loads((S/'review_before/intended_geometry.json').read_text());g=json.loads((R/'native_geometry.json').read_text())
audit=json.loads((R/'native_import_check.json').read_text())
assert not audit['errors'] and audit['source_sha256']==sha(a.pcb)
def canonical(q):return json.dumps(q,sort_keys=True)
def counter(q):return Counter(map(canonical,q))
assert g['board_width']==old['board_width'] and g['board_height']==old['board_height']
for key in ['parts','pads']:
    assert counter(q for q in g[key] if q['ref'] not in new)==counter(q for q in old[key] if q['ref'] not in removed),key
assert counter(g['tracks'])==counter(old['tracks']+dc['added_tracks'])
assert g['arcs']==old['arcs'] and g['draw']==old['draw']
layer_fix=json.loads((ROOT/'layer_mask_via_intent.json').read_text()) if (ROOT/'layer_mask_via_intent.json').exists() else {}
assert counter(before_rf_vias(g['vias']))+counter(dc['removed_ground_vias'])+counter(layer_fix.get('removed_ground_vias',[]))+counter(l3_intent().get('removed_ground_vias',[]))==counter(old['vias'])
assert all(v['net']=='GND' for v in dc['removed_ground_vias'])
expected_zones=[{k:v for k,v in z.items() if k!='filled'} for z in old['zones']]
expected_zones=[z for z in expected_zones if z not in layer_fix.get('removed_cutouts',[])]
if (ROOT/'dc_plane_intent.json').exists():
    plane=json.loads((ROOT/'dc_plane_intent.json').read_text())
    for spec in plane.get('planes',[plane]):
        next(z for z in expected_zones if z['name']==spec['zone'])['outline']=spec['outline_mm']
assert [{k:v for k,v in z.items() if k!='filled'} for z in g['zones']]==l3_zones(expected_zones)

def sch(path):
    with olefile.OleFileIO(path) as o:return [{k.upper():v for k,v in parse(b).items()} for b in blocks(o.openstream('FileHeader').read())]
def refs(rs):return {int(r['OWNERINDEX'])+1:r['TEXT'] for r in rs if r.get('RECORD')=='34'}
def component_values(rs):
    return {ref:tuple(rs[i].get(k,'0' if k=='ORIENTATION' else '') for k in ['LIBREFERENCE','LOCATION.X','LOCATION.Y','ORIENTATION','UNIQUEID']) for i,ref in refs(rs).items()}
def pin_values(rs):
    rm=refs(rs)
    return {(rm[int(q['OWNERINDEX'])+1],q['DESIGNATOR']):tuple(q.get(k,'0') for k in ['LOCATION.X','LOCATION.Y','PINLENGTH','PINCONGLOMERATE','ELECTRICAL']) for q in rs if q.get('RECORD')=='2'}
def wires(rs):return Counter(tuple((float(q.get('X'+str(i),0)),float(q.get('Y'+str(i),0))) for i in range(1,int(q['LOCATIONCOUNT'])+1)) for q in rs if q.get('RECORD')=='27')
def labels(rs):return Counter((q['TEXT'],float(q.get('LOCATION.X',0)),float(q.get('LOCATION.Y',0))) for q in rs if q.get('RECORD')=='25')
before=sch(S/'before.SchDoc');after=sch(a.schematic)
bc=component_values(before);ac=component_values(after)
assert set(ac)==set(bc)-removed|new
assert {k:v for k,v in ac.items() if k not in new}=={k:v for k,v in bc.items() if k not in removed}
bp=pin_values(before);ap=pin_values(after)
assert {k:v for k,v in ap.items() if k[0] not in new}=={k:v for k,v in bp.items() if k[0] not in removed}
removed_ids={'TOQYGBHH','JRMAYUVE','MMFGONZR','YSVVKXGV','JPQXJXMS','HMLYGRBE','ICRMDGUI','PHWILOEK'}
remaining=[q for q in before if q.get('UNIQUEID') not in removed_ids]
added_wires=Counter();added_labels=Counter();pin_nets={}
segments=[LineString(q) for q in wires(after)]
for ref,y,net in [('J9',330,'VIN_P'),('J10',170,'VIN_N')]:
    for num,dy,n in [('1',30,net),('2',0,'GND'),('3',-30,'')]:
        v=ap[ref,num];x,py,length,cong=map(float,v[:4]);dx,dy_tip=[(1,0),(0,1),(-1,0),(0,-1)][int(cong)&3]
        tip=(x+dx*length,py+dy_tip*length)
        assert tip==(170,y+dy)
        attached=[q for q in segments if q.distance(Point(tip))<1e-6]
        if n:
            endx=240. if num=='1' else 190.
            wire=((170.,float(y+dy)),(endx,float(y+dy)));added_wires[wire]+=1
            label=(n,endx,float(y+dy))
            if num=='2':added_labels[label]+=1
            assert any(q.distance(Point(label[1:]))<1e-6 for q in attached)
        else:assert not attached
        pad=next(q for q in g['pads'] if (q['ref'],q['num'])==(ref,num));assert pad['net']==n
        pin_nets[ref+'.'+num]=n or 'NC'
assert wires(after)==wires(remaining)+added_wires
assert labels(after)==labels(remaining)+added_labels
assert 'R15' not in ac
log=(S/'schematic_native.txt').read_text().splitlines()
assert 'SCH SAVED CLOSED' in log and 'SCH REOPENED' in log
assert (S/'schematic_native.txt').stat().st_mtime>=a.schematic.stat().st_mtime
with olefile.OleFileIO(a.pcb) as o:
    cs=[parse(b) for b in blocks(o.openstream('Components6/Data').read())]
    for c in cs:
        if c['SOURCEDESIGNATOR'] in new:assert c['SOURCEUNIQUEID']==ac[c['SOURCEDESIGNATOR']][-1]
    text=o.openstream('Texts6/Data').read();wide=o.openstream('WideStrings6/Data').read()
    for note in ['TI RF geometry / JLC 4L adaptation','QSTL / THS3491 RGT / REV D']:
        assert note.encode() not in text and note.encode('utf-16le') not in wide
    off=0;silk=[]
    while off<len(text):
        assert text[off]==5;n=struct.unpack_from('<I',text,off+1)[0];raw=text[off+5:off+5+n];off+=5+n
        n=struct.unpack_from('<I',text,off)[0];t=text[off+4:off+4+n];off+=4+n
        if raw[0]==33:
            x,y,h=struct.unpack_from('<iii',raw,13);silk.append((t[1:].decode('cp1252'),[x*.00000254,68.58-y*.00000254],h*.00000254))
    for t in dc['silk']:
        assert any(txt==t['text'] and math.dist(pos,t['pos'])<.00002 and abs(h-t['height'])<.00002 for txt,pos,h in silk),t
report=dict(pcb_sha256=sha(a.pcb),schematic_sha256=sha(a.schematic),baseline_pcb_sha256=sha(S/'before.PcbDoc'),baseline_schematic_sha256=sha(S/'before.SchDoc'),
    existing_schematic_preserved=True,new_connector_pin_nets=pin_nets,native_schematic_save_reopen_verified=True,
    schematic_components=len(ac),pcb_components=len(g['parts']),pads=len(g['pads']),vias=len(g['vias']),
    board_outline_mounts_RF_filters_L2_windows_preserved=True,removed_only_overlapping_ground_vias=len(dc['removed_ground_vias']),
    removed_components=sorted(removed),added_components=sorted(new),review_silkscreen_notes_removed=True,polarity_silkscreen_verified=True,
    native_ERC_DRC=False,screenshot_verified=False)
(R/'dc_inputs_check.json').write_text(json.dumps(report,indent=2)+'\n')
print('DC inputs verified: native PCB geometry, schematic pins/wires/labels, polarity silk and preservation')
