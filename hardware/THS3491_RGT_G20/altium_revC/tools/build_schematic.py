"""Create native Altium compound SchDoc records and a matching visible SVG review.
No source project is edited. Pin-to-net connections are checked before writing.
"""
from pathlib import Path
import sys,json,struct,hashlib,html,shutil
H=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(H.parent/'altium/tools/vendor'))
import olefile
from cfb_copy_update import update_copy
M=json.loads((H/'staging/review/design_manifest.json').read_text())
parts={p['ref']:p for p in M['parts']}
R=[];SVG=[];pins={};expected={};wires=[];labels=[];serial=0
def uid(s):return ''.join(chr(65+b%26) for b in hashlib.sha256(('QSTL_REVC_'+s).encode()).digest()[:8])
def add(r,**kw):
 global serial
 serial+=1;kw['UniqueID']=uid(str(serial));R.append({'RECORD':str(r),**{k:str(v) for k,v in kw.items()}});return len(R)-2
def txt(s,x,y,size=12,color='#193247'):
 SVG.append(f'<text x="{x}" y="{1100-y}" font-size="{size}" fill="{color}">{html.escape(s)}</text>')
def line(a,b,color='#26744e',width=1.6):SVG.append(f'<path d="M {a[0]} {1100-a[1]} L {b[0]} {1100-b[1]}" fill="none" stroke="{color}" stroke-width="{width}"/>')
def wire(a,b):
 if a==b:return
 add(27,OwnerPartId=-1,LineWidth=1,Color=32768,LocationCount=2,X1=a[0],Y1=a[1],X2=b[0],Y2=b[1]);wires.append((a,b));line(a,b)
def label(net,p):
 add(25,OwnerPartId=-1,Color=128,FontID=1,Text=net,**{'Location.X':p[0],'Location.Y':p[1]});labels.append((net,p));txt(net,p[0]+3,p[1]+5,10)
def node(p):add(29,OwnerPartId=-1,Color=32768,**{'Location.X':p[0],'Location.Y':p[1]});SVG.append(f'<circle cx="{p[0]}" cy="{1100-p[1]}" r="2.5" fill="#26744e"/>')
def stub(ref,n,net,d=25):
 p,dir=pins[(ref,str(n))];v=[(1,0),(0,1),(-1,0),(0,-1)][dir];q=(p[0]+v[0]*d,p[1]+v[1]*d);wire(p,q);label(net,q)
