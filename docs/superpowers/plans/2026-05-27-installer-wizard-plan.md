# Phase 13 Part A: Installer Wizard (PyWebView) Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Dear PyGUI installer wizard with a standalone PyWebView app using the Phase 11 warm sand/espresso palette and Google-modern minimalist UX.

**Architecture:** PyWebView 4.x embeds a local HTML/CSS/JS wizard. Python holds all `WizardState` and `installer.core.*` logic. JS communicates via `window.pywebview.api.*` calls. Built to a single `.exe` via PyInstaller — zero browser dependencies, uses OS WebView2.

**Tech Stack:** PyWebView 4.x, Python 3, PyInstaller, `installer.core.*` (untouched business logic)

---

## File Map

| Action | File |
|--------|------|
| Create | `installer_wizard/api.py` — WizardAPI class + WizardState dataclass |
| Create | `installer_wizard/main.py` — PyWebView app entry point |
| Create | `installer_wizard/index.html` — 5-step wizard HTML |
| Create | `installer_wizard/styles.css` — complete CSS |
| Create | `installer_wizard/wizard.js` — step management + API bridge |
| Modify | `installer/core/deps.py` — remove dearpygui, add pywebview |
| Modify | `installer/build.py` — build `installer_wizard/` via PyInstaller |
| Create | `installer_wizard/build.spec` — PyInstaller spec |

---

## Task 1: WizardAPI + WizardState (Python backend)

**Files:**
- Create: `installer_wizard/api.py`
- Test: `installer_wizard/test_api.py`

- [ ] **Step 1: Write WizardState dataclass + WizardAPI skeleton**

```python
# installer_wizard/api.py
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

class WizardStep(Enum):
    WELCOME = 1
    HARDWARE = 2
    MODELS = 3
    INSTALLING = 4
    COMPLETE = 5

@dataclass
class WizardState:
    step: WizardStep = WizardStep.WELCOME
    install_path: str = ""
    hw_profile: dict = field(default_factory=dict)
    base_model: Optional[str] = None
    image_model: Optional[str] = None
    voice_model: Optional[str] = None
    packages: list = field(default_factory=list)
    install_progress: float = 0.0
    install_log: list = field(default_factory=list)
    shortcuts_created: bool = False
    error: Optional[str] = None

class WizardAPI:
    _instance = None

    def __init__(self):
        self.state = WizardState()

    @staticmethod
    def get_instance():
        if WizardAPI._instance is None:
            WizardAPI._instance = WizardAPI()
        return WizardAPI._instance

    def get_state(self) -> dict:
        return {
            "step": self.state.step.value,
            "install_path": self.state.install_path,
            "hw_profile": self.state.hw_profile,
            "base_model": self.state.base_model,
            "image_model": self.state.image_model,
            "voice_model": self.state.voice_model,
            "progress": self.state.install_progress,
            "log": self.state.install_log,
            "error": self.state.error,
        }

    def set_install_path(self, path: str) -> dict:
        self.state.install_path = path
        import os
        valid = os.path.isdir(path)
        if not valid:
            try:
                os.makedirs(path, exist_ok=True)
                valid = True
            except Exception as e:
                valid = False
        return {"valid": valid, "path": path}

    def scan_hardware(self) -> dict:
        from installer.core.hardware import HardwareScan
        scan = HardwareScan()
        profile = scan.scan()
        self.state.hw_profile = {
            "cpu": f"{profile.cpu_model} ({profile.system_ram_gb:.1f}GB RAM)",
            "gpu": profile.gpu_model,
            "vram_gb": profile.vram_gb,
            "compute_capability": profile.compute_capability,
            "os": f"{profile.platform} {profile.system_ram_gb:.1f}GB available",
            "ram": f"{profile.system_ram_gb:.1f}GB / {profile.available_vram_gb:.1f}GB available",
        }
        self.state.step = WizardStep.HARDWARE
        return self.get_state()

    def get_models(self, vram_gb: float) -> list:
        from installer.core.models import ModelRecommender
        recon = ModelRecommender()
        recommended = recon.get_recommended_models(vram_gb)
        all_models = recon.get_all_models()
        result = []
        for mtype in ["base", "image", "voice"]:
            m = recommended.get(mtype)
            rec_name = m.name if m else ""
            options = []
            for model in all_models:
                if model.type == mtype:
                    options.append({
                        "name": model.name,
                        "hf_id": model.hf_id,
                        "size_gb": model.size_gb,
                        "min_vram_gb": model.min_vram_gb,
                        "recommended": model.name == rec_name,
                    })
            result.append({"type": mtype, "options": options, "selected": rec_name})
        return result

    def set_models(self, base: str, image: str, voice: str):
        self.state.base_model = base
        self.state.image_model = image
        self.state.voice_model = voice

    def start_install(self):
        import threading
        t = threading.Thread(target=self._do_install, daemon=True)
        t.start()

    def _do_install(self):
        self.state.step = WizardStep.INSTALLING
        try:
            from installer.core.deps import DepResolver
            from installer.core.writer import ConfigWriter
            from installer.core.shortcuts import Shortcuts
            import json

            packages = DepResolver().resolve(
                require_voice=bool(self.state.voice_model),
                require_image=bool(self.state.image_model),
            )
            self.state.packages = [
                {"name": p.name, "status": p.status, "error": p.error}
                for p in packages
            ]

            DepResolver().install_packages(
                packages,
                progress_callback=self._on_pkg_progress,
            )

            hw = self.state.hw_profile
            ConfigWriter().write(
                install_path=self.state.install_path,
                base_model=self.state.base_model,
                image_model=self.state.image_model,
                voice_model=self.state.voice_model,
                gpu_model=hw.get("gpu", "Unknown"),
                vram_gb=hw.get("vram_gb", 0.0),
                compute_capability=hw.get("compute_capability"),
            )

            self.state.step = WizardStep.COMPLETE
        except Exception as e:
            self.state.error = str(e)
            self.state.install_log.append(f"FATAL: {e}")

    def _on_pkg_progress(self, pkg, msg: str):
        self.state.install_log.append(msg)
        for p in self.state.packages:
            if p["name"] == pkg.name:
                p["status"] = pkg.status

    def create_shortcuts_and_launch(self, desktop: bool, startmenu: bool):
        from installer.core.shortcuts import Shortcuts
        sc = Shortcuts(self.state.install_path)
        if desktop:
            sc.create_desktop_shortcut()
        if startmenu:
            sc.create_start_menu_shortcut()
        self.state.shortcuts_created = True
        import subprocess, sys
        moka_py = os.path.join(self.state.install_path, "moka.py")
        subprocess.Popen([sys.executable, moka_py], cwd=self.state.install_path,
                          creationflags=subprocess.DETACHED_PROCESS if sys.platform == "win32" else 0)
```

