import unittest, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.module_registry import ModuleRegistry, ModuleMetadata

class TestMR(unittest.TestCase):
    def test_register_get(self):
        r = ModuleRegistry(); r.register("m", ModuleMetadata("m","1.0.0","desc"), lambda: object())
        self.assertIsNotNone(r.get("m"))
    def test_list(self):
        r = ModuleRegistry()
        r.register("a", ModuleMetadata("a","1.0.0",""), lambda: None)
        r.register("b", ModuleMetadata("b","1.0.0",""), lambda: None)
        self.assertEqual(len(r.list_modules()), 2)
    def test_metadata(self):
        r = ModuleRegistry(); r.register("x", ModuleMetadata("x","2.0.0","d"), lambda: None)
        self.assertEqual(r.get_metadata("x").version, "2.0.0")
    def test_deregister(self):
        r = ModuleRegistry(); r.register("y", ModuleMetadata("y","1.0.0",""), lambda: None)
        r.deregister("y"); self.assertIsNone(r.get("y"))

if __name__ == "__main__": unittest.main()