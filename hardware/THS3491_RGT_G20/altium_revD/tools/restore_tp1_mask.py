"""Remove only the obsolete TP1 protected island from the bottom GND opening."""
import json,struct
from shapely.geometry import Point,Polygon
from shapely.ops import unary_union
from native_update import ROOT,records,rec,props,point,mil,update_copy
from fix_layer_mask_vias import streams_of,put,reindex
S=ROOT/'staging/remove_tp1_20261028';R=ROOT/'review'
intent=json.loads((ROOT/'remove_tp1_intent.json').read_text())
center=Point(intent['position_mm']);local=center.buffer(intent['local_restore_radius_mm'])
g=json.loads((R/'native_geometry.json').read_text());old=json.loads((S/'review_before/native_geometry.json').read_text())
changes=[]
for z,prev in zip(g['zones'],old['zones']):
    assert {k:v for k,v in z.items() if k!='filled'}=={k:v for k,v in prev.items() if k!='filled'}
    def area(q):return unary_union([Polygon(f['outline'],f['holes']).buffer(0) for f in q.get('filled',[])])
    before,after=area(prev),area(z);delta=after.symmetric_difference(before)
    assert delta.difference(local).area<.000001,z['name']
    assert before.difference(after).area<.000001,z['name']
    if delta.area>.000001:assert z['net']=='GND';changes.append(dict(layer=z['layer'],net=z['net'],added_copper_mm2=after.area-before.area))
mask=json.loads((S/'review_before/layer_mask_via_check.json').read_text())['bottom_mask_regions']
removed=[]
for region in mask:
    kept=[]
    for hole in region['holes']:
        if Polygon(hole).covers(center):assert local.covers(Polygon(hole));removed.append(hole)
        else:kept.append(hole)
    region['holes']=kept
assert len(removed)==1
intent.update(bottom_mask_regions=mask,removed_mask_island=removed[0],restored_copper=changes)
(ROOT/'remove_tp1_intent.json').write_text(json.dumps(intent,indent=2)+'\n')
source=S/'filled.PcbDoc';streams=streams_of(source);updates={};changed={}
for name in ['Regions6','ShapeBasedRegions6']:
    rows=[rec(11,raw) for raw in records(streams[name+'/Data'],11) if raw[0]!=38]
    if name=='ShapeBasedRegions6':
        for i,f in enumerate(mask):
            h=bytearray(18);h[0]=38;h[1]=12;struct.pack_into('<5H',h,3,65535,65535,65535,65535,65535);struct.pack_into('<H',h,14,len(f['holes']))
            p=dict(V7_LAYER='BOTTOMSOLDER',NAME='BOTTOM_GND_EXPOSURE_'+str(i),KIND=0,SUBPOLYINDEX=65535,UNIONINDEX=0,ARCRESOLUTION=mil(.02),ISSHAPEBASED='TRUE',ISBOARDCUTOUT='FALSE')
            raw=bytes(h)+props(p)+struct.pack('<I',len(f['outline']))
            raw+=b''.join(struct.pack('<B5i2d',0,*point(v),0,0,0,0.,0.) for v in f['outline']+[f['outline'][0]])
            for hole in f['holes']:raw+=struct.pack('<I',len(hole))+b''.join(struct.pack('<2d',*point(v)) for v in hole)
            rows.append(rec(11,raw))
    put(updates,name,rows);changed[name]=len(rows)
reindex(streams,updates,changed);update_copy(source,S/'candidate.PcbDoc',updates)
print('Restored only TP1 copper/mask:',changes,'removed one mask island')
