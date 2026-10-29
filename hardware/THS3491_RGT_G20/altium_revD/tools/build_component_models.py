"""Prepare portable STEP models. Run with FreeCAD 0.20's bin/python.exe.

Standard passives/header retain KiCad's licensed STEP originals. The custom
models are nominal package / envelope representations, not vendor-certified
manufacturing geometry. No PCB placement or copper is changed by this script.
"""
from pathlib import Path
import hashlib
import json
import re
import shutil
import FreeCAD as App
import Part

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'models3d'
LIB = Path('C:/Program Files/KiCad/6.0/share/kicad/3dmodels')
OUT.mkdir(exist_ok=True)
SILVER = (.72, .74, .77)
BLACK = (.10, .11, .13)
TAN = (.63, .45, .25)

def box(x, y, z, dx, dy, dz):
    return Part.makeBox(dx, dy, dz, App.Vector(x, y, z))

def colored_step(name, shapes, colors):
    """Write a STEP BREP with explicit AP214 solid presentation colors."""
    path = OUT / name
    Part.makeCompound(shapes).exportStep(str(path))
    text = path.read_text(encoding='utf-8')
    solids = re.findall(r'#(\d+)\s*=\s*MANIFOLD_SOLID_BREP\(', text)
    assert len(solids) == len(colors), (name, len(solids), len(colors))
    context = re.search(r'#(\d+)\s*=\s*\(\s*GEOMETRIC_REPRESENTATION_CONTEXT', text).group(1)
    index = max(map(int, re.findall(r'#(\d+)\s*=', text))) + 1
    lines = []
    def add(value):
        nonlocal index
        n = index; index += 1; lines.append('#{}={};'.format(n, value)); return n
    styles = []
    for solid, color in zip(solids, colors):
        c = add("COLOUR_RGB('',{},{},{})".format(*color))
        f = add("FILL_AREA_STYLE_COLOUR('',#{})".format(c))
        a = add("FILL_AREA_STYLE('',(#{0}))".format(f))
        s = add('SURFACE_STYLE_FILL_AREA(#{})'.format(a))
        side = add("SURFACE_SIDE_STYLE('',(#{0}))".format(s))
        usage = add('SURFACE_STYLE_USAGE(.BOTH.,#{})'.format(side))
        p = add('PRESENTATION_STYLE_ASSIGNMENT((#{}))'.format(usage))
        styles.append(add("STYLED_ITEM('',(#{0}),#{1})".format(p, solid)))
    add("MECHANICAL_DESIGN_GEOMETRIC_PRESENTATION_REPRESENTATION('',({}),#{})".format(','.join('#'+str(s) for s in styles), context))
    text = text.replace('ENDSEC;\nEND-ISO-10303-21;', '\n'.join(lines)+'\nENDSEC;\nEND-ISO-10303-21;')
    path.write_text(text, encoding='utf-8')

def chip(name, length, width, height, term, color):
    parts = [box(-length/2+term, -width/2, .025, length-2*term, width, height-.025),
             box(-length/2, -width/2, 0, term, width, height),
             box(length/2-term, -width/2, 0, term, width, height)]
    colored_step(name, parts, [color, SILVER, SILVER])

standard = {
 'R_0603.step':'Resistor_SMD.3dshapes/R_0603_1608Metric.step',
 'C_0402.step':'Capacitor_SMD.3dshapes/C_0402_1005Metric.step',
 'C_0603.step':'Capacitor_SMD.3dshapes/C_0603_1608Metric.step',
 'C_0805.step':'Capacitor_SMD.3dshapes/C_0805_2012Metric.step',
 'Header_1x02_2p54.step':'Connector_PinHeader_2.54mm.3dshapes/PinHeader_1x02_P2.54mm_Vertical.step',
}
for name, source in standard.items():
    shutil.copy2(LIB/source, OUT/name)
chip('C_1206_H0p85.step', 3.2, 1.6, .85, .45, TAN)
chip('Ferrite_0805_H0p85.step', 2., 1.25, .85, .5, BLACK)

# RGT: 3x3 mm, 0.5-mm pitch, pin 1 upper left in top view, height 1 mm.
# This is a nominal visualization; the exposed terminal is not a land pattern.
qfn = [box(-1.5, -1.5, .05, 3, 3, .95)]
colors = [BLACK]
qfn.append(box(-.825, -.825, 0, 1.65, 1.65, .05)); colors.append(SILVER)
for coord in [-.75, -.25, .25, .75]:
    qfn += [box(-1.5,coord-.12,0,.4,.24,.12), box(1.1,coord-.12,0,.4,.24,.12),
            box(coord-.12,-1.5,0,.24,.4,.12), box(coord-.12,1.1,0,.24,.4,.12)]
    colors += [SILVER]*4
