# Image Runtime Manager Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ComfyUI integration — hardware-aware workflow generation, approval gates, real-time monitoring, queue management, resource control.

**Architecture:** `ImageRuntimeManager` (orchestrator) + `HardwareScanner` (GPU detection) + `WorkflowGenerator` (template+LLM) + `ImageApprovalGate` (risk scoring) + `ImageMonitor` (WebSocket/polling). Wraps existing `ComfyUIPlugin` for server primitives. Uses `ApprovalQueue` for human review. All modules publish to `EventBus`.

**Tech Stack:** Python, ComfyUI HTTP/WS API, `requests`, `websockets`, existing ApprovalGate, EventBus, ServiceManager, ApprovalQueue.

---

## Task 1: HardwareScanner

**Files:**
- Create: `core_runtime/hardware_scanner.py`
- Create: `tests/test_hardware_scanner.py`
- Read: `core_runtime/desktop_runtime_cache.py` (to understand cache interface)

### `core_runtime/hardware_scanner.py`

```python
"""HardwareScanner — detect GPU model, VRAM, system RAM, compute capability."""

import subprocess
import re
import psutil
from dataclasses import dataclass
from typing import Optional

@dataclass
class HardwareProfile:
    gpu_model: str
    vram_gb: float
    system_ram_gb: float
    available_vram_gb: float
    compute_capability: Optional[str]  # e.g. "8.6" for RTX 4090

class HardwareScanner:
    def scan(self) -> HardwareProfile:
        gpu_model, vram, compute = self._detect_nvidia()
        if not gpu_model:
            gpu_model, vram, compute = self._detect_amd()
        if not gpu_model:
            gpu_model, vram, compute = "unknown", 0.0, None
        ram = psutil.virtual_memory().total / (1024**3)
        return HardwareProfile(
            gpu_model=gpu_model,
            vram_gb=vram,
            system_ram_gb=ram,
            available_vram_gb=vram,  # initial scan: assume all available
            compute_capability=compute,
        )

    def _detect_nvidia(self):
        try:
            r = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total,compute_arch",
                 "--format=csv,noheader,nonoheader"],
                capture_output=True, text=True, timeout=10
            )
            if r.returncode == 0 and r.stdout.strip():
                parts = r.stdout.strip().split(", ")
                model = parts[0]
                vram = float(re.sub(r'[^\d.]', '', parts[1])) / 1024  # MB to GB
                compute = parts[2] if len(parts) > 2 else None
                return model, vram, compute
        except Exception:
            pass
        return None, None, None

    def _detect_amd(self):
        # Placeholder — AMD detection via rocm-smi or wmic
        return None, None, None
```

### `tests/test_hardware_scanner.py`

```python
import unittest
import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core_runtime.hardware_scanner import HardwareScanner, HardwareProfile

class TestHardwareScanner(unittest.TestCase):
    def test_scan_returns_profile(self):
        scanner = HardwareScanner()
        profile = scanner.scan()
        self.assertIsInstance(profile, HardwareProfile)
        self.assertIsInstance(profile.vram_gb, float)
        self.assertIsInstance(profile.system_ram_gb, float)

    def test_hardware_profile_dataclass_fields(self):
        p = HardwareProfile(gpu_model="RTX 4090", vram_gb=24.0,
                            system_ram_gb=32.0, available_vram_gb=24.0,
                            compute_capability="8.9")
        self.assertEqual(p.gpu_model, "RTX 4090")
        self.assertEqual(p.vram_gb, 24.0)

    def test_auto_tuned_limits_4gb(self):
        scanner = HardwareScanner.__new__(HardwareScanner)
        limits = scanner._auto_limits(4.0)
        self.assertEqual(limits["max_resolution"], 512)
        self.assertEqual(limits["max_steps"], 50)

    def test_auto_tuned_limits_8gb(self):
        scanner = HardwareScanner.__new__(HardwareScanner)
        limits = scanner._auto_limits(8.0)
        self.assertEqual(limits["max_resolution"], 1024)
        self.assertEqual(limits["max_steps"], 100)

    def test_auto_tuned_limits_16gb(self):
        scanner = HardwareScanner.__new__(HardwareScanner)
        limits = scanner._auto_limits(16.0)
        self.assertEqual(limits["max_resolution"], 2048)
        self.assertEqual(limits["max_steps"], 200)
```

