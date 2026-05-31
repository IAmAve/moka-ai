
$errLog = "C:\\Users\\Ave\\AppData\\Local\\Temp\\moka_err2.log"
"Starting at $(Get-Date)" | Out-File $errLog
$proc = Start-Process -FilePath "D:/Ave/Documents/PROJECTS/moka-ai/installer/dist/MokaAI-Setup/MokaAI-Setup.exe" -PassThru -RedirectStandardError $errLog
"Started PID: $($proc.Id)" | Add-Content $errLog
Start-Sleep 5
if ($proc.HasExited) {
    "Exited with code: $($proc.ExitCode)" | Add-Content $errLog
} else {
    "Still running, WS=$([math]::Round($proc.WorkingSet64/1MB))MB" | Add-Content $errLog
    Start-Sleep 10
    if (-not $proc.HasExited) { Stop-Process $proc.Id -Force -ErrorAction SilentlyContinue }
    "Stopped at $(Get-Date)" | Add-Content $errLog
}
"Done at $(Get-Date)" | Add-Content $errLog
