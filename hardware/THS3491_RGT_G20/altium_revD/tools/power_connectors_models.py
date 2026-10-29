"""Nominal connector STEP envelopes from the cited mechanical drawings (FreeCAD)."""
from pathlib import Path
import json,hashlib,re
import FreeCAD as App
import Part
ROOT=Path(__file__).resolve().parents[1];S=ROOT/'staging/dc_inputs_20261028';OUT=ROOT/'models3d'
# Reuse only the colour/STEP writer, never run the old full-board model builder.
src=(ROOT/'tools/build_component_models.py').read_text()
exec(src[src.index('SILVER ='):src.index('standard =')])
axis=App.Vector(0,1,0)
body=box(-4.5,-13.7,0,9,14.4,11)
opening=Part.makeCylinder(3.25,9.5,App.Vector(0,-13.71,6.5),axis)
body=body.cut(opening)
pin=Part.makeCylinder(1.,8.,App.Vector(0,-12.7,6.5),axis)
terminals=[box(-.5,-.1,-3.5,1,.2,3.5),box(-.5,-6.1,-3.5,1,.2,3.5),box(4.6,-3.5,-3.5,.2,1,3.5)]
colored_step('PJ-102AH_nominal.step',[body,pin,*terminals],[BLACK,SILVER,*([SILVER]*3)])
data=json.loads((S/'placements.json').read_text())
intent=json.loads((S/'intent.json').read_text())
for d in intent['connectors']:
 data['placements'].append(dict(ref=d['ref'],model='PJ-102AH_nominal.step',
  x_mm=d['pos'][0],y_altium_mm=68.58-d['pos'][1],rotation_z=d['angle'],side='top'))
data['excluded']=[d for d in data['excluded'] if d['ref'] not in ({x['ref'] for x in intent['connectors']} | set(intent['removed_components']))]
for name in ['PJ-102AH_nominal.step']:
 path=OUT/name;shape=Part.Shape();shape.read(str(path));assert shape.isValid();b=shape.BoundBox
 mesh=[]
 for solid in shape.Solids:
  vv,ff=solid.tessellate(.05);mesh.append(dict(vertices=[[v.x,v.y,v.z] for v in vv],faces=ff))
 (ROOT/'staging/models3d_probe'/(path.stem+'.mesh.json')).write_text(json.dumps(mesh))
 data['assets'].append(dict(file=name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bounds_mm=[b.XMin,b.YMin,b.ZMin,b.XMax,b.YMax,b.ZMax],solids=len(shape.Solids),source='Nominal drawing-based model; power_connectors_intent.json sources'))
assert len(data['placements'])==26
(OUT/'placements.json').write_text(json.dumps(data,indent=2)+'\n')
print('Added 1 DC jack asset / 2 placements; 26 total models')
