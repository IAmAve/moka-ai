import unittest, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core_runtime.desktop_runtime_cache import DesktopRuntimeCache

class TestDesktopRuntimeCache(unittest.TestCase):
    def test_singleton_same_instance(self):
        c1 = DesktopRuntimeCache()
        c2 = DesktopRuntimeCache()
        self.assertIs(c1, c2)

    def test_set_and_get_software(self):
        c = DesktopRuntimeCache()
        c.clear()
        c.set_software("git", {"name": "git", "version": "2.40", "path": "/a", "source": "path", "category": "dev"})
        result = c.get_software("git")
        self.assertIsNotNone(result)
        self.assertEqual(result["name"], "git")

    def test_get_missing_returns_none(self):
        c = DesktopRuntimeCache()
        c.clear()
        self.assertIsNone(c.get_software("nonexistent"))

    def test_runtime_roundtrip(self):
        c = DesktopRuntimeCache()
        c.clear()
        c.set_runtime(["CODE.EXE", "GIT.EXE"])
        self.assertEqual(len(c.get_runtimes()), 2)

    def test_plugin_availability_defaults_true(self):
        c = DesktopRuntimeCache()
        self.assertTrue(c.is_plugin_available("vscode"))

    def test_set_plugin_availability(self):
        c = DesktopRuntimeCache()
        c.clear()
        c.set_plugin_availability("chrome", False)
        self.assertFalse(c.is_plugin_available("chrome"))

    def test_clear_empties_cache(self):
        c = DesktopRuntimeCache()
        c.clear()
        c.set_software("x", {"name": "x"})
        c.set_runtime(["A"])
        c.clear()
        self.assertEqual(len(c.get_all_software()), 0)
        self.assertEqual(len(c.get_runtimes()), 0)

    def test_hardware_profile_storage(self):
        """set_hardware_profile / get_hardware_profile round-trips correctly."""
        from core_runtime.hardware_scanner import HardwareProfile
        cache = DesktopRuntimeCache()
        profile = HardwareProfile(gpu_model="RTX 4090", vram_gb=24.0, system_ram_gb=32.0,
                                  available_vram_gb=24.0, compute_capability="8.9")
        cache.set_hardware_profile(profile)
        retrieved = cache.get_hardware_profile()
        self.assertIsInstance(retrieved, HardwareProfile)
        self.assertEqual(retrieved.gpu_model, "RTX 4090")
        self.assertEqual(retrieved.vram_gb, 24.0)

if __name__ == "__main__":
    unittest.main()