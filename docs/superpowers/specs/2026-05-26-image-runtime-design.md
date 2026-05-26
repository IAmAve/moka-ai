# Image Runtime Manager — Phase 10

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** ComfyUI integration with workflow generation, real-time monitoring, queue management, resource control, and hardware-aware approval gates.

**Architecture:** A dedicated managed service (`ImageRuntimeManager`) that wraps `ComfyUIPlugin` for server primitives, generates workflows via template + LLM completion, approves submissions via risk-scored approval gates auto-tuned to detected GPU VRAM, and monitors progress via WebSocket with polling fallback.

**Tech Stack:** Python, ComfyUI HTTP/WS API, existing ApprovalGate, EventBus, ServiceManager, PermissionLevel.

---

## 1. Hardware Profiling

### HardwareScanner (`core_runtime/hardware_scanner.py`)

Runs as part of `DesktopRuntimeManager.run()` on MokaAI startup.

**Detects:**
- GPU model (NVIDIA via `nvidia-smi`, AMD via `rocm-smi`, Intel via `wmic path win32_VideoController`)
- VRAM in GB (from `nvidia-smi --query-gpu=memory.total --format=csv` or equivalent)
- Total system RAM (via `psutil.virtual_memory().total` or `wmic OS`)
- Available VRAM at scan time

**Output:** `HardwareProfile` dataclass stored in `DesktopRuntimeCache`:

```python
@dataclass
class HardwareProfile:
    gpu_model: str
    vram_gb: float
    system_ram_gb: float
    available_vram_gb: float
    compute_capability: Optional[str]  # e.g. "8.6" for RTX 4090
```

### Auto-Tuned Resource Limits

Limits scale with detected VRAM:

| VRAM  | Max Resolution | Max Steps | Max Concurrent |
|-------|---------------|-----------|----------------|
| 4 GB  | 512×512       | 50        | 1              |
| 8 GB  | 1024×1024     | 100       | 2              |
| 16 GB | 2048×2048     | 200       | 3              |
| 24 GB+| 3072×3072     | 500       | 4              |

Risk tiers also scale with hardware — on 4GB VRAM, a 1024² 100-step job is HIGH risk (not MEDIUM).

---

## 2. Workflow Generation

### Template + LLM Hybrid

**Template storage:** `workflows/templates/` directory containing ComfyUI workflow JSON files per task category:
- `portrait.json`
- `landscape.json`
- `anime.json`
- `architecture.json`
- `abstract.json`
- `default.json` — fallback minimal valid ComfyUI workflow

**Template format:** ComfyUI workflow JSON with `{prompt}`, `{model}`, `{seed}`, `{steps}`, `{cfg}`, `{resolution}` placeholders.

**Generation flow:**
1. User intent received (e.g. "generate a portrait of a cyberpunk samurai")
2. Match intent to nearest template category (keyword matching, or LLM classifies)
3. Load template JSON
4. LLM fills placeholders: prompt text, desired model checkpoints, resolution, steps
5. Validate generated JSON: all node IDs are unique, all node references resolve, required base nodes present
6. If validation fails: retry LLM fill up to 2 times, then fall back to `default.yaml`
7. Return `GeneratedWorkflow` with the ready-to-queue JSON and a `risk_estimate`

---

## 3. Approval Gate

### Risk Scoring

Uses existing `ApprovalGate.score_promotion()` pattern adapted for image generation:

```python
def score_generation(workflow_json, hardware_profile: HardwareProfile) -> GenerationRisk:
    vram_estimate = estimate_vram(workflow_json)  # based on resolution × model size
    step_count = workflow_json.get("metadata", {}).get("steps", 50)

    risk = 0
    if vram_estimate > hardware_profile.available_vram_gb * 0.8:
        risk += 5  # would exhaust VRAM
    if step_count > hardware_profile.max_steps:
        risk += 3
    if resolution > hardware_profile.max_resolution:
        risk += 2

    if risk >= 5: return Risk.HIGH
    elif risk >= 2: return Risk.MEDIUM
    else: return Risk.LOW
```

**Approval actions:**
- `LOW`: Submit directly to ComfyUI — no blocking
- `MEDIUM`: Queue for non-blocking human review; generation starts in background. User approves via `ApprovalQueue`. If rejected, running job is cancelled.
- `HIGH`: Block until human approves — same pattern as Phase 9 `ApprovalGate`

---

## 4. Status Monitoring

### Real-Time Monitoring

Uses WebSocket + polling hybrid:

