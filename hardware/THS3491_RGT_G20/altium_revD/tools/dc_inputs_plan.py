"""Two adapter-only DC inputs, preserving the existing RF board envelope."""
from pathlib import Path
import json,math
from shapely.geometry import Point,LineString
ROOT=Path(__file__).resolve().parents[1]
S=ROOT/'staging/dc_inputs_20261028'
g=json.loads((S/'review_before/intended_geometry.json').read_text())
removed={'J4','J5','J6','J8'}
specs=[dict(ref='J9',value='+15V DC',pattern='SameSky_PJ-102AH',pos=[16.5,13.7],angle=180.,net='VIN_P'),
       dict(ref='J10',value='-15V DC',pattern='SameSky_PJ-102AH',pos=[21.,54.88],angle=0.,net='VIN_N')]
for d in specs:d.update(mpn='PJ-102AH',manufacturer='Same Sky',jlc_part='',jlc_stock_verified=False,jlc_assembly_verified=False)
g['parts']=[p for p in g['parts'] if p['ref'] not in removed]
g['pads']=[p for p in g['pads'] if p['ref'] not in removed]
for d in specs:
 f={k:d[k] for k in ['ref','value','pattern','pos','angle']};f['layer']='F.Cu';g['parts'].append(f)
 sign=-1 if d['angle']==180 else 1;x,y=d['pos']
 for num,dx,dy,net in [(1,0,0,d['net']),(2,0,6,'GND'),(3,4.7,3,'')]:
  g['pads'].append(dict(ref=d['ref'],num=str(num),net=net,pos=[x+sign*dx,y+sign*dy],size=[2.6,2.6],drill=[1.6,1.6],angle=0.,shape=1 if num==1 else 0,roundrect_ratio=0.,layers=['F.Cu','In1.Cu','In2.Cu','B.Cu','F.Mask','B.Mask'],connection=1,npth=False))
routes=[('VIN_P',[[16.5,13.7],[20.5,13.7],[20.5,6.9]]),('VIN_N',[[21,54.88],[17,54.88],[17,49]])]
added=[dict(net=net,start=a,end=b,width=1.,layer='F.Cu') for net,ps in routes for a,b in zip(ps,ps[1:])]
g['tracks'].extend(added)
newpads=[p for p in g['pads'] if p['ref'] in {'J9','J10'}]
removed_vias=[];kept=[]
for v in g['vias']:
 hit=any(math.dist(v['pos'],p['pos'])<p['size'][0]/2+v['diameter']/2+.25 for p in newpads)
 hit=hit or any(t['net']!=v['net'] and LineString([t['start'],t['end']]).distance(Point(v['pos']))<t['width']/2+v['diameter']/2+.25 for t in added)
 if hit:
  assert v['net']=='GND';removed_vias.append(v)
 else:kept.append(v)
g['vias']=kept
silk=[('+15V DC',[11.8,16.2],.85),('CENTER +15V',[11.8,17.5],.65),('SHELL GND',[11.8,18.6],.65),
      ('-15V DC',[16.3,51.9],.85),('CENTER -15V',[27.5,66.1],.65),('SHELL GND',[27.5,67.2],.65)]
intent=dict(date='2026-10-28',mode='DC adapters only; banana sockets cancelled by user',connectors=specs,removed_components=sorted(removed),added_tracks=added,removed_ground_vias=removed_vias,
 silk=[dict(text=t,pos=p,height=h) for t,p,h in silk],mechanical_outline_tracks=12,
 topology='J9 feeds VIN_P before L1; J10 feeds VIN_N before L2; both sleeves connect to GND. No power conversion.',
 polarity={'J9':{'1':'VIN_P (+15V)','2':'GND','3':'NC (sleeve switch)'},'J10':{'1':'VIN_N (-15V)','2':'GND','3':'NC (sleeve switch)'}},
 connector_rating='PJ-102AH: 24 VDC, 5 A; 2.0 mm center pin, for 5.5/2.1 mm mating plug',
 sourcing_note='Manufacturer MPN specified for manual THT assembly. C9900001188 is an assembly-service catalog entry, not evidence of stocked Same Sky parts.',
 preserved=['41.65601 x 68.58 mm outline','four mounting holes','RF parts/pads/tracks/arcs','input filters and rectangular islands','L2 RF-pad cutouts','VCC/VEE entry via arrays'],
 sources={'barrel':'https://www.sameskydevices.com/product/resource/pj-102ah.pdf'})
(S/'intent.json').write_text(json.dumps(intent,indent=2))
(S/'geometry.json').write_text(json.dumps(g,indent=2))
print('DC-only plan:',len(g['parts']),'parts,',len(g['pads']),'pads;',len(removed_vias),'overlapping GND vias removed')
