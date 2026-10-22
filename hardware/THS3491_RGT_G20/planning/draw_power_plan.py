"""Planning illustrations only. Never writes CAD or modifies Rev C geometry."""
from pathlib import Path
import json,copy,math,html
H=Path(__file__).resolve().parent
source=H.parent/'altium_revC/review/native_geometry.json'
g=copy.deepcopy(json.loads(source.read_text()));U=(18.79601,27.94)
moves={'C3':(26.79701,11.53539,-90),'C4':(10.79501,44.34461,90),'C5':(19.29601,24.19683,90),'C6':(19.3908,31.68317,-90)}
for f in g['parts']:
 if f['ref'] not in moves:continue
 nx,ny,ang=moves[f['ref']];ox,oy=f['pos'];da=ang-f['angle'];r=math.radians(da)
 for q in g['pads']:
  if q['ref']!=f['ref']:continue
  dx,dy=q['pos'][0]-ox,q['pos'][1]-oy
  q['pos']=[nx+dx*math.cos(r)+dy*math.sin(r),ny-dx*math.sin(r)+dy*math.cos(r)];q['angle']+=da
 f['pos']=[nx,ny];f['angle']=ang
colors={'GND':'#d5dee4','VCC':'#d86243','VEE':'#346fce','VIN_P':'#f3c0aa','VIN_N':'#f3c0aa','TEMP':'#a95a9f','TJ_RAW':'#a95a9f'}
def col(n):return colors.get(n,'#15836f')
def box(x,y,w,h):return [(x,y),(x+w,y),(x+w,y+h),(x,y+h)]
def mirror(ps):return [(2*U[0]-x,2*U[1]-y) for x,y in ps]
rawminus=box(9.5,48.2,11.2,4.35)
entryminus=box(9.5,44.48,2.5,3.0)
islands=[('VIN_N',rawminus),('VIN_P',mirror(rawminus)),('VEE',entryminus),('VCC',mirror(entryminus)),('VEE',box(18.9,29.0,1.35,2.55)),('VCC',box(18.9,24.33,1.35,2.55)),('VCC',box(24.35,30.3,1.10,0.9)),('VEE',box(24.35,31.8,1.10,1.1))]
# C5 uses the same narrow, supply-pin-only island shape as C6.
# PD is an independent thin trace to a VCC via, outside that island.
pd_path=[(18.04601,26.54),(18.04601,25.70),(17.75,25.40)]
pd_via=pd_path[-1]
vias=[]
def v(n,x,y):vias.append((n,x,y))
for q in g['pads']:
 if q['ref'] in ['C1','C2','C3','C4','C5','C6','C7','L1','L2'] and q['net'] in ['GND','VCC','VEE']:v(q['net'],*q['pos'])
for x in [10.1,10.82,11.54]:
 for y in [45.85,46.45]:v('VEE',x,y);v('VCC',2*U[0]-x,2*U[1]-y)
for x,y in [(19.2,30.0),(19.85,30.0),(19.85,30.6)]:v('VEE',x,y)
for x,y in [(19.2,25.88),(19.85,25.88),(19.85,25.28)]:v('VCC',x,y)
v('VCC',*pd_via)
for dx,dy in [(0,0),(-.45,-.45),(.45,-.45),(-.45,.45),(.45,.45)]:v('GND',U[0]+dx,U[1]+dy)
def polygon(ps):return 'M '+' L '.join(f'{x:.5f},{y:.5f}' for x,y in ps)+' Z'
def text(x,y,t,size=.68,anchor='start',fill='#20364b'):
 return f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{size}" fill="{fill}" stroke="white" stroke-width="{size*.17}" paint-order="stroke">{html.escape(t)}</text>'
def line(ps,n,width=.25,white=False,dash=False):
 d='M '+' L '.join(f'{x},{y}' for x,y in ps)
 return f'<path d="{d}" fill="none" stroke="{"white" if white else col(n)}" stroke-width="{width}" stroke-linejoin="round" stroke-linecap="round"'+(' stroke-dasharray=".6 .4"' if dash else '')+'/>'
