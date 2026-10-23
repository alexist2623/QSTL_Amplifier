"""Apply the approved placement intent to the checked-in Rev C geometry.

Run with Python 3 and shapely. Coordinates are mm, viewed from the top,
with y increasing downward. Rev C and the planning files remain read-only.
"""
from pathlib import Path
import copy
import json
import math

from shapely.geometry import Point, Polygon, LineString, box
from shapely.affinity import rotate, translate

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / 'altium_revC'
REVIEW = ROOT / 'review'
REVIEW.mkdir(parents=True, exist_ok=True)
g = json.loads((SOURCE / 'review/native_geometry.json').read_text())
intent = json.loads((ROOT.parent / 'planning/power_plan_intent.json').read_text())
original = copy.deepcopy(g)
# User's final shape correction: sharp rectangular copper, with no corner radius.
shape_targets=[p for p in g['pads'] if p['ref'] in {'R14','R15','U1'}]
assert len(shape_targets)==21
for pad in shape_targets:
    pad['shape']=1  # KiCad PAD_SHAPE_RECT; Altium eRectangular = 2.
    pad['roundrect_ratio']=0
moves = {r: intent[k] for r, k in [('C3', 'C3_filter_side'), ('C4', 'C4_filter_side'),
                                  ('C5', 'C5_TI_original'), ('C6', 'C6_TI_original')]}
entry_intent=json.loads((ROOT/'input_rectangle_intent.json').read_text())
moves.update(entry_intent['moves'])
for f in g['parts']:
    if f['ref'] not in moves:
        continue
    x, y, angle = moves[f['ref']]
    ox, oy = f['pos']
    da = angle - f['angle']
    a = math.radians(da)
    for pad in g['pads']:
        if pad['ref'] != f['ref']:
            continue
        dx, dy = pad['pos'][0] - ox, pad['pos'][1] - oy
        pad['pos'] = [round(x + dx * math.cos(a) + dy * math.sin(a), 6),
                      round(y - dx * math.sin(a) + dy * math.cos(a), 6)]
        pad['angle'] = (pad['angle'] + da) % 360
    f['pos'], f['angle'] = [x, y], angle

def rect(x0, y0, x1, y1):
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]

outlines = {
    'L1_VCC_LOCAL_PIN_ISLAND': rect(18.90, 24.33, 20.25, 26.88),
    'L1_VEE_LOCAL_PIN_ISLAND': rect(18.90, 29.00, 20.25, 31.55),
    'L1_VCC_ENTRY_VIA_ISLAND': rect(25.59202, 8.40, 28.09202, 11.40),
    'L1_VEE_ENTRY_VIA_ISLAND': rect(9.50, 44.48, 12.00, 47.48),
}
outlines.update({name:rect(*bounds) for name,bounds in entry_intent['zone_rectangles_mm'].items()})
# C7 uses one via in each pad to reach its supply on L3. These two tiny
# surface polygons add no connection; the VEE thermal leaves a protruding stub.
g['zones']=[z for z in g['zones'] if z['name'] not in ['L1_C7_VCC','L1_C7_VEE']]
rf_refs={'R1','R2','R3','R4','R5','R6','R7','R14','R15','U1'}
rf_nets={'inm','RG_DRIVE','INV','FB','inpt_raw','inpt','AMP_OUT','output'}
rf_windows=[]
for pad in g['pads']:
    if pad['ref'] not in rf_refs or pad['net'] not in rf_nets: continue
    w,h=pad['size']; margin=.10
    footprint=translate(rotate(box(-w/2,-h/2,w/2,h/2),-pad['angle'],origin=(0,0)),*pad['pos'])
    window=footprint.buffer(margin,join_style=2)
    outline=[[round(x,6),round(y,6)] for x,y in list(window.exterior.coords)[:-1]]
    name=f"L2_RF_PAD_{pad['ref']}_{pad['num']}"
    g['zones'].append(dict(name=name,net='',layer='In1.Cu',priority=0,keepout=True,outline=outline,filled=[]))
    rf_windows.append(dict(ref=pad['ref'],pad=pad['num'],net=pad['net'],name=name,
        pad_outline_mm=list(footprint.exterior.coords)[:-1],outline_mm=outline,margin_mm=margin))
assert len(rf_windows)==19
for z in g['zones']:
    if z['name'] in outlines:
        z['outline'] = outlines[z['name']]
    z['filled'] = []  # Every copper area must be refilled before native export.

# TEMP must escape to the left of the restored C6 power pad/island.
g['tracks'] = [t for t in g['tracks'] if t['net'] != 'TJ_RAW']
paths = [
    ('TJ_RAW', .20, [[18.54601,29.34],[18.54601,33.1],[22.6,36.9],[22.60001,37.5]]),
    ('TJ_RAW', .20, [[22.60001,37.5],[22.6,39.3],[23.1,39.3]]),
    ('VCC', .15, intent['PD16']['L1_trace']),
]
for net, width, points in paths:
    for a, b in zip(points, points[1:]):
        g['tracks'].append(dict(net=net, start=a, end=b, width=width, layer='F.Cu'))

