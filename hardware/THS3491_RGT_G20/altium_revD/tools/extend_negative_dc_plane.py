"""Extend VIN_N like VIN_P, retaining both jack footprints and all existing wiring."""
import hashlib,json,re,shutil
import olefile
from native_update import ROOT,blocks,parse,props,mil,update_copy
S=ROOT/'staging/dc_planes_both_20261028';S.mkdir(exist_ok=False)
pcb=ROOT/'QSTL_THS3491_RGT_G20_RevD.PcbDoc'
shutil.copy2(pcb,S/'before.PcbDoc')
shutil.copy2(ROOT/'QSTL_THS3491_RGT_G20_RevD.SchDoc',S/'before.SchDoc')
shutil.copy2(ROOT/'dc_plane_intent.json',S/'plane_intent_before.json')
shutil.copytree(ROOT/'review',S/'review_before',ignore=shutil.ignore_patterns('*.png','*.svg'))
g=json.loads((ROOT/'review/intended_geometry.json').read_text())
intent=json.loads((ROOT/'dc_plane_intent.json').read_text())
positive={k:intent[k] for k in ['zone','net','layer','old_outline_mm','outline_mm']};positive['ref']='J9'
outline=[[9.39202,46.98],[23.3,46.98],[23.3,63.68],[16.4,63.68],[16.4,50.98],[9.39202,50.98]]
name='L1_NEGATIVE_INPUT';zone=next(z for z in g['zones'] if z['name']==name);old=zone['outline']
zone['outline']=outline;zone.pop('filled',None)
negative=dict(zone=name,net='VIN_N',layer='F.Cu',ref='J10',old_outline_mm=old,outline_mm=outline)
intent['planes']=[positive,negative]
intent['request']='User requested both positive and negative raw supply copper planes expanded around their fixed DC jack pads.'
intent['unchanged']=[s for s in intent['unchanged'] if s!='negative input']
intent['pinout'].update({'J10.1':'VIN_N center','J10.2':'GND sleeve','J10.3':'NC sleeve switch'})
intent['negative_extension_baseline_sha256']=hashlib.sha256(pcb.read_bytes()).hexdigest()
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
print('Both plane definitions prepared; component, pad, track and via streams unchanged')