def pad(q,clearance=False):
 x,y=q['pos'];w,h=q['size'];hole=q['drill'][0]
 if q['npth']:return '' if clearance else f'<circle cx="{x}" cy="{y}" r="{hole/2}" fill="white" stroke="#82919e" stroke-width=".06"/>'
 if 'F.Cu' not in q['layers']:return ''
 def shape(fill,stroke,sw):
  if q['shape']==0:return f'<circle cx="{x}" cy="{y}" r="{w/2}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
  return f'<rect x="{x-w/2}" y="{y-h/2}" width="{w}" height="{h}" rx="{min(w,h)*.12}" transform="rotate({-q["angle"]} {x} {y})" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
 if clearance:
  if q['ref']=='U1' and q['num']=='16':return shape('white','white',.38)
  if q['net'] in ['VCC','VEE','VIN_P','VIN_N','GND']:return ''
  return shape('white','white',.38)
 s=shape(col(q['net']),'#bca05b',.045)
 if hole:s+=f'<circle cx="{x}" cy="{y}" r="{hole/2}" fill="white"/>'
 return s
def body(mode='L1',core=False,labels=True):
 s=f'<rect width="41.65601" height="68.58" fill="{col("GND") if mode=="L1" else "#e7edf1"}" stroke="#536778" stroke-width=".09"/>'
 if mode=='L1':
  for net,ps in islands:s+=f'<path d="{polygon(ps)}" fill="{col(net)}" stroke="white" stroke-width=".16"/>'
  for q in g['pads']:s+=pad(q,True)
  s+=f'<circle cx="{pd_via[0]}" cy="{pd_via[1]}" r=".38" fill="white"/>'
  # Read-only use of original RF centerlines; TEMP is a proposed escape route.
  trace_shapes=[]
  for t in g['tracks']+g['arcs']:
   if t['net'] in ['TEMP','TJ_RAW'] or t['layer']!='F.Cu':continue
   a,e=t['start'],t['end'];d=f'M {a[0]},{a[1]} L {e[0]},{e[1]}'
   if 'radius' in t:d=f'M {a[0]},{a[1]} A {t["radius"]},{t["radius"]} 0 0 {int(t["angle"]>0)} {e[0]},{e[1]}'
   trace_shapes.append((d,t['net'],t['width']))
  paths=[[(18.54601,29.34),(18.54601,33.1),(22.6,36.9),(22.6,37.5)],[(22.6,37.5),(22.6,39.3),(23.1,39.3)],[(23.1,40.7),(25.4,43),(34,43),(35,44)]]
  for ps in paths:trace_shapes.append(('M '+' L '.join(f'{x},{y}' for x,y in ps),'TJ_RAW',.2))
  trace_shapes.append(('M '+' L '.join(f'{x},{y}' for x,y in pd_path),'VCC',.15))
  for white in [True,False]:
   for d,net,width in trace_shapes:
    # Ground copper merges into the surrounding ground pour, including NC15.
    if white and net=='GND':continue
    s+=f'<path d="{d}" fill="none" stroke="{"white" if white else col(net)}" stroke-width="{width+.35 if white else width}" stroke-linecap="round" stroke-linejoin="round"/>'
  for q in g['pads']:s+=pad(q)
 else:
  # Large connected areas, not long narrow tracks. Final antipads are not drawn.
  pp=[(.3,.3),(41.356,.3),(41.356,27.59),(25.9,27.59),(25.9,31.4),(23.8,31.4),(23.8,27.59),(.3,27.59)]
  nn=[(.3,28.29),(23.1,28.29),(23.1,32.1),(26.6,32.1),(26.6,28.29),(41.356,28.29),(41.356,68.28),(.3,68.28)]
  for net,ps in [('VCC',pp),('VEE',nn)]:s+=f'<path d="{polygon(ps)}" fill="{col(net)}" fill-opacity=".7"/>'
  # L1 islands are projected as dashed outlines only, not L3 raw supply copper.
  for net,ps in islands:
   s+=f'<path d="{polygon(ps)}" fill="none" stroke="#334d64" stroke-width=".10" stroke-dasharray=".35 .22"/>'
  for q in g['pads']:
   if q['npth']:s+=pad(q)
   elif q['ref'] in ['J4','J5','J6','J8','J7'] and q['drill'][0]:
    x,y=q['pos'];s+=f'<circle cx="{x}" cy="{y}" r="{max(q["size"])/2+.2}" fill="#edf1f4"/><circle cx="{x}" cy="{y}" r="{q["drill"][0]/2}" fill="white"/>'
  for q in g['pads']:
   if q['ref']=='U1':
    x,y=q['pos'];s+=f'<circle cx="{x}" cy="{y}" r=".09" fill="#263d55"/>'
 for net,x,y in vias:
  if mode=='L3' and net=='GND':
   s+=f'<circle cx="{x}" cy="{y}" r=".40" fill="#edf1f4"/>'
  edge=col(net) if (x,y)==pd_via else 'white'
  s+=f'<circle cx="{x}" cy="{y}" r=".20" fill="{col(net)}" stroke="{edge}" stroke-width=".045"/><circle cx="{x}" cy="{y}" r=".08" fill="white"/>'
 if mode=='L1' and labels:
  offsets={'U1':(0,0),'R1':(0,-1),'R2':(-.7,-1),'R3':(-1.2,0),'R4':(0,-1.3),'R6':(-1.3,0),'R7':(1.3,0),'R14':(0,-1.1),'C3':(2,0),'C4':(-1.9,0),'C5':(1.4,0),'C6':(1.4,0),'C1':(2,0),'C2':(-1.9,0),'L1':(1.6,0),'L2':(-1.6,0),'C7':(1.5,0)}
  for f in g['parts']:
   if f['ref'] in offsets:
    dx,dy=offsets[f['ref']];x,y=f['pos'];s+=text(x+dx,y+dy,f['ref'],.58,'middle')
  for x,y,txt in [(18.66901,4.4,'+15 V'),(14.66901,4.4,'GND'),(18.92301,52.4,'−15 V'),(22.92301,51.6,'GND'),(36.2,46.6,'TEMP / GND')]:s+=text(x,y,txt,.65,'middle')
 elif mode=='L3':
  s+=text(30,17,'VCC  +15 V',1.25,'middle')+text(30,55,'VEE  −15 V',1.25,'middle')
 return s
