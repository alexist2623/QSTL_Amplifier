"""Generate native Altium STEP insertion / save / reopen verification script."""
from pathlib import Path
import argparse
import json

ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser()
p.add_argument('--pcb',type=Path,required=True)
p.add_argument('--script-dir',type=Path,required=True)
p.add_argument('--log',type=Path,required=True)
p.add_argument('--verify-only',action='store_true',help='Save/reopen and verify an already populated PCB without adding models')
p.add_argument('--add-refs',nargs='+',help='Add only these new component bodies; preserve already embedded models')
a=p.parse_args();d=a.script_dir.resolve();d.mkdir(parents=True,exist_ok=True)
data=json.loads((ROOT/'models3d/placements.json').read_text(encoding='utf-8'))
calls=[]
for row in data['placements']:
    if a.add_refs and row['ref'] not in a.add_refs: continue
    model=str(ROOT/'models3d'/row['model'])
    layer='eMechanical14' if row['side']=='bottom' else 'eMechanical13'
    side=1 if row['side']=='bottom' else 0
    calls.append("    If Comp.Name.Text = '{}' Then AddModel(Board, Comp, '{}', {}, {}, {}, Report, LogFile);".format(row['ref'],model,row['rotation_z'],layer,side))
script=r'''Var ModelFailed : Boolean;

Procedure AddModel(Board:IPCB_Board; Comp:IPCB_Component; Path:String;
 ZRotation:Double; MechLayer:TLayer; Side:Integer; Report:TStringList; LogFile:String);
Var Body:IPCB_ComponentBody; Model:IPCB_Model;
Begin
 Report.Add('LOAD,'+Comp.Name.Text+','+Path);Report.SaveToFile(LogFile);
 Body:=PCBServer.PCBObjectFactory(eComponentBodyObject,eNoDimension,eCreate_Default);
 If Body=Nil Then Begin Report.Add('ERROR body factory'); Report.SaveToFile(LogFile); ModelFailed:=True; Exit; End;
 Model:=Body.ModelFactory_FromFilename(Path,False);
 If Model=Nil Then Begin Report.Add('ERROR STEP load '+Path); Report.SaveToFile(LogFile); ModelFailed:=True; Exit; End;
 Model.SetState(0,0,ZRotation,0);
 Body.SetState_FromModel; Body.Model:=Model;
 Board.AddPCBObject(Body); Comp.AddPCBObject(Body);
 PCBServer.SendMessageToRobots(Board.I_ObjectAddress,c_Broadcast,PCBM_BoardRegisteration,Body.I_ObjectAddress);
 Body.BeginModify;
 Try
  Body.Layer:=MechLayer;
  Body.BodyProjection:=Side;
  Body.MoveByXY(Comp.X,Comp.Y);
 Finally Body.EndModify; End;
 Report.Add('ADDED,'+Comp.Name.Text);Report.SaveToFile(LogFile);
End;

Procedure AddComponentModels;
Var Doc:IServerDocument; Board:IPCB_Board; Iter:IPCB_BoardIterator;
 Comp:IPCB_Component; Body:IPCB_ComponentBody; Parts:TInterfaceList;
 Report:TStringList; FileName,LogFile:String; I,Count:Integer;
Begin
 FileName:='__PCB__';LogFile:='__LOG__';
 ModelFailed:=False;Report:=TStringList.Create;Report.Add('START');Report.Add('PCB='+FileName);Report.SaveToFile(LogFile);
 Doc:=Client.OpenDocument('PCB',FileName);
 If Doc=Nil Then Exit;
 If Doc.Modified Then Begin Report.Add('ABORT unsaved changes');Report.SaveToFile(LogFile);Exit;End;
 Client.ShowDocument(Doc);Board:=PCBServer.GetPCBBoardByPath(FileName);If Board=Nil Then Exit;
 Iter:=Board.BoardIterator_Create;Iter.AddFilter_ObjectSet(MkSet(eComponentBodyObject));
 Iter.AddFilter_LayerSet(AllLayers);Iter.AddFilter_Method(eProcessAll);
 Body:=Iter.FirstPCBObject;If Body<>Nil Then Begin
  Board.BoardIterator_Destroy(Iter);Report.Add('ABORT existing bodies');Report.SaveToFile(LogFile);Exit;
 End;Board.BoardIterator_Destroy(Iter);
 Parts:=TInterfaceList.Create;Iter:=Board.BoardIterator_Create;
 Iter.AddFilter_ObjectSet(MkSet(eComponentObject));Iter.AddFilter_LayerSet(AllLayers);Iter.AddFilter_Method(eProcessAll);
 Comp:=Iter.FirstPCBObject;While Comp<>Nil Do Begin Parts.Add(Comp);Comp:=Iter.NextPCBObject;End;
 Board.BoardIterator_Destroy(Iter);
 PCBServer.PreProcess;
 Try
  For I:=0 To Parts.Count-1 Do Begin Comp:=Parts.Items[I];
__CALLS__
   If ModelFailed Then Break;
  End;
 Finally PCBServer.PostProcess;End;
 Parts.Free;If ModelFailed Then Exit;Board.ViewManager_FullUpdate;
 If Not Doc.DoFileSave('PCB Binary') Then Begin Report.Add('SAVE FAILED');Report.SaveToFile(LogFile);Exit;End;
 Report.Add('SAVED');Report.SaveToFile(LogFile);Client.CloseDocument(Doc);
 Doc:=Client.OpenDocument('PCB',FileName);If Doc=Nil Then Exit;Client.ShowDocument(Doc);
 Board:=PCBServer.GetPCBBoardByPath(FileName);If Board=Nil Then Exit;
 Iter:=Board.BoardIterator_Create;Iter.AddFilter_ObjectSet(MkSet(eComponentBodyObject));
 Iter.AddFilter_LayerSet(AllLayers);Iter.AddFilter_Method(eProcessAll);
 Count:=0;Body:=Iter.FirstPCBObject;
 While Body<>Nil Do Begin
  Inc(Count);If Body.Component=Nil Then Begin Report.Add('ERROR unbound body');Report.SaveToFile(LogFile);Exit;End;
  If Body.Model=Nil Then Begin Report.Add('ERROR missing model');Report.SaveToFile(LogFile);Exit;End;
  Report.Add('BODY,'+Body.Component.Name.Text+',side='+IntToStr(Body.BodyProjection)+',layer='+IntToStr(Body.Layer));
  Body:=Iter.NextPCBObject;
 End;Board.BoardIterator_Destroy(Iter);
 Report.Add('COUNT='+IntToStr(Count));
 If Count<>__COUNT__ Then Begin Report.Add('ERROR unexpected body count');Report.SaveToFile(LogFile);Exit;End;
 Report.Add('REOPENED');Report.SaveToFile(LogFile);
 Client.SendMessage('PCB:Zoom','Action=All',255,Client.CurrentView);
 Report.Free;
End;
'''.replace('__PCB__',str(a.pcb.resolve())).replace('__LOG__',str(a.log.resolve())).replace('__CALLS__','\n'.join(calls)).replace('__COUNT__',str(len(data['placements'])))
if a.verify_only:
    start=script.index(' Iter:=Board.BoardIterator_Create;')
    end=script.index(" If Not Doc.DoFileSave('PCB Binary')",start)
    script=script[:start]+script[end:]
elif a.add_refs:
    start=script.index(' Body:=Iter.FirstPCBObject;If Body<>Nil Then Begin')
    end=script.index(' Parts:=TInterfaceList.Create;',start)
    conditions=' Or '.join("(Body.Component.Name.Text='{}')".format(ref) for ref in a.add_refs)
    script=script[:start]+''' Count:=0;Body:=Iter.FirstPCBObject;
 While Body<>Nil Do Begin
  If Body.Component=Nil Then Exit;
  If '''+conditions+''' Then Begin Report.Add('ABORT duplicate target body');Report.SaveToFile(LogFile);Exit;End;
  Inc(Count);Body:=Iter.NextPCBObject;
 End;Board.BoardIterator_Destroy(Iter);
 If Count<>'''+str(len(data['placements'])-len(a.add_refs))+''' Then Begin Report.Add('ABORT baseline model count');Report.SaveToFile(LogFile);Exit;End;
'''+script[end:]
(d/'AddModels.pas').write_text(script,encoding='utf-8')
(d/'AddModels.PrjScr').write_text('[Design]\nVersion=1.0\n[Document1]\nDocumentPath=AddModels.pas\n',encoding='utf-8')
print(d/'AddModels.PrjScr')
