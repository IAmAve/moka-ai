# -*- mode: python ; coding: utf-8 -*-
"""
Cross-platform build script for Moka AI Installer.

Usage:
    Windows (from repo root):
        python installer/build.py

    macOS (from repo root):
        python3 installer/build.py

    Linux (from repo root):
        python3 installer/build.py

Each platform builds its own installer using the platform-specific spec.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

PLATFORM_SPECS = {
    "win32": "platforms/macos-dmg.spec",   # Windows uses spec in platforms subdir
    "darwin": "platforms/macos-dmg.spec",
    "linux": "platforms/linux-appimage.spec",
}


def get_spec_file():
    plat = sys.platform
    for key, spec in PLATFORM_SPECS.items():
        if plat.startswith(key):
            full_spec = Path(__file__).parent / spec
            if full_spec.exists():
                return str(full_spec)
    raise RuntimeError(f"No spec file found for platform {sys.platform}")


def build():
    # Must run from installer/ directory (where this script lives)
    installer_dir = Path(__file__).parent.resolve()
    repo_root = installer_dir.parent
    spec_file = get_spec_file()
    spec_name = Path(spec_file).stem

    print(f"[build] platform: {sys.platform}")
    print(f"[build] spec: {spec_file}")
    print(f"[build] repo: {repo_root}")

    os.chdir(installer_dir)

    # Clean old build artifacts
    build_dir = installer_dir / "build"
    dist_dir = installer_dir / "dist"
    for d in [build_dir, dist_dir]:
        if d.exists():
            shutil.rmtree(d)
            print(f"[build] Removed {d}")

    # Run PyInstaller
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        spec_file,
    ]
    print(f"[build] Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"[build] FAILED (exit {result.returncode})")
        return result.returncode

    # Locate output
    dist_files = list(dist_dir.glob("*"))
    print(f"[build] Output: {[str(f) for f in dist_files]}")
    print("[build] Done!")
    return 0


if __name__ == "__main__":
    sys.exit(build())