"""KiCad 6.0.10 geometry audit; never an Altium application DRC.

Requires an audit import of Rev C without Texts6, because the KiCad 6 text
parser cannot read Rev C's newer text records. The native deliverable retains
all its texts. No native copper is removed for the audit.
"""
from pathlib import Path
import json
import math
import pcbnew as p
import wx

ROOT=Path(__file__).resolve().parents[1]
S=ROOT/'staging'; S.mkdir(exist_ok=True)
app=wx.App(False); log=wx.LogStderr()
g=json.loads((ROOT/'review/intended_geometry.json').read_text())
base=json.loads((ROOT.parent/'altium_revC/review/native_geometry.json').read_text())
b=p.LoadBoard(str(S/'baseline_import.kicad_pcb'))
fps={f.GetReference():f for f in b.GetFootprints()}
def xy(v): return [p.ToMM(v.x),p.ToMM(v.y)]
def vec(x,y): return p.wxPoint(p.FromMM(x),p.FromMM(y))
offset=[xy(fps['U1'].GetPosition())[i]-[18.79601,27.94][i] for i in range(2)]
b.Move(vec(-offset[0],-offset[1]))
for layer,name in [(p.F_Cu,'F.Cu'),(p.In1_Cu,'In1.Cu'),(p.In2_Cu,'In2.Cu'),(p.B_Cu,'B.Cu')]:
    b.SetLayerName(layer,name)
for f in b.GetFootprints():
    f.Reference().SetVisible(False); f.Value().SetVisible(False)
for f in g['parts']:
    fps[f['ref']].SetPosition(vec(*f['pos']))
    fps[f['ref']].SetOrientationDegrees(f['angle'])

# Check import fidelity before editing tracks/zones. Tolerance covers the
# 2.54-nm Altium coordinate quantization, not a placement discrepancy.
actual={(f.GetReference(),q.GetNumber()):q for f in b.GetFootprints() for q in f.Pads()}
for q in g['pads']:
    if not any(l.endswith('.Cu') for l in q['layers']): continue
    a=actual[q['ref'],q['num']]
    assert math.dist(xy(a.GetPosition()),q['pos'])<.00002,(q['ref'],q['num'],xy(a.GetPosition()),q['pos'])
    assert a.GetNetname()==q['net'],(q['ref'],q['num'])
    if q['ref'] in {'R14','R15','U1'}:
        assert q['shape']==1 and q['roundrect_ratio']==0
        a.SetShape(p.PAD_SHAPE_RECT)
        a.SetRoundRectRadiusRatio(0)

nets={n:b.FindNet(n) for n in set(q['net'] for q in g['pads'] if q['net'])}
for t in list(b.GetTracks()):
    if isinstance(t,p.PCB_VIA) or (not isinstance(t,p.PCB_ARC) and t.GetNetname()=='TJ_RAW'):
        b.Remove(t)
for v in g['vias']:
    q=p.PCB_VIA(b); q.SetPosition(vec(*v['pos'])); q.SetWidth(p.FromMM(v['diameter']))
    q.SetDrill(p.FromMM(v['drill'])); q.SetViaType(p.VIATYPE_THROUGH)
    q.SetLayerPair(p.F_Cu,p.B_Cu); q.SetNet(nets[v['net']]); b.Add(q)
for t in g['tracks']:
    if t['net'] not in ['TJ_RAW','VCC']: continue
    q=p.PCB_TRACK(b); q.SetStart(vec(*t['start'])); q.SetEnd(vec(*t['end']))
    q.SetWidth(p.FromMM(t['width'])); q.SetLayer(p.F_Cu); q.SetNet(nets[t['net']]); b.Add(q)
for z in list(b.Zones()): b.Remove(z)
layers={'F.Cu':p.F_Cu,'In1.Cu':p.In1_Cu,'In2.Cu':p.In2_Cu,'B.Cu':p.B_Cu}
zone_pairs=[]
for d in g['zones']:
    z=p.ZONE(b); z.SetLayer(layers[d['layer']]); z.SetZoneName(d['name'])
    z.SetPriority(d.get('priority',0)); z.SetLocalClearance(p.FromMM(.205))
    z.SetMinThickness(p.FromMM(.10)); z.SetThermalReliefGap(p.FromMM(.20))
    z.SetThermalReliefSpokeWidth(p.FromMM(.25))
    z.SetPadConnection(p.ZONE_CONNECTION_THERMAL if d['layer']=='F.Cu' else p.ZONE_CONNECTION_FULL)
    if d['keepout']:
        z.SetIsRuleArea(True); z.SetDoNotAllowCopperPour(True)
        z.SetDoNotAllowTracks(False); z.SetDoNotAllowVias(False); z.SetDoNotAllowPads(False)
        z.SetDoNotAllowFootprints(False)
    else: z.SetNet(nets[d['net']])
    z.Outline().NewOutline()
    for x,y in d['outline']: z.Outline().Append(p.FromMM(x),p.FromMM(y))
    b.Add(z); zone_pairs.append((z,d))
for f in b.GetFootprints():
    for q in f.Pads():
        solid=f.GetReference() in ['U1','H9'] or (f.GetReference() in ['C3','C4','C5','C6'] and q.GetNetname()=='GND')
        q.SetZoneConnection(p.ZONE_CONNECTION_FULL if solid else p.ZONE_CONNECTION_THERMAL)
        q.SetThermalGap(p.FromMM(.2)); q.SetThermalSpokeWidth(p.FromMM(.25))
ds=b.GetDesignSettings()
for name,value in [('m_MinClearance',.15),('m_TrackMinWidth',.15),('m_ViasMinSize',.4),
                   ('m_ViasMinAnnularWidth',.1),('m_MinThroughDrill',.2),
                   ('m_HoleToHoleMin',.25),('m_CopperEdgeClearance',.25)]:
    setattr(ds,name,p.FromMM(value))
print('Refilling geometry using',p.GetBuildVersion(),flush=True)
b.BuildConnectivity()
filler=p.ZONE_FILLER(b)
assert filler.Fill(b.Zones()), 'Zone fill failed'
def loop(c): return [xy(c.CPoint(i)) for i in range(c.PointCount())]
for z,d in zone_pairs:
    d['filled']=[]
    if d['keepout']: continue
    poly=z.GetFilledPolysList(z.GetLayer())
    for i in range(poly.OutlineCount()):
        d['filled'].append(dict(outline=loop(poly.Outline(i)),
                               holes=[loop(poly.Hole(i,j)) for j in range(poly.HoleCount(i))]))
(ROOT/'review/native_geometry.json').write_text(json.dumps(g,indent=2))
p.SaveBoard(str(S/'geometry_audit.kicad_pcb'),b)
print('Writing DRC report',flush=True)
assert p.WriteDRCReport(b,str(ROOT/'review/geometry_drc.txt'),p.EDA_UNITS_MILLIMETRES,True)
print('Geometry and DRC saved',flush=True)
