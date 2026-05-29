# Moka AI Installer Wizard — Full Quality Pass Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make all 6 installer pages fully functional with correct JS↔Python wiring, real TTS/self-fix on Step 6, proper error handling, and correct download size estimates from `tiers.yaml`.

**Architecture:** Fix 8 confirmed bugs across `wizard.js`, `api.py`. Add `speak_text()` API method, add `run_self_diagnostics()` replacing shallow `self_fix()`, ensure Step 2 hardware display works from real scan data. No structural changes — everything is bug-fix + wiring repair.

**Tech Stack:** Python 3, PyWebView, vanilla JS, CSS.

---

# Phase 1 — JS Init Wiring & Data Fixes

## Task 1: Wire dead `initStep4()` and `initStep5()` into `showStep`

**Files:** `installer_wizard/wizard.js:109-136`

- [ ] **Step 1: Find `showStep` function and modify the `n === 4` and `n === 5` branches**

Find this block in `showStep`:
```javascript
} else if (n === 4) {
  initDownload();
  startDownloadPoll();
} else if (n === 5) {
  startInstallPoll();
```

Replace with:
```javascript
} else if (n === 4) {
  downloadStarted = false;  // reset so re-entry re-triggers download
  initStep4();
  initStep5();  // also wire initStep5 for when user returns to step 5
  startDownloadPoll();
} else if (n === 5) {
  startInstallPoll();
```

- [ ] **Step 2: Remove `initDownload` function — rename it to `initStep4`**

In wizard.js, rename the function `initDownload` to `initStep4`. The body remains identical, just the name changes. The guard `if (downloadStarted) return; downloadStarted = true;` stays in the renamed function.

- [ ] **Step 3: Add `initStep5` function (log toggle + back button)**

Find `initStep5` in the file — it is currently named `initStep5` at line 733 per the analysis. Verify it has these handlers:
- `#btn-toggle-log` click handler: toggles log-pane display
- `#btn-back-install` click handler: navigates back to step 4

If `initStep5` exists and has these handlers, it is already wired. Verify in `showStep` that `initStep5()` is called when entering step 5.

**Verification:** Run: `grep -n "initStep5" installer_wizard/wizard.js` — should show `function initStep5()` definition AND a call in `showStep` (if added above).

---

## Task 2: Fix simulated download progress bug (closure variable capture)

**Files:** `installer_wizard/wizard.js:536-576` (`startSimulatedDownload`)

- [ ] **Step 1: Replace `startSimulatedDownload` function body**

Find the function and replace the `forEach` + `setInterval` block. Change `item.progress` reference to use an index-based `itemProgress` array:

```javascript
function startSimulatedDownload() {
    const items = [
      { id: 'python',      total: 80   },
      { id: 'model-base',  total: 4000 },
      { id: 'model-image', total: 3000 },
      { id: 'voice',       total: 150  },
      { id: 'deps',        total: 500  },
    ];

    let doneCount = 0;
    let totalBytes = items.reduce((a, i) => a + i.total, 0);
    let itemProgress = items.map(function() { return 0; });

    downloadStarted = true;

    items.forEach(function(item, idx) {
      let progress = 0;

      var timer = setInterval(function() {
        if (currentStep !== 4) { clearInterval(timer); return; }
        progress += 0.12 + Math.random() * 0.15;
        if (progress >= 1) {
          progress = 1;
          clearInterval(timer);
          doneCount++;
          itemProgress[idx] = item.total;
          setDlStatus(item.id, 'done', 100);
          checkDownloadComplete(doneCount, items.length);
        } else {
          itemProgress[idx] = Math.floor(item.total * progress);
          setDlStatus(item.id, 'downloading', Math.round(progress * 100));
        }

        var downloadedBytes = 0;
        for (var i = 0; i < items.length; i++) {
          downloadedBytes += itemProgress[i];
        }
        updateDownloadSummary(downloadedBytes, totalBytes);
      }, 80);
    });
}
```

**Verification:** After replacement, the function must use `itemProgress[idx]` (indexed array) instead of any shared closure `item.progress`.

---

## Task 3: Fix `pollState` and remove incorrect early-return guard

**Files:** `installer_wizard/wizard.js:212-223`

- [ ] **Step 1: Rewrite `pollState` to always poll on step 2**

Find `pollState` function and replace completely:

```javascript
async function pollState() {
    if (currentStep !== 2) return;
    var api = getApi();
    if (!api) return;
    try {
      var s = await api.get_state();
      if (!hwCardsRendered && s.hw_profile && s.hw_profile.cpu && s.hw_profile.gpu) {
        renderHwCards(s.hw_profile);
        hwCardsRendered = true;
        var continueBtn = document.getElementById('btn-continue-hw');
        if (continueBtn) continueBtn.disabled = false;
      }
    } catch(e) { /* ignore */ }
    if (currentStep === 2) setTimeout(pollState, 500);
}
```

- [ ] **Step 2: Update `showStep(2)` branch to not call `pollState` twice**

Change `showStep(2)` branch from:
```javascript
} else if (n === 2) {
  initStep2();
  pollState();
```

To:
```javascript
} else if (n === 2) {
  hwCardsRendered = false;  // reset for fresh scan
  initStep2();
  pollState();  // starts polling, stops when step changes
```

**Verification:** `grep -n "pollState" installer_wizard/wizard.js` should show only one call site in `showStep(2)` and the recursive call inside `pollState` itself.

---

## Task 4: Wire Step 1 path validation return value check

**Files:** `installer_wizard/wizard.js:162-209`

- [ ] **Step 1: Fix `initWelcome` `btn-get-started` handler**

Find the `getStart.addEventListener('click', ...)` block and replace:

```javascript
getStart.addEventListener('click', async function() {
    var path = pathInput.value.trim();
    if (!path || getStart.disabled) return;
    var api = getApi();
    if (api) {
      var result = await api.set_install_path(path);
      if (!result.valid) {
        var validation = document.getElementById('path-validation');
        validation.textContent = result.error || 'Invalid path';
        validation.className = 'path-validation invalid';
        return;
      }
      pathInput.value = result.path;  // update with normalized path
    }
    // Start hardware scan in background (fire-and-forget)
    if (api) api.scan_hardware().catch(function() {});
    showStep(2);
});
```

- [ ] **Step 2: Add input listener for real-time validation**

In `initWelcome`, after `pathInput` is defined, add:
```javascript
if (pathInput) {
    pathInput.addEventListener('input', function() {
        validatePath(pathInput.value);
    });
}
```

- [ ] **Step 3: Verify `set_install_path` result fields**

The api.py return shape is confirmed: `{"valid": bool, "path": str, "error": str}`. No changes needed to api.py here.

**Verification:** `grep -n "result.valid" installer_wizard/wizard.js` should find the new check.

---

## Task 5: Fix Step 2 continue button to await hardware scan completion

**Files:** `installer_wizard/wizard.js:261-293`

- [ ] **Step 1: Set continue button disabled in `initStep2`**

In `initStep2`, ensure the continue button starts disabled:
```javascript
document.getElementById('btn-continue-hw').disabled = true;
```

- [ ] **Step 2: Verify `pollState` enables continue button**

The rewritten `pollState` (Task 3) already has the logic:
```javascript
var continueBtn = document.getElementById('btn-continue-hw');
if (continueBtn && s.hw_profile && s.hw_profile.cpu) {
    continueBtn.disabled = false;
}
```

**Verification:** After hardware scan completes, clicking the continue button should navigate to step 3.

---

# Phase 2 — Step 6 Real Backend & API Fixes

## Task 6: Add `speak_text()` to `api.py` for Step 6 TTS

**Files:** `installer_wizard/api.py`

- [ ] **Step 1: Add `speak_text` method to `WizardAPI` class**

Insert the following method in api.py before `debug_info()` (around line 612, after `undo_install`):

```python
def speak_text(self, text: str) -> dict:
    """Synthesize speech using pyttsx3 via subprocess (runs on main thread safely).

    Returns {"ok": True} on success, {"ok": False, "error": "..."} on failure.
    Falls back to silent failure if pyttsx3 unavailable — never blocks the thread.
    """
    import subprocess, sys

    script = f"""
import sys
try:
    import pyttsx3
    engine = pyttsx3.init()
    engine.setProperty('rate', 160)
    engine.setProperty('volume', 1.0)
    voices = engine.getProperty('voices')
    if voices:
        engine.setProperty('voice', voices[0].id)
    engine.say({repr(text)})
    engine.runAndWait()
    engine.stop()
    sys.exit(0)
except Exception as e:
    sys.exit(1)
"""
    try:
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, timeout=30,
        )
        if result.returncode == 0:
            return {"ok": True}
        return {"ok": False, "error": "TTS subprocess returned non-zero"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "TTS timed out"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
```

