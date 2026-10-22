"""Construct an editable native Altium PCB compound document from verified geometry.
Uses Windows Structured Storage and documented/readable native record layouts.
Native Altium repour/DRC is a separate mandatory review step.
"""
from pathlib import Path
import sys,struct,json,uuid,re,hashlib,copy,math
H=Path(__file__).resolve().parents[1];S=H/'staging';sys.path.insert(0,str(H.parent/'altium/tools/vendor'))
import olefile
from cfb_copy_update import update_copy
g=json.loads((H/'review/native_geometry.json').read_text())
manifest=json.loads((S/'review/design_manifest.json').read_text());mp={p['ref']:p for p in manifest['parts']}
def uid(s):return ''.join(chr(65+b%26) for b in hashlib.sha256(('QSTL_REVC_'+s).encode()).digest()[:8])
def guid(s):return '{'+str(uuid.uuid5(uuid.NAMESPACE_URL,'qstl/revc/'+s)).upper()+'}'
def unit(v):return round(v/2.54e-6)
def mil(v):return f'{v/.0254:.8f}mil'
BW,BH=g['board_width'],g['board_height']
def point(p):return (unit(p[0]),unit(BH-p[1]))
def block(b):return struct.pack('<I',len(b))+b
def props(r):return block(('|'+'|'.join(k+'='+str(v) for k,v in r.items())+'\0').encode('cp1252'))
def parse(b):
 n=struct.unpack_from('<I',b,0)[0];return dict(s.split('=',1) for s in b[4:4+n].rstrip(b'\0').decode('cp1252').split('|') if '=' in s)
def rec(k,b):return bytes([k])+block(b)
LAY={'F.Cu':1,'In1.Cu':2,'In2.Cu':3,'B.Cu':32,'F.SilkS':33,'B.SilkS':34,'F.Paste':35,'B.Paste':36,'F.Mask':37,'B.Mask':38,'Edge.Cuts':57,'F.Fab':57,'B.Fab':58}
LAY.update({'F.Silkscreen':33,'B.Silkscreen':34,'F.Fabrication':57,'B.Fabrication':58})
LNAME={1:'TOP',2:'MID1',3:'MID2',32:'BOTTOM',33:'TOPOVERLAY',34:'BOTTOMOVERLAY',35:'TOPPASTE',36:'BOTTOMPASTE',37:'TOPSOLDER',38:'BOTTOMSOLDER',57:'MECHANICAL1',58:'MECHANICAL2'}
L7={1:16777217,2:16777218,3:16777219,32:16842751,33:16973830,34:16973831,35:16973832,36:16973833,37:16973834,38:16973835,57:16908301,58:16908302,74:0}
template=Path(r'C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\branched_fpc_20261002\dsub_blank.PcbDoc')
o=olefile.OleFileIO(template);updates={};counts={}
def put(name,records):
 updates[name+'/Data']=b''.join(records);updates[name+'/Header']=struct.pack('<I',len(records));counts[name]=len(records)
board=parse(o.openstream('Board6/Data').read())
sub=guid('substack');master=guid('masterstack')
for k in list(board):
 if k.startswith(('V9_STACK_LAYER','V9_CACHE_LAYER','V9_SUBSTACK','V9_MASTERSTACK')) or re.fullmatch(r'(KIND|VX|VY|CX|CY|SA|EA|R)\d+',k):del board[k]
