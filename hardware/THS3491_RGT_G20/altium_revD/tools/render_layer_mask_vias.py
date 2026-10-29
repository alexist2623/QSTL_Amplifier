"""Draw actual saved bottom mask, pin protection, and restored RF copper."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as MPath
from matplotlib.patches import PathPatch,Circle,Rectangle
from shapely.geometry import Polygon,Point,box
from shapely.geometry.polygon import orient
from shapely.affinity import rotate
from shapely.ops import unary_union
R=Path(__file__).resolve().parents[1]/'review'
g=json.loads((R/'native_geometry.json').read_text());report=json.loads((R/'layer_mask_via_check.json').read_text())
fill=json.loads((R/'native_import_copper.json').read_text())
intent=json.loads((R.parent/'layer_mask_via_intent.json').read_text())
if (R.parent/'remove_tp1_intent.json').exists():
    report['bottom_mask_regions']=json.loads((R.parent/'remove_tp1_intent.json').read_text())['bottom_mask_regions']

def patch(ax,p,color,edge='none',lw=.5,alpha=1):
    if p.is_empty:return
    if p.geom_type=='MultiPolygon':
        for q in p.geoms:patch(ax,q,color,edge,lw,alpha)
        return
    p=orient(p,sign=1);verts=[];codes=[]
    for loop in [p.exterior,*p.interiors]:
        points=list(loop.coords);verts+=points;codes += [MPath.MOVETO]+[MPath.LINETO]*(len(points)-2)+[MPath.CLOSEPOLY]
    ax.add_patch(PathPatch(MPath(verts,codes),facecolor=color,edgecolor=edge,lw=lw,alpha=alpha))

def pad(p):
    x,y=p['pos'];w,h=p['size']
    q=Point(x,y).buffer(w/2,resolution=32) if p['shape']==0 else box(x-w/2,y-h/2,x+w/2,y+h/2)
    return rotate(q,-p['angle'],origin=(x,y))

def bottom(ax,limits):
    patch(ax,box(0,0,g['board_width'],g['board_height']),'#216343')
    for f in report['bottom_mask_regions']:patch(ax,Polygon(f['outline'],f['holes']),'#dcb95d')
    # Actual pad openings remain distinct from the newly opened GND field.
    for p in g['pads']:
        if 'B.Mask' in p['layers']:patch(ax,pad(p),'#f8d371','#243e37',.4)
        elif p['ref']=='U1' and p['num']!='17':patch(ax,pad(p),'none','#eef7ff',.65)
        if p['drill'][0]:ax.add_patch(Circle(p['pos'],p['drill'][0]/2,facecolor='#f3f5f6',edgecolor='#697d7a',lw=.4))
    for v in g['vias']:ax.add_patch(Circle(v['pos'],v['drill']/2,fc='#f3f5f6',ec='none'))
    x,y=next(p['pos'] for p in g['parts'] if p['ref']=='U1')
    ax.add_patch(Rectangle((x-1.5,y-1.5),3,3,fc='none',ec='#0082e1',lw=1.8,ls='--'))
    ax.set_xlim(limits[:2]);ax.set_ylim(limits[3],limits[2]);ax.set_aspect('equal')
    ax.set_xlabel('x (mm)');ax.set_ylabel('y from board top (mm)')

fig=plt.figure(figsize=(13,10));grid=fig.add_gridspec(2,2,width_ratios=[1,1.15])
ax=fig.add_subplot(grid[:,0]);bottom(ax,(-.8,42.45,-.8,69.38));ax.set_title('Bottom GND exposure',loc='left',fontweight='bold')
ax.annotate('U1 directly above',xy=(18.79601,27.94),xytext=(3,21),arrowprops=dict(arrowstyle='->',color='#0070bf'),color='#0064aa',fontsize=10)
ax.annotate('Existing H9 solder pad',xy=(18.79601,35.074),xytext=(3,40),arrowprops=dict(arrowstyle='->',color='#334a43'),color='#334a43',fontsize=9)
ax=fig.add_subplot(grid[0,1]);bottom(ax,(16.25,21.35,25.4,30.5));ax.set_title('U1 underside / pin areas stay masked',loc='left',fontweight='bold')
ax.text(18.79601,27.94,'Exposed GND\nunder EP',ha='center',va='center',fontsize=10,color='#49370e')
ax=fig.add_subplot(grid[1,1]);z=next(z for z in g['zones'] if z['name']=='L1_POSITIVE_INPUT');patch(ax,Polygon(z['outline']),'#f4e4d8')
for f in fill:
    if f['layer']=='F.Cu' and f['net']=='VIN_P':patch(ax,Polygon(f['outline'],f['holes']),'#db9167')
for v in g['vias']:
    if v['net']=='GND':ax.add_patch(Circle(v['pos'],v['diameter']/2,fc='#679786',ec='white',lw=.5))
for v in intent['removed_ground_vias']:ax.plot(*v['pos'],marker='x',color='#b52635',ms=7,mew=1.4)
for p in g['pads']:
    if p['ref']=='J9':patch(ax,pad(p),'#c5cbd0','#4b5963');ax.text(*p['pos'],p['num'],ha='center',va='center',fontsize=10,clip_on=True)
ax.set_xlim(13,22.3);ax.set_ylim(16.7,12.2);ax.set_aspect('equal');ax.set_title('VIN_P / 12 overlapping GND vias removed',loc='left',fontweight='bold');ax.set_xlabel('x (mm)');ax.set_ylabel('y from board top (mm)')
fig.suptitle('Rev D — saved native geometry verification',fontsize=18,fontweight='bold',x=.08,ha='left')
fig.text(.08,.025,'Gold: exposed copper   Green: solder mask   Blue dashed: U1 body projection   Red crosses: removed vias\nAligned top-view coordinates for comparison (not mirrored). Native file render, not an Altium screenshot.',fontsize=10,color='#334a53')
fig.tight_layout(rect=[0,.10,1,.94]);fig.savefig(R/'bottom_ground_mask_and_vias.png',dpi=175);plt.close(fig)

fig,axs=plt.subplots(1,3,figsize=(14,5))
for ax,layer,title in zip(axs,['In1.Cu','In2.Cu','B.Cu'],['L2: RF windows retained','L3: RF windows removed','L4: RF windows removed']):
    for f in fill:
        if f['layer']==layer:patch(ax,Polygon(f['outline'],f['holes']),{'GND':'#c5cfd7','VCC':'#dc997f','VEE':'#8caed2'}.get(f['net'],'#bca4ca'))
    for p in g['pads']:
        if p['ref']=='U1':patch(ax,pad(p),'none','#222c34',.6)
    for c in json.loads((R/'native_import_cutouts.json').read_text()):
        if c['layer']==layer:patch(ax,Polygon(c['outline']),'none','#be3c64',.65)
    ax.set_xlim(13.5,23);ax.set_ylim(30.5,25.7);ax.set_aspect('equal');ax.set_title(title,loc='left',fontweight='bold');ax.set_xlabel('x (mm)')
fig.text(.03,.05,'Actual saved copper; black outlines are U1 pad projections. L3 retains the required clearances between power and GND.',fontsize=10)
fig.tight_layout(rect=[0,.12,1,1]);fig.savefig(R/'RF_layers_L2_L3_L4.png',dpi=180);plt.close(fig)
print('Saved bottom-mask, VIN_P via and RF layer comparison figures')