---

## Task 2: HardwareProfile in DesktopRuntimeCache + DesktopRuntimeManager

**Files:**
- Modify: `core_runtime/desktop_runtime_cache.py`
- Modify: `core_runtime/desktop_runtime_manager.py`
- Modify: `tests/test_desktop_runtime_cache.py` (add HardwareProfile test)

### Changes to `desktop_runtime_cache.py`

Add method to store/retrieve HardwareProfile:

```python
def set_hardware_profile(self, profile: HardwareProfile):
    self._hardware_profile = profile

def get_hardware_profile(self) -> Optional[HardwareProfile]:
    return getattr(self, '_hardware_profile', None)
```

### Changes to `desktop_runtime_manager.py`

In `run()`, after software/runtimes scan, add hardware scan:

```python
from core_runtime.hardware_scanner import HardwareScanner
# In run():
self._hardware_scanner = HardwareScanner()
hw_profile = self._hardware_scanner.scan()
self._cache.set_hardware_profile(hw_profile)
```

---

## Task 3: WorkflowGenerator + ComfyUI Templates

**Files:**
- Create: `core_runtime/workflow_generator.py`
- Create: `tests/test_workflow_generator.py`
- Create: `workflows/templates/portrait.json`
- Create: `workflows/templates/landscape.json`
- Create: `workflows/templates/anime.json`
- Create: `workflows/templates/default.json`
- Modify: `core_runtime/desktop_runtime_cache.py` (add template storage path)

### `core_runtime/workflow_generator.py`

```python
"""WorkflowGenerator — loads ComfyUI templates, fills via LLM."""

import json
import os
import re
from dataclasses import dataclass
from typing import Optional

def _simple_llm_fill(template_json: dict, intent: str) -> dict:
    """Minimal LLM fill: replaces {prompt} with intent, sets reasonable defaults."""
    # Find the KSampler node and set its prompt text
    workflow = template_json.copy()
    workflow.setdefault("nodes", [])

    # For default template: create a minimal valid KSampler pipeline
    prompt_text = intent

    # Replace {prompt} wherever it appears in string values
    def replace_prompt(obj):
        if isinstance(obj, dict):
            return {k: replace_prompt(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [replace_prompt(v) for v in obj]
        elif isinstance(obj, str):
            return obj.replace("{prompt}", prompt_text)
        return obj

    return replace_prompt(workflow)


class WorkflowGenerator:
    def __init__(self, templates_path: str = "workflows/templates", logger=None):
        self._templates_path = templates_path
        self._log = logger.info if logger else lambda m: None
        self._templates = {}
        self._load_templates()

    def _load_templates(self):
        if not os.path.exists(self._templates_path):
            os.makedirs(self._templates_path, exist_ok=True)
            self._create_defaults()
        for fname in os.listdir(self._templates_path):
            if fname.endswith(".json"):
                with open(os.path.join(self._templates_path, fname)) as f:
                    name = fname[:-5]  # strip .json
                    self._templates[name] = json.load(f)
        self._log(f"Loaded {len(self._templates)} workflow templates: {list(self._templates.keys())}")

    def _create_defaults(self):
        default = {
            "nodes": [
                {"id": 1, "type": "CheckpointLoaderSimple", "attrs": {"model": "sd_xl_base_1.0.safetensors"}},
                {"id": 2, "type": "CLIPTextEncode", "attrs": {"text": "{prompt}"}},
                {"id": 3, "type": "CLIPTextEncode", "attrs": {"text": "masterpiece, best quality"}},
                {"id": 4, "type": "KSampler", "attrs": {"steps": 50, "cfg": 7.0, "seed": 0, "sampler_name": "euler"}},
                {"id": 5, "type": "VAEDecode", "attrs": {}},
                {"id": 6, "type": "SaveImage", "attrs": {"filename_prefix": "MokaGen"}}
            ],
            "links": [[2, 1, 4], [3, 1, 4], [4, 5], [5, 6]]
        }
        categories = ["portrait", "landscape", "anime", "default"]
        for cat in categories:
            path = os.path.join(self._templates_path, f"{cat}.json")
            if not os.path.exists(path):
                with open(path, "w") as f:
                    json.dump(default if cat == "default" else default, f)

    def match_template(self, intent: str) -> str:
        intent_lower = intent.lower()
        keywords = {
            "portrait": ["portrait", "face", "person", "headshot", "selfie"],
            "landscape": ["landscape", "scenery", "outdoor", "nature", "mountain", "forest"],
            "anime": ["anime", "manga", "cell shaded", "illustrated"],
        }
        for cat, words in keywords.items():
            if any(w in intent_lower for w in words):
                return cat
        return "default"

    def generate(self, intent: str, template_category: Optional[str] = None) -> dict:
        cat = template_category or self.match_template(intent)
        template = self._templates.get(cat, self._templates.get("default"))
        if not template:
            raise ValueError(f"No template found for category: {cat}")
        return _simple_llm_fill(template, intent)

    def validate(self, workflow_json: dict) -> bool:
        """Check it has required nodes and no duplicate IDs."""
        if "nodes" not in workflow_json:
            return False
        ids = [n["id"] for n in workflow_json["nodes"]]
        if len(ids) != len(set(ids)):
            return False
        return True
```

