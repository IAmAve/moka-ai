import unittest, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.event_bus import EventBus
from core.health_monitor import HealthMonitor

class TestHM(unittest.TestCase):
    def test_register(self):
        hm = HealthMonitor(EventBus()); hm.register_component("svc", lambda: True)
        self.assertIn("svc", hm._components)
    def test_all_healthy(self):
        hm = HealthMonitor(EventBus()); hm.register_component("a", lambda: True); hm.register_component("b", lambda: True)
        self.assertEqual(hm.check_health()["status"], "ok")
    def test_one_fails(self):
        hm = HealthMonitor(EventBus()); hm.register_component("good", lambda: True); hm.register_component("bad", lambda: False)
        self.assertEqual(hm.check_health()["status"], "degraded")
    def test_all_fail(self):
        hm = HealthMonitor(EventBus()); hm.register_component("x", lambda: False)
        self.assertEqual(hm.check_health()["status"], "critical")

if __name__ == "__main__": unittest.main()