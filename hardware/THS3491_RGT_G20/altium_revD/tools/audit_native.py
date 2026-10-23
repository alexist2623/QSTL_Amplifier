"""Independent KiCad 6 import audit of the delivered native copper.

Use import_for_audit.py after saving through Altium. Imported copper is
checked WITHOUT refilling. The complete native file includes Texts6.
"""
from pathlib import Path
import json
import math
import pcbnew as p
import wx

ROOT=Path(__file__).resolve().parents[1]
S=ROOT/'staging'; R=ROOT/'review'
app=wx.App(False); log=wx.LogStderr()
g=json.loads((R/'native_geometry.json').read_text())
provenance=json.loads((S/'native_roundtrip.import.json').read_text())
b=p.LoadBoard(str(S/'native_roundtrip.kicad_pcb'))
fps={f.GetReference():f for f in b.GetFootprints()}
def xy(v): return [p.ToMM(v.x),p.ToMM(v.y)]
offset=[xy(fps['U1'].GetPosition())[i]-[18.79601,27.94][i] for i in range(2)]
b.Move(p.wxPoint(p.FromMM(-offset[0]),p.FromMM(-offset[1])))
for layer,name in [(p.F_Cu,'F.Cu'),(p.In1_Cu,'In1.Cu'),(p.In2_Cu,'In2.Cu'),(p.B_Cu,'B.Cu')]:
    b.SetLayerName(layer,name)
errors=[]; tol=.00002
def check(ok,*detail):
    if not ok: errors.append(detail)
def close(a,b): return math.dist(a,b)<tol
for f in g['parts']:
    q=fps[f['ref']]
    check(close(xy(q.GetPosition()),f['pos']),'component_position',f['ref'])
    check(abs((q.GetOrientationDegrees()-f['angle']+180)%360-180)<.0001,'component_angle',f['ref'])
actual={(f.GetReference(),q.GetNumber()):q for f in b.GetFootprints() for q in f.Pads()}
shape_details=[]
for q in g['pads']:
    if not any(l.endswith('.Cu') for l in q['layers']): continue
    a=actual[q['ref'],q['num']]
    check(close(xy(a.GetPosition()),q['pos']),'pad_position',q['ref'],q['num'])
    check(a.GetNetname()==q['net'],'pad_net',q['ref'],q['num'])
    check(close(xy(a.GetSize()),q['size']),'pad_size',q['ref'],q['num'])
    check(a.GetShape()==q['shape'],'pad_shape',q['ref'],q['num'],a.GetShape(),q['shape'])
    if q['ref'] in {'R14','R15','U1'}:
        check(a.GetShape()==p.PAD_SHAPE_RECT,'target_rectangular',q['ref'],q['num'])
        # KiCad retains an inactive roundrect ratio on rectangular pads too.
        # Verify actual copper outline: exactly four perpendicular corners.
        poly=a.GetEffectivePolygon()
        corners=[xy(poly.Outline(0).CPoint(i)) for i in range(poly.Outline(0).PointCount())]
        check(poly.OutlineCount()==1 and len(corners)==4,
              'pad_four_corners',q['ref'],q['num'],len(corners))
        if len(corners)==4:
            edges=[[corners[(i+1)%4][j]-corners[i][j] for j in range(2)] for i in range(4)]
            check(all(abs(sum(edges[i][j]*edges[(i+1)%4][j] for j in range(2)))<.00001 for i in range(4)),
                  'pad_right_angles',q['ref'],q['num'])
            area=abs(sum(corners[i][0]*corners[(i+1)%4][1]-corners[(i+1)%4][0]*corners[i][1] for i in range(4)))/2
            check(abs(area-q['size'][0]*q['size'][1])<.00001,'pad_rectangular_area',q['ref'],q['num'])
        shape_details.append(dict(ref=q['ref'],pad=q['num'],shape='rectangle',
            size_mm=xy(a.GetSize()),inactive_roundrect_ratio=a.GetRoundRectRadiusRatio(),
            radius_mm=0 if a.GetShape()==p.PAD_SHAPE_RECT else p.ToMM(a.GetRoundRectCornerRadius()),
            copper_outline_mm=corners))
    check(abs((a.GetOrientationDegrees()-q['angle']+180)%360-180)<.0001,'pad_rotation',q['ref'],q['num'])
vias=[v for v in b.GetTracks() if isinstance(v,p.PCB_VIA)]
arcs=[v for v in b.GetTracks() if isinstance(v,p.PCB_ARC)]
tracks=[v for v in b.GetTracks() if not isinstance(v,(p.PCB_ARC,p.PCB_VIA))]
check(len(vias)==len(g['vias']),'via_count')
check(len(arcs)==len(g['arcs']),'arc_count')
check(len(tracks)==len(g['tracks']),'track_count',len(tracks),len(g['tracks']))
for v in g['vias']:
    hits=[a for a in vias if a.GetNetname()==v['net'] and close(xy(a.GetPosition()),v['pos'])]
    check(len(hits)==1,'via',v)
    if hits:
        check(abs(p.ToMM(hits[0].GetDrillValue())-v['drill'])<tol,'via_drill',v)
        check(abs(p.ToMM(hits[0].GetWidth())-v['diameter'])<tol,'via_diameter',v)
