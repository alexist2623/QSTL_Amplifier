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
g=json.loads((R/'native_geometry.json').read_text())
pad_count=len(g['pads']);top_count=sum('F.Cu' in p['layers'] and 'B.Cu' not in p['layers'] for p in g['pads'])
bottom_count=sum('B.Cu' in p['layers'] and 'F.Cu' not in p['layers'] for p in g['pads'])
multi_count=pad_count-top_count-bottom_count
mechanical_count=json.loads((ROOT/'dc_inputs_intent.json').read_text())['mechanical_outline_tracks']
track_count=len(g['tracks'])+mechanical_count
rectangle_count=sum(p['ref'] in {'R14','R15','U1'} for p in g['pads'])
assert log.stat().st_mtime>=pcb.stat().st_mtime, 'Native log predates current PCB'
required=['Document opened','Board available','Pads='+str(pad_count),'TopPads='+str(top_count),
          'BottomPads='+str(bottom_count),'MultiPads='+str(multi_count),'OtherPads=0','Tracks='+str(track_count),
          'Native save succeeded','Closed saved document','Native reopen succeeded']
required+=['Verified='+str(rectangle_count),'Failures=0']
via_count=len(json.loads((R/'native_geometry.json').read_text())['vias'])
required+=['Vias='+str(via_count)]
assert all(line in lines for line in required)
pad_rows=[s for s in lines if s.startswith('PAD,')]
assert len(pad_rows)==rectangle_count and all(re.search(r',shape=2,.*?,radius=0$',s) for s in pad_rows)
encoding=check(pcb)
assert not encoding['errors'] and encoding['version_info_bytes']>0
assert not pcb.with_suffix('.PcbDoc.htm').exists(), 'Review new conversion report before accepting'
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
report=dict(open_save_reopen_passed=True,pcb_sha256=sha(pcb),log_sha256=sha(log),
            script_sha256=sha(R/'native_shape_repair/ShapeRepair.pas'),
            application='Altium Designer Professional 25.8.1',
            native_pad_counts=dict(top=top_count,bottom=bottom_count,multilayer=multi_count,total=pad_count),
            native_tracks=track_count,signal_tracks=len(g['tracks']),mechanical_outline_tracks=mechanical_count,
            native_vias=via_count,
            new_version_conversion_report=False,layer_encoding=encoding,
            native_rectangles_verified=rectangle_count,native_corner_radius_mm=0,native_shape_failures=0,
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