vias = json.loads((SOURCE / 'review/vias.json').read_text())
pads = {(p['ref'],p['num']):p for p in g['pads']}
vias = [v for v in vias if v['group'] != 'U1 local parallel vias']
for v in vias:
    if v['group'].startswith(tuple(r + '.' for r in moves)):
        ref, num = v['group'].split()[0].split('.')
        v['pos'] = pads[ref,num]['pos'][:]
    # Keep the C3/C4 pad drill at least .25 mm from the entry-via drills.
    if v['group']=='entry parallel vias' and abs(v['pos'][1]-10.35)<.001:
        v['pos'][1]=10.30
    if v['group']=='entry parallel vias' and abs(v['pos'][1]-45.53)<.001:
        v['pos'][1]=45.58
for net, coords in [('VCC', [(19.2,25.88),(19.85,25.88),(19.85,25.28)]),
                    ('VEE', [(19.2,30.0),(19.85,30.0),(19.85,30.6)])]:
    for x, y in coords:
        vias.append(dict(net=net,pos=[x,y],diameter=.4,drill=.2,group='U1 local parallel vias'))
vias.append(dict(net='VCC',pos=intent['PD16']['via'],diameter=.4,drill=.2,
                 group='PD16 dedicated via'))

def pad_shape(p):
    x,y = p['pos']; w,h = p['size']
    if p['shape'] == 0:
        return Point(x,y).buffer(w/2)
    return translate(rotate(box(-w/2,-h/2,w/2,h/2),-p['angle'],origin=(0,0)),x,y)

# Keep deliberate via-in-pad connections. Remove redundant supply/stitching
# vias that overlap the moved input pads, even when they share the pad's net.
entry_pads=[p for p in g['pads'] if p['ref'] in entry_intent['moves']]
entry_removed=[]
remaining=[]
for v in vias:
    overlap=any(pad_shape(p).distance(Point(v['pos']))<v['diameter']/2+.01 for p in entry_pads)
    near_drill=any(math.dist(v['pos'],q['pos'])<(v['drill']+q['drill'])/2+.25-.00001
                   for q in vias if q['group'].startswith(tuple(r+'.' for r in entry_intent['moves']))
                   and q is not v)
    if v['group'] in {'entry parallel vias','GND stitching'} and (overlap or near_drill):
        entry_removed.append(v)
    else: remaining.append(v)
vias=remaining

# Dense supply-via arrays in the newly widened filtered input islands.
# These use the same pad/drill dimensions as the adjacent ground stitching,
# but connect to the island's own VCC/VEE net and its L3 supply plane.
entry_array_vias=[]
for spec in entry_intent.get('filtered_via_arrays',[]):
    for x,y in spec['positions_mm']:
        v=dict(net=spec['net'],pos=[x,y],diameter=spec['diameter_mm'],
               drill=spec['drill_mm'],group='filtered entry via array')
        entry_array_vias.append(v)
vias.extend(entry_array_vias)

# Preserve earlier removals and clear ground stitching away from supply copper.
obstacles = [Polygon(z['outline']).buffer(.405) for z in g['zones']
             if z['layer']=='F.Cu' and z['name'] in outlines]
obstacles += [pad_shape(p).buffer(.405) for p in g['pads']
              if p['ref'] in moves and p['net'] != 'GND']
obstacles += [LineString([t['start'],t['end']]).buffer(t['width']/2+.405)
              for t in g['tracks'] if t['net'] in ['TJ_RAW','VCC']]
fixed = [v for v in vias if v['group'] != 'GND stitching']
removed = []
kept = []
for v in vias:
    conflict = v['group']=='GND stitching' and (
        any(math.dist(v['pos'],q['pos'])<.00001 for q in entry_intent['retained_prior_stitching_removals']) or
        any(o.intersects(Point(v['pos'])) for o in obstacles) or
        any(math.dist(v['pos'],q['pos']) < (.55 if q['net']!='GND' else .45)
            for q in fixed))
    (removed if conflict else kept).append(v)
vias = kept
g['vias'] = [{k:v[k] for k in ['net','pos','diameter','drill']} for v in vias]
for d in g['draw']:
    if d.get('type')=='text':
        d['text'] = d['text'].replace('REV C','REV D')

(REVIEW/'intended_geometry.json').write_text(json.dumps(g,indent=2))
(REVIEW/'vias.json').write_text(json.dumps(vias,indent=2))
(REVIEW/'rf_pad_windows.json').write_text(json.dumps(rf_windows,indent=2))
(REVIEW/'change_manifest.json').write_text(json.dumps(dict(
    source='altium_revC/review/native_geometry.json', moves=moves,
    changed_zone_outlines=outlines, changed_routes=paths,
    removed_redundant_zones=['L1_C7_VCC','L1_C7_VEE'],
    rectangular_pad_targets=[(p['ref'],p['num']) for p in shape_targets],
    pad_corner_radius_mm=0,
    removed_stitching_vias=removed, via_count=len(vias),
    removed_input_overlap_vias=entry_removed,
    input_rectangle_intent='input_rectangle_intent.json',
    L2_RF_pad_windows=len(rf_windows),
    filtered_entry_array_vias=entry_array_vias,
    purpose='Latest capacitor/PD/NC correction; electrical net assignments unchanged',
    fill_status='Pending; intended_geometry.json contains no filled copper'),indent=2))
print('Prepared Rev D:',len(vias),'vias;',len(removed),'conflicting stitching vias removed')
