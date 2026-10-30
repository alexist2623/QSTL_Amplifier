"""Render saved-copper before/after views for L2 pad windows and clean L3 planes."""
from pathlib import Path
import hashlib,json,math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle,Polygon as Patch
from matplotlib.collections import PatchCollection
from shapely.geometry import Polygon,LineString,box
from shapely.affinity import rotate
from shapely.ops import unary_union
import render_review as src

ROOT=Path(__file__).resolve().parents[1];R=ROOT/'review';B=R/'l3_cleanup_baseline/review_before'
g=src.g;old=json.loads((B/'native_geometry.json').read_text());prior=json.loads((B/'native_import_copper.json').read_text())
digest=hashlib.sha256((ROOT/'QSTL_THS3491_RGT_G20_RevD.PcbDoc').read_bytes()).hexdigest()
assert digest==json.loads((R/'native_import_check.json').read_text())['source_sha256']
assert digest==json.loads((R/'l3_cleanup_check.json').read_text())['pcb_sha256'], 'Historical renderer: use render_resistor_windows.py for the subsequent L2 revision'
plt.rcParams['font.family']='Malgun Gothic';plt.rcParams['axes.unicode_minus']=False

def field(ax,fs,geom,layer,limits):
    ax.set_facecolor('#fff')
    for f in fs:
        if f['layer']==layer:src.polygon(ax,f)
    for p in geom['pads']:
        if not p['drill'][0]:continue
        x,y=p['pos'];w,h=p['size']
        if layer in p['layers'] and not p['npth']:
            shape=Circle((x,y),w/2) if p['shape']==0 else Patch(list(rotate(box(x-w/2,y-h/2,x+w/2,y+h/2),-p['angle'],origin=(x,y)).exterior.coords))
            shape.set_facecolor(src.color(p['net']));shape.set_edgecolor('#657782');shape.set_linewidth(.4);ax.add_patch(shape)
        ax.add_patch(Circle((x,y),p['drill'][0]/2,fc='white',ec='none'))
    rings=[Circle(v['pos'],v['diameter']/2) for v in geom['vias']]
    holes=[Circle(v['pos'],v['drill']/2) for v in geom['vias']]
    ax.add_collection(PatchCollection(rings,facecolors=[src.color(v['net']) for v in geom['vias']],edgecolors='#8799a5',linewidths=.35))
    ax.add_collection(PatchCollection(holes,facecolors='white',edgecolors='none'))
    ax.set_xlim(limits[:2]);ax.set_ylim(limits[3],limits[2]);ax.set_aspect('equal');ax.axis('off')

def copper(fs,layer,net):return unary_union([Polygon(f['outline'],f['holes']).buffer(0) for f in fs if f['layer']==layer and f['net']==net])

rf={'FB','INV','inpt','AMP_OUT','RG_DRIVE','inm','inpt_raw','output'}
def signal_overlay(ax):
    for t in g['tracks']+g['arcs']:
        if t['layer']!='F.Cu' or t['net'] not in rf:continue
        if 'radius' in t:
            cx,cy=t['center'];a=math.atan2(t['start'][1]-cy,t['start'][0]-cx)
            pts=[(cx+t['radius']*math.cos(a+math.radians(t['angle'])*i/300),cy+t['radius']*math.sin(a+math.radians(t['angle'])*i/300)) for i in range(301)]
        else:pts=[t['start'],t['end']]
        q=LineString(pts).buffer(t['width']/2)
        ax.add_patch(Patch(list(q.exterior.coords),fc='#157f91',ec='none',alpha=.70))
    for p in g['pads']:
        if p['net'] not in rf or 'F.Cu' not in p['layers']:continue
        x,y=p['pos'];w,h=p['size']
        q=rotate(box(x-w/2,y-h/2,x+w/2,y+h/2),-p['angle'],origin=(x,y))
        ax.add_patch(Patch(list(q.exterior.coords),fc='#66c7d3',ec='#186a79',lw=.6,alpha=.9))
    for ref in ['R2','R3','R4','R6','R7','U1','R14']:
        p=next(p for p in g['parts'] if p['ref']==ref);x,y=p['pos']
        if ref=='R14':y-=.9
        ax.text(x,y,ref,fontsize=10,color='#253f52',ha='center',va='center',bbox=dict(fc='white',alpha=.8,ec='none',pad=.8))