def comp(ref,x,y,vertical=False):
 p=parts[ref];typ=p['sym'];pn=p['nets'];root=add(1,LibReference=p['mpn'] or p['fp'],ComponentDescription=p['value'],PartCount=2,DisplayModeCount=1,IndexInSheet=-1,OwnerPartId=-1,CurrentPartId=1,LibraryPath='*',SourceLibraryName='QSTL',TargetFileName='*',AreaColor=11599871,Color=128,PartIDLocked='T',DesignItemId=p['mpn'] or p['fp'],AllPinCount=len(pn),**{'Location.X':x,'Location.Y':y})
 R[-1]['UniqueID']=uid(ref)
 if typ=='AMP':
  a,b=(x-70,y-120),(x+70,y+120)
  pinset=[('1','FB',x-70,y+90,2,1),('2','NC/GND',x-70,y+60,2,4),('3','IN-',x-70,y+10,2,0),('4','IN+',x-70,y-50,2,0),('9','NC/GND',x+70,y-80,0,4),('10','OUT',x+70,y,0,1),('11','OUT',x+70,y-20,0,4),('12','NC/GND',x+70,y+60,0,4),('13','V+',x+40,y+120,1,7),('14','V+',x+10,y+120,1,7),('15','NC',x-20,y+120,1,4),('16','PDn',x-50,y+120,1,0),('5','GND',x-50,y-120,3,7),('6','TEMP',x-20,y-120,3,1),('7','V-',x+10,y-120,3,7),('8','V-',x+40,y-120,3,7),('17','EP',x+65,y-120,3,4)]
 elif typ in ['R','C','BEAD']:
  if vertical:
   a,b=(x-9,y-15),(x+9,y+15);pinset=[('1','',x,y+15,1,4),('2','',x,y-15,3,4)]
   if ref in ['R5','R7']:pinset=[('1','',x,y-15,3,4),('2','',x,y+15,1,4)]
  else:a,b=(x-20,y-8),(x+20,y+8);pinset=[('1','',x-20,y,2,4),('2','',x+20,y,0,4)]
  if ref=='R8':pinset=[('2','',x-20,y,2,4),('1','',x+20,y,0,4)]
 elif typ=='SMA':
  a,b=(x-15,y-15),(x+15,y+15);pinset=[('1','SIG',x+15,y,0,4),('2','GND',x,y-15,3,4)]
  if ref=='J3':pinset=[('1','SIG',x-15,y,2,4),('2','GND',x,y-15,3,4)]
 elif typ=='HEADER':
  a,b=(x-20,y-35),(x+20,y+35);pinset=[('1','TEMP',x-20,y+10,2,4),('2','GND',x-20,y-20,2,4)]
 elif typ=='POWER':
  a,b=(x-30,y-50),(x+30,y+50);pinset=[(str(i),pn[str(i)],x+30,y+60-i*25,0,4) for i in range(1,5)]
 else:a,b=(x-12,y-12),(x+12,y+12);pinset=[('1','',x,y-12,3,4)]
 if typ=='SMA':
  pinset=[v for v in pinset if v[0]=='1']+[(str(i),'GND',x-15+(i-2)*10,y-15,3,4) for i in range(2,6)]
 add(14,OwnerIndex=root,OwnerPartId=1,Color=128,AreaColor=11599871,IsSolid='T',**{'Location.X':a[0],'Location.Y':a[1],'Corner.X':b[0],'Corner.Y':b[1]})
 SVG.append(f'<rect x="{a[0]}" y="{1100-b[1]}" width="{b[0]-a[0]}" height="{b[1]-a[1]}" fill="#fff6d9" stroke="#25475d" stroke-width="1.5"/>')
 for n,name,px,py,d,et in pinset:
  add(2,OwnerIndex=root,OwnerPartId=1,Electrical=et,PinConglomerate=48+d,PinLength=30,Name=name,Designator=n,**{'Location.X':px,'Location.Y':py})
  v=[(1,0),(0,1),(-1,0),(0,-1)][d];tip=(px+v[0]*30,py+v[1]*30);pins[(ref,n)]=(tip,d);expected[(ref,n)]=pn[n];line((px,py),tip,'#25475d',1)
  if typ=='AMP':txt(name,px+(4 if d==2 else -35 if d==0 else -9),py+(4 if d in [0,2] else -12 if d==1 else 8),9)
  txt(n,(px+tip[0])/2+1,(py+tip[1])/2+3,7)
 for r,name,val,tx,ty in [(34,'Designator',ref,x-35 if vertical else x-15,b[1]+10),(41,'Comment',p['value'],x+(18 if vertical else -15),y+(0 if vertical else -26))]:
  if typ=='AMP':tx=x-25;ty=y+50 if r==34 else y-45
  if typ=='SMA' and r==41:tx=x+35 if ref=='J3' else x-78;ty=y+3
  add(r,OwnerIndex=root,OwnerPartId=-1,Color=8388608,FontID=1,Text=val,Name=name,**{'Location.X':tx,'Location.Y':ty});txt(val,tx,ty,11)
 for name,val in [('MPN',p['mpn']),('LCSC',p['lcsc']),('Footprint',p['fp'])]:add(41,OwnerIndex=root,OwnerPartId=-1,IsHidden='T',Name=name,Text=val)
 il=add(44,OwnerIndex=root);mi=add(45,OwnerIndex=il,IndexInSheet=-1,ModelName=p['fp'],ModelType='PCBLIB',IsCurrent='T');add(46,OwnerIndex=mi);add(48,OwnerIndex=mi)
def pt(r,n):return pins[(r,str(n))][0]
def connect(*ps):
 for a,b in zip(ps,ps[1:]):wire(a,b)
