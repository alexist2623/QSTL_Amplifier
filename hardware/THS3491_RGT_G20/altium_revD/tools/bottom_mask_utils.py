"""Shared geometry helpers for the actual bottom-side solder mask."""
import struct
import olefile
from shapely.geometry import Polygon,Point,box
from shapely.affinity import rotate
from shapely.ops import unary_union
from native_update import records,parse
MOUNTS={'H1','H2','H3','H4'}

def pad_shape(p):
    x,y=p['pos'];w,h=p['size']
    q=Point(x,y).buffer(w/2,resolution=48) if p['shape']==0 else box(x-w/2,y-h/2,x+w/2,y+h/2)
    return rotate(q,-p['angle'],origin=(x,y))

def protection(g):
    pins=[pad_shape(p).buffer(.30,join_style=2) for p in g['pads'] if 'B.Cu' in p['layers'] and p['ref'] not in MOUNTS]
    vias=[Point(v['pos']).buffer(v['diameter']/2+.30,resolution=32) for v in g['vias'] if v['net']!='GND']
    return unary_union(pins+vias)

def read_bottom_mask(path):
    rows=[]
    with olefile.OleFileIO(path) as o:
        for raw in records(o.openstream('Regions6/Data').read(),11):
            if raw[0]!=38:continue
            n=struct.unpack_from('<I',raw,18)[0];q=parse(raw[22:22+n]);off=22+n
            assert q['NAME'].startswith('BOTTOM_GND_EXPOSURE_')
            loops=[]
            for _ in range(1+struct.unpack_from('<H',raw,14)[0]):
                count=struct.unpack_from('<I',raw,off)[0];off+=4;pts=[]
                for _ in range(count):
                    x,y=struct.unpack_from('<2d',raw,off);off+=16;pts.append([x*.00000254,68.58-y*.00000254])
                loops.append(pts)
            rows.append(dict(outline=loops[0],holes=loops[1:]))
    return rows

def union_rows(rows):return unary_union([Polygon(r['outline'],r['holes']).buffer(0) for r in rows])
def serialize(q):return dict(outline=[list(p) for p in list(q.exterior.coords)[:-1]],holes=[[list(p) for p in list(h.coords)[:-1]] for h in q.interiors])
