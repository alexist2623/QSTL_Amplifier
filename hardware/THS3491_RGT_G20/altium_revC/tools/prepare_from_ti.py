"""Rev C: actual TI HSP006A footprint locations and curved input routes.
The RF core is copied, not inferred from a screenshot. Power is redesigned.
Run with KiCad Python; final delivery is Altium.
"""
from pathlib import Path
import pcbnew as p, json, math, copy
H=Path(__file__).resolve().parents[1];S=H/'staging';(S/'review').mkdir(exist_ok=True)
TI=H.parent/'altium/reference/TI_HSP006A/original_import.kicad_pcb'
src=p.LoadBoard(str(TI));b=p.BOARD();b.SetCopperLayerCount(4)
W,Y=41.65601,68.58;OX,OY=127.673095,70.7136;UX,UY=18.79601,27.94
mm=p.FromMM
def vec(x,y):return p.VECTOR2I(mm(x),mm(y))
def xy(v):return [p.ToMM(v.x),p.ToMM(v.y)]
def box(a,c,d,e):return [(a,c),(d,c),(d,e),(a,e)]
mapping={'NetJ1_1':'inm','NetJ2_1':'inpt_raw','NetR6_2':'inpt','NetR1_2':'RG_DRIVE','NetR3_2':'INV','NetR4_2':'FB','NetR9_1':'AMP_OUT','NetJ3_1':'output','VS+':'VCC','VS-':'VEE','NetC1_1':'VIN_P','NetC2_1':'VIN_N','NetC8_1':'TJ_RAW','NetR8_1':'TEMP','GND':'GND'}
nets={}
for i,n in enumerate(sorted(set(mapping.values())),1):
 q=p.NETINFO_ITEM(b,n,i);b.Add(q);nets[n]=q
fps={};orig={f.GetReference():f for f in src.GetFootprints()}
keep=['U1']+[f'R{i}' for i in range(1,9)]+[f'C{i}' for i in range(1,9)]+['L1','L2','J1','J2','J3','TP1']
for ref in keep:
 f=p.FOOTPRINT(orig[ref]);f.Move(vec(-OX,-OY));b.Add(f);fps[ref]=f
 f.Reference().SetVisible(False);f.Value().SetVisible(False)
 for pd in f.Pads():pd.SetNet(nets[mapping[pd.GetNetname()]])
 # Remove imported mask/paste customizations; use a single explicit policy.
 for pd in f.Pads():pd.SetLocalSolderMaskMargin(mm(.04));pd.SetLocalSolderPasteMargin(0);pd.SetLocalSolderPasteMarginRatio(0.0)
 # Keep visible footprint outline graphics; hidden property texts are not CAM data.
 f.SetDNP(ref=='R5')
def move(ref,x,y,angle):fps[ref].SetPosition(vec(x,y));fps[ref].SetOrientationDegrees(angle)
def pad(ref,n):return next(pd for pd in fps[ref].Pads() if pd.GetNumber()==str(n))
def at(ref,n):return xy(pad(ref,n).GetPosition())
def addfp(ref,lib,name,x,y,angle,value,connections):
 f=p.FootprintLoad(str(Path(r'C:\Users\Measurement2\AppData\Local\Programs\KiCad\10.0\share\kicad\footprints')/(lib+'.pretty')),name)
 f.SetReference(ref);f.SetValue(value);f.SetPosition(vec(x,y));f.SetOrientationDegrees(angle);f.Reference().SetVisible(False);f.Value().SetVisible(False);b.Add(f);fps[ref]=f
 for pd in f.Pads():pd.SetNet(nets[connections[pd.GetNumber()]]);pd.SetLocalSolderMaskMargin(mm(.04))
 return f
