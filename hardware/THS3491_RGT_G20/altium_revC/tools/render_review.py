"""Review drawings from copper geometry; editable vector schematics, not photos."""
from pathlib import Path
import json, math, html
H=Path(__file__).resolve().parents[1];g=json.loads((H/'review/native_geometry.json').read_text())
colors={'GND':'#cbd5df','VCC':'#dd583f','VIN_P':'#ed9a73','VEE':'#3869bd','VIN_N':'#8eaee2','TEMP':'#b15ba8','TJ_RAW':'#b15ba8'}
def color(n):return colors.get(n,'#178b77')
def poly(ps):return 'M '+' L '.join(f'{x:.5f},{y:.5f}' for x,y in ps)+' Z '
def body(layer,labels=True):
 s=[f'<rect width="{g["board_width"]}" height="{g["board_height"]}" fill="#f8fafc" stroke="#26384b" stroke-width=".1"/>']
 for z in g['zones']:
  if z['layer']!=layer or z['keepout']:continue
  for f in z['filled']:s.append(f'<path d="{poly(f["outline"])+"".join(poly(h) for h in f["holes"])}" fill="{color(z["net"])}" fill-rule="evenodd"/>')
 for t in g['tracks']+g['arcs']:
  if t['layer']!=layer:continue
  a,e=t['start'],t['end'];d=f'M {a[0]},{a[1]} L {e[0]},{e[1]}'
  if 'radius' in t:d=f'M {a[0]},{a[1]} A {t["radius"]},{t["radius"]} 0 {int(abs(t["angle"])>180)} {int(t["angle"]>0)} {e[0]},{e[1]}'
  s.append(f'<path d="{d}" fill="none" stroke="{color(t["net"])}" stroke-width="{t["width"]}" stroke-linecap="round"/>')
 for p in g['pads']:
  x,y=p['pos'];w,h=p['size']
  if p['npth']:s.append(f'<circle cx="{x}" cy="{y}" r="{p["drill"][0]/2}" fill="white" stroke="#687b8b" stroke-width=".05"/>');continue
  if layer not in p['layers']:continue
  rad=min(w,h)*p['roundrect_ratio'] if p['shape']==4 else min(w,h)/2 if p['shape']==2 else 0
  if p['shape']==0:s.append(f'<circle cx="{x}" cy="{y}" r="{w/2}" fill="{color(p["net"])}" stroke="#c49f42" stroke-width=".06"/>')
  else:s.append(f'<rect x="{x-w/2}" y="{y-h/2}" width="{w}" height="{h}" rx="{rad}" transform="rotate({-p["angle"]} {x} {y})" fill="{color(p["net"])}" stroke="#c49f42" stroke-width=".06"/>')
  if p['drill'][0]:s.append(f'<circle cx="{x}" cy="{y}" r="{p["drill"][0]/2}" fill="white"/>')
 for v in g['vias']:
  x,y=v['pos'];s.append(f'<circle cx="{x}" cy="{y}" r="{v["diameter"]/2}" fill="{color(v["net"])}" stroke="#718191" stroke-width=".025"/><circle cx="{x}" cy="{y}" r="{v["drill"]/2}" fill="#f8fafc"/>')
 if labels:
  offsets={'U1':(0,0),'R1':(0,-1.1),'R2':(-.3,-1.1),'R3':(-1.1,0),'R4':(0,-1.3),'R5':(0,-1.2),'R6':(-1.2,0),'R7':(1.2,0),'R14':(0,-1.1),'R15':(1.6,.3),'C3':(0,-1),'C4':(0,1.4),'C5':(-1.2,-.3),'C6':(1.2,.3),'C7':(1.5,0),'C1':(1.6,0),'C2':(-1.7,0),'C8':(-1.5,0),'R8':(-1.6,0),'L1':(1.5,0),'L2':(-1.5,0),'J1':(2.5,-4),'J2':(2.5,4),'J3':(-2.5,-4),'J4':(0,-2.1),'J5':(0,-2.1),'J6':(0,2.7),'J8':(0,2.7),'J7':(1.2,2.5),'TP1':(0,2)}
  names={'J1':'J1 IN−','J2':'J2 IN+','J3':'J3 OUT','J4':'+15 V','J5':'GND','J6':'−15 V','J8':'GND','J7':'1:TEMP  2:GND'}
  for p in g['parts']:
   if p['ref'] not in offsets:continue
   dx,dy=offsets[p['ref']];x,y=p['pos'];s.append(f'<text x="{x+dx}" y="{y+dy}" font-size=".57" text-anchor="middle" fill="#203147" stroke="white" stroke-width=".12" paint-order="stroke">{html.escape(names.get(p["ref"],p["ref"]))}</text>')
 return ''.join(s)
