"""Dimensioned DC input review from saved native geometry, not an app screenshot."""
from pathlib import Path
import json,math,struct
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle,Circle
from matplotlib.transforms import Affine2D
import olefile
from render_review import polygon,color
from native_update import parse,blocks
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'review';S=ROOT/'staging/dc_inputs_20261028'
g=json.loads((R/'native_geometry.json').read_text());dc=json.loads((ROOT/'dc_inputs_intent.json').read_text())
fill=json.loads((R/'native_import_copper.json').read_text())
fig,(ax,info)=plt.subplots(1,2,figsize=(10,10),gridspec_kw={'width_ratios':[1.25,1]})
for f in fill:
    if f['layer']=='F.Cu':polygon(ax,f)
for t in g['tracks']:
    if t['layer']=='F.Cu':ax.plot(*zip(t['start'],t['end']),color=color(t['net']),lw=max(.4,t['width']*7),solid_capstyle='round')
for q in g['pads']:
    if 'F.Cu' not in q['layers']:continue
    x,y=q['pos'];w,h=q['size']
    p=Circle((x,y),w/2) if q['shape']==0 else Rectangle((x-w/2,y-h/2),w,h)
    p.set_transform(Affine2D().rotate_deg_around(x,y,-q['angle'])+ax.transData)
    p.set_facecolor('#d4ad4e');p.set_edgecolor('#826527');p.set_linewidth(.35);ax.add_patch(p)
    if q['drill'][0]:ax.add_patch(Circle((x,y),q['drill'][0]/2,color='white',lw=0))
for v in g['vias']:ax.add_patch(Circle(v['pos'],v['drill']/2,color='#6c7880',lw=0))
for r in dc['connectors']:
    x,y=r['pos'];top=y-.7 if r['angle']==0 else y-13.7
    ax.add_patch(Rectangle((x-4.5,top),9,14.4,fc='#27333c33',ec='#152632',lw=1.6))
    ax.text(x,top+5.2,r['ref']+'\nPJ-102AH',ha='center',va='center',fontsize=8,weight='bold',color='#142e45')
    mouth=68.58 if r['ref']=='J10' else 0
    ax.plot([x-4.5,x+4.5],[mouth,mouth],color='#111827',lw=4)
for t in dc['silk']:ax.text(*t['pos'],t['text'],fontsize=5.8,color='#112734',va='bottom')
ax.add_patch(Rectangle((0,0),g['board_width'],g['board_height'],fc='none',ec='#142e45',lw=1.1))
ax.set(xlim=(-1,42.65),ylim=(69.58,-1),aspect='equal',xlabel='x (mm)',ylabel='y from top (mm)')
ax.set_title('Saved PCB / top view',weight='bold',pad=14)
info.axis('off')
info.text(.02,.97,'Adapter inputs only',fontsize=19,weight='bold',va='top')
info.text(.02,.88,'J9  +15V input\nCenter: +15V (VIN_P)\nSleeve: GND\nMating direction: top edge',fontsize=12,linespacing=1.6,va='top')
info.text(.02,.65,'J10  -15V input\nCenter: -15V (VIN_N)\nSleeve: GND\nMating direction: bottom edge',fontsize=12,linespacing=1.6,va='top')
info.text(.02,.41,'Same Sky PJ-102AH\n5.5 / 2.1 mm mating plug\n24 VDC / 5 A connector rating\nPin 3: unused sleeve switch',fontsize=11,linespacing=1.6,va='top')
info.text(.02,.20,'PCB: 41.656 x 68.580 mm\nMounting holes unchanged\nNo banana sockets\nNo voltage / polarity conversion',fontsize=11,linespacing=1.6,va='top')
fig.text(.07,.025,'Native copper and nominal body outlines re-rendered for review; not an Altium screenshot.',fontsize=8,color='#536675')
fig.tight_layout(rect=(0,.04,1,1));fig.savefig(R/'dc_input_layout.png',dpi=180);plt.close(fig)

# Draw the changed schematic area from the actual saved native records.
schematic=S/'assembly.SchDoc'
with olefile.OleFileIO(schematic) as o:rs=[{k.upper():v for k,v in parse(b).items()} for b in blocks(o.openstream('FileHeader').read())]
fig,ax=plt.subplots(figsize=(12,8))
for q in rs:
    if q.get('ISHIDDEN')=='T':continue
    typ=q.get('RECORD');x=float(q.get('LOCATION.X',0));y=float(q.get('LOCATION.Y',0))
    if typ in ['27','6'] and 'LOCATIONCOUNT' in q:
        xy=[(float(q.get('X'+str(i),0)),float(q.get('Y'+str(i),0))) for i in range(1,int(q['LOCATIONCOUNT'])+1)]
        ax.plot(*zip(*xy),color='#233e73' if typ=='27' else '#6b301f',lw=1)
    elif typ=='14':
        cx=float(q.get('CORNER.X',x));cy=float(q.get('CORNER.Y',y))
        ax.add_patch(Rectangle((min(x,cx),min(y,cy)),abs(cx-x),abs(cy-y),fc='#fff6df',ec='#783b2b',lw=1,zorder=1))
    elif typ=='2':
        length=float(q.get('PINLENGTH',0));ori=int(q.get('PINCONGLOMERATE',0))&3
        dx,dy=[(1,0),(0,1),(-1,0),(0,-1)][ori];ex=x+dx*length;ey=y+dy*length
        ax.plot([x,ex],[y,ey],color='#6b301f',lw=1,zorder=2)
        if 0<x<500 and 70<y<420:
            ax.text((x+ex)/2,(y+ey)/2+4,q.get('DESIGNATOR',''),ha='center',fontsize=7,zorder=4)
            if q.get('NAME'):ax.text(x-dx*5,y-dy*5,q['NAME'],ha='right' if dx>0 else 'left',va='center',fontsize=8,zorder=4)
    elif typ in ['4','25','34','41'] and 0<x<500 and 70<y<420:
        ax.text(x,y,q.get('TEXT',''),fontsize=8,va='bottom',color='#233e73',zorder=4)
    elif typ=='29':ax.add_patch(Circle((x,y),2,color='#233e73'))
ax.set(xlim=(0,510),ylim=(75,415),aspect='equal');ax.axis('off')
ax.set_title('Saved schematic: DC jacks and existing input filters',fontsize=15,weight='bold')
fig.text(.08,.045,'Re-rendered native schematic geometry. Pin 3 is intentionally unconnected. Not an Altium screenshot.',fontsize=9)
fig.savefig(R/'dc_input_schematic.png',dpi=160);plt.close(fig)
print('Wrote DC placement and schematic review figures')
