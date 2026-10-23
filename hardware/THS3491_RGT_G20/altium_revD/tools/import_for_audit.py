"""Import the complete Altium-saved Rev D with KiCad 6 Python (including text)."""
from pathlib import Path
import hashlib
import json
import pcbnew as p
import wx

ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'QSTL_THS3491_RGT_G20_RevD.PcbDoc'
target=ROOT/'staging/native_roundtrip.kicad_pcb'
app=wx.App(False); log=wx.LogStderr()
board=p.LoadBoard(str(source),p.IO_MGR.ALTIUM_DESIGNER)
assert board
p.SaveBoard(str(target),board)
target.with_suffix('.import.json').write_text(json.dumps(dict(
    source=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    reader=p.GetBuildVersion(),text_stream_excluded=False),indent=2))
print('Imported complete PCB, including Texts6:',len(board.GetFootprints()),'parts')