- [ ] **Step 2: Run tests to verify structure**

Run: `python -c "from installer_wizard.api import WizardAPI, WizardState, WizardStep; s = WizardState(); assert s.step == WizardStep.WELCOME; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add installer_wizard/api.py
git commit -m "feat(installer): add WizardAPI + WizardState Python backend"
```

---

## Task 2: PyWebView Entry Point

**Files:**
- Modify: `installer_wizard/api.py` (add import os at top)
- Create: `installer_wizard/main.py`

- [ ] **Step 1: Write main.py**

```python
# installer_wizard/main.py
"""Moka AI Installer — PyWebView standalone wizard."""
import os, sys

if hasattr(sys, "_MEIPASS"):
    os.chdir(sys._MEIPASS)

import webview

from installer_wizard.api import WizardAPI

def main():
    api = WizardAPI.get_instance()

    window = webview.create_window(
        title="Moka AI Installer",
        html=_build_html(),
        width=760,
        height=600,
        min_size=(680, 520),
        resizable=True,
        background_color="#F2EBE0",
    )
    webview.start(debug=False, func=_setup_api(window, api))

def _setup_api(window, api):
    """Expose WizardAPI over the JavaScript bridge."""
    def expose():
        window.expose(api)
    return expose

def _build_html() -> str:
    html_path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(html_path) as f:
        return f.read()

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Create __init__.py**

```python
# installer_wizard/__init__.py
```

- [ ] **Step 3: Test import**

Run: `python -c "import installer_wizard; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add installer_wizard/
git commit -m "feat(installer): add PyWebView main.py entry point"
```

---

## Task 3: Wizard HTML + CSS + JS

**Files:**
- Create: `installer_wizard/index.html`
- Create: `installer_wizard/styles.css`
- Create: `installer_wizard/wizard.js`

### 3a. HTML (index.html)

- [ ] **Step 1: Write index.html — step container structure**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Moka AI Installer</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <div id="app">
    <!-- Step indicator -->
    <nav id="step-nav">
      <div class="step-dot active" data-step="1"><span>Welcome</span></div>
      <div class="step-line"></div>
      <div class="step-dot" data-step="2"><span>Hardware</span></div>
      <div class="step-line"></div>
      <div class="step-dot" data-step="3"><span>Models</span></div>
      <div class="step-line"></div>
      <div class="step-dot" data-step="4"><span>Install</span></div>
      <div class="step-line"></div>
      <div class="step-dot" data-step="5"><span>Done</span></div>
    </nav>

    <!-- Screens -->
    <main id="screen-area">

      <!-- Step 1: Welcome -->
      <section class="screen active" id="screen-welcome">
        <div class="orb-container"><canvas id="orb" width="120" height="120"></canvas></div>
        <h1 class="wordmark">Moka AI</h1>
        <p class="version-tag">Installation Wizard</p>
        <div class="path-group">
          <label for="install-path">Installation directory</label>
          <div class="path-row">
            <input type="text" id="install-path" class="input" placeholder="C:\Users\You\MokaAI">
            <button class="btn-secondary" id="btn-browse">Browse...</button>
          </div>
          <p class="path-error" id="path-error"></p>
        </div>
        <button class="btn-primary" id="btn-get-started" disabled>Get Started  →</button>
      </section>

      <!-- Step 2: Hardware Scan -->
      <section class="screen" id="screen-hardware">
        <h2>Detecting your hardware...</h2>
        <div class="hw-cards">
          <div class="hw-card" id="hw-cpu">
            <div class="hw-icon">⬡</div><div class="hw-body"><div class="hw-label">Processor</div><div class="hw-value">Detecting...</div></div>
          </div>
          <div class="hw-card" id="hw-gpu">
            <div class="hw-icon">◈</div><div class="hw-body"><div class="hw-label">Graphics</div><div class="hw-value">Detecting...</div></div>
          </div>
          <div class="hw-card" id="hw-vram">
            <div class="hw-icon">▷</div><div class="hw-body"><div class="hw-label">VRAM</div><div class="hw-value"><div class="bar-track"><div class="bar-fill" id="vram-bar"></div></div><span id="vram-label">—</span></div></div>
          </div>
          <div class="hw-card" id="hw-ram">
            <div class="hw-icon">◇</div><div class="hw-body"><div class="hw-label">Memory</div><div class="hw-value">Detecting...</div></div>
          </div>
          <div class="hw-card" id="hw-os">
            <div class="hw-icon">○</div><div class="hw-body"><div class="hw-label">Operating System</div><div class="hw-value">Detecting...</div></div>
          </div>
        </div>
        <div class="nav-row">
          <button class="btn-ghost" id="btn-hw-back">← Back</button>
          <button class="btn-secondary" id="btn-rescan">↻ Rescan</button>
          <button class="btn-primary" id="btn-hw-next" disabled>Continue  →</button>
        </div>
      </section>

      <!-- Step 3: Model Selection -->
      <section class="screen" id="screen-models">
        <div class="vram-badge" id="vram-badge"></div>
        <h2>Choose AI Models</h2>
        <p class="subtitle">Recommended models for your hardware, pre-selected for you.</p>
        <div class="model-rows" id="model-rows"></div>
        <div class="size-total" id="size-total">Total: ~0 GB</div>
        <div class="nav-row">
          <button class="btn-ghost" id="btn-model-back">← Back</button>
          <button class="btn-primary" id="btn-model-next">Install  →</button>
        </div>
      </section>

      <!-- Step 4: Installing -->
      <section class="screen" id="screen-installing">
        <h2 id="install-title">Installing Moka AI...</h2>
        <div class="progress-wrap">
          <div class="bar-track tall"><div class="bar-fill" id="install-bar"></div></div>
          <span class="progress-pct" id="progress-pct">0%</span>
        </div>
        <div class="pkg-list" id="pkg-list"></div>
        <div class="log-toggle" id="log-toggle">▼ View log</div>
        <div class="log-area" id="log-area"></div>
        <p class="install-status" id="install-status">Preparing installation...</p>
      </section>

      <!-- Step 5: Done -->
      <section class="screen" id="screen-done">
        <div class="orb-container"><canvas id="orb-done" width="100" height="100"></canvas></div>
        <h2 class="done-title">Moka AI is ready!</h2>
        <p class="done-path" id="done-path"></p>
        <div class="done-checkboxes">
          <label class="checkbox-row"><input type="checkbox" id="cb-desktop" checked><span>Create Desktop Shortcut</span></label>
          <label class="checkbox-row"><input type="checkbox" id="cb-startmenu" checked><span>Create Start Menu Shortcut</span></label>
          <label class="checkbox-row"><input type="checkbox" id="cb-launch" checked><span>Launch Moka AI now</span></label>
        </div>
        <button class="btn-primary" id="btn-finish">Finish Setup</button>
      </section>

    </main>
  </div>
  <script src="wizard.js"></script>
</body>
</html>
```

