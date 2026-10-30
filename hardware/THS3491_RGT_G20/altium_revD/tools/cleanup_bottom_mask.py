"""Remove top-side pad shadows from bottom mask; expose all mounting-ring vias."""
import hashlib,json,shutil,struct
from shapely.geometry import Polygon,box
from shapely.ops import unary_union
from shapely import set_precision
from native_update import ROOT,blocks,block,parse,props,records,rec,point,mil,unit,update_copy
from fix_layer_mask_vias import streams_of,put,reindex
from bottom_mask_utils import protection,read_bottom_mask,union_rows,serialize,MOUNTS
R=ROOT/'review';B=R/'bottom_mask_cleanup_baseline';S=ROOT/'staging/bottom_mask_cleanup_20261030'
pcb=ROOT/'QSTL_THS3491_RGT_G20_RevD.PcbDoc';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
g=json.loads((R/'native_geometry.json').read_text());base=json.loads((R/'validation_summary.json').read_text())
assert sha(pcb)==base['sha256'][pcb.name] and all(base['checks'].values())
oldmask=union_rows(read_bottom_mask(pcb))
ground=unary_union([Polygon(f['outline'],f['holes']).buffer(0) for f in json.loads((R/'native_import_copper.json').read_text()) if f['layer']=='B.Cu' and f['net']=='GND'])
desired=ground.buffer(-.01).intersection(box(.5,.5,g['board_width']-.5,g['board_height']-.5)).difference(protection(g).buffer(.002,join_style=2))
desired=set_precision(desired,.001)
pieces=list(desired.geoms) if desired.geom_type=='MultiPolygon' else [desired]
pieces=[p for p in pieces if p.area>.05];desired=unary_union(pieces)
assert oldmask.difference(desired).area<.003
assert desired.difference(ground.buffer(.00001)).area<.00001
assert desired.intersection(protection(g).buffer(-.00001)).area<.00001
B.mkdir(exist_ok=False);S.mkdir(exist_ok=False);(B/'review_before').mkdir()
shutil.copy2(pcb,B/'before.PcbDoc');shutil.copy2(pcb.with_suffix('.SchDoc'),B/'before.SchDoc')
for name in ['native_geometry.json','native_import_copper.json','native_import_cutouts.json','validation_summary.json','mount_mask_check.json','mount_mask_import_check.json']:
    shutil.copy2(R/name,B/'review_before'/name)
(B/'README.md').write_text('Historical baseline before bottom-pad projection cleanup and mounting-via exposure, 2026-10-30.\n')
intent=dict(request='Expose the mounting-ring GND vias and remove top-side footprint/pad projections from bottom solder mask.',baseline_pcb_sha256=sha(pcb),baseline_schematic_sha256=sha(pcb.with_suffix('.SchDoc')),mount_opening_diameter_mm=7.6,mount_mask_expansion_mm=2.2125,mount_via_ring_radius_mm=3.4,mount_via_diameter_mm=.4,mount_via_outer_mask_margin_mm=.2,pin_mask_margin_mm=.30,non_GND_via_mask_margin_mm=.30,board_mask_border_mm=.50,bottom_mask_regions=[serialize(p) for p in pieces],previous_bottom_opening_area_mm2=oldmask.area,bottom_opening_area_mm2=desired.area,removed_top_pad_projections=[dict(ref=p['ref'],pad=p['num']) for p in g['pads'] if 'F.Cu' in p['layers'] and 'B.Cu' not in p['layers'] and (p['ref'],p['num'])!=('U1','17')],protected_actual_bottom_pads=[dict(ref=p['ref'],pad=p['num']) for p in g['pads'] if 'B.Cu' in p['layers'] and p['ref'] not in MOUNTS])
(ROOT/'bottom_mask_cleanup_intent.json').write_text(json.dumps(intent,indent=2)+'\n')
streams=streams_of(pcb);updates={};changed={};refs=[parse(b)['SOURCEDESIGNATOR'] for b in blocks(streams['Components6/Data'])]
data=streams['Pads6/Data'];rows=[];off=0;count=0
while off<len(data):
    assert data[off]==2;off+=1;bs=[]
    for _ in range(6):n=struct.unpack_from('<I',data,off)[0];off+=4;bs.append(data[off:off+n]);off+=n
    raw=bytearray(bs[4]);ref=refs[struct.unpack_from('<H',raw,7)[0]]
    if ref in MOUNTS:
        assert raw[102]==2 and struct.unpack_from('<i',raw,90)[0]==unit(1.4125)
        struct.pack_into('<i',raw,90,unit(2.2125));count+=1
    bs[4]=bytes(raw);rows.append(bytes([2])+b''.join(block(b) for b in bs))
assert count==4;updates['Pads6/Data']=b''.join(rows)
for name in ['Regions6','ShapeBasedRegions6']:
    rows=[]
    for raw in records(streams[name+'/Data'],11):
        if raw[0]==38:
            n=struct.unpack_from('<I',raw,18)[0];q=parse(raw[22:22+n]);assert q['NAME'].startswith('BOTTOM_GND_EXPOSURE_');continue
        rows.append(rec(11,raw))
    # Altium creates the plain Regions6 cache when saving this source stream.
    if name=='ShapeBasedRegions6':
        for i,f in enumerate(intent['bottom_mask_regions']):
            h=bytearray(18);h[0]=38;h[1]=12;struct.pack_into('<5H',h,3,65535,65535,65535,65535,65535);struct.pack_into('<H',h,14,len(f['holes']))
            p=dict(V7_LAYER='BOTTOMSOLDER',NAME='BOTTOM_GND_EXPOSURE_'+str(i),KIND=0,SUBPOLYINDEX=65535,UNIONINDEX=0,ARCRESOLUTION=mil(.02),ISSHAPEBASED='TRUE',ISBOARDCUTOUT='FALSE')
            raw=bytes(h)+props(p)+struct.pack('<I',len(f['outline']))
            raw+=b''.join(struct.pack('<B5i2d',0,*point(v),0,0,0,0.,0.) for v in f['outline']+[f['outline'][0]])
            for hole in f['holes']:raw+=struct.pack('<I',len(hole))+b''.join(struct.pack('<2d',*point(v)) for v in hole)
            rows.append(rec(11,raw))
    put(updates,name,rows);changed[name]=len(rows)
reindex(streams,updates,changed);update_copy(pcb,S/'candidate.PcbDoc',updates)
print('7.6 mm mounting openings; bottom mask',len(pieces),'regions;',len(intent['removed_top_pad_projections']),'top-only pad projections removed; area',desired.area)
