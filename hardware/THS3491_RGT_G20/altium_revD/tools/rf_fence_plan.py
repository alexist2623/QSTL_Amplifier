"""Place a 3W GND via fence around RF copper, preserving existing layout."""
from pathlib import Path
import argparse,hashlib,json,math,shutil,struct,uuid
import olefile
from shapely.geometry import Polygon,Point,LineString,box
from shapely.affinity import rotate
from shapely.ops import unary_union
from shapely.prepared import prep
from native_update import ROOT,blocks,parse,records,rec,point,unit,update_copy
R=ROOT/'review';S=ROOT/'staging/rf_fence_20261028'
RF_NETS={'inm','RG_DRIVE','INV','FB','inpt_raw','inpt','AMP_OUT','output'}
WIDTH=.3058;GAP=3*WIDTH;DIAMETER=.4;DRILL=.2;PITCH=.9

def padshape(q):
    x,y=q['pos'];w,h=q['size']
    p=Point(x,y).buffer(w/2,resolution=48) if q['shape']==0 else box(x-w/2,y-h/2,x+w/2,y+h/2)
    return rotate(p,-q['angle'],origin=(x,y))

def rf_copper(g):
    shapes=[LineString([t['start'],t['end']]).buffer(t['width']/2,resolution=64) for t in g['tracks'] if t['net'] in RF_NETS]
    for a in g['arcs']:
        if a['net'] not in RF_NETS:continue
        cx,cy=a['center'];start=math.atan2(a['start'][1]-cy,a['start'][0]-cx)
        count=max(3,math.ceil(abs(a['angle'])*10))
        coords=[(cx+a['radius']*math.cos(start+math.radians(a['angle'])*i/count),cy+a['radius']*math.sin(start+math.radians(a['angle'])*i/count)) for i in range(count+1)]
        shapes.append(LineString(coords).buffer(a['width']/2,resolution=64))
    shapes += [padshape(q) for q in g['pads'] if q['net'] in RF_NETS and 'F.Cu' in q['layers']]
    return unary_union(shapes)

