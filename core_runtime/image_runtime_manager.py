"""ImageRuntimeManager - ComfyUI workflow orchestration, approval, and monitoring."""

from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from core.event_bus import EventBus
from core.service_manager import ServiceManager
from core_runtime.workflow_generator import WorkflowGenerator
from core_runtime.image_approval_gate import ImageApprovalGate, GenerationRisk
from core_runtime.desktop_runtime_cache import DesktopRuntimeCache


class GenerationStatus(Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class GenerationRequest:
    request_id: str
    intent: str
    workflow_json: dict
    risk: GenerationRisk
    status: GenerationStatus = GenerationStatus.PENDING
    prompt_id: Optional[str] = None
    error: Optional[str] = None


class ImageRuntimeManager:
    _service_name = "image_runtime_manager"

    def __init__(
        self,
        cache: DesktopRuntimeCache = None,
        approval_gate: ImageApprovalGate = None,
        workflow_generator: WorkflowGenerator = None,
        event_bus: EventBus = None,
        service_manager: ServiceManager = None,
        logger=None,
    ):
        self._cache = cache
        self._approval_gate = approval_gate or ImageApprovalGate(logger=logger)
        self._workflow_generator = workflow_generator or WorkflowGenerator(logger=logger)
        self._event_bus = event_bus or EventBus()
        self._service_manager = service_manager
        self._logger = logger
        self._log = logger.info if logger else lambda m: None
        self._pending_requests: Dict[str, GenerationRequest] = {}
        self._running_prompts: Dict[str, str] = {}
        self._log("ImageRuntimeManager initialized")

    def start(self):
        self._log("ImageRuntimeManager started")
        hw = self._cache.get_hardware_profile() if self._cache else None
        if hw:
            self._log(f"Hardware profile: {hw.gpu_model}, {hw.vram_gb}GB VRAM")

    def stop(self):
        self._log("ImageRuntimeManager stopped")

    def generate(self, intent: str, options: dict = None) -> GenerationRequest:
        options = options or {}
        request_id = f"gen_{uuid.uuid4().hex[:8]}"

        category = options.get("template")
        workflow_json = self._workflow_generator.generate(intent, category)
        if not self._workflow_generator.validate(workflow_json):
            return GenerationRequest(
                request_id=request_id, intent=intent,
                workflow_json=workflow_json, risk=GenerationRisk.HIGH,
                status=GenerationStatus.FAILED, error="invalid workflow"
            )

        hw = self._cache.get_hardware_profile() if self._cache else None
        if not hw:
            from core_runtime.hardware_scanner import HardwareProfile
            hw = HardwareProfile(gpu_model="unknown", vram_gb=8.0,
                                  system_ram_gb=16.0, available_vram_gb=8.0,
                                  compute_capability=None)

        risk = self._approval_gate.score_generation(workflow_json, hw)
        approval_result = self._approval_gate.request_approval(
            request_id,
            f"Generate image: {intent[:50]}",
            risk
        )

        request = GenerationRequest(
            request_id=request_id,
            intent=intent,
            workflow_json=workflow_json,
            risk=risk,
            status=GenerationStatus.PENDING,
        )
        self._pending_requests[request_id] = request

        if approval_result.get("auto_approved"):
            request.status = GenerationStatus.QUEUED

        self._event_bus.publish("image_gen.approval_pending", {
            "request_id": request_id, "risk": risk.value, "intent": intent
        })
        return request

    def approve(self, request_id: str) -> bool:
        request = self._pending_requests.get(request_id)
        if not request:
            return False
        if request.status == GenerationStatus.CANCELLED:
            return False
        if request.status != GenerationStatus.PENDING:
            return True  # already approved (QUEUED by auto-approval, COMPLETED, etc.)
        request.status = GenerationStatus.QUEUED
        return True

    def reject(self, request_id: str) -> bool:
        request = self._pending_requests.get(request_id)
        if not request:
            return False
        request.status = GenerationStatus.CANCELLED
        return True

    def get_request(self, request_id: str) -> Optional[GenerationRequest]:
        return self._pending_requests.get(request_id)