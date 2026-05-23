import unittest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.service_manager import ServiceManager, ServiceStatus

class TestServiceManager(unittest.TestCase):
    def setUp(self):
        self.sm = ServiceManager()

    def test_register_and_get_service(self):
        class DummyService:
            def start(self): pass
            def stop(self): pass
        dummy = DummyService()
        self.sm.register_service("dummy", dummy)
        retrieved = self.sm.get_service("dummy")
        self.assertIs(retrieved, dummy)

    def test_get_service_returns_none_for_missing(self):
        result = self.sm.get_service("nonexistent")
        self.assertIsNone(result)

    def test_service_lifecycle(self):
        class LifecycleService:
            def __init__(self):
                self.started = False
                self.stopped = False
            def start(self): self.started = True
            def stop(self): self.stopped = True
        svc = LifecycleService()
        self.sm.register_service("lifecycle", svc)
        self.sm.start_service("lifecycle")
        self.assertTrue(svc.started)
        self.assertEqual(self.sm.get_status("lifecycle"), ServiceStatus.RUNNING)
        self.sm.stop_service("lifecycle")
        self.assertTrue(svc.stopped)
        self.assertEqual(self.sm.get_status("lifecycle"), ServiceStatus.STOPPED)

    def test_get_status_returns_unknown_for_missing(self):
        self.assertEqual(self.sm.get_status("nonexistent"), ServiceStatus.UNKNOWN)

    def test_start_service_sets_failed_on_exception(self):
        class FailingService:
            def start(self):
                raise RuntimeError("boom")
        svc = FailingService()
        self.sm.register_service("fail", svc)
        result = self.sm.start_service("fail")
        self.assertFalse(result)
        self.assertEqual(self.sm.get_status("fail"), ServiceStatus.FAILED)

    def test_stop_service_sets_failed_on_exception(self):
        class FailingService:
            def __init__(self):
                self.started = False
            def start(self):
                self.started = True
            def stop(self):
                raise RuntimeError("boom")
        svc = FailingService()
        self.sm.register_service("fail", svc)
        self.sm.start_service("fail")  # first starts
        result = self.sm.stop_service("fail")
        self.assertFalse(result)
        self.assertEqual(self.sm.get_status("fail"), ServiceStatus.FAILED)

    def test_list_services(self):
        self.sm.register_service("s1", object())
        self.sm.register_service("s2", object())
        listed = self.sm.list_services()
        self.assertIn("s1", listed)
        self.assertIn("s2", listed)

if __name__ == '__main__':
    unittest.main()