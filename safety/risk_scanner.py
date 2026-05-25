from dataclasses import dataclass
from typing import List
from .permission_levels import PermissionManager, PermissionLevel
from .intent_detector import Intent

@dataclass
class RiskAssessment:
    required_level: PermissionLevel
    risk_factors: List[str]
    blocked: bool

class RiskScanner:
    def __init__(self, permission_manager: PermissionManager = None, logger=None):
        self.permission_manager = permission_manager or PermissionManager()
        self._logger = logger
        self._log = logger.info if logger else lambda m: None

    def assess(self, intent: Intent) -> RiskAssessment:
        risk_factors = []

        if self.permission_manager.is_dangerous_pattern(intent.original_text):
            risk_factors.append("dangerous_pattern")

        if self.permission_manager.is_protected_path(intent.target):
            risk_factors.append("protected_path")

        required_level = intent.suggested_level
        blocked = len(risk_factors) > 0

        if blocked:
            self._log(f"Risk assessment blocked: {risk_factors} for '{intent.action} {intent.target}'")
        return RiskAssessment(
            required_level=required_level,
            risk_factors=risk_factors,
            blocked=blocked
        )