**WebSocket** (`ws://localhost:8188/ws`):
- `executing` — node started, log node name
- `progress` — `(node_id, progress, VRAM_used)` — progress bar updates
- `executed` — node finished
- `finished` — full workflow complete, output image path known
- `error` — node or workflow error

**Polling fallback:** If WebSocket unavailable (ComfyUI not on localhost, or connection refused), poll `/history/{prompt_id}` every 5s and `/queue` every 10s.

**ImageRuntimeManager public API:**
```python
def monitor(self, prompt_id: str) -> GenerationStatus:
    """Start monitoring a prompt. Returns current status snapshot.
    Progress events published to EventBus as 'image_gen.progress'."""
```

---

## 5. Queue Management

### Through ComfyUI API

No separate queue — ComfyUI's own queue is the source of truth.

**Actions:**
- `queue_list()` → items in ComfyUI `/queue`, returns `list[QueueItem]`
- `queue_clear()` → clear ComfyUI queue (superuser only)
- `queue_cancel(prompt_id)` → remove a specific item by prompt_id
- `queue_reorder(prompt_id, new_position)` → move item in queue
- `queue_pause()` / `queue_resume()` → toggle ComfyUI queue processing

All queue actions logged to EventBus as `image_gen.queue.changed`.

---

## 6. Resource Control

### Generation Limits (enforced before queuing)

Limits are `hardware_profile`-derived and NOT user-configurable (prevents exceeding hardware):

- `max_steps`: max steps per generation (from VRAM table)
- `max_resolution`: max image dimension (from VRAM table)
- `max_concurrent`: max simultaneous running jobs (from VRAM table)
- `max_vram_per_job`: estimated VRAM per job type

If a workflow exceeds limits: reject before queuing, report which limit was exceeded.

---

## 7. Components

### ImageRuntimeManager (`core_runtime/image_runtime_manager.py`)

**Public API:**
```python
class ImageRuntimeManager:
    def generate(self, intent: str, options: dict) -> GenerationRequest
        # 1. Generate workflow from template+LLM
        # 2. Score risk against hardware profile
        # 3. Route through approval gate
        # 4. Return GenerationRequest pending_approval

    def approve(self, request_id: str) -> bool
        # Human approves a MEDIUM/HIGH request => submit to ComfyUI

    def reject(self, request_id: str) -> bool
        # Human rejects => discard request

    def monitor(self, prompt_id: str) -> GenerationStatus
        # Subscribe to live status for a ComfyUI prompt

    def queue_list(self) -> list[QueueItem]
    def queue_cancel(self, prompt_id: str) -> bool
    def queue_clear(self) -> bool
```

**Lifecycle:** `start()` / `stop()` managed by ServiceManager.

### WorkflowGenerator (`core_runtime/workflow_generator.py`)

```python
class WorkflowGenerator:
    def generate(self, intent: str, template_category: str) -> WorkflowSpec
        # Load template, LLM-fill placeholders, validate, return completed JSON

    def match_template(self, intent: str) -> str
        # Keyword or LLM classification → template name
```

### ImageApprovalGate (`core_runtime/image_approval_gate.py`)

Wraps `ApprovalGate` with `score_generation(workflow, hardware_profile)`. Uses `ApprovalQueue` for MEDIUM/HIGH.

### ImageMonitor (`core_runtime/image_monitor.py`)

WebSocket client + polling fallback. Publishes events to EventBus.

---

## 8. Data Flow

```
User: "generate a portrait"
  → ImageRuntimeManager.generate(intent)
    → WorkflowGenerator.match_template() → "portrait"
    → WorkflowGenerator.generate() → template filled + LLM completed
    → ImageApprovalGate.score_generation() → Risk.HIGH
    → ImageApprovalGate.request_approval() → queued for human review
    → user calls approve(request_id)
    → ComfyUIPlugin._queue_workflow({"workflow_json": ...})
    → ImageMonitor.monitor(prompt_id) [WebSocket + polling]
    → EventBus.publish("image_gen.progress", {prompt_id, node, progress})
    → EventBus.publish("image_gen.finished", {prompt_id, output_path})
```

---

## 9. Testing

- Unit: WorkflowGenerator template matching and filling
- Unit: ImageApprovalGate risk scoring per hardware tier
- Unit: ImageMonitor WebSocket/polling state machine
- Integration: Full generate → approve → monitor → finish flow (requires live ComfyUI)

---

## 10. Acceptance Criteria

- Queue is stable: no jobs lost, completed/failed correctly reported
- Approval gates work at all three risk tiers
- Resource limits auto-scale from detected hardware
- WebSocket monitoring publishes live progress events
- ImageRuntimeManager registered as a managed service in MokaAI