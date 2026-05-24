"""
Task Orchestration Module for MOKA AI Core Runtime

Handles multi-step task workflows with step tracking, state management,
and integration with TaskQueue/WorkerManager.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime


class OrchestrationStatus(Enum):
    """Status of an orchestrated workflow."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class StepStatus(Enum):
    """Status of an individual step."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class WorkflowStep:
    """Represents a single step in an orchestrated workflow."""
    name: str
    handler: Callable[[Dict[str, Any]], Any]
    description: str = ""
    required: bool = True
    rollback_handler: Optional[Callable[[], None]] = None
    status: StepStatus = StepStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class OrchestratedWorkflow:
    """Represents a complete orchestrated workflow."""
    workflow_id: str
    name: str
    steps: List[WorkflowStep]
    status: OrchestrationStatus = OrchestrationStatus.PENDING
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


class TaskOrchestrator:
    """Orchestrates multi-step workflows with state management and rollback."""

    def __init__(self):
        self._workflows: Dict[str, OrchestratedWorkflow] = {}
        self._workflow_stack: List[str] = []
        self._execution_history: List[Dict[str, Any]] = []

    def create_workflow(
        self,
        workflow_id: str,
        name: str,
        steps: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
    ) -> OrchestratedWorkflow:
        """Create a new orchestrated workflow from step definitions."""
        if workflow_id in self._workflows:
            raise ValueError(f"Workflow '{workflow_id}' already exists")

        workflow_steps = []
        for step_def in steps:
            handler = step_def.get("handler")
            if not callable(handler):
                raise ValueError(f"Step '{step_def.get('name')}' must have a callable handler")

            workflow_steps.append(
                WorkflowStep(
                    name=step_def["name"],
                    handler=handler,
                    description=step_def.get("description", ""),
                    required=step_def.get("required", True),
                    rollback_handler=step_def.get("rollback_handler"),
                )
            )

        workflow = OrchestratedWorkflow(
            workflow_id=workflow_id,
            name=name,
            steps=workflow_steps,
            context=context or {},
        )
        self._workflows[workflow_id] = workflow
        return workflow

    def execute_workflow(
        self,
        workflow_id: str,
        initial_context: Optional[Dict[str, Any]] = None,
        stop_on_failure: bool = True,
    ) -> OrchestratedWorkflow:
        """Execute a workflow by ID, returning the completed workflow."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow '{workflow_id}' not found")

        if workflow.status == OrchestrationStatus.RUNNING:
            raise RuntimeError(f"Workflow '{workflow_id}' is already running")

        if initial_context:
            workflow.context.update(initial_context)

        workflow.status = OrchestrationStatus.RUNNING
        self._workflow_stack.append(workflow_id)

        try:
            for step in workflow.steps:
                if workflow.status == OrchestrationStatus.FAILED and stop_on_failure:
                    break

                self._execute_step(workflow, step)

            completed_count = sum(
                1 for s in workflow.steps if s.status == StepStatus.COMPLETED
            )
            failed_count = sum(
                1 for s in workflow.steps if s.status == StepStatus.FAILED
            )

            if failed_count > 0 and stop_on_failure:
                workflow.status = OrchestrationStatus.FAILED
            elif completed_count == len(workflow.steps):
                workflow.status = OrchestrationStatus.COMPLETED
            else:
                workflow.status = OrchestrationStatus.PAUSED

        except Exception as e:
            workflow.status = OrchestrationStatus.FAILED
            raise

        finally:
            if self._workflow_stack and self._workflow_stack[-1] == workflow_id:
                self._workflow_stack.pop()

            workflow.completed_at = datetime.now()
            self._record_execution(workflow)

        return workflow

    def _execute_step(self, workflow: OrchestratedWorkflow, step: WorkflowStep) -> None:
        """Execute a single step within a workflow."""
        step.status = StepStatus.RUNNING
        step.started_at = datetime.now()

        try:
            step.result = step.handler(workflow.context)
            step.status = StepStatus.COMPLETED
        except Exception as e:
            step.error = str(e)
            step.status = StepStatus.FAILED

            if step.required:
                workflow.status = OrchestrationStatus.FAILED
                self._rollback_workflow(workflow, step)

        finally:
            step.completed_at = datetime.now()

    def _rollback_workflow(
        self, workflow: OrchestratedWorkflow, failed_step: WorkflowStep
    ) -> None:
        """Rollback a workflow to before the failed step."""
        for step in workflow.steps:
            if step.status == StepStatus.COMPLETED and step.rollback_handler:
                try:
                    step.rollback_handler()
                except Exception:
                    pass

        workflow.status = OrchestrationStatus.ROLLED_BACK

    def pause_workflow(self, workflow_id: str) -> bool:
        """Pause a running workflow."""
        workflow = self._workflows.get(workflow_id)
        if not workflow or workflow.status != OrchestrationStatus.RUNNING:
            return False
        workflow.status = OrchestrationStatus.PAUSED
        return True

    def resume_workflow(self, workflow_id: str) -> OrchestratedWorkflow:
        """Resume a paused workflow from where it left off."""
        workflow = self._workflows.get(workflow_id)
        if not workflow or workflow.status != OrchestrationStatus.PAUSED:
            raise ValueError(f"Workflow '{workflow_id}' is not paused")

        return self.execute_workflow(workflow_id, stop_on_failure=True)

    def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel and rollback a workflow."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return False

        if workflow.status == OrchestrationStatus.RUNNING:
            self._rollback_workflow(workflow, workflow.steps[-1])

        workflow.status = OrchestrationStatus.FAILED
        workflow.completed_at = datetime.now()
        return True

    def get_workflow(self, workflow_id: str) -> Optional[OrchestratedWorkflow]:
        """Get a workflow by ID."""
        return self._workflows.get(workflow_id)

    def list_workflows(self) -> List[Dict[str, str]]:
        """List all registered workflows with their status."""
        return [
            {"workflow_id": w.workflow_id, "name": w.name, "status": w.status.value}
            for w in self._workflows.values()
        ]

    def get_workflow_history(
        self, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get execution history for workflows."""
        return self._execution_history[-limit:]

    def _record_execution(self, workflow: OrchestratedWorkflow) -> None:
        """Record a workflow execution in history."""
        self._execution_history.append({
            "workflow_id": workflow.workflow_id,
            "name": workflow.name,
            "status": workflow.status.value,
            "completed_at": workflow.completed_at.isoformat() if workflow.completed_at else None,
            "step_results": [
                {"name": s.name, "status": s.status.value, "error": s.error}
                for s in workflow.steps
            ],
        })

    def clear_workflow(self, workflow_id: str) -> bool:
        """Remove a workflow from the orchestrator."""
        if workflow_id in self._workflows:
            del self._workflows[workflow_id]
            return True
        return False