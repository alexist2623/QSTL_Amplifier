from pathlib import Path
import json,pcbnew as pcb
H=Path(__file__).resolve().parents[1]
b=pcb.LoadBoard(str(H/'staging/QSTL_THS3491_RGT_G20.kicad_pcb'))
def xy(v):return [pcb.ToMM(v.x),pcb.ToMM(v.y)]
def loop(c):return [xy(c.CPoint(i)) for i in range(c.PointCount())]
parts=[];pads=[];tracks=[];arcs=[];vias=[];zones=[];draw=[]
for f in b.GetFootprints():
 parts.append(dict(ref=f.GetReference(),value=f.GetValue(),pattern=str(f.GetFPID().GetLibItemName()),pos=xy(f.GetPosition()),angle=f.GetOrientationDegrees(),layer=b.GetLayerName(f.GetLayer())))
 for p in f.Pads():
  pads.append(dict(ref=f.GetReference(),num=p.GetNumber(),net=p.GetNetname().lstrip('/'),pos=xy(p.GetPosition()),size=xy(p.GetSize()),angle=p.GetOrientationDegrees(),drill=xy(p.GetDrillSize()),shape=int(p.GetShape()),roundrect_ratio=p.GetRoundRectRadiusRatio(),layers=[b.GetLayerName(l) for l in p.GetLayerSet().Seq()],connection=int(p.GetLocalZoneConnection()),npth=p.GetAttribute()==pcb.PAD_ATTRIB_NPTH))
for t in b.GetTracks():
 if isinstance(t,pcb.PCB_VIA):vias.append(dict(net=t.GetNetname().lstrip('/'),pos=xy(t.GetPosition()),diameter=pcb.ToMM(t.GetWidth(pcb.F_Cu)),drill=pcb.ToMM(t.GetDrillValue())))
 elif isinstance(t,pcb.PCB_ARC):arcs.append(dict(net=t.GetNetname(),start=xy(t.GetStart()),mid=xy(t.GetMid()),end=xy(t.GetEnd()),center=xy(t.GetCenter()),radius=pcb.ToMM(t.GetRadius()),angle=t.GetAngle().AsDegrees(),width=pcb.ToMM(t.GetWidth()),layer=b.GetLayerName(t.GetLayer())))
 else:tracks.append(dict(net=t.GetNetname().lstrip('/'),start=xy(t.GetStart()),end=xy(t.GetEnd()),width=pcb.ToMM(t.GetWidth()),layer=b.GetLayerName(t.GetLayer())))
for z in b.Zones():
 layers=z.GetLayerSet().Seq()
 for layer in layers:
  filled=[]
  if not z.GetIsRuleArea():
   poly=z.GetFilledPolysList(layer)
   for i in range(poly.OutlineCount()):filled.append(dict(outline=loop(poly.Outline(i)),holes=[loop(poly.Hole(i,j)) for j in range(poly.HoleCount(i))]))
  zones.append(dict(net=z.GetNetname().lstrip('/'),name=z.GetZoneName(),layer=b.GetLayerName(layer),priority=z.GetAssignedPriority(),keepout=z.GetIsRuleArea(),outline=loop(z.Outline().Outline(0)),filled=filled))
for s in b.GetDrawings():
 if isinstance(s,pcb.PCB_SHAPE):draw.append(dict(type='shape',shape=int(s.GetShape()),layer=b.GetLayerName(s.GetLayer()),start=xy(s.GetStart()),end=xy(s.GetEnd()),width=pcb.ToMM(s.GetWidth()),filled=s.IsSolidFill()))
 elif isinstance(s,pcb.PCB_TEXT):draw.append(dict(type='text',layer=b.GetLayerName(s.GetLayer()),pos=xy(s.GetPosition()),text=s.GetText(),size=xy(s.GetTextSize())))
(H/'review/native_geometry.json').write_text(json.dumps(dict(board_width=41.65601,board_height=68.58,parts=parts,pads=pads,tracks=tracks,arcs=arcs,vias=vias,zones=zones,draw=draw),indent=2))
print(len(parts),'parts',len(pads),'pads',len(tracks),'tracks',len(vias),'vias',len(zones),'zones')