---

## Task 4: ImageApprovalGate + ImageRuntimeManager

**Files:**
- Create: `core_runtime/image_approval_gate.py`
- Create: `tests/test_image_approval_gate.py`
- Create: `core_runtime/image_runtime_manager.py`
- Create: `tests/test_image_runtime_manager.py`
- Modify: `plugins/comfyui_plugin.py`

### `core_runtime/image_approval_gate.py`

```python
"""ImageApprovalGate — risk scoring for image generation requests."""

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
        """Estimate VRAM from resolution and model in workflow. Very rough."""
        nodes = {n["id"]: n for n in workflow_json.get("nodes", [])}
        resolution = 512  # default
        for node in nodes.values():
            if node.get("type") == "EmptyLatentImage":
                w = node.get("attrs", {}).get("width", 512)
                h = node.get("attrs", {}).get("height", 512)
                resolution = max(w, h)
        # Rough estimate: ~4GB for 1024x1024 SDXL
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
        hw_limit_vram = hardware_profile.vram_gb * 0.8  # 80% of available

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
```

### `core_runtime/image_runtime_manager.py`

```python
"""ImageRuntimeManager — ComfyUI workflow orchestration, approval, and monitoring."""

import uuid
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from core.event_bus import EventBus
from core.service_manager import ServiceManager
from core_runtime.workflow_generator import WorkflowGenerator
from core_runtime.image_approval_gate import ImageApprovalGate, GenerationRisk
from core_runtime.image_monitor import ImageMonitor
from plugins.comfyui_plugin import ComfyUIPlugin
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
        monitor: ImageMonitor = None,
        event_bus: EventBus = None,
        service_manager: ServiceManager = None,
        logger=None,
    ):
        self._cache = cache
        self._approval_gate = approval_gate or ImageApprovalGate(logger=logger)
        self._workflow_generator = workflow_generator or WorkflowGenerator(logger=logger)
        self._monitor = monitor or ImageMonitor(logger=logger)
        self._event_bus = event_bus or EventBus()
        self._service_manager = service_manager
        self._logger = logger
        self._log = logger.info if logger else lambda m: None
        self._comfyui = ComfyUIPlugin(logger=logger)
        self._pending_requests: Dict[str, GenerationRequest] = {}
        self._running_prompts: Dict[str, str] = {}  # prompt_id -> request_id
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
            return self._submit_to_comfyui(request)

        self._event_bus.publish("image_gen.approval_pending", {
            "request_id": request_id, "risk": risk.value, "intent": intent
        })
        return request

    def _submit_to_comfyui(self, request: GenerationRequest) -> GenerationRequest:
        result = self._comfyui.execute({
            "action": "queue",
            "workflow_json": request.workflow_json
        })
        if result.get("ok"):
            request.prompt_id = result.get("prompt_id")
            request.status = GenerationStatus.RUNNING
            self._running_prompts[request.prompt_id] = request.request_id
            self._monitor.subscribe(request.prompt_id, request.request_id)
        else:
            request.status = GenerationStatus.FAILED
            request.error = result.get("error", "queue failed")
        return request

    def approve(self, request_id: str) -> bool:
        request = self._pending_requests.get(request_id)
        if not request:
            return False
        if request.status != GenerationStatus.PENDING:
            return False
        request.status = GenerationStatus.QUEUED
        self._submit_to_comfyui(request)
        return True

    def reject(self, request_id: str) -> bool:
        request = self._pending_requests.get(request_id)
        if not request:
            return False
        request.status = GenerationStatus.CANCELLED
        return True

    def monitor(self, prompt_id: str) -> Dict[str, Any]:
        return self._monitor.get_status(prompt_id)

    def queue_list(self) -> List[Dict[str, Any]]:
        result = self._comfyui.execute({"action": "status"})
        queued = result.get("response", {}).get("queue", []) if result.get("ok") else []
        return queued

    def queue_cancel(self, prompt_id: str) -> bool:
        # ComfyUI API: POST /interrupt with prompt_id
        return True

    def queue_clear(self) -> bool:
        return True
```

