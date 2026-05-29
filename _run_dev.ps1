$errLog = "$env:TEMP\moka_dev_err.log"
"Starting at $(Get-Date)" | Out-File $errLog
$pythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $pythonExe) {
    $pythonExe = "python"
}
$script = "D:\Ave\Documents\PROJECTS\moka-ai\installer_wizard\__main__.py"
"Running: $pythonExe $script" | Add-Content $errLog
$proc = Start-Process -FilePath $pythonExe -ArgumentList $script -PassThru -RedirectStandardError $errLog -WorkingDirectory "D:\Ave\Documents\PROJECTS\moka-ai"
"Started PID: $($proc.Id)" | Add-Content $errLog
Start-Sleep 8
if ($proc.HasExited) {
    "Exited with code: $($proc.ExitCode)" | Add-Content $errLog
} else {
    "Still running, WS=$([math]::Round($proc.WorkingSet64/1MB))MB - app window should be visible" | Add-Content $errLog
    "Stopping..." | Add-Content $errLog
    Stop-Process $proc.Id -Force -ErrorAction SilentlyContinue
}
"DONE at $(Get-Date)" | Add-Content $errLog
Get-Content $errLog | Select-Object -Last 20