# Phase 8 — Desktop Runtime: Software Profile Engine & Scanners

**Date:** 2026-05-25
**Status:** Approved

---

## 1. Overview

MOKA AI detects installed desktop software at startup with **zero ongoing resource cost**. Each scanner runs once, caches results, and feeds the Software Profile Engine. The system has no background polling, no continuous threads, and degrades gracefully when tools are not found.

---

## 2. Scanners

### 2.1 SoftwareScanner

**Purpose:** Detect installed software across registry and filesystem.

**Detection Sources (in order of cost):**

| Source | Method | What it finds |
|--------|--------|---------------|
| Registry (x64) | `winreg` query `HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*` | Installed apps with versions |
| Registry (x86) | `winreg` query `HKLM\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*` | 32-bit installed apps |
| Common paths | Filesystem scan of `%ProgramFiles%`, `%ProgramFiles(x86)%`, `%LocalAppData%` | Apps installed without registry entry |
| PATH | `shutil.which()` for known CLI toolnames | CLI tools (`git`, `python`, `node`, `code`, `docker`, etc.) |

**Cached Output:** `Dict[str, Dict[name, version, path, source]]` stored in `DesktopRuntimeCache`.

**Known Software Map** (category-tagged for broad desktop awareness):

```python
KNOWN_SOFTWARE = {
    # Dev tools
    "python": {"category": "dev", "exe": "python"},
    "node": {"category": "dev", "exe": "node"},
    "git": {"category": "dev", "exe": "git"},
    "docker": {"category": "dev", "exe": "docker"},
    "vscode": {"category": "dev", "exe": "code", "path": r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"},
    "visualstudio": {"category": "dev", "exe": "devenv"},
    "pycharm": {"category": "dev", "exe": "pycharm64"},
    "intellij": {"category": "dev", "exe": "idea64"},
    "rust": {"category": "dev", "exe": "rustc"},
    "go": {"category": "dev", "exe": "go"},
    "java": {"category": "dev", "exe": "java"},
    "maven": {"category": "dev", "exe": "mvn"},
    "gradle": {"category": "dev", "exe": "gradle"},
    "cmake": {"category": "dev", "exe": "cmake"},
    # Browsers
    "chrome": {"category": "browser", "exe": "chrome", "path": r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"},
    "firefox": {"category": "browser", "exe": "firefox"},
    "edge": {"category": "browser", "exe": "msedge"},
    "opera": {"category": "browser", "exe": "opera"},
    "brave": {"category": "browser", "exe": "brave"},
    # Communication
    "slack": {"category": "communication", "exe": "slack"},
    "teams": {"category": "communication", "exe": "teams"},
    "discord": {"category": "communication", "exe": "discord"},
    "zoom": {"category": "communication", "exe": "zoom"},
    "outlook": {"category": "communication", "exe": "OUTLOOK"},
    # Productivity
    "notion": {"category": "productivity", "exe": "Notion"},
    "obsidian": {"category": "productivity", "exe": "Obsidian"},
    "onenote": {"category": "productivity", "exe": "ONENOTE"},
    "dropbox": {"category": "productivity", "exe": "Dropbox"},
    "onedrive": {"category": "productivity", "exe": "OneDrive"},
    " libreoffice": {"category": "productivity", "exe": "soffice"},
    # Media
    "spotify": {"category": "media", "exe": "Spotify"},
    "vlc": {"category": "media", "exe": "vlc"},
    "gimp": {"category": "media", "exe": "gimp"},
    "blender": {"category": "media", "exe": "blender"},
    # Games / Launchers
    "steam": {"category": "games", "exe": "steam"},
    "epic": {"category": "games", "exe": "EpicGamesLauncher"},
    "minecraft": {"category": "games", "exe": "MinecraftLauncher"},
}
```

**Detection Logic:** For each entry in `KNOWN_SOFTWARE`, attempt detection via:
1. `shutil.which(exe)` — for CLI tools
2. Registry key search using `DisplayName` match
3. Filesystem path check for known install locations

**Complexity:** O(n) where n = len(KNOWN_SOFTWARE). Each check is a simple dict lookup or registry open — **not a full registry traversal**. The registry scan for uninstalled apps is separate and also bounded.

**Performance target:** < 1.5 seconds at startup.

### 2.2 RuntimeScanner

**Purpose:** Snapshot of currently running processes at scan time.

