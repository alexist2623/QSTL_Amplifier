"""Review rendering of native-audited embedded STEP geometry; not a screenshot."""
from pathlib import Path
import json
import math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

ROOT=Path(__file__).resolve().parents[1]
audit=json.loads((ROOT/'review/component_3d_check.json').read_text(encoding='utf-8'))
g=json.loads((ROOT/'review/native_geometry.json').read_text(encoding='utf-8'))
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})
W,H=41.65601,68.58
T=1.6
meshes={}
for r in audit['components']:
    model=r['model']
    if model not in meshes:
        meshes[model]=json.loads((ROOT/'staging/models3d_probe'/(Path(model).stem+'.mesh.json')).read_text())

def add(ax, faces, color, edge='none', alpha=1):
    p=Poly3DCollection(faces,facecolors=color,edgecolors=edge,linewidths=.15,alpha=alpha,zsort='average')
    ax.add_collection3d(p)

def color_for(r,index):
    ref=r['ref']
    if ref in ['J1','J2','J3']:return [.78,.61,.26]
    if ref=='H9':return [.65,.69,.74]
    if ref=='U1':return [.1,.11,.13] if index==0 else [.72,.74,.77]
    if ref.startswith('C'):return [.67,.47,.26] if index==0 else [.72,.74,.77]
    if ref=='J7':return [.12,.13,.15] if index==0 else [.83,.66,.3]
    return [.1,.11,.13] if index==0 else [.72,.74,.77]

def scene(ax,side='top',core=False):
    x0,x1,y0,y1=(12,27,H-34,H-22) if core else (0,W,0,H)
    top=[[x0,y0,0],[x1,y0,0],[x1,y1,0],[x0,y1,0]]
    bot=[[x0,y0,-T],[x1,y0,-T],[x1,y1,-T],[x0,y1,-T]]
    add(ax,[top,bot],[.18,.40,.22])
    for i in range(4):add(ax,[[top[i],top[(i+1)%4],bot[(i+1)%4],bot[i]]],[.52,.47,.29])
    # Pads and mounting holes are drawn at the same coordinates as audited copper.
    for p in g['pads']:
        bottom='B.Cu' in p['layers'] and 'F.Cu' not in p['layers']
        if (side=='top')==bottom:continue
        x,y=p['pos'];y=H-y;z=-T-.008 if bottom else .008
        if core and not (x0<x<x1 and y0<y<y1):continue
        if p['npth']:
            radius=p['drill'][0]/2
            theta=np.linspace(0,2*np.pi,36)
            face=np.column_stack([x+radius*np.cos(theta),y+radius*np.sin(theta),np.full_like(theta,z)])
            add(ax,[face],[.07,.08,.08]);continue
        sx,sy=p['size'];a=math.radians(p['angle'])
        pts=np.array([[-sx/2,-sy/2],[sx/2,-sy/2],[sx/2,sy/2],[-sx/2,sy/2]])
        rot=np.array([[math.cos(a),-math.sin(a)],[math.sin(a),math.cos(a)]])
        pts=pts@rot.T+[x,y];face=np.column_stack([pts,np.full(4,z)])
        add(ax,[face],[.78,.65,.29])
    for r in audit['components']:
        if core and r['ref'] not in ['U1','R2','R3','R4','R6','R7','R14','C5','C6','C7']:continue
        # Hide the far-side bodies in each inspection view to avoid painter
        # ordering artifacts; each side is rendered in its own panel.
        if r['side']!=side:continue
        a=math.radians(r['rotation_z']);rot=np.array([[math.cos(a),-math.sin(a)],[math.sin(a),math.cos(a)]])
        component_faces=[];component_colors=[]
        for i,m in enumerate(meshes[r['model']]):
            v=np.array(m['vertices']);v[:,:2]=v[:,:2]@rot.T+np.array(r['position_mm'][:2])
            if side=='bottom':v[:,2]=-T-v[:,2]
            else:v[:,2]+=.015
            f=np.array(m['faces']);faces=v[f]
            norms=np.cross(faces[:,1]-faces[:,0],faces[:,2]-faces[:,0]);norms/=np.maximum(np.linalg.norm(norms,axis=1)[:,None],1e-9)
            light=np.array([-.4,-.3,.85 if side=='top' else -.85]);shade=.52+.48*np.maximum(0,norms@light)
            colors=np.minimum(1,np.array(color_for(r,i))[None,:]*shade[:,None])
            component_faces.extend(faces);component_colors.extend(colors)
        add(ax,component_faces,component_colors)
    if core:
        ax.set_xlim(12,27);ax.set_ylim(H-34,H-22);ax.set_zlim(-.4,4);ax.set_box_aspect((15,12,4.4))
    else:
        ax.set_xlim(-10,W+10);ax.set_ylim(-3,H+3);ax.set_zlim(-14,12);ax.set_box_aspect((W+20,H+6,26))
    ax.view_init(elev=42 if side=='top' else -45,azim=-65 if side=='top' else -115)
    ax.set_proj_type('ortho');ax.set_axis_off();ax.set_facecolor('#f3f5f7')

fig=plt.figure(figsize=(15,9),facecolor='#f3f5f7')
axes=[fig.add_subplot(1,3,i+1,projection='3d',computed_zorder=False) for i in range(3)]
scene(axes[0]);scene(axes[1],'bottom');scene(axes[2],core=True)
for ax,t in zip(axes,['Top assembly | 25 bodies','Bottom | 7109DG envelope','RF core | QFN and passives']):ax.set_title(t,pad=4,fontweight='bold')
fig.suptitle('Rev D - embedded component 3D models',fontsize=20,fontweight='bold',y=.94)
fig.text(.05,.13,'26 fitted components / 11 STEP assets / two PJ-102AH DC inputs\nDNP, test pad and bare mounting holes intentionally have no body.',fontsize=12)
fig.text(.05,.065,'Re-rendered from native-audited STEP placement. This is not an Altium screenshot.\nNominal package models; PJ-102AH details and 7109DG fins are simplified.',fontsize=10,color='#4d5660')
fig.subplots_adjust(left=.01,right=.99,top=.85,bottom=.20,wspace=.01)
fig.savefig(ROOT/'review/component_3d_overview.png',dpi=180)
plt.close(fig)
print(ROOT/'review/component_3d_overview.png')
