"""Compare saved mounting-via exposure and removal of top-only pad mask shadows."""
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
from bottom_mask_utils import read_bottom_mask,union_rows,pad_shape
from native_update import ROOT,blocks,parse
R=ROOT/'review';B=R/'bottom_mask_cleanup_baseline';pcb=ROOT/'QSTL_THS3491_RGT_G20_RevD.PcbDoc'
g=json.loads((R/'native_geometry.json').read_text());fs=json.loads((R/'native_import_copper.json').read_text());audit=json.loads((R/'bottom_mask_cleanup_check.json').read_text())
assert audit['pcb_sha256']==hashlib.sha256(pcb.read_bytes()).hexdigest()
plt.rcParams['font.family']='Malgun Gothic';plt.rcParams['axes.unicode_minus']=False
def patch(ax,p,color):
    if p.is_empty:return
    if p.geom_type!='Polygon':
        for q in p.geoms:
            if q.geom_type in ['Polygon','MultiPolygon']:patch(ax,q,color)
        return
    p=orient(p,sign=1);verts=[];codes=[]
    for loop in [p.exterior,*p.interiors]:
        pts=list(loop.coords);verts+=pts;codes+=[MPath.MOVETO]+[MPath.LINETO]*(len(pts)-2)+[MPath.CLOSEPOLY]
    ax.add_patch(PathPatch(MPath(verts,codes),fc=color,ec='none'))
grounds={l:unary_union([Polygon(f['outline'],f['holes']).buffer(0) for f in fs if f['layer']==l and f['net']=='GND']) for l in ['F.Cu','B.Cu']}
before=union_rows(read_bottom_mask(B/'before.PcbDoc'));after=union_rows(read_bottom_mask(pcb))
pad_openings=[]
with olefile.OleFileIO(pcb) as o:
    refs=[parse(b)['SOURCEDESIGNATOR'] for b in blocks(o.openstream('Components6/Data').read())];data=o.openstream('Pads6/Data').read()
off=0
while off<len(data):
    off+=1;bs=[]
    for _ in range(6):n=struct.unpack_from('<I',data,off)[0];off+=4;bs.append(data[off:off+n]);off+=n
    raw=bs[4];ref=refs[struct.unpack_from('<H',raw,7)[0]];num=bs[0][1:1+bs[0][0]].decode('ascii')
    p=next(p for p in g['pads'] if p['ref']==ref and p['num']==num)
    if 'B.Mask' in p['layers']:
        assert raw[102]==2
        expansion=struct.unpack_from('<i',raw,90)[0]*.00000254
        pad_openings.append(pad_shape(p).buffer(expansion,join_style=2))
pad_openings=unary_union(pad_openings)
fig,axs=plt.subplots(2,2,figsize=(12,10.8),gridspec_kw=dict(height_ratios=[1,1.05]))
cx,cy=next(p['pos'] for p in g['pads'] if p['ref']=='H1')
for col,diam in enumerate([6,7.6]):
    ax=axs[0,col];clip=box(cx-4.2,cy-4.2,cx+4.2,cy+4.2);opening=Point((cx,cy)).buffer(diam/2,resolution=128)
    patch(ax,clip,'#336e45');patch(ax,opening,'#a6a38e');patch(ax,opening.intersection(grounds['F.Cu']),'#d9b857')
    for v in g['vias']:
        p=Point(v['pos'])
        if not clip.covers(p):continue
        exposed=opening.covers(p.buffer(v['diameter']/2))
        ax.add_patch(Circle(v['pos'],v['diameter']/2,fc='#e6c66b' if exposed else '#285c39',ec='none'))
        ax.add_patch(Circle(v['pos'],v['drill']/2,fc='#f3f5f4' if exposed else '#1d482d',ec='none'))
    ax.add_patch(Circle((cx,cy),1.5875,fc='#f5f6f7',ec='#263e30',lw=.7))
    ax.set_xlim(cx-4.2,cx+4.2);ax.set_ylim(cy+4.2,cy-4.2);ax.set_aspect('equal');ax.axis('off')
    ax.set_title(('수정 전 · Ø6 mm, 비아는 마스크로 덮임' if col==0 else '수정 후 · Ø7.6 mm, 비아 24개 모두 노출'),fontsize=13,fontweight='bold',pad=10)
clip=box(12.5,23,26.5,34)
for ax,mask,title in zip(axs[1],[before,after],['수정 전 · 상면 패드가 하면에 투영됨','수정 후 · 실제 하면 접속부와 전원 비아만 보호']):
    mask=unary_union([mask,pad_openings])
    patch(ax,clip,'#336e45');patch(ax,mask.intersection(clip),'#d9b857')
    for v in g['vias']:
        p=Point(v['pos'])
        if not clip.covers(p):continue
        ax.add_patch(Circle(v['pos'],v['diameter']/2,fc='#e6c66b' if mask.covers(p) else '#285c39',ec='none'))
        ax.add_patch(Circle(v['pos'],v['drill']/2,fc='#f3f5f4' if mask.covers(p) else '#1d482d',ec='none'))
    ax.text(18.79601,27.94,'상면 U1 위치',ha='center',va='center',fontsize=9,color='#29463c',bbox=dict(fc='white',ec='none',alpha=.8,pad=1))
    ax.text(18.79601,33.45,'H9 실제 하면 패드',ha='center',va='center',fontsize=8,color='#29463c',bbox=dict(fc='white',ec='none',alpha=.8,pad=1))
    ax.set_xlim(12.5,26.5);ax.set_ylim(34,23);ax.set_aspect('equal');ax.axis('off');ax.set_title(title,fontsize=13,fontweight='bold',pad=10)
fig.suptitle('GND 노출 수정 · 장착 비아와 하면 마스크',x=.045,ha='left',fontsize=21,fontweight='bold')
fig.text(.045,.10,'금색: 노출 GND 동박   녹색: 솔더마스크   회갈색: 동박 이격부',fontsize=11)
fig.text(.045,.055,'장착 홀 4곳의 비아 96개 노출 · 상면 패드 63개의 하면 투영 제거 · 하면 노출 면적 약 127.48 mm² 증가',fontsize=10.5,color='#486170')
fig.text(.045,.02,'실제 하면 부품·관통 핀과 전원 비아 주변 마스크는 유지. Altium 저장 파일 기반 도면이며 화면 캡처가 아닙니다.',fontsize=10,color='#486170')
fig.tight_layout(rect=[.015,.145,.985,.94],h_pad=2.8);fig.savefig(R/'bottom_mask_cleanup_before_after.png',dpi=180);plt.close(fig)
(R/'bottom_mask_cleanup_figure.json').write_text(json.dumps(dict(pcb_sha256=audit['pcb_sha256'],native_screenshot=False,figure='bottom_mask_cleanup_before_after.png'),indent=2)+'\n')
print('Rendered saved bottom-mask and mounting-via comparison')
