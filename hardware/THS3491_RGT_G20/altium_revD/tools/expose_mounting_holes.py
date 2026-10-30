"""Expose the existing GND annulus around H1-H4 using their native pad mask settings."""
import hashlib,json,shutil,struct
import olefile
from native_update import ROOT,blocks,block,parse,unit,update_copy
R=ROOT/'review';B=R/'mount_mask_baseline';S=ROOT/'staging/mount_mask_20261030'
pcb=ROOT/'QSTL_THS3491_RGT_G20_RevD.PcbDoc';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
g=json.loads((R/'native_geometry.json').read_text());baseline=json.loads((R/'validation_summary.json').read_text())
assert sha(pcb)==baseline['sha256'][pcb.name] and all(baseline['checks'].values())
B.mkdir(exist_ok=False);S.mkdir(exist_ok=False);(B/'review_before').mkdir()
shutil.copy2(pcb,B/'before.PcbDoc');shutil.copy2(pcb.with_suffix('.SchDoc'),B/'before.SchDoc')
for f in ['native_geometry.json','native_import_copper.json','native_import_cutouts.json','validation_summary.json','rf_resistor_windows_check.json']:
    shutil.copy2(R/f,B/'review_before'/f)
(B/'README.md').write_text('Historical baseline before mounting-hole solder-mask expansion on 2026-10-30.\n')
with olefile.OleFileIO(pcb) as o:
    refs=[parse(b)['SOURCEDESIGNATOR'] for b in blocks(o.openstream('Components6/Data').read())]
    data=o.openstream('Pads6/Data').read()
rows=[];holes=[];off=0
while off<len(data):
    assert data[off]==2;off+=1;bs=[]
    for _ in range(6):n=struct.unpack_from('<I',data,off)[0];off+=4;bs.append(data[off:off+n]);off+=n
    raw=bytearray(bs[4]);ref=refs[struct.unpack_from('<H',raw,7)[0]]
    if ref in ['H1','H2','H3','H4']:
        p=next(p for p in g['pads'] if p['ref']==ref)
        assert p['npth'] and p['size']==[3.175,3.175] and p['drill']==[3.175,3.175]
        assert raw[102]==2 and struct.unpack_from('<i',raw,90)[0]==0
        expansion=(6.0-p['size'][0])/2
        struct.pack_into('<i',raw,90,unit(expansion))
        holes.append(dict(ref=ref,center_mm=p['pos'],drill_diameter_mm=3.175,opening_diameter_mm=6.0,mask_expansion_mm=expansion,layers=['F.Mask','B.Mask'],plated=False))
    bs[4]=bytes(raw);rows.append(bytes([2])+b''.join(block(b) for b in bs))
assert len(holes)==4
intent=dict(request='Expose copper around the mechanical mounting holes.',baseline_pcb_sha256=sha(pcb),baseline_schematic_sha256=sha(pcb.with_suffix('.SchDoc')),holes=holes,opening_basis='6.0 mm nominal screw-head review envelope used by the existing mounting-via design',method='Manual pad solder-mask expansion on both outer sides; existing GND copper is exposed. Hole drilling/plating, all copper and all vias are unchanged.')
(ROOT/'mount_mask_intent.json').write_text(json.dumps(intent,indent=2)+'\n')
update_copy(pcb,S/'candidate.PcbDoc',{'Pads6/Data':b''.join(rows)})
print('H1-H4: 6.0 mm top and bottom mask openings; 1.4125 mm manual expansion')