def feature(ref,x,y,net,drill=1.3,size=3):
 f=p.FOOTPRINT(b);f.SetReference(ref);f.SetValue(net);f.SetFPID(p.LIB_ID('QSTL','WIRE_PAD'));f.SetPosition(vec(x,y));b.Add(f);fps[ref]=f
 pd=p.PAD(f);pd.SetNumber('1');pd.SetShape(p.PAD_SHAPE_CIRCLE);pd.SetAttribute(p.PAD_ATTRIB_PTH);pd.SetLayerSet(p.PAD.PTHMask());pd.SetSize(vec(size,size));pd.SetDrillSize(vec(drill,drill));pd.SetPosition(vec(x,y));pd.SetNet(nets[net]);f.Add(pd)
 f.Reference().SetVisible(False);f.Value().SetVisible(False)
 return f
def track(net,points,width=.2,layer=p.F_Cu):
 for a,e in zip(points,points[1:]):
  if math.dist(a,e)<.00001:continue
  t=p.PCB_TRACK(b);t.SetStart(vec(*a));t.SetEnd(vec(*e));t.SetWidth(mm(width));t.SetLayer(layer);t.SetNet(nets[net]);b.Add(t)
vialist=[]
def via(net,x,y,diam=.4,drill=.2,group='GND stitching'):
 if any(math.dist([x,y],v['pos'])<.001 for v in vialist):return
 v=p.PCB_VIA(b);v.SetPosition(vec(x,y));v.SetWidth(mm(diam));v.SetDrill(mm(drill));v.SetViaType(p.VIATYPE_THROUGH);v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetNet(nets[net]);v.SetFrontTentingMode(p.TENTING_MODE_TENTED);v.SetBackTentingMode(p.TENTING_MODE_TENTED);b.Add(v);vialist.append(dict(net=net,pos=[x,y],diameter=diam,drill=drill,group=group))
def zone(net,points,layer=p.F_Cu,priority=0,name='',solid=False,keepout=False):
 z=p.ZONE(b);z.SetLayer(layer);z.SetZoneName(name);z.SetAssignedPriority(priority);z.SetLocalClearance(mm(.205));z.SetMinThickness(mm(.10));z.SetThermalReliefGap(mm(.20));z.SetThermalReliefSpokeWidth(mm(.25));z.SetPadConnection(p.ZONE_CONNECTION_FULL if solid else p.ZONE_CONNECTION_THERMAL)
 if keepout:z.SetIsRuleArea(True);z.SetDoNotAllowZoneFills(True);z.SetDoNotAllowTracks(False);z.SetDoNotAllowVias(False);z.SetDoNotAllowPads(False);z.SetDoNotAllowFootprints(False)
 else:z.SetNet(nets[net])
 o=z.Outline();o.NewOutline()
 for x,y in points:o.Append(mm(x),mm(y))
 b.Add(z);return z

# Preserve all J1/J2 and R1..R7 locations, rotations and exact curved centerlines.
rf_nets={'NetJ1_1','NetJ2_1','NetR1_2','NetR3_2','NetR4_2','NetR6_2'}
for t in src.GetTracks():
 if isinstance(t,p.PCB_VIA) or t.GetNetname() not in rf_nets:continue
 q=p.Cast_to_PCB_ARC(t.Duplicate()) if isinstance(t,p.PCB_ARC) else p.Cast_to_PCB_TRACK(t.Duplicate());q.Move(vec(-OX,-OY));q.SetLayer(p.F_Cu);q.SetNet(nets[mapping[t.GetNetname()]]);b.Add(q)
 if t.GetNetname() in ['NetJ1_1','NetJ2_1','NetR1_2']:q.SetWidth(mm(.3058))

# The original attenuator is removed; the original output axis is retained.
addfp('R14','Resistor_SMD','R_0603_1608Metric',22.2,UY,0,'49.9',{'1':'AMP_OUT','2':'output'})
addfp('R15','Resistor_SMD','R_0805_2012Metric',31.0,UY+.9125,270,'1Meg',{'1':'output','2':'GND'})
for n in [10,11]:track('AMP_OUT',[at('U1',n),(20.57621,at('U1',n)[1]),(20.82621,UY),(21.375,UY)],.24001)
track('output',[at('R14',2),at('R15',1),at('J3',1)],.3058)

