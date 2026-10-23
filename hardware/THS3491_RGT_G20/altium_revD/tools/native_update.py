"""Copy and patch Rev C's Altium PCB streams using Windows Structured Storage.

This preserves the original stack, pad metadata, schematic linkage, RF arc
records and manufacturing rules. Geometry is re-read independently for audit.
The helper in Rev C rejects overwriting source or an existing output.
Dependencies: olefile 0.47; Windows. No historical carrier/staging files.
"""
from pathlib import Path
import argparse
import json
import re
import struct
import sys
import uuid

import olefile

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT.parent/'altium_revC'
sys.path.insert(0,str(SOURCE/'tools'))
from cfb_copy_update import update_copy

def block(data): return struct.pack('<I',len(data))+data
def props(d): return block(('|'+'|'.join(k+'='+str(v) for k,v in d.items())+'\0').encode('cp1252'))
def parse(data): return dict(s.split('=',1) for s in data.rstrip(b'\0').decode('cp1252').split('|') if '=' in s)
def blocks(data):
    offset=0
    while offset<len(data):
        size=struct.unpack_from('<I',data,offset)[0]; offset+=4
        assert offset+size<=len(data)
        yield data[offset:offset+size]; offset+=size
    assert offset==len(data)
def records(data,kind):
    offset=0
    while offset<len(data):
        assert data[offset]==kind,(offset,data[offset],kind)
        size=struct.unpack_from('<I',data,offset+1)[0]
        yield data[offset+5:offset+5+size]; offset+=5+size
    assert offset==len(data)
def rec(kind,data): return bytes([kind])+block(data)
def unit(mm): return round(mm/2.54e-6)
def mil(mm): return f'{mm/.0254:.8f}mil'
def point(pos): return unit(pos[0]),unit(68.58-pos[1])
LAY={'F.Cu':1,'In1.Cu':2,'In2.Cu':3,'B.Cu':32}
LNAME={1:'TOP',2:'MID1',3:'MID2',32:'BOTTOM'}
# Verified against native AD example documents. Modern readers use these
# extended IDs even when the legacy byte at offset 0 is correct.
LAYER_V7={1:0x01000001,2:0x01000002,3:0x01000003,32:0x0100ffff,
          33:0x01030006,34:0x01030007,35:0x01030008,36:0x01030009,
          37:0x0103000a,38:0x0103000b,57:0x01020001,58:0x01020002,
          74:0x0103000f}

def fix_track_layer(data):
    raw=bytearray(data)
    assert len(raw)>=45
    # Offset 40 is the flag preceding the uint32 layer at 41. The original
    # writer put the uint32 at 40, yielding 0x01010000 (InternalPlaneLayer(0)).
    raw[40]=0
    struct.pack_into('<I',raw,41,LAYER_V7[raw[0]])
    return raw

def import_copy(source,target):
    return update_copy(source,target,{'Texts6/Data':b'','Texts6/Header':struct.pack('<I',0)})