def build(reuse_stage=False,output_name='candidate.PcbDoc'):
    pcb=ROOT/'QSTL_THS3491_RGT_G20_RevD.PcbDoc'
    if not reuse_stage:
        S.mkdir(exist_ok=False)
        shutil.copy2(pcb,S/'before.PcbDoc');shutil.copy2(pcb.with_suffix('.SchDoc'),S/'before.SchDoc')
        shutil.copytree(R,S/'review_before',ignore=shutil.ignore_patterns('*.png','*.svg'))
    assert pcb.read_bytes()==(S/'before.PcbDoc').read_bytes()
    g=json.loads((S/'review_before/native_geometry.json').read_text());rf=rf_copper(g)
    boundary=rf.buffer(GAP+DIAMETER/2+.002,resolution=64).exterior
    safe=box(.5,.5,g['board_width']-.5,g['board_height']-.5)
    grounds={layer:unary_union([Polygon(f['outline'],f['holes']).buffer(0) for z in g['zones'] if z['layer']==layer and z['net']=='GND' and not z['keepout'] for f in z['filled']]) for layer in ['F.Cu','In1.Cu','In2.Cu','B.Cu']}
    common=prep(unary_union([safe]).intersection(grounds['F.Cu']).intersection(grounds['In1.Cu']).intersection(grounds['In2.Cu']).intersection(grounds['B.Cu']))
    pin_avoid=prep(unary_union([padshape(q).buffer(.20) for q in g['pads']]))
    def valid_xy(xy):
        q=Point(xy);disk=q.buffer(DIAMETER/2+.001,resolution=24)
        return rf.distance(q)>=GAP+DIAMETER/2+.0005 and common.covers(disk) and not pin_avoid.intersects(disk)
    count=math.ceil(boundary.length/PITCH);added=[];used=[];targets=[];missed=[]
    existing=[v for v in g['vias'] if v['net']=='GND']
    for i in range(count):
        d=boundary.length*i/count;q=boundary.interpolate(d);xy=[q.x,q.y]
        if not safe.covers(q):continue
        targets.append(xy)
        # Reuse a qualified existing shield via when it already serves this point.
        # Existing GND vias already have valid antipads where they pass power
        # layers. Reuse them without requiring a new full copper disk in L3.
        matches=[v for v in existing+added if math.dist(v['pos'],xy)<=.46 and rf.distance(Point(v['pos']))>=GAP+v['diameter']/2+.0005]
        if matches:
            v=min(matches,key=lambda v:math.dist(v['pos'],xy))
            if v not in used:used.append(v)
            continue
        before=boundary.interpolate((d-.01)%boundary.length);after=boundary.interpolate((d+.01)%boundary.length)
        tangent=(after.x-before.x,after.y-before.y);length=math.hypot(*tangent)
        normals=[(-tangent[1]/length,tangent[0]/length),(tangent[1]/length,-tangent[0]/length)]
        normal=max(normals,key=lambda v:rf.distance(Point(q.x+v[0]*.05,q.y+v[1]*.05)))
        candidates=[]
        for step in range(11):
            for along in [0,-.10,.10,-.20,.20]:
                pos=[round(q.x+normal[0]*step*.1+tangent[0]/length*along,6),round(q.y+normal[1]*step*.1+tangent[1]/length*along,6)]
                if not valid_xy(pos):continue
                if any(math.dist(pos,v['pos'])<(DIAMETER+v['diameter'])/2+.052 for v in g['vias']+added):continue
                candidates.append((math.dist(pos,xy),pos))
            if candidates:break
        if not candidates:missed.append(xy);continue
        pos=min(candidates)[1];v=dict(net='GND',pos=pos,diameter=DIAMETER,drill=DRILL);added.append(v);used.append(v)
    assert len(added)>70
    g['vias']+=added
    intent=dict(request='RF shield vias with 3W copper-edge gap; both sides of input curves/output and RF component perimeter.',
        baseline_pcb_sha256=hashlib.sha256(pcb.read_bytes()).hexdigest(),distance_definition='RF copper edge to via copper edge',
        reference_trace_width_mm=WIDTH,minimum_gap_mm=GAP,nominal_pitch_mm=PITCH,diameter_mm=DIAMETER,drill_mm=DRILL,
        added_ground_vias=added,reused_existing_vias=[v for v in used if v not in added],fence_targets_mm=targets,blocked_targets_mm=missed,
        local_outward_adjustment_max_mm=1.0,
        preserved='All existing vias, parts, pads, tracks, arcs, polygons/cutouts, bottom mask, schematic and 3D models.',
        references=['https://www.analog.com/en/resources/technical-articles/pcbs-layout-guidelines-for-rf--mixedsignal.html','https://resources.altium.com/p/microstrip-ground-clearance-how-close-too-close'])
    (ROOT/'rf_fence_intent.json').write_text(json.dumps(intent,indent=2)+'\n');(S/'geometry.json').write_text(json.dumps(g,indent=2))
    with olefile.OleFileIO(pcb) as o:streams={'/'.join(k):o.openstream(k).read() for k in o.listdir()}
    nets={parse(b)['NAME']:i for i,b in enumerate(blocks(streams['Nets6/Data']))};vs=list(records(streams['Vias6/Data'],3));rows=[rec(3,v) for v in vs]
    sample=next(v for v in vs if struct.unpack_from('<H',v,3)[0]==nets['GND'] and abs(struct.unpack_from('<i',v,21)[0]*.00000254-.4)<.00001)
    for v in added:
        raw=bytearray(sample);struct.pack_into('<5H',raw,3,nets['GND'],65535,65535,65535,65535)
        struct.pack_into('<4i',raw,13,*point(v['pos']),unit(DIAMETER),unit(DRILL))
        rows.append(rec(3,raw))
    updates={'Vias6/Data':b''.join(rows),'Vias6/Header':struct.pack('<I',len(rows))}
    ids=streams['PrimitiveGuids/Data'];rr=[ids[i:i+24] for i in range(0,len(ids),24)]
    rr += [struct.pack('<II',3843,i)+uuid.uuid5(uuid.NAMESPACE_URL,f'qstl/rf-fence/via/{i}').bytes_le for i in range(len(vs),len(rows))]
    updates.update({'PrimitiveGuids/Data':b''.join(rr),'PrimitiveGuids/Header':struct.pack('<I',len(rr))})
    assert Path(output_name).name==output_name
    update_copy(pcb,S/output_name,updates)
    (R/'native_geometry.json').write_text(json.dumps(g,indent=2));(R/'intended_geometry.json').write_text(json.dumps(g,indent=2))
    print('Added',len(added),'reused',len(intent['reused_existing_vias']),'blocked',len(missed),'of',len(targets),'targets; total vias',len(g['vias']))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--reuse-stage',action='store_true');p.add_argument('--output-name',default='candidate.PcbDoc');a=p.parse_args();build(a.reuse_stage,a.output_name)
