import unittest, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core_runtime.approval_gate import ApprovalGate, PromotionRisk

class TestApprovalGate(unittest.TestCase):
    def test_promotion_risk_enum_exists(self):
        self.assertTrue(hasattr(PromotionRisk, 'LOW'))
        self.assertTrue(hasattr(PromotionRisk, 'MEDIUM'))
        self.assertTrue(hasattr(PromotionRisk, 'HIGH'))

    def test_init_injects_dependencies(self):
        ag = ApprovalGate(logger=None)
        self.assertIsNotNone(ag._risk_scanner)
        self.assertIsNotNone(ag._approval_queue)

    def test_score_promotion_low_for_small_changes(self):
        ag = ApprovalGate(logger=None)
        self.assertEqual(ag.score_promotion([], sandbox_path="/tmp/small"), PromotionRisk.LOW)

    def test_score_promotion_high_for_protected_paths(self):
        ag = ApprovalGate(logger=None)
        self.assertEqual(ag.score_promotion([{"file": ".env", "type": "modify"}], sandbox_path="/tmp/test"), PromotionRisk.HIGH)

    def test_score_promotion_medium_for_deletes(self):
        ag = ApprovalGate(logger=None)
        self.assertEqual(ag.score_promotion([{"file": "src/utils.py", "type": "delete"}], sandbox_path="/tmp/test"), PromotionRisk.MEDIUM)

    def test_request_auto_approve_low_risk(self):
        ag = ApprovalGate(logger=None)
        result = ag.request_promotion_approval("sbox-1", "temp", "test", PromotionRisk.LOW)
        self.assertTrue(result["auto_approved"])

    def test_request_queues_high_risk(self):
        ag = ApprovalGate(logger=None)
        result = ag.request_promotion_approval("sbox-2", "test", "live", PromotionRisk.HIGH)
        self.assertFalse(result["auto_approved"])

    def test_is_approved_false_for_unapproved(self):
        ag = ApprovalGate(logger=None)
        ag.request_promotion_approval("sbox-3", "temp", "test", PromotionRisk.HIGH)
        self.assertFalse(ag.is_approved("sbox-3"))

    def test_is_approved_true_after_manual_approve(self):
        ag = ApprovalGate(logger=None)
        ag.request_promotion_approval("sbox-4", "temp", "test", PromotionRisk.HIGH)
        ag._approval_queue.approve("promotion_sbox-4_temp_test")
        self.assertTrue(ag.is_approved("sbox-4"))

if __name__ == "__main__": unittest.main()