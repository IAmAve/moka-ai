# Cross-Platform Installer Build Guide

## Current Status

- **Windows** ✅ `.exe` in `dist/MokaAI-Setup.exe` (one-file, ~266 MB)
- **macOS** 🏗️ spec ready — build on macOS machine
- **Linux** 🏗️ spec ready — build on Linux machine

---

## Windows Build

```bash
# From repo root
pyinstaller --clean MokaAI-Setup.spec --noconfirm

# Output: dist/MokaAI-Setup.exe
```

Requirements:
- Python 3.10+ with `pip install pyinstaller dearpygui yaml jinja2 psutil screeninfo`
- Windows 10/11

---

## macOS Build

**Prerequisites:**

```bash
brew install pyinstaller create-dmg
pip install dearpygui yaml jinja2 psutil screeninfo
```

**Build:**

```bash
# From repo root
cd installer
python3 build.py

# Or directly:
cd installer/platforms
pyinstaller --clean macos-dmg.spec --noconfirm
# Output: installer/dist/Moka AI Installer.app
```

**Create DMG:**

```bash
create-dmg \
  --volname "Moka AI Installer" \
  --icon-size 120 \
  --window-pos 200 120 \
  --window-size 600 400 \
  --icon "Moka AI Installer" 150 180 \
  dist/MokaAI-Setup.dmg \
  "dist/Moka AI Installer.app/"
```

**Requirements:**
- macOS 10.15+ (Catalina)
- Apple Silicon or Intel

---

## Linux Build

**Prerequisites:**

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip python3-venv
pip install pyinstaller dearpygui yaml jinja2 psutil screeninfo

# AppImage tooling (for packaging into .AppImage)
wget -q "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage" \
  -O appimagetool
chmod +x appimagetool
```

**Build:**

```bash
# From repo root
cd installer
python3 build.py

# Or directly:
cd installer/platforms
pyinstaller --clean linux-appimage.spec --noconfirm
# Output: installer/dist/MokaAI-Setup/  (one-dir)
```

**Package as AppImage:**

```bash
cd installer/dist
ARCH=x86_64 ../appimagetool MokaAI-Setup MokaAI-Setup-x86_64.AppImage
```

**Requirements:**
- Ubuntu 18.04+ / Debian stable
- x86_64 or ARM64

---

## Installer Features

All platforms share the same feature set:

| Feature | Description |
|---------|-------------|
| Directory picker | Native file dialog with Browse button |
| Dark theme | Moka AI dark palette (#161B22 background, #388BFD accent) |
| Hardware scan | GPU detection via nvidia-smi, WMI, PyTorch CUDA |
| Model selection | VRAM-tiered base/image/voice model combos |
| Progress bar | Install progress with % display |
| Desktop shortcut | Platform-specific shortcut creation |
| Uninstaller | Clean removal via uninstall_moka.exe / Application folder |

---

## Architecture

```
installer/
├── wizard.py              ← Main entry (all platforms)
├── build.py               ← Cross-platform build runner
├── core/                  ← Business logic (no DPG)
│   ├── hardware.py        ← GPU/RAM detection
│   ├── models.py          ← Model recommender
│   ├── deps.py            ← Dependency resolver
│   ├── writer.py          ← Config file writer
│   └── shortcuts.py       ← Desktop/start menu shortcuts
├── platforms/
│   ├── windows-onefile.spec  ← PyInstaller spec for Windows
│   ├── macos-dmg.spec        ← PyInstaller spec for macOS .app
│   └── linux-appimage.spec   ← PyInstaller spec for Linux
└── templates/
    └── config.yaml.j2
```

---

## Adding Hardware Detection for a New GPU

Edit `installer/core/hardware.py` and add a new method:

```python
def _my_gpu_smi(self) -> Optional[dict]:
    """Detect MyBrand GPU."""
    try:
        r = subprocess.run(
            ["mygpu-smi", "--query=name,vram", "--format=csv"],
            capture_output=True, text=True, timeout=15,
        )
        if r.returncode != 0:
            return None
        parts = r.stdout.strip().split(",")
        return {"name": parts[0], "vram_gb": round(float(parts[1]) / 1024, 2)}
    except Exception:
        return None
```

Then add it to `_detect_gpu()`:

```python
info = self._my_gpu_smi()
if info:
    return info["name"], info["vram_gb"], None
```