remaining_arcs=list(arcs); remaining_tracks=list(tracks)
for t in g['tracks']+g['arcs']:
    pool=remaining_arcs if 'radius' in t else remaining_tracks
    hits=[a for a in pool if a.GetNetname()==t['net']
          and ((close(xy(a.GetStart()),t['start']) and close(xy(a.GetEnd()),t['end']))
               or (close(xy(a.GetEnd()),t['start']) and close(xy(a.GetStart()),t['end'])))]
    check(bool(hits),'track_geometry',t)
    if hits:
        check(abs(p.ToMM(hits[0].GetWidth())-t['width'])<tol,'track_width',t)
        pool.remove(hits[0])  # Rev C has two coincident AMP_OUT segments.
check(not remaining_arcs and not remaining_tracks,'unexpected_track_geometry')
def loop(c): return [xy(c.CPoint(i)) for i in range(c.PointCount())]
filled=[]
cutouts=[]
for z in b.Zones():
    if z.GetIsRuleArea():
        cutouts.append(dict(layer=b.GetLayerName(z.GetLayer()),outline=loop(z.Outline().Outline(0))))
        continue
    polys=z.GetFilledPolysList(z.GetLayer())
    for i in range(polys.OutlineCount()):
        filled.append(dict(net=z.GetNetname(),layer=b.GetLayerName(z.GetLayer()),
                           outline=loop(polys.Outline(i)),
                           holes=[loop(polys.Hole(i,j)) for j in range(polys.HoleCount(i))]))
(R/'native_import_copper.json').write_text(json.dumps(filled,indent=2))
(R/'native_import_cutouts.json').write_text(json.dumps(cutouts,indent=2))
# The importer does not retain per-pad query rules. Apply their declared
# electrical/manufacturing settings to the audit copy, leaving fill untouched.
for f in b.GetFootprints():
    f.Reference().SetVisible(False); f.Value().SetVisible(False)
    for q in f.Pads():
        solid=f.GetReference() in ['U1','H9'] or (f.GetReference() in ['C3','C4','C5','C6'] and q.GetNetname()=='GND')
        q.SetZoneConnection(p.ZONE_CONNECTION_FULL if solid else p.ZONE_CONNECTION_THERMAL)
        q.SetThermalGap(p.FromMM(.2)); q.SetThermalSpokeWidth(p.FromMM(.25))
for z in b.Zones():
    if z.GetIsRuleArea(): continue
    z.SetLocalClearance(p.FromMM(.205)); z.SetThermalReliefGap(p.FromMM(.2))
    z.SetThermalReliefSpokeWidth(p.FromMM(.25))
    z.SetPadConnection(p.ZONE_CONNECTION_THERMAL if z.GetLayer()==p.F_Cu else p.ZONE_CONNECTION_FULL)
ds=b.GetDesignSettings()
for name,value in [('m_MinClearance',.15),('m_TrackMinWidth',.15),('m_ViasMinSize',.4),
                   ('m_ViasMinAnnularWidth',.1),('m_MinThroughDrill',.2),
                   ('m_HoleToHoleMin',.25),('m_CopperEdgeClearance',.25)]:
    setattr(ds,name,p.FromMM(value))
b.BuildConnectivity()
assert p.WriteDRCReport(b,str(R/'native_audit_drc.txt'),p.EDA_UNITS_MILLIMETRES,True)
p.SaveBoard(str(S/'native_audit.kicad_pcb'),b)
report=dict(reader=p.GetBuildVersion(),errors=errors,copper_layers=b.GetCopperLayerCount(),
            parts=len(fps),pads=len(actual),vias=len(vias),arcs=len(arcs),tracks=len(tracks),
            TEMP_header_pitch_mm=math.dist(xy(actual['J7','1'].GetPosition()),xy(actual['J7','2'].GetPosition())),
            copper_refilled_in_native_audit=False,
            text_stream_excluded_from_import=provenance['text_stream_excluded'],
            source_sha256=provenance['source_sha256'],altium_application_DRC=False)
report['all_pad_shapes_checked']=len(actual)
report['persistent_polygon_cutouts']=len(cutouts)
report['rectangular_pads_verified']=shape_details
report['rounded_rectangle_pads']=[]
(R/'native_import_check.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
assert not errors,errors
assert b.GetCopperLayerCount()==4