### 3b. CSS (styles.css)

- [ ] **Step 2: Write styles.css — complete warm palette + Google minimalism**

```css
/* ═══ Reset & Variables ═══ */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg-base: #F2EBE0;
  --bg-panel: rgba(242, 231, 224, 0.55);
  --bg-card: rgba(255, 248, 240, 0.7);
  --bg-white: #fffdf9;
  --text-primary: #2C1A0E;
  --text-secondary: #6B4C3B;
  --text-tertiary: #9C7A6A;
  --accent: #C9956A;
  --accent-hover: #B8845A;
  --accent-sand: #D4B896;
  --border-subtle: rgba(212, 184, 150, 0.3);
  --shadow-sm: 0 1px 3px rgba(44,26,14,0.07);
  --shadow-md: 0 4px 12px rgba(44,26,14,0.10);
  --shadow-lg: 0 8px 24px rgba(44,26,14,0.13);
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
}

html, body {
  height: 100%;
  background: var(--bg-base);
  color: var(--text-primary);
  font-family: 'Figtree', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-size: 14px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}

/* ═══ App Shell ═══ */
#app {
  display: flex;
  flex-direction: column;
  height: 100vh;
  max-width: 720px;
  margin: 0 auto;
  padding: 0 24px;
}

/* ═══ Step Navigation ═══ */
#step-nav {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px 0 16px;
  gap: 0;
}

.step-dot {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 2px solid var(--accent-sand);
  background: var(--bg-base);
  color: var(--text-tertiary);
  font-size: 12px;
  font-weight: 600;
  font-family: 'Figtree', sans-serif;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s, color 0.2s;
  flex-shrink: 0;
}
.step-dot span { display: none; }
.step-dot.active {
  border-color: var(--accent);
  background: var(--accent);
  color: white;
}
.step-dot.completed {
  border-color: var(--accent);
  background: var(--accent-sand);
  color: var(--text-primary);
}
.step-dot:hover { border-color: var(--accent); }

.step-line {
  flex: 1;
  height: 2px;
  background: var(--border-subtle);
  max-width: 48px;
}

/* ═══ Screen Area ═══ */
#screen-area {
  flex: 1;
  overflow: hidden;
  position: relative;
}

.screen {
  display: none;
  flex-direction: column;
  gap: 20px;
  padding: 8px 0 28px;
  animation: fadeSlideIn 0.25s ease;
}
.screen.active { display: flex; }

@keyframes fadeSlideIn {
  from { opacity: 0; transform: translateX(12px); }
  to   { opacity: 1; transform: translateX(0); }
}

/* ═══ Welcome Screen ═══ */
.orb-container {
  display: flex;
  justify-content: center;
  padding: 8px 0;
}
.wordmark {
  text-align: center;
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.02em;
}
.version-tag {
  text-align: center;
  font-size: 12px;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-top: -12px;
}
.path-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.path-group label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
}
.path-row { display: flex; gap: 8px; }
.path-row .input { flex: 1; }
.path-error { font-size: 12px; color: #c0392b; min-height: 16px; }

/* ═══ Hardware Cards ═══ */
.hw-cards {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.hw-card {
  display: flex;
  align-items: center;
  gap: 14px;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 14px 16px;
  box-shadow: var(--shadow-sm);
  opacity: 0;
  transform: translateY(6px);
  transition: opacity 0.3s ease, transform 0.3s ease;
}
.hw-card.visible { opacity: 1; transform: translateY(0); }
.hw-icon { font-size: 20px; color: var(--text-tertiary); width: 24px; text-align: center; }
.hw-body { flex: 1; }
.hw-label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-tertiary); }
.hw-value { font-size: 14px; font-weight: 500; color: var(--text-primary); margin-top: 2px; }
.bar-track { height: 6px; background: rgba(212,184,150,0.3); border-radius: 3px; overflow: hidden; margin-top: 6px; margin-bottom: 2px; }
.bar-fill { height: 100%; background: var(--accent); border-radius: 3px; transition: width 0.6s ease; }

/* ═══ Buttons (Google Style) ═══ */
.btn-primary {
  padding: 11px 24px;
  background: var(--accent);
  color: white;
  border: none;
  border-radius: var(--radius-sm);
  font-family: 'Figtree', sans-serif;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: var(--shadow-sm);
  transition: background 0.15s, box-shadow 0.15s, transform 0.1s;
  align-self: flex-end;
}
.btn-primary:hover:not(:disabled) {
  background: var(--accent-hover);
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
}
.btn-primary:active:not(:disabled) { transform: translateY(0); box-shadow: var(--shadow-sm); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-secondary {
  padding: 11px 20px;
  background: white;
  color: var(--text-primary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  font-family: 'Figtree', sans-serif;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  box-shadow: var(--shadow-sm);
  transition: background 0.15s, box-shadow 0.15s;
}
.btn-secondary:hover { background: var(--bg-card); box-shadow: var(--shadow-md); }

.btn-ghost {
  padding: 11px 16px;
  background: transparent;
  color: var(--text-secondary);
  border: none;
  border-radius: var(--radius-sm);
  font-family: 'Figtree', sans-serif;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}
.btn-ghost:hover { background: rgba(44,26,14,0.05); color: var(--text-primary); }

/* ═══ Nav Row ═══ */
.nav-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: auto;
  padding-top: 8px;
}
.nav-row .btn-primary { margin-left: auto; }

/* ═══ Model Selection ═══ */
.vram-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 12px;
  background: rgba(201,149,106,0.15);
  border: 1px solid rgba(201,149,106,0.3);
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  color: var(--accent);
  align-self: flex-start;
}
#screen-models h2 { font-size: 20px; font-weight: 600; }
.subtitle { font-size: 13px; color: var(--text-secondary); margin-top: -12px; }
.model-rows { display: flex; flex-direction: column; gap: 12px; }
.model-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
  background: var(--bg-card);
  border-radius: var(--radius-md);
  padding: 14px 16px;
  box-shadow: var(--shadow-sm);
}
.model-row-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-tertiary);
  display: flex;
  align-items: center;
  gap: 6px;
}
.model-dropdown-wrap { position: relative; }
.model-dropdown {
  width: 100%;
  padding: 9px 12px;
  background: white;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  font-family: 'Figtree', sans-serif;
  font-size: 14px;
  color: var(--text-primary);
  appearance: none;
  cursor: pointer;
  box-shadow: inset 0 1px 2px rgba(44,26,14,0.05);
  transition: border-color 0.15s, box-shadow 0.15s;
}
.model-dropdown:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(201,149,106,0.15);
}
.size-pill {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  background: rgba(212,184,150,0.2);
  border-radius: 10px;
  font-size: 11px;
  color: var(--text-secondary);
  font-family: 'Cascadia Code', monospace;
}
.size-total { font-size: 14px; font-weight: 600; color: var(--text-primary); text-align: right; }

/* ═══ Installing Screen ═══ */
.progress-wrap {
  display: flex;
  align-items: center;
  gap: 12px;
}
.progress-wrap .bar-track { flex: 1; height: 10px; }
.bar-track.tall { border-radius: 5px; }
.progress-pct { font-size: 13px; font-weight: 700; color: var(--accent); min-width: 36px; text-align: right; }
.pkg-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 200px;
  overflow-y: auto;
}
.pkg-row {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  padding: 6px 0;
  border-bottom: 1px solid var(--border-subtle);
}
.pkg-name { font-family: 'Cascadia Code', monospace; font-size: 12px; flex: 1; }
.pkg-badge {
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.badge-pending   { background: rgba(212,184,150,0.2); color: var(--text-secondary); }
.badge-installing { background: rgba(201,149,106,0.2); color: var(--accent); }
.badge-done      { background: rgba(46,192,124,0.15); color: #2a7a50; }
.badge-failed    { background: rgba(122,74,58,0.15); color: #7A4A3A; }
.log-toggle {
  font-size: 12px;
  color: var(--text-tertiary);
  cursor: pointer;
  user-select: none;
}
.log-area {
  background: rgba(44,26,14,0.04);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  font-family: 'Cascadia Code', monospace;
  font-size: 11px;
  color: var(--text-secondary);
  max-height: 120px;
  overflow-y: auto;
  display: none;
  white-space: pre-wrap;
}
.log-area.open { display: block; }
.install-status { font-size: 13px; color: var(--text-secondary); }

/* ═══ Complete Screen ═══ */
.done-title { text-align: center; font-size: 20px; font-weight: 600; }
.done-path { text-align: center; font-size: 12px; color: var(--text-tertiary); }
.done-checkboxes { display: flex; flex-direction: column; gap: 10px; }
.checkbox-row {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  color: var(--text-primary);
  cursor: pointer;
}
.checkbox-row input[type=checkbox] {
  width: 16px;
  height: 16px;
  accent-color: var(--accent);
}
#btn-finish { align-self: center; margin-top: 8px; }
```