---

## Task 5: ImageMonitor + MokaAI Wiring + Integration

**Files:**
- Create: `core_runtime/image_monitor.py`
- Create: `tests/test_image_monitor.py`
- Modify: `moka.py`
- Create: `tests/test_image_runtime_integration.py`

### `core_runtime/image_monitor.py`

```python
"""ImageMonitor — WebSocket + polling fallback for ComfyUI generation progress."""

import threading
import time
import json
from typing import Any, Dict, Optional

class ImageMonitor:
    def __init__(self, comfyui_url: str = "http://localhost:8188", logger=None):
        self._comfyui_url = comfyui_url
        self._ws_url = comfyui_url.replace("http", "ws") + "/ws"
        self._logger = logger
        self._log = logger.info if logger else lambda m: None
        self._subscriptions: Dict[str, str] = {}  # prompt_id -> request_id
        self._status: Dict[str, Dict[str, Any]] = {}  # prompt_id -> status
        self._stop_events: Dict[str, threading.Event] = {}
        self._event_bus = None
        try:
            import websockets
            self._websockets_available = True
        except ImportError:
            self._websockets_available = False
            self._log("websockets not available — using polling fallback")

    def set_event_bus(self, event_bus):
        self._event_bus = event_bus

    def subscribe(self, prompt_id: str, request_id: str):
        self._subscriptions[prompt_id] = request_id
        self._status[prompt_id] = {"state": "running", "progress": 0, "output": None}
        self._stop_events[prompt_id] = threading.Event()
        if self._websockets_available:
            t = threading.Thread(target=self._ws_loop, args=(prompt_id,), daemon=True)
            t.start()
        else:
            t = threading.Thread(target=self._poll_loop, args=(prompt_id,), daemon=True)
            t.start()

    def unsubscribe(self, prompt_id: str):
        if prompt_id in self._stop_events:
            self._stop_events[prompt_id].set()
        self._subscriptions.pop(prompt_id, None)
        self._status.pop(prompt_id, None)

    def get_status(self, prompt_id: str) -> Optional[Dict[str, Any]]:
        return self._status.get(prompt_id)

    def _ws_loop(self, prompt_id: str):
        import asyncio, websockets, json as jsonmod
        stop = self._stop_events.get(prompt_id)
        while not stop.is_set():
            try:
                async def receive():
                    async with websockets.connect(self._ws_url) as ws:
                        while not stop.is_set():
                            msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                            self._handle_ws_message(prompt_id, jsonmod.loads(msg))
                asyncio.run(receive())
            except Exception as e:
                self._log(f"WS error for {prompt_id}: {e}, retrying in 5s")
                time.sleep(5)

    def _poll_loop(self, prompt_id: str):
        import requests
        stop = self._stop_events.get(prompt_id)
        while not stop.is_set():
            try:
                r = requests.get(
                    f"{self._comfyui_url}/history/{prompt_id}",
                    timeout=10
                )
                if r.ok:
                    data = r.json()
                    if prompt_id in data:
                        self._status[prompt_id] = {
                            "state": "completed",
                            "output": data[prompt_id].get("outputs", {})
                        }
                        self._publish("image_gen.finished", prompt_id)
                        return
            except Exception as e:
                self._log(f"Polling error for {prompt_id}: {e}")
            time.sleep(5)

    def _handle_ws_message(self, prompt_id: str, msg: dict):
        msg_type = msg.get("type", "")
        data = msg.get("data", {})

        if msg_type == "progress":
            self._status[prompt_id] = {
                "state": "running",
                "progress": data.get("value", 0),
                "node": data.get("node", "")
            }
            self._publish("image_gen.progress", {
                "prompt_id": prompt_id,
                "progress": data.get("value", 0),
                "node": data.get("node", "")
            })
        elif msg_type == "executing":
            self._publish("image_gen.executing", {
                "prompt_id": prompt_id,
                "node": data.get("node", "")
            })
        elif msg_type == "finished":
            self._status[prompt_id] = {
                "state": "completed",
                "output": data.get("output", {})
            }
            req_id = self._subscriptions.get(prompt_id)
            self._publish("image_gen.finished", {
                "prompt_id": prompt_id,
                "request_id": req_id,
                "output": data.get("output", {})
            })
            self.unsubscribe(prompt_id)
        elif msg_type == "error":
            self._status[prompt_id] = {"state": "failed", "error": data.get("error", "")}
            self._publish("image_gen.error", {
                "prompt_id": prompt_id,
                "error": data.get("error", "")
            })
            self.unsubscribe(prompt_id)

    def _publish(self, event: str, data: dict):
        if self._event_bus:
            self._event_bus.publish(event, data)
```

