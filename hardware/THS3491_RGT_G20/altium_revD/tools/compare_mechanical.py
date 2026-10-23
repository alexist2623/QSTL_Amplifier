"""Compare exact Rev D CAD with explicitly approximate TI SLOU063 artwork.

TI publishes approximate board size, but no dimensioned mounting-hole drawing.
Do not use the illustration-normalized TI coordinates as drilling dimensions.
"""
from pathlib import Path
import json
import numpy as np
import fitz
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle

ROOT=Path(__file__).resolve().parents[1]; R=ROOT/'review'
pdf=ROOT/'reference/THS4021EVM_SLOU063.pdf'
g=json.loads((R/'native_geometry.json').read_text())
mounts={p['ref']:p for p in g['pads'] if p['npth']}
qsize=np.array([g['board_width'],g['board_height']])
qholes=np.array([mounts[r]['pos'] for r in ['H3','H4','H1','H2']])
qspacing=qholes[3]-qholes[0]
page=fitz.open(pdf)[13]
outline=next(d['rect'] for d in page.get_drawings() if d['rect'].y0>390 and d['rect'].width>230)
circles=[d['rect'] for d in page.get_drawings() if d['type']=='fs' and
         d['rect'].y0>390 and 13<d['rect'].width<20 and
         (d['rect'].x0<190 or d['rect'].x0>400)]
assert len(circles)==4
circles.sort(key=lambda r:(r.y0>500,r.x0))
tsize=np.array([1.7*25.4,1.4*25.4])
tholes=np.array([[(r.x0+r.x1)/2-outline.x0,(r.y0+r.y1)/2-outline.y0] for r in circles])
tholes*=tsize/np.array([outline.width,outline.height])
# Symmetric nominal grid from the four artwork centers. The artwork itself
# has small drafting asymmetries, so retain raw estimates in the data report.
tspacing=np.array([np.mean(tholes[[1,3],0])-np.mean(tholes[[0,2],0]),
                   np.mean(tholes[[2,3],1])-np.mean(tholes[[0,1],1])])
offsets=tsize/2+np.array([[-1,-1],[1,-1],[-1,1],[1,1]])*tspacing/2
delta=tspacing-qspacing
report=dict(units='mm',orientation='Top view, output SMA on right; no rotation',
            qstl=dict(board_size=qsize.tolist(),mount_hole_pitch=qspacing.tolist(),hole_diameter=3.175,
                      holes={r:mounts[r]['pos'] for r in ['H3','H4','H1','H2']}),
            ths4021evm=dict(board_size_approx=tsize.tolist(),hole_pitch_estimate=tspacing.tolist(),
                           artwork_center_estimates=tholes.tolist(),
                           method='Normalize Figure 2-1 board outline independently in X/Y to the approximate 1.7 by 1.4 inch size; average opposite hole rows/columns',
                           limitation='Figure 2-1 is explicitly not to scale. Hole dimensions and tolerances are not provided. These are rough illustration-based estimates, not verified mechanical coordinates.',
                           source_url='https://www.ti.com/lit/ug/slou063/slou063.pdf',pdf_page=14),
            board_size_difference_qstl_minus_ti=(qsize-tsize).tolist(),
            pitch_difference_ti_minus_qstl=delta.tolist(),
            conclusion='No direct four-hole mounting compatibility in this orientation; exact adapter dimensions require TI mechanical CAD or physical measurement')
(R/'mechanical_compare_THS4021EVM.json').write_text(json.dumps(report,indent=2))

plt.rcParams.update({'font.family':'Malgun Gothic','axes.unicode_minus':False,'svg.fonttype':'none'})
blue='#1465ad'; orange='#dc7b14'; ink='#193145'
fig=plt.figure(figsize=(13,9),facecolor='#f7f9fc')
fig.text(.06,.94,'QSTL Rev D / THS4021EVM 기구 비교',fontsize=21,weight='bold',color=ink)
fig.text(.06,.903,'같은 방향의 윗면 기준(출력 SMA 오른쪽)  |  단위: mm  |  TI 홀 좌표는 그림 기반 추정',fontsize=10.5,color='#4d6070')

def base(pos,title,xlim,ylim):
    ax=fig.add_axes(pos); ax.set_aspect('equal'); ax.set_xlim(*xlim); ax.set_ylim(*ylim)
    ax.invert_yaxis(); ax.axis('off'); ax.set_title(title,fontsize=13,weight='bold',pad=15,color=ink)
    return ax
