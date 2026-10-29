"""Render final perimeter via placement and enlarged lower board edge."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle,Rectangle,Polygon as Patch
from rf_fence_plan import rf_copper,padshape
R=Path(__file__).resolve().parents[1]/'review';g=json.loads((R/'native_geometry.json').read_text());intent=json.loads((R.parent/'edge_via_intent.json').read_text())
fig=plt.figure(figsize=(12,10));grid=fig.add_gridspec(2,2,width_ratios=[1,1.05],height_ratios=[1,1])
def draw(ax):
    ax.add_patch(Rectangle((0,0),g['board_width'],g['board_height'],fc='#e4eee9',ec='#354f43',lw=1.3))
    for p in g['pads']:
        if p['npth']:ax.add_patch(Circle(p['pos'],p['drill'][0]/2,fc='white',ec='#60766c',lw=.7))
        elif p['ref'].startswith('J'):
            poly=padshape(p);ax.add_patch(Patch(list(poly.exterior.coords),fc='#b9c9c1' if p['net']=='GND' else '#c7887e',ec='#5e7167',lw=.3))
    rf=rf_copper(g)
    for poly in getattr(rf,'geoms',[rf]):ax.add_patch(Patch(list(poly.exterior.coords),fc='#ba7465',ec='none',alpha=.7))
    for v in g['vias']:
        added=v in intent['added_ground_vias'];color='#db7b20' if added else '#8bada0'
        ax.add_patch(Circle(v['pos'],v['diameter']/2,fc=color,ec='none'))
        ax.add_patch(Circle(v['pos'],v['drill']/2,fc='white',ec='none'))
    ax.set_aspect('equal');ax.tick_params(labelsize=9)
    ax.set_xlabel('x (mm)');ax.set_ylabel('y from board top (mm)')
ax=fig.add_subplot(grid[:,0]);draw(ax);ax.set_xlim(-1,42.7);ax.set_ylim(69.6,-1)
ax.set_title('Four-edge GND via fence',loc='left',fontsize=14,fontweight='bold')
ax=fig.add_subplot(grid[0,1]);draw(ax);ax.set_xlim(-.8,13);ax.set_ylim(69.4,57)
ax.set_title('Lower-left edge and mounting-hole ring',loc='left',fontsize=12,fontweight='bold')
ax.annotate('',xy=(11,68.58),xytext=(11,67.58),arrowprops=dict(arrowstyle='<->',color='#244f42'))
ax.text(10.8,68.1,'1.0 mm',fontsize=10,ha='right',va='center',color='#244f42')
ax.annotate('New edge row',xy=(9.922602,67.58),xytext=(8,65.4),fontsize=10,color='#9e4b0e',arrowprops=dict(arrowstyle='->',color='#9e4b0e'))
ax=fig.add_subplot(grid[1,1]);ax.axis('off')
ax.text(0,.95,'148 new GND vias',fontsize=20,fontweight='bold',color='#9e4b0e',va='top')
ax.text(0,.78,'Center inset: 1.00 mm\nCopper-to-board edge: 0.80 mm\nNominal pitch: 1.00 mm\nVia copper / drill: 0.40 / 0.20 mm',fontsize=13,linespacing=1.7,va='top',color='#274c3d')
ax.text(0,.36,'50 existing vias reused at perimeter targets.\n16 targets omitted near RF connector pads.\nAll new vias connect to GND on L1-L4.\nTotal board vias: 965.',fontsize=11,linespacing=1.7,va='top',color='#476858')
fig.suptitle('Rev D / board-edge GND vias',x=.07,ha='left',fontsize=19,fontweight='bold')
fig.text(.07,.025,'Orange: new edge vias. Grey-green: existing vias, including mounting-hole rings.\nRendered from saved native PCB geometry; not an Altium screenshot.',fontsize=9,color='#476858')
fig.tight_layout(rect=[0,.11,1,.94]);fig.savefig(R/'board_edge_vias.png',dpi=180);plt.close(fig)
print('Saved board-edge via placement diagram')
