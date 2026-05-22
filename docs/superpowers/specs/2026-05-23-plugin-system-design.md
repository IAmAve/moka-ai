# Plugin System Design

> **For agentic workers:** Implementation via `superpowers:writing-plans` with `superpowers:subagent-driven-development` or `superpowers:executing-plans`.

**Goal:** Production plugin architecture for MOKA AI enabling third-party extensions and built-in tool wrappers with crash isolation, recovery, and hot-load capability.

**Architecture:** Process-isolated plugins communicate via message-based RPC. MOKA is the parent orchestrator; plugins are stateless wrappers around external tools. Each plugin runs in its own subprocess with isolated address space.

**Tech Stack:** Python `subprocess` + `json-rpc` over stdin/stdout, `signal` for lifecycle management, `psutil` for resource monitoring.

---

## 1. Plugin Structure

```
plugins/
  <plugin_name>/
    manifest.json        # Plugin metadata and permissions
    plugin.py            # Entry point — implements Plugin interface
    requirements.txt     # Optional pip dependencies (auto-installed on load)
    config/              # Plugin-specific configuration
      default.json
```

### manifest.json Schema

```json
{
  "name": "vscode",
  "version": "1.0.0",
  "description": "VSCode editor integration",
  "entry": "plugin.py",
  "permissions": ["process", "filesystem:./projects/*"],
  "health_check": "ping",
  "commands": {
    "open_file": { "description": "Open file in VSCode" },
    "search": { "description": "Search in workspace" }
  }
}
```

### Plugin Interface (plugin.py)

```python
from abc import ABC, abstractmethod

class Plugin(ABC):
    @abstractmethod
    def metadata(self) -> dict:
        """Returns manifest contents."""

    @abstractmethod
    def execute(self, command: str, params: dict) -> dict:
        """
        Executes a command.
        Returns: {"success": bool, "result": any, "error": str|null}
        """

    @abstractmethod
    def verify(self) -> bool:
        """Health check — returns True if plugin is responsive."""

    @abstractmethod
    def rollback(self, action_id: str) -> bool:
        """Rollback effects of a specific action."""

    @abstractmethod
    def health(self) -> dict:
        """
        Returns health status: {
          "status": "ok|degraded|down",
          "latency_ms": int,
          "error": str|null
        }
        """

    def on_load(self) -> bool:
        """Called when plugin is loaded. Return False to reject load."""
        return True

    def on_unload(self) -> None:
        """Called when plugin is unloaded."""
        pass
```

---

## 2. PluginManager

Manages plugin lifecycle — loading, unloading, querying.

```python
class PluginManager:
    def __init__(self, plugins_path: str = "plugins/"):
        self._plugins: dict[str, PluginInstance] = {}
        self._plugins_path = plugins_path

    def discover(self) -> list[str]:
        """Scans plugins_path for plugin directories with manifest.json."""

    def load(self, name: str) -> bool:
        """Loads plugin by name. Spawns subprocess, runs health check."""

    def unload(self, name: str) -> None:
        """Stops plugin subprocess gracefully, calls on_unload."""

    def reload(self, name: str) -> bool:
        """Unloads then loads — hot reload."""

    def execute(self, name: str, command: str, params: dict) -> dict:
        """Sends command to plugin subprocess via RPC."""

    def get_plugin(self, name: str) -> PluginInstance | None:
        """Returns loaded plugin instance or None."""

    def list_loaded(self) -> list[str]:
        """Returns names of currently loaded plugins."""

    def list_available(self) -> list[str]:
        """Returns names of all discovered plugins (loaded + available)."""

    def get_health(self, name: str) -> dict:
        """Returns health status of a plugin."""
```

### PluginInstance

```python
@dataclass
class PluginInstance:
    name: str
    process: subprocess.Popen
    manifest: dict
    state: Literal["loading", "running", "degraded", "down", "unloading"]
    restart_policy: RestartPolicy
    consecutive_failures: int = 0
```

---

## 3. Crash Recovery

### RestartPolicy

```python
@dataclass
class RestartPolicy:
    max_retries: int = 3
    base_delay_seconds: float = 1.0
    exponential_base: float = 2.0
```

### Recovery Flow

```
Plugin execution fails (crash or non-zero exit)
  → increment consecutive_failures
  → if failures < max_retries:
      sleep(delay = base_delay * exponential_base ** failures)
      respawn plugin process, re-execute
  → else:
      set state = "down"
      notify operator (log + optional callback)
      plugin stays disabled until explicitly reloaded
```