# The positive supply entry remains above the RF core. Negative is its 180-degree
# counterpart around U1. Bulk caps / beads keep the same mirrored relationship.
entry=(18.66901,6.858)
feature('J4',*entry,'VIN_P');feature('J5',entry[0]-4,entry[1],'GND')
feature('J6',2*UX-entry[0],2*UY-entry[1],'VIN_N');feature('J8',2*UX-(entry[0]-4),2*UY-entry[1],'GND')
for plus,minus in [('C1','C2'),('L1','L2')]:
 f=fps[plus];x,y=xy(f.GetPosition());move(minus,2*UX-x,2*UY-y,(f.GetOrientationDegrees()+180)%360)
# Local decouplers are closer than TI's original bulk bypass locations.
move('C5',17.79202,24.95,90);move('C3',20.55,24.50,0)
move('C6',19.8,2*UY-24.95,270);move('C4',2*UX-20.55,2*UY-24.50,180)
move('C7',24.9,31.5,270)
# TEMP is an analog measurement header for jumper leads, never a shorting cap.
move('C8',23.1,37.5,0);move('R8',23.1,40,90)
addfp('J7','Connector_PinHeader_2.54mm','PinHeader_1x02_P2.54mm_Vertical',35.0,44.0,90,'TEMP / GND',{'1':'TEMP','2':'GND'})
track('TJ_RAW',[at('U1',6),(18.54601,30.4),(18.9,30.8),(18.9,32.5),(22.6,36.2),at('C8',1)],.20)
track('TJ_RAW',[at('C8',1),(22.6,39.3),at('R8',2)],.20)
track('TEMP',[at('R8',1),(25.4,43.0),(34.0,43.0),at('J7',1)],.25)

# Explicit copper connections from every grounded U1 pad into the ground EP.
ground_ends={2:(UX-.5,UY-.25),5:(UX-.75,UY+.5),9:(UX+.5,UY+.75),12:(UX+.5,UY-.75),15:(UX-.25,UY-.5)}
for n,pt in ground_ends.items():track('GND',[at('U1',n),pt],.20)
for dx,dy in [(0,0),(-.45,-.45),(.45,-.45),(-.45,.45),(.45,.45)]:via('GND',UX+dx,UY+dy,group='U1 EP via-in-pad')

# Ground reference layers and local capacitance windows near sensitive pins.
for layer in [p.F_Cu,p.In1_Cu,p.B_Cu]:zone('GND',box(.3,.3,W-.3,Y-.3),layer,name='GND_REFERENCE',solid=layer!=p.F_Cu)
for layer in [p.F_Cu,p.In1_Cu,p.In2_Cu,p.B_Cu]:
 zone('',[(14.20,26.30),(16.95,26.30),(17.65,27.15),(17.65,29.15),(16.65,29.15),(16.65,28.60),(14.20,28.60)],layer,name='FB_INV_LOCAL_WINDOW',keepout=True)
 zone('',box(17.5,29.0,17.85,29.12),layer,name='INPLUS_LOCAL_WINDOW',keepout=True)
 zone('',box(19.75,27.25,21.22,28.63),layer,name='OUT_LOCAL_WINDOW',keepout=True)
