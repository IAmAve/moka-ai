"""
Approval Gate — risk-scored promotion approval for Engineering Workflow Orchestrator.

LOW risk: auto-approved, promotion proceeds without human.
MEDIUM/HIGH risk: queued via ApprovalQueue for human review.
"""

from enum import Enum

from safety.approval_queue import ApprovalQueue
from safety.permission_levels import PermissionLevel


class PromotionRisk(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ApprovalGate:
    PROMOTION_TIMEOUT_SECONDS = 300  # 5 minute timeout for human approval

    def __init__(self, risk_scanner=None, approval_queue=None, logger=None):
        from safety.risk_scanner import RiskScanner
        self._risk_scanner = risk_scanner or RiskScanner()
        self._approval_queue = approval_queue or ApprovalQueue()
        self._logger = logger
        self._log = logger.info if logger else lambda m: None
        self._auto_approved = set()  # set of approval_ids auto-approved by us

    def score_promotion(self, changes, sandbox_path="") -> PromotionRisk:
        if not changes:
            return PromotionRisk.LOW
        risk_sum = 0
        protected_patterns = [".env", "credentials", "id_rsa", "password",
                              ".key", "secrets", "config/prod"]
        for ch in changes:
            f = ch.get("file", "")
            if any(p in f for p in protected_patterns):
                risk_sum += 5
            elif ch.get("type") == "delete":
                risk_sum += 2
            elif len(f) > 200:
                risk_sum += 1
        if risk_sum >= 5:
            return PromotionRisk.HIGH
        elif risk_sum >= 2:
            return PromotionRisk.MEDIUM
        return PromotionRisk.LOW

    def request_promotion_approval(
        self, sandbox_id: str, from_env: str, to_env: str, risk: PromotionRisk
    ):
        approval_id = f"promotion_{sandbox_id}_{from_env}_{to_env}"
        if risk == PromotionRisk.LOW:
            self._auto_approved.add(approval_id)
            self._log(f"Auto-approved promotion {approval_id}")
            return {"approval_id": approval_id, "auto_approved": True}
        else:
            self._approval_queue.request_approval(
                approval_id,
                f"Promote sandbox {sandbox_id} from {from_env} to {to_env}",
                PermissionLevel.MEDIUM if risk == PromotionRisk.MEDIUM
                    else PermissionLevel.DANGEROUS,
            )
            return {"approval_id": approval_id, "auto_approved": False}

    def is_approved(self, sandbox_id: str) -> bool:
        for from_env in ["temp", "test"]:
            for to_env in ["test", "live"]:
                aid = f"promotion_{sandbox_id}_{from_env}_{to_env}"
                if aid in self._auto_approved or self._approval_queue.is_approved(aid):
                    return True
        return False

    def is_promotion_approved(self, sandbox_id: str, from_env: str, to_env: str) -> bool:
        """Check if a specific promotion (from_env -> to_env) is approved."""
        aid = f"promotion_{sandbox_id}_{from_env}_{to_env}"
        return aid in self._auto_approved or self._approval_queue.is_approved(aid)