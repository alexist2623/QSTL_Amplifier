"""Refill native-imported hardware, retaining original RF and polygon definitions."""
from pathlib import Path
import json
import argparse
import pcbnew as p
import wx
ROOT=Path(__file__).resolve().parents[1];S=ROOT/'staging/dc_inputs_20261028';R=ROOT/'review'
parser=argparse.ArgumentParser();parser.add_argument('--geometry',type=Path,default=S/'geometry.json');parser.add_argument('--output-dir',type=Path,default=S);args=parser.parse_args()
S=args.output_dir
app=wx.App(False);log=wx.LogStderr()
g=json.loads(args.geometry.read_text())
b=p.LoadBoard(str(ROOT/'staging/native_roundtrip.kicad_pcb'))
fps={f.GetReference():f for f in b.GetFootprints()}
assert set(fps)=={f['ref'] for f in g['parts']}
def xy(v):return [p.ToMM(v.x),p.ToMM(v.y)]
offset=[xy(fps['U1'].GetPosition())[i]-[18.79601,27.94][i] for i in range(2)]
b.Move(p.wxPoint(p.FromMM(-offset[0]),p.FromMM(-offset[1])))
for layer,name in [(p.F_Cu,'F.Cu'),(p.In1_Cu,'In1.Cu'),(p.In2_Cu,'In2.Cu'),(p.B_Cu,'B.Cu')]:b.SetLayerName(layer,name)
for z in list(b.Zones()):b.Remove(z)
layers={'F.Cu':p.F_Cu,'In1.Cu':p.In1_Cu,'In2.Cu':p.In2_Cu,'B.Cu':p.B_Cu}
pairs=[]
for d in g['zones']:
 z=p.ZONE(b);z.SetLayer(layers[d['layer']]);z.SetZoneName(d['name']);z.SetPriority(d.get('priority',0))
 z.SetLocalClearance(p.FromMM(.205));z.SetMinThickness(p.FromMM(.1));z.SetThermalReliefGap(p.FromMM(.2));z.SetThermalReliefSpokeWidth(p.FromMM(.25))
 z.SetPadConnection(p.ZONE_CONNECTION_THERMAL if d['layer']=='F.Cu' else p.ZONE_CONNECTION_FULL)
 if d['keepout']:
  z.SetIsRuleArea(True);z.SetDoNotAllowCopperPour(True);z.SetDoNotAllowTracks(False);z.SetDoNotAllowVias(False);z.SetDoNotAllowPads(False);z.SetDoNotAllowFootprints(False)
 else:z.SetNet(b.FindNet(d['net']))
 z.Outline().NewOutline()
 for x,y in d['outline']:z.Outline().Append(p.FromMM(x),p.FromMM(y))
 b.Add(z);pairs.append((z,d))
for f in b.GetFootprints():
 f.Reference().SetVisible(False);f.Value().SetVisible(False)
 for q in f.Pads():
  solid=f.GetReference() in ['U1','H9'] or (f.GetReference() in ['C3','C4','C5','C6'] and q.GetNetname()=='GND')
  q.SetZoneConnection(p.ZONE_CONNECTION_FULL if solid else p.ZONE_CONNECTION_THERMAL)
  q.SetThermalGap(p.FromMM(.2));q.SetThermalSpokeWidth(p.FromMM(.25))
ds=b.GetDesignSettings()
for n,v in [('m_MinClearance',.15),('m_TrackMinWidth',.15),('m_ViasMinSize',.4),('m_ViasMinAnnularWidth',.1),('m_MinThroughDrill',.2),('m_HoleToHoleMin',.25),('m_CopperEdgeClearance',.25)]:setattr(ds,n,p.FromMM(v))
b.BuildConnectivity();filler=p.ZONE_FILLER(b);assert filler.Fill(b.Zones())
def loop(c):return [xy(c.CPoint(i)) for i in range(c.PointCount())]
for z,d in pairs:
 d['filled']=[]
 if d['keepout']:continue
 poly=z.GetFilledPolysList(z.GetLayer())
 for i in range(poly.OutlineCount()):d['filled'].append(dict(outline=loop(poly.Outline(i)),holes=[loop(poly.Hole(i,j)) for j in range(poly.HoleCount(i))]))
(R/'native_geometry.json').write_text(json.dumps(g,indent=2))
(R/'intended_geometry.json').write_text((S/'geometry.json').read_text())
p.SaveBoard(str(S/'filled.kicad_pcb'),b)
assert p.WriteDRCReport(b,str(R/'geometry_drc.txt'),p.EDA_UNITS_MILLIMETRES,True)
print('Filled native hardware; geometry_drc.txt written')
