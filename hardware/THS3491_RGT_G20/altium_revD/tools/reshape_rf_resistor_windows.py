"""L2: remove amplifier-pad windows and open each RF resistor's pad-to-pad gap."""
from pathlib import Path
import hashlib,json,shutil,struct,uuid
import olefile
from shapely.geometry import Polygon,box,Point
from shapely.affinity import rotate
from shapely.ops import unary_union
from native_update import ROOT,records,rec,props,parse,point,mil,update_copy
R=ROOT/'review';B=R/'rf_resistor_windows_baseline';S=ROOT/'staging/rf_resistor_windows_20261030'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def pad_polygon(p):
    x,y=p['pos'];w,h=p['size']
    return rotate(box(x-w/2,y-h/2,x+w/2,y+h/2),-p['angle'],origin=(x,y))

def build():
    pcb=ROOT/'QSTL_THS3491_RGT_G20_RevD.PcbDoc';sch=pcb.with_suffix('.SchDoc')
    g=json.loads((R/'native_geometry.json').read_text());digest=sha(pcb)
    prior=json.loads((R/'validation_summary.json').read_text())
    assert digest==prior['sha256'][pcb.name]==json.loads((R/'native_import_check.json').read_text())['source_sha256'] and all(prior['checks'].values())
    old=[z for z in g['zones'] if z['layer']=='In1.Cu' and z['keepout']]
    assert len(old)==18 and all(z['name'].startswith('L2_RF_PAD_') for z in old)
    refs=sorted({z['name'].split('_')[3] for z in old if not z['name'].startswith('L2_RF_PAD_U1_')})
    assert set(refs)=={'R1','R2','R3','R4','R5','R6','R7','R14'}
    new=[];specs=[]
    for ref in refs:
        pads=[p for p in g['pads'] if p['ref']==ref];assert len(pads)==2
        rects=[pad_polygon(p) for p in pads]
        bounds=unary_union(rects).bounds;x0,y0,x1,y1=bounds
        # One continuous resistor-body window; retain the original 0.10 mm
        # pad margin. Grounded pads and their return vias stay on L2 GND.
        bounds=[x0-.1,y0-.1,x1+.1,y1+.1]
        axis=0 if abs(pads[0]['pos'][0]-pads[1]['pos'][0])>abs(pads[0]['pos'][1]-pads[1]['pos'][1]) else 1
        grounded=[p for p in pads if p['net']=='GND']
        if grounded:
            assert len(grounded)==1
            gp=grounded[0];sp=next(p for p in pads if p['net']!='GND');gb=pad_polygon(gp).bounds
            if gp['pos'][axis]<sp['pos'][axis]:bounds[axis]=gb[axis+2]
            else:bounds[axis+2]=gb[axis]
        poly=box(*bounds);outline=[[round(x,8),round(y,8)] for x,y in list(poly.exterior.coords)[:-1]]
        z=dict(name='L2_RF_RESISTOR_'+ref,net='',layer='In1.Cu',priority=0,keepout=True,outline=outline)
        new.append(z);specs.append(dict(ref=ref,outline=outline,grounded_pads=[p['num'] for p in grounded]))
    total=unary_union([Polygon(z['outline']) for z in new])
    assert all(total.disjoint(pad_polygon(p)) for p in g['pads'] if p['ref']=='U1')
    # A copper void has no opposing net; preserve the entire GND via land,
    # rather than applying the power-plane clearance rule to this empty area.
    assert all(total.distance(Point(v['pos']))>=v['diameter']/2 for v in g['vias'] if v['net']=='GND')
    S.mkdir(exist_ok=False);B.mkdir(exist_ok=False);(B/'review_before').mkdir()
    shutil.copy2(pcb,B/'before.PcbDoc');shutil.copy2(sch,B/'before.SchDoc')
    for f in ['native_geometry.json','native_import_copper.json','native_import_cutouts.json','validation_summary.json','l3_cleanup_check.json','component_3d_check.json']:
        shutil.copy2(R/f,B/'review_before'/f)
    (B/'README.md').write_text('Historical verified baseline before the RF resistor-window/U1 correction on 2026-10-30.\n')
    intent=dict(request='No L2 window under the amplifier pads. RF resistor pad-to-pad gaps must be open; inter-component traces retain L2 GND.',baseline_pcb_sha256=digest,baseline_schematic_sha256=sha(sch),removed_U1_pad_windows=5,replaced_resistor_pad_windows=13,new_resistor_windows=specs,pad_margin_mm=.1,ground_pad_policy='Open the entire gap up to the inner edge of the grounded pad; retain copper beneath the GND pad and its via.',preserved=['all L1/L3/L4 copper','parts/pads/tracks/arcs/vias','all L3 supply shapes','three L1 clearances','bottom mask','schematic','26 embedded models'])
    (ROOT/'rf_resistor_windows_intent.json').write_text(json.dumps(intent,indent=2)+'\n')
    g['zones']=[z for z in g['zones'] if z not in old]+new
    (S/'geometry.json').write_text(json.dumps(g,indent=2)+'\n')
    with olefile.OleFileIO(pcb) as o:streams={'/'.join(k):o.openstream(k).read() for k in o.listdir()}
    updates={};counts={}
    for key in ['Regions6','ShapeBasedRegions6']:
        rows=[];removed=[]
        for raw in records(streams[key+'/Data'],11):
            size=struct.unpack_from('<I',raw,18)[0];q=parse(raw[22:22+size])
            if raw[0]==2 and q.get('KIND')=='1':removed.append(q['NAME']);continue
            rows.append(rec(11,raw))
        assert len(removed)==18 and set(removed)=={z['name'] for z in old}
        for z in new:
            h=bytearray(18);h[0]=2;h[1]=12;struct.pack_into('<HHHHH',h,3,65535,65535,65535,65535,65535)
            d=dict(V7_LAYER='MID1',NAME=z['name'],KIND=1,SUBPOLYINDEX=65535,UNIONINDEX=0,ARCRESOLUTION=mil(.02),ISSHAPEBASED='TRUE',ISBOARDCUTOUT='FALSE')
            prefix=bytes(h)+props(d)+struct.pack('<I',len(z['outline']))
            if key=='Regions6':raw=prefix+b''.join(struct.pack('<2d',*point(p)) for p in z['outline'])
            else:raw=prefix+b''.join(struct.pack('<B5i2d',0,*point(p),0,0,0,0.,0.) for p in z['outline']+[z['outline'][0]])
            rows.append(rec(11,raw))
        updates[key+'/Data']=b''.join(rows);updates[key+'/Header']=struct.pack('<I',len(rows));counts[key]=len(rows)
    ids=streams['PrimitiveGuids/Data'];rows=[ids[i:i+24] for i in range(0,len(ids),24) if struct.unpack_from('<I',ids,i)[0] not in [4953,5209]]
    for tag,key in [(4953,'Regions6'),(5209,'ShapeBasedRegions6')]:
        rows += [struct.pack('<II',tag,i)+uuid.uuid5(uuid.NAMESPACE_URL,f'qstl/resistor-windows/{tag}/{i}').bytes_le for i in range(counts[key])]
    updates['PrimitiveGuids/Data']=b''.join(rows);updates['PrimitiveGuids/Header']=struct.pack('<I',len(rows))
    update_copy(pcb,S/'outline.PcbDoc',updates)
    print('L2: removed 5 U1 windows; combined 13 resistor-pad windows into 8 resistor-body windows')

if __name__=='__main__':build()
