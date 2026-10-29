"""Check the authorized R15 removal and explanatory-silkscreen deletion."""
from pathlib import Path
from collections import Counter
import argparse
import hashlib
import json
import struct
import olefile

ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def sch_records(path):
    with olefile.OleFileIO(path) as o:b=o.openstream('FileHeader').read()
    pos=0;rows=[]
    while pos<len(b):
        n=struct.unpack_from('<I',b,pos)[0];pos+=4
        assert n>>24==0
        raw=b[pos:pos+n];pos+=n
        rows.append({k.upper():v for k,v in (s.split('=',1) for s in raw.rstrip(b'\0').decode('cp1252').split('|') if '=' in s)})
    return rows
def refmap(rs):
    return {int(r['OWNERINDEX'])+1:r['TEXT'] for r in rs if r.get('RECORD')=='34'}
def components(rs):
    refs=refmap(rs)
    return {ref:tuple(rs[i].get(k,'0' if k in ['ORIENTATION'] else '') for k in ['LIBREFERENCE','LOCATION.X','LOCATION.Y','ORIENTATION']) for i,ref in refs.items()}
def pins(rs):
    refs=refmap(rs)
    return { (refs[int(r['OWNERINDEX'])+1],r['DESIGNATOR']):tuple(r.get(k,'0') for k in ['LOCATION.X','LOCATION.Y','PINLENGTH','PINCONGLOMERATE','ELECTRICAL'])
            for r in rs if r.get('RECORD')=='2' }
def wires(rs):
    return Counter(tuple((r.get('X'+str(i), '0'),r.get('Y'+str(i),'0')) for i in range(1,int(r['LOCATIONCOUNT'])+1)) for r in rs if r.get('RECORD')=='27')
def labels(rs):
    return Counter((r.get('TEXT',''),r.get('LOCATION.X','0'),r.get('LOCATION.Y','0')) for r in rs if r.get('RECORD')=='25')

p=argparse.ArgumentParser();p.add_argument('--pcb',type=Path,default=ROOT/'QSTL_THS3491_RGT_G20_RevD.PcbDoc')
p.add_argument('--schematic',type=Path,default=ROOT/'QSTL_THS3491_RGT_G20_RevD.SchDoc')
p.add_argument('--output',type=Path,default=ROOT/'review/output_load_removal.json');a=p.parse_args()
baseline=ROOT.parent/'altium_revC/QSTL_THS3491_RGT_G20_RevC.SchDoc'
before=sch_records(baseline);after=sch_records(a.schematic)
bc=components(before);ac=components(after)
assert ac=={k:v for k,v in bc.items() if k!='R15'}
bp=pins(before);ap=pins(after)
assert ap=={k:v for k,v in bp.items() if k[0]!='R15'}, 'Remaining schematic pins changed'
bw=wires(before)
for w in [(('1250','620'),('1250','650')),(('1250','530'),('1250','505'))]:
    assert bw[w]==1;del bw[w]
assert wires(after)==bw,'Unexpected schematic wire changes'
bl=labels(before);bl[('GND','1250','505')]-=1
assert labels(after)==+bl,'Unexpected schematic net label changes'
assert not any(r.get('RECORD')=='29' and r.get('LOCATION.X')=='1250' and r.get('LOCATION.Y')=='650' for r in after)
with olefile.OleFileIO(a.pcb) as o:
    b=o.openstream('Components6/Data').read();assert b'SOURCEDESIGNATOR=R15|' not in b
    text=o.openstream('Texts6/Data').read()
    wide=o.openstream('WideStrings6/Data').read()
    for note in ['TI RF geometry / JLC 4L adaptation','QSTL / THS3491 RGT / REV D']:
        assert note.encode() not in text and note.encode('utf-16le') not in wide
report=dict(pcb_sha256=sha(a.pcb),schematic_sha256=sha(a.schematic),baseline_schematic_sha256=sha(baseline),
            removed_component='R15',removed_value='1Meg',remaining_schematic_components=len(ac),
            remaining_schematic_pins=len(ap),remaining_pin_properties_unchanged=True,
            only_two_R15_branch_wires_removed=True,only_R15_ground_label_removed=True,
            obsolete_junction_removed=True,remaining_components_unchanged=True,
            review_silkscreen_notes_removed=True,output_signal_path_retained=True,
            native_schematic_ERC=False)
a.output.write_text(json.dumps(report,indent=2)+'\n')
print('R15 removed; all other schematic pins/components/wires/labels preserved; review silk removed')
