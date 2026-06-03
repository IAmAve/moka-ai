# Moka AI — Installation Guide

## Overview

Moka AI uses a native WebView2 installer for Windows. The installer is a single executable that bundles all required files and dependencies — no internet connection needed after download.

![Full App Screenshot](docs/superpowers/screenshots/full-app.png)

---

## System Requirements

| Requirement | Minimum | Recommended |
|---|---|---|
| OS | Windows 10 (64-bit) | Windows 11 |
| RAM | 8 GB | 16 GB |
| GPU | Integrated Graphics | NVIDIA/AMD dedicated GPU |
| VRAM | — | 4 GB+ for base models |
| Disk | 5 GB free | 10 GB+ free |
| WebView2 | Built-in (Win10 1803+) | Always up-to-date |

> WebView2 is pre-installed on Windows 10 (build 1803+) and all of Windows 11. If missing, the installer will prompt to install it automatically.

---

## Download

Download the latest `MokaAI-Setup.exe` from the `dist/` directory:

```
dist/MokaAI-Setup/MokaAI-Setup.exe
```

---

## How to Install

### Logger Utility

`utils/logger.py` provides a helper to normalize logger objects so that code can safely call `logger.info(msg)` regardless of whether a full `logging.Logger`, a simple callable, or `None` was supplied.

**Usage example:**
```python
from utils.logger import normalize_logger

# Accept any logger-like object
custom_logger = lambda msg: print(f"CUSTOM: {msg}")
log = normalize_logger(custom_logger)
log.info("Installer started")
```

The function returns a no‑op logger when `None` is passed, making it safe for optional logging.


### Step 1 — Run the Installer

1. Double-click `MokaAI-Setup.exe`
2. If Windows shows a SmartScreen warning, click **More info → Run anyway** (the app is signed, this is normal for unsigned installers during development)

**UI improvements:** The installer now includes ARIA labels for screen readers, proper focus management when navigating steps, and displays error dialogs with clear messages for missing permissions or failed downloads.

### Step 2 — Welcome Screen

The installer opens with a welcome screen. Choose your install location (default is recommended):

- **Default:** `C:\Users\<you>\AppData\Local\MokaAI`
- Click **Get Started** to proceed

### Step 3 — Hardware Detection

The installer automatically detects your:

- CPU (cores/threads)
- GPU (model, VRAM, compute capability)
- RAM and available disk space

This determines which AI models are recommended for your system.

### Step 4 — Model Selection

Choose which AI capabilities to install:

| Model Type | Description | VRAM Needed |
|---|---|---|
| **Base** | Conversational AI (required) | ~2 GB |
| **Image** | Image generation | 4–8 GB |
| **Voice** | TTS + speech recognition | ~1 GB |

The installer pre-selects the best tier based on your hardware. You can customize each category.

### Step 5 — Installing

The installer installs all selected components:

- Python dependencies (via pip)
- AI model files (downloaded on-demand)
- Configuration files
- Start Menu / Desktop shortcuts (optional)

A live progress bar and log are shown.

### Step 6 — Complete

Once done, choose:

- **Create Desktop Shortcut** — adds an icon on your Desktop
- **Create Start Menu Shortcut** — adds Moka AI to your app list
- **Launch Moka AI** — starts the app immediately

---

## Build from Source

### Prerequisites

Install Python dependencies:

```powershell
pip install pyinstaller webview pywin32 jinja2 pyyaml psutil
```

### Build the Installer

From the `installer/` directory:

```powershell
cd installer
python -m PyInstaller --clean --noconfirm installer_webview.spec
```

Output: `installer/dist/MokaAI-Setup/MokaAI-Setup.exe`

### Build Scripts

Two helper scripts are included at the repo root:

| File | Use |
|---|---|
| `_build.bat` | Full build with prompts, displays exe size |
| `_rebuild.bat` | Quick rebuild, no prompts |

---

## Project Structure (Installer)

```
installer/
├── installer_webview.spec   ← PyInstaller spec (unified, this is the one used)
├── build.py                ← Cross-platform build script
├── platforms/
│   ├── macos-dmg.spec
│   └── linux-appimage.spec
├── core/                   ← Business logic (installed with app)
│   ├── hardware.py         ← GPU/CPU detection
│   ├── models.py           ← Model tier recommender
│   ├── deps.py             ← pip dependency resolver
│   ├── writer.py           ← Config file generator
│   ├── shortcuts.py         ← Desktop/Start Menu shortcut creator
│   └── uninstaller.py      ← Uninstaller business logic
├── data/
│   └── tiers.yaml          ← Model tier definitions
├── templates/
│   └── config.yaml.j2      ← Config file Jinja2 template
└── dist/                   ← Build output
    └── MokaAI-Setup/
        └── MokaAI-Setup.exe
```

```
installer_wizard/           ← Wizard UI (PyWebView)
├── main.py                 ← Entry point (webview.create_window)
├── api.py                  ← JS API bridge (progress, install, shortcuts)
├── index.html              ← Step-based wizard UI
├── styles.css              ← Warm-palette CSS
└── wizard.js               ← Orb animation + step transitions

uninstall_moka.py           ← Standalone uninstaller (no deps beyond stdlib+pywin32)
uninstall_moka.spec         ← PyInstaller spec for uninstaller
```

---

## How the Installer Works

1. **Welcome** — user picks install path
2. **Hardware Scan** — `installer/core/hardware.py` detects GPU/RAM via `nvidia-smi`, WMI, `rocm-smi`, or `system_profiler`
3. **Model Select** — `installer/core/models.py` reads `tiers.yaml` and recommends the right model tier for detected VRAM
4. **Install** — `installer/core/deps.py` calls `pip install` for required packages; `installer/core/writer.py` renders `config.yaml.j2` → `config/config.yaml`
5. **Shortcuts** — `installer/core/shortcuts.py` creates `.lnk` files on Windows via PowerShell
6. **Registry** — `installer/core/writer.py` writes `HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Uninstall\MokaAI` so the app appears in Add/Remove Programs

---

## Uninstall

- **Start Menu → Settings → Apps → Installed apps → Moka AI → Uninstall**
- Or run `uninstall_moka.exe` from the install directory
- Or run `uninstall_moka.py` directly (requires only Python stdlib + pywin32)

Uninstaller removes:
- All installed files in `C:\Users\<you>\AppData\Local\MokaAI`
- Desktop shortcut
- Start Menu shortcut
- Windows registry entry

---

## Troubleshooting

### "WebView2 runtime not found"

Install it manually: https://developer.microsoft.com/en-us/microsoft-edge/webview2/

### Build fails with "pywebview not found"

Install all build dependencies:

```powershell
pip install pyinstaller webview pywin32 jinja2 pyyaml psutil
```

### Installer hangs on hardware scan

Run with admin privileges, or check that GPU drivers are up-to-date.

### Config files not written

Make sure the install path is writable (not `C:\Program Files` without admin rights).

---

## Architecture

```
MokaAI-Setup.exe
├── _internal/
│   ├── python.exe              ← Bundled Python runtime
│   ├── installer_wizard/       ← UI layer (HTML/CSS/JS + PyWebView)
│   ├── installer/core/         ← Business logic (hardware, deps, config, shortcuts)
│   ├── installer/data/         ← tiers.yaml (model definitions)
│   ├── installer/templates/   ← config.yaml.j2 (config template)
│   ├── webview/                ← PyWebView runtime (uses OS WebView2)
│   └── [Python stdlib + deps]  ← jinja2, yaml, psutil, etc.
```

The installer does NOT bundle AI models — they are downloaded on first use by the main app.