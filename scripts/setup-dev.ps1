# MOKA AI Developer Setup Script
# Sets up the development environment with additional tools

param(
    [switch]$SkipPreCommit
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot

Write-Host "=== MOKA AI Developer Setup ===" -ForegroundColor Cyan
Write-Host ""

# Install dev tools
Write-Host "[1/4] Installing development tools..." -ForegroundColor Yellow
$devTools = @(
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "flake8>=6.0.0",
    "mypy>=1.0.0",
    "safety>=2.3.0",
    "black>=23.0.0",
    "isort>=5.12.0"
)

foreach ($tool in $devTools) {
    Write-Host "  Installing $tool..." -ForegroundColor Gray
    pip install $tool 2>&1 | Out-Null
}
Write-Host "  Development tools installed" -ForegroundColor Green

# Setup pre-commit hooks
if (-not $SkipPreCommit) {
    Write-Host "[2/4] Setting up pre-commit hooks..." -ForegroundColor Yellow
    $preCommitContent = @"
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files

  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black
        language_version: python

  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort
"@

    $hooksDir = Join-Path $RepoRoot ".git\hooks"
    if (-not (Test-Path $hooksDir)) {
        New-Item -ItemType Directory -Path $hooksDir | Out-Null
    }

    $preCommitPath = Join-Path $RepoRoot ".pre-commit-config.yaml"
    Set-Content -Path $preCommitPath -Value $preCommitContent
    Write-Host "  Created .pre-commit-config.yaml" -ForegroundColor Green

    # Install pre-commit
    pip install pre-commit 2>&1 | Out-Null
    Push-Location $RepoRoot
    try {
        pre-commit install 2>&1 | Out-Null
        Write-Host "  Pre-commit hooks installed" -ForegroundColor Green
    } catch {
        Write-Host "  WARNING: Could not install pre-commit hooks" -ForegroundColor Yellow
    } finally {
        Pop-Location
    }
}

# Create VS Code settings
Write-Host "[3/4] Setting up VS Code configuration..." -ForegroundColor Yellow
$vscodeDir = Join-Path $RepoRoot ".vscode"
if (-not (Test-Path $vscodeDir)) {
    New-Item -ItemType Directory -Path $vscodeDir | Out-Null
}

$vscodeSettings = @{
    "python.linting.flake8Enabled" = $true
    "python.linting.mypyEnabled" = $true
    "python.formatting.provider" = "black"
    "python.testing.pytestEnabled" = $true
    "python.testing.pytestArgs" = @("tests/", "-v")
    "files.exclude" = @{
        "**/__pycache__" = $true
        "**/*.pyc" = $true
    }
} | ConvertTo-Json -Depth 4

Set-Content -Path (Join-Path $vscodeDir "settings.json") -Value $vscodeSettings
Write-Host "  Created .vscode/settings.json" -ForegroundColor Green

# Create launch configuration
$launchConfig = @{
    version = "0.2.0"
    configurations = @(
        @{
            name = "Run MOKA AI"
            type = "debugpy"
            request = "launch"
            program = "moka.py"
            cwd = "`${workspaceFolder}"
            console = "integratedTerminal"
        }
    )
} | ConvertTo-Json -Depth 4

Set-Content -Path (Join-Path $vscodeDir "launch.json") -Value $launchConfig
Write-Host "  Created .vscode/launch.json" -ForegroundColor Green

# Verify setup
Write-Host "[4/4] Verifying installation..." -ForegroundColor Yellow
$checks = @(
    @{ name = "pytest"; cmd = "python -m pytest --version" }
    @{ name = "flake8"; cmd = "python -m flake8 --version" }
    @{ name = "black"; cmd = "python -m black --version" }
)

foreach ($check in $checks) {
    try {
        $result = Invoke-Expression $check.cmd 2>&1
        Write-Host "  $($check.name): OK" -ForegroundColor Green
    } catch {
        Write-Host "  $($check.name): FAILED" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "=== Developer Setup Complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "Run tests:   .\scripts\test.ps1" -ForegroundColor White
Write-Host "Run MOKA:    .\scripts\run.ps1" -ForegroundColor White
Write-Host "Clean:       .\scripts\clean.ps1 -Full" -ForegroundColor White