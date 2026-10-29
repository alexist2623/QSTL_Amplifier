"""Render saved/reopened native pad shapes and the cleaned C7 copper."""
from pathlib import Path
import json, math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, PathPatch
from matplotlib.path import Path as MPath
from shapely.geometry import box, Polygon, LineString, Point
from shapely.affinity import rotate, translate
from shapely.geometry.polygon import orient

R=Path(__file__).resolve().parents[1]/'review'
g=json.loads((R/'native_geometry.json').read_text())
audit=json.loads((R/'native_import_check.json').read_text())
assert not audit['errors'] and len(audit['rectangular_pads_verified'])==19
shapes={(x['ref'],x['pad']):x for x in audit['rectangular_pads_verified']}
assert all(x['radius_mm']==0 for x in shapes.values())
fills=json.loads((R/'native_import_copper.json').read_text())
plt.rcParams.update({'font.family':'Malgun Gothic','axes.unicode_minus':False})
colors={'GND':'#d7e0e7','VCC':'#d64a3c','VEE':'#246bb6','AMP_OUT':'#13917e','output':'#13917e'}
def draw(ax,poly,color,edge='none',lw=.7):
    if poly.is_empty:return
    if poly.geom_type=='MultiPolygon':
        for p in poly.geoms:draw(ax,p,color,edge,lw)
        return
    poly=orient(poly,sign=1); verts=[]; codes=[]
    for loop in [poly.exterior,*poly.interiors]:
        p=list(loop.coords); verts+=p
        codes += [MPath.MOVETO]+[MPath.LINETO]*(len(p)-2)+[MPath.CLOSEPOLY]
    ax.add_patch(PathPatch(MPath(verts,codes),facecolor=color,edgecolor=edge,lw=lw))
def panel(ax,limits):
    x0,x1,y0,y1=limits; clip=box(x0,y0,x1,y1)
    for f in fills:
        if f['layer']=='F.Cu':draw(ax,Polygon(f['outline'],f['holes']).intersection(clip),colors.get(f['net'],'#956caa'))
    for t in g['tracks']:
        if t['layer']=='F.Cu':draw(ax,LineString([t['start'],t['end']]).buffer(t['width']/2).intersection(clip),colors.get(t['net'],'#956caa'))
    for p in g['pads']:
        if 'F.Cu' not in p['layers'] or not clip.contains(Point(p['pos'])):continue
        w,h=p['size']; radius=shapes.get((p['ref'],p['num']),{}).get('radius_mm',0)
        if p['shape']==0:poly=Point(0,0).buffer(w/2)
        else:poly=box(-w/2+radius,-h/2+radius,w/2-radius,h/2-radius).buffer(radius,resolution=48) if radius else box(-w/2,-h/2,w/2,h/2)
        poly=translate(rotate(poly,-p['angle'],origin=(0,0)),*p['pos'])
        draw(ax,poly,colors.get(p['net'],'#956caa'),'#455c6c')
    for v in g['vias']:
        if clip.contains(Point(v['pos'])):
            ax.add_patch(Circle(v['pos'],v['diameter']/2,facecolor=colors.get(v['net'],'#956caa'),edgecolor='#6f8495',lw=.6))
            ax.add_patch(Circle(v['pos'],v['drill']/2,facecolor='white',edgecolor='none'))
    ax.set_xlim(x0,x1);ax.set_ylim(y1,y0);ax.set_aspect('equal');ax.set_facecolor('#fbfcfe')
    ax.spines[['top','right']].set_visible(False); ax.tick_params(labelsize=8)
    ax.set_xlabel('x (mm)',fontsize=9);ax.set_ylabel('보드 위에서 y (mm)',fontsize=9)

fig=plt.figure(figsize=(14,6.1),facecolor='white')
fig.text(.05,.94,'직각 사각형 패드 19개 / 모서리 반경 0',fontsize=21,weight='bold',color='#193145')
fig.text(.05,.88,'Altium 25.8.1 저장 → 닫기 → 재열기: Rectangle 형상 19개 및 반경 0 검사 통과',fontsize=11,color='#456174')
a=fig.add_axes([.055,.26,.63,.52]);panel(a,(20.6,32.5,26.6,30.6))
a.set_title('R14: 직각 사각형 / R15 제거',loc='left',fontsize=12,pad=14)
a.annotate('R14  ·  R = 0',xy=(23.025,27.94),xytext=(24.2,27.05),fontsize=10,
           arrowprops=dict(arrowstyle='-',color='#61788c'),color='#193145')
a.annotate('R15 제거 · 출력 경로 유지',xy=(31,27.94),xytext=(29.5,30),fontsize=10,ha='center',
           arrowprops=dict(arrowstyle='-',color='#61788c'),color='#193145')
b=fig.add_axes([.76,.24,.18,.55]);panel(b,(23.9,25.9,30.05,33.0))
b.set_title('C7: 비아 연결 유지',fontsize=12,pad=14)
b.text(24.9,30.2,'VCC',ha='center',fontsize=9,color='#b33226')
b.text(24.9,32.85,'VEE 돌출 동박 제거',ha='center',fontsize=9,color='#17538a')
fig.text(.05,.13,'네이티브 PCB를 독립 판독기로 다시 읽은 형상입니다. Altium 화면 캡처는 아닙니다.',fontsize=10,color='#526c7e')
fig.text(.05,.08,'R14 2개 + U1 17개: 크기·위치·넷 유지. R15 1 MΩ 출력 부하와 두 패드를 제거하고 동박 갱신.',fontsize=9.5,color='#526c7e')
fig.savefig(R/'pad_shape_verification.png',dpi=180)
fig.savefig(R/'pad_shape_verification.svg')
print('Saved shape verification figures')