board.update(V9_MASTERSTACK_STYLE='0',V9_MASTERSTACK_ID=master,V9_MASTERSTACK_NAME='JLC04161H-7628',V9_MASTERSTACK_ISFLEX='FALSE',V9_MASTERSTACK_SHOWTOPDIELECTRIC='TRUE',V9_MASTERSTACK_SHOWBOTTOMDIELECTRIC='TRUE',V9_SUBSTACK0_ID=sub,V9_SUBSTACK0_NAME='JLC04161H-7628',V9_SUBSTACK0_ISFLEX='FALSE',V9_SUBSTACK0_TYPE='0',V9_SUBSTACK0_SERVICE='FALSE',V9_SUBSTACK0_USEDBYPRIMS='TRUE',UNIQUEID=uid('board'))
stack=[('Top Paste',16973832,0,0,0),('Top Overlay',16973830,0,0,0),('Top Solder',16973834,.0152,3.8,3),('L1 Signal GND',16777217,.035,0,0),('7628 Prepreg',17039361,.2104,4.4,0),('L2 GND',16777218,.0152,0,0),('FR4 Core',17039362,1.065,4.6,1),('L3 Split Power',16777219,.0152,0,0),('7628 Prepreg',17039363,.2104,4.4,0),('L4 GND Thermal',16842751,.035,0,0),('Bottom Solder',16973835,.0152,3.8,3),('Bottom Overlay',16973831,0,0,0),('Bottom Paste',16973833,0,0,0)]
for i,(name,lid,th,er,typ) in enumerate(stack):
 d={'ID':guid('stack'+str(i)),'NAME':name,'LAYERID':lid,'USEDBYPRIMS':'TRUE','COMPONENTPLACEMENT':1 if i==3 else 2 if i==9 else 0}
 if er:d.update(DIELTYPE=typ,DIELCONST=er,DIELHEIGHT=mil(th),DIELMATERIAL='Solder Resist' if typ==3 else 'FR4-7628' if typ==0 else 'FR4')
 elif th:d['COPTHICK']=mil(th)
 d[sub+'CONTEXT']='0';d[sub+'USEDBYPRIMS']='TRUE'
 for prefix in [f'V9_STACK_LAYER{i}_',f'V9_CACHE_LAYER{i}_']:
  for k,v in d.items():board[prefix+k]=str(v)
chain=[1,2,3,32]
for n in range(1,33):
 board[f'LAYER{n}PREV']=str(chain[chain.index(n)-1] if n in chain and chain.index(n)>0 else 0)
 board[f'LAYER{n}NEXT']=str(chain[chain.index(n)+1] if n in chain and chain.index(n)<3 else 0)
for n,th,dh,er,typ,name in [(1,.035,.2104,4.4,0,'L1 Signal GND'),(2,.0152,1.065,4.6,1,'L2 GND'),(3,.0152,.2104,4.4,0,'L3 Split Power'),(32,.035,0,4.4,0,'L4 GND Thermal')]:
 for k,v in dict(NAME=name,COPTHICK=mil(th),DIELHEIGHT=mil(dh),DIELCONST=er,DIELTYPE=typ,DIELMATERIAL='FR4').items():board[f'LAYER{n}{k}']=str(v)
outline=[(0,0),(BW,0),(BW,BH),(0,BH)]
def verts(r,ps,flip=True):
 for i,p in enumerate(ps+[ps[0]]):
  x,y=p;y=BH-y if flip else y
  r.update({f'KIND{i}':'0',f'VX{i}':mil(x),f'VY{i}':mil(y),f'CX{i}':'0mil',f'CY{i}':'0mil',f'SA{i}':'0',f'EA{i}':'0',f'R{i}':'0mil'})
verts(board,outline);put('Board6',[props(board)])
# Remove stale template caches and geometry; retain valid file header/version metadata.
for name in ['BoardRegions','Classes6','SignalClasses','TClearanceViolation','Texts','WideStrings6','PadViaCacheLibraryLinksSection','PadViaLibraryLinks','PrimitiveGuids','UniqueIDPrimitiveInformation','FileVersionInfo']:
 if o.exists(name+'/Data'):put(name,[])
old_br=o.openstream('BoardRegions/Data').read();br_header=old_br[5:23];br_props=parse(old_br[23:]);br_props.update(NAME='QSTL Rev C rigid board',LAYERSTACKID=sub)
put('BoardRegions',[rec(11,br_header+props(br_props)+struct.pack('<I',4)+b''.join(struct.pack('<2d',*point(p)) for p in outline))])
netnames=sorted({p['net'] for p in g['pads'] if p['net']});netid={n:i for i,n in enumerate(netnames)}
base={'SELECTION':'FALSE','LOCKED':'FALSE','POLYGONOUTLINE':'FALSE','USERROUTED':'TRUE','KEEPOUT':'FALSE','UNIONINDEX':'0'}
put('Nets6',[props(dict(base,LAYER='TOP',NAME=n,VISIBLE='TRUE',COLOR=128,UNIQUEID=uid(n),LOOPREMOVAL='TRUE',JUMPERSVISIBLE='TRUE')) for n in netnames])
comps=[];compid={p['ref']:i for i,p in enumerate(g['parts'])}
for p in g['parts']:
 m=mp.get(p['ref'],{});r=dict(base,LAYER=LNAME[LAY[p['layer']]],PRIMITIVELOCK='TRUE',X=mil(p['pos'][0]),Y=mil(BH-p['pos'][1]),PATTERN=p['pattern'],NAMEON='TRUE',COMMENTON='FALSE',GROUPNUM=0,COUNT=0,ROTATION=p['angle'],HEIGHT=mil(1),COMMENTAUTOPOSITION=3,SOURCEDESIGNATOR=p['ref'],SOURCEUNIQUEID=uid(p['ref']),SOURCEHIERARCHICALPATH='QSTL_THS3491_RGT_G20_RevC',SOURCEFOOTPRINTLIBRARY='*',SOURCECOMPONENTLIBRARY='QSTL',SOURCELIBREFERENCE=m.get('mpn',p['pattern']),SOURCEDESCRIPTION=p['value'],UNIQUEID=uid('PCB'+p['ref']),JUMPERSVISIBLE='TRUE');comps.append(props(r))
