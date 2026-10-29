"""Before/after L3 render from native re-imports, not an app screenshot."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as MPath
from matplotlib.patches import PathPatch,Circle
from shapely.geometry import Polygon,box
from shapely.geometry.polygon import orient
R=Path(__file__).resolve().parents[1]/'review';S=R.parent/'staging/l3_local_power_20261028'
g=json.loads((R/'native_geometry.json').read_text());old=json.loads((S/'review_before/native_import_copper.json').read_text());new=json.loads((R/'native_import_copper.json').read_text())
intent=json.loads((R.parent/'l3_local_power_intent.json').read_text())
colors={'VCC':'#d55c40','VEE':'#3d7dcc','GND':'#cbd6dc'}
def patch(ax,p,color):
    p=orient(p,sign=1);v=[];c=[]
    for loop in [p.exterior,*p.interiors]:
        points=list(loop.coords);v+=points;c += [MPath.MOVETO]+[MPath.LINETO]*(len(points)-2)+[MPath.CLOSEPOLY]
    ax.add_patch(PathPatch(MPath(v,c),fc=color,ec='none'))
fig,axs=plt.subplots(1,2,figsize=(11,9.7))
for ax,fs,title in zip(axs,[old,new],['Before / broad split power','After / local power + GND']):
    for f in fs:
        if f['layer']=='In2.Cu':patch(ax,Polygon(f['outline'],f['holes']),colors[f['net']])
    for p in g['pads']:
        if p['npth']:ax.add_patch(Circle(p['pos'],p['drill'][0]/2,fc='white',ec='#344855',lw=.5))
    for v in g['vias']:
        if v['net'] in ['VCC','VEE']:ax.add_patch(Circle(v['pos'],.15,fc=colors[v['net']],ec='white',lw=.4))
    ax.set_xlim(-.8,42.45);ax.set_ylim(69.38,-.8);ax.set_aspect('equal');ax.set_title(title,loc='left',fontweight='bold',fontsize=14)
    ax.set_xlabel('x (mm)');ax.set_ylabel('y from board top (mm)')
ax=axs[1]
for v in intent['removed_ground_vias']:ax.plot(*v['pos'],'x',ms=3,color='#691f27',mew=.7)
for text,pos,anchor in [('VCC array',(25.5,10.8),(30,7.0)),('VEE array',(13,45),(3,50)),('U1',(18.79601,27.94),(6,28)),('C7 branches',(24.9,31.5),(29,36)),('7 GND vias removed\n0.8 mm bridge',(21.6,17.8),(29,19))]:
    ax.annotate(text,xy=pos,xytext=anchor,fontsize=8.5,color='#213c4b',arrowprops=dict(arrowstyle='-',lw=.8,color='#213c4b'),bbox=dict(fc='white',ec='none',alpha=.88,pad=1))
fig.suptitle('L3 power corridors follow the marked route',x=.08,ha='left',fontsize=17,fontweight='bold')
fig.text(.08,.035,'Red: VCC   Blue: VEE   Grey: GND\nNative saved geometry. Both supply rails and all 47 power vias remain connected; C7 uses 0.30 mm branches.',fontsize=10,color='#344a57')
fig.tight_layout(rect=[0,.09,1,.95]);fig.savefig(R/'L3_local_power_before_after.png',dpi=180);plt.close(fig)
print('Saved L3 before/after')