# Split supply distribution is entirely internal; only entry and pin-side islands
# exist on L1. A dedicated small local + island also feeds rail-to-rail capacitor C7.
zone('VCC',[(.3,.3),(W-.3,.3),(W-.3,UY-.35),(25.9,UY-.35),(25.9,31.4),(23.8,31.4),(23.8,UY-.35),(.3,UY-.35)],p.In2_Cu,priority=2,name='L3_VCC',solid=True)
zone('VEE',box(.3,UY+.35,W-.3,Y-.3),p.In2_Cu,name='L3_VEE',solid=True)
local_plus=[(17.1,25.05),(19.0,25.05),(19.0,23.7),(20.6,23.7),(20.6,25.65),(20.05,26.65),(17.1,26.65)]
local_minus=[(2*UX-x,2*UY-y) for x,y in local_plus]
# VEE pins are on the right side of the southern pin row.
local_minus += []
zone('VCC',local_plus,priority=3,name='L1_VCC_LOCAL_PIN_ISLAND')
zone('VEE',local_minus,priority=3,name='L1_VEE_LOCAL_PIN_ISLAND')
# Entry islands connect the solder pad -> C1 -> bead on L1, then via cluster to L3.
raw_plus=[(16.7,4.9),(20.5,4.9),(25.4,3.8),(28.2,3.8),(28.2,8.55),(25.6,8.55),(25.6,7.45),(20.5,8.9),(16.7,8.9)]
raw_minus=[(2*UX-x,2*UY-y) for x,y in raw_plus]
zone('VIN_P',raw_plus,priority=2,name='L1_POSITIVE_INPUT');zone('VIN_N',raw_minus,priority=2,name='L1_NEGATIVE_INPUT')
bead_plus=box(25.8,8.25,27.8,10.65)
bead_minus=[(2*UX-x,2*UY-y) for x,y in bead_plus]
zone('VCC',bead_plus,priority=3,name='L1_VCC_ENTRY_VIA_ISLAND');zone('VEE',bead_minus,priority=3,name='L1_VEE_ENTRY_VIA_ISLAND')
zone('VCC',box(24.35,30.3,25.45,31.2),priority=3,name='L1_C7_VCC')
zone('VEE',box(24.35,31.8,25.45,32.9),priority=3,name='L1_C7_VEE')
# The C7 positive landing connects by L3 extension, away from the output corridor.

# Component pad vias: grounds stay on ground; power vias stay on their islands.
for ref in ['C1','C2','C3','C4','C5','C6','C7','C8','L1','L2','R2','R5','R7','R15']:
 for pd in fps[ref].Pads():
  n=pd.GetNetname()
  if n not in ['GND','VCC','VEE']:continue
  via(n,*xy(pd.GetPosition()),group=ref+'.'+pd.GetNumber()+' via-in-pad')
for x,y in [(26.2,9.7),(26.9,9.7),(27.6,9.7),(26.2,10.35),(26.9,10.35),(27.6,10.35)]:
 via('VCC',x,y,group='entry parallel vias');via('VEE',2*UX-x,2*UY-y,group='entry parallel vias')
for x,y in [(17.4,25.4),(17.4,26.05),(19.7,25.9),(20.3,25.7)]:via('VCC',x,y,group='U1 local parallel vias')
for x,y in [(20.25,29.9),(20.25,30.55),(17.6,30.5),(17.6,31.9)]:via('VEE',x,y,group='U1 local parallel vias')

def segment_distance(pt,a,c):
 dx,dy=c[0]-a[0],c[1]-a[1];l=dx*dx+dy*dy
 u=max(0,min(1,((pt[0]-a[0])*dx+(pt[1]-a[1])*dy)/l)) if l else 0
 return math.dist(pt,[a[0]+u*dx,a[1]+u*dy])
signal_segments=[]
for t in b.GetTracks():
 if isinstance(t,p.PCB_VIA) or t.GetNetname()=='GND':continue
 pts=[xy(t.GetStart()),xy(t.GetEnd())]
 if isinstance(t,p.PCB_ARC):
  c=xy(t.GetCenter());a=math.atan2(pts[0][1]-c[1],pts[0][0]-c[0]);da=math.radians(t.GetAngle().AsDegrees());r=p.ToMM(t.GetRadius())
  pts=[[c[0]+r*math.cos(a+da*i/300),c[1]+r*math.sin(a+da*i/300)] for i in range(301)]
 signal_segments.extend((a,e,p.ToMM(t.GetWidth())/2) for a,e in zip(pts,pts[1:]))
