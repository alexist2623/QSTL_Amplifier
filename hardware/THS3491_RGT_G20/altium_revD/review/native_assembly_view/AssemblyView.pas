Procedure ShowFinalAssembly;
Var Doc:IServerDocument; Report:TStringList;
Begin
 Report:=TStringList.Create;
 Doc:=Client.OpenDocument('SCH','C:\Jeonghyun\SNU_GIT\QSTL_Amplifier\hardware\THS3491_RGT_G20\altium_revD\QSTL_THS3491_RGT_G20_RevD.SchDoc');If Doc=Nil Then Exit;
 Report.Add('FINAL SCHEMATIC OPENED');
 Doc:=Client.OpenDocument('PCB','C:\Jeonghyun\SNU_GIT\QSTL_Amplifier\hardware\THS3491_RGT_G20\altium_revD\QSTL_THS3491_RGT_G20_RevD.PcbDoc');If Doc=Nil Then Exit;Client.ShowDocument(Doc);
 Client.SendMessage('PCB:SwitchTo3D','',255,Client.CurrentView);
 Client.SendMessage('PCB:ResetCamera','To=ISOMETRIC',255,Client.CurrentView);
 Client.SendMessage('PCB:Zoom','Action=Document|Target=Board',255,Client.CurrentView);
 Report.Add('FINAL PCB OPENED; 3D VIEW REQUESTED');Report.SaveToFile('C:\Jeonghyun\SNU_GIT\QSTL_Amplifier\hardware\THS3491_RGT_G20\altium_revD\review\native_assembly_view\view.txt');Report.Free;
End;
