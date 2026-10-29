"""Compare the two native DC input pours at the same physical scale."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle,Rectangle
from matplotlib.transforms import Affine2D
from render_review import polygon,colors
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'review'
g=json.loads((R/'native_geometry.json').read_text());fill=json.loads((R/'native_import_copper.json').read_text());intent=json.loads((ROOT/'dc_plane_intent.json').read_text())
colors.update(VIN_P='#f4b779',VIN_N='#a6c5ed',GND='#dce3e8',VCC='#a8d7c0',VEE='#a8d7c0')
fig,axes=plt.subplots(1,2,figsize=(12,10))
for ax,spec,limits in zip(axes,intent['planes'],[(8,30,1,23),(7.5,29.5,44,66)]):
    for f in fill:
        if f['layer']=='F.Cu':polygon(ax,f)
    for q in g['pads']:
        if 'F.Cu' not in q['layers']:continue
        x,y=q['pos'];w,h=q['size']
        if not (limits[0]-2<x<limits[1]+2 and limits[2]-2<y<limits[3]+2):continue
        p=Circle((x,y),w/2) if q['shape']==0 else Rectangle((x-w/2,y-h/2),w,h)
        p.set_transform(Affine2D().rotate_deg_around(x,y,-q['angle'])+ax.transData)
        p.set_facecolor('#c4ab63');p.set_edgecolor('#7a673c');p.set_linewidth(.55);ax.add_patch(p)
        if q['drill'][0]:ax.add_patch(Circle((x,y),q['drill'][0]/2,fc='white',lw=0))
    for v in g['vias']:
        ax.add_patch(Circle(v['pos'],v['diameter']/2,fc=colors.get(v['net'],'#888'),ec='#6b7f8c',lw=.3))
        ax.add_patch(Circle(v['pos'],v['drill']/2,fc='white',lw=0))
    ps=spec['outline_mm']+[spec['outline_mm'][0]];ax.plot(*zip(*ps),'--',color='#155fe1',lw=1.4)
    for q in g['pads']:
        if q['ref']!=spec['ref']:continue
        label={'1':spec['net'],'2':'GND','3':'SW / NC'}[q['num']]
        ax.text(*q['pos'],q['num']+'\n'+label,fontsize=8,ha='center',va='center',weight='bold',color='#19324a',bbox=dict(fc='white',ec='none',alpha=.87,pad=.8))
    ax.set(xlim=limits[:2],ylim=(limits[3],limits[2]),aspect='equal',xlabel='x (mm)',ylabel='y from board top (mm)')
    ax.set_title(spec['ref']+' / '+('+15V - VIN_P' if spec['net']=='VIN_P' else '-15V - VIN_N'),fontsize=15,weight='bold',pad=14)
fig.suptitle('Both DC input copper planes expanded',fontsize=21,weight='bold',y=.94)
fig.text(.07,.12,'Both inputs: clearance to GND pad 2 = 0.205 mm; to unused switch pad 3 = 1.10 mm.\nPins, components, vias, RF routing and filter positions remain unchanged.',fontsize=11,linespacing=1.6)
fig.text(.07,.05,'Blue dashed: polygon boundary. Grey: GND. Green: filtered supply. Same scale in both panels.\nRe-rendered from the Altium-saved PCB; not an Altium screenshot.',fontsize=9,color='#536675')
fig.subplots_adjust(left=.07,right=.98,top=.88,bottom=.20,wspace=.2)
fig.savefig(R/'dc_planes_both.png',dpi=180);plt.close(fig)
print(R/'dc_planes_both.png')
