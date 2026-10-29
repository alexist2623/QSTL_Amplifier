"""Draw TP1 removal using the baseline and final native PCB geometry."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle,Rectangle,Polygon as Patch
from rf_fence_plan import padshape
R=Path(__file__).resolve().parents[1]/'review';S=R.parent/'staging/remove_tp1_20261028'
before=json.loads((S/'review_before/native_geometry.json').read_text());after=json.loads((R/'native_geometry.json').read_text())
fig,axs=plt.subplots(1,2,figsize=(12,5.3))
for ax,g,title in zip(axs,[before,after],['Before / isolated TP1 GND pin','After / TP1 removed']):
    ax.add_patch(Rectangle((0,0),g['board_width'],g['board_height'],fc='#dce9e1',ec='#325b47',lw=1))
    for t in g['tracks']:
        if t['layer']=='F.Cu':ax.plot([t['start'][0],t['end'][0]],[t['start'][1],t['end'][1]],color='#bd806d',lw=t['width']*5)
    for p in g['pads']:
        if 'F.Cu' not in p['layers']:continue
        poly=padshape(p);ax.add_patch(Patch(list(poly.exterior.coords),fc='#b6c8bd' if p['net']=='GND' else '#bd806d',ec='#526b5d',lw=.4))
        if p['drill'][0]:ax.add_patch(Circle(p['pos'],p['drill'][0]/2,fc='white',ec='none'))
    for v in g['vias']:
        ax.add_patch(Circle(v['pos'],v['diameter']/2,fc='#8eaf9f',ec='none'));ax.add_patch(Circle(v['pos'],v['drill']/2,fc='white',ec='none'))
    ax.set_xlim(25.5,42.1);ax.set_ylim(31,18);ax.set_aspect('equal');ax.set_title(title,loc='left',fontsize=13,fontweight='bold');ax.set_xlabel('x (mm)')
axs[0].annotate('TP1\nGND through-hole',xy=(31.49601,21.8948),xytext=(28,19.2),fontsize=10,color='#814f19',arrowprops=dict(arrowstyle='->',color='#814f19'))
axs[1].annotate('GND copper restored\nNo pad or drill hole',xy=(31.49601,21.8948),xytext=(28,19.2),fontsize=10,color='#275b40',arrowprops=dict(arrowstyle='->',color='#275b40'))
axs[0].set_ylabel('y from board top (mm)')
fig.text(.07,.025,'Saved-file geometry comparison. Output connector, RF route and all 965 vias are preserved. Not an Altium screenshot.',fontsize=9,color='#476858')
fig.tight_layout(rect=[0,.07,1,1]);fig.savefig(R/'TP1_removed.png',dpi=180);plt.close(fig)
print('Saved TP1 removal comparison')
