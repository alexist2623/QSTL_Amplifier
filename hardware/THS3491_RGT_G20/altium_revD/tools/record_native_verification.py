"""Record an actual successful Altium script run against the delivered file.

Run review/native_shape_repair/ShapeRepair.PrjScr in Altium first. Its .pas contains the
absolute paths for the recorded workstation; adjust those if relocating.
"""
from pathlib import Path
import hashlib
import json
import re
from check_layer_encoding import check

ROOT=Path(__file__).resolve().parents[1]; R=ROOT/'review'
pcb=ROOT/'QSTL_THS3491_RGT_G20_RevD.PcbDoc'
log=R/'altium_native_check.txt'
lines=log.read_text().splitlines()
assert log.stat().st_mtime>=pcb.stat().st_mtime, 'Native log predates current PCB'
required=['Document opened','Board available','Pads=84','TopPads=66',
          'BottomPads=7','MultiPads=11','OtherPads=0','Tracks=42',
          'Native save succeeded','Closed saved document','Native reopen succeeded']
required+=['Verified=21','Failures=0']
via_count=len(json.loads((R/'native_geometry.json').read_text())['vias'])
required+=['Vias='+str(via_count)]
assert all(line in lines for line in required)
pad_rows=[s for s in lines if s.startswith('PAD,')]
assert len(pad_rows)==21 and all(re.search(r',shape=2,.*?,radius=0$',s) for s in pad_rows)
encoding=check(pcb)
assert not encoding['errors'] and encoding['version_info_bytes']>0
assert not pcb.with_suffix('.PcbDoc.htm').exists(), 'Review new conversion report before accepting'
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
report=dict(open_save_reopen_passed=True,pcb_sha256=sha(pcb),log_sha256=sha(log),
            script_sha256=sha(R/'native_shape_repair/ShapeRepair.pas'),
            application='Altium Designer Professional 25.8.1',
            native_pad_counts=dict(top=66,bottom=7,multilayer=11,total=84),
            native_tracks=42,signal_tracks=38,mechanical_outline_tracks=4,
            native_vias=via_count,
            new_version_conversion_report=False,layer_encoding=encoding,
            native_rectangles_verified=21,native_corner_radius_mm=0,native_shape_failures=0,
            screenshot_verified=False,native_ERC_DRC_repoured=False)
(R/'altium_application_check.json').write_text(json.dumps(report,indent=2))
metadata=json.loads((R/'layer_metadata_repair.json').read_text())
metadata['version_conversion_dialog_resolved']=True
metadata['altium_native_open_save_reopen_verified']=True
metadata['root_cause']='Tracks6 extended layer uint32 was at offset 40 instead of 41; pads retained Bottom layer extended ID'
(R/'layer_metadata_repair.json').write_text(json.dumps(metadata,indent=2))
build=json.loads((R/'native_file_build.json').read_text())
build['finalization']=dict(saved_by='Altium Designer 25.8.1',delivered_sha256=sha(pcb),
                          evidence='altium_application_check.json')
(R/'native_file_build.json').write_text(json.dumps(build,indent=2))
print('Recorded native Altium open/save/reopen evidence for',report['pcb_sha256'])