put('Components6',comps)
padrecords=[];apertures=[]
for p in g['pads']:
 if not any(l in ['F.Cu','B.Cu','In1.Cu','In2.Cu'] for l in p['layers']):
  apertures.append(p);continue
 blocks=[(S/f'smd_pad_{i}.bin').read_bytes() for i in range(6)]
 pn=p['num'].encode('ascii');blocks[0]=bytes([len(pn)])+pn
 b=bytearray(blocks[4]);layer=74 if p['drill'][0] else 32 if 'B.Cu' in p['layers'] else 1
 b[0]=layer;b[1]=12;b[2]=0;struct.pack_into('<HHHHH',b,3,netid.get(p['net'],65535),65535,compid[p['ref']],65535,65535)
 x,y=point(p['pos']);sx,sy=map(unit,p['size']);hole=unit(p['drill'][0]);struct.pack_into('<9i',b,13,x,y,sx,sy,sx,sy,sx,sy,hole)
 shape=1 if p['shape'] in [0,4] else 2;b[49:52]=bytes([shape]*3);struct.pack_into('<d',b,52,p['angle']);b[60]=0 if p['npth'] else 1;b[62]=0
 struct.pack_into('<ii',b,86,unit(0 if 'F.Paste' in p['layers'] or 'B.Paste' in p['layers'] else -10),unit(.04 if not p['npth'] else 0));b[101]=2;b[102]=2
 blocks[4]=bytes(b)
 if p['shape']==4:
  shape_data=bytearray(596)
  for j in range(29):struct.pack_into('<i',shape_data,j*4,sx);struct.pack_into('<i',shape_data,116+j*4,sy)
  shape_data[232:261]=bytes([1]*29);shape_data[532:564]=bytes([9]*32);shape_data[564:596]=bytes([round(p['roundrect_ratio']*200)]*32)
  blocks[5]=bytes(shape_data)
 else:blocks[5]=b''
 padrecords.append(bytes([2])+b''.join(block(t) for t in blocks))
put('Pads6',padrecords)
tracks=[]
def track(a,b,w,layer,net='',component=65535):
 raw=bytearray((S/'Tracks6_sample.bin').read_bytes());raw[0]=layer;raw[1]=12;raw[2]=0;struct.pack_into('<HHHHH',raw,3,netid.get(net,65535),65535,component,65535,65535);struct.pack_into('<5i',raw,13,*point(a),*point(b),unit(w));struct.pack_into('<H',raw,33,65535);struct.pack_into('<I',raw,40,L7[layer]);tracks.append(rec(4,raw))
for t in g['tracks']:track(t['start'],t['end'],t['width'],LAY[t['layer']],t['net'])
for i,a in enumerate(outline):track(a,outline[(i+1)%4],.05,57)
put('Tracks6',tracks)
arcs=[]
for a in g['arcs']:
 raw=bytearray(57);layer=LAY[a['layer']];raw[0]=layer;raw[1]=12
 struct.pack_into('<HHHHH',raw,3,netid[a['net']],65535,65535,65535,65535)
 cx,cy=a['center'];sa=math.degrees(math.atan2(-(a['end'][1]-cy),a['end'][0]-cx))%360;ea=(sa+abs(a['angle']))%360
 struct.pack_into('<3i2diH',raw,13,*point(a['center']),unit(a['radius']),sa,ea,unit(a['width']),65535)
 struct.pack_into('<I',raw,52,L7[layer]);arcs.append(rec(1,raw))
