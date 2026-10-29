from pathlib import Path
import argparse
import json
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description='Generate Altium-native pad shape repair and reopen verification.')
parser.add_argument('--pcb',type=Path,required=True)
parser.add_argument('--script-dir',type=Path,required=True)
parser.add_argument('--log',type=Path,required=True)
parser.add_argument('--assembly-finalization',action='store_true')
args=parser.parse_args()
d=args.script_dir.resolve(); d.mkdir(parents=True,exist_ok=True)
g=json.loads((ROOT/'review/native_geometry.json').read_text())
pads=[p for p in g['pads'] if p['ref'] in {'R14','R15','U1'}]
assert len(pads) in [19,21]
assert all(p['shape']==1 and p['roundrect_ratio']==0 for p in pads)
conditions='\n'.join(f"    If (Ref = '{p['ref']}') And (Pad.Name = '{p['num']}') Then Pct := {round(p['roundrect_ratio']*200)};" for p in pads)
template=r'''Function DesiredRadius(Pad : IPCB_Pad2) : Integer;
Var Ref : String; Pct : Integer;
Begin
    Pct := -1;
    Ref := '';
    If Pad.Component <> Nil Then Ref := Pad.Component.Name.Text;
__CONDITIONS__
    Result := Pct;
End;

Procedure ShapeRepair;
Var
    Doc : IServerDocument;
    Board : IPCB_Board;
    Iterator : IPCB_BoardIterator;
    Pad : IPCB_Pad2;
    Pct, Count, Failures, I, Total, TopPads, BottomPads, MultiPads, OtherPads : Integer;
    Obj : IPCB_Primitive;
    PadList : TInterfaceList;
    Report : TStringList;
    FileName, LogFile, Ref : String;
Begin
    FileName := '__PCB__';
    LogFile := '__LOG__';
    Report := TStringList.Create;
    Report.Add('START'); Report.SaveToFile(LogFile);
    Doc := Client.OpenDocument('PCB', FileName);
    If Doc = Nil Then Exit;
    Report.Add('Document opened'); Report.SaveToFile(LogFile);
    If Doc.Modified Then Begin Report.Add('ABORT: document has unsaved changes'); Report.SaveToFile(LogFile); Exit; End;
    Client.ShowDocument(Doc);
    If Not Doc.DoFileSave('PCB Binary') Then Exit;
    Report.Add('NORMALIZED'); Report.SaveToFile(LogFile);
    Client.CloseDocument(Doc);
    Doc := Client.OpenDocument('PCB', FileName);
    Client.ShowDocument(Doc);
    Board := PCBServer.GetPCBBoardByPath(FileName);
    If Board = Nil Then Exit;
    Report.Add('Board available'); Report.SaveToFile(LogFile);
    Count := 0;
    PadList := TInterfaceList.Create;
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(ePadObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    Pad := Iterator.FirstPCBObject;
    While Pad <> Nil Do
    Begin
        If DesiredRadius(Pad)>=0 Then PadList.Add(Pad);
        Pad := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
    Report.Add('COLLECTED=' + IntToStr(PadList.Count)); Report.SaveToFile(LogFile);
    PCBServer.PreProcess;
    Try
        For I := 0 To PadList.Count-1 Do
        Begin
            Pad := PadList.Items[I];
            Pct := DesiredRadius(Pad);
            If Pct >= 0 Then
            Begin
                Report.Add('EDIT=' + Pad.Component.Name.Text + '.' + Pad.Name); Report.SaveToFile(LogFile);
                Pad.TopShape := eRectangular;
                Report.Add('SHAPE SET'); Report.SaveToFile(LogFile);
                Pad.StackCRPctOnLayer[eTopLayer] := Pct;
                Report.Add('RADIUS SET'); Report.SaveToFile(LogFile);
                Inc(Count);
            End;
        End;
    Finally
        PCBServer.PostProcess;
    End;
    PadList.Free;
    Report.Add('Changed=' + IntToStr(Count)); Report.SaveToFile(LogFile);
    Board.ViewManager_FullUpdate;
    If Not Doc.DoFileSave('PCB Binary') Then Begin Report.Add('SAVE FAILED'); Report.SaveToFile(LogFile); Exit; End;
    Report.Add('SAVED'); Report.Add('Native save succeeded'); Report.SaveToFile(LogFile);
    Client.CloseDocument(Doc);
    Report.Add('Closed saved document'); Report.SaveToFile(LogFile);
    Doc := Client.OpenDocument('PCB', FileName);
    If Doc = Nil Then Exit;
    Client.ShowDocument(Doc);
    Board := PCBServer.GetPCBBoardByPath(FileName);
    If Board = Nil Then Exit;
    Report.Add('REOPENED'); Report.Add('Native reopen succeeded'); Report.SaveToFile(LogFile);
    Count := 0; Failures := 0;
    Total := 0; TopPads := 0; BottomPads := 0; MultiPads := 0; OtherPads := 0;
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(ePadObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    Pad := Iterator.FirstPCBObject;
    While Pad <> Nil Do
    Begin
        Inc(Total);
        If Pad.Layer=eTopLayer Then Inc(TopPads)
        Else If Pad.Layer=eBottomLayer Then Inc(BottomPads)
        Else If Pad.Layer=eMultiLayer Then Inc(MultiPads)
        Else Inc(OtherPads);
        Pct := DesiredRadius(Pad);
        If Pct >= 0 Then
        Begin
            Inc(Count);
            Ref := Pad.Component.Name.Text;
            Report.Add('PAD,' + Ref + ',' + Pad.Name + ',shape=' + IntToStr(Pad.TopShape) + ',radius_pct=' + IntToStr(Pad.CRPercentage[eTopLayer]) + ',xsize=' + IntToStr(Pad.TopXSize) + ',ysize=' + IntToStr(Pad.TopYSize) + ',radius=' + IntToStr(Pad.CornerRadius[eTopLayer]));
            { Rectangle has zero effective CornerRadius. Altium reloads the
              inactive rounded-rectangle percentage as its default 50. }
            If (Pad.TopShape <> eRectangular) Or (Pad.CornerRadius[eTopLayer] <> 0) Then Inc(Failures);
        End;
        Pad := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
    Report.Add('Verified=' + IntToStr(Count));
    Report.Add('Failures=' + IntToStr(Failures));
    Report.Add('Pads=' + IntToStr(Total));
    Report.Add('TopPads=' + IntToStr(TopPads));
    Report.Add('BottomPads=' + IntToStr(BottomPads));
    Report.Add('MultiPads=' + IntToStr(MultiPads));
    Report.Add('OtherPads=' + IntToStr(OtherPads));
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eTrackObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    Total := 0; Obj := Iterator.FirstPCBObject;
    While Obj <> Nil Do Begin Inc(Total); Obj := Iterator.NextPCBObject; End;
    Board.BoardIterator_Destroy(Iterator);
    Report.Add('Tracks=' + IntToStr(Total));
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eViaObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    Total := 0; Obj := Iterator.FirstPCBObject;
    While Obj <> Nil Do Begin Inc(Total); Obj := Iterator.NextPCBObject; End;
    Board.BoardIterator_Destroy(Iterator);
    Report.Add('Vias=' + IntToStr(Total));
    Board.ViewManager_FullUpdate;
    Client.SendMessage('PCB:Zoom','Action=All',255,Client.CurrentView);
    Report.SaveToFile(LogFile);
    Report.Free;
End;
'''
script=template.replace('__CONDITIONS__',conditions).replace('__PCB__',str(args.pcb.resolve())).replace('__LOG__',str(args.log.resolve()))
if args.assembly_finalization:
    script=script.replace('Obj : IPCB_Primitive;', 'Obj : IPCB_Primitive; Txt : IPCB_Text; Body : IPCB_ComponentBody; KillList : TInterfaceList;')
    script=script.replace("Report.Add('START');", "Report.Add('START'); Report.Add('PCB='+FileName);")
    cleanup=r'''
    KillList:=TInterfaceList.Create;
    Iterator:=Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eTextObject));Iterator.AddFilter_LayerSet(MkSet(eTopOverlay));Iterator.AddFilter_Method(eProcessAll);
    Txt:=Iterator.FirstPCBObject;
    While Txt<>Nil Do Begin
      If (Txt.Text='TI RF geometry / JLC 4L adaptation') Or (Txt.Text='QSTL / THS3491 RGT / REV D') Then KillList.Add(Txt);
      Txt:=Iterator.NextPCBObject;
    End;Board.BoardIterator_Destroy(Iterator);
    PCBServer.PreProcess;
    Try
      For I:=0 To KillList.Count-1 Do Begin
        Obj:=KillList.Items[I];Board.RemovePCBObject(Obj);
        PCBServer.SendMessageToRobots(Board.I_ObjectAddress,c_Broadcast,PCBM_BoardRegisteration,Obj.I_ObjectAddress);
      End;
    Finally PCBServer.PostProcess;End;
    Report.Add('Review silk removed='+IntToStr(KillList.Count));Report.SaveToFile(LogFile);KillList.Free;
'''
    script=script.replace("    Report.Add('Board available'); Report.SaveToFile(LogFile);", "    Report.Add('Board available'); Report.SaveToFile(LogFile);"+cleanup)
    model_check=r'''
    Count:=0;Iterator:=Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eComponentBodyObject));Iterator.AddFilter_LayerSet(AllLayers);Iterator.AddFilter_Method(eProcessAll);
    Body:=Iterator.FirstPCBObject;
    While Body<>Nil Do Begin
      If Body.Component=Nil Then Begin Report.Add('ERROR unbound body');Report.SaveToFile(LogFile);Exit;End;
      If Body.Model=Nil Then Begin Report.Add('ERROR missing model');Report.SaveToFile(LogFile);Exit;End;
      Inc(Count);Report.Add('BODY,'+Body.Component.Name.Text+',side='+IntToStr(Body.BodyProjection)+',layer='+IntToStr(Body.Layer));
      Body:=Iterator.NextPCBObject;
    End;Board.BoardIterator_Destroy(Iterator);
    Report.Add('COUNT='+IntToStr(Count));
'''
    at=script.rfind('    Board.ViewManager_FullUpdate;')
    script=script[:at]+model_check+script[at:]
# Keep older RunScript commands compatible with the actual entry point.
script+='\nProcedure RunShapeRepair;\nBegin\n    ShapeRepair;\nEnd;\n'
(d/'ShapeRepair.pas').write_text(script)
(d/'ShapeRepair.PrjScr').write_text('[Design]\nVersion=1.0\n[Document1]\nDocumentPath=ShapeRepair.pas\n')