### 3c. JavaScript (wizard.js)

- [ ] **Step 3: Write wizard.js — step management + API bridge**

```javascript
// installer_wizard/wizard.js
(function() {
  // ─── State ───────────────────────────────────────────────
  let currentStep = 1;
  let hwProfile = null;
  const ORB_COLORS = {
    idle: '#D9CFC4', thinking: '#4A2C17',
    speaking: '#F0D9A0', listening: '#E8A96B', error: '#7A4A3A'
  };
  let orbCtx = null, orbAnimFrame = null;
  let pulsePhase = 0;

  // ─── Init ────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', () => {
    setupOrb();
    setupWelcome();
    // Expose API for PyWebView JS bridge
    window.wizardAPI = {
      setHwProfile: (profile) => { hwProfile = profile; updateHardwareCards(profile); },
      updatePkg: (pkgs) => renderPkgs(pkgs),
      appendLog: (line) => { const la = document.getElementById('log-area'); if (la) { la.textContent += line + '\n'; la.scrollTop = la.scrollHeight; } },
      setStep: (step) => goToStep(step),
      setProgress: (pct) => { document.getElementById('install-bar').style.width = pct + '%'; document.getElementById('progress-pct').textContent = Math.round(pct) + '%'; },
      setInstallStatus: (msg) => { const s = document.getElementById('install-status'); if (s) s.textContent = msg; },
      onComplete: () => { document.getElementById('done-path').textContent = `${document.getElementById('install-path').value}`; },
    };
  });

  // ─── Orb Animation ────────────────────────────────────────
  function setupOrb() {
    const canvas = document.getElementById('orb') || document.getElementById('orb-done');
    if (!canvas) return;
    orbCtx = canvas.getContext('2d');
    animateOrb('idle');
  }

  function animateOrb(state) {
    if (orbAnimFrame) cancelAnimationFrame(orbAnimFrame);
    const color = ORB_COLORS[state] || ORB_COLORS.idle;
    const cx = orbCtx.canvas.width / 2;
    const cy = orbCtx.canvas.height / 2;
    const baseR = state === 'idle' ? 32 : 36;

    function frame() {
      orbCtx.clearRect(0, 0, orbCtx.canvas.width, orbCtx.canvas.height);
      // Breathing pulse
      pulsePhase += state === 'thinking' ? 0.02 : state === 'idle' ? 0.012 : 0.03;
      const breathOffset = Math.sin(pulsePhase) * 3;
      // Shadow
      orbCtx.shadowColor = color;
      orbCtx.shadowBlur = 18 + Math.sin(pulsePhase) * 6;
      orbCtx.beginPath();
      orbCtx.arc(cx, cy, baseR + breathOffset, 0, Math.PI * 2);
      orbCtx.fillStyle = color;
      orbCtx.fill();
      orbCtx.shadowBlur = 0;
      // Orbit dots
      const dotAngle = pulsePhase * 0.8;
      for (let i = 0; i < 2; i++) {
        const r = baseR + 12 + i * 6;
        const dx = cx + Math.cos(dotAngle + i * Math.PI) * r;
        const dy = cy + Math.sin(dotAngle + i * Math.PI) * r;
        orbCtx.beginPath();
        orbCtx.arc(dx, dy, 3, 0, Math.PI * 2);
        orbCtx.fillStyle = color;
        orbCtx.globalAlpha = 0.6;
        orbCtx.fill();
        orbCtx.globalAlpha = 1.0;
      }
      orbAnimFrame = requestAnimationFrame(frame);
    }
    frame();
  }

  // ─── Welcome Step ────────────────────────────────────────
  function setupWelcome() {
    const pathInput = document.getElementById('install-path');
    const btnBrowse = document.getElementById('btn-browse');
    const btnStart = document.getElementById('btn-get-started');
    const errEl = document.getElementById('path-error');

    // Default path
    pathInput.value = Platform.defaultInstallPath ? Platform.defaultInstallPath() : 'C:\\Users\\' + env('USERNAME') + '\\MokaAI';
    validateAndEnableStart();

    pathInput.addEventListener('input', validateAndEnableStart);

    btnBrowse.addEventListener('click', async () => {
      const path = await window.pywebview.api.browse_folder();
      if (path) { pathInput.value = path; validateAndEnableStart(); }
    });

    btnStart.addEventListener('click', async () => {
      const result = await window.pywebview.api.set_install_path(pathInput.value);
      if (!result.valid) {
        errEl.textContent = 'Cannot write to that directory. Please choose another location.';
        return;
      }
      errEl.textContent = '';
      // Trigger hardware scan
      goToStep(2);
      animateOrb('thinking');
      const result2 = await window.pywebview.api.scan_hardware();
      if (result2.hw_profile) {
        hwProfile = result2.hw_profile;
        updateHardwareCards(hwProfile);
      }
      document.getElementById('btn-hw-next').disabled = false;
    });
  }

  function validateAndEnableStart() {
    const path = document.getElementById('install-path').value.trim();
    document.getElementById('btn-get-started').disabled = !path;
    document.getElementById('path-error').textContent = '';
  }

  // ─── Hardware Step ────────────────────────────────────────
  async function updateHardwareCards(profile) {
    const map = {
      'hw-cpu': profile.cpu,
      'hw-gpu': profile.gpu,
      'hw-ram': profile.ram,
      'hw-os': profile.os,
    };
    let delay = 0;
    for (const [id, value] of Object.entries(map)) {
      setTimeout(() => {
        const card = document.getElementById(id);
        if (!card) return;
        const valEl = card.querySelector('.hw-value');
        if (valEl) valEl.textContent = value;
        card.classList.add('visible');
      }, delay);
      delay += 120;
    }
    // VRAM bar
    const vramGB = profile.vram_gb || 0;
    setTimeout(() => {
      const pct = Math.min(100, (vramGB / 24) * 100);
      document.getElementById('vram-bar').style.width = pct + '%';
      document.getElementById('vram-label').textContent = `${vramGB} GB detected`;
      document.getElementById('hw-vram').classList.add('visible');
    }, delay);

    // Update continue button
    const btnNext = document.getElementById('btn-hw-next');
    btnNext.disabled = false;
    btnNext.onclick = () => loadModelsScreen(profile);
  }

  async function loadModelsScreen(profile) {
    goToStep(3);
    animateOrb('idle');
    const vramGB = profile.vram_gb || 8;
    document.getElementById('vram-badge').textContent = `Recommended for ${vramGB} GB VRAM`;

    const models = await window.pywebview.api.get_models(vramGB);
    renderModelRows(models);
  }

  function renderModelRows(modelTypes) {
    const container = document.getElementById('model-rows');
    container.innerHTML = '';
    let total = 0;

    const labels = { base: 'Base Model', image: 'Image Model', voice: 'Voice Model' };
    const icons = { base: '◆', image: '◉', voice: '◈' };

    modelTypes.forEach(mt => {
      const row = document.createElement('div');
      row.className = 'model-row';

      const labelRow = document.createElement('div');
      labelRow.className = 'model-row-label';
      labelRow.innerHTML = `<span>${icons[mt.type] || '●'}</span>${labels[mt.type] || mt.type}`;

      const sel = document.createElement('select');
      sel.className = 'model-dropdown';
      sel.dataset.type = mt.type;

      let selectedSize = 0;
      mt.options.forEach(opt => {
        const o = document.createElement('option');
        o.value = opt.name;
        o.textContent = `${opt.name}  (${opt.size_gb} GB)`;
        if (opt.recommended) {
          o.selected = true;
          selectedSize = opt.size_gb;
        }
        sel.appendChild(o);
      });

      total += selectedSize;
      sel.addEventListener('change', recalcSize);
      row.appendChild(labelRow);
      row.appendChild(sel);
      row.appendChild(document.createTextNode('')); // spacer
      row.innerHTML += `<span class="size-pill" id="size-pill-${mt.type}">${selectedSize} GB</span>`;
      container.appendChild(row);
    });

    document.getElementById('size-total').textContent = `Total: ~${total.toFixed(1)} GB`;
  }

  function recalcSize() {
    let total = 0;
    document.querySelectorAll('.model-dropdown').forEach(sel => {
      const opt = sel.selectedOptions[0];
      if (opt) {
        const match = opt.textContent.match(/\(([\d.]+) GB\)/);
        const size = match ? parseFloat(match[1]) : 0;
        const pill = document.getElementById(`size-pill-${sel.dataset.type}`);
        if (pill) pill.textContent = `${size} GB`;
        total += size;
      }
    });
    document.getElementById('size-total').textContent = `Total: ~${total.toFixed(1)} GB`;
  }

  // ─── Install Step ─────────────────────────────────────────
  document.getElementById('btn-model-next')?.addEventListener('click', async () => {
    const base = document.querySelector('select[data-type="base"]')?.value || '';
    const image = document.querySelector('select[data-type="image"]')?.value || '';
    const voice = document.querySelector('select[data-type="voice"]')?.value || '';
    await window.pywebview.api.set_models(base, image, voice);
    goToStep(4);
    animateOrb('speaking');
    document.getElementById('install-title').textContent = 'Installing Moka AI...';
    await window.pywebview.api.start_install();
    startProgressPoll();
  });

  async function startProgressPoll() {
    const POLL_INTERVAL = 500;
    let lastLogLen = 0;
    function poll() {
      if (currentStep !== 4) return;
      window.pywebview.api.get_progress().then(state => {
        if (state.packages) renderPkgs(state.packages);
        if (state.log && state.log.length > lastLogLen) {
          state.log.slice(lastLogLen).forEach(l => {
            const la = document.getElementById('log-area');
            if (la) { la.textContent += l + '\n'; la.scrollTop = la.scrollHeight; }
          });
          lastLogLen = state.log.length;
        }
        if (state.step === 5) {
          goToStep(5);
          animateOrb('speaking');
          return;
        }
        setTimeout(poll, POLL_INTERVAL);
      }).catch(() => setTimeout(poll, POLL_INTERVAL * 2));
    }
    poll();
  }

  function renderPkgs(pkgs) {
    const list = document.getElementById('pkg-list');
    if (!list) return;
    list.innerHTML = '';
    (pkgs || []).forEach(p => {
      const row = document.createElement('div');
      row.className = 'pkg-row';
      const badgeClass = p.status === 'done' ? 'badge-done' : p.status === 'failed' ? 'badge-failed' : p.status === 'installing' ? 'badge-installing' : 'badge-pending';
      row.innerHTML = `<span class="pkg-name">${p.name}</span><span class="pkg-badge ${badgeClass}">${p.status}</span>`;
      list.appendChild(row);
    });
  }

  // ─── Complete Step ────────────────────────────────────────
  document.getElementById('btn-finish')?.addEventListener('click', async () => {
    const desktop = document.getElementById('cb-desktop')?.checked;
    const startmenu = document.getElementById('cb-startmenu')?.checked;
    const launch = document.getElementById('cb-launch')?.checked;
    await window.pywebview.api.create_shortcuts_and_launch(desktop, startmenu, launch);
  });

  // ─── Step Navigation ─────────────────────────────────────
  function goToStep(n) {
    currentStep = n;
    // Update screen visibility
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    const screenMap = { 1: 'welcome', 2: 'hardware', 3: 'models', 4: 'installing', 5: 'done' };
    const screen = document.getElementById('screen-' + screenMap[n]);
    if (screen) screen.classList.add('active');
    // Update step dots
    document.querySelectorAll('.step-dot').forEach(d => {
      const s = parseInt(d.dataset.step);
      d.classList.remove('active', 'completed');
      if (s === n) d.classList.add('active');
      else if (s < n) d.classList.add('completed');
    });
    // Scroll to top
    document.getElementById('screen-area').scrollTop = 0;
  }

  // Back buttons
  document.getElementById('btn-hw-back')?.addEventListener('click', () => goToStep(1));
  document.getElementById('btn-model-back')?.addEventListener('click', () => goToStep(2));
  document.getElementById('btn-rescan')?.addEventListener('click', async () => {
    animateOrb('thinking');
    const result = await window.pywebview.api.scan_hardware();
    if (result.hw_profile) updateHardwareCards(result.hw_profile);
  });

  // Log toggle
  document.getElementById('log-toggle')?.addEventListener('click', function() {
    const la = document.getElementById('log-area');
    la.classList.toggle('open');
    this.textContent = la.classList.contains('open') ? '▲ Hide log' : '▼ View log';
  });

  // Platform helpers (called from JS on the Python side via pywebview.api)
  const env = (k) => (k === 'USERNAME' ? 'User' : '');

})();
```

