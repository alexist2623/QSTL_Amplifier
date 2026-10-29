"""Add a GND via row along all four board edges, preserving previous layout."""
from pathlib import Path
import argparse,hashlib,json,math,shutil,struct,uuid
import olefile
from shapely.geometry import Polygon,Point
from shapely.ops import unary_union
from rf_fence_plan import rf_copper,padshape
from native_update import ROOT,blocks,parse,records,rec,point,unit,update_copy
R=ROOT/'review';S=ROOT/'staging/edge_via_fence_20261028'
INSET=1.0;PITCH=1.0;DIAMETER=.4;DRILL=.2;RF_GAP=.9174

def plan(g):
    w,h=g['board_width'],g['board_height'];rf=rf_copper(g)
    ground={l:unary_union([Polygon(f['outline'],f['holes']).buffer(0) for z in g['zones'] if z['layer']==l and z['net']=='GND' and not z['keepout'] for f in z['filled']]) for l in ['F.Cu','In1.Cu','In2.Cu','B.Cu']}
    pins=unary_union([padshape(q).buffer(.2) for q in g['pads']])
    targets=[]
    corners=[('top',(INSET,INSET),(w-INSET,INSET)),('right',(w-INSET,INSET),(w-INSET,h-INSET)),('bottom',(w-INSET,h-INSET),(INSET,h-INSET)),('left',(INSET,h-INSET),(INSET,INSET))]
    for side,start,end in corners:
        count=math.ceil(math.dist(start,end)/PITCH)
        for i in range(count):targets.append(dict(side=side,pos=[round(start[j]+(end[j]-start[j])*i/count,6) for j in [0,1]]))
    added=[];reused=[];skipped=[]
    for target in targets:
        pos=target['pos'];near=[v for v in g['vias'] if v['net']=='GND' and math.dist(pos,v['pos'])<.46]
        if near:
            v=min(near,key=lambda v:math.dist(pos,v['pos']))
            if v not in reused:reused.append(v)
            target['result']='existing';target['via_pos']=v['pos'];continue
        disk=Point(pos).buffer(DIAMETER/2+.001);reasons=[]
        if not all(c.covers(disk) for c in ground.values()):reasons.append('not fully inside GND on all four layers')
        if pins.intersects(disk):reasons.append('pad clearance')
        if rf.distance(Point(pos))<RF_GAP+DIAMETER/2+.001:reasons.append('RF 3W clearance')
        if any(math.dist(pos,v['pos'])<v['diameter']/2+DIAMETER/2+.052 for v in g['vias']+added):reasons.append('existing via clearance')
        if reasons:
            target['result']='protected gap';target['reasons']=reasons;skipped.append(target);continue
        added.append(dict(net='GND',pos=pos,diameter=DIAMETER,drill=DRILL));target['result']='added';target['via_pos']=pos
    return added,reused,skipped,targets

def build():
    pcb=ROOT/'QSTL_THS3491_RGT_G20_RevD.PcbDoc'
    g=json.loads((R/'native_geometry.json').read_text());added,reused,skipped,targets=plan(g)
    assert len(g['vias'])==817 and len(added)==148 and len(reused)==50 and len(skipped)==16
    S.mkdir(exist_ok=False)
    shutil.copy2(pcb,S/'before.PcbDoc');shutil.copy2(pcb.with_suffix('.SchDoc'),S/'before.SchDoc')
    shutil.copytree(R,S/'review_before',ignore=shutil.ignore_patterns('*.png','*.svg'))
    intent=dict(request='Ground via fence along the board perimeter.',baseline_pcb_sha256=hashlib.sha256(pcb.read_bytes()).hexdigest(),
        center_inset_mm=INSET,nominal_pitch_mm=PITCH,diameter_mm=DIAMETER,drill_mm=DRILL,minimum_copper_to_board_edge_mm=INSET-DIAMETER/2,
        RF_copper_edge_gap_mm=RF_GAP,added_ground_vias=added,reused_existing_vias=reused,protected_targets=skipped,targets=targets,
        unchanged=['all previous vias including mounting rings and RF fence','board outline and holes','pads and parts','tracks and arcs','all copper and cutouts','bottom mask','schematic','3D models'])
    (ROOT/'edge_via_intent.json').write_text(json.dumps(intent,indent=2)+'\n')
    g['vias']+=added;(S/'geometry.json').write_text(json.dumps(g,indent=2))
    with olefile.OleFileIO(pcb) as o:streams={'/'.join(k):o.openstream(k).read() for k in o.listdir()}
    nets={parse(b)['NAME']:i for i,b in enumerate(blocks(streams['Nets6/Data']))};vs=list(records(streams['Vias6/Data'],3))
    sample=next(v for v in vs if struct.unpack_from('<H',v,3)[0]==nets['GND'] and abs(struct.unpack_from('<i',v,21)[0]*.00000254-DIAMETER)<.00001)
    rows=[rec(3,v) for v in vs]
    for v in added:
        raw=bytearray(sample);struct.pack_into('<5H',raw,3,nets['GND'],65535,65535,65535,65535)
        struct.pack_into('<4i',raw,13,*point(v['pos']),unit(DIAMETER),unit(DRILL));rows.append(rec(3,raw))
    updates={'Vias6/Data':b''.join(rows),'Vias6/Header':struct.pack('<I',len(rows))}
    ids=streams['PrimitiveGuids/Data'];rr=[ids[i:i+24] for i in range(0,len(ids),24)]
    rr += [struct.pack('<II',3843,i)+uuid.uuid5(uuid.NAMESPACE_URL,f'qstl/edge-fence/via/{i}').bytes_le for i in range(len(vs),len(rows))]
    updates.update({'PrimitiveGuids/Data':b''.join(rr),'PrimitiveGuids/Header':struct.pack('<I',len(rr))})
    update_copy(pcb,S/'candidate.PcbDoc',updates)
    (R/'native_geometry.json').write_text(json.dumps(g,indent=2));(R/'intended_geometry.json').write_text(json.dumps(g,indent=2))
    print('Added',len(added),'edge vias; reused',len(reused),'protected gaps',len(skipped),'total',len(g['vias']))

if __name__=='__main__':build()
