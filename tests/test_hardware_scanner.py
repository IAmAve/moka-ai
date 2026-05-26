import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core_runtime.hardware_scanner import HardwareScanner, HardwareProfile


class TestHardwareScanner(unittest.TestCase):
    def test_scan_returns_profile(self):
        """scan() returns a HardwareProfile with float fields."""
        scanner = HardwareScanner()
        profile = scanner.scan()
        self.assertIsInstance(profile, HardwareProfile)
        self.assertIsInstance(profile.vram_gb, float)
        self.assertIsInstance(profile.system_ram_gb, float)
        self.assertIsInstance(profile.available_vram_gb, float)

    def test_hardware_profile_dataclass_fields(self):
        """Creating HardwareProfile directly sets and retrieves field values correctly."""
        profile = HardwareProfile(
            gpu_model="NVIDIA RTX 4090",
            vram_gb=24.0,
            system_ram_gb=32.0,
            available_vram_gb=16.0,
            compute_capability="8.9",
        )
        self.assertEqual(profile.gpu_model, "NVIDIA RTX 4090")
        self.assertEqual(profile.vram_gb, 24.0)
        self.assertEqual(profile.system_ram_gb, 32.0)
        self.assertEqual(profile.available_vram_gb, 16.0)
        self.assertEqual(profile.compute_capability, "8.9")

    def test_auto_tuned_limits_4gb(self):
        """_auto_limits returns correct tier values for 4GB VRAM."""
        scanner = HardwareScanner()
        limits = scanner._auto_limits(4.0)
        self.assertEqual(limits["max_resolution"], 512)
        self.assertEqual(limits["max_steps"], 50)
        self.assertEqual(limits["max_concurrent"], 1)

    def test_auto_tuned_limits_8gb(self):
        """_auto_limits returns correct tier values for 8GB VRAM."""
        scanner = HardwareScanner()
        limits = scanner._auto_limits(8.0)
        self.assertEqual(limits["max_resolution"], 1024)
        self.assertEqual(limits["max_steps"], 100)
        self.assertEqual(limits["max_concurrent"], 2)

    def test_auto_tuned_limits_16gb(self):
        """_auto_limits returns correct tier values for 16GB VRAM."""
        scanner = HardwareScanner()
        limits = scanner._auto_limits(16.0)
        self.assertEqual(limits["max_resolution"], 2048)
        self.assertEqual(limits["max_steps"], 200)
        self.assertEqual(limits["max_concurrent"], 3)


if __name__ == "__main__":
    unittest.main()