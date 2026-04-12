$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("C:\Users\desktop\Desktop\Subtitle_Tool.lnk")
$Shortcut.TargetPath = "d:\Project Temporary\subtitle\subtitle_development\launcher\launch.bat"
$Shortcut.WorkingDirectory = "d:\Project Temporary\subtitle\subtitle_development\launcher"
$Shortcut.Save()
