"""Render native RF copper and shield-via placement."""
import json,math
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from shapely.geometry import Polygon
from rf_fence_plan import rf_copper,ROOT
R=ROOT/'review';g=json.loads((R/'native_geometry.json').read_text());intent=json.loads((ROOT/'rf_fence_intent.json').read_text())
rf=rf_copper(g)
fig,ax=plt.subplots(figsize=(15,8));ax.set_facecolor('#f1f5f4')
for p in (list(rf.geoms) if hasattr(rf,'geoms') else [rf]):ax.fill(*p.exterior.xy,color='#bd7540',zorder=3)
for v in g['vias']:
    if v in intent['added_ground_vias'] or v in intent['reused_existing_vias']:continue
    ax.add_patch(Circle(v['pos'],v['diameter']/2,fc='#c9d1d0',ec='none',zorder=1))
for vs,col in [(intent['reused_existing_vias'],'#1870b3'),(intent['added_ground_vias'],'#159566')]:
    for v in vs:
        ax.add_patch(Circle(v['pos'],v['diameter']/2,fc=col,ec='none',zorder=5));ax.add_patch(Circle(v['pos'],v['drill']/2,fc='white',ec='none',zorder=6))
for x,y in intent['blocked_targets_mm']:ax.plot(x,y,'x',color='#c5576d',ms=4,alpha=.7)
for p in g['parts']:
    if p['ref'] in ['J1','J2','J3','R1','R14','U1']:
        x,y=p['pos'];ax.text(x+(.7 if x<2 else -.7 if x>40 else 0),y+(.1 if p['ref']=='U1' else 2.3),p['ref'],ha='center',fontsize=10,color='#283b47')
# Dimension at a clear portion of the output trace.
x=31.7;y=27.94;gap=intent['minimum_gap_mm'];half=intent['reference_trace_width_mm']/2
ax.annotate('',xy=(x,y-half-gap),xytext=(x,y-half),arrowprops=dict(arrowstyle='<->',color='#1d3b4a',lw=1))
ax.text(x+.45,y-half-gap/2,'3W = 0.9174 mm\nCopper edge to copper edge',fontsize=9,va='center',color='#1d3b4a')
ax.set_xlim(-.5,42.15);ax.set_ylim(39,18.5);ax.set_aspect('equal');ax.set_xlabel('x (mm)');ax.set_ylabel('y from board top (mm)')
fig.suptitle('RF GND shield vias / 3W spacing',x=.07,ha='left',fontsize=18,fontweight='bold')
fig.text(.07,.035,f"Green: {len(intent['added_ground_vias'])} new vias   Blue: {len(intent['reused_existing_vias'])} existing vias reused   Grey: other existing vias\nVia diameter / drill: 0.40 / 0.20 mm; nominal pitch 0.90 mm. Crosses mark protected or obstructed locations.",fontsize=10,color='#344d58')
fig.tight_layout(rect=[0,.10,1,.94]);fig.savefig(R/'RF_3W_shield_vias.png',dpi=180);plt.close(fig)
print('Saved RF shield via diagram')
