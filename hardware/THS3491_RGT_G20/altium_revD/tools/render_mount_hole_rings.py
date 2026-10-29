"""Render mounting-hole ring overview and a dimensioned close-up."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle,Rectangle
R=Path(__file__).resolve().parents[1]/'review';g=json.loads((R/'native_geometry.json').read_text());intent=json.loads((R.parent/'mount_hole_ring_intent.json').read_text())
fig=plt.figure(figsize=(11,10));grid=fig.add_gridspec(1,2,width_ratios=[1,1.2]);ax=fig.add_subplot(grid[0,0])
ax.add_patch(Rectangle((0,0),g['board_width'],g['board_height'],fc='#dce6e2',ec='#45635b',lw=1))
for v in g['vias']:
    if v in intent['added_ground_vias']:continue
    ax.add_patch(Circle(v['pos'],v['diameter']/2,fc='#a5b8b1',ec='none'))
for ring in intent['rings']:
    ax.add_patch(Circle(ring['center_mm'],ring['hole_diameter_mm']/2,fc='white',ec='#4f6260',lw=.7))
    for pos in ring['positions_mm']:
        ax.add_patch(Circle(pos,.2,fc='#d37927',ec='none'));ax.add_patch(Circle(pos,.1,fc='white',ec='none'))
    x,y=ring['center_mm'];ax.text(x,y+(4.7 if y<30 else -4.4),ring['ref']+' / 24 vias',ha='center',fontsize=9,color='#38504a')
ax.set_xlim(-1,42.7);ax.set_ylim(69.6,-1);ax.set_aspect('equal');ax.set_xlabel('x (mm)');ax.set_ylabel('y from board top (mm)');ax.set_title('Four mounting holes',loc='left',fontweight='bold')
ax=fig.add_subplot(grid[0,1]);ring=next(q for q in intent['rings'] if q['ref']=='H3');x,y=ring['center_mm']
ax.add_patch(Rectangle((x-4.4,y-4.4),8.8,8.8,fc='#dce6e2',ec='none'))
ax.add_patch(Circle((x,y),3.4,fc='none',ec='#b2702d',lw=.7,ls=':'))
ax.add_patch(Circle((x,y),3,fc='none',ec='#617d71',lw=1,ls='--'))
ax.add_patch(Circle((x,y),3.175/2,fc='white',ec='#4f6260',lw=1))
for pos in ring['positions_mm']:
    ax.add_patch(Circle(pos,.2,fc='#d37927',ec='#7a4513',lw=.4));ax.add_patch(Circle(pos,.1,fc='white',ec='none'))
ax.plot(x,y,'+',color='#345047',ms=7)
ax.annotate('',xy=(x+3.4,y),xytext=(x,y),arrowprops=dict(arrowstyle='<->',color='#23453a',lw=1))
ax.text(x+1.7,y-.22,'R 3.4 mm',ha='center',fontsize=10,color='#23453a')
ax.text(x,y+.65,'Hole diameter\n3.175 mm',ha='center',fontsize=11,color='#345047')
ax.text(x,y-4,'24 GND vias / 15 degree steps',ha='center',fontsize=12,fontweight='bold')
ax.text(x,y+4.05,'Via copper / drill: 0.40 / 0.20 mm\nDotted: via centers; dashed: nominal 6 mm screw head',ha='center',va='top',fontsize=9,color='#345047')
ax.set_xlim(x-4.4,x+4.4);ax.set_ylim(y+4.8,y-4.4);ax.set_aspect('equal');ax.axis('off')
fig.suptitle('GND via rings around mechanical mounting holes',x=.07,ha='left',fontsize=17,fontweight='bold')
fig.text(.07,.025,'Orange: 96 added vias. Existing holes, RF geometry and all other vias are preserved.\nRendered from the saved native PCB geometry; not an Altium screenshot.',fontsize=9,color='#345047')
fig.tight_layout(rect=[0,.07,1,.94]);fig.savefig(R/'mechanical_hole_via_rings.png',dpi=180);plt.close(fig)
print('Saved mounting-hole via-ring diagram')
