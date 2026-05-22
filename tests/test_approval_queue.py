import unittest
import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from safety.approval_queue import ApprovalQueue, PendingApproval, ApprovalStatus
from safety.permission_levels import PermissionLevel

class TestApprovalQueue(unittest.TestCase):
    def setUp(self):
        self.queue = ApprovalQueue(timeout_seconds=2)

    def test_queue_requires_approval_for_dangerous(self):
        result = self.queue.requires_approval(PermissionLevel.DANGEROUS)
        self.assertTrue(result)

    def test_queue_allows_safe_without_approval(self):
        result = self.queue.requires_approval(PermissionLevel.SAFE)
        self.assertFalse(result)

    def test_request_approval_adds_to_queue(self):
        self.queue.request_approval("action-1", "delete file", PermissionLevel.DANGEROUS)
        self.assertEqual(len(self.queue.get_pending()), 1)

    def test_approval_timeout(self):
        self.queue.request_approval("action-timeout", "test", PermissionLevel.DANGEROUS)
        time.sleep(3)
        self.assertFalse(self.queue.is_pending("action-timeout"))

    def test_approve_marks_approved(self):
        self.queue.request_approval("action-2", "test", PermissionLevel.DANGEROUS)
        self.queue.approve("action-2")
        self.assertTrue(self.queue.is_approved("action-2"))

    def test_deny_marks_denied(self):
        self.queue.request_approval("action-3", "test", PermissionLevel.DANGEROUS)
        self.queue.deny("action-3")
        pending = self.queue.get_pending()
        action_ids = [p.approval_id for p in pending]
        self.assertNotIn("action-3", action_ids)

if __name__ == '__main__':
    unittest.main()