import unittest, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core_runtime.tool_scanner import ToolScanner

class TestToolScanner(unittest.TestCase):
    def test_map_code_vscode(self):
        self.assertEqual(ToolScanner().map("code"), "vscode")
    def test_map_git_git(self):
        self.assertEqual(ToolScanner().map("git"), "git")
    def test_map_chrome_chrome(self):
        self.assertEqual(ToolScanner().map("chrome"), "chrome")
    def test_map_unknown_none(self):
        self.assertIsNone(ToolScanner().map("nonexistent_xyz789"))
    def test_map_case_insensitive(self):
        self.assertEqual(ToolScanner().map("CODE"), "vscode")
    def test_bulk_map_filters_none(self):
        r = ToolScanner().bulk_map(["code", "git", "nonexistent_xyz"])
        self.assertIn("vscode", r)
        self.assertIn("git", r)
        self.assertNotIn("nonexistent_xyz", r)