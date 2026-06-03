# Installer Wizard – PyWebView Stand‑alone Design

**Date:** 2026‑06‑03
**Author:** Claude (AI assistant)

---

## Overview
The goal is to replace the existing Dear PyGUI installer wizard with a lightweight, cross‑platform standalone application built on **PyWebView 4.x**. The UI will be pure web (HTML/CSS/JS) rendered inside the native WebView provided by the OS (WebView2 on Windows, WKWebView on macOS, WebKitGTK on Linux). All business‑logic remains in the existing `installer.core.*` modules; a thin `WizardAPI` bridge exposes the required operations to the front‑end.

### Primary Benefits
- **Small footprint** – No bundled Chromium; binary size remains < 5 MB added to the existing installer.
- **Cross‑platform** – Single codebase works on Windows, macOS, Linux.
- **Design fidelity** – Full CSS control for the warm sand/espresso palette and 5‑step non‑linear flow.
- **Reuse existing logic** – No need to rewrite hardware detection, model recommendation, or dependency resolution.

---

## Architecture
```
+ installer_wizard/
|   api.py            # WizardAPI + WizardState (backend bridge)
|   main.py           # PyWebView entry point, creates window
|   index.html        # UI skeleton – 5 step screens
|   styles.css        # Warm sand palette, layout, animations
|   wizard.js         # Front‑end logic, step navigation, API calls
|   __init__.py       # package marker
+ installer/core/      # Existing business logic (unchanged)
+ installer/build.py   # Updated to bundle the wizard via PyInstaller
+ installer/installer_webview.spec  # PyInstaller spec for the wizard exe
```

### Data Flow
1. **Front‑end** loads `index.html` and calls `window.pywebview.api` methods provided by `WizardAPI`.
2. **WizardAPI** updates a single `WizardState` dataclass and returns JSON snapshots to the UI.
3. UI **polls** progress during the install step (via `get_progress`).
4. Upon completion the UI triggers `create_shortcuts_and_launch` which writes shortcuts and optionally launches the main Moka AI app.

---

## UI Specification (5 Steps)
| Step | Screen | Core UI Elements | Primary API Calls |
|------|----------|-------------------|--------------------|
| **1 – Welcome** | Centered column with wordmark, version tag, orb canvas, installation path input, **Browse** button, **Get Started** CTA | `orb` (idle animation), `install‑path` textbox, `btn‑browse`, `btn‑get‑started` (disabled until path entered) | `set_install_path(path)` → validates & creates directory |
| **2 – Hardware Scan** | Animated hardware cards (CPU, GPU, VRAM, RAM, OS) with staggered fade‑in | `hw‑card` elements, `vram‑bar`, **Rescan** button, **Continue** CTA | `scan_hardware()` → returns `hw_profile` JSON |
| **3 – Model Selection** | VRAM badge, three model rows (Base, Image, Voice) each with a dropdown pre‑selected to recommended model, size pills, total size estimate | `model‑dropdown` elements, `size‑pill`, `size‑total` | `get_models(vram_gb)` → list of options, `set_models(base, image, voice)` |
| **4 – Installing** | Large progress bar, percentage, package list with status badges, toggleable log panel, status header | `install‑bar`, `progress‑pct`, `pkg‑list`, `log‑area` | `start_install()` → spawns thread, UI polls `get_progress()` |
| **5 – Complete** | Celebration orb, **Done** title, path display, three checkboxes (Desktop shortcut, Start‑menu shortcut, Launch now), **Finish Setup** CTA | `cb‑desktop`, `cb‑startmenu`, `cb‑launch`, `btn‑finish` | `create_shortcuts_and_launch(desktop, startmenu, launch)` |

### Visual Details
- **Palette** – matches Phase 11 warm sand variables (`--bg‑base: #F2EBE0`, `--accent: #C9956A`).
- **Typography** – Google Font *Figtree* for headings/body, *Cascadia Code* for monospaced values.
- **Animations** – Orb pulse (idle → thinking → speaking), hardware card stagger (120 ms), progress bar easing (0.5 s).
- **Navigation** – Step dots clickable, back/next buttons always visible; state persisted in `WizardState`.

---

## Error Handling & Edge Cases
| Situation | Detection | UI Feedback |
|-----------|-----------|-------------|
| Invalid install path | `set_install_path` returns `{valid:false}` | Inline error text (`path‑error`) & disabled **Get Started** |
| Hardware scan failure | Exception in `HardwareScan` caught, `error` field set | Red orb state, error message overlay, **Retry** button enabled |
| Model list empty (unsupported VRAM) | `get_models` returns empty options | Show “No compatible models – increase VRAM or choose manually” message |
| Install thread crashes | `WizardAPI._do_install` catches, sets `state.error` | Red orb state, detailed log entry, **Retry** button on Install screen |
| Shortcut creation fails | `create_shortcuts_and_launch` catches, returns error | Inline toast/alert on Complete screen |

All errors are logged to `state.install_log` and displayed in the collapsible log pane.

---

## Testing Strategy
1. **Unit tests** for `WizardAPI` methods (`set_install_path`, `scan_hardware`, `get_models`, `set_models`). Existing `installer_wizard/test_api.py` will be updated accordingly.
2. **Integration test** – launch `installer_wizard/main.py` with `PYWEBVIEW_DEBUG=1` and simulate UI actions via Selenium‑like headless `pywebview` test harness (already used in `tests/installer_wizard.test.js`).
3. **Cross‑platform smoke test** – run the packaged `.exe` on Windows, verify UI loads, steps flow, and shortcuts are created.
4. **Performance** – ensure hardware scan < 2 s, model list fetch < 1 s, install progress updates at ≤ 500 ms interval.

---

## Build & Packaging
- Add `installer_wizard` files to `installer/installer_webview.spec` (see plan).
- Update `installer/build.py` to expose a new **wizard** target (`python installer/build.py wizard`).
- Run `pyinstaller --clean installer_webview.spec` → produces `MokaAI‑Setup.exe`.
- Ensure `pywebview` is listed in `INSTALLER_PACKAGES` (replace `dearpygui`).

---

## Acceptance Criteria (Checklist)
- [ ] PyWebView app launches on all supported OSes without external browser dependencies.
- [ ] All 5 steps accessible via step dots and Back/Next buttons.
- [ ] Hardware scan auto‑triggers and populates cards with staggered animation.
- [ ] Model dropdowns show only compatible models for detected VRAM, pre‑selected to recommended.
- [ ] Install progress streams live package status and logs.
- [ ] Finish screen creates Desktop + Start‑Menu shortcuts (Windows) and optionally launches Moka AI.
- [ ] Warm sand/espresso palette applied throughout.
- [ ] No Chromium bundle; final installer size increase ≈ 2 MB.
- [ ] Unit & integration tests pass (`pytest -q` reports all green).

---

*End of design specification.*
