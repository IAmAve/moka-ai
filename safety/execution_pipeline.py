from dataclasses import dataclass
from typing import Any, Dict, Optional, Callable
import os
from .permission_levels import PermissionManager, PermissionLevel
from .intent_detector import IntentDetector
from .risk_scanner import RiskScanner
from .approval_queue import ApprovalQueue
from .rollback_manager import RollbackManager
from .emergency_stop import EmergencyStop
from core.event_bus import EventBus

@dataclass
class ExecutionResult:
    success: bool
    blocked: bool = False
    requires_approval: bool = False
    error: Optional[str] = None
    action_id: Optional[str] = None

class ExecutionPipeline:
    def __init__(self, base_path: str = ".safety_snapshots", event_bus: EventBus = None):
        self.permission_manager = PermissionManager()
        self.intent_detector = IntentDetector()
        self.risk_scanner = RiskScanner(self.permission_manager)
        self.approval_queue = ApprovalQueue(
            timeout_seconds=self.permission_manager.get_approval_timeout()
        )
        self.rollback_manager = RollbackManager(base_path)
        self.emergency_stop = EmergencyStop()
        self._execution_handlers: Dict[str, Callable] = {}
        self.event_bus = event_bus or EventBus()

    def execute(self, action: str, target: str, params: Dict[str, Any]) -> ExecutionResult:
        if self.emergency_stop.is_stopped():
            return ExecutionResult(success=False, blocked=True, error="Emergency stop active")

        intent = self.intent_detector.detect(f"{action} {target}")
        assessment = self.risk_scanner.assess(intent)

        if assessment.blocked:
            self.event_bus.publish('safety.action_blocked', {
                'action': action,
                'target': target,
                'risk_factors': assessment.risk_factors
            })
            return ExecutionResult(success=False, blocked=True, error=f"Blocked: {', '.join(assessment.risk_factors)}")

        if self.approval_queue.requires_approval(assessment.required_level):
            self.event_bus.publish('safety.approval_required', {
                'action_id': f"{action}_{target}",
                'action': action,
                'target': target,
                'level': assessment.required_level.value
            })
            self.approval_queue.request_approval(
                f"{action}_{target}",
                f"{action} on {target}",
                assessment.required_level
            )
            return ExecutionResult(success=False, requires_approval=True, action_id=f"{action}_{target}")

        exec_result = self._execute_action(action, target, params)
        return self._verify_execution(exec_result, action, target)

    def _verify_execution(self, result: ExecutionResult, action: str, target: str) -> ExecutionResult:
        """Verify execution outcome and trigger rollback on failure."""
        if not result.success and result.action_id:
            self.rollback_manager.rollback(result.action_id)
        return result

    def _execute_action(self, action: str, target: str, params: Dict[str, Any]) -> ExecutionResult:
        # Create snapshot before execution
        target_basename = os.path.basename(target).replace(".", "_")
        action_id = f"{action}_{target_basename}"
        self.rollback_manager.create_snapshot(action_id, target)

        handler = self._execution_handlers.get(action)
        if handler:
            try:
                handler(target, params)
                return ExecutionResult(success=True, action_id=action_id)
            except Exception as e:
                # Verification will trigger rollback
                return ExecutionResult(success=False, error=str(e), action_id=action_id)
        return ExecutionResult(success=True, action_id=action_id)

    def register_handler(self, action: str, handler: Callable):
        self._execution_handlers[action] = handler

    def approve(self, action_id: str) -> bool:
        return self.approval_queue.approve(action_id)

    def deny(self, action_id: str) -> bool:
        return self.approval_queue.deny(action_id)