"""ImageApprovalGate - risk scoring for image generation requests."""

from __future__ import annotations
from enum import Enum


class GenerationRisk(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ImageApprovalGate:
    VRAM_LIMITS = {
        4:  {"max_resolution": 512,  "max_steps": 50,  "max_concurrent": 1},
        8:  {"max_resolution": 1024, "max_steps": 100, "max_concurrent": 2},
        16: {"max_resolution": 2048, "max_steps": 200, "max_concurrent": 3},
        24: {"max_resolution": 3072, "max_steps": 500, "max_concurrent": 4},
    }

    def __init__(self, approval_queue=None, logger=None):
        from safety.approval_queue import ApprovalQueue
        self._approval_queue = approval_queue or ApprovalQueue()
        self._logger = logger
        self._log = logger.info if logger else lambda m: None
        self._auto_approved = set()

    def _vram_limit(self, vram_gb: float) -> dict:
        tiers = sorted(self.VRAM_LIMITS.keys())
        for tier in tiers:
            if vram_gb <= tier:
                return self.VRAM_LIMITS[tier]
        return self.VRAM_LIMITS[tiers[-1]]

    def _estimate_vram(self, workflow_json: dict) -> float:
        nodes = {n["id"]: n for n in workflow_json.get("nodes", [])}
        resolution = 512
        for node in nodes.values():
            if node.get("type") == "EmptyLatentImage":
                w = node.get("attrs", {}).get("width", 512)
                h = node.get("attrs", {}).get("height", 512)
                resolution = max(w, h)
        estimated_gb = (resolution / 1024.0) ** 2 * 4.0
        return estimated_gb

    def _estimate_steps(self, workflow_json: dict) -> int:
        for node in workflow_json.get("nodes", []):
            if node.get("type") == "KSampler":
                return node.get("attrs", {}).get("steps", 50)
        return 50

    def score_generation(self, workflow_json: dict, hardware_profile) -> GenerationRisk:
        vram_estimate = self._estimate_vram(workflow_json)
        steps = self._estimate_steps(workflow_json)
        limits = self._vram_limit(hardware_profile.vram_gb)
        hw_limit_vram = hardware_profile.vram_gb * 0.8

        risk = 0
        if vram_estimate > hw_limit_vram:
            risk += 5
        if steps > limits["max_steps"]:
            risk += 3
        if vram_estimate > hardware_profile.vram_gb:
            risk += 2

        if risk >= 5:
            return GenerationRisk.HIGH
        elif risk >= 2:
            return GenerationRisk.MEDIUM
        return GenerationRisk.LOW

    def request_approval(self, request_id: str, description: str, risk: GenerationRisk):
        if risk == GenerationRisk.LOW:
            self._auto_approved.add(request_id)
            self._log(f"Auto-approved image request {request_id}")
            return {"approval_id": request_id, "auto_approved": True}
        else:
            from safety.permission_levels import PermissionLevel
            self._approval_queue.request_approval(
                request_id, description,
                PermissionLevel.MEDIUM if risk == GenerationRisk.MEDIUM
                    else PermissionLevel.DANGEROUS
            )
            return {"approval_id": request_id, "auto_approved": False}

    def is_approved(self, request_id: str) -> bool:
        return request_id in self._auto_approved or self._approval_queue.is_approved(request_id)