def wrap(content,w,h):return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><rect width="100%" height="100%" fill="white"/><g font-family="Arial, sans-serif">{content}</g></svg>'
def txt(x,y,t,size=20,fill='#203147'):return f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}">{html.escape(t)}</text>'
s=txt(45,48,'QSTL THS3491 RGT · Rev C · L1',28)+txt(45,80,'TI RF coordinates and curved routes retained · 41.656 × 68.58 mm',17)
s+='<g transform="translate(45,110) scale(14)">'+body('F.Cu')+'</g>'
notes=[('Power path',150),('L1 entry island → via cluster',192),('→ L3 supply area → via cluster',224),('→ small L1 island at U1',256),('Opposite, symmetric ±15 V sections',320),('C1/C2, L1/L2, C3/C4, C5/C6',354),('C3/C5 close to U1',418),('Ground pads separated from power',450),('U1 pins 2, 5, 9, 12, 15 + EP: GND',514),('5 ground vias inside the exposed pad',546),('TEMP header J7',610),('2.54 mm pitch · pin 1 TEMP / pin 2 GND',642),('R8=0 Ω and C8=100 nF retained',674),('Jumper leads; do not fit a shorting cap',706),('JLC04161H-7628 design basis',770),('L1/L2 dielectric 0.2104 mm',802),('RF W=0.3058 mm / ground gap≈0.205 mm',834),('No field-solver SI/PI result claimed',866),('Native Altium application DRC pending',944)]
for t,y in notes:s+=txt(665,y,t,18)
for y,n in [(1010,'VCC'),(1040,'VEE'),(1070,'TEMP')]:s+=f'<rect x="665" y="{y-15}" width="20" height="18" fill="{color(n)}"/>'+txt(700,y,n,18)
(H/'review/layout_L1_annotated.svg').write_text(wrap(s,1140,1110),encoding='utf-8')
s=txt(35,45,'L1 core · actual copper, pad and via geometry',27)+'<svg x="35" y="80" width="1330" height="770" viewBox="12.7 22.5 14 10.9">'+body('F.Cu')+'</svg>'+txt(35,890,'Red: VCC · blue: VEE · grey: GND · green: RF · purple: TEMP',18)
(H/'review/layout_core_detail.svg').write_text(wrap(s,1400,930),encoding='utf-8')
s=txt(35,45,'L3 power areas · ground-via antipads included',27)+'<g transform="translate(35,80) scale(13)">'+body('In2.Cu',False)+'</g>'
(H/'review/layout_L3_power.svg').write_text(wrap(s,630,1010),encoding='utf-8')
# A precise schematic redrawing highlights the requested EVM resistors.
s=txt(45,45,'TI EVM output network — R9, R10 and R11 highlighted',27)+txt(45,76,'Redrawn from the TI HSP006A / SLOU483 schematic; original attenuator, not the modified board',17)
def wire(x,y,a,b):return f'<path d="M {x},{y} L {a},{b}" stroke="#25475d" stroke-width="3" fill="none"/>'
def ground(x,y):return wire(x,y,x,y+10)+wire(x-15,y+10,x+15,y+10)+wire(x-10,y+16,x+10,y+16)+wire(x-5,y+22,x+5,y+22)
def resistor(x,y,name,val,vertical=False,hi='#f5f7fa'):
 if vertical:return f'<rect x="{x-48}" y="{y-46}" width="96" height="112" rx="12" fill="{hi}"/>'+wire(x,y-40,x,y-20)+f'<rect x="{x-10}" y="{y-20}" width="20" height="40" fill="white" stroke="#25475d" stroke-width="2"/>'+wire(x,y+20,x,y+40)+txt(x+18,y-3,name,17)+txt(x+18,y+20,val,16)
 return f'<rect x="{x-60}" y="{y-50}" width="120" height="98" rx="12" fill="{hi}"/>'+wire(x-60,y,x-30,y)+f'<rect x="{x-30}" y="{y-10}" width="60" height="20" fill="white" stroke="#25475d" stroke-width="2"/>'+wire(x+30,y,x+60,y)+txt(x-27,y-25,name,18)+txt(x-27,y+35,val,17)
