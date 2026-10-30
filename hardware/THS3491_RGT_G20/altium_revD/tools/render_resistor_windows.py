"""Show the actual saved L2 copper beneath RF resistor bodies and U1."""
from pathlib import Path
import json,hashlib,math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle,Polygon as Patch
from matplotlib.collections import PatchCollection
from shapely.geometry import Polygon,LineString,box
from shapely.affinity import rotate
from shapely.ops import unary_union
import render_review as src
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'review';B=R/'rf_resistor_windows_baseline/review_before'
old=json.loads((B/'native_import_copper.json').read_text());g=src.g
digest=hashlib.sha256((ROOT/'QSTL_THS3491_RGT_G20_RevD.PcbDoc').read_bytes()).hexdigest()
assert digest==json.loads((R/'native_import_check.json').read_text())['source_sha256']
plt.rcParams['font.family']='Malgun Gothic';plt.rcParams['axes.unicode_minus']=False
def copper(fs):return unary_union([Polygon(f['outline'],f['holes']).buffer(0) for f in fs if f['layer']=='In1.Cu' and f['net']=='GND'])
restored=copper(src.fill).difference(copper(old));src.colors['RESTORED']='#8bd29d'
rf={'FB','INV','inpt','AMP_OUT','RG_DRIVE','inm','inpt_raw','output'}
fig,axs=plt.subplots(1,2,figsize=(12,5.9))
for ax,fill,title in zip(axs,[old,src.fill],['수정 전 · 패드별 개구','수정 후 · 저항 패드 사이 연결, U1 아래 GND']):
    for f in fill:
        if f['layer']=='In1.Cu':src.polygon(ax,f)
    if fill is src.fill:
        for q in getattr(restored,'geoms',[restored]):
            if q.geom_type=='Polygon':src.polygon(ax,dict(outline=list(q.exterior.coords),holes=[list(h.coords) for h in q.interiors],net='RESTORED'))
    ax.add_collection(PatchCollection([Circle(v['pos'],v['diameter']/2) for v in g['vias']],facecolors=[src.color(v['net']) for v in g['vias']],edgecolors='#8195a1',linewidths=.4))
    ax.add_collection(PatchCollection([Circle(v['pos'],v['drill']/2) for v in g['vias']],facecolors='white',edgecolors='none'))
    for t in g['tracks']+g['arcs']:
        if t['layer']!='F.Cu' or t['net'] not in rf:continue
        if 'radius' in t:
            cx,cy=t['center'];a=math.atan2(t['start'][1]-cy,t['start'][0]-cx)
            pts=[(cx+t['radius']*math.cos(a+math.radians(t['angle'])*i/300),cy+t['radius']*math.sin(a+math.radians(t['angle'])*i/300)) for i in range(301)]
        else:pts=[t['start'],t['end']]
        q=LineString(pts).buffer(t['width']/2);ax.add_patch(Patch(list(q.exterior.coords),fc='#157f91',ec='none',alpha=.7))
    for p in g['pads']:
        if p['net'] not in rf or 'F.Cu' not in p['layers']:continue
        x,y=p['pos'];w,h=p['size'];q=rotate(box(x-w/2,y-h/2,x+w/2,y+h/2),-p['angle'],origin=(x,y))
        ax.add_patch(Patch(list(q.exterior.coords),fc='#66c7d3',ec='#186a79',lw=.6,alpha=.9))
    for ref in ['R2','R3','R4','R6','R7','U1','R14']:
        p=next(p for p in g['parts'] if p['ref']==ref);x,y=p['pos']
        if ref=='R14':y-=.9
        ax.text(x,y,ref,fontsize=10,color='#253f52',ha='center',va='center',bbox=dict(fc='white',alpha=.8,ec='none',pad=.8))
    ax.set_xlim(13,24.2);ax.set_ylim(31.1,24.3);ax.set_aspect('equal');ax.axis('off');ax.set_title(title,fontsize=14,fontweight='bold',pad=12)
fig.suptitle('L2 · 앰프 칩 개구 제거 / 저항 패드 사이 개구 연결',x=.04,ha='left',fontsize=20,fontweight='bold')
fig.text(.04,.115,'회색: L2 GND   흰색: 동박 없는 부분   녹색: U1 아래 복구한 GND   청록색: L1 패드·배선 투영',fontsize=10.5)
fig.text(.04,.06,'RF 저항 R1–R7·R14: 각 저항의 패드 사이까지 연결된 개구 8개. GND 패드와 비아 연결은 유지.\nU1 개구 5개 제거. 부품 사이 트레이스 아래와 L3 전원 면은 유지.',fontsize=10.5,color='#486170')
fig.text(.04,.025,'Altium 저장 파일을 다시 읽어 그린 도면이며, 화면 캡처가 아닙니다.',fontsize=10,color='#486170')
fig.tight_layout(rect=[.01,.18,.99,.92]);fig.savefig(R/'L2_resistor_windows_before_after.png',dpi=180);plt.close(fig)
(R/'resistor_windows_figure.json').write_text(json.dumps(dict(pcb_sha256=digest,baseline=str(B),native_screenshot=False,figure='L2_resistor_windows_before_after.png'),indent=2)+'\n')
print('Rendered saved L2 resistor-window correction')
