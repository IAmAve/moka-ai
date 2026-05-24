import unittest, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from moka import MokaAI

class TestWiredMokaAI(unittest.TestCase):
    def test_initialized_false_before_init(self):
        m = MokaAI()
        self.assertFalse(m.initialized)

    def test_all_new_modules_created(self):
        m = MokaAI()
        self.assertIsNotNone(m.health_monitor)
        self.assertIsNotNone(m.version_manager)
        self.assertIsNotNone(m.env_manager)
        self.assertIsNotNone(m.telemetry)

    def test_initialize_and_shutdown(self):
        m = MokaAI()
        m.initialize()
        self.assertTrue(m.initialized)
        services = m.service_manager.list_services()
        self.assertIn("plugin_manager", services)
        m.shutdown()
        self.assertFalse(m.initialized)

if __name__ == "__main__": unittest.main()