put('Arcs6',arcs)
texts=[]
def textrec(s,pos,size,layer,component=65535,isref=False):
 raw=bytearray(137);raw[0]=layer;raw[1]=12;struct.pack_into('<HHHHH',raw,3,65535,65535,component,65535,65535);struct.pack_into('<3i',raw,13,*point(pos),unit(size));struct.pack_into('<d',raw,27,0);raw[35]=1 if layer==34 else 0;struct.pack_into('<i',raw,36,unit(.12));raw[41]=1 if isref else 0;raw[46:56]='Arial'.encode('utf-16le');struct.pack_into('<I',raw,115,4294967295)
 s=s.encode('ascii');texts.append(rec(5,raw)+block(bytes([len(s)])+s))
for d in g['draw']:
 if d['type']=='text':textrec(d['text'],[d['pos'][0]+(1 if LAY[d['layer']]==34 else -1)*len(d['text'])*d['size'][0]*.30,d['pos'][1]+d['size'][1]/2],d['size'][1],LAY[d['layer']])
for p in g['parts']:textrec(p['ref'],[p['pos'][0]-.7,p['pos'][1]-1.7],.75,57 if p['layer']=='F.Cu' else 58,compid[p['ref']],True)
put('Texts6',texts)
vias=[]
for v in g['vias']:
 raw=bytearray((S/'Vias6_sample.bin').read_bytes());raw[0]=74;raw[1]=108;raw[2]=0;struct.pack_into('<HHHHH',raw,3,netid[v['net']],65535,65535,65535,65535);struct.pack_into('<4i',raw,13,*point(v['pos']),unit(v['diameter']),unit(v['drill']));raw[29]=1;raw[30]=32;raw[74]=0
 for offset in range(75,203,4):struct.pack_into('<i',raw,offset,unit(v['diameter']))
 vias.append(rec(3,raw))
put('Vias6',vias)
# Native polygons plus their filled copper regions; local capacitance cutouts.
polys=[];regions=[];shape_regions=[]
def region(ps,holes,layer,net='',poly=65535,kind=0,name='',extended=False):
 hdr=bytearray(18);hdr[0]=layer;hdr[1]=12;struct.pack_into('<HHHHH',hdr,3,netid.get(net,65535),poly,65535,65535,65535);struct.pack_into('<H',hdr,14,len(holes))
 r={'V7_LAYER':LNAME[layer],'NAME':name,'KIND':kind,'SUBPOLYINDEX':0 if poly!=65535 else 65535,'UNIONINDEX':0,'ARCRESOLUTION':mil(.02),'ISSHAPEBASED':'TRUE' if extended else 'FALSE','ISBOARDCUTOUT':'FALSE'}
 data=bytes(hdr)+props(r)+struct.pack('<I',len(ps))
 for p in ps+([ps[0]] if extended else []):
  if extended:data+=struct.pack('<B5i2d',0,*point(p),0,0,0,0.,0.)
  else:data+=struct.pack('<2d',*point(p))
 for hs in holes:data+=struct.pack('<I',len(hs))+b''.join(struct.pack('<2d',*point(p)) for p in hs)
 return rec(11,data)
for z in sorted(g['zones'],key=lambda z:-z.get('priority',0)):
 layer=LAY[z['layer']]
 if z['keepout']:shape_regions.append(region(z['outline'],[],layer,kind=1,name=z['name'],extended=True));continue
 i=len(polys);r=dict(base,LAYER=LNAME[layer],NET=netid[z['net']],PRIMITIVELOCK='TRUE',POLYGONTYPE='Polygon',POUROVER='TRUE',REMOVEDEAD='TRUE',GRIDSIZE=mil(.05),TRACKWIDTH=mil(.15),HATCHSTYLE='Solid',USEOCTAGONS='FALSE',MINPRIMLENGTH=mil(.025),SHELVED='FALSE',RESTORELAYER='UNKNOWN',RESTORENET='',REMOVEISLANDSBYAREA='TRUE',REMOVENECKS='TRUE',AREATHRESHOLD='0',ARCRESOLUTION=mil(.02),NECKWIDTHTHRESHOLD=mil(.15),POUROVERSTYLE=1,NAME=','.join(str(ord(c)) for c in z['name']),POURINDEX=i+1,IGNOREVIOLATIONS='FALSE');verts(r,z['outline']);polys.append(props(r))
 for f in z['filled']:regions.append(region(f['outline'],f['holes'],layer,z['net'],i,name=z['name']))
