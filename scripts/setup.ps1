# MOKA AI Setup Script
# Run this once to set up the development environment

param(
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot

Write-Host "=== MOKA AI Setup ===" -ForegroundColor Cyan
Write-Host "Repository: $RepoRoot"
Write-Host ""

# Create required directories
Write-Host "[1/5] Creating directories..." -ForegroundColor Yellow
$dirs = @("logs", "data", "workspace", "models", "config")
foreach ($dir in $dirs) {
    $path = Join-Path $RepoRoot $dir
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Path $path | Out-Null
        Write-Host "  Created: $dir/" -ForegroundColor Green
    } else {
        Write-Host "  Exists: $dir/" -ForegroundColor Gray
    }
}

# Check Python
Write-Host "[2/5] Checking Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  Found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Python not found. Please install Python 3.11+" -ForegroundColor Red
    exit 1
}

# Install dependencies
Write-Host "[3/5] Installing dependencies..." -ForegroundColor Yellow
$requirements = Join-Path $RepoRoot "requirements.txt"
if (Test-Path $requirements) {
    pip install -r $requirements
    Write-Host "  Dependencies installed" -ForegroundColor Green
} else {
    Write-Host "  WARNING: requirements.txt not found" -ForegroundColor Yellow
}

# Create config file
Write-Host "[4/5] Setting up configuration..." -ForegroundColor Yellow
$configDir = Join-Path $RepoRoot "config"
$configFile = Join-Path $configDir "config.json"
if (-not (Test-Path $configFile)) {
    $defaultConfig = @{
        log_level = "INFO"
        max_workers = 4
        voice_enabled = $true
        memory_backend = "sqlite"
        storage_path = "data/"
        plugins_path = "plugins/"
        models_path = "models/"
        temp_path = "temp/"
    } | ConvertTo-Json -Depth 3
    Set-Content -Path $configFile -Value $defaultConfig
    Write-Host "  Created: config/config.json" -ForegroundColor Green
}

# Run tests
if (-not $SkipTests) {
    Write-Host "[5/5] Running tests..." -ForegroundColor Yellow
    Push-Location $RepoRoot
    try {
        python -m pytest tests/ -v --tb=short
        Write-Host "  Tests passed" -ForegroundColor Green
    } catch {
        Write-Host "  WARNING: Some tests may have failed. Run scripts/test.ps1 for details." -ForegroundColor Yellow
    } finally {
        Pop-Location
    }
}

Write-Host ""
Write-Host "=== Setup Complete ===" -ForegroundColor Cyan
Write-Host "Run 'python moka.py' to start MOKA AI." -ForegroundColor White