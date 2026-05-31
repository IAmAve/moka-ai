# -*- mode: python ; coding: utf-8 -*-
"""
Moka AI Installer — Unified Windows WebView2 PyInstaller spec.

ENTRY POINT : installer_wizard/__main__.py
BUNDLES     : installer_wizard/ (UI) + installer/core/ (logic)
              + installer/data/ (tiers) + installer/templates/ (config)
TARGET      : Windows x64 with OS-native WebView2 (no bundled Chromium)

Build (from installer/ directory):
    cd installer
    python -m PyInstaller --clean --noconfirm installer_webview.spec

    # Output: dist/MokaAI-Setup/MokaAI-Setup.exe  (one-dir bundle)

Prerequisites:
    pip install pyinstaller webview pywin32 jinja2 pyyaml psutil
"""

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_data_files

block_cipher = None

# repo root is two levels up from installer/ directory
repo_root = Path("D:/Ave/Documents/PROJECTS/moka-ai")
wizard_dir  = repo_root / "installer_wizard"
core_dir    = repo_root / "installer" / "core"
data_dir    = repo_root / "installer" / "data"
templates_dir = repo_root / "installer" / "templates"

# ── Extra data files to bundle ─────────────────────────────────────────────
# installer/core/ is a Python package — PyInstaller auto-collects the .py files.
# We explicitly add the non-Python data assets.
wizard_datas = collect_data_files("installer_wizard", include_py_files=False)
# Dirs and files needed at runtime in the install directory.
# moka_launcher.txt and moka_voice_ref.wav are in installer/data (already above).
# We add the Moka AI runtime tree from the repo.
runtime_root = repo_root  # same repo root
extra_data = wizard_datas + [
    (str(data_dir),        "installer/data"),
    (str(templates_dir),   "installer/templates"),
    # Runtime entry points
    (str(runtime_root / "main.py"),           "."),
    (str(runtime_root / "moka.py"),           "."),
    # Runtime module trees (copied flat into install dir)
    (str(runtime_root / "core"),               "core"),
    (str(runtime_root / "core_runtime"),       "core_runtime"),
    (str(runtime_root / "personality"),        "personality"),
    (str(runtime_root / "voice"),              "voice"),
    (str(runtime_root / "memory"),             "memory"),
    (str(runtime_root / "learning"),           "learning"),
    (str(runtime_root / "safety"),            "safety"),
    (str(runtime_root / "config"),             "config"),
    # Frontend (Flask serves this at runtime)
    (str(runtime_root / "frontend"),           "frontend"),
]

# ── Hidden imports ────────────────────────────────────────────────────────────
# Business-logic modules (installer/core)
hardware_mods = [
    "installer.core.hardware",
    "installer.core.models",
    "installer.core.deps",
    "installer.core.downloader",
    "installer.core.writer",
    "installer.core.shortcuts",
    "installer.core.uninstaller",
]
# Wizard UI layer
wizard_mods = [
    "installer_wizard",
    "installer_wizard.api",
    "installer_wizard.__main__",
]
# Third-party deps used by core
thirdparty_mods = [
    "jinja2",
    "jinja2.ext",
    "yaml",
    "yaml.cyaml",
    "psutil",
    "importlib.metadata",
    "winreg",
]

# ── webview DLLs (WebView2 C++/CLI assemblies from site-packages) ─────────────
# These are loaded dynamically and collect_all may not include them — add explicitly
_wv_lib_dlls = []
for _sp in [r"C:\Users\Ave\AppData\Local\Programs\Python\Python311\Lib\site-packages\webview\lib"]:
    if Path(_sp).exists():
        for _dll in Path(_sp).glob("*.dll"):
            _wv_lib_dlls.append((str(_dll), "webview/lib"))

# Collect webview package data files + binaries
webview_submodules = []
webview_datas = list(_wv_lib_dlls)  # prepend explicit DLLs
webview_binaries = []
try:
    wc = collect_all("webview")
    webview_datas += wc[0]
    webview_binaries = wc[1]
    webview_submodules = wc[2]
except Exception as e:
    print(f"[spec] collect_all webview failed: {e}")
    try:
        # Fallback: locate webview package on disk
        import site
        for sp in site.getsitepackages():
            wp = Path(sp) / "webview"
            if wp.exists() and wp.is_dir():
                import os
                for root, dirs, files in os.walk(wp):
                    for fn in files:
                        fp = Path(root) / fn
                        webview_datas.append((str(fp), "webview" + str(fp.relative_to(wp))))
                break
    except Exception as e2:
        print(f"[spec] fallback webview collection also failed: {e2}")

# Finalise datas for Analysis
datas = extra_data + webview_datas

webview_mods = webview_submodules + [
    "webview",
    "webview.cli",
    "webview.win32",
    "webview.finders",
]

hiddenimports = (
    hardware_mods
    + wizard_mods
    + webview_mods
    + thirdparty_mods
    # Phase runtime modules (needed by moka.py / main.py at startup)
    + [
        # core/
        "core.event_bus",
        "core.service_manager",
        "core.di_container",
        "core.health_monitor",
        "core.version_manager",
        "core.environment_manager",
        "core.telemetry",
        "core.logger",
        "core.config",
        "core.plugin_manager",
        # core_runtime/
        "core_runtime.desktop_runtime_manager",
        "core_runtime.engineering_workflow_orchestrator",
        "core_runtime.image_runtime_manager",
        "core_runtime.software_profile_engine",
        # personality/
        "personality.personality_engine",
        "personality.mood_engine",
        "personality.localization_service",
        # voice/
        "voice.voice_service",
        # memory/
        "memory.short_term_memory",
        "memory.long_term_memory",
        "memory.behavior_memory",
        # learning/
        "learning.hermes_learning_system",
        # safety/
        "safety.emergency_stop",
        # services bridge
        "core.services",
    ]
)

print(f"[spec] webview_datas={len(webview_datas)}, webview_binaries={len(webview_binaries)}, hiddenimports={len(hiddenimports)}")

# ── Analysis ─────────────────────────────────────────────────────────────────
a = Analysis(
    [str(wizard_dir / "__main__.py")],
    pathex=[str(repo_root)],
    binaries=webview_binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "PIL", "cv2"],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ── EXE ──────────────────────────────────────────────────────────────────────
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MokaAI-Setup",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(repo_root / "frontend" / "static" / "img" / "moka-logo.ico"),
)

# ── COLLECT (one-dir bundle) ──────────────────────────────────────────────────
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="MokaAI-Setup",
)