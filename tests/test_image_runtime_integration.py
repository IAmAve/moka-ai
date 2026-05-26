"""Integration tests for ImageRuntimeManager - tests the full pipeline."""
import unittest, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core_runtime.image_runtime_manager import ImageRuntimeManager, GenerationStatus
from core_runtime.workflow_generator import WorkflowGenerator
from core_runtime.image_approval_gate import GenerationRisk


class TestImageRuntimeIntegration(unittest.TestCase):
    def test_full_pipeline_generate_approve_reject(self):
        mgr = ImageRuntimeManager(logger=None)

        # Generate
        req = mgr.generate("A cyberpunk samurai portrait")
        self.assertIsNotNone(req.request_id)

        # Approve
        ok = mgr.approve(req.request_id)
        self.assertTrue(ok)

        # Reject (create new request)
        req2 = mgr.generate("another image")
        self.assertTrue(mgr.reject(req2.request_id))
        self.assertEqual(req2.status, GenerationStatus.CANCELLED)

    def test_workflow_generator_round_trip(self):
        wg = WorkflowGenerator(logger=None)
        wf = wg.generate("A serene mountain landscape", template_category="default")
        self.assertIn("nodes", wf)
        self.assertTrue(wg.validate(wf))

    def test_risk_scoring_integration(self):
        mgr = ImageRuntimeManager(logger=None)
        req = mgr.generate("A portrait")
        self.assertIn(req.risk, GenerationRisk)


if __name__ == "__main__":
    unittest.main()