"""Draw imported native copper, with capacitor centers and L2 pad cutouts."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as MPath
from matplotlib.patches import PathPatch, Circle
from shapely.geometry import Polygon, Point, box
from shapely.affinity import rotate, translate
from shapely.geometry.polygon import orient

ROOT=Path(__file__).resolve().parents[1]; R=ROOT/'review'
g=json.loads((R/'native_geometry.json').read_text())
fills=json.loads((R/'native_import_copper.json').read_text())
audit=json.loads((R/'native_import_check.json').read_text()); assert not audit['errors']
entry=json.loads((ROOT/'input_rectangle_intent.json').read_text())
windows=json.loads((R/'rf_pad_windows.json').read_text())
parts={p['ref']:p for p in g['parts']}
plt.rcParams.update({'font.family':'Malgun Gothic','axes.unicode_minus':False})
colors={'GND':'#dae3e9','VIN_P':'#e9a66b','VIN_N':'#64a6c9','VCC':'#c85138','VEE':'#2864a6'}

def draw(ax,poly,color,edge='none',lw=.7,alpha=1):
    if poly.is_empty:return
    if poly.geom_type in {'MultiPolygon','GeometryCollection'}:
        for p in poly.geoms:
            if p.geom_type in {'Polygon','MultiPolygon'}:draw(ax,p,color,edge,lw,alpha)
        return
    poly=orient(poly,sign=1); vertices=[]; codes=[]
    for loop in [poly.exterior,*poly.interiors]:
        pts=list(loop.coords);vertices+=pts
        codes += [MPath.MOVETO]+[MPath.LINETO]*(len(pts)-2)+[MPath.CLOSEPOLY]
    ax.add_patch(PathPatch(MPath(vertices,codes),facecolor=color,edgecolor=edge,lw=lw,alpha=alpha))

def pad_shape(p):
    w,h=p['size']
    s=Point(0,0).buffer(w/2) if p['shape']==0 else box(-w/2,-h/2,w/2,h/2)
    return translate(rotate(s,-p['angle'],origin=(0,0)),*p['pos'])

def panel(ax,limits,layer):
    x0,x1,y0,y1=limits;clip=box(x0,y0,x1,y1)
    for f in fills:
        if f['layer']==layer:draw(ax,Polygon(f['outline'],f['holes']).intersection(clip),colors.get(f['net'],'#459386'))
    if layer=='F.Cu':
        for p in g['pads']:
            if 'F.Cu' in p['layers'] and clip.contains(Point(p['pos'])):
                draw(ax,pad_shape(p),colors.get(p['net'],'#459386'),'#536574')
                if p['drill'][0]: ax.add_patch(Circle(p['pos'],p['drill'][0]/2,color='white'))
    for v in g['vias']:
        if clip.contains(Point(v['pos'])):
            ax.add_patch(Circle(v['pos'],v['diameter']/2,facecolor=colors.get(v['net'],'#459386'),edgecolor='#8093a1',lw=.4))
            ax.add_patch(Circle(v['pos'],v['drill']/2,facecolor='white',edgecolor='none'))
    ax.set_xlim(x0,x1);ax.set_ylim(y1,y0);ax.set_aspect('equal');ax.set_facecolor('#fff')
    ax.spines[['top','right']].set_visible(False);ax.tick_params(labelsize=8)
    ax.set_xlabel('x (mm)',fontsize=9);ax.set_ylabel('보드 위에서 y (mm)',fontsize=9)

fig,axes=plt.subplots(1,2,figsize=(14,7.3))
for ax,sign,limits,refs,names in [
    (axes[0],'-15 V',(8.0,25.0,41.8,53.5),['C4','L2','C2'],['L1_NEGATIVE_INPUT','L1_VEE_ENTRY_VIA_ISLAND']),
    (axes[1],'+15 V',(12.6,29.6,2.3,14.1),['C1','L1','C3'],['L1_POSITIVE_INPUT','L1_VCC_ENTRY_VIA_ISLAND'])]:
    panel(ax,limits,'F.Cu')
    for name in names:
        b=entry['zone_rectangles_mm'][name];xs=[b[0],b[2],b[2],b[0],b[0]];ys=[b[1],b[1],b[3],b[3],b[1]]
        ax.plot(xs,ys,'--',color='#20364c',lw=1.1)
    for ref in refs:
        x,y=parts[ref]['pos'];ax.plot(x,y,'+',color='#10283d',ms=12,mew=1.5)
        dx=-1.8 if sign=='-15 V' else 1.9
        ax.annotate(ref+' 중심',(x,y),xytext=(x+dx,y),ha='center',va='center',fontsize=9,
                    arrowprops=dict(arrowstyle='-',color='#3a5060'),bbox=dict(facecolor='white',edgecolor='none',alpha=.9,pad=2))
    ax.set_title(sign+' 입력부 / L1',loc='left',fontsize=15,weight='bold',pad=14)
fig.suptitle('전원 동박 직사각형 · 커패시터 중심을 지나는 경계',fontsize=20,weight='bold',x=.065,ha='left')
fig.text(.065,.08,'점선: 직사각형 폴리곤 경계   +: 부품 중심   |   양쪽 180° 대칭',fontsize=11,color='#29475c')
fig.text(.065,.035,'-15 V: C2 ↑ 1.880 mm, C4·L2 ↑ 1.026 mm. +15 V는 반대 방향으로 대칭 이동. 저장된 Altium 파일 재판독 그림.',fontsize=10,color='#526b7c')
fig.tight_layout(rect=[.025,.12,.99,.93]);fig.savefig(R/'input_rectangle_verification.png',dpi=170);fig.savefig(R/'input_rectangle_verification.svg');plt.close(fig)

fig,axes=plt.subplots(1,2,figsize=(15,7),gridspec_kw={'width_ratios':[1.5,1]})
for ax,limits,title in [(axes[0],(5.3,32.4,19.6,37.3),'RF 영역 전체'),(axes[1],(13.7,24.0,24.5,31.5),'U1 · 피드백 · 출력 직렬 저항 확대')]:
    panel(ax,limits,'In1.Cu');clip=box(limits[0],limits[2],limits[1],limits[3])
    for win in windows:
        if clip.intersects(Polygon(win['outline_mm'])):
            draw(ax,Polygon(win['pad_outline_mm']),'#f8bd53','#b77312',.8,.8)
            x,y=parts[win['ref']]['pos']
    for ref in ['R1','R2','R3','R4','R5','R6','R7','R14','R15','U1']:
        x,y=parts[ref]['pos']
        if clip.contains(Point(x,y)):
            ax.text(x,y,ref,fontsize=8,ha='center',va='center',color='#183248',bbox=dict(facecolor='white',edgecolor='none',alpha=.9,pad=1.5))
    ax.set_title(title,fontsize=13,loc='left',pad=13)
fig.suptitle('L2 GND 개구 / RF 신호 패드 19개 아래 구리 겹침 0',fontsize=20,weight='bold',x=.065,ha='left')
fig.text(.065,.09,'회색: 실제 L2 GND 동박   흰색: 개구   주황: 상면 RF 신호 패드 투영',fontsize=11,color='#29475c')
fig.text(.065,.045,'각 패드 외곽 + 0.10 mm 여유. GND 패드·U1 노출 방열 패드 유지. 저장 파일 재판독 결과이며 SI/EM 해석 결과는 아님.',fontsize=10,color='#526b7c')
fig.tight_layout(rect=[.025,.14,.99,.93]);fig.savefig(R/'L2_RF_pad_clearance.png',dpi=170);fig.savefig(R/'L2_RF_pad_clearance.svg');plt.close(fig)
if entry.get('filtered_via_arrays'):
    fig,axes=plt.subplots(1,2,figsize=(13,6))
    for ax,spec,limits in zip(axes,entry['filtered_via_arrays'],[(8.8,16.0,42.0,47.7),(21.6,28.8,8.2,13.9)]):
        panel(ax,limits,'F.Cu')
        x0,y0,x1,y1=entry['zone_rectangles_mm'][spec['zone']]
        ax.plot([x0,x1,x1,x0,x0],[y0,y0,y1,y1,y0],'--',color='#20364c',lw=1.1)
        ax.set_title(spec['net']+' / 6.0 mm 폭 + 4×4 비아 배열',loc='left',fontsize=13,weight='bold',pad=14)
    fig.suptitle('입력 필터 후단 전원 면 확장 / 전원 비아 32개 추가',fontsize=19,weight='bold',x=.065,ha='left')
    fig.text(.065,.09,'비아 패드 Ø0.40 mm · 드릴 Ø0.20 mm · 피치 0.80 mm / VCC·VEE 각각 16개',fontsize=11,color='#29475c')
    fig.text(.065,.04,'커패시터 중심 경계·L3 전원 연결 유지. 확장 경계의 GND 비아 3개 제거. Altium 저장 파일을 재판독한 그림.',fontsize=10,color='#526b7c')
    fig.tight_layout(rect=[.025,.20,.99,.93]);fig.savefig(R/'entry_plane_via_arrays.png',dpi=180);fig.savefig(R/'entry_plane_via_arrays.svg');plt.close(fig)
print('Saved input rectangles and L2 RF pad clearance figures')