def safe_ground_via(x,y):
 if any(segment_distance([x,y],a,e)<w+.41 for a,e,w in signal_segments):return False
 for f in fps.values():
  for pd in f.Pads():
   if pd.GetNetname()=='GND':continue
   px,py=xy(pd.GetPosition());sx,sy=xy(pd.GetSize());ang=math.radians(pd.GetOrientationDegrees())
   dx=(x-px)*math.cos(ang)-(y-py)*math.sin(ang);dy=(x-px)*math.sin(ang)+(y-py)*math.cos(ang)
   if math.hypot(max(0,abs(dx)-sx/2),max(0,abs(dy)-sy/2))<.42:return False
 return True

# Retain the TI ground-stitch pattern where it does not conflict with new copper.
# Limit the array to .50 mm spacing / .20 mm drill, all now through-vias.
power_boxes=[]
for z in b.Zones():
 if z.GetLayer()==p.F_Cu and z.GetNetname() in ['VCC','VEE','VIN_P','VIN_N']:
  q=z.Outline().Outline(0);pts=[xy(q.CPoint(i)) for i in range(q.PointCount())];power_boxes.append((min(t[0] for t in pts)-.4,min(t[1] for t in pts)-.4,max(t[0] for t in pts)+.4,max(t[1] for t in pts)+.4))
for v in src.GetTracks():
 if not isinstance(v,p.PCB_VIA) or v.GetNetname()!='GND':continue
 x,y=xy(v.GetPosition());x-=OX;y-=OY
 if not (.65<x<W-.65 and .65<y<Y-.65):continue
 if abs(x-UX)<2.1 and abs(y-UY)<2.1:continue
 if 23.4<x<26.3 and 26.9<y<31.8:continue # unbroken L3 neck to C7 VCC
 if any(a<x<c and d<y<e for a,d,c,e in power_boxes):continue
 if any(math.dist([x,y],q['pos'])<(.62 if q['net']!='GND' else .51) for q in vialist):continue
 # Avoid relocated SMD bodies and both sides of non-ground pads.
 if not safe_ground_via(x,y):continue
 via('GND',x,y)
for x in [1,W-1]:
 for y in range(2,68,3):
  if safe_ground_via(x,y) and all(math.dist([x,y],xy(pd.GetPosition()))>2.4 for f in fps.values() for pd in f.Pads()) and all(math.dist([x,y],v['pos'])>.51 for v in vialist):via('GND',x,y)

# Mechanical holes retained at the four TI mounting positions; no banana hardware.
f=p.FOOTPRINT(orig['H9']);f.Move(vec(-OX,-OY+1.8));b.Add(f);fps['H9']=f
for pd in list(f.Pads()):
 if not pd.GetNumber():f.Remove(pd)
 else:pd.SetNet(nets['GND']);pd.SetLocalZoneConnection(p.ZONE_CONNECTION_FULL)
f.Reference().SetVisible(False);f.Value().SetVisible(False)
for ref in ['H1','H2','H3','H4']:
 f=p.FOOTPRINT(orig[ref]);f.Move(vec(-OX,-OY));b.Add(f);fps[ref]=f
 f.Reference().SetVisible(False);f.Value().SetVisible(False)
 for pd in f.Pads():
  pd.SetNet(nets['GND']);pd.SetAttribute(p.PAD_ATTRIB_NPTH);pd.SetSize(pd.GetDrillSize())
for a,e in zip([(0,0),(W,0),(W,Y),(0,Y)],[(W,0),(W,Y),(0,Y),(0,0)]):
 s=p.PCB_SHAPE();s.SetShape(p.SHAPE_T_SEGMENT);s.SetStart(vec(*a));s.SetEnd(vec(*e));s.SetWidth(mm(.05));s.SetLayer(p.Edge_Cuts);b.Add(s)
for f in fps.values():
 # The TI importer splits courtyard loops into malformed segments. Retain the
 # real copper and assembly graphics; regenerate courtyards only in final CAD.
 for g in list(f.GraphicalItems()):
  if g.GetLayer() in [p.F_CrtYd,p.B_CrtYd]:f.Remove(g)
 for pd in f.Pads():
  solid=f.GetReference() in ['U1','H9'] or (f.GetReference() in ['C3','C4','C5','C6'] and pd.GetNetname()=='GND')
  pd.SetLocalZoneConnection(p.ZONE_CONNECTION_FULL if solid else p.ZONE_CONNECTION_THERMAL);pd.SetThermalGap(mm(.2));pd.SetThermalSpokeAngleDegrees(0)
