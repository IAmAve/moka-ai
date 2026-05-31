import unittest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core_runtime.image_approval_gate import ImageApprovalGate, GenerationRisk
from core_runtime.hardware_scanner import HardwareProfile


class TestImageApprovalGate(unittest.TestCase):
    def setUp(self):
        self.gate = ImageApprovalGate(logger=None)

    def test_low_risk_on_small_workflow(self):
        hw = HardwareProfile(gpu_model="RTX 4090", vram_gb=24.0, system_ram_gb=32.0,
                              available_vram_gb=24.0, compute_capability="8.9")
        wf = {
            "nodes": [
                {"id": 4, "type": "KSampler", "attrs": {"steps": 50}},
            ]
        }
        risk = self.gate.score_generation(wf, hw)
        self.assertEqual(risk, GenerationRisk.LOW)

    def test_medium_risk_on_oversized_steps(self):
        """Steps well over 8GB tier limit (100) triggers MEDIUM risk."""
        hw = HardwareProfile(gpu_model="RTX 4090", vram_gb=8.0, system_ram_gb=32.0,
                              available_vram_gb=8.0, compute_capability="8.9")
        wf = {
            "nodes": [
                {"id": 4, "type": "KSampler", "attrs": {"steps": 500}},
            ]
        }
        risk = self.gate.score_generation(wf, hw)
        self.assertEqual(risk, GenerationRisk.MEDIUM)

    def test_request_approval_low_auto_approves(self):
        result = self.gate.request_approval("req1", "test", GenerationRisk.LOW)
        self.assertTrue(result["auto_approved"])
        self.assertTrue(self.gate.is_approved("req1"))

    def test_request_approval_high_queues(self):
        result = self.gate.request_approval("req2", "test", GenerationRisk.HIGH)
        self.assertFalse(result["auto_approved"])
        # Not auto-approved - relies on approval queue


if __name__ == "__main__":
    unittest.main()