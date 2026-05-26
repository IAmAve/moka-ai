import unittest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core_runtime.image_runtime_manager import ImageRuntimeManager, GenerationStatus, GenerationRequest
from core_runtime.image_approval_gate import GenerationRisk
from core_runtime.hardware_scanner import HardwareProfile


class TestImageRuntimeManager(unittest.TestCase):
    def setUp(self):
        self.mgr = ImageRuntimeManager(logger=None)

    def test_generate_returns_request(self):
        req = self.mgr.generate("A sunset over mountains")
        self.assertIsInstance(req, GenerationRequest)
        self.assertIn("gen_", req.request_id)
        self.assertEqual(req.intent, "A sunset over mountains")
        self.assertIn(req.risk, GenerationRisk)

    def test_generate_low_risk_auto_queued(self):
        req = self.mgr.generate("A simple portrait")
        self.assertEqual(req.status, GenerationStatus.QUEUED)

    def test_approve_pending_request(self):
        """approve() transitions a PENDING request (HIGH risk) to QUEUED."""
        req = self.mgr.generate("A massive ultra-detailed 4K landscape with mountains and forests at 4096x4096 pixels and epic composition")
        # This intent should be HIGH risk: large resolution would exceed limits if resolution were high
        # But for LOW-risk (auto-QUEUED): verify approve returns True anyway
        # For this test: create a HIGH-risk pending request directly
        from core_runtime.image_approval_gate import GenerationRisk
        req = self.mgr._pending_requests[req.request_id]
        req.status = GenerationStatus.PENDING
        req.risk = GenerationRisk.HIGH
        pending_id = req.request_id
        ok = self.mgr.approve(pending_id)
        self.assertTrue(ok)
        self.assertEqual(req.status, GenerationStatus.QUEUED)

    def test_reject_cancels_request(self):
        req = self.mgr.generate("Test image")
        pending_id = req.request_id
        ok = self.mgr.reject(pending_id)
        self.assertTrue(ok)
        self.assertEqual(req.status, GenerationStatus.CANCELLED)

    def test_approve_unknown_returns_false(self):
        ok = self.mgr.approve("nonexistent")
        self.assertFalse(ok)

    def test_reject_unknown_returns_false(self):
        ok = self.mgr.reject("nonexistent")
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()