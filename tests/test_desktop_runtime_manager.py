import unittest, sys, os, threading
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from unittest.mock import MagicMock
from core_runtime.desktop_runtime_manager import DesktopRuntimeManager

class TestDesktopRuntimeManager(unittest.TestCase):
    def test_run_returns_required_keys(self):
        result = DesktopRuntimeManager().run()
        for k in ("software_detected", "runtime_count", "plugins_available", "profiles_generated"):
            self.assertIn(k, result)

    def test_run_counts_non_negative(self):
        result = DesktopRuntimeManager().run()
        self.assertGreaterEqual(result["software_detected"], 0)
        self.assertGreaterEqual(result["runtime_count"], 0)

    def test_get_cache_returns_cache(self):
        m = DesktopRuntimeManager()
        self.assertIsNotNone(m.get_cache())

    def test_no_extra_non_daemon_threads(self):
        before = {t.name for t in threading.enumerate() if not t.daemon and t.is_alive()}
        DesktopRuntimeManager().run()
        after = {t.name for t in threading.enumerate() if not t.daemon and t.is_alive()}
        # Only the test runner thread should be added
        new = after - before
        self.assertEqual(len(new), 0, f"new threads: {new}")

if __name__ == "__main__":
    unittest.main()