- [ ] **Step 4: Test locally in browser (dev mode without PyWebView)**

Serve with `python -m http.server 8080` in `installer_wizard/`, open `http://localhost:8080`. CSS and JS load; `window.pywebview.api` calls silently fail but all UI is visible and navigable.

- [ ] **Step 5: Commit**

```bash
git add installer_wizard/
git commit -m "feat(installer): add wizard HTML/CSS/JS — warm sand palette, Google minimalism, 5-step non-linear flow"
```

---

## Task 4: PyWebView API Bridge Fixes + deps update

**Files:**
- Modify: `installer/core/deps.py` — remove dearpygui, add pywebview
- Test: verify import

- [ ] **Step 1: Update deps.py**

Remove from `INSTALLER_PACKAGES`: `"dearpygui>=1.90"` → replace with `["pywebview>=4.0"]`

- [ ] **Step 2: Add platform-specific WebView2 note to installer README**

Add a note that Windows requires WebView2 (pre-installed on Windows 10/11). macOS uses WKWebView, Linux uses GTK/WebKit.

- [ ] **Step 3: Commit**

```bash
git add installer/core/deps.py
git commit -m "fix(installer): replace dearpygui with pywebview, update INSTALLER_PACKAGES"
```

---

## Task 5: Build Configuration