R=[{'HEADER':'Protel for Windows - Schematic Capture Binary File Version 5.0','Weight':'0','MinorVersion':'13','UniqueID':uid('sheet')}]
add(31,FontIdCount=1,Size1=10,FontName1='Arial',UseMBCS='T',IsBOC='T',HotSpotGridOn='T',HotSpotGridSize=5,SystemFont=1,BorderOn='T',TitleBlockOn='F',AreaColor=16317695,SnapGridOn='T',SnapGridSize=5,VisibleGridOn='T',VisibleGridSize=10,CustomX=1600,CustomY=1100,CustomXZones=8,CustomYZones=5,CustomMarginWidth=20,Display_Unit=0,UseCustomSheet='T')
positions={'U1':(800,650,False),'R4':(600,740,False),'R3':(450,660,False),'R1':(250,660,False),'R2':(350,750,True),'R5':(250,525,True),'R6':(400,600,False),'R7':(550,525,True),'J1':(100,660,False),'J2':(100,540,False),'R14':(1050,650,False),'J3':(1380,650,False),'R15':(1250,575,True),'J4':(100,340,False),'J5':(160,340,False),'J6':(100,180,False),'J8':(160,180,False),'L1':(370,360,False),'L2':(370,200,False),'C1':(260,300,True),'C2':(260,140,True),'C3':(500,300,True),'C4':(500,140,True),'C5':(650,300,True),'C6':(650,140,True),'C7':(800,280,True),'R8':(1080,350,False),'C8':(980,290,True),'J7':(1350,340,False),'TP1':(1460,300,False),'H9':(1400,180,False)}
for ref,(x,y,v) in positions.items():comp(ref,x,y,v)
connect(pt('J1',1),pt('R1',1));connect(pt('R1',2),(350,660),pt('R3',1));connect((350,660),pt('R2',2));node((350,660));label('inm',(180,660));label('RG_DRIVE',(350,660));stub('R2',1,'GND')
connect(pt('R3',2),(550,660),pt('U1',3));connect((550,660),pt('R4',1));node((550,660));label('INV',(570,660));connect(pt('R4',2),pt('U1',1));label('FB',(660,740))
connect(pt('J2',1),(180,540),(180,600),pt('R6',1));connect(pt('R6',2),pt('U1',4));label('inpt_raw',(180,600));label('inpt',(580,600))
for ref in ['R5','R7']:
 pp=pt(ref,2);connect(pp,(pp[0],600));node((pp[0],600));stub(ref,1,'GND')
connect(pt('U1',10),pt('R14',1));connect(pt('U1',11),(960,630),(960,650));node((960,650));label('AMP_OUT',(940,650))
connect(pt('R14',2),pt('J3',1));connect(pt('R15',1),(1250,650));node((1250,650));label('output',(1220,650));stub('R15',2,'GND')
for ref in ['J1','J2','J3']:
 ps=[pt(ref,n) for n in range(2,6)];gy=ps[0][1]-10
 for pp in ps:wire(pp,(pp[0],gy))
 wire((ps[0][0],gy),(ps[-1][0],gy));label('GND',(ps[0][0],gy))
for n in ['2','5','6','7','8','9','12','13','14','15','16','17']:stub('U1',n,parts['U1']['nets'][n],70 if n=='6' else 45 if n in ['14','8'] else 25)
for ref in ['J4','J5','J6','J8']:stub(ref,1,parts[ref]['nets']['1'],15)
for l,y,raw,rail in [('L1',360,'VIN_P','VCC'),('L2',200,'VIN_N','VEE')]:
 connect((240,y),pt(l,1));label(raw,(240,y));connect(pt(l,2),(860,y));label(rail,(860,y))
for c,y in [('C1',360),('C2',200),('C3',360),('C4',200),('C5',360),('C6',200)]:
 pp=pt(c,1);connect(pp,(pp[0],y));node((pp[0],y));stub(c,2,'GND',15)
