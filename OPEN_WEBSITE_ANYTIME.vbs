Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Users\HP\OneDrive\Desktop\web1"
WshShell.Run "C:\Users\HP\python311\pythonw.exe scripts\launch.py", 0, False
