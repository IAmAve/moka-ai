import unittest, sys, os, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core_runtime.engineering_workflow_orchestrator import (
    EngineeringWorkflowOrchestrator, WorkflowSpec, PipelineStage
)
from core_runtime.sandbox_manager import Sandbox, SandboxEnvironment, SandboxStatus

class TestEWO(unittest.TestCase):
    def _mock_sandbox(self):
        return Sandbox(
            sandbox_id="fake-id", workflow_id="fake-wf",
            environment=SandboxEnvironment.TEMP,
            worktree_path=tempfile.gettempdir() + "/fake_worktree",
            container_id=None, status=SandboxStatus.READY
        )

    def test_workflow_spec_dataclass(self):
        spec = WorkflowSpec(
            intent="add login form",
            file_changes=[],
            dependencies=[],
            plan={}
        )
        self.assertEqual(spec.intent, "add login form")
        self.assertEqual(spec.status, "pending")

    def test_pipeline_stage_enum_has_all_stages(self):
        self.assertTrue(hasattr(PipelineStage, 'ANALYZE'))
        self.assertTrue(hasattr(PipelineStage, 'CREATE'))
        self.assertTrue(hasattr(PipelineStage, 'INSTALL'))
        self.assertTrue(hasattr(PipelineStage, 'CODE'))
        self.assertTrue(hasattr(PipelineStage, 'TEST'))
        self.assertTrue(hasattr(PipelineStage, 'DEBUG'))
        self.assertTrue(hasattr(PipelineStage, 'APPROVAL'))
        self.assertTrue(hasattr(PipelineStage, 'LAUNCH'))

    def test_ewo_inits_with_dependencies(self):
        ewo = EngineeringWorkflowOrchestrator(logger=None)
        self.assertIsNotNone(ewo._sandbox_manager)
        self.assertIsNotNone(ewo._approval_gate)
        self.assertIsNotNone(ewo._debug_loop)
        self.assertIsNotNone(ewo._task_orchestrator)
        self.assertIsNotNone(ewo._event_bus)

    def test_run_returns_workflow_result(self):
        ewo = EngineeringWorkflowOrchestrator(logger=None)
        ewo.analyze = lambda intent: WorkflowSpec(intent=intent, file_changes=[], dependencies=[], plan={})
        ewo._sandbox_manager.create_sandbox = lambda wid: "fake-id"
        ewo._sandbox_manager.get_sandbox = lambda sid: self._mock_sandbox()
        ewo.test = lambda spec, sid: True
        result = ewo.run("add user auth")
        self.assertEqual(result.status, "success")
        self.assertEqual(result.sandbox_id, "fake-id")

    def test_run_stops_at_debug_if_exhausted(self):
        ewo = EngineeringWorkflowOrchestrator(logger=None)
        ewo.analyze = lambda intent: WorkflowSpec(intent=intent, file_changes=[], dependencies=[], plan={})
        ewo._sandbox_manager.create_sandbox = lambda wid: "fake-id"
        ewo._sandbox_manager.get_sandbox = lambda sid: self._mock_sandbox()
        ewo.test = lambda spec, sid: False  # force test to fail → debug loop
        ewo._execute_debug = lambda sb_id, spec: {"exhausted": True}
        result = ewo.run("add login")
        self.assertEqual(result.stage, PipelineStage.DEBUG)
        self.assertTrue(result.debug_exhausted)
        self.assertIsNotNone(ewo._event_bus)

if __name__ == "__main__":
    unittest.main()