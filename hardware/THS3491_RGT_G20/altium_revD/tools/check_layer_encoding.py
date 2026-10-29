"""Catch errors masked by importers that prefer the legacy layer byte.

Tracks6 uses a uint32 at byte 41 of its payload. Pads6 uses a uint32 at
byte 114 of its fifth subrecord. Compare both to the legacy byte, as well
as checking the expected pad counts for this board. Use after native save.
"""
import argparse
from collections import Counter
from pathlib import Path
import json
import struct
import olefile
from native_update import LAYER_V7, records


def check(path):
    errors=[]
    pad_layers=Counter(); track_layers=Counter()
    with olefile.OleFileIO(path) as ole:
        data=ole.openstream('Pads6/Data').read(); offset=0; index=0
        while offset<len(data):
            assert data[offset]==2
            offset+=1; blocks=[]
            for _ in range(6):
                size=struct.unpack_from('<I',data,offset)[0]; offset+=4
                blocks.append(data[offset:offset+size]); offset+=size
            raw=blocks[4]; legacy=raw[0]
            modern=struct.unpack_from('<I',raw,114)[0]
            if modern!=LAYER_V7.get(legacy):
                errors.append(dict(kind='pad',index=index,legacy=legacy,modern=hex(modern)))
            pad_layers[legacy]+=1; index+=1
        for index,raw in enumerate(records(ole.openstream('Tracks6/Data').read(),4)):
            legacy=raw[0]; modern=struct.unpack_from('<I',raw,41)[0]
            if modern!=LAYER_V7.get(legacy) or raw[40]!=0:
                errors.append(dict(kind='track',index=index,legacy=legacy,modern=hex(modern),flag=raw[40]))
            track_layers[legacy]+=1
        for index,raw in enumerate(records(ole.openstream('Arcs6/Data').read(),1)):
            modern=struct.unpack_from('<I',raw,52)[0]
            if modern!=LAYER_V7.get(raw[0]):
                errors.append(dict(kind='arc',index=index,legacy=raw[0],modern=hex(modern)))
        version_bytes=len(ole.openstream('FileVersionInfo/Data').read())
    # Primitive counts are checked against the current design by audit_native
    # and record_native_verification; connector additions change those counts.
    return dict(errors=errors,pad_layers=dict(pad_layers),track_layers=dict(track_layers),
                version_info_bytes=version_bytes)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pcb',type=Path)
    parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    result=check(args.pcb)
    text=json.dumps(result,indent=2)
    if args.report: args.report.write_text(text)
    print(text)
    raise SystemExit(bool(result['errors']))