s+=f'<rect x="50" y="140" width="160" height="80" fill="#edf3f7" stroke="#25475d" stroke-width="2"/>'+txt(65,174,'THS3491',22)+txt(65,202,'OUT pins 10, 11',15)+wire(210,180,600,180)
s+=resistor(330,290,'R9','240 Ω',True,'#ffdfbb')+resistor(450,290,'R10','240 Ω',True,'#ffdfbb')+wire(330,180,330,250)+wire(450,180,450,250)+ground(330,330)+ground(450,330)
s+=resistor(660,180,'R11','287 Ω',False,'#fff0a9')+wire(720,180,790,180)+resistor(850,180,'R12','287 Ω')+wire(910,180,1150,180)
s+=resistor(970,290,'R13','54.9 Ω',True)+wire(970,180,970,250)+ground(970,330)+resistor(1150,290,'Load','50 Ω',True)+wire(1150,180,1150,250)+ground(1150,330)+txt(1050,145,'J3 → instrument',18)
for x in [330,450,970,1150]:s+=f'<circle cx="{x}" cy="180" r="5" fill="#25475d"/>'
s+=txt(50,410,'R9 || R10 = 120 Ω shunt load. Combined with the attenuator path, U1 sees ≈100 Ω.',20)
s+=txt(50,444,'R11 + R12 + (R13 || 50 Ω): VJ3 / VOUT ≈0.0436 (−27.2 dB). R3/R4 set amplifier gain.',20)
s+=wire(45,478,1230,478)+txt(45,520,'Modified board TEMP connection · J7, 2.54 mm pitch',27)
s+=f'<rect x="50" y="575" width="190" height="80" fill="#edf3f7" stroke="#25475d" stroke-width="2"/>'+txt(65,608,'U1 TEMP, pin 6',20)+txt(65,636,'Internal die sensor',16)+wire(240,610,600,610)+resistor(660,610,'R8','0 Ω')+wire(720,610,1050,610)
s+=wire(400,610,400,662)+wire(380,662,420,662)+wire(380,671,420,671)+wire(400,671,400,705)+ground(400,705)+txt(430,671,'C8  100 nF',18)+f'<circle cx="400" cy="610" r="5" fill="#25475d"/>'
s+=f'<rect x="1015" y="580" width="165" height="150" rx="10" fill="#f3eafa" stroke="#71517f" stroke-width="2"/><circle cx="1050" cy="610" r="9" fill="white" stroke="#71517f" stroke-width="3"/><circle cx="1050" cy="690" r="9" fill="white" stroke="#71517f" stroke-width="3"/>'+txt(1070,617,'1 TEMP',19)+txt(1070,697,'2 GND',19)+wire(1050,690,940,690)+ground(940,690)
s+=wire(1015,610,1041,610)
s+=txt(50,800,'Typical: 1.06 V at 25 °C, +3.2 mV/°C. High-impedance readout and calibration are needed.',20)+txt(50,834,'Tj ≈25 + (VTEMP − 1.06) / 0.0032 °C. This is a measurement output, not an enable pin.',20)+txt(50,868,'Connect a meter/ADC using jumper leads. Do not short header pins 1–2 with a jumper cap.',20)
(H/'review/EVM_R9_R10_R11_TEMP_explained.svg').write_text(wrap(s,1280,905),encoding='utf-8')
print('Rendered layout L1, core, L3 and EVM/TEMP schematic explanation')
