from pathlib import Path
import json,math,pcbnew as p
H=Path(__file__).resolve().parents[1];S=H/'staging'
b=p.LoadBoard(str(S/'native_roundtrip.kicad_pcb'));source=p.LoadBoard(str(S/'QSTL_THS3491_RGT_G20.kicad_pcb'))
m=json.loads((S/'review/design_manifest.json').read_text());g=json.loads((H/'review/native_geometry.json').read_text())
def xy(v):return [p.ToMM(v.x),p.ToMM(v.y)]
fps={f.GetReference():f for f in b.GetFootprints()};pads={(f.GetReference(),q.GetNumber()):q for f in b.GetFootprints() for q in f.Pads()}
offset=[xy(fps['U1'].GetPosition())[i]-[18.79601,27.94][i] for i in range(2)]
def local(v):return [a-d for a,d in zip(xy(v),offset)]
errors=[]
for f in m['parts']:
 if f['ref'] not in fps:errors.append(['missing_component',f['ref']]);continue
 if math.dist(local(fps[f['ref']].GetPosition()),[f['x'],f['y']])>.002:errors.append(['position',f['ref']])
 for n,net in f['nets'].items():
  if (f['ref'],n) not in pads or pads[f['ref'],n].GetNetname()!=net:errors.append(['pin_net',f['ref'],n,net])
vias=[t for t in b.GetTracks() if isinstance(t,p.PCB_VIA)];arcs=[t for t in b.GetTracks() if isinstance(t,p.PCB_ARC)]
for a in g['arcs']:
 hits=[t for t in arcs if t.GetNetname()==a['net'] and math.dist(local(t.GetStart()),a['start'])<.002 and math.dist(local(t.GetEnd()),a['end'])<.002]
 if len(hits)!=1:errors.append(['arc_geometry',a])
for v in g['vias']:
 if not any(t.GetNetname()==v['net'] and math.dist(local(t.GetPosition()),v['pos'])<.002 for t in vias):errors.append(['via_geometry',v])
ep=pads['U1','17'];ev=[t for t in vias if t.GetNetname()=='GND' and math.dist(xy(t.GetPosition()),xy(ep.GetPosition()))<.7]
vip=[]
for v in json.loads((H/'review/vias.json').read_text()):
 if 'via-in-pad' in v['group'] and not v['group'].startswith('U1'):
  ref,n=v['group'].split()[0].split('.');q=pads[ref,n]
  if math.dist(local(q.GetPosition()),v['pos'])>.002:errors.append(['via_in_pad',ref,n])
  vip.append(v)
power_tracks=[t for t in b.GetTracks() if not isinstance(t,p.PCB_VIA) and t.GetNetname() in ['VIN_P','VIN_N','VCC','VEE']]
pitch=math.dist(xy(pads['J7','1'].GetPosition()),xy(pads['J7','2'].GetPosition()))
assert not errors,errors
assert b.GetCopperLayerCount()==4 and len(ev)==5 and len(arcs)==3 and not power_tracks and abs(pitch-2.54)<.002
# Importer does not transfer query-scoped pad polygon rules. Reapply the declared
# rules to this audit copy only; keep the imported copper fill unchanged.
for f in b.GetFootprints():
 f.Reference().SetVisible(False);f.Value().SetVisible(False)
 for q in f.Pads():
  solid=f.GetReference() in ['U1','H9'] or (f.GetReference() in ['C3','C4','C5','C6'] and q.GetNetname()=='GND')
  q.SetLocalZoneConnection(p.ZONE_CONNECTION_FULL if solid else p.ZONE_CONNECTION_THERMAL);q.SetThermalGap(p.FromMM(.2));q.SetThermalSpokeAngleDegrees(0)
for z in b.Zones():
 if z.GetIsRuleArea():continue
 z.SetLocalClearance(p.FromMM(.205));z.SetThermalReliefGap(p.FromMM(.2));z.SetThermalReliefSpokeWidth(p.FromMM(.25));z.SetPadConnection(p.ZONE_CONNECTION_FULL if z.GetLayer()!=p.F_Cu else p.ZONE_CONNECTION_THERMAL)
ds=b.GetDesignSettings();ds.m_MinClearance=p.FromMM(.15);ds.m_TrackMinWidth=p.FromMM(.15);ds.m_ViasMinSize=p.FromMM(.4);ds.m_ViasMinAnnularWidth=p.FromMM(.1);ds.m_MinThroughDrill=p.FromMM(.2);ds.m_HoleToHoleMin=p.FromMM(.25);ds.m_CopperEdgeClearance=p.FromMM(.25)
r=dict(copper_layers=4,parts=len(fps),native_pad_count=len(g['pads']),component_via_in_pad_count=len(vip),EP_via_count=len(ev),native_arc_count=len(arcs),native_via_count=len(vias),TEMP_header_pitch_mm=pitch,errors=errors,power_track_count=len(power_tracks),altium_application_DRC=False)
(H/'review/native_import_check.json').write_text(json.dumps(r,indent=2));print(r)
p.SaveBoard(str(S/'native_audit.kicad_pcb'),b);(S/'native_audit.kicad_pro').write_text((S/'QSTL_THS3491_RGT_G20.kicad_pro').read_text())
