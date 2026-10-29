"""Dual power entry: preserve the two existing rail/GND inputs and RF layout."""
from pathlib import Path
import copy,json,math
from shapely.geometry import Point,LineString

ROOT=Path(__file__).resolve().parents[1]
S=ROOT/'staging/power_connectors_jlc_20261028'
raise SystemExit('Superseded: user cancelled banana sockets. Use dc_inputs_plan.py for the two DC inputs.')
g=json.loads((S/'review_before/intended_geometry.json').read_text())
old=copy.deepcopy(g)
specs=[
 dict(ref='J4',value='+15V BANANA',pattern='Keystone_575_6',pos=[34.,13.],angle=0.,net='VIN_P'),
 dict(ref='J5',value='GND BANANA',pattern='Keystone_575_6',pos=[5.,12.1],angle=0.,net='GND'),
 dict(ref='J6',value='-15V BANANA',pattern='Keystone_575_6',pos=[8.,57.5],angle=0.,net='VIN_N'),
 dict(ref='J8',value='GND BANANA',pattern='Keystone_575_6',pos=[33.,57.5],angle=0.,net='GND'),
 dict(ref='J9',value='+15V DC',pattern='SameSky_PJ-102AH',pos=[16.5,13.7],angle=180.,net='VIN_P'),
 dict(ref='J10',value='-15V DC',pattern='SameSky_PJ-102AH',pos=[21.,54.88],angle=0.,net='VIN_N')]
for d in specs:
 d.update(mpn='575-6' if 'BANANA' in d['value'] else 'PJ-102AH', manufacturer='Keystone' if 'BANANA' in d['value'] else 'Same Sky', jlc_part='C4993646' if 'BANANA' in d['value'] else '', jlc_stock_verified=False, jlc_assembly_verified=False)
refs={d['ref'] for d in specs}
parts={d['ref']:d for d in g['parts']}
g['pads']=[p for p in g['pads'] if p['ref'] not in refs]
def pad(ref,num,net,pos,size,drill,shape=0):
 return dict(ref=ref,num=str(num),net=net,pos=pos,size=size,angle=0.,drill=[drill,drill],shape=shape,roundrect_ratio=0.,layers=['F.Cu','In1.Cu','In2.Cu','B.Cu','F.Mask','B.Mask'],connection=1,npth=False)
for d in specs:
 f={k:d[k] for k in ['ref','value','pattern','pos','angle']};f['layer']='F.Cu'
 if d['ref'] in parts:parts[d['ref']].update(f)
 else:g['parts'].append(f)
 if d['pattern']=='Keystone_575_6':g['pads'].append(pad(d['ref'],1,d['net'],d['pos'],[8.3,8.3],5.35))
 else:
  sign=-1 if d['angle']==180 else 1;x,y=d['pos']
  for num,dx,dy,net in [(1,0,0,d['net']),(2,0,6,'GND'),(3,4.7,3,'')]:
   g['pads'].append(pad(d['ref'],num,net,[x+sign*dx,y+sign*dy],[2.6,2.6],1.6,1 if num==1 else 0))
routes=[('VIN_P',[[16.5,13.7],[20.5,13.7],[20.5,6.9]]),
        ('VIN_P',[[34,13],[31,13],[31,6.9],[27,6.9]]),
        ('VIN_N',[[21,54.88],[17,54.88],[17,49]]),
        ('VIN_N',[[8,57.5],[13,57.5],[17,54.88]])]
added=[]
for net,ps in routes:
 for a,b in zip(ps,ps[1:]):added.append(dict(net=net,start=a,end=b,width=1.,layer='F.Cu'))
g['tracks'].extend(added)
# Remove only ground stitching vias whose annulus/drill intersects new input
# hardware or a new raw-supply track. Filtered supply arrays stay untouched.
newpads=[p for p in g['pads'] if p['ref'] in refs]
removed=[];kept=[]
for v in g['vias']:
 hit=any(math.dist(v['pos'],p['pos'])<p['size'][0]/2+v['diameter']/2+.25 for p in newpads)
 hit=hit or any(t['net']!=v['net'] and LineString([t['start'],t['end']]).distance(Point(v['pos']))<t['width']/2+v['diameter']/2+.25 for t in added)
 if hit:
  assert v['net']=='GND',('Cannot remove filtered via',v)
  removed.append(v)
 else:kept.append(v)
g['vias']=kept
silk=[
 ('+15V',[31.3,18.4],1.15),('GND',[.8,7.7],.85),
 ('-15V',[1.,52.7],1.0),('GND',[30.7,52.7],1.0),
 ('+15V DC',[11.8,16.2],.85),('CTR +15V',[11.8,17.5],.65),('SHELL GND',[11.8,18.6],.65),
 ('-15V DC',[16.3,51.9],.85),('CTR -15V',[27.5,66.1],.65),('SHELL GND',[27.5,67.2],.65),
 ('DC OR BANANA',[22.2,2.],.65),('ONE SOURCE / RAIL',[3.,67.8],.65)]
intent=dict(date='2026-10-28',connectors=specs,added_tracks=added,removed_ground_vias=removed,
 silk=[dict(text=t,pos=p,height=h) for t,p,h in silk],
 topology='Each barrel jack parallels its existing raw-input banana pair. Use one source per rail.',
 polarity={'J9':{'1':'VIN_P (+15V)','2':'GND','3':'NC (sleeve switch)'},'J10':{'1':'VIN_N (-15V)','2':'GND','3':'NC (sleeve switch)'}},
 banana_mount='575-6: 5.1562 mm body through 5.35 mm plated hole; 7.9248 mm flange, 2.3622 mm above top. Shank extends 6.731 mm below PCB top. Through-hole solder assembly; mechanical retention/PCBA process requires supplier review.',
 preserved=['board outline','four mounting holes','RF parts/pads/tracks/arcs','input filters and rectangular islands','L2 RF-pad cutouts','VCC/VEE entry via arrays'],
 sources={'barrel':'https://www.sameskydevices.com/product/resource/pj-102ah.pdf','banana':'https://www.keyelco.com/userAssets/file/K75p119.pdf','banana_drawing':'https://www.keyelco.com/product-pdf.cfm?p=2381'})
(S/'intent.json').write_text(json.dumps(intent,indent=2))
(S/'geometry.json').write_text(json.dumps(g,indent=2))
print('Plan:',len(g['parts']),'parts,',len(g['pads']),'pads;',len(removed),'overlapping GND vias removed')
