"""Render individual copper layers and a same-orientation four-layer gallery."""
import hashlib,json,math
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Circle,Rectangle,Polygon as Patch
from matplotlib.transforms import Affine2D
from shapely.geometry import LineString,box
import numpy as np
import render_review as src
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'review';OUT=R/'layers';OUT.mkdir(exist_ok=True)
pcb=ROOT/'QSTL_THS3491_RGT_G20_RevD.PcbDoc'
digest=hashlib.sha256(pcb.read_bytes()).hexdigest()
assert digest==json.loads((R/'native_import_check.json').read_text())['source_sha256']
g=src.g
src.colors['']='#a69a8e'
layers=[('L1','F.Cu','TOP / signals and power'),('L2','In1.Cu','GROUND / RF resistor windows'),('L3','In2.Cu','POWER + GND'),('L4','B.Cu','BOTTOM / GND')]

def draw(ax,layer):
    ax.set_facecolor('#fafbfc')
    for f in src.fill:
        if f['layer']==layer:src.polygon(ax,f)
    for t in g['tracks']+g['arcs']:
        if t['layer']!=layer:continue
        if 'radius' in t:
            cx,cy=t['center'];a=math.atan2(t['start'][1]-cy,t['start'][0]-cx)
            angles=np.linspace(a,a+math.radians(t['angle']),max(120,math.ceil(abs(t['angle'])*4)))
            points=list(zip(cx+t['radius']*np.cos(angles),cy+t['radius']*np.sin(angles)))
        else:points=[t['start'],t['end']]
        poly=LineString(points).buffer(t['width']/2,resolution=32)
        ax.add_patch(Patch(list(poly.exterior.coords),fc=src.color(t['net']),ec='none'))
    drilled=[]
    for p in g['pads']:
        x,y=p['pos'];w,h=p['size']
        if not p['npth'] and layer in p['layers']:
            if p['shape']==0:q=Circle((x,y),w/2)
            elif p['shape']==4:
                r=src.native_shapes[p['ref'],p['num']]['radius_mm']
                poly=box(x-w/2+r,y-h/2+r,x+w/2-r,y+h/2-r).buffer(r,resolution=24)
                q=Patch(list(poly.exterior.coords));q.set_transform(Affine2D().rotate_deg_around(x,y,-p['angle'])+ax.transData)
            else:
                q=Rectangle((x-w/2,y-h/2),w,h);q.set_transform(Affine2D().rotate_deg_around(x,y,-p['angle'])+ax.transData)
            q.set_facecolor(src.color(p['net']));q.set_edgecolor('#6e7d85');q.set_linewidth(.25);ax.add_patch(q)
        if p['drill'][0]:drilled.append(Circle((x,y),p['drill'][0]/2))
    rings=[Circle(v['pos'],v['diameter']/2) for v in g['vias']]
    ax.add_collection(PatchCollection(rings,facecolors=[src.color(v['net']) for v in g['vias']],edgecolors='#6d7e88',linewidths=.2))
    drilled += [Circle(v['pos'],v['drill']/2) for v in g['vias']]
    ax.add_collection(PatchCollection(drilled,facecolors='white',edgecolors='none'))
    ax.add_patch(Rectangle((0,0),g['board_width'],g['board_height'],fc='none',ec='#304959',lw=.65))
    ax.set_xlim(-.5,g['board_width']+.5);ax.set_ylim(g['board_height']+.5,-.5);ax.set_aspect('equal');ax.axis('off')

fig,axs=plt.subplots(1,4,figsize=(16,8.0))
for ax,(name,layer,title) in zip(axs,layers):
    draw(ax,layer);ax.set_title(name+'\n'+title,fontsize=12,fontweight='bold',pad=12)
fig.suptitle('Rev D / saved copper layers',x=.04,ha='left',fontsize=20,fontweight='bold')
fig.text(.04,.055,'GND: grey   RF/signal: teal   VCC: red   VEE: blue   VIN+: peach   VIN-: light blue   TEMP: purple   NC: taupe',fontsize=10,color='#304959')
fig.text(.04,.025,'All layers viewed from the top, with identical orientation. Bottom solder mask is not shown. Saved-file render, not an Altium screenshot.',fontsize=10,color='#4a6172')
fig.tight_layout(rect=[.015,.09,.995,.93]);fig.savefig(OUT/'L1-L4_overview.png',dpi=180);plt.close(fig)
for name,layer,title in layers:
    fig,ax=plt.subplots(figsize=(7,11.5));draw(ax,layer);ax.set_title(name+' / '+title,fontsize=16,fontweight='bold',pad=14)
    fig.text(.09,.035,'Top-view orientation | 41.656 x 68.580 mm\nSaved PCB copper, pads and holes; solder mask not shown.',fontsize=10,color='#4a6172')
    fig.tight_layout(rect=[.02,.075,.98,.98]);fig.savefig(OUT/(name+'.png'),dpi=220);plt.close(fig)
(OUT/'provenance.json').write_text(json.dumps(dict(source=pcb.name,pcb_sha256=digest,views=[v[0] for v in layers],orientation='all layers viewed from top; L4 not mirrored',content='saved copper, pads and holes; no solder mask or silkscreen',native_screenshot=False),indent=2)+'\n')
print('Rendered L1-L4 overview and four full-resolution copper-layer images')