ds=b.GetDesignSettings();ds.m_MinClearance=mm(.15);ds.m_TrackMinWidth=mm(.15);ds.m_ViasMinSize=mm(.4);ds.m_ViasMinAnnularWidth=mm(.1);ds.m_MinThroughDrill=mm(.2);ds.m_HoleToHoleMin=mm(.25);ds.m_CopperEdgeClearance=mm(.25)
values={'U1':'THS3491IRGTR','R1':'49.9','R2':'0','R3':'20.5','R4':'390','R5':'49.9 DNP','R6':'0','R7':'49.9','R8':'0','C1':'4.7u / 50V','C2':'4.7u / 50V','C3':'1u / 50V','C4':'1u / 50V','C5':'100n / 50V X7R','C6':'100n / 50V X7R','C7':'10n / 100V','C8':'100n / 25V','L1':'220R @100MHz','L2':'220R @100MHz'}
values.update(J1='SMA IN-',J2='SMA IN+',J3='SMA OUT')
oldparts={x['ref']:x for x in json.loads((H.parent/'altium/staging/review/design_manifest.json').read_text())['parts']}
parts=[]
for ref,f in fps.items():
 if ref in values:f.SetValue(values[ref])
 n={pd.GetNumber():pd.GetNetname() for pd in f.Pads()};v=oldparts.get(ref,{})
 typ='AMP' if ref=='U1' else 'R' if ref.startswith('R') else 'C' if ref.startswith('C') else 'BEAD' if ref.startswith('L') else 'SMA' if ref in ['J1','J2','J3'] else 'HEADER' if ref=='J7' else 'TEST'
 mpn=v.get('mpn',f.GetValue());lcsc=v.get('lcsc','')
 if ref in ['J1','J2','J3']:mpn='142-0701-851';lcsc=''
 if ref=='J7':mpn='GENERIC_1x02_2.54mm';lcsc=''
 if ref in ['R5','R6']:mpn='CRCW060349R9FKEA' if ref=='R5' else 'CRCW06030000Z0EA';lcsc='C844930' if ref=='R5' else 'C844915'
 parts.append(dict(ref=ref,value=f.GetValue(),sym=typ,fp=str(f.GetFPID().GetLibItemName()),nets=n,mpn=mpn,lcsc=lcsc,x=xy(f.GetPosition())[0],y=xy(f.GetPosition())[1],angle=f.GetOrientationDegrees(),dnp=ref=='R5'))
for text,x,y in [('QSTL / THS3491 RGT / REV C',W/2,62),('TI RF geometry / JLC 4L adaptation',W/2,64),('+15V',entry[0],entry[1]-2.5),('-15V',2*UX-entry[0],2*UY-entry[1]+2.5),('TEMP   GND',36.3,46.5)]:
 t=p.PCB_TEXT(b);t.SetText(text);t.SetPosition(vec(x,y));t.SetTextSize(vec(.8,.8));t.SetTextThickness(mm(.12));t.SetLayer(p.F_SilkS);b.Add(t)
p.SaveBoard(str(S/'QSTL_THS3491_RGT_G20.kicad_pcb'),b)
(S/'review/design_manifest.json').write_text(json.dumps(dict(parts=parts,board_width=W,board_height=Y),indent=2))
(H/'review/vias.json').write_text(json.dumps(vialist,indent=2))
(H/'review/ti_baseline.json').write_text(json.dumps(dict(source='https://e2e.ti.com/cfs-file/__key/communityserver-discussions-components-files/14/HSP006A.zip',origin_mm=[OX,OY],board_width=W,board_height=Y,unchanged_RF_references=['U1','J1','J2','J3','R1','R2','R3','R4','R5','R6','R7'],curved_input_routes_copied=True),indent=2))
print('Rev C geometry:',len(fps),'parts',len(vialist),'vias')
