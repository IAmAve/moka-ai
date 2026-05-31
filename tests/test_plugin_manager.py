import unittest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.plugin_manager import PluginManager, IsolatedPluginRunner, PluginState
from plugins.base_plugin import MokaPlugin, PluginMetadata, PluginPermissions


# ── Test plugin that always succeeds ────────────────────────────────────────
class DummyPlugin(MokaPlugin):
    @property
    def metadata(self):
        return PluginMetadata(name="dummy", version="1.0.0", description="Test", author="MOKA")

    @property
    def permissions(self):
        return PluginPermissions()

    def execute(self, data):
        return data.get("value", 0) * 2

    def verify(self):
        return True

    def rollback(self):
        return True

    def health(self):
        return {"ok": True, "message": "healthy"}


# ── Test plugin that crashes ─────────────────────────────────────────────────
class CrashingPlugin(MokaPlugin):
    @property
    def metadata(self):
        return PluginMetadata(name="crash", version="1.0.0", description="Crashes", author="MOKA")

    @property
    def permissions(self):
        return PluginPermissions()

    def execute(self, data):
        raise RuntimeError("intentional crash")

    def verify(self):
        return True

    def rollback(self):
        return True

    def health(self):
        return {"ok": False, "message": "crashed"}


class TestIsolatedPluginRunner(unittest.TestCase):
    def test_success_returns_result(self):
        runner = IsolatedPluginRunner(DummyPlugin(), logger=type("L", (), {"info": lambda s, m: None})())
        result = runner.execute({"value": 21}, timeout=5)
        self.assertTrue(result["ok"])
        self.assertEqual(result["result"], 42)

    def test_exception_caught_returns_error(self):
        runner = IsolatedPluginRunner(CrashingPlugin(), logger=type("L", (), {"info": lambda s, m: None})())
        result = runner.execute({}, timeout=5)
        self.assertFalse(result["ok"])
        self.assertIn("intentional crash", result["error"])


class TestPluginManager(unittest.TestCase):
    def setUp(self):
        self.logs = []
        self.logger = type("L", (), {"info": lambda s, m: self.logs.append(m)})()
        self.manager = PluginManager(plugins_path="plugins/", logger=self.logger)

    def test_initial_state_empty(self):
        self.assertEqual(len(self.manager._entries), 0)

    def test_execute_nonexistent_returns_error(self):
        result = self.manager.execute("no-such-plugin", {})
        self.assertFalse(result["ok"])
        self.assertIn("not found", result["error"])

    def test_direct_load_and_execute(self):
        dummy = DummyPlugin(logger=self.logger)
        self.manager._entries["dummy"] = type("E", (), {
            "name": "dummy",
            "instance": dummy,
            "state": PluginState.LOADED,
            "crash_count": 0,
            "recovery_lock": __import__("threading").Lock(),
        })()
        self.manager._executors["dummy"] = IsolatedPluginRunner(dummy, logger=self.logger)
        result = self.manager.execute("dummy", {"value": 3})
        self.assertTrue(result["ok"])
        self.assertEqual(result["result"], 6)

    def test_crash_isolated_does_not_propagate(self):
        crashing = CrashingPlugin(logger=self.logger)
        self.manager._entries["crash"] = type("E", (), {
            "name": "crash",
            "instance": crashing,
            "state": PluginState.LOADED,
            "crash_count": 0,
            "max_retries": 1,
            "retry_delay": 0.1,
            "recovery_lock": __import__("threading").Lock(),
        })()
        self.manager._executors["crash"] = IsolatedPluginRunner(crashing, logger=self.logger)
        # Should not raise — exception is caught internally
        result = self.manager.execute("crash", {})
        self.assertFalse(result["ok"])
        self.assertEqual(result["plugin"], "crash")

    def test_health_check_one_plugin(self):
        self.assertEqual(self.manager.health_check("dummy"), {"ok": False, "error": "not found"})

    def test_discover_plugins_finds_created_files(self):
        # Count actual plugin files in the plugins directory
        discovered = self.manager.discover_plugins()
        self.assertIsInstance(discovered, list)

    def test_plugin_recovery_disabled_after_max_retries(self):
        crashing = CrashingPlugin(logger=self.logger)
        entry = type("E", (), {
            "name": "crash",
            "instance": crashing,
            "state": PluginState.CRASHED,
            "crash_count": 3,
            "max_retries": 2,
            "retry_delay": 0.1,
            "recovery_lock": __import__("threading").Lock(),
            "last_crash": None,
            "last_health": None,
        })()
        if hasattr(entry, "last_crash"):
            entry.last_crash = __import__("datetime").datetime.now()
        self.manager._entries["crash"] = entry
        self.manager._schedule_recovery("crash")
        self.assertEqual(entry.state, PluginState.DISABLED)


class TestBasePluginInterface(unittest.TestCase):
    def test_abstract_methods_raise(self):
        class Incomplete(MokaPlugin):
            pass
        # Cannot instantiate abstract class
        with self.assertRaises(TypeError):
            Incomplete()

    def test_metadata_defaults(self):
        class Complete(MokaPlugin):
            @property
            def metadata(self):
                return PluginMetadata(name="x", version="1.0", description="y", author="z")
            @property
            def permissions(self):
                return PluginPermissions()

            def execute(self, data):
                return {}
            def verify(self):
                return True
            def rollback(self):
                return True
            def health(self):
                return {"ok": True, "message": ""}

        p = Complete()
        self.assertEqual(p.metadata.name, "x")
        self.assertFalse(p.permissions.filesystem)


if __name__ == "__main__":
    unittest.main()