
$errLog = "$env:TEMP\moka_install_test.log"
$env:MOKA_DEBUG = "1"
$proc = Start-Process -FilePath "D:/Ave/Documents/PROJECTS/moka-ai/installer/dist/MokaAI-Setup/MokaAI-Setup.exe" -PassThru -RedirectStandardError $errLog
Write-Host "PID: $($proc.Id)"
Start-Sleep 3

# Check if still running
try {
    $p = Get-Process -Id $proc.Id -ErrorAction Stop
    Write-Host "Status: RUNNING, WS=$([math]::Round($p.WorkingSet64/1MB))MB"
} catch {
    Write-Host "Status: EXITED (code=$($proc.ExitCode))"
}

# Read stderr log
if (Test-Path $errLog) {
    $content = Get-Content $errLog -Raw
    if ($content) { Write-Host "STDERR: $content" }
}
