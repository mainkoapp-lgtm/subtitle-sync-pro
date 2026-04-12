$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("C:\Users\desktop\Desktop\0_SUBTITLE_TOOL_LAUNCHER.lnk")
$Shortcut.TargetPath = "d:\Project Temporary\subtitle\subtitle_development\launcher\launch.bat"
$Shortcut.IconLocation = "d:\Project Temporary\subtitle\subtitle_development\launcher\icon.png"
$Shortcut.WorkingDirectory = "d:\Project Temporary\subtitle\subtitle_development\launcher"
$Shortcut.Save()
