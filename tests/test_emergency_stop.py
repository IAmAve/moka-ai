import unittest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from safety.emergency_stop import EmergencyStop, EmergencyStopEvent

class TestEmergencyStop(unittest.TestCase):
    def setUp(self):
        # Reset singleton for each test
        EmergencyStop._instance = None

    def test_stop_sets_flag(self):
        stop = EmergencyStop()
        stop.trigger()
        self.assertTrue(stop.is_stopped())

    def test_reset_clears_flag(self):
        stop = EmergencyStop()
        stop.trigger()
        stop.reset()
        self.assertFalse(stop.is_stopped())

    def test_callback_invoked(self):
        stop = EmergencyStop()
        callback_invoked = []
        def on_stop(event):
            callback_invoked.append(True)
        stop.register_callback(on_stop)
        stop.trigger()
        self.assertEqual(len(callback_invoked), 1)

    def test_clears_on_reset(self):
        stop = EmergencyStop()
        stop.trigger()
        self.assertTrue(stop.is_stopped())
        stop.reset()
        self.assertFalse(stop.is_stopped())

if __name__ == '__main__':
    unittest.main()