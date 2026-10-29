"""Apply the user's annotated VIN_P outline while preserving jack pin locations."""
from pathlib import Path
import json,re,shutil,hashlib
import olefile
from native_update import ROOT,blocks,parse,props,mil,update_copy
S=ROOT/'staging/dc_plane_20261028';S.mkdir(exist_ok=False)
pcb=ROOT/'QSTL_THS3491_RGT_G20_RevD.PcbDoc'
shutil.copy2(pcb,S/'before.PcbDoc')
shutil.copy2(ROOT/'QSTL_THS3491_RGT_G20_RevD.SchDoc',S/'before.SchDoc')
shutil.copytree(ROOT/'review',S/'review_before',ignore=shutil.ignore_patterns('*.png','*.svg'))
g=json.loads((ROOT/'review/intended_geometry.json').read_text())
outline=[[14.2,4.9],[28.2,4.9],[28.2,8.9],[21.1,8.9],[21.1,15.2],[14.2,15.2]]
name='L1_POSITIVE_INPUT'
zone=next(z for z in g['zones'] if z['name']==name);old=zone['outline'];zone['outline']=outline;zone.pop('filled',None)
intent=dict(date='2026-10-28',zone=name,net='VIN_P',layer='F.Cu',old_outline_mm=old,outline_mm=outline,
    request='User blue outline: expand positive raw supply copper into an L shape. Keep connector pins fixed.',
    pinout={'J9.1':'VIN_P center','J9.2':'GND sleeve','J9.3':'NC sleeve switch'},
    switch_operation='3 connects to 2 with no plug; opens on plug insertion. PCB pin 3 remains unconnected.',
    datasheet='https://www.sameskydevices.com/product/resource/pj-102ah.pdf',
    unchanged=['connector pins and holes','all components and 3D models','all tracks and vias','negative input','filtered supply islands','L2 RF-pad windows','schematic','BOM'],
    baseline_pcb_sha256=hashlib.sha256(pcb.read_bytes()).hexdigest())
(ROOT/'dc_plane_intent.json').write_text(json.dumps(intent,indent=2)+'\n')
(S/'geometry.json').write_text(json.dumps(g,indent=2))
with olefile.OleFileIO(pcb) as o:polys=[parse(b) for b in blocks(o.openstream('Polygons6/Data').read())]
changed=0
for q in polys:
    if ''.join(chr(int(c)) for c in q['NAME'].split(','))!=name:continue
    changed+=1
    for key in list(q):
        if re.fullmatch(r'(KIND|VX|VY|CX|CY|SA|EA|R)\d+',key):del q[key]
    for i,(x,y) in enumerate(outline+[outline[0]]):
        q.update({f'KIND{i}':0,f'VX{i}':mil(x),f'VY{i}':mil(68.58-y),f'CX{i}':'0mil',f'CY{i}':'0mil',f'SA{i}':0,f'EA{i}':0,f'R{i}':'0mil'})
assert changed==1
update_copy(pcb,S/'outline.PcbDoc',{'Polygons6/Data':b''.join(props(q) for q in polys)})
print('Expanded VIN_P polygon definition; all pins, tracks, vias and negative input preserved')
