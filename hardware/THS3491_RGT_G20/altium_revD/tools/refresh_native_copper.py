"""Refresh only filled copper from independently checked geometry.

Preserves native component/model data, polygon definitions, free regions and
cutouts. Altium must open/save/reopen the generated copy before delivery.
"""
from pathlib import Path
import argparse
import json
import struct
import uuid
import olefile
from native_update import ROOT, blocks, parse, props, records, rec, point, mil, LAY, LNAME, update_copy

p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
p.add_argument('--output',type=Path,required=True);a=p.parse_args()
g=json.loads((ROOT/'review/native_geometry.json').read_text())
with olefile.OleFileIO(a.source) as o:
    streams={'/'.join(k):o.openstream(k).read() for k in o.listdir()}
polys=[parse(v) for v in blocks(streams['Polygons6/Data'])]
nets={parse(v)['NAME']:i for i,v in enumerate(blocks(streams['Nets6/Data']))}
def name(v): return ''.join(chr(int(c)) for c in v['NAME'].split(','))
regions=[];shapes=[]
for key,target in [('Regions6',regions),('ShapeBasedRegions6',shapes)]:
    target.extend(rec(11,v) for v in records(streams[key+'/Data'],11)
                  if struct.unpack_from('<H',v,5)[0]==65535)
for z in g['zones']:
    if z['keepout']:continue
    layer=LAY[z['layer']]
    hits=[i for i,v in enumerate(polys) if name(v)==z['name'] and v['LAYER']==LNAME[layer]]
    assert len(hits)==1,(z['name'],hits)
    for f in z['filled']:
        h=bytearray(18);h[0]=layer;h[1]=12
        struct.pack_into('<HHHHH',h,3,nets[z['net']],hits[0],65535,65535,65535)
        struct.pack_into('<H',h,14,len(f['holes']))
        d=dict(V7_LAYER=LNAME[layer],NAME=z['name'],KIND=0,SUBPOLYINDEX=0,
               UNIONINDEX=0,ARCRESOLUTION=mil(.02),ISSHAPEBASED='FALSE',ISBOARDCUTOUT='FALSE')
        prefix=bytes(h)+props(d)+struct.pack('<I',len(f['outline']))
        plain=prefix+b''.join(struct.pack('<2d',*point(v)) for v in f['outline'])
        curved=prefix+b''.join(struct.pack('<B5i2d',0,*point(v),0,0,0,0.,0.) for v in f['outline']+[f['outline'][0]])
        for hole in f['holes']:
            extra=struct.pack('<I',len(hole))+b''.join(struct.pack('<2d',*point(v)) for v in hole)
            plain+=extra;curved+=extra
        regions.append(rec(11,plain));shapes.append(rec(11,curved))
updates={}
for key,rows in [('Regions6',regions),('ShapeBasedRegions6',shapes)]:
    updates[key+'/Data']=b''.join(rows);updates[key+'/Header']=struct.pack('<I',len(rows))
ids=streams['PrimitiveGuids/Data'];rows=[ids[i:i+24] for i in range(0,len(ids),24)
     if struct.unpack_from('<I',ids,i)[0] not in [4953,5209]]
for tag,items in [(4953,regions),(5209,shapes)]:
    rows.extend(struct.pack('<II',tag,i)+uuid.uuid5(uuid.NAMESPACE_URL,f'qstl/revd/output-load-removed/{tag}/{i}').bytes_le for i in range(len(items)))
updates['PrimitiveGuids/Data']=b''.join(rows);updates['PrimitiveGuids/Header']=struct.pack('<I',len(rows))
update_copy(a.source.resolve(),a.output.resolve(),updates)
print('Wrote filled copper with',len(regions),'regions; native save/reopen required:',a.output)