### Changes to `moka.py`

```python
from core_runtime.image_runtime_manager import ImageRuntimeManager

# In __init__:
self.image_runtime = None

# In _register_core_services:
self.image_runtime = ImageRuntimeManager(
    cache=self.desktop_runtime.get_cache() if self.desktop_runtime else None,
    event_bus=self.event_bus,
    logger=self.logger,
)
self.service_manager.register_service("image_runtime_manager", self.image_runtime)

# In _validate_startup:
("image_runtime", lambda: self.image_runtime),

# In shutdown:
if hasattr(self.image_runtime, 'stop'):
    self.image_runtime.stop()
```

### Changes to `plugins/comfyui_plugin.py`

Add `queue` action to `_queue_workflow` that accepts direct workflow JSON:

```python
def _queue_workflow(self, data: Dict[str, Any]) -> Dict[str, Any]:
    workflow_json = data.get("workflow_json")
    port = data.get("port", self.DEFAULT_PORT)
    url = f"http://localhost:{port}/prompt"

    if workflow_json:
        # Direct JSON submission
        try:
            response = requests.post(url, json={"prompt": workflow_json}, timeout=30)
            if response.ok:
                result = response.json()
                self._log(f"Workflow queued: prompt_id={result.get('prompt_id')}")
                return {"ok": True, "prompt_id": result.get("prompt_id")}
            return {"ok": False, "status": response.status_code, "error": response.text}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # Existing path: from file
    workflow_path = data.get("workflow_path")
    ...
```