for p in apertures:
 x,y=p['pos'];sx,sy=p['size'];layer=LAY[p['layers'][0]];shape_regions.append(region([(x-sx/2,y-sy/2),(x+sx/2,y-sy/2),(x+sx/2,y+sy/2),(x-sx/2,y+sy/2)],[],layer,name='EP_STENCIL',extended=True))
for d in g['draw']:
 if d['type']=='shape' and d['filled'] and d['layer'] in ['B.Mask','F.Mask']:
  x,y=d['start'];a,b=d['end'];shape_regions.append(region([(x,y),(a,y),(a,b),(x,b)],[],LAY[d['layer']],name='HEATSINK_MASK',extended=True))
put('Polygons6',polys);put('Regions6',regions);put('ShapeBasedRegions6',shape_regions)
# Rule scopes are mutually exclusive for thermal versus direct pad connections.
samples=json.loads((S/'rules_sample.json').read_text());rules=[]
def rule(kind,name,scope='All',priority=1,**kw):
 k,r=next((k,copy.deepcopy(r)) for k,r in samples if r['RULEKIND']==kind)
 r={a:b for a,b in r.items() if not a.startswith('MIDLAYER')};r.update(NAME=name,SCOPE1EXPRESSION=scope,SCOPE2EXPRESSION='All',PRIORITY=str(priority),COMMENT='',UNIQUEID=uid(name));r.update(kw);rules.append(struct.pack('<H',k)+props(r))
rule('Clearance','Copper_to_polygon_0p20',"InPolygon",1,GAP=mil(.20),GENERICCLEARANCE=mil(.20))
rule('Clearance','Copper_min_0p15','All',2,GAP=mil(.15),GENERICCLEARANCE=mil(.15))
rule('Width','Trace_width','All',MINLIMIT=mil(.15),MAXLIMIT=mil(1.5),PREFEREDWIDTH=mil(.3058))
solid="IsVia Or InComponent('U1') Or InComponent('H9') Or ((InComponent('C3') Or InComponent('C4') Or InComponent('C5') Or InComponent('C6')) And InNet('GND'))"
rule('PolygonConnect','Direct_RF_thermal_vias',solid,1,CONNECTSTYLE='Direct')
rule('PolygonConnect','Pad_thermal_relief','Not ('+solid+')',2,CONNECTSTYLE='Relief',RELIEFCONDUCTORWIDTH=mil(.25),AIRGAPWIDTH=mil(.20),RELIEFENTRIES='4')
rule('HoleSize','Finished_drill','All',MINLIMIT=mil(.20),MAXLIMIT=mil(3.2))
rule('MinimumAnnularRing','Annular_ring','All',MINIMUM=mil(.10))
rule('SolderMaskExpansion','Mask_expansion','All',EXPANSION=mil(.04))
for kind in ['ShortCircuit','UnRoutedNet','UnpouredPolygon']:rule(kind,kind)
put('Rules6',rules)
# Allocate new primitive IDs instead of reusing IDs from the blank carrier.
tags={'Arcs6':3329,'Board6':83,'BoardRegions':7522,'Nets6':520,'Components6':777,'Polygons6':1034,'Pads6':3586,'Vias6':3843,'Tracks6':4100,'Texts6':4357,'Regions6':4953,'ShapeBasedRegions6':5209}
ids=[]
for name,tag in tags.items():
 for i in range(counts.get(name,0)):ids.append(struct.pack('<II',tag,i)+uuid.uuid5(uuid.NAMESPACE_URL,f'qstl/revc/{name}/{i}').bytes_le)
put('PrimitiveGuids',ids)
out=H/'QSTL_THS3491_RGT_G20_RevC.PcbDoc'
if out.exists():out.unlink() # Only this generated destination; never the source carrier.
audit=update_copy(template,out,updates)
(H/'review/native_file_build.json').write_text(json.dumps(dict(counts=counts,stack=stack,source_carrier_unchanged=audit['source_unchanged'],altium_roundtrip_verified=False,sha256=audit['destination_sha256']),indent=2))
print(out,counts)
