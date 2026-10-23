Procedure NativeCheck;
Var
    Report : TStringList;
    Doc : IServerDocument;
    Board : IPCB_Board;
    Iterator : IPCB_BoardIterator;
    Obj : IPCB_Primitive;
    Pad : IPCB_Pad;
    Count, TopPads, BottomPads, MultiPads, OtherPads : Integer;
    FileName, LogFile : String;
Begin
    LogFile := 'C:\Jeonghyun\SNU_GIT\QSTL_Amplifier\hardware\THS3491_RGT_G20\altium_revD\review\altium_native_check.txt';
    Report := TStringList.Create;
    Report.Add('Native check started');
    Report.SaveToFile(LogFile);
    FileName := 'C:\Jeonghyun\SNU_GIT\QSTL_Amplifier\hardware\THS3491_RGT_G20\altium_revD\QSTL_THS3491_RGT_G20_RevD.PcbDoc';
    Doc := Client.OpenDocument('PCB', FileName);
    If Doc = Nil Then Exit;
    Report.Add('Document opened');
    Report.SaveToFile(LogFile);
    Board := PCBServer.GetPCBBoardByPath(FileName);
    If Board = Nil Then Exit;
    Report.Add('Board available');
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(ePadObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    Count := 0; TopPads := 0; BottomPads := 0; MultiPads := 0; OtherPads := 0;
    Pad := Iterator.FirstPCBObject;
    While Pad <> Nil Do
    Begin
        Inc(Count);
        If Pad.Layer = eTopLayer Then Inc(TopPads)
        Else If Pad.Layer = eBottomLayer Then Inc(BottomPads)
        Else If Pad.Layer = eMultiLayer Then Inc(MultiPads)
        Else Inc(OtherPads);
        Report.Add('PAD,' + Pad.Name + ',' + IntToStr(Pad.Layer) + ',' + IntToStr(Pad.X) + ',' + IntToStr(Pad.Y));
        Pad := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
    Report.Add('Pads=' + IntToStr(Count));
    Report.Add('TopPads=' + IntToStr(TopPads));
    Report.Add('BottomPads=' + IntToStr(BottomPads));
    Report.Add('MultiPads=' + IntToStr(MultiPads));
    Report.Add('OtherPads=' + IntToStr(OtherPads));
    Iterator := Board.BoardIterator_Create;
    Iterator.AddFilter_ObjectSet(MkSet(eTrackObject));
    Iterator.AddFilter_LayerSet(AllLayers);
    Iterator.AddFilter_Method(eProcessAll);
    Count := 0;
    Obj := Iterator.FirstPCBObject;
    While Obj <> Nil Do
    Begin
        Inc(Count);
        Obj := Iterator.NextPCBObject;
    End;
    Board.BoardIterator_Destroy(Iterator);
    Report.Add('Tracks=' + IntToStr(Count));
    Report.SaveToFile(LogFile);
    Client.ShowDocument(Doc);
    If Doc.DoFileSave('PCB Binary') Then Report.Add('Native save succeeded')
    Else Report.Add('Native save FAILED');
    Report.SaveToFile(LogFile);
    Client.CloseDocument(Doc);
    Report.Add('Closed saved document');
    Report.SaveToFile(LogFile);
    Doc := Client.OpenDocument('PCB', FileName);
    If Doc = Nil Then Begin Report.Add('Reopen FAILED'); Report.SaveToFile(LogFile); Exit; End;
    Board := PCBServer.GetPCBBoardByPath(FileName);
    If Board = Nil Then Begin Report.Add('Reopened board unavailable'); Report.SaveToFile(LogFile); Exit; End;
    Report.Add('Native reopen succeeded');
    Client.ShowDocument(Doc);
    Board.ViewManager_FullUpdate;
    Client.SendMessage('PCB:Zoom', 'Action=All', 255, Client.CurrentView);
    Report.SaveToFile(LogFile);
    Report.Free;
End;
