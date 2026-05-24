# MOKA AI Test Runner Script

param(
    [switch]$Verbose,
    [switch]$Coverage,
    [string]$Pattern = "*",
    [switch]$Fast
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot

Write-Host "=== MOKA AI Test Runner ===" -ForegroundColor Cyan

# Set test path
$testPath = if ($Pattern -eq "*") {
    "tests/"
} else {
    "tests/test_$Pattern.py"
}

# Build pytest arguments
$args = @($testPath, "-v")

if ($Coverage) {
    $args += @("--cov=. --cov-report=html --cov-report=term")
}
if ($Fast) {
    $args += @("-x")  # Stop on first failure
}
if ($Verbose) {
    $args += @("-vv")
}
$args += @("--tb=short")

# Run tests
Push-Location $RepoRoot
try {
    python -m pytest @args
    $exitCode = $LASTEXITCODE

    if ($exitCode -eq 0) {
        Write-Host ""
        Write-Host "All tests passed!" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "Some tests failed (exit code: $exitCode)" -ForegroundColor Red
    }

    exit $exitCode
} catch {
    Write-Host "Test execution failed: $_" -ForegroundColor Red
    exit 1
} finally {
    Pop-Location
}