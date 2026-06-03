---
name: installer-unified-spec
description: Unified installer_webview.spec bundles all wizard + core files for single PyInstaller build
metadata:
  type: reference
---

# Installer Unified Spec

## File
`installer/installer_webview.spec` — unified PyInstaller spec (rewritten from old fragmented specs)

## What it bundles
- Entry: `installer_wizard/main.py`
- UI: `installer_wizard/` (main.py, api.py, index.html, styles.css, wizard.js)
- Logic: `installer/core/` (hardware, models, deps, writer, shortcuts, uninstaller)
- Data: `installer/data/` (tiers.yaml)
- Templates: `installer/templates/` (config.yaml.j2)
- Runtime: webview collect_data_files

## Build command
```powershell
cd installer
python -m PyInstaller --clean --noconfirm installer_webview.spec
# Output: dist/MokaAI-Setup/MokaAI-Setup.exe
```

## Build prerequisites
```
pip install pyinstaller webview pywin32 jinja2 pyyaml psutil
```

## Old specs (deprecated)
- `MokaAI-Setup.spec` (repo root) — dearpygui, deprecated
- `installer/installer_webview.spec` was incomplete, now replaced with this unified version