import unittest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from safety.intent_detector import IntentDetector, Intent

class TestIntentDetector(unittest.TestCase):
    def test_detect_read_action(self):
        detector = IntentDetector()
        intent = detector.detect("read the file config.py")
        self.assertEqual(intent.action, "read")
        self.assertIn("config.py", intent.target)

    def test_detect_write_action(self):
        detector = IntentDetector()
        intent = detector.detect("write to config.json")
        self.assertEqual(intent.action, "write")

    def test_detect_delete_action(self):
        detector = IntentDetector()
        intent = detector.detect("delete the temp file")
        self.assertEqual(intent.action, "delete")

    def test_detect_unknown_action_defaults_to_medium(self):
        detector = IntentDetector()
        intent = detector.detect("do something")
        self.assertEqual(intent.suggested_level.value, "medium")

if __name__ == '__main__':
    unittest.main()