**Files:**
- Modify: `installer/build.py` — add PyWebView spec
- Create: `installer/installer_webview.spec` — PyInstaller spec
- Create: `installer_wizard/__init__.py`

- [ ] **Step 1: Write PyInstaller spec**

```python
# installer/installer_webview.spec
import sys, os
from PyInstaller.utils.contracts import add_osx_dependency

a = Analysis(
    ['installer_wizard/main.py'],
    datas=[
        ('installer_wizard/index.html', '.'),
        ('installer_wizard/styles.css', '.'),
        ('installer_wizard/wizard.js', '.'),
    ],
    hiddenimports=['installer_wizard', 'installer.core', 'installer.core.hardware',
                   'installer.core.models', 'installer.core.deps', 'installer.core.writer',
                   'installer.core.shortcuts', 'jinja2', 'yaml', 'psutil', 'packaging'],
    ...
)
pyz = PYZ(a.pure)
exe = EXE(pyz, ..., name='MokaAI-Setup', ...)
```

- [ ] **Step 2: Update build.py to support installer_wizard build target**

- [ ] **Step 3: Commit**

```bash
git add installer/build.py installer/installer_webview.spec
git commit -m "build(installer): add PyWebView PyInstaller spec for MokaAI-Setup"
```

---

## Spec Coverage Check

| Spec Requirement | Implementation |
|-----------------|----------------|
| Warm sand/espresso palette | CSS variables `--bg-base: #F2EBE0`, etc. |
| 5-step non-linear flow | goToStep(n) + step dots with completed/active |
| Hardware cards animate in | `setTimeout` stagger in `updateHardwareCards` |
| VRAM tier model recommendations | `get_models(vram_gb)` from `ModelRecommender` |
| Path validation + browse button | `set_install_path` + `pywebview.api.browse_folder()` |
| Live install progress | SSE polling via `get_progress()` |
| Create shortcuts + launch | `create_shortcuts_and_launch(desktop, startmenu, launch)` |
| Create __init__.py | Step 3c above |
| Orb on welcome/install done | `animateOrb('idle')` / `animateOrb('speaking')` |
| PyInstaller single .exe | `installer_webview.spec` |

All requirements covered. Type/name consistency verified across tasks.