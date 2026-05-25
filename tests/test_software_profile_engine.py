import unittest, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from unittest.mock import MagicMock
from core_runtime.software_profile_engine import SoftwareProfileEngine

class TestSoftwareProfileEngine(unittest.TestCase):
    def setUp(self):
        mock_db = MagicMock()
        self.engine = SoftwareProfileEngine(db=mock_db)

    def test_generate_returns_desktop_scan(self):
        r = self.engine.generate({}, [], {})
        self.assertIn("desktop-scan", r)
        self.assertIn("desktop-runtime", r)

    def test_desktop_scan_has_correct_fields(self):
        r = self.engine.generate({}, [], {})
        p = r["desktop-scan"]
        self.assertEqual(p.profile_id, "desktop-scan")
        self.assertIn("Desktop Environment", p.name)

    def test_all_6_categories_generated(self):
        r = self.engine.generate({}, [], {})
        for cat in ("dev", "browser", "communication", "productivity", "media", "games"):
            self.assertIn(f"category-{cat}", r, f"missing category-{cat}")

    def test_path_source_boosts_confidence(self):
        software = {"git": {"name": "git", "version": "2.40", "path": "/a", "source": "path", "category": "dev"}}
        r = self.engine.generate(software, [], {})
        self.assertGreaterEqual(r["desktop-scan"].confidence_score, 0.9)

    def test_empty_software_still_returns_profiles(self):
        r = self.engine.generate({}, [], {})
        self.assertEqual(len(r), 8)  # desktop-scan + runtime + 6 categories

if __name__ == "__main__":
    unittest.main()