def dim(ax,a,b,label,color,offset=(0,0)):
    a=np.array(a); b=np.array(b)
    ax.annotate('',xy=b,xytext=a,arrowprops=dict(arrowstyle='<->',color=color,lw=1.1))
    mid=(a+b)/2+offset
    ax.text(*mid,label,color=color,fontsize=10,ha='center',va='center',bbox=dict(facecolor='#f7f9fc',edgecolor='none',pad=2))

ax=base([.045,.235,.43,.60],'① 보드 중심을 맞춘 외곽 비교',(-31,31),(-39,39))
for size,holes,col in [(qsize,qholes,blue),(tsize,offsets,orange)]:
    ax.add_patch(Rectangle(-size/2,*size,facecolor=col,alpha=.07,edgecolor='none'))
    ax.add_patch(Rectangle(-size/2,*size,fill=False,edgecolor=col,lw=2.1,linestyle='-' if col==blue else '--'))
    for p in holes-size/2:
        ax.add_patch(Circle(p,1.5875,fill=False,edgecolor=col,lw=1.9))
        ax.plot(p[0],p[1],'+',color=col,ms=5)
dim(ax,[-qsize[0]/2,37],[qsize[0]/2,37],f'{qsize[0]:.2f}',blue)
dim(ax,[-27,-qsize[1]/2],[-27,qsize[1]/2],f'{qsize[1]:.2f}',blue,(-1.0,0))
ax.text(0,-23,'TI 약 43.18 × 35.56',ha='center',fontsize=11,color=orange,
        bbox=dict(facecolor='#f7f9fc',edgecolor='none',pad=3))
ax.text(0,26,'Rev D 41.66 × 68.58',ha='center',fontsize=11,color=blue)

ax=base([.525,.235,.43,.60],'② 왼쪽 위 홀 하나를 맞춘 홀 간격 비교',(-9,47),(-7,67))
for spacing,col in [(qspacing,blue),(tspacing,orange)]:
    ax.add_patch(Rectangle((0,0),*spacing,fill=False,edgecolor=col,lw=1.4,linestyle='--'))
    for x,y in [(0,0),(spacing[0],0),(0,spacing[1]),tuple(spacing)]:
        ax.add_patch(Circle((x,y),1.5875,fill=False,edgecolor=col,lw=2))
ax.text(-1,-4,'기준 홀',fontsize=10,color=ink,ha='right')
dim(ax,[0,63],[qspacing[0],63],f'Rev D {qspacing[0]:.2f}',blue)
dim(ax,[0,tspacing[1]+4],[tspacing[0],tspacing[1]+4],f'TI 추정 약 {tspacing[0]:.1f}',orange)
dim(ax,[-6,0],[-6,qspacing[1]],f'{qspacing[1]:.2f}',blue)
dim(ax,[tspacing[0]+5,0],[tspacing[0]+5,tspacing[1]],f'약 {tspacing[1]:.1f}',orange)
ax.annotate(f'오른쪽 홀: 약 {delta[0]:+.1f} mm',xy=(tspacing[0],0),xytext=(17,-5),
            fontsize=10,color=ink,arrowprops=dict(arrowstyle='-',color='#718190'))
ax.annotate(f'아래쪽 홀: 약 {abs(delta[1]):.1f} mm 위',xy=(tspacing[0],tspacing[1]),xytext=(18,44),
            fontsize=10,color=ink,ha='center',arrowprops=dict(arrowstyle='->',color='#718190'))

fig.text(.06,.178,'파랑: Rev D CAD 실치수     주황: TI 보드 공칭 크기 / 장착홀 추정',fontsize=11,color=ink)
fig.text(.06,.134,f'Rev D는 폭이 약 1.52 mm 작고 높이가 약 33.02 mm 큽니다. 이 방향으로는 4개 홀이 함께 맞지 않습니다.',fontsize=11.5,weight='bold',color=ink)
fig.text(.06,.092,'주의: TI SLOU063 Figure 2-1은 “not to scale” 참고 그림입니다. 홀 간격·홀 지름의 치수 및 공차는 미공개입니다.',fontsize=10,color='#924c0b')
fig.text(.06,.066,'주황 원은 위치 비교용 표시이며 TI 실제 홀 지름을 나타내지 않습니다. 가공·어댑터 설계에는 TI CAD 또는 실측값이 필요합니다.',fontsize=9.4,color='#924c0b')
fig.text(.06,.035,'출처: ti.com/tool/THS4021EVM · SLOU063 pp.1-2, 2-2  |  Rev D native_geometry.json  |  2026-10-22',fontsize=9,color='#607384')
fig.savefig(R/'mechanical_compare_THS4021EVM.png',dpi=190)
fig.savefig(R/'mechanical_compare_THS4021EVM.svg')
print(json.dumps(report,indent=2))
