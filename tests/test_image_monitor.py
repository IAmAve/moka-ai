import unittest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core_runtime.image_monitor import ImageMonitor


class TestImageMonitor(unittest.TestCase):
    def test_subscribe_stores_status(self):
        m = ImageMonitor(logger=None)
        m.subscribe("prompt_123", "req_abc")
        self.assertIn("prompt_123", m._subscriptions)
        self.assertEqual(m._subscriptions["prompt_123"], "req_abc")

    def test_get_status_returns_stored(self):
        m = ImageMonitor(logger=None)
        m._status["prompt_123"] = {"state": "running", "progress": 50}
        status = m.get_status("prompt_123")
        self.assertEqual(status["state"], "running")
        self.assertEqual(status["progress"], 50)

    def test_get_status_unknown_returns_none(self):
        m = ImageMonitor(logger=None)
        self.assertIsNone(m.get_status("unknown"))

    def test_unsubscribe_clears(self):
        m = ImageMonitor(logger=None)
        m.subscribe("prompt_123", "req_abc")
        m.unsubscribe("prompt_123")
        self.assertNotIn("prompt_123", m._subscriptions)
        self.assertNotIn("prompt_123", m._status)


if __name__ == "__main__":
    unittest.main()