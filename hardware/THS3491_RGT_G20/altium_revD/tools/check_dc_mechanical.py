"""Check new jack solids against every existing fitted body and mounting envelope."""
from pathlib import Path
import json
import FreeCAD as A
import Part
ROOT=Path(__file__).resolve().parents[1]
data=json.loads((ROOT/'models3d/placements.json').read_text());g=json.loads((ROOT/'review/native_geometry.json').read_text())
shapes={}
for r in data['placements']:
    s=Part.Shape();s.read(str(ROOT/'models3d'/r['model']))
    if r['side']=='bottom':
        m=A.Matrix();m.A33=-1;s=s.transformGeometry(m);s.translate(A.Vector(0,0,-1.6))
    s.rotate(A.Vector(),A.Vector(0,0,1),r['rotation_z']);s.translate(A.Vector(r['x_mm'],r['y_altium_mm'],0));shapes[r['ref']]=s
distances={}
for ref in ['J9','J10']:
    s=shapes[ref];b=s.BoundBox
    assert b.XMin>=0 and b.XMax<=g['board_width'] and b.YMin>=-.001 and b.YMax<=g['board_height']+.001
    distances[ref]={}
    for other,t in shapes.items():
        if other==ref:continue
        d=s.distToShape(t)[0];assert d>.1,(ref,other,d)
        distances[ref][other]=round(d,4)
    for p in g['pads']:
        if p['ref'] in ['H1','H2','H3','H4']:
            t=Part.makeCylinder(3,12,A.Vector(p['pos'][0],68.58-p['pos'][1],0))
            d=s.distToShape(t)[0];assert d>.1,(ref,p['ref'],d)
            distances[ref][p['ref']+'_6mm_screw_head']=round(d,4)
report=dict(new_jack_body_collisions=0,minimum_clearance_mm={r:min(d.values()) for r,d in distances.items()},clearances_mm=distances,nominal_model_check=True,plug_mating_direction='J9 top edge; J10 bottom edge',board_size_mm=[g['board_width'],g['board_height']])
(ROOT/'review/dc_mechanical_check.json').write_text(json.dumps(report,indent=2))
print(report['minimum_clearance_mm'])