def build(destination):
    g=json.loads((ROOT/'review/native_geometry.json').read_text())
    # C7 VCC is an inherited pad/via direct connection; its tiny thermal
    # polygon was already empty in Rev C. Every other supply/ground zone fills.
    assert all(z['filled'] for z in g['zones'] if not z['keepout'] and z['name']!='L1_C7_VCC')
    with olefile.OleFileIO(SOURCE/'QSTL_THS3491_RGT_G20_RevC.PcbDoc') as ole:
        streams={'/'.join(p):ole.openstream(p).read() for p in ole.listdir()}
    updates={}; counts={}
    def put(name,rows):
        counts[name]=len(rows); updates[name+'/Data']=b''.join(rows)
        updates[name+'/Header']=struct.pack('<I',len(rows))
    board=parse(next(blocks(streams['Board6/Data'])))
    before_board=dict(board)
    # The carrier retained a contradictory two-layer flex V8 stack even though
    # Rev C added a rigid four-layer V9 stack. Make both serializations agree.
    old_aux={}
    for key,value in board.items():
        match=re.fullmatch(r'LAYER_V8_(\d+)(.*)',key)
        if match: old_aux.setdefault(int(match[1]),{})[match[2]]=value
    for key in list(board):
        if key.startswith(('LAYER_V8_','LAYERMASTERSTACK_V8','LAYERSUBSTACK_V8')):
            del board[key]
        # Fixed legacy layer slots must remain present for older readers.
        # They are not part of the active chain and have no assigned net.
    board['LAYERSTACKSTYLE']='0'
    board['FILENAME']='QSTL_THS3491_RGT_G20_RevD.PcbDoc'
    for suffix in ['STYLE','ID','NAME','SHOWTOPDIELECTRIC','SHOWBOTTOMDIELECTRIC','ISFLEX']:
        board['LAYERMASTERSTACK_V8'+suffix]=board['V9_MASTERSTACK_'+suffix]
    for suffix in ['ID','NAME','ISFLEX','SERVICE','USEDBYPRIMS','TYPE']:
        board['LAYERSUBSTACK_V8_0'+suffix]=board['V9_SUBSTACK0_'+suffix]
    board['LAYERSUBSTACK_V8_0SHOWTOPDIELECTRIC']='TRUE'
    board['LAYERSUBSTACK_V8_0SHOWBOTTOMDIELECTRIC']='TRUE'
    v9={}
    for key,value in board.items():
        match=re.fullmatch(r'V9_STACK_LAYER(\d+)_(.*)',key)
        if match: v9.setdefault(int(match[1]),{})[match[2]]=value
    stackids={d['LAYERID'] for d in v9.values()}
    entries=[v9[i] for i in sorted(v9)]
    entries += [{k:v for k,v in d.items() if not k.startswith('_')}
                for _,d in sorted(old_aux.items())
                if int(d.get('LAYERID','0'))>=16908289 and d.get('LAYERID') not in stackids
                and not 17039361<=int(d.get('LAYERID','0'))<=17104895]
    for i,d in enumerate(entries):
        for key,value in d.items():
            board[f'LAYER_V8_{i}'+('_' if key.startswith('{') else '')+key]=value
    for i in [0,1,2]:
        key=f'LAYERSET{i}LAYERS'
        if key in board:
            board[key]=board[key].replace('TopLayer,BottomLayer','TopLayer,MidLayer1,MidLayer2,BottomLayer')
    put('Board6',[props(board)])
    # Board region continues to reference the same valid rigid V9 substack.
    updates['BoardRegions/Data']=streams['BoardRegions/Data'].replace(b'QSTL Rev C rigid board',b'QSTL Rev D rigid board')
    compatibility=dict(
        old_v8_stack_name=before_board.get('LAYERMASTERSTACK_V8NAME'),
        old_v8_is_flex=before_board.get('LAYERMASTERSTACK_V8ISFLEX'),
        corrected_v8_stack_name=board['LAYERMASTERSTACK_V8NAME'],
        corrected_v8_is_flex=board['LAYERMASTERSTACK_V8ISFLEX'],
        inactive_negative_plane_slots_preserved_for_legacy_readers=list(range(1,17)),
        active_copper_layers=[d['NAME'] for d in v9.values() if int(d['LAYERID']) in [16777217,16777218,16777219,16842751]],
        physical_copper_layer_ids_unchanged=True,
        version_conversion_dialog_resolved=False,
        altium_ui_verification=False)
    (ROOT/'review/layer_metadata_repair.json').write_text(json.dumps(compatibility,indent=2))
    netid={parse(d)['NAME']:i for i,d in enumerate(blocks(streams['Nets6/Data']))}
    comps=[parse(d) for d in blocks(streams['Components6/Data'])]
    parts={d['ref']:d for d in g['parts']}
    refs={i:d['SOURCEDESIGNATOR'] for i,d in enumerate(comps)}
    moved=set(json.loads((ROOT/'review/change_manifest.json').read_text())['moves'])
    for d in comps:
        ref=d['SOURCEDESIGNATOR']; f=parts[ref]
        d['SOURCEHIERARCHICALPATH']='QSTL_THS3491_RGT_G20_RevD'
        if ref in moved:
            d.update(X=mil(f['pos'][0]),Y=mil(68.58-f['pos'][1]),ROTATION=f['angle'])
    put('Components6',[props(d) for d in comps])
    pads={(q['ref'],q['num']):q for q in g['pads']}
    data=streams['Pads6/Data']; off=0; rows=[]
    while off<len(data):
        start=off; assert data[off]==2; off+=1; bs=[]
        for _ in range(6):
            n=struct.unpack_from('<I',data,off)[0]; off+=4
            bs.append(data[off:off+n]); off+=n
        raw=bytearray(bs[4]); ci=struct.unpack_from('<H',raw,7)[0]
        ref=refs[ci]; num=bs[0][1:1+bs[0][0]].decode('ascii')
        if ref in moved:
            q=pads[ref,num]; struct.pack_into('<2i',raw,13,*point(q['pos']))
            struct.pack_into('<d',raw,52,q['angle'])
        assert len(raw)>=118
        struct.pack_into('<I',raw,114,LAYER_V7[raw[0]])
        if ref in {'R14','R15','U1'}:
            assert pads[ref,num]['shape']==1
            raw[49:52]=bytes([2,2,2])  # Top/mid/bottom rectangular pad shape.
            bs[5]=b''  # Discard inherited round-rectangle extension.
        bs[4]=bytes(raw)
        rows.append(bytes([2])+b''.join(block(v) for v in bs))
    put('Pads6',rows)

    # Preserve RF geometry and nets, while repairing every track's extended
    # layer field. Replace only TJ_RAW geometry; append its escape and PD16.
    orig_tracks=list(records(streams['Tracks6/Data'],4))
    tracks=[rec(4,fix_track_layer(d)) for d in orig_tracks if struct.unpack_from('<H',d,3)[0]!=netid['TJ_RAW']]
    for t in g['tracks']:
        if t['net'] not in ['TJ_RAW','VCC']: continue
        raw=bytearray(orig_tracks[0]); raw[0]=1; raw[1]=12; raw[2]=0
        struct.pack_into('<HHHHH',raw,3,netid[t['net']],65535,65535,65535,65535)
        struct.pack_into('<5i',raw,13,*point(t['start']),*point(t['end']),unit(t['width']))
        struct.pack_into('<H',raw,33,65535)
        tracks.append(rec(4,fix_track_layer(raw)))
    put('Tracks6',tracks)
    sample=next(records(streams['Vias6/Data'],3)); rows=[]
    for v in g['vias']:
        raw=bytearray(sample); raw[0]=74; raw[1]=108; raw[2]=0
        struct.pack_into('<HHHHH',raw,3,netid[v['net']],65535,65535,65535,65535)
        struct.pack_into('<4i',raw,13,*point(v['pos']),unit(v['diameter']),unit(v['drill']))
        raw[29]=1; raw[30]=32; raw[74]=0
        for offset in range(75,203,4): struct.pack_into('<i',raw,offset,unit(v['diameter']))
        rows.append(rec(3,raw))
    put('Vias6',rows)

    # Component labels follow relocated components. Keep all remaining text
    # attributes and positions, updating only the printed revision label.
    data=streams['Texts6/Data']; off=0; rows=[]
    while off<len(data):
        assert data[off]==5; off+=1
        n=struct.unpack_from('<I',data,off)[0]; off+=4
        raw=bytearray(data[off:off+n]); off+=n
        n=struct.unpack_from('<I',data,off)[0]; off+=4
        txt=data[off:off+n]; off+=n
        ci=struct.unpack_from('<H',raw,7)[0]
        if refs.get(ci) in moved:
            f=parts[refs[ci]]
            struct.pack_into('<2i',raw,13,*point([f['pos'][0]-.7,f['pos'][1]-1.7]))
        if b'REV C' in txt: txt=txt.replace(b'REV C',b'REV D')
        rows.append(rec(5,raw)+block(txt))
    put('Texts6',rows)

    def vertices(d,ps):
        for i,(x,y) in enumerate(ps+[ps[0]]):
            d.update({f'KIND{i}':0,f'VX{i}':mil(x),f'VY{i}':mil(68.58-y),
                      f'CX{i}':'0mil',f'CY{i}':'0mil',f'SA{i}':0,f'EA{i}':0,f'R{i}':'0mil'})
    polys=[]; regions=[]
    for z in sorted(g['zones'],key=lambda z:-z.get('priority',0)):
        if z['keepout']: continue
        layer=LAY[z['layer']]; i=len(polys)
        d=dict(SELECTION='FALSE',LAYER=LNAME[layer],NET=netid[z['net']],PRIMITIVELOCK='TRUE',
               POLYGONTYPE='Polygon',POUROVER='TRUE',REMOVEDEAD='TRUE',GRIDSIZE=mil(.05),
               TRACKWIDTH=mil(.15),HATCHSTYLE='Solid',USEOCTAGONS='FALSE',MINPRIMLENGTH=mil(.025),
               SHELVED='FALSE',RESTORELAYER='UNKNOWN',RESTORENET='',REMOVEISLANDSBYAREA='TRUE',
               REMOVENECKS='TRUE',AREATHRESHOLD='0',ARCRESOLUTION=mil(.02),
               NECKWIDTHTHRESHOLD=mil(.15),POUROVERSTYLE=1,
               NAME=','.join(str(ord(c)) for c in z['name']),POURINDEX=i+1,IGNOREVIOLATIONS='FALSE')
        vertices(d,z['outline']); polys.append(props(d))
        for f in z['filled']:
            hdr=bytearray(18); hdr[0]=layer; hdr[1]=12
            struct.pack_into('<HHHHH',hdr,3,netid[z['net']],i,65535,65535,65535)
            struct.pack_into('<H',hdr,14,len(f['holes']))
            d=dict(V7_LAYER=LNAME[layer],NAME=z['name'],KIND=0,SUBPOLYINDEX=0,
                   UNIONINDEX=0,ARCRESOLUTION=mil(.02),ISSHAPEBASED='FALSE',ISBOARDCUTOUT='FALSE')
            data=bytes(hdr)+props(d)+struct.pack('<I',len(f['outline']))
            data+=b''.join(struct.pack('<2d',*point(v)) for v in f['outline'])
            for hole in f['holes']:
                data+=struct.pack('<I',len(hole))+b''.join(struct.pack('<2d',*point(v)) for v in hole)
            regions.append(rec(11,data))
    put('Polygons6',polys); put('Regions6',regions)

    # Persistent layer-specific polygon cutouts, in addition to the baked fill.
    # Preserve all original cutouts, stencil apertures, and heatsink mask shapes.
    shapes=[rec(11,d) for d in records(streams['ShapeBasedRegions6/Data'],11)]
    for z in g['zones']:
        if not z['name'].startswith('L2_RF_PAD_'): continue
        layer=LAY[z['layer']]
        hdr=bytearray(18); hdr[0]=layer; hdr[1]=12
        struct.pack_into('<HHHHH',hdr,3,65535,65535,65535,65535,65535)
        d=dict(V7_LAYER=LNAME[layer],NAME=z['name'],KIND=1,SUBPOLYINDEX=65535,
               UNIONINDEX=0,ARCRESOLUTION=mil(.02),ISSHAPEBASED='TRUE',ISBOARDCUTOUT='FALSE')
        data=bytes(hdr)+props(d)+struct.pack('<I',len(z['outline']))
        for pos in z['outline']+[z['outline'][0]]:
            data+=struct.pack('<B5i2d',0,*point(pos),0,0,0,0.,0.)
        shapes.append(rec(11,data))
    put('ShapeBasedRegions6',shapes)

    # Replace primitive IDs only for streams whose indexed records changed.
    tags={'Components6':777,'Polygons6':1034,'Pads6':3586,'Vias6':3843,
          'Tracks6':4100,'Texts6':4357,'Regions6':4953,'ShapeBasedRegions6':5209}
    oldids=streams['PrimitiveGuids/Data']; ids=[]
    assert len(oldids)%24==0
    for i in range(0,len(oldids),24):
        row=oldids[i:i+24]
        if struct.unpack_from('<I',row)[0] not in tags.values(): ids.append(row)
    for name,tag in tags.items():
        for i in range(counts[name]):
            ids.append(struct.pack('<II',tag,i)+uuid.uuid5(uuid.NAMESPACE_URL,f'qstl/revd/{name}/{i}').bytes_le)
    put('PrimitiveGuids',ids)
    report=update_copy(SOURCE/'QSTL_THS3491_RGT_G20_RevC.PcbDoc',destination,updates)
    report['counts']=counts
    report['altium_application_roundtrip']=False
    report['preserved_streams_of_interest']=['Nets6','Rules6','Arcs6']
    report['preserved_original_shape_regions']=len(shapes)-19
    report['added_L2_RF_pad_cutouts']=19
    (ROOT/'review/native_file_build.json').write_text(json.dumps(report,indent=2))
    print('Saved',destination)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit-source',type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    if args.audit_source:
        report=import_copy(args.audit_source,args.output)
        args.output.with_suffix('.audit.json').write_text(json.dumps(report,indent=2))
    else: build(args.output)