### Graceful Degradation

- If a plugin is `down`, `execute()` returns `{"success": False, "error": "plugin unavailable"}`
- Other plugins continue functioning
- MOKA core never crashes due to plugin failure

---

## 4. Message Protocol (RPC)

MOKA ↔ Plugin communication via JSON-RPC over stdin/stdout.

**MOKA → Plugin (request):**
```json
{
  "jsonrpc": "2.0",
  "id": "uuid",
  "method": "execute",
  "params": {
    "command": "open_file",
    "params": {"path": "src/main.py", "line": 42}
  }
}
```

**Plugin → MOKA (response):**
```json
{
  "jsonrpc": "2.0",
  "id": "uuid",
  "result": {"success": true, "result": "opened"},
  "error": null
}
```

**Plugin → MOKA (notification):**
```json
{
  "jsonrpc": "2.0",
  "method": "health_report",
  "params": {"status": "degraded", "latency_ms": 500}
}
```

---

## 5. Built-in Plugins

All built-in plugins are wrappers around external CLI tools.

### vscode

- Commands: `open_file`, `open_folder`, `search`, `show_in_editor`
- Wrapper: `code.exe` CLI (`code --goto <file>:<line>`)
- Health check: `code --version` (fast, no-op)

### git

- Commands: `status`, `commit`, `push`, `pull`, `log`, `branch_list`, `diff`
- Wrapper: `git` CLI
- Health check: `git --version`

### chrome

- Commands: `navigate`, `search`, `get_page`, `bookmarks`
- Wrapper: Chrome CLI with `--remote-debugging-port` + CDP protocol
- Health check: CDP `Browser.getVersion`

### explorer

- Commands: `list_dir`, `show_in_folder`, `create_folder`, `copy_file`, `move_file`, `delete_file`
- Wrapper: Python `pathlib` + `shutil` (no external dependency)
- Health check: `list_dir(".")` (always works)

### terminal

- Commands: `execute`, `get_output`, `kill`
- Wrapper: `conhost.exe` or Windows Terminal CLI
- Health check: `echo pong`
- **Caution:** Commands are routed through safety system before execution

### comfyui

- Commands: `trigger_workflow`, `queue_status`, `get_history`, `clear_queue`
- Wrapper: ComfyUI `ComfyUI-SDK` or HTTP API (`http://localhost:8188`)
- Health check: `GET /history` (empty but confirms server up)
- **Caution:** Workflow triggers routed through approval queue (DANGEROUS level)

---

## 6. Safety Integration

- All plugin commands pass through `safety/execution_pipeline.py` before execution
- Plugins declare their permission requirements in `manifest.json` under `permissions`
- DANGEROUS operations (file deletion, network calls) trigger approval queue
- Execution pipeline handles rollback if plugin action fails post-execution
- **Terminal plugin** is the only plugin that executes arbitrary commands — those commands are scanned by `risk_scanner.py` before running

---

## 7. Hot-Loading

- **No automatic scanning during runtime** — operator controls load/unload
- `!plugin load <name>` — discovers, loads, health-checks
- `!plugin unload <name>` — graceful shutdown, no restart
- `!plugin reload <name>` — hot reload without restarting MOKA core
- `!plugin list` — shows all available and loaded plugins
- After initial MOKA startup, all plugins start in `available` (not loaded) state
- On `!plugin load all`, all discovered plugins load simultaneously

---

## 8. Error Handling

| Scenario | Behavior |
|----------|----------|
| Plugin process crashes mid-execution | Recovery flow (retry with backoff) |
| Plugin returns error JSON | Wrapped with context: which plugin, which command |
| Plugin times out (>30s per command) | Plugin marked `degraded`, operator notified |
| Plugin manifest missing | Rejected at discover time — not loadable |
| Plugin on_unload throws | Logged, process killed, instance cleaned up |
| Plugin subprocess not responding to ping | Health check fails → degraded state |

---

## 9. Testing

- Unit tests per plugin (mock the subprocess/Popen layer)
- PluginManager tests: load, unload, reload, execute, health
- Recovery tests: simulate crash, verify retry + disable behavior
- RPC protocol tests: malformed JSON, wrong message types, timeouts
- Integration tests: real plugin subprocess spawned, command roundtripped