def wrap(content,w,h):return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><rect width="100%" height="100%" fill="white"/><g font-family="Malgun Gothic, Arial, sans-serif">{content}</g></svg>'
def t(x,y,s,size=21,fill='#20364b'):return f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}">{html.escape(s)}</text>'
s=t(45,48,'수정 계획 · L1 배치와 국부 전원 면',31)+t(45,85,'C5/C6는 TI EVM 원위치·방향 / C3/C4는 입력 필터 측 / CAD 미변경',20)
s+='<g transform="translate(45,115) scale(15.5)">'+body('L1')+'</g>'
notes=[('① U1 근처에는 C5 / C6',165),('각 100 nF, TI 원본 좌표·회전 유지',203),('C3 / C4 (1 µF)는 근접 영역에서 이동',241),('② 입력 측 작은 L1 면',329),('−15 V 입력 + C2 + L2 입력 패드',367),('사용자 표시의 빨간 영역에 해당',405),('③ 필터 후 작은 L1 면',493),('L2 출력 + C4 전원 패드 + 비아 군',531),('비아들을 하나의 면 안에 모음',569),('④ U1 직전 작은 L1 면',657),('C5 쪽도 C6처럼 전원 핀만 포함',695),('각 GND 패드는 전원 면 밖에 둠',733),('입력부 ↔ U1 사이 공급은 L3 면',821),('PD16: 가는 L1 배선 → 비아 → L3 VCC',859),('NC15: 주변 L1 GND 면에 직접 연결',897),('±전원 입력부는 대칭',971),('C5/C6는 대칭보다 EVM 원위치 우선',1009),('전원 연결 의도를 표현한 계획도',1081),('최종 면 경계·간격·비아 수는 미확정',1119)]
for a,y in notes:s+=t(735,y,a,21 if a[0] in '①②③④' else 19)
(H/'power_plan_L1.svg').write_text(wrap(s,1210,1230),encoding='utf-8')
s=t(40,48,'수정 계획 · C5 전원 면도 C6와 같은 방식',30)+t(40,83,'PD16: 별도 배선 + 비아 / NC15: 주변 GND 면 / VS+13·14: C5 국부 전원 면',20)
s+='<svg x="45" y="115" width="1120" height="800" viewBox="13.3 22.0 12.5 12.8">'+body('L1',True)+'</svg>'
s+=t(55,960,'C5/C6 중심·회전은 TI HSP006A에서 직접 읽은 값. 색면·비아는 연결 의도 표시.',19)
(H/'power_plan_core.svg').write_text(wrap(s,1210,1000),encoding='utf-8')
# Detailed pin identification without scaling or relocating any component.
s=t(40,48,'C5 쪽 수정 · C6와 같은 전원 면 구성',31)+t(40,86,'배치·연결 계획도 / Altium 및 CAD 파일 미변경',20)
detail=body('L1',True,False)
detail+=text(20.0,24.15,'C5',.30,'middle')
detail+=text(20.0,24.46,'100 nF',.19,'middle')
detail+=text(17.2,23.55,'L1 GND',.23,'middle')
for x,label in [(18.04601,'16'),(18.54601,'15'),(19.04601,'14'),(19.54601,'13')]:
 detail+=text(x,27.08,label,.19,'middle')
