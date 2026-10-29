"""Native-copper zoom explaining the L-shaped supply and switched jack contact."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle,Rectangle
from render_review import polygon,colors
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'review'
g=json.loads((R/'native_geometry.json').read_text());fill=json.loads((R/'native_import_copper.json').read_text());intent=json.loads((ROOT/'dc_plane_intent.json').read_text())
colors.update(VIN_P='#f7ba76',GND='#dce3e8',VCC='#a8d7c0')
fig,(ax,info)=plt.subplots(1,2,figsize=(14,7),gridspec_kw={'width_ratios':[1.65,1]})
for f in fill:
    if f['layer']=='F.Cu':polygon(ax,f)
for q in g['pads']:
    if 'F.Cu' not in q['layers']:continue
    x,y=q['pos'];w,h=q['size']
    if not (9<x<29.5 and 4<y<16):continue
    if q['shape']==0:p=Circle((x,y),w/2)
    else:
        from matplotlib.transforms import Affine2D
        p=Rectangle((x-w/2,y-h/2),w,h);p.set_transform(Affine2D().rotate_deg_around(x,y,-q['angle'])+ax.transData)
    p.set_facecolor('#c4ab63');p.set_edgecolor('#6a603f');p.set_linewidth(.8);ax.add_patch(p)
    if q['drill'][0]:ax.add_patch(Circle((x,y),q['drill'][0]/2,color='white',lw=0))
for v in g['vias']:
    ax.add_patch(Circle(v['pos'],v['diameter']/2,fc=colors.get(v['net'],'#888'),ec='#6b7f8c',lw=.3))
    ax.add_patch(Circle(v['pos'],v['drill']/2,fc='white',lw=0))
ps=intent['outline_mm']+[intent['outline_mm'][0]];ax.plot(*zip(*ps),'--',color='#155fe1',lw=1.5)
for num,label,xy in [('1','VIN_P',(16.5,13.7)),('2','GND',(16.5,7.7)),('3','SW / NC',(11.8,10.7))]:
    ax.text(*xy,num+'\n'+label,ha='center',va='center',fontsize=10,weight='bold',color='#1a324b',bbox=dict(fc='white',ec='none',alpha=.85,pad=1))
ax.annotate('GND clearance\n0.205 mm',(18.02,7.7),xytext=(20.5,6.2),fontsize=9,color='#22384c',arrowprops=dict(arrowstyle='->',color='#22384c'))
ax.annotate('Side contact isolated\n1.10 mm to VIN_P',(13.1,10.7),xytext=(9.5,5.4),fontsize=9,color='#22384c',arrowprops=dict(arrowstyle='->',color='#22384c'))
ax.set(xlim=(9,29.5),ylim=(16,4),aspect='equal',xlabel='x (mm)',ylabel='y from board top (mm)')
ax.set_title('VIN_P copper follows the marked L shape',fontsize=15,weight='bold',pad=14)
info.axis('off');info.text(0,.95,'PJ-102AH pinout',fontsize=18,weight='bold',va='top')
info.text(0,.82,'1  Center contact  ->  +15V\n2  Outer sleeve     ->  GND\n3  Sleeve switch    ->  PCB NC',fontsize=12,linespacing=1.8,va='top',family='monospace')
info.text(0,.54,'Inside the jack:\nNo plug:  2 -- 3 closed\nPlug in:  2    3 open',fontsize=12,linespacing=1.8,va='top',family='monospace')
info.text(0,.28,'Orange: VIN_P copper\nGrey: GND copper\nBlue dashed: polygon boundary\n\nPin positions remain unchanged.',fontsize=11,linespacing=1.5,va='top')
fig.text(.07,.035,'Re-rendered from the Altium-saved PCB. Not an app screenshot. Pinout: Same Sky PJ-102AH datasheet, p.2.',fontsize=9,color='#536675')
fig.tight_layout(rect=(0,.07,1,1));fig.savefig(R/'dc_plane_pinout.png',dpi=170);plt.close(fig)
print(R/'dc_plane_pinout.png')
