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

    def test_snapshot_created_before_execution(self):
        import os
        file_path = os.path.join(self.temp_dir, "to_modify.txt")
        with open(file_path, 'w') as f:
            f.write("original\n")

        # Register a handler that modifies a file
        def modifier(target, params):
            with open(target, 'w') as f:
                f.write("new_content\n")
        self.pipeline.register_handler("modify", modifier)

        result = self.pipeline.execute("modify", file_path, {})
        self.assertTrue(result.success)

        # Verify rollback restored original
        self.pipeline.rollback_manager.rollback(f"modify_{file_path}")
        with open(file_path, 'r') as f:
            self.assertEqual(f.read(), "original\n")



    def test_verification_failure_triggers_rollback(self):
        import os
        import tempfile
        file_path = os.path.join(self.temp_dir, "verify_test.txt")
        with open(file_path, 'w') as f:
            f.write("original\n")
        
        def failing_handler(target, params):
            with open(target, 'w') as f:
                f.write("new_content\n")
            raise RuntimeError("Intentional failure")
        
        self.pipeline.register_handler("failing_action", failing_handler)
        result = self.pipeline.execute("failing_action", file_path, {})
        self.assertFalse(result.success)
        
        with open(file_path, 'r') as f:
            self.assertEqual(f.read(), "original\n")


if __name__ == '__main__':
    unittest.main()

    def test_verification_failure_triggers_rollback(self):
        import os
        import tempfile
        file_path = os.path.join(self.temp_dir, "verify_test.txt")
        with open(file_path, 'w') as f:
            f.write("original\n")
        
        def failing_handler(target, params):
            with open(target, 'w') as f:
                f.write("new_content\n")
            raise RuntimeError("Intentional failure")
        
        self.pipeline.register_handler("failing_action", failing_handler)
        result = self.pipeline.execute("failing_action", file_path, {})
        self.assertFalse(result.success)
        
        with open(file_path, 'r') as f:
            self.assertEqual(f.read(), "original\n")
