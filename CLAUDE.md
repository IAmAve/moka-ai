# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Moka AI is a local AI voice companion with adaptive learning. This is a **multi-branch monorepo** — the current branch (`phase-9-workflow-wizard`) contains only the installer. The full product runtime spans multiple branches.

### Branches

| Branch | Contents |
|--------|----------|
| `main` | Core library modules only (HealthMonitor, TaskQueue, WorkerManager, ServiceManager, DI, EventBus, Logger + `personality/voice/memory/safety/learning/` + tests). No app entry point. |
| `phase-8-desktop-runtime` | `main` + `core_runtime/` desktop software detection, profile engine, runtime scanners |
| `phase-9-workflow` | **Full production app**: `main` + `core_runtime/` + `frontend/` + `installer/` + `installer_wizard/` + Flask/SocketIO backend + `moka.py` bootstrap. Everything in one branch. |
| `phase-9-workflow-wizard` | **Current branch** — installer only. Stripped to `installer/core/`, `installer_wizard/`, and built `dist/MokaAI-Setup/`. Runtime source not present. |
| `worktree-phase-8-desktop-runtime` | Worktree of phase-8 for parallel work |

The fully functional Moka AI application is on `phase-9-workflow`. Switch to it for runtime development.

## Dev Commands (Current Branch — Installer)

**Run the installer in dev mode:**
```powershell
python installer_wizard/main.py
```

**Build the installer (from installer/ directory):**
```powershell
cd installer
python build.py
```
Output: `dist/MokaAI-Setup/MokaAI-Setup.exe`

**Install dev dependencies:**
```powershell
pip install -e .
```

---

## Full Application Architecture (phase-9-workflow)

### Entry Points

- `moka.py` → `MokaAI` in `main.py` → Flask/SocketIO backend → frontend
- The installer writes `moka.py` to the install directory, which launches `MokaAI.initialize()`

### MokaAI Startup Sequence (`main.py`)

```
1. EnvironmentManager.validate()         — checks Python, disk, env vars
2. Config.load() + Logger.initialize()   — loads config.yaml, opens log
3. DIContainer.register()                — registers event_bus, telemetry singletons
4. PluginManager.initialize()            — loads explorer/terminal/comfyui plugins
5. DesktopRuntimeManager.run()           — scans software (10 apps) + runtime processes + profile categories
6. ServiceManager.register()             — health_monitor, version_manager, engineering_workflow, image_runtime
7. _validate_startup()                    — 10 null-check validations
8. ServiceManager.start_service()        — starts all registered services
9. HealthMonitor.start()                 — background health checking
10. event_bus.publish("moka:startup_validated")
```

### Event Bus (`core/event_bus.py`)

Key system events: `moka:startup_validated`, `moka:services_started`, `moka:shutdown_complete`, `workflow.stage.completed`. All components communicate via publish/subscribe.

### Engineering Workflow Orchestrator (`core_runtime/engineering_workflow_orchestrator.py`)

Human-in-the-loop pipeline: `analyze → create → install → code → test → debug → approval (temp→test→live)`. Uses `SandboxManager` + `ApprovalGate` + `DebugLoop` + `RollbackManager`. Two-gate promotion model: sandbox must pass approval in both temp→test and test→live before running in live.

## Personality & Behavior

### Personality Profile (`personality/personality_engine.py`)

Role: **Female mentor companion, Tagalog-first**. Traits: Disciplined, Teacher, Structured, Direct, Supportive, Professional. Default communication: Formal. Mood shifts communication style dynamically.

### Mood States (`personality/mood_engine.py` and `MoodState`)

| Mood | Effect |
|------|--------|
| ENCOURAGING | Prefix: "Galing mo!" |
| STRICT | Suffix: " gawain mo na." |
| SUPPORTIVE | Suffix: " Andidto lang ako." |
| NEUTRAL | Base phrase, no prefix/suffix |
| FOCUSED | Direct, minimum modulation |
| CONCERNED | Empathetic phrasing |
| SATISFIED | Positive confirmation |

Mood is managed by `MoodEngine` and set via `PersonalityEngine.set_mood()`.

### Adaptive Learning (`learning/hermes_learning_system.py`)

Pipeline: `observe → draft → test → learn_and_adapt → skill created (inactive) → requires user approval before activation`. **Never auto-executes learned behaviors.**

## The Orb — Visual State Engine (`frontend/static/js/orb.js`)

Canvas-based animated orb, 5 states driven by `orb_state` Socket.IO events from the backend:

| State | Color | Pulse | Meaning |
|-------|-------|-------|---------|
| idle | `#D9CFC4` cream | 3s slow | Ready at rest |
| listening | `#E8A96B` amber | 1s fast | Mic active |
| thinking | `#4A2C17` dark brown | 2s | Generating response |
| speaking | `#F0D9A0` gold | 0.8s rapid | TTS playing, speech rings expand |
| error | `#7A4A3A` muted red | 4s slow | Problem state |

Transitions: `listening` → particle burst on enter. `speaking` → continuous expanding ring animation.

## Frontend Socket.IO Events (`frontend/static/js/app.js`)

Events received from backend and their UI effects:
- `message` → chat messages
- `voice_transcript` → voice panel transcript lines
- `orb_state` → orb canvas `setState()` call
- `memory_update` → memory panel (short_term + long_term)
- `skill_update` → skills grid panel
- `task_update` → tasks panel list
- `resource_update` → GPU/RAM color-coded bars
- `learning_update` → learning dashboard panel
- `history_events` → history filter pills

## Installer Architecture (current branch)

### Two UI Layers

- **`installer/wizard.py`** — Dear PyGUI wizard (legacy)
- **`installer_wizard/`** — PyWebView2 wizard (current): `main.py` creates a frameless `webview.create_window` with `index.html` + `wizard.js` + `api.py` Python bridge

### Business Logic Modules (`installer/core/`, no UI dependencies)

- **`hardware.py`** — `HardwareScan`. Detection order: WMI `Win32_VideoController` (all vendors) → nvidia-smi → PyTorch CUDA. Hard-coded VRAM corrections for AMD RX 580/570 under-reporting.
- **`models.py`** — `ModelRecommender` reads `tiers.yaml` (4/8/12/16/24 GB tiers)
- **`deps.py`** — `DepResolver` computes pip packages, runs `pip install` subprocess
- **`downloader.py`** — `ModelDownloader`: Ollama (`ollama pull`) + HuggingFace (`snapshot_download`)
- **`writer.py`** — `ConfigWriter` + Jinja2 templates → `config.yaml` / credentials in install dir
- **`shortcuts.py`** — `Shortcuts` creates Windows `.lnk` shortcuts
- **`uninstaller.py`** — `UninstallerCore` removes install dir + registry entries

### Build System

- `installer/build.py` — cross-platform PyInstaller entry
- `installer/installer_webview.spec` — Windows WebView2 spec (uses OS WebView2, no bundled Chromium)
- `installer/platforms/macos-dmg.spec` / `linux-appimage.spec` — other platforms
- Output: `dist/MokaAI-Setup/MokaAI-Setup.exe` (one-dir bundle with `_internal/` + `webview/` runtime)

### Model Download Flow

1. `pip install` for Python packages (torch, transformers, diffusers, etc.)
2. Ollama pulled via streaming `ollama pull <model>` (logs streamed in real-time to UI)
3. HuggingFace models via `huggingface_hub snapshot_download` with resume and cache

Failures are logged with warnings — models re-download on first launch.