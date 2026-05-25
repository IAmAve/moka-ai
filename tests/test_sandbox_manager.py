import unittest, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core_runtime.sandbox_manager import SandboxManager, SandboxStatus, SandboxEnvironment

class TestSandboxManager(unittest.TestCase):
    def setUp(self):
        self.sm = SandboxManager(base_path="d:/tmp/moka_sandboxes", logger=None)

    def test_sandbox_status_enum_exists(self):
        self.assertTrue(hasattr(SandboxStatus, 'PENDING'))
        self.assertTrue(hasattr(SandboxStatus, 'READY'))
        self.assertTrue(hasattr(SandboxStatus, 'DESTROYED'))

    def test_init_stores_base_path(self):
        self.assertEqual(self.sm.base_path, "d:/tmp/moka_sandboxes")

    def test_create_sandbox_returns_sandbox_id(self):
        sid = self.sm.create_sandbox("wf-001")
        self.assertIsInstance(sid, str)
        self.assertTrue(len(sid) > 0)

    def test_create_sandbox_creates_worktree_dir(self):
        sid = self.sm.create_sandbox("wf-002")
        import os
        wt_path = os.path.join(self.sm.base_path, f"worktree_{sid}")
        self.assertTrue(os.path.isdir(wt_path))

    def test_sandbox_environments_enum_has_temp_test_live(self):
        self.assertTrue(hasattr(SandboxEnvironment, 'TEMP'))
        self.assertTrue(hasattr(SandboxEnvironment, 'TEST'))
        self.assertTrue(hasattr(SandboxEnvironment, 'LIVE'))

    def test_destroy_sandbox_removes_worktree(self):
        import os
        sid = self.sm.create_sandbox("wf-003")
        wt_path = os.path.join(self.sm.base_path, f"worktree_{sid}")
        self.assertTrue(os.path.isdir(wt_path))
        self.sm.destroy_sandbox(sid)
        self.assertFalse(os.path.isdir(wt_path))

    def test_promote_environment_advances(self):
        sid = self.sm.create_sandbox("wf-004")
        sandbox = self.sm.get_sandbox(sid)
        self.assertEqual(sandbox.environment, SandboxEnvironment.TEMP)
        next_env = self.sm.promote_environment(sid)
        self.assertEqual(next_env, SandboxEnvironment.TEST)

if __name__ == "__main__":
    unittest.main()