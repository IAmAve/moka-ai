# MOKA AI Cleanup Script

param(
    [switch]$Force,
    [switch]$Full
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot

Write-Host "=== MOKA AI Cleanup ===" -ForegroundColor Cyan

if (-not $Force) {
    Write-Host "This will remove generated files. Use -Force to skip confirmation." -ForegroundColor Yellow
    $confirmation = Read-Host "Continue? (y/n)"
    if ($confirmation -ne "y") {
        Write-Host "Cancelled."
        exit 0
    }
}

# Remove Python cache
Write-Host "[1/4] Removing __pycache__ directories..." -ForegroundColor Yellow
Get-ChildItem -Path $RepoRoot -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue | ForEach-Object {
    Remove-Item -Path $_.FullName -Recurse -Force
    Write-Host "  Removed: $($_.FullName)"
}

# Remove .pyc files
Write-Host "[2/4] Removing .pyc files..." -ForegroundColor Yellow
Get-ChildItem -Path $RepoRoot -Recurse -Filter "*.pyc" -ErrorAction SilentlyContinue | ForEach-Object {
    Remove-Item -Path $_.FullName -Force
}

# Remove test artifacts
if ($Full) {
    Write-Host "[3/4] Removing test artifacts..." -ForegroundColor Yellow
    $testArtifacts = @(".pytest_cache", "test-results", "htmlcov", ".coverage")
    foreach ($artifact in $testArtifacts) {
        $path = Join-Path $RepoRoot $artifact
        if (Test-Path $path) {
            Remove-Item -Path $path -Recurse -Force
            Write-Host "  Removed: $artifact"
        }
    }
}

# Clear logs (optionally)
Write-Host "[4/4] Clearing logs..." -ForegroundColor Yellow
$logsDir = Join-Path $RepoRoot "logs"
if (Test-Path $logsDir) {
    Get-ChildItem -Path $logsDir -Filter "*.log" -ErrorAction SilentlyContinue | ForEach-Object {
        Remove-Item -Path $_.FullName -Force
        Write-Host "  Removed: logs/$($_.Name)"
    }
}

Write-Host ""
Write-Host "=== Cleanup Complete ===" -ForegroundColor Green