import unittest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from safety.risk_scanner import RiskScanner, RiskAssessment
from safety.intent_detector import Intent
from safety.permission_levels import PermissionLevel

class TestRiskScanner(unittest.TestCase):
    def test_safe_action_not_blocked(self):
        scanner = RiskScanner()
        intent = Intent("read", "config.py", {}, PermissionLevel.SAFE, "read config.py")
        assessment = scanner.assess(intent)
        self.assertFalse(assessment.blocked)

    def test_dangerous_pattern_blocked(self):
        scanner = RiskScanner()
        intent = Intent("execute", "rm -rf /tmp/test", {}, PermissionLevel.DANGEROUS, "rm -rf /tmp/test")
        assessment = scanner.assess(intent)
        self.assertTrue(assessment.blocked)
        self.assertIn("dangerous_pattern", assessment.risk_factors)

    def test_protected_path_blocked(self):
        scanner = RiskScanner()
        intent = Intent("delete", "/etc/passwd", {}, PermissionLevel.DANGEROUS, "delete /etc/passwd")
        assessment = scanner.assess(intent)
        self.assertTrue(assessment.blocked)
        self.assertIn("protected_path", assessment.risk_factors)

    def test_medium_requires_approval(self):
        scanner = RiskScanner()
        intent = Intent("write", "project/newfile.py", {}, PermissionLevel.MEDIUM, "create newfile.py")
        assessment = scanner.assess(intent)
        self.assertEqual(assessment.required_level, PermissionLevel.MEDIUM)

if __name__ == '__main__':
    unittest.main()