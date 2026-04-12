Add-Type -AssemblyName System.Drawing
$pngPath = "d:\Project Temporary\subtitle\subtitle_development\launcher\icon.png"
$icoPath = "d:\Project Temporary\subtitle\subtitle_development\launcher\icon.ico"

$image = [System.Drawing.Bitmap]::FromFile($pngPath)
$iconHandle = $image.GetHicon()
$icon = [System.Drawing.Icon]::FromHandle($iconHandle)

$fileStream = New-Object System.IO.FileStream($icoPath, [System.IO.FileMode]::Create)
$icon.Save($fileStream)
$fileStream.Close()

$icon.Dispose()
$image.Dispose()

# Update Shortcut
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("C:\Users\desktop\Desktop\Subtitle_Tool.lnk")
$Shortcut.IconLocation = $icoPath
$Shortcut.Save()
