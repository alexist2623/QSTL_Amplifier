"""Render independently imported native copper; these are not Altium screenshots."""
from pathlib import Path
import json
import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as MPath
from matplotlib.patches import PathPatch, Circle, Rectangle
from matplotlib.transforms import Affine2D
import numpy as np
from shapely.geometry import Polygon, box
from shapely.geometry.polygon import orient

R=Path(__file__).resolve().parents[1]/'review'
g=json.loads((R/'native_geometry.json').read_text())
fill=json.loads((R/'native_import_copper.json').read_text())
native_shapes={(d['ref'],d['pad']):d for d in json.loads((R/'native_import_check.json').read_text())['rounded_rectangle_pads']}
colors={'GND':'#cbd5df','VCC':'#d74f39','VEE':'#3778c9','VIN_P':'#edb493',
        'VIN_N':'#95b2df','TJ_RAW':'#a54ca4','TEMP':'#a54ca4'}
def color(net): return colors.get(net,'#128476')
def polygon(ax,f):
    poly=orient(Polygon(f['outline'],f['holes']),sign=1)
    verts=[]; codes=[]
    for loop in [poly.exterior,*poly.interiors]:
        pts=list(loop.coords); verts.extend(pts)
        codes.extend([MPath.MOVETO]+[MPath.LINETO]*(len(pts)-2)+[MPath.CLOSEPOLY])
    ax.add_patch(PathPatch(MPath(verts,codes),facecolor=color(f['net']),edgecolor='none'))
def render(name,title,layer,limits,figsize,detail=False):
    fig,ax=plt.subplots(figsize=figsize)
    fig.patch.set_facecolor('white'); ax.set_facecolor('#f9fbfd')
    for f in fill:
        if f['layer']==layer: polygon(ax,f)
    for t in g['tracks']+g['arcs']:
        if t['layer']!=layer: continue
        if 'radius' in t:
            cx,cy=t['center']; a=math.atan2(t['start'][1]-cy,t['start'][0]-cx)
            angles=np.linspace(a,a+math.radians(t['angle']),120)
            xs=cx+t['radius']*np.cos(angles); ys=cy+t['radius']*np.sin(angles)
        else: xs,ys=zip(t['start'],t['end'])
        # Plot data-space strokes as buffered polygon strips, preserving widths.
        from shapely.geometry import LineString
        line=LineString(zip(xs,ys)).buffer(t['width']/2)
        ax.add_patch(plt.Polygon(list(line.exterior.coords),color=color(t['net']),linewidth=0))
    for q in g['pads']:
        x,y=q['pos']; w,h=q['size']
        if q['npth']:
            ax.add_patch(Circle((x,y),q['drill'][0]/2,color='white',ec='#536675',lw=.4)); continue
        if layer not in q['layers']: continue
        if q['shape']==0: patch=Circle((x,y),w/2)
        elif q['shape']==4:
            radius=native_shapes[q['ref'],q['num']]['radius_mm']
            shape=box(x-w/2+radius,y-h/2+radius,x+w/2-radius,y+h/2-radius).buffer(radius,resolution=24)
            patch=plt.Polygon(list(shape.exterior.coords))
            patch.set_transform(Affine2D().rotate_deg_around(x,y,-q['angle'])+ax.transData)
        else:
            patch=Rectangle((x-w/2,y-h/2),w,h)
            patch.set_transform(Affine2D().rotate_deg_around(x,y,-q['angle'])+ax.transData)
        patch.set_facecolor(color(q['net'])); patch.set_edgecolor('#b69a58'); patch.set_linewidth(.45)
        ax.add_patch(patch)
        if q['drill'][0]: ax.add_patch(Circle((x,y),q['drill'][0]/2,color='white'))
    for v in g['vias']:
        ax.add_patch(Circle(v['pos'],v['diameter']/2,facecolor=color(v['net']),edgecolor='#697985',lw=.25))
        ax.add_patch(Circle(v['pos'],v['drill']/2,color='#f9fbfd',lw=0))
    if layer=='F.Cu':
        refs=['U1','C3','C4','C5','C6','C1','C2','L1','L2','C7','C8','R8','J1','J2','J3','J7']
        for f in g['parts']:
            x,y=f['pos']
            if f['ref'] not in refs or not (limits[0]<x<limits[1] and limits[2]<y<limits[3]): continue
            if f['ref']=='U1': dx,dy=0,.1
            elif f['ref'] in ['C5','C6']: dx,dy=1.2,0
            else: dx,dy=1.6,0
            if not detail:
                ax.text(x+dx,y+dy,f['ref'],fontsize=9,ha='center',va='center',color='#243a4c',
                        bbox=dict(facecolor='white',alpha=.84,edgecolor='none',pad=.7))
        if detail:
            labels=[('16 / PD',(18.04601,26.54),(17.32,27.15)),
                    ('15 / NC GND',(18.54601,26.54),(18.546,27.46)),
                    ('14 / VS+',(19.04601,26.54),(19.18,27.15)),
                    ('13 / VS+',(19.54601,26.54),(20.22,27.46)),
                    ('C5 GND',(19.29601,23.49683),(20.6,23.22)),
                    ('C5 VCC',(19.29601,24.89683),(20.6,24.4)),
                    ('PD via to L3',(17.75,25.4),(16.93,24.7))]
            for label,point,text in labels:
                ax.annotate(label,point,xytext=text,fontsize=9,ha='center',color='#22394b',
                            arrowprops=dict(arrowstyle='-',color='#22394b',lw=.7),
                            bbox=dict(facecolor='white',alpha=.92,edgecolor='none',pad=1.5))
    ax.set_xlim(limits[:2]); ax.set_ylim(limits[3],limits[2]); ax.set_aspect('equal')
    ax.set_xlabel('x (mm)'); ax.set_ylabel('y from board top (mm)')
    ax.spines[['top','right']].set_visible(False); ax.tick_params(labelsize=8)
    ax.set_title(title,loc='left',fontsize=15,fontweight='bold',pad=18)
    fig.text(.09,.02,'Native copper re-import | red: VCC  blue: VEE  grey: GND  purple: TEMP\n'
             'Review only. Altium open/save verified; native repour and application DRC pending.',fontsize=8,color='#4a6172')
    fig.tight_layout(rect=[0,.07,1,1])
    fig.savefig(R/(name+'.png'),dpi=180)
    fig.savefig(R/(name+'.svg'))
    plt.close(fig)

if __name__=='__main__':
    render('layout_L1','Rev D / L1 layout','F.Cu',(-1,42.65,-1,69.58),(9,13))
    render('layout_core','Rev D / C5–C6 and TEMP escape','F.Cu',(13,26,22,34.8),(11,10))
    render('layout_PD_NC','Rev D / separate PD route and NC ground','F.Cu',(16.35,21.25,22.8,28.3),(10,10),True)
    render('layout_L3','Rev D / L3 split power','In2.Cu',(-1,42.65,-1,69.58),(9,13))
    print('Saved four native-copper PNG/SVG review drawings')
