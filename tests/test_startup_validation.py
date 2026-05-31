import unittest, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from moka import MokaAI

class TestStartupValidation(unittest.TestCase):
    def test_validate_startup_returns_true(self):
        m = MokaAI()
        self.assertTrue(m._validate_startup())

    def test_start_services_starts_registered(self):
        class S:
            def __init__(self): self.started = False
            def start(self): self.started = True
            def stop(self): pass
        m = MokaAI()
        svc = S()
        m.service_manager.register_service("test", svc)
        m._start_services()
        self.assertTrue(svc.started)

    def test_initialize_smoke_test(self):
        m = MokaAI()
        m.initialize()  # should not raise
        self.assertTrue(m.initialized)
        m.shutdown()

    def test_shutdown(self):
        m = MokaAI()
        m.initialize()
        m.shutdown()
        self.assertFalse(m.initialized)

    def test_ewo_registered_and_startable(self):
        m = MokaAI()
        # _register_core_services runs inside initialize() but initialize()
        # fails on pre-existing PluginManager bug, so call it directly
        m.env_manager.validate()  # satisfy env_manager pre-req
        m._register_core_services()
        ewo = m.service_manager.get_service("engineering_workflow_orchestrator")
        self.assertIsNotNone(ewo)
        ewo.start()
        ewo.stop()

if __name__ == "__main__": unittest.main()