qfn.append(Part.makeCylinder(.12,.006,App.Vector(-1.04,1.04,1.0))); colors.append((.65,.65,.65))
colored_step('THS3491_RGT_nominal.step',qfn,colors)

# 7109DG: overall envelope from Boyd drawing, simplified sheet-metal fins.
# The mounting tab is at the footprint origin. The cage is 7.134 mm behind it.
# Nominal sheet thickness and slot details are visual approximations.
t=.5; y0=-16.824; length=19.38; height=11.43
hs=[box(-5.715,-2.54,0,11.43,5.08,t),
    box(-5.715,y0,0,11.43,length,t)]
for sign in [-1,1]:
    xmin=7.62 if sign>0 else -8.12
    hs.append(box(xmin,y0,0,t,length,height))
    for i in range(5):
        yy=y0+i*3.876
        xx=8.12 if sign>0 else -12.7
        hs.append(box(xx,yy,height-t,4.58,3.15,t))
        xx=12.2 if sign>0 else -12.7
        hs.append(box(xx,yy,0,t,3.15,height))
    xx=5.715 if sign>0 else -8.12
    hs.append(box(xx,y0,0,2.405,length,t))
colored_step('7109DG_simplified.step',hs,[SILVER]*len(hs))

# Exact part-number STEP distributed by Pulse Research Lab from manufacturer
# models. Shift the seating plane (-0.127 mm) to local z=0. Preserve the source.
s=Part.Shape(); s.read(str(OUT/'sources/SMA_142-0701-851.stp'))
s.translate(App.Vector(0,0,.127))
colored_step('SMA_142-0701-851_seated.step',s.Solids,[(.76,.58,.22)]*len(s.Solids))

g=json.loads((ROOT/'review/native_geometry.json').read_text(encoding='utf-8'))
placements=[]; exclusions=[]
for part in g['parts']:
    ref=part['ref']; angle=part['angle']; x,y=part['pos']; model=None
    if ref=='R15': continue  # Output load removed by the 2026-10-27 request.
    if ref=='R5': reason='DNP: not fitted'
    elif ref in ['H1','H2','H3','H4']: reason='Mounting hole; no fitted hardware'
    elif ref in ['J4','J5','J6','J8','TP1']: reason='Bare solder/test pad; no component body'
    elif ref.startswith('R'): model='R_0603.step'
    elif ref in ['C1','C2']: model='C_1206_H0p85.step'
    elif ref in ['C3','C4']: model='C_0805.step'
    elif ref in ['C5','C6','C7']: model='C_0603.step'
    elif ref=='C8': model='C_0402.step'
    elif ref in ['L1','L2']: model='Ferrite_0805_H0p85.step'
    elif ref=='U1': model='THS3491_RGT_nominal.step'
    elif ref in ['J1','J2','J3']: model='SMA_142-0701-851_seated.step'; angle+=90
    elif ref=='J7': model='Header_1x02_2p54.step'
    elif ref=='H9': model='7109DG_simplified.step'
    else: raise ValueError(ref)
    if model:
        placements.append(dict(ref=ref,model=model,x_mm=x,y_altium_mm=68.58-y,
                               rotation_z=angle,side='bottom' if part['layer']=='B.Cu' else 'top'))
    else: exclusions.append(dict(ref=ref,reason=reason))
assert len(placements)==24 and len(exclusions)==10
assets=[]
for path in sorted(OUT.glob('*.step')):
    shape=Part.Shape();shape.read(str(path)); b=shape.BoundBox
    assert shape.isValid() and len(shape.Solids)>0,path
    mesh=[]
    for solid in shape.Solids:
        vertices,faces=solid.tessellate(.06)
        mesh.append({'vertices':[[v.x,v.y,v.z] for v in vertices], 'faces':faces})
    meshpath=ROOT/'staging/models3d_probe'/ (path.stem+'.mesh.json')
    meshpath.write_text(json.dumps(mesh),encoding='utf-8')
    assets.append(dict(file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                       bounds_mm=[b.XMin,b.YMin,b.ZMin,b.XMax,b.YMax,b.ZMax],solids=len(shape.Solids),
                       source=standard.get(path.name,'See models3d/README.md')))
(OUT/'placements.json').write_text(json.dumps(dict(placements=placements,excluded=exclusions,assets=assets),indent=2)+'\n',encoding='utf-8')
print('Prepared',len(assets),'models for',len(placements),'fitted components')
