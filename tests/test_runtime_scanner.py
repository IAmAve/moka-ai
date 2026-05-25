import unittest, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core_runtime.runtime_scanner import RuntimeScanner

class TestRuntimeScanner(unittest.TestCase):
    def test_scan_returns_list(self):
        self.assertIsInstance(RuntimeScanner().scan(), list)
    def test_items_uppercase(self):
        for item in RuntimeScanner().scan():
            self.assertEqual(item, item.upper())
    def test_items_are_strings(self):
        for item in RuntimeScanner().scan():
            self.assertIsInstance(item, str)
    def test_not_empty(self):
        self.assertGreater(len(RuntimeScanner().scan()), 0)