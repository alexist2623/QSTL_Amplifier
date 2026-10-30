"""Remove the three L2 trace-spanning cutouts; retain only RF pad windows."""
import json,struct,uuid
import olefile
from native_update import ROOT,records,rec,parse,update_copy
R=ROOT/'review';S=ROOT/'staging/l3_plane_cleanup_20261030'
names={'INPLUS_LOCAL_WINDOW','OUT_LOCAL_WINDOW','FB_INV_LOCAL_WINDOW'}
g=json.loads((R/'native_geometry.json').read_text())
removed=[z for z in g['zones'] if z['layer']=='In1.Cu' and z['keepout'] and z['name'] in names]
assert len(removed)==3
g['zones']=[z for z in g['zones'] if z not in removed]
assert len([z for z in g['zones'] if z['keepout'] and z['layer']=='In1.Cu'])==18
(S/'geometry_pad_only.json').write_text(json.dumps(g,indent=2)+'\n')
intent=json.loads((ROOT/'l3_cleanup_intent.json').read_text())
intent['L2_pad_only_correction']=dict(request='Only cut out L2 GND beneath RF component pads; restore GND beneath connecting traces.',removed_trace_cutout_names=sorted(names),removed_outlines=[dict(name=z['name'],outline=z['outline']) for z in removed],retained_pad_windows=18,pad_window_margin_mm=.1)
intent['preserved'].remove('all L2 cutouts')
intent['preserved'].append('18 L2 RF pad windows; three L1 cutouts unchanged')
(ROOT/'l3_cleanup_intent.json').write_text(json.dumps(intent,indent=2)+'\n')
with olefile.OleFileIO(S/'candidate.PcbDoc') as o:streams={'/'.join(k):o.openstream(k).read() for k in o.listdir()}
updates={};counts={}
for key in ['Regions6','ShapeBasedRegions6']:
    rows=[];found=[]
    for raw in records(streams[key+'/Data'],11):
        size=struct.unpack_from('<I',raw,18)[0];q=parse(raw[22:22+size])
        if raw[0]==2 and q.get('KIND')=='1' and q.get('NAME') in names:
            found.append(q['NAME']);continue
        rows.append(rec(11,raw))
    assert set(found)==names and len(found)==3
    updates[key+'/Data']=b''.join(rows);updates[key+'/Header']=struct.pack('<I',len(rows));counts[key]=len(rows)
ids=streams['PrimitiveGuids/Data'];rows=[ids[i:i+24] for i in range(0,len(ids),24) if struct.unpack_from('<I',ids,i)[0] not in [4953,5209]]
for tag,key in [(4953,'Regions6'),(5209,'ShapeBasedRegions6')]:
    rows += [struct.pack('<II',tag,i)+uuid.uuid5(uuid.NAMESPACE_URL,f'qstl/l2-pad-only/{tag}/{i}').bytes_le for i in range(counts[key])]
updates['PrimitiveGuids/Data']=b''.join(rows);updates['PrimitiveGuids/Header']=struct.pack('<I',len(rows))
update_copy(S/'candidate.PcbDoc',S/'pad_only_outline.PcbDoc',updates)
print('Removed three L2 trace-spanning cutouts; retained 18 pad windows')