fig,axs=plt.subplots(1,2,figsize=(12,5.4))
restored=copper(src.fill,'In1.Cu','GND').difference(copper(prior,'In1.Cu','GND'))
for ax,fs,geom,title in zip(axs,[prior,src.fill],[old,g],['수정 전 · 트레이스까지 이어진 개구','수정 후 · 패드 아래 개구만 유지']):
    field(ax,fs,geom,'In1.Cu',(13.0,24.2,24.3,31.1))
    if fs is src.fill:
        for q in getattr(restored,'geoms',[restored]):
            if q.geom_type=='Polygon':
                f=dict(outline=list(q.exterior.coords),holes=[list(h.coords) for h in q.interiors],net='RESTORED')
                src.colors['RESTORED']='#8bd29d';src.polygon(ax,f)
    signal_overlay(ax);ax.set_title(title,fontsize=16,fontweight='bold',pad=12)
fig.suptitle('L2 GND 개구 수정',x=.04,ha='left',fontsize=21,fontweight='bold')
fig.text(.04,.095,'회색: L2 GND   흰색: 동박 없는 부분   녹색: 복구한 GND   청록색: L1 패드·배선 투영',fontsize=11)
fig.text(.04,.035,'트레이스용 개구 3개 삭제 · RF 패드 개구 18개 유지 · 배선 아래 GND 복구\nAltium 저장 파일을 다시 읽어 그린 도면이며, 화면 캡처가 아닙니다.',fontsize=10,color='#486170')
fig.tight_layout(rect=[.01,.16,.99,.92]);fig.savefig(R/'L2_pad_only_before_after.png',dpi=180);plt.close(fig)

fig,axs=plt.subplots(1,2,figsize=(10,10.2))
for ax,fs,geom,title in zip(axs,[prior,src.fill],[old,g],['수정 전','수정 후']):
    field(ax,fs,geom,'In2.Cu',(8,32,7.5,48.5));ax.set_title(title,fontsize=17,fontweight='bold')
axs[1].annotate('VCC 연결면\n최소 폭 0.9 mm',(29.9,28.5),xytext=(26.0,19.0),fontsize=10,ha='center',arrowprops=dict(arrowstyle='->',color='#263c51'),bbox=dict(fc='white',ec='none',alpha=.94))
axs[1].annotate('VEE 연결면\n최소 폭 1.0 mm',(24.5,32.4),xytext=(27.6,36.0),fontsize=10,ha='center',arrowprops=dict(arrowstyle='->',color='#263c51'),bbox=dict(fc='white',ec='none',alpha=.94))
fig.suptitle('L3 전원 면 정리',x=.055,ha='left',fontsize=21,fontweight='bold')
fig.text(.055,.075,'빨강: VCC   파랑: VEE   회색: GND\n전원 면과 겹치는 GND 비아 126개 제거 · 총 비아 839개',fontsize=11)
fig.text(.055,.025,'L2 RF 패드 개구와 전원 동박 사이 최소 0.297 mm.\nAltium 저장 파일 기반 재렌더링 · 모든 층을 위에서 본 방향.',fontsize=10,color='#486170')
fig.tight_layout(rect=[.02,.13,.98,.94]);fig.savefig(R/'L3_clean_power_before_after.png',dpi=180);plt.close(fig)
(R/'plane_cleanup_figures.json').write_text(json.dumps(dict(pcb_sha256=digest,baseline=str(B),native_screenshot=False,figures=['L2_pad_only_before_after.png','L3_clean_power_before_after.png']),indent=2)+'\n')
print('Rendered L2 pad-only correction and L3 clean-plane before/after drawings')
