# MOKA AI Development Run Script

param(
    [switch]$Debug,
    [switch]$NoValidation
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot

Write-Host "=== MOKA AI Development ===" -ForegroundColor Cyan

# Set environment
$env:PYTHONPATH = $RepoRoot

if ($Debug) {
    $env:LOG_LEVEL = "DEBUG"
    Write-Host "Debug mode enabled" -ForegroundColor Yellow
}

# Check requirements
Write-Host "Checking environment..." -ForegroundColor Yellow

# Verify logs directory exists
$logsDir = Join-Path $RepoRoot "logs"
if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir | Out-Null
    Write-Host "  Created logs/ directory" -ForegroundColor Green
}

# Check config
$configFile = Join-Path $RepoRoot "config\config.json"
if (-not (Test-Path $configFile)) {
    Write-Host "  WARNING: config/config.json not found. Run scripts/setup.ps1 first." -ForegroundColor Yellow
}

# Run MOKA
Write-Host "Starting MOKA AI..." -ForegroundColor Green
Write-Host ""

Push-Location $RepoRoot
try {
    python moka.py
} finally {
    Pop-Location
}