**Method:** `subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True)` — single Windows built-in call.

**Cached Output:** `List[str]` of process names (uppercased for matching).

**Also-runs once at startup.** No polling.

### 2.3 ToolScanner

**Purpose:** Map detected executables → MOKA plugin names.

**Implementation:** Static `TOOL_TO_PLUGIN` mapping dict — O(1) lookup.

```python
TOOL_TO_PLUGIN = {
    "code": "vscode",
    "git": "git",
    "chrome": "chrome",
    "explorer": "explorer",
    "wt": "terminal",
    "cmd": "terminal",
    "python": "terminal",
    "docker": "terminal",
    "node": "terminal",
    "comfyui": "comfyui",
}
```

---

## 3. SoftwareProfileEngine

**Purpose:** Aggregate scan results into `SoftwareProfile` entries in `SoftwareProfileDatabase`.

**Generated Profiles:**

| Profile ID | Name | Description |
|------------|------|-------------|
| `desktop-scan` | Desktop Environment Scan | Full software inventory from this scan |
| `desktop-runtime` | Desktop Runtime | Running processes at scan time |
| `category-dev` | Dev Tools | Detected dev tools available |
| `category-browser` | Browsers | Detected browsers |
| `category-communication` | Communication Apps | Detected comms apps |
| `category-productivity` | Productivity Apps | Detected productivity apps |
| `category-games` | Games & Launchers | Detected game launchers |

**`confidence_score` determination:**
- Direct executable detection via PATH or known path → `0.95`
- Registry match without version confirmation → `0.8`
- Category presence via running process snapshot → `0.7`

**Engine output:** Updates `SoftwareProfileDatabase` with generated profiles. Existing `profile_id` entries are overwritten on each scan (session-refresh semantics).

---

## 4. Fallback Handling

**Principle:** Per-plugin `verify()` is the source of truth at execution time. Scanner results prime the cache, but `verify()` checks liveness.

**Fallback Chain:**

```
1. Scanner marks tool "not found"  →  profile written with low confidence
2. Plugin.execute() called          →  plugin.verify() returns False
3. PluginManager.execute() catches  →  returns {"ok": False, "error": "...not found"}
4. Moka responds gracefully          →  "X not available — skipping or install?"
```

**No plugin crash propagates.** The `IsolatedPluginRunner` already catches exceptions. If `verify()` is False, the plugin is in `PluginState.DISABLED` and execution is denied.

**When scan finds nothing for a category:** The profile exists but with empty `usage_patterns`. Moka knows the category is available at low confidence. Plugins in that category are still tried — their own `verify()` may confirm or deny.

---

## 5. Phase 8 Module Inventory

| Module | File | Responsibility |
|--------|------|----------------|
| `SoftwareScanner` | `core_runtime/software_scanner.py` | Registry/path/disk detection |
| `RuntimeScanner` | `core_runtime/runtime_scanner.py` | Running process snapshot |
| `ToolScanner` | `core_runtime/tool_scanner.py` | Executable → plugin mapping |
| `SoftwareProfileEngine` | `core_runtime/software_profile_engine.py` | Profile generation |
| `DesktopRuntimeCache` | `core_runtime/desktop_runtime_cache.py` | In-memory scan result cache |
| `DesktopRuntimeManager` | `core_runtime/desktop_runtime_manager.py` | Orchestrates all scanners, wires to MokaAI |

---

## 6. Resource Cost

| Operation | Time | Memory | Background |
|-----------|------|--------|------------|
| SoftwareScanner startup | ~1.2s | < 100 KB | No |
| RuntimeScanner startup | ~0.2s | < 10 KB | No |
| ToolScanner init | < 1ms | < 5 KB | No |
| SoftwareProfileEngine | < 50ms | < 50 KB | No |
| **Total at startup** | **~1.5s once** | **< 200 KB** | **Zero** |

No background threads, no polling, no periodic scans.

---

## 7. Acceptance Criteria

| Criterion | Verification |
|-----------|-------------|
| Profiles generated | `DesktopRuntimeManager.run()` produces entries in `SoftwareProfileDatabase` |
| Fallback handling works | Plugin `verify()` returns False when tool absent; `execute()` returns error dict |
| Zero background cost | After startup, no threads running, no scheduled scans |
| Broad software detection | Scanner queries both registry hives + PATH + known paths |
| Plugin isolation preserved | Plugin crash during scan does not affect Moka core |