connect(pt('C7',1),(800,360));connect(pt('C7',2),(800,200));node((800,360));node((800,200))
connect((950,350),pt('R8',2));label('TJ_RAW',(950,350));connect(pt('C8',1),(980,350));node((980,350));connect(pt('R8',1),pt('J7',1));label('TEMP',(1190,350));stub('J7',2,'GND',15);stub('C8',2,'GND',15);stub('TP1',1,'GND');stub('H9',1,'GND')
notes=[('QSTL  |  THS3491 RGT  |  REV C',70,1020),('TI HSP006A RF geometry / RF=390 ohm / RG=20.5 ohm / gain=20.0244 V/V',70,980),('R2=0 fitted: non-inverting mode. Remove R2 before using J1; source impedance changes the gain.',70,940),('Output attenuator R9-R13 removed. R14=49.9 ohm series; R15=1 Mohm local load.',70,910),('JLC04161H-7628 / 4 layers / 41.656 x 68.58 mm / CPWG design W=0.3058 mm, G=0.20 mm',70,870),('SUPPLY FILTER AND LOCAL DECOUPLING',70,430),('TEMP HEADER / HIGH-IMPEDANCE MEASUREMENT',950,430),('J7: 1=TEMP, 2=GND; 2.54 mm pitch. Jumper leads only, no shorting cap.',950,90),('R5 DNP / R6=0 fitted / H9 grounded heatsink, bottom side.',70,70)]
for ss,x,y in notes:add(4,OwnerPartId=-1,FontID=1,Color=128,Text=ss,**{'Location.X':x,'Location.Y':y});txt(ss,x,y,20 if y==1020 else 13)
# Connectivity union: pin tips, wire intersections/endpoints and labels.
pts={p for p,d in pins.values()}|{p for a,b in wires for p in [a,b]}|{p for n,p in labels};parent={p:p for p in pts}
def find(p):
 while parent[p]!=p:parent[p]=parent[parent[p]];p=parent[p]
 return p
def join(a,b):parent[find(a)]=find(b)
def on(p,a,b):return abs((p[0]-a[0])*(b[1]-a[1])-(p[1]-a[1])*(b[0]-a[0]))<1e-8 and min(a[0],b[0])<=p[0]<=max(a[0],b[0]) and min(a[1],b[1])<=p[1]<=max(a[1],b[1])
for a,b in wires:
 for p in pts:
  if on(p,a,b):join(a,p)
named={}
for n,p in labels:named.setdefault(find(p),set()).add(n)
errors=[]
for key,(p,d) in pins.items():
 got=named.get(find(p),set())
 if got!={expected[key]}:errors.append((key,expected[key],list(got)))
(H/'review/schematic_connectivity.json').write_text(json.dumps(dict(pin_count=len(pins),errors=errors),indent=2));assert not errors,errors
R[0]['Weight']=str(len(R)-1)
def pack(rows):
 out=[]
 for r in rows:
  data=('|'+'|'.join(k+'='+str(v) for k,v in r.items())+'\0').encode('cp1252');out.extend([struct.pack('<I',len(data)),data])
 return b''.join(out)
template=Path(r'C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB.SchDoc')
out=H/'QSTL_THS3491_RGT_G20_RevC.SchDoc'
if out.exists():out.rename(H/'staging/previous.SchDoc') if not (H/'staging/previous.SchDoc').exists() else out.unlink()
update_copy(template,out,{'FileHeader':pack(R)})
(H/'review/schematic_native_records.json').write_text(json.dumps(R,indent=2))
(H/'review/schematic.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1100" viewBox="0 0 1600 1100"><rect width="1600" height="1100" fill="white"/><g font-family="Arial">'+''.join(SVG)+'</g></svg>')
(H/'QSTL_THS3491_RGT_G20_RevC.PrjPcb').write_text('[Design]\nVersion=1.0\n[Document1]\nDocumentPath=QSTL_THS3491_RGT_G20_RevC.SchDoc\n[Document2]\nDocumentPath=QSTL_THS3491_RGT_G20_RevC.PcbDoc\n')
print('Native SchDoc:',out,'verified pins:',len(pins))
