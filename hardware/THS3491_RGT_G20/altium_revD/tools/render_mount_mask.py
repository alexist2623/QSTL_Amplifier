"""Render exposed copper from saved pad mask expansions and native copper regions."""
from pathlib import Path
import json,hashlib,struct
import olefile
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as MPath
from matplotlib.patches import PathPatch,Circle
from shapely.geometry import Polygon,Point,box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
from native_update import ROOT,records,parse
R=ROOT/'review';g=json.loads((R/'native_geometry.json').read_text());fill=json.loads((R/'native_import_copper.json').read_text());a=json.loads((R/'mount_mask_check.json').read_text())
pcb=ROOT/'QSTL_THS3491_RGT_G20_RevD.PcbDoc';assert hashlib.sha256(pcb.read_bytes()).hexdigest()==a['pcb_sha256']
plt.rcParams['font.family']='Malgun Gothic';plt.rcParams['axes.unicode_minus']=False

def patch(ax,p,color):
    if p.is_empty:return
    if p.geom_type!='Polygon':
        for q in p.geoms:
            if q.geom_type in ['Polygon','MultiPolygon']:patch(ax,q,color)
        return
    p=orient(p,sign=1);verts=[];codes=[]
    for loop in [p.exterior,*p.interiors]:
        xy=list(loop.coords);verts+=xy;codes += [MPath.MOVETO]+[MPath.LINETO]*(len(xy)-2)+[MPath.CLOSEPOLY]
    ax.add_patch(PathPatch(MPath(verts,codes),fc=color,ec='none'))

bottom=[]
with olefile.OleFileIO(pcb) as o:
    for raw in records(o.openstream('Regions6/Data').read(),11):
        if raw[0]!=38:continue
        n=struct.unpack_from('<I',raw,18)[0];off=22+n;loops=[]
        for _ in range(1+struct.unpack_from('<H',raw,14)[0]):
            count=struct.unpack_from('<I',raw,off)[0];off+=4;points=[]
            for _ in range(count):x,y=struct.unpack_from('<2d',raw,off);off+=16;points.append((x*.00000254,68.58-y*.00000254))
            loops.append(points)
        bottom.append(Polygon(loops[0],loops[1:]))
bottom=unary_union(bottom)
grounds={layer:unary_union([Polygon(f['outline'],f['holes']).buffer(0) for f in fill if f['layer']==layer and f['net']=='GND']) for layer in ['F.Cu','B.Cu']}
hole=next(p for p in g['pads'] if p['ref']=='H1');x,y=hole['pos'];local=box(x-4.15,y-4.15,x+4.15,y+4.15)
fig,axs=plt.subplots(1,3,figsize=(13,6.2))
for ax,layer,after,title in zip(axs,['F.Cu','F.Cu','B.Cu'],[False,True,True],['수정 전 · 상면','수정 후 · 상면','수정 후 · 하면']):
    patch(ax,local,'#336e45')
    disk=Point((x,y)).buffer(3 if after else 1.5875,resolution=128)
    mask_opening=unary_union([disk,bottom]) if layer=='B.Cu' else disk
    patch(ax,mask_opening.intersection(local),'#a6a38e')
    # Gold shows exposed GND copper, not empty substrate inside the NPTH clearance.
    patch(ax,grounds[layer].intersection(mask_opening).intersection(local),'#d9b857')
    for v in g['vias']:
        p=Point(v['pos'])
        if not local.covers(p):continue
        ax.add_patch(Circle(v['pos'],v['diameter']/2,fc='#d9b857' if mask_opening.covers(p) else '#285c39',ec='none'))
        ax.add_patch(Circle(v['pos'],v['drill']/2,fc='#efefea' if mask_opening.covers(p) else '#1d482d',ec='none'))
    ax.add_patch(Circle((x,y),1.5875,fc='#f6f7f8',ec='#1c2921',lw=.8))
    if after:
        ax.add_patch(Circle((x,y),3,fc='none',ec='#f8ecc3',lw=.8,ls='--'))
        ax.annotate('',(x-3,y-3.45),(x+3,y-3.45),arrowprops=dict(arrowstyle='<->',color='#244735',lw=1))
        ax.text(x,y-3.7,'마스크 개구 Ø6.00 mm',ha='center',va='center',fontsize=11,color='#203e30',bbox=dict(fc='white',ec='none',pad=1.2))
    ax.set_xlim(x-4.15,x+4.15);ax.set_ylim(y+4.15,y-4.15);ax.set_aspect('equal');ax.axis('off');ax.set_title(title,fontweight='bold',fontsize=15,pad=12)
fig.suptitle('장착 홀 H1–H4 · GND 동박 노출',fontsize=21,fontweight='bold',x=.04,ha='left')
fig.text(.04,.14,'금색: 노출 GND 동박   녹색: 솔더마스크   회갈색: 동박 이격부   흰색: Ø3.175 mm 홀',fontsize=10.5)
fig.text(.04,.08,'장착 홀 4곳에 동일 적용 · 상·하면 개구 Ø6 mm · 홀 주변 비아 배열 유지',fontsize=10.5,color='#486170')
fig.text(.04,.035,'하면의 기존 넓은 GND 노출 유지. Altium 저장 파일 기반 도면이며 화면 캡처가 아닙니다.',fontsize=10.5,color='#486170')
fig.tight_layout(rect=[.01,.21,.99,.9]);fig.savefig(R/'mounting_hole_copper_exposure.png',dpi=180);plt.close(fig)
(R/'mount_mask_figure.json').write_text(json.dumps(dict(pcb_sha256=a['pcb_sha256'],native_screenshot=False,figure='mounting_hole_copper_exposure.png',scope='H1 shown; identical 6 mm openings at H1-H4 on both sides'),indent=2)+'\n')
print('Rendered saved mounting-hole solder-mask openings and exposed GND')
