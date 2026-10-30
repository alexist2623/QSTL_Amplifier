"""Read mounting-pad solder-mask openings using the independent KiCad importer."""
from pathlib import Path
import json
import pcbnew as p
ROOT=Path(__file__).resolve().parents[1];source=ROOT/'staging/native_roundtrip.kicad_pcb'
meta=json.loads(source.with_suffix('.import.json').read_text());board=p.LoadBoard(str(source));rows=[]
for f in board.GetFootprints():
    if f.GetReference() not in ['H1','H2','H3','H4']:continue
    for pad in f.Pads():
        m=p.ToMM(pad.GetLocalSolderMaskMargin())
        rows.append(dict(ref=f.GetReference(),mask_expansion_mm=m,opening_diameter_mm=p.ToMM(pad.GetSize().x)+2*m,top_mask=pad.IsOnLayer(p.F_Mask),bottom_mask=pad.IsOnLayer(p.B_Mask)))
diameter=7.6 if (ROOT/'bottom_mask_cleanup_intent.json').exists() else 6.0
assert len(rows)==4 and all(abs(r['opening_diameter_mm']-diameter)<.00001 and r['top_mask'] and r['bottom_mask'] for r in rows)
(ROOT/'review/mount_mask_import_check.json').write_text(json.dumps(dict(pcb_sha256=meta['source_sha256'],reader=meta['reader'],holes=rows),indent=2)+'\n')
print('Independent import: all four holes have',diameter,'mm openings on both mask layers')
