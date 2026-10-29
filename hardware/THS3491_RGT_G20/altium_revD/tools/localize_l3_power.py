"""Keep L3 filtered supply corridors as annotated; fill the rest with GND."""
from pathlib import Path
import hashlib,json,re,shutil,struct,uuid
import olefile
from shapely.geometry import Polygon,LineString,Point
from shapely.ops import unary_union
from native_update import ROOT,blocks,parse,props,mil,update_copy,records,rec,point

R=ROOT/'review';S=ROOT/'staging/l3_local_power_20261028';S.mkdir(exist_ok=False)
pcb=ROOT/'QSTL_THS3491_RGT_G20_RevD.PcbDoc'
shutil.copy2(pcb,S/'before.PcbDoc');shutil.copy2(pcb.with_suffix('.SchDoc'),S/'before.SchDoc')
shutil.copytree(R,S/'review_before',ignore=shutil.ignore_patterns('*.png','*.svg'))
g=json.loads((R/'native_geometry.json').read_text())
outlines={
 'VCC':[[18.3,8.9],[28.2,8.9],[28.2,12.56139],[23.2,12.56139],[23.2,16.0],[24.4,19.0],[22.6,21.4],[20.7,26.8],[17.35,26.8],[17.35,24.8],[18.2,22.8],[18.2,17.3],[19.2,13.2]],
 'VEE':[[18.8,29.3],[20.9,29.3],[20.9,36.0],[20.5,39.0],[21.0,46.98],[9.39202,46.98],[9.39202,43.31861],[13.0,42.6],[16.0,43.2],[14.5,39.8],[14.6,34.8],[16.2,33.1]]}
branches={
 'VCC':[[19.8,25.8],[20.7,27.1],[21.0,27.4],[23.9,27.4],[24.0,27.7],[24.9,30.8]],
 'VEE':[[19.8,30.6],[20.9,32.0],[22.4,32.6],[24.1,32.6],[24.9,32.2]]}
specs=[]
for net in ['VCC','VEE']:
    q=unary_union([Polygon(outlines[net]),LineString(branches[net]).buffer(.15,cap_style=2,join_style=2),Point(branches[net][-1]).buffer(.23,resolution=32)])
    assert q.is_valid and q.geom_type=='Polygon' and not q.interiors
    z=next(z for z in g['zones'] if z['name']=='L3_'+net)
    old={k:v for k,v in z.items() if k!='filled'}
    z['outline']=[list(p) for p in list(q.exterior.coords)[:-1]];z['priority']=2 if net=='VCC' else 1;z.pop('filled',None)
    specs.append(dict(net=net,name=z['name'],old_zone=old,new_zone=z.copy(),corridor_outline_mm=outlines[net],C7_branch_mm=branches[net],branch_width_mm=.30))
ground=dict(net='GND',name='L3_GND',layer='In2.Cu',priority=0,keepout=False,outline=[[.3,.3],[41.35601,.3],[41.35601,68.28],[.3,68.28]])
g['zones'].append(ground)
bridge=LineString([(21.6,15.2),(21.6,20.5)])
removed_vias=[v for v in g['vias'] if v['net']=='GND' and bridge.distance(Point(v['pos']))<.4+v['diameter']/2+.206]
assert len(removed_vias)==7
g['vias']=[v for v in g['vias'] if v not in removed_vias]
intent=dict(request='User blue annotated L3 power corridors; GND everywhere else. Preserve all hardware positions and connectivity.',
    baseline_pcb_sha256=hashlib.sha256(pcb.read_bytes()).hexdigest(),planes=specs,added_ground_zone=ground,
    C7_branch_reason='Existing C7 lies outside annotated corridors; 0.30 mm branches preserve both via-in-pad supply connections.',
    removed_ground_vias=removed_vias,minimum_bridge_width_mm=.8,bridge_line_mm=[[21.6,15.2],[21.6,20.5]],
    unchanged=['components','pads','all other vias','tracks','arcs','board outline','mounting holes','L1','L2','L4','bottom mask','schematic','models'])
(ROOT/'l3_local_power_intent.json').write_text(json.dumps(intent,indent=2)+'\n');(S/'geometry.json').write_text(json.dumps(g,indent=2))
with olefile.OleFileIO(pcb) as o:streams={'/'.join(k):o.openstream(k).read() for k in o.listdir()}
polys=[parse(b) for b in blocks(streams['Polygons6/Data'])]
nets={parse(b)['NAME']:i for i,b in enumerate(blocks(streams['Nets6/Data']))}
def name(q):return ''.join(chr(int(c)) for c in q['NAME'].split(','))
def vertices(q,outline):
    for key in list(q):
        if re.fullmatch(r'(KIND|VX|VY|CX|CY|SA|EA|R)\d+',key):del q[key]
    for i,(x,y) in enumerate(outline+[outline[0]]):
        q.update({f'KIND{i}':0,f'VX{i}':mil(x),f'VY{i}':mil(68.58-y),f'CX{i}':'0mil',f'CY{i}':'0mil',f'SA{i}':0,f'EA{i}':0,f'R{i}':'0mil'})
for spec in specs:
    q=next(q for q in polys if name(q)==spec['name']);vertices(q,spec['new_zone']['outline'])
q=dict(next(q for q in polys if name(q)=='L3_VEE'));q.update(NET=str(nets['GND']),NAME=','.join(str(ord(c)) for c in ground['name']),POURINDEX=str(len(polys)+1),UNIQUEID='L3GNDNEW')
vertices(q,ground['outline']);polys.append(q)
updates={'Polygons6/Data':b''.join(props(q) for q in polys),'Polygons6/Header':struct.pack('<I',len(polys))}
via_rows=[]
for raw in records(streams['Vias6/Data'],3):
    xy=struct.unpack_from('<ii',raw,13)
    if any(abs(xy[0]-point(v['pos'])[0])<10 and abs(xy[1]-point(v['pos'])[1])<10 for v in removed_vias):continue
    via_rows.append(rec(3,raw))
assert len(via_rows)==len(g['vias'])
updates.update({'Vias6/Data':b''.join(via_rows),'Vias6/Header':struct.pack('<I',len(via_rows))})
ids=streams['PrimitiveGuids/Data'];rows=[ids[i:i+24] for i in range(0,len(ids),24) if struct.unpack_from('<I',ids,i)[0] not in [1034,3843]]
rows += [struct.pack('<II',1034,i)+uuid.uuid5(uuid.NAMESPACE_URL,f'qstl/l3-local-power/polygon/{i}').bytes_le for i in range(len(polys))]
rows += [struct.pack('<II',3843,i)+uuid.uuid5(uuid.NAMESPACE_URL,f'qstl/l3-local-power/via/{i}').bytes_le for i in range(len(via_rows))]
updates.update({'PrimitiveGuids/Data':b''.join(rows),'PrimitiveGuids/Header':struct.pack('<I',len(rows))})
update_copy(pcb,S/'outline.PcbDoc',updates)
print('Localized L3 power polygons and added GND outline:',[(s['net'],Polygon(s['new_zone']['outline']).area) for s in specs])
