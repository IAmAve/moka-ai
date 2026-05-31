"""
Plugin Manager for MOKA AI

Handles plugin discovery, hot-loading, execution isolation, crash recovery,
and lifecycle management. Each plugin runs in an isolated context — a crash
in one plugin does not affect others or the main process.
"""

import os
import sys
import importlib.util
import threading
import time
import queue
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


class PluginState(Enum):
    LOADED = "loaded"
    RUNNING = "running"
    CRASHED = "crashed"
    DISABLED = "disabled"
    RECOVERING = "recovering"


@dataclass
class PluginEntry:
    name: str
    instance: Any
    spec: Any
    state: PluginState = PluginState.LOADED
    crash_count: int = 0
    last_crash: Optional[datetime] = None
    last_health: Optional[Dict[str, Any]] = None
    max_retries: int = 3
    retry_delay: float = 5.0
    recovery_lock: threading.Lock = field(default_factory=threading.Lock)


class IsolatedPluginRunner:
    """Wraps a plugin execute() call in full exception isolation."""

    def __init__(self, plugin: Any, logger: Callable = None):
        self._plugin = plugin
        self._logger = logger
        self._log = logger.info if logger else lambda m: None
        self._result_queue: queue.Queue = queue.Queue(maxsize=1)
        self._error_queue: queue.Queue = queue.Queue(maxsize=1)
        self._crashed = False
        self._crash_error: Optional[Exception] = None

    def execute(self, data: Dict[str, Any], timeout: float = 30.0) -> Dict[str, Any]:
        self._crashed = False
        self._crash_error = None
        worker = threading.Thread(target=self._run, args=(data,), daemon=True)
        worker.start()
        worker.join(timeout=timeout)

        if worker.is_alive():
            self._log(f"Plugin '{self._plugin.metadata.name}' timed out after {timeout}s")
            return {"ok": False, "error": "execution timeout", "plugin": self._plugin.metadata.name}
        if self._crashed:
            self._plugin.on_crash(self._crash_error)
            if self._plugin._rollback_handler:
                try:
                    self._plugin._rollback_handler()
                    self._log(f"Rollback handler executed for '{self._plugin.metadata.name}'")
                except Exception as rb_err:
                    self._log(f"Rollback also failed: {rb_err}")
            return {"ok": False, "error": str(self._crash_error), "plugin": self._plugin.metadata.name}

        try:
            return self._result_queue.get_nowait()
        except queue.Empty:
            return {"ok": False, "error": "no result returned", "plugin": self._plugin.metadata.name}

    def _run(self, data: Dict[str, Any]) -> None:
        try:
            result = self._plugin.execute(data)
            try:
                self._result_queue.put_nowait({"ok": True, **result} if isinstance(result, dict) else {"ok": True, "result": result})
            except queue.Full:
                pass
        except Exception as e:
            self._crashed = True
            self._crash_error = e
            try:
                self._error_queue.put_nowait(e)
            except queue.Full:
                pass


