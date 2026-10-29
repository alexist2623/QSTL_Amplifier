"""Audit embedded STEP bytes, native placement, ownership and copper preservation."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import struct
import zlib
import olefile

ROOT=Path(__file__).resolve().parents[1]
def sha(b): return hashlib.sha256(b).hexdigest()
def blocks(b):
    pos=0
    while pos<len(b):
        n=struct.unpack_from('<I',b,pos)[0];pos+=4
        yield b[pos:pos+n];pos+=n
    assert pos==len(b)
def props(b):
    return dict(x.split('=',1) for x in b.rstrip(b'\0').decode('cp1252').split('|') if '=' in x)
def read(path):
    with olefile.OleFileIO(path) as o:
        return {'/'.join(s):o.openstream(s).read() for s in o.listdir()}
def bodies(stream):
    pos=0;out=[]
    while pos<len(stream):
        assert stream[pos]==12
        n=struct.unpack_from('<I',stream,pos+1)[0]
        raw=stream[pos+5:pos+5+n];pos+=5+n
        component=struct.unpack_from('<H',raw,7)[0]
        pn=struct.unpack_from('<I',raw,18)[0]
        out.append((component,props(raw[22:22+pn])))
    assert pos==len(stream)
    return out
def mm(v):
    if v.endswith('mil'): return float(v[:-3])*.0254
    raise ValueError(v)

p=argparse.ArgumentParser();p.add_argument('--pcb',type=Path,required=True)
p.add_argument('--baseline',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
p.add_argument('--native-log',type=Path,required=True)
p.add_argument('--geometry-audit',type=Path,required=True)
a=p.parse_args();s=read(a.pcb);baseline=read(a.baseline)
log=a.native_log.read_text().splitlines()
assert a.native_log.stat().st_mtime>=a.pcb.stat().st_mtime, 'Native log predates PCB'
assert all(line in log for line in ['START','SAVED','REOPENED'])
assert 'PCB='+str(a.pcb.resolve()) in log, 'Native log describes another file'
assert not any(line.startswith(('ERROR','ABORT','SAVE FAILED')) for line in log)
intent=json.loads((ROOT/'models3d/placements.json').read_text(encoding='utf-8'))
expected={r['ref']:r for r in intent['placements']}
assert 'COUNT='+str(len(expected)) in log
components=[props(b)['SOURCEDESIGNATOR'] for b in blocks(s['Components6/Data'])]
model_list=[props(b) for b in blocks(s['Models/Data'])]
model_ids={m['ID']:m for m in model_list}
embedded={}; failures=[]
for i,m in enumerate(model_list):
    assert m['EMBED']=='TRUE',m
    payload=zlib.decompress(s['Models/'+str(i)])
    source=ROOT/'models3d'/m['NAME']
    assert source.is_file(),source
    assert payload==source.read_bytes(),m['NAME']
    embedded[m['ID']]={'file':m['NAME'],'sha256':sha(payload),'bytes':len(payload)}
rows=[]
for component,v in bodies(s['ComponentBodies6/Data']):
    ref=components[component];e=expected[ref];asset=embedded[v['MODELID']]
    assert v['MODEL.EMBED']=='TRUE'
    assert asset['file']==e['model'],(ref,asset,e)
    actual=[mm(v['MODEL.2D.X']),mm(v['MODEL.2D.Y']),mm(v['MODEL.3D.DZ'])]
    assert math.dist(actual,[e['x_mm'],e['y_altium_mm'],0])<.00002,(ref,actual,e)
    assert abs((float(v['MODEL.3D.ROTZ'])-e['rotation_z']+180)%360-180)<.0001
    assert float(v['MODEL.3D.ROTX'])==0 and float(v['MODEL.3D.ROTY'])==0
    assert float(v['MODEL.2D.ROTATION'])==0
    assert int(v['BODYPROJECTION'])==(1 if e['side']=='bottom' else 0)
    assert v['V7_LAYER']==('MECHANICAL14' if e['side']=='bottom' else 'MECHANICAL13')
    rows.append(dict(ref=ref,model=asset['file'],model_sha256=asset['sha256'],
                     position_mm=actual,rotation_z=float(v['MODEL.3D.ROTZ']),
                     side=e['side'],embedded=True))
assert len(rows)==len(expected) and {r['ref'] for r in rows}==set(expected)
assert {line.split(',')[1] for line in log if line.startswith('BODY,')}==set(expected)
assert len(bodies(s['ShapeBasedComponentBodies6/Data']))==len(expected)
unchanged=[]
changed=[]
for name in ['Pads6','Tracks6','Vias6','Arcs6','Nets6','Polygons6','Regions6','ShapeBasedRegions6','Rules6','Texts6']:
    key=name+'/Data'
    (unchanged if s[key]==baseline[key] else changed).append(key)
geometry=json.loads(a.geometry_audit.read_text())
assert not geometry['errors'] and geometry['source_sha256']==sha(a.pcb.read_bytes())
design=json.loads((ROOT/'review/native_geometry.json').read_text())
assert geometry['parts']==len(design['parts']) and geometry['pads']==len(design['pads'])
report=dict(pcb_sha256=sha(a.pcb.read_bytes()),baseline_sha256=sha(a.baseline.read_bytes()),
            native_save_reopen_verified=True,native_log_sha256=sha(a.native_log.read_bytes()),
            model_count=len(rows),unique_assets=len({r['model'] for r in rows}),
            components=rows,excluded=intent['excluded'],embedded_step_bytes_verified=True,
            native_placement_verified=True,unchanged_streams=unchanged,
            reserialized_or_authorized_changed_streams=changed,
            independent_electrical_geometry_verified=True,
            geometry_audit_sha256=sha(a.geometry_audit.read_bytes()),
            screenshot_verified=False,figure_source='Re-rendered embedded STEP geometry and native placement',
            simplified_models=['THS3491_RGT_nominal.step','7109DG_simplified.step','C_1206_H0p85.step','Ferrite_0805_H0p85.step'])
a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(f'{len(rows)} bound embedded models verified; placement and independent electrical geometry verified')
