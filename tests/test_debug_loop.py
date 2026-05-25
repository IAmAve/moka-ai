import unittest, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core_runtime.debug_loop import DebugLoop

class TestDebugLoop(unittest.TestCase):
    def test_debug_loop_init(self):
        dl = DebugLoop(max_attempts=3, logger=None)
        self.assertEqual(dl.max_attempts, 3)

    def test_should_escalate_false_before_limit(self):
        dl = DebugLoop(max_attempts=3, logger=None)
        self.assertFalse(dl.should_escalate(1))
        self.assertFalse(dl.should_escalate(2))

    def test_should_escalate_true_at_limit(self):
        dl = DebugLoop(max_attempts=3, logger=None)
        self.assertTrue(dl.should_escalate(3))

    def test_auto_fix_calls_handler_multiple_times(self):
        dl = DebugLoop(max_attempts=3, logger=None)
        call_count = 0
        def failing_handler():
            nonlocal call_count
            call_count += 1
            return False  # still failing
        result = dl.auto_fix("sb-1", failing_handler, max_attempts=3)
        self.assertEqual(call_count, 3)
        self.assertTrue(result["exhausted"])

    def test_auto_fix_stops_on_success(self):
        dl = DebugLoop(max_attempts=3, logger=None)
        call_count = 0
        def success_handler():
            nonlocal call_count
            call_count += 1
            return call_count >= 2  # succeeds on 2nd try
        result = dl.auto_fix("sb-2", success_handler, max_attempts=3)
        self.assertEqual(call_count, 2)
        self.assertFalse(result["exhausted"])
        self.assertTrue(result["success"])

if __name__ == "__main__":
    unittest.main()