for x,label in [(18.04601,'PD'),(18.54601,'NC'),(19.29601,'VS+')]:
 detail+=text(x,27.37,label,.19,'middle')
s+='<svg x="40" y="130" width="790" height="650" viewBox="16.7 23.1 5.3 4.6">'+detail+'</svg>'
s+=t(870,180,'① C5 + VS+ 13·14',25,'#ba4d31')
s+=t(870,219,'C6 쪽과 같은 폭의 작은 L1 면',19)
s+=t(870,254,'C5 전원 패드와 비아 군을 포함',19)
s+=t(870,289,'비아 군 → L3 VCC',19)
s+=t(870,365,'② PD 16',25,'#ba4d31')
s+=t(870,404,'가는 배선 → 별도 비아',19)
s+=t(870,439,'→ L3 VCC',19)
s+=t(870,515,'③ NC 15',25)
s+=t(870,554,'주변 L1 GND 면에 연결',19)
s+=t(870,589,'PD 배선과 VS+ 면 사이',19)
s+=t(870,624,'GND 연결 통로 유지',19)
s+=t(48,835,'회색: L1 GND   /   빨강: VCC   /   흰색: 구리 이격   /   원: 비아',21)
s+=t(48,879,'C5의 GND 패드는 전원 면 밖에 유지. C5/C6 위치·방향은 TI EVM 기준 유지.',20)
s+=t(48,921,'전원 면과 연결 경로의 의도 표시이며, 제조용 치수·DRC 확정 도면은 아닙니다.',18)
(H/'power_plan_PD_NC.svg').write_text(wrap(s,1320,950),encoding='utf-8')
s=t(45,48,'수정 계획 · L3 전원 면',31)+t(45,85,'상면 투영 기준 / 색면은 L3 / 점선은 L1 국부 면의 위치',20)
s+='<g transform="translate(45,115) scale(15.5)">'+body('L3')+'</g>'
notes=[('VCC / VEE를 넓은 면으로 분배',165),('빨강: +15 V 필터 후 전원',207),('파랑: −15 V 필터 후 전원',249),('입력 측 경로',343),('J6 → L1 VIN_N 면 → L2',385),('→ L1 VEE 면의 비아 군 → L3 VEE',427),('소자 측 경로',521),('L3 → 비아 군 → C5/C6 국부 면',563),('→ VS+ 13·14 / VS− 7·8',605),('PD16은 별도 비아로 L3 VCC 연결',647),('층 구성',741),('L1: RF + 국부 전원 면 + GND',783),('L2: GND 기준 면',825),('L3: VCC / VEE 전원 면',867),('L4: GND / 방열',909),('전원 면과 다른 net의 관통 비아는',1013),('L3에서 antipad로 이격',1051),('전체 antipad·최종 간격은 아직 미반영',1105)]
for a,y in notes:s+=t(735,y,a,20)
(H/'power_plan_L3.svg').write_text(wrap(s,1210,1230),encoding='utf-8')
record={'status':'PLAN ONLY; no Altium execution or CAD writes','source':str(source),'C5_TI_original':moves['C5'],'C6_TI_original':moves['C6'],'C3_filter_side':moves['C3'],'C4_filter_side':moves['C4'],'PD16':{'net':'VCC','L1_trace':pd_path,'via_to':'L3 VCC','via':pd_via},'NC15':'Directly joined to surrounding L1 GND; no enclosing supply island','VSplus13_14':'C5 local island has the same dimensions as C6 island; PD16 excluded','notes':['C5/C6 exact TI positions take priority over 180-degree symmetry at U1.','Input power blocks and C3/C4 remain 180-degree symmetric.','Copper outlines and via positions are illustrative, not DRC-validated.']}
(H/'power_plan_intent.json').write_text(json.dumps(record,indent=2))
print('Saved four planning drawings. CAD documents unchanged.')
