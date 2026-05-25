from dataclasses import dataclass
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from enum import Enum
from .permission_levels import PermissionLevel

class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"

@dataclass
class PendingApproval:
    approval_id: str
    action: str
    description: str
    level: PermissionLevel
    requested_at: datetime
    expires_at: datetime
    status: ApprovalStatus = ApprovalStatus.PENDING

class ApprovalQueue:
    def __init__(self, timeout_seconds: int = 60, logger=None):
        self.timeout_seconds = timeout_seconds
        self._logger = logger
        self._log = logger.info if logger else lambda m: None
        self._pending: Dict[str, PendingApproval] = {}

    def requires_approval(self, level: PermissionLevel) -> bool:
        return level in [PermissionLevel.DANGEROUS, PermissionLevel.SYSTEM]

    def request_approval(self, action_id: str, description: str, level: PermissionLevel) -> PendingApproval:
        now = datetime.now()
        approval = PendingApproval(
            approval_id=action_id,
            action=action_id,
            description=description,
            level=level,
            requested_at=now,
            expires_at=now + timedelta(seconds=self.timeout_seconds),
            status=ApprovalStatus.PENDING
        )
        self._pending[action_id] = approval
        return approval

    def approve(self, action_id: str) -> bool:
        if action_id in self._pending:
            self._pending[action_id].status = ApprovalStatus.APPROVED
            self._log(f"Approval granted for action '{action_id}'")
            return True
        return False

    def deny(self, action_id: str) -> bool:
        if action_id in self._pending:
            self._pending[action_id].status = ApprovalStatus.DENIED
            self._log(f"Approval denied for action '{action_id}'")
            return True
        return False

    def is_pending(self, action_id: str) -> bool:
        if action_id not in self._pending:
            return False
        approval = self._pending[action_id]
        if datetime.now() > approval.expires_at:
            approval.status = ApprovalStatus.EXPIRED
            return False
        return approval.status == ApprovalStatus.PENDING

    def is_approved(self, action_id: str) -> bool:
        if action_id in self._pending:
            return self._pending[action_id].status == ApprovalStatus.APPROVED
        return False

    def get_pending(self) -> List[PendingApproval]:
        self._cleanup_expired()
        return [a for a in self._pending.values() if a.status == ApprovalStatus.PENDING]

    def _cleanup_expired(self):
        now = datetime.now()
        for approval in self._pending.values():
            if approval.status == ApprovalStatus.PENDING and now > approval.expires_at:
                approval.status = ApprovalStatus.EXPIRED