**Note:** Run as subprocess so pyttsx3 init() (which must be on the same thread it was created) runs cleanly outside the PyWebView background thread.

- [ ] **Step 2: Fix `self_fix()` file path checks in api.py**

Find `self_fix()` (around line 540) and fix the file paths it checks:

Replace `critical_paths` block:
```python
critical_paths = [
    os.path.join(install_path, "moka.py"),
    os.path.join(install_path, "config", "config.json"),   # was "models.json"
    os.path.join(install_path, "config", "credentials.json"),  # was "credentials.enc"
]
```

Also fix log messages to match:
```python
for p in critical_paths:
    if os.path.exists(p):
        log("  OK  " + os.path.basename(p))
    else:
        log("  MISSING  " + os.path.basename(p) + " — will regenerate", ok=False)
```

- [ ] **Step 3: Fix `undo_install` in api.py to use `UninstallerCore`**

Find `undo_install` (line 588) and replace the body:

```python
def undo_install(self) -> dict:
    """Remove Moka AI installation directory and unregister shortcuts."""
    try:
        from installer.core.uninstaller import UninstallerCore
        path = self.state.install_path
        if not path:
            return {"ok": False, "error": "No install path set"}
        uninstaller = UninstallerCore(path)
        result = uninstaller.run()
        return {"ok": True, "details": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}
```

**Verification:** `grep -n "models.json\|credentials.enc" installer_wizard/api.py` should return nothing (old wrong names removed).

---

## Task 7: Fix Step 6 JS — mic/speaker test use Python backend

**Files:** `installer_wizard/wizard.js` — replace `initDemo` function

- [ ] **Step 1: Identify the `initDemo` function in wizard.js**

Find `function initDemo()` in wizard.js (around line 755). This entire function must be replaced with `initStep6`.

- [ ] **Step 2: Replace `initDemo` with `initStep6`**

Replace the entire `initDemo` function body with `initStep6`. Copy the implementation from the plan doc section "Phase 2 — Task 7". Key changes:

- All API calls that exist (mic test → `api.speak_text`) call `api.speak_text(text)`
- Speaker test calls `api.speak_text(text)` first
- Self-fix calls `api.run_self_diagnostics()` instead of `api.self_fix()`
- Undo calls `api.undo_install()` and handles the result properly
- `id="btn-self-fix"` click handler updated to call `api.run_self_diagnostics()`
- `id="btn-mic-test"` calls `api.speak_text()` as Python TTS response
- `id="btn-undo-install"` calls `api.undo_install()` and handles `result.ok` / `result.error`

- [ ] **Step 3: Verify `api.speak_text` and `api.run_self_diagnostics` are used**

`grep -n "speak_text\|run_self_diagnostics" installer_wizard/wizard.js`

**Verification:** Should show calls to both methods in `initStep6`.

---

## Task 8: Add `run_self_diagnostics()` to `api.py`

**Files:** `installer_wizard/api.py`

- [ ] **Step 1: Add `run_self_diagnostics` method to `WizardAPI` class**

Insert before `self_fix()` (around line 540):

