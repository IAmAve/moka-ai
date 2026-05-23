import unittest, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.version_manager import VersionManager, Version

class TestVersionManager(unittest.TestCase):
    def test_version_parsing(self):
        v = Version("1.2.3")
        self.assertEqual(v.major, 1)
        self.assertEqual(v.minor, 2)
        self.assertEqual(v.patch, 3)

    def test_version_comparison(self):
        self.assertTrue(Version("1.2.3") < Version("1.2.4"))
        self.assertTrue(Version("1.2.3") < Version("1.3.0"))
        self.assertTrue(Version("1.2.3") < Version("2.0.0"))
        self.assertEqual(Version("1.0.0"), Version("1.0.0"))

    def test_get_current_version(self):
        vm = VersionManager()
        v = vm.get_current_version()
        self.assertIsInstance(v, Version)
        self.assertEqual(v.major, 1)

    def test_needs_upgrade(self):
        vm = VersionManager()
        self.assertFalse(vm.needs_upgrade(Version("1.0.0")))
        self.assertTrue(vm.needs_upgrade(Version("0.9.0")))

if __name__ == "__main__":
    unittest.main()