class PluginManager:
    """Manages hot-loading, isolation, and crash recovery for MOKA plugins."""

    def __init__(self, plugins_path: str = "plugins/", logger: Callable = None):
        self._logger = logger
        self._log = logger.info if logger else lambda m: None
        if hasattr(plugins_path, "config") and hasattr(plugins_path, "get"):
            # Accept Config object — pull plugins_path from its config dict
            self.plugins_path = plugins_path.get("plugins_path", "plugins/")
        else:
            self.plugins_path = plugins_path
        self._entries: Dict[str, PluginEntry] = {}
        self._executors: Dict[str, IsolatedPluginRunner] = {}
        self._recovery_thread: Optional[threading.Thread] = None
        self._recovery_running = False
        self._health_checks: Dict[str, threading.Event] = {}
        self._log(f"PluginManager initialized with path: {self.plugins_path}")

    def initialize(self) -> bool:
        """Discover and load all plugins. Returns True if any loaded successfully."""
        count = self.load_all()
        return count > 0

    # ── Loading ────────────────────────────────────────────────────────────

    def discover_plugins(self) -> List[str]:
        """Return plugin filenames found in the plugins directory."""
        if not os.path.exists(self.plugins_path):
            return []
        return [f for f in os.listdir(self.plugins_path) if f.endswith(".py") and not f.startswith("_")]

    def load_plugin(self, plugin_file: str) -> bool:
        """Load a single plugin file, instantiate its MokaPlugin, and register it."""
        try:
            spec = importlib.util.spec_from_file_location(
                f"plugins.{plugin_file[:-3]}",
                os.path.join(self.plugins_path, plugin_file),
            )
            if spec is None or spec.loader is None:
                return False

            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)

            # Find the first MokaPlugin subclass in the module
            plugin_cls = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and issubclass(attr, self._get_base_plugin()) and attr is not self._get_base_plugin():
                    plugin_cls = attr
                    break

            if plugin_cls is None:
                self._log(f"No MokaPlugin subclass found in {plugin_file}")
                return False

            instance = plugin_cls(logger=self._logger)
            entry = PluginEntry(
                name=instance.metadata.name,
                instance=instance,
                spec=spec,
            )
            self._entries[instance.metadata.name] = entry
            self._executors[instance.metadata.name] = IsolatedPluginRunner(instance, logger=self._logger)
            self._log(f"Loaded plugin '{instance.metadata.name}' v{instance.metadata.version}")
            return True

        except Exception as e:
            self._log(f"Failed to load plugin {plugin_file}: {e}")
            return False

    def load_all(self) -> int:
        """Discover and load all plugins. Returns count of successfully loaded."""
        count = 0
        for plugin_file in self.discover_plugins():
            if self.load_plugin(plugin_file):
                count += 1
        self._log(f"Loaded {count}/{len(self.discover_plugins())} plugins")
        return count

    def unload_plugin(self, name: str) -> bool:
        if name not in self._entries:
            return False
        self._entries[name].state = PluginState.DISABLED
        del self._entries[name]
        del self._executors[name]
        self._log(f"Unloaded plugin '{name}'")
        return True

    # ── Execution ─────────────────────────────────────────────────────────

    def execute(self, plugin_name: str, data: Dict[str, Any] = None, timeout: float = 30.0) -> Dict[str, Any]:
        """Execute a plugin in isolation. Returns result dict or error."""
        if plugin_name not in self._entries:
            return {"ok": False, "error": f"plugin '{plugin_name}' not found"}
        entry = self._entries[plugin_name]
        if entry.state == PluginState.DISABLED:
            return {"ok": False, "error": f"plugin '{plugin_name}' is disabled"}

        entry.state = PluginState.RUNNING
        try:
            executor = self._executors.get(plugin_name)
            if not executor:
                return {"ok": False, "error": "executor not found"}

            result = executor.execute(data or {}, timeout=timeout)

            if not result.get("ok", False):
                entry.state = PluginState.CRASHED
                entry.crash_count += 1
                entry.last_crash = datetime.now()
                self._log(f"Plugin '{plugin_name}' execution failed: {result.get('error')}")
                self._schedule_recovery(plugin_name)
            else:
                entry.state = PluginState.LOADED
                entry.instance.reset_health()
                entry.last_health = entry.instance.health()

            return result
        finally:
            if entry.state == PluginState.RUNNING:
                entry.state = PluginState.LOADED

    # ── Crash recovery ─────────────────────────────────────────────────────

    def _schedule_recovery(self, plugin_name: str) -> None:
        entry = self._entries.get(plugin_name)
        if not entry:
            return
        if entry.crash_count >= entry.max_retries:
            entry.state = PluginState.DISABLED
            self._log(f"Plugin '{plugin_name}' disabled after {entry.crash_count} crashes")
            return
        entry.state = PluginState.RECOVERING
        if not self._recovery_running:
            self._start_recovery_thread()
        self._log(f"Plugin '{plugin_name}' scheduled for recovery in {entry.retry_delay}s (crash {entry.crash_count}/{entry.max_retries})")

    def _start_recovery_thread(self) -> None:
        self._recovery_running = True
        self._recovery_thread = threading.Thread(target=self._recovery_loop, daemon=True)
        self._recovery_thread.start()

    def _recovery_loop(self) -> None:
        while self._recovery_running:
            for name, entry in list(self._entries.items()):
                if entry.state != PluginState.RECOVERING:
                    continue
                recovery_ready = True
                if entry.last_crash:
                    elapsed = (datetime.now() - entry.last_crash).total_seconds()
                    recovery_ready = elapsed >= entry.retry_delay
                if not recovery_ready:
                    continue

                with entry.recovery_lock:
                    try:
                        healthy = entry.instance.verify()
                        health_report = entry.instance.health()
                        entry.instance.reset_health()
                        entry.last_health = health_report
                        if healthy and health_report.get("ok", False):
                            entry.state = PluginState.LOADED
                            self._log(f"Plugin '{name}' recovered successfully")
                            # Re-create executor in case the thread crashed
                            self._executors[name] = IsolatedPluginRunner(entry.instance, logger=self._logger)
                        else:
                            raise RuntimeError(f"health check failed: {health_report.get('message', 'unknown')}")
                    except Exception as e:
                        entry.crash_count += 1
                        entry.last_crash = datetime.now()
                        if entry.crash_count >= entry.max_retries:
                            entry.state = PluginState.DISABLED
                            self._log(f"Plugin '{name}' disabled after recovery failure: {e}")
                        else:
                            entry.state = PluginState.RECOVERING
                            self._log(f"Plugin '{name}' recovery attempt failed: {e}")
            time.sleep(1.0)

    def recover_plugin(self, plugin_name: str) -> bool:
        """Manually trigger recovery for a crashed plugin."""
        entry = self._entries.get(plugin_name)
        if not entry:
            return False
        with entry.recovery_lock:
            try:
                entry.instance.verify()
                entry.instance.reset_health()
                entry.last_health = entry.instance.health()
                entry.state = PluginState.LOADED
                entry.crash_count = 0
                entry.last_crash = None
                self._executors[plugin_name] = IsolatedPluginRunner(entry.instance, logger=self._logger)
                self._log(f"Plugin '{plugin_name}' manually recovered")
                return True
            except Exception as e:
                self._log(f"Manual recovery of '{plugin_name}' failed: {e}")
                return False

    # ── Status ─────────────────────────────────────────────────────────────

    def health_check(self, plugin_name: str = None) -> Dict[str, Any]:
        """Return health for one plugin or all plugins."""
        if plugin_name:
            entry = self._entries.get(plugin_name)
            if not entry:
                return {"ok": False, "error": "not found"}
            return {
                "name": entry.name,
                "state": entry.state.value,
                "crash_count": entry.crash_count,
                "last_crash": entry.last_crash.isoformat() if entry.last_crash else None,
                "health": entry.instance.health() if entry.instance else {"ok": False, "message": "no instance"},
            }
        return {
            name: self.health_check(name) for name in self._entries
        }

    def is_healthy(self) -> bool:
        return all(e.state == PluginState.LOADED for e in self._entries.values())

    # ── Static helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _get_base_plugin():
        from plugins.base_plugin import MokaPlugin
        return MokaPlugin