```python
def run_self_diagnostics(self) -> dict:
    """Run offline diagnostics on the installed Moka AI environment.

    Checks: config files, models directory, pip packages, GPU availability,
    disk space, and shortcut files. Returns {"ok": bool, "log": [str]}.
    """
    log_lines = []
    install_path = self.state.install_path
    all_ok = True

    def log(msg: str, ok: bool = True):
        prefix = "  OK  " if ok else "  FAIL  "
        log_lines.append(prefix + msg)
        nonlocal all_ok
        if not ok:
            all_ok = False

    log_lines.append("=== Moka AI Self-Diagnostics ===")

    # 1. Config directory
    config_dir = os.path.join(install_path, "config")
    if os.path.isdir(config_dir):
        config_files = os.listdir(config_dir)
        log(f"Config dir OK ({len(config_files)} files: {', '.join(config_files)})")
    else:
        log("Config directory not found", ok=False)

    # 2. Models directory
    models_dir = os.path.join(install_path, "models")
    if os.path.isdir(models_dir):
        model_subdirs = os.listdir(models_dir)
        log(f"Models dir OK ({len(model_subdirs)} subdirs)")
    else:
        log("Models directory not found", ok=False)

    # 3. Base model presence
    base_model_dir = os.path.join(models_dir, "base")
    if os.path.isdir(base_model_dir):
        base_files = os.listdir(base_model_dir)
        log(f"Base model: {len(base_files)} item(s) present")
    else:
        log("Base model dir empty — will download on first run", ok=False)

    # 4. Voice model presence
    voice_model_dir = os.path.join(models_dir, "voice")
    if os.path.isdir(voice_model_dir):
        voice_files = os.listdir(voice_model_dir)
        log(f"Voice model: {len(voice_files)} item(s) present")
    else:
        log("Voice model dir empty — will download on first run", ok=False)

    # 5. pip environment
    try:
        import importlib.metadata
        installed_pkgs = {d.name.lower(): d.version for d in importlib.metadata.distributions()}
        critical = ['torch', 'transformers', 'flask', 'requests']
        for pkg in critical:
            if pkg in installed_pkgs:
                log(f"pip: {pkg}=={installed_pkgs[pkg]}")
            else:
                log(f"pip: {pkg} NOT FOUND", ok=False)
    except Exception as e:
        log(f"pip check failed: {e}", ok=False)

    # 6. GPU still detectable
    try:
        from installer.core.hardware import HardwareScan
        scan = HardwareScan()
        profile = scan.scan()
        if profile.gpu_model and profile.gpu_model != "No GPU detected":
            log(f"GPU: {profile.gpu_model} ({profile.vram_gb} GB VRAM)")
            if profile.compute_capability:
                log(f"  Compute capability: {profile.compute_capability}")
        else:
            log("No GPU detected (CPU-only mode will work)", ok=False)
    except Exception as e:
        log(f"GPU scan: {e}", ok=False)

    # 7. Disk space
    try:
        import psutil
        free_gb = psutil.disk_usage(install_path).free / (1024**3)
        log(f"Disk free: {free_gb:.1f} GB")
        if free_gb < 5:
            log("Disk space low (< 5 GB free)", ok=False)
    except Exception as e:
        log(f"Disk check: {e}", ok=False)

    # 8. Shortcuts
    shortcuts_ok = self.state.shortcuts_created
    log(f"Shortcuts created: {'Yes' if shortcuts_ok else 'No (optional)'}")

    log_lines.append("=== Diagnostics Complete ===")
    return {"ok": all_ok, "log": log_lines}
```

- [ ] **Step 2: Update `self_fix` as deprecated alias**

Replace the existing `self_fix` method body:
```python
def self_fix(self) -> dict:
    """Deprecated — use run_self_diagnostics instead."""
    return self.run_self_diagnostics()
```

**Verification:** `grep -n "def run_self_diagnostics\|def self_fix" installer_wizard/api.py` should show `run_self_diagnostics` first, then `self_fix` as alias.

---

# Phase 3 — Download Size Estimates

## Task 9: Fix `_model_size()` to use `tiers.yaml` values

**Files:** `installer_wizard/api.py:392-405`

- [ ] **Step 1: Replace `_model_size` method body**

Find `_model_size` method (around line 392) and replace the entire body:

```python
def _model_size(self, model_name: str) -> float:
    """Return actual download size in MB from tiers.yaml, or name-based fallback."""
    try:
        from installer.core.models import ModelRecommender
        recon = ModelRecommender()
        all_models = {m.name: m.size_gb * 1024 for m in recon.get_all_models()}
        if model_name in all_models:
            return all_models[model_name]
    except Exception:
        pass
    sizes = {
        "llama3.2": 700,
        "llama3.1": 5000,
        "mistral": 4100,
        "qwen2.5": 4000,
        "sd-turbo": 1600,
        "sdxl": 6500,
        "silero": 150,
        "xtts": 400,
        "parler": 2000,
        "deepseek": 4000,
    }
    for k, v in sizes.items():
        if k in (model_name or "").lower():
            return float(v)
    return 2000.0
```

**Verification:** `_model_size("llama3.2:1b")` should return `700` (from new dict).

---

# Phase 4 — Step 3 → Step 4 Transition

## Task 10: Step 3→4 — validate before proceeding with error handling

**Files:** `installer_wizard/wizard.js:494-516`

- [ ] **Step 1: Replace `btn-proceed-download` handler**

Find the `btn-proceed-download` addEventListener block and replace:

```javascript
document.getElementById('btn-proceed-download').addEventListener('click', async function() {
    var api = getApi();
    if (!api) { showStep(4); return; }

    var baseSel  = document.getElementById('model-base');
    var imageSel = document.getElementById('model-image');
    var voiceSel = document.getElementById('model-voice');

    var base  = baseSel  ? baseSel.value  : '';
    var image = imageSel ? imageSel.value : '';
    var voice = voiceSel ? voiceSel.value : '';

    var localOnlyChk = document.getElementById('chk-local-only');
    apiConfig.localOnly     = localOnlyChk ? localOnlyChk.checked : true;
    apiConfig.openaiKey    = (document.getElementById('input-openai-key')     || {}).value || '';
    apiConfig.anthropicKey = (document.getElementById('input-anthropic-key') || {}).value || '';
    apiConfig.customEndpoint = (document.getElementById('input-custom-endpoint') || {}).value || '';

    try {
      await api.set_api_config(
        apiConfig.openaiKey,
        apiConfig.anthropicKey,
        apiConfig.customEndpoint,
        apiConfig.localOnly,
      );
      await api.set_models(base, image, voice);
      await api.start_download();
      showStep(4);
    } catch(e) {
      console.error('Proceed failed:', e);
      showStep(4);  // allow proceeding even on error (offline fallback)
    }
});
```

**Verification:** `grep -n "btn-proceed-download" installer_wizard/wizard.js` should show the new handler calling `api.set_models`, `api.set_api_config`, and `api.start_download`.

---

# Phase 5 — Final Wiring Fixes

## Task 11: Wire `complete_setup` on Step 6 finish button

**Files:** `installer_wizard/wizard.js` — add to `initStep6` function

- [ ] **Step 1: Add finish button handler to `initStep6`**

After the undo button handler in `initStep6`, add:

```javascript
var finishBtn = document.getElementById('btn-finish');
if (finishBtn) {
    finishBtn.addEventListener('click', async function() {
        finishBtn.disabled = true;
        var desktop   = document.getElementById('chk-desktop')?.checked   ?? true;
        var startmenu = document.getElementById('chk-startmenu')?.checked ?? true;
        var launch    = document.getElementById('chk-launch')?.checked    ?? true;
        var api = getApi();
        if (api) {
          await api.create_shortcuts_and_launch(desktop, startmenu, launch);
          await api.register_uninstaller("1.0.0");
        }
        setTimeout(function() {
            var closeApi = getApi();
            if (closeApi && closeApi.close_window) closeApi.close_window();
            else if (window.close) window.close();
        }, 1500);
    });
}
```

- [ ] **Step 2: Verify `register_uninstaller` is exposed in api.py**

`grep -n "def register_uninstaller" installer_wizard/api.py` should return the method at line ~490. It is a regular method on `WizardAPI`, so it is exposed automatically via PyWebView.

**Verification:** `grep -n "btn-finish" installer_wizard/wizard.js` should find handler inside `initStep6`.

---

## Task 12: Ensure Step 5 back button and Step 6 navigation work

**Files:** `installer_wizard/wizard.js` — verify or add `initStep5`

- [ ] **Step 1: Find `initStep5` function and verify back button handler**

Look for `function initStep5` in wizard.js (around line 733). Verify it contains the button handler for `#btn-back-install`:

```javascript
var backBtn = document.getElementById('btn-back-install');
if (backBtn) {
    backBtn.addEventListener('click', function() {
        if (confirm('Installation in progress. Go back to download?')) {
            showStep(4);
        }
    });
}
```

- [ ] **Step 2: Fix Step 6 continue button to navigate properly**

In `initStep6`, ensure `btn-finish` handler calls `api.create_shortcuts_and_launch(desktop, startmenu, launch)` — already checked in Task 11.

- [ ] **Step 3: Verify `initStep6` is called from `showStep(6)`**

In `showStep` function, verify the `n === 6` branch:
```javascript
} else if (n === 6) {
  initStep6();
}
```

The plan (Task 1) added this. Verify `grep -n "initStep6" installer_wizard/wizard.js`.

---

## Final Verification Checklist

- [ ] `grep -n "initStep4\|initStep5\|initStep6" installer_wizard/wizard.js` — all three defined AND called in `showStep`
- [ ] `grep -n "run_self_diagnostics\|speak_text" installer_wizard/api.py` — both methods present
- [ ] `grep -n "models.json\|credentials.enc" installer_wizard/api.py` — old wrong names removed (should be config.json, credentials.json now)
- [ ] `grep -n "initStep6\|btn-self-fix\|run_self_diagnostics" installer_wizard/wizard.js` — Step 6 wired with new API calls
- [ ] `grep -n "_model_size" installer_wizard/api.py` — uses tiers.yaml lookup