"""Patch only input hardware and its traces; native save/reopen is required."""
from pathlib import Path
import copy,json,struct,uuid,argparse
import olefile
from native_update import ROOT,blocks,parse,props,records,rec,block,point,unit,mil,LAYER_V7,fix_track_layer,update_copy

S=ROOT/'staging/dc_inputs_20261028'
parser=argparse.ArgumentParser();parser.add_argument('--schematic-only',action='store_true');parser.add_argument('--sch-output',type=Path,default=S/'hardware.SchDoc');args=parser.parse_args()
g=json.loads((S/'geometry.json').read_text());intent=json.loads((S/'intent.json').read_text())
spec={d['ref']:d for d in intent['connectors']}
def uid(s):return ''.join(chr(65+b%26) for b in uuid.uuid5(uuid.NAMESPACE_URL,'qstl/power/'+s).bytes[:8])
with olefile.OleFileIO(S/'before.PcbDoc') as o:streams={'/'.join(k):o.openstream(k).read() for k in o.listdir()}
updates={};counts={}
def put(name,rows):
 counts[name]=len(rows);updates[name+'/Data']=b''.join(rows);updates[name+'/Header']=struct.pack('<I',len(rows))
cs=[parse(v) for v in blocks(streams['Components6/Data'])]
for ref in ['J9','J10']:
 d=copy.deepcopy(cs[10]);d.update(SOURCEDESIGNATOR=ref,SOURCEUNIQUEID=uid(ref),UNIQUEID=uid('PCB'+ref));cs.append(d)
ci={d['SOURCEDESIGNATOR']:i for i,d in enumerate(cs)}
for ref,p in spec.items():
 cs[ci[ref]].update(X=mil(p['pos'][0]),Y=mil(68.58-p['pos'][1]),ROTATION=p['angle'],PATTERN=p['pattern'],
  SOURCELIBREFERENCE='PJ-102AH',SOURCEDESCRIPTION=p['value'],NAMEON='FALSE',HEIGHT=mil(11))
put('Components6',[props(d) for d in cs])
nets={parse(v)['NAME']:i for i,v in enumerate(blocks(streams['Nets6/Data']))}
d=streams['Pads6/Data'];off=0;rows=[];sample=None
while off<len(d):
 start=off;assert d[off]==2;off+=1;bs=[]
 for _ in range(6):
  n=struct.unpack_from('<I',d,off)[0];off+=4;bs.append(d[off:off+n]);off+=n
 ref=cs[struct.unpack_from('<H',bs[4],7)[0]]['SOURCEDESIGNATOR']
 if ref=='J4':sample=bs
 if ref not in spec:rows.append(d[start:off])
for p in g['pads']:
 if p['ref'] not in spec:continue
 bs=list(sample);pn=p['num'].encode();bs[0]=bytes([len(pn)])+pn
 b=bytearray(bs[4]);b[0]=74;b[1]=12;b[2]=0
 struct.pack_into('<HHHHH',b,3,nets.get(p['net'],65535),65535,ci[p['ref']],65535,65535)
 sx,sy=map(unit,p['size']);struct.pack_into('<9i',b,13,*point(p['pos']),sx,sy,sx,sy,sx,sy,unit(p['drill'][0]))
 b[49:52]=bytes([2 if p['shape']==1 else 1]*3);struct.pack_into('<d',b,52,0)
 b[60]=1;b[62]=0;struct.pack_into('<ii',b,86,unit(-10),unit(.04));b[101]=2;b[102]=2
 struct.pack_into('<I',b,114,LAYER_V7[74]);bs[4]=bytes(b);bs[5]=b''
 rows.append(bytes([2])+b''.join(block(v) for v in bs))
put('Pads6',rows)
ts=list(records(streams['Tracks6/Data'],4));rows=[rec(4,t) for t in ts]
def track(a,b,w,layer=1,net='',owner=65535):
 raw=bytearray(ts[0]);raw[0]=layer;raw[1]=12;raw[2]=0
 struct.pack_into('<HHHHH',raw,3,nets.get(net,65535),65535,owner,65535,65535)
 struct.pack_into('<5i',raw,13,*point(a),*point(b),unit(w));struct.pack_into('<H',raw,33,65535)
 rows.append(rec(4,fix_track_layer(raw)))
for t in intent['added_tracks']:track(t['start'],t['end'],t['width'],net=t['net'])
# Footprint assembly outlines on Mechanical 1, unobtrusive to functional silk.
for ref in ['J9','J10']:
 p=spec[ref];x,y=p['pos'];s=-1 if p['angle']==180 else 1
 ps=[[x+s*dx,y+s*dy] for dx,dy in [(-4.5,-.7),(4.5,-.7),(4.5,13.7),(-4.5,13.7)]]
 for a,b in zip(ps,ps[1:]+ps[:1]):track(a,b,.1,57,owner=ci[ref])
put('Tracks6',rows)
vs=list(records(streams['Vias6/Data'],3));rows=[]
for v in vs:
 x,y=struct.unpack_from('<ii',v,13)
 if any(abs(x-point(z['pos'])[0])<10 and abs(y-point(z['pos'])[1])<10 for z in intent['removed_ground_vias']):continue
 rows.append(rec(3,v))
assert len(rows)==len(g['vias']);put('Vias6',rows)
d=streams['Texts6/Data'];off=0;rows=[]
while off<len(d):
 start=off;off+=1;n=struct.unpack_from('<I',d,off)[0];off+=4;raw=d[off:off+n];off+=n
 n=struct.unpack_from('<I',d,off)[0];off+=4;txt=d[off:off+n];off+=n
 owner=struct.unpack_from('<H',raw,7)[0]
 if owner in [ci[r] for r in spec] or txt[1:] in [b'+15V',b'-15V']:continue
 rows.append(d[start:off])
def text(txt,pos,size,owner=65535,isref=False):
 raw=bytearray(137);raw[0]=57 if isref else 33;raw[1]=12;struct.pack_into('<HHHHH',raw,3,65535,65535,owner,65535,65535)
 struct.pack_into('<3i',raw,13,*point(pos),unit(size));struct.pack_into('<d',raw,27,0)
 struct.pack_into('<i',raw,36,unit(.12));raw[41]=1 if isref else 0;raw[46:56]='Arial'.encode('utf-16le');struct.pack_into('<I',raw,115,4294967295)
 # Standard stroke text, no WideStrings lookup is needed.
 s=txt.encode('ascii');rows.append(rec(5,raw)+block(bytes([len(s)])+s))
for t in intent['silk']:text(t['text'],t['pos'],t['height'])
for ref,p in spec.items():text(ref,[p['pos'][0]-.7,p['pos'][1]-1.7],.8,ci[ref],True)
put('Texts6',rows)
tags={'Components6':777,'Pads6':3586,'Vias6':3843,'Tracks6':4100,'Texts6':4357}
ids=streams['PrimitiveGuids/Data'];rr=[ids[i:i+24] for i in range(0,len(ids),24) if struct.unpack_from('<I',ids,i)[0] not in tags.values()]
for name,tag in tags.items():rr.extend(struct.pack('<II',tag,i)+uuid.uuid5(uuid.NAMESPACE_URL,f'qstl/power/{name}/{i}').bytes_le for i in range(counts[name]))
put('PrimitiveGuids',rr)
if not args.schematic_only:update_copy(S/'before.PcbDoc',S/'hardware.PcbDoc',updates)

# Schematic: preserve existing connectivity; remove obsolete wire pads,
# append explicitly labelled three-terminal DC connectors in the free top band.
with olefile.OleFileIO(S/'before.SchDoc') as o:rs=[parse(v) for v in blocks(o.openstream('FileHeader').read())]
refs={r['Text']:int(r['OwnerIndex'])+1 for r in rs if r.get('RECORD')=='34'}

def add(r):rs.append({k:str(v) for k,v in r.items()});return len(rs)-1
def unique(r,tag):r['UniqueID']=uid(tag);return r
for ref,cx,cy,net in [('J9',30,330,'VIN_P'),('J10',30,170,'VIN_N')]:
 i=len(rs);r=dict(rs[refs['J7']]);r.update(LibReference='PJ-102AH',DesignItemId='PJ-102AH',ComponentDescription=spec[ref]['value'],AllPinCount='3',UniqueID=uid(ref),**{'Location.X':str(cx),'Location.Y':str(cy),'IndexInSheet':str(200+i)})
 add(r);owner=i-1
 add(unique(dict(RECORD=14,OwnerIndex=owner,OwnerPartId=1,**{'Location.X':cx-20,'Location.Y':cy-50,'Corner.X':cx+110,'Corner.Y':cy+50},Color=128,AreaColor=11599871,IsSolid='T'),ref+'box'))
 for num,dy,pname,pnet in [(1,30,'CENTER',net),(2,0,'SLEEVE','GND'),(3,-30,'SWITCH_NC','')]:
  add(unique(dict(RECORD=2,OwnerIndex=owner,OwnerPartId=1,Electrical=4,PinConglomerate=56,PinLength=30,**{'Location.X':cx+110,'Location.Y':cy+dy},Name=pname,Designator=num),ref+'pin'+str(num)))
  if pnet:
   endx=240 if num==1 else cx+160
   add(unique(dict(RECORD=27,OwnerPartId=-1,LineWidth=1,Color=8388608,LocationCount=2,X1=cx+140,Y1=cy+dy,X2=endx,Y2=cy+dy),ref+'wire'+str(num)))
   if num==2:add(unique(dict(RECORD=25,OwnerPartId=-1,**{'Location.X':endx,'Location.Y':cy+dy},Color=128,FontID=2,Text=pnet),ref+'net'+str(num)))
 for name,val in [('MPN','PJ-102AH'),('Footprint','SameSky_PJ-102AH'),('Comment',spec[ref]['value'])]:
  add(unique(dict(RECORD=41,OwnerIndex=owner,OwnerPartId=-1,FontID=2,IsHidden='T',Name=name,Text=val),ref+name))
 add(unique(dict(RECORD=34,OwnerIndex=owner,OwnerPartId=-1,**{'Location.X':cx-20,'Location.Y':cy+60},Color=8388608,FontID=2,Text=ref+' / '+spec[ref]['value'],Name='Designator'),ref+'ref'))
 # The designator must remain the bare reference for schematic/PCB linkage.
 rs[-1]['Text']=ref
 ml=add(dict(RECORD=44,OwnerIndex=owner))
 mi=add(unique(dict(RECORD=45,OwnerIndex=ml-1,ModelName='SameSky_PJ-102AH',ModelType='PCBLIB',DatafileCount=1,ModelDatafileEntity0='SameSky_PJ-102AH',ModelDatafileKind0='PCBLib',IsCurrent='T'),ref+'model'))
 add(dict(RECORD=46,OwnerIndex=mi-1));add(dict(RECORD=48,OwnerIndex=mi-1))
 add(unique(dict(RECORD=4,OwnerPartId=-1,**{'Location.X':cx-20,'Location.Y':cy-65},Color=8388608,FontID=2,Text=spec[ref]['value']+' / 5.5-2.1mm'),ref+'note'))
# Remove obsolete one-pin inputs and only their dedicated wire/label pairs.
remove={refs[k] for k in intent['removed_components']}
removed_ids={'TOQYGBHH','JRMAYUVE','MMFGONZR','YSVVKXGV','JPQXJXMS','HMLYGRBE','ICRMDGUI','PHWILOEK'}
remove.update(i for i,q in enumerate(rs) if q.get('UniqueID') in removed_ids)
while True:
 extra={i for i,q in enumerate(rs) if 'OwnerIndex' in q and int(q['OwnerIndex'])+1 in remove}
 if extra<=remove:break
 remove.update(extra)
index_map={old_i:new_i for new_i,old_i in enumerate(i for i in range(len(rs)) if i not in remove)}
new=[]
for old_i,q in enumerate(rs):
 if old_i in remove:continue
 if 'OwnerIndex' in q and int(q['OwnerIndex'])>=0:q['OwnerIndex']=str(index_map[int(q['OwnerIndex'])+1]-1)
 new.append(q)
rs=new
rs[0]['Weight']=str(len(rs)-1)
update_copy(S/'before.SchDoc',args.sch_output,{'FileHeader':b''.join(props(r) for r in rs)})
print('Created native PCB and schematic candidates; existing 24 embedded models preserved')
