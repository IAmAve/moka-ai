# Moka AI Installer

A production-ready Windows installer for Moka AI — a local AI voice companion with adaptive learning capabilities.

## What Is Moka AI?

Moka AI is a desktop AI companion that runs entirely on your local machine. It features:

- **Voice-first interaction** with a speaking orb animation
- **Adaptive learning** that tailors behavior to your preferences over time
- **Workflow automation** for software engineering tasks (code review, debugging, refactoring)
- **Software profiling** — learns your tools, coding style, and project conventions
- **Privacy-first** — all data stays on your machine, no cloud dependency

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| OS | Windows 10/11 | Windows 11 |
| GPU | NVIDIA GPU with 4GB VRAM | NVIDIA GPU with 8GB+ VRAM |
| RAM | 8 GB | 16 GB |
| Disk | 10 GB free | 20 GB free |
| Python | — | 3.11+ (bundled in installer) |

## Installation

### Option 1: Run the Installer (Recommended)

1. Download `MokaAI-Setup.exe` from `dist/`
2. Double-click to run — no Python or dependencies needed on your machine
3. Follow the wizard:
   - **Welcome** — choose install location
   - **Hardware Scan** — automatically detects your GPU and VRAM
   - **Model Selection** — recommended AI models chosen based on your hardware tier
   - **Install** — downloads and configures selected models
   - **Finish** — shortcuts created on Desktop and Start Menu

### Option 2: Portable Uninstall

The standalone `uninstall_moka.exe` can be run at any time to remove Moka AI from your machine, including all shortcuts and registry entries.

## Architecture

The installer bundles:
- **Dear PyGUI** — native windowing UI framework
- **PyInstaller** — self-contained executable packaging
- **VRAM-tiered model selection** — 4GB / 8GB / 12GB / 16GB / 24GB GPU tiers
- **Cross-platform path handling** — `pathlib.Path` throughout for eventual macOS/Linux support

## Uninstallation

Run `uninstall_moka.exe` from the `dist/` folder, or use Windows Settings → Apps → Moka AI → Uninstall.

## Development

This repository contains the **distribution artifacts only** after the archive commit. The full source (backend, core runtime, frontend, plugins, AI models) is preserved in git history on the `phase-9-workflow` branch.

To reinstall dev dependencies after cloning:
```bash
pip install -e .
```

## License

MIT License — see `LICENSE`