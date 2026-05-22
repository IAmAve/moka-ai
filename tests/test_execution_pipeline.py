import unittest
import sys
import os
import tempfile
import shutil
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from safety.execution_pipeline import ExecutionPipeline, ExecutionResult
from safety.emergency_stop import EmergencyStop
from safety.permission_levels import PermissionLevel

class TestExecutionPipeline(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.pipeline = ExecutionPipeline(base_path=self.temp_dir)
        EmergencyStop._instance = None
        EmergencyStop().reset()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_safe_action_executes(self):
        result = self.pipeline.execute("read", "config.py", {})
        self.assertTrue(result.success)
        self.assertFalse(result.blocked)
        self.assertFalse(result.requires_approval)

    def test_dangerous_action_requires_approval(self):
        result = self.pipeline.execute("delete", "temp.txt", {})
        self.assertTrue(result.requires_approval)

    def test_blocked_pattern_returns_blocked(self):
        result = self.pipeline.execute("execute", "rm -rf /", {})
        self.assertTrue(result.blocked)
        self.assertIn("Blocked", result.error)

    def test_emergency_stop_blocks_execution(self):
        EmergencyStop().trigger()
        result = self.pipeline.execute("read", "test.txt", {})
        self.assertTrue(result.blocked)
        self.assertEqual(result.error, "Emergency stop active")

    def test_approval_then_execution(self):
        result = self.pipeline.execute("delete", "temp.txt", {})
        self.assertTrue(result.requires_approval)
        action_id = result.action_id
        approved = self.pipeline.approve(action_id)
        self.assertTrue(approved)

if __name__ == '__main__':
    unittest.main()