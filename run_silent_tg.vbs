Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "py -3 " & Chr(34) & "%USERPROFILE%\PCTrack\tracker.py" & Chr(34), 0, False
