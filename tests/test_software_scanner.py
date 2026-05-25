import unittest, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core_runtime.software_scanner import SoftwareScanner

class TestSoftwareScanner(unittest.TestCase):
    def test_known_software_has_git_and_chrome(self):
        s = SoftwareScanner()
        self.assertIn("git", s.KNOWN_SOFTWARE)
        self.assertIn("chrome", s.KNOWN_SOFTWARE)

    def test_all_have_category_and_exe(self):
        s = SoftwareScanner()
        for name, spec in s.KNOWN_SOFTWARE.items():
            self.assertIn("category", spec, name)
            self.assertIn("exe", spec, name)

    def test_scan_returns_dict(self):
        r = SoftwareScanner().scan()
        self.assertIsInstance(r, dict)

    def test_results_have_required_keys(self):
        r = SoftwareScanner().scan()
        for name, data in r.items():
            for k in ("name", "version", "path", "source", "category"):
                self.assertIn(k, data, f"{name} missing {k}")
            break

    def test_all_6_categories_present(self):
        cats = {spec["category"] for spec in SoftwareScanner().KNOWN_SOFTWARE.values()}
        for c in ("dev", "browser", "communication", "productivity", "media", "games"):
            self.assertIn(c, cats, f"missing category: {c}")