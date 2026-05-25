# Engineering Workflow Orchestrator — Design

**Date:** 2026-05-26
**Phase:** 9
**Status:** Approved

---

## Overview

The Engineering Workflow Orchestrator (EWO) is a human-in-the-loop pipeline engine that executes multi-stage software engineering workflows across isolated sandbox environments. It extends the existing `TaskOrchestrator` with sandbox promotion, approval gates, and rollback capabilities.

---

## Pipeline Stages

| Stage | Purpose |
|-------|---------|
| `analyze` | Parse natural language intent AND scan existing codebase; output a `WorkflowSpec` |
| `create` | Generate implementation plan from `WorkflowSpec` (step ordering, file changes, dependencies) |
| `install` | Provision dependencies in the sandbox (pip install, npm install, etc.) |
| `code` | Write and modify code files within the sandbox worktree |
| `test` | Execute the existing test suite within the sandbox container |
| `debug` | Auto-fix loop (N iterations, configurable); prompt human if iterations exhausted |
| `approval` | Risk-scored gate: low-risk auto-approved; high-risk queued for human review |
| `launch` | Promote approved code to the next environment (temp→test or test→live) |

---

## Sandbox Model

Three environments with mandatory approval gates between them:

```
temp  →  [approval gate]  →  test  →  [approval gate]  →  live
```

### Filesystem Isolation
- Each sandbox uses a **git worktree** for isolated filesystem access
- Worktrees are created from a base branch; changes are isolated from main
- On rollback, the worktree is removed and recreated from the last known-good commit

### Execution Isolation
- Each sandbox runs code inside an **isolated container** (docker/podman)
- Container images are provisioned per workflow run
- On rollback, the container is destroyed and a new one is spawned from the base image

---

## Approval Gates

Two gates: **temp→test** and **test→live**

### Auto-Approval (AI)
The `RiskScanner` classifies changes:
- **Low risk** → auto-approved, promotion proceeds without human intervention
- **Medium risk** → flagged, human approval required before promotion
- **High risk** → always requires explicit human approval

### Human Approval
- Pending approvals are queued via `ApprovalQueue` (existing safety system)
- User receives notification with: diff summary, risk score, affected files
- User can approve, deny, or request changes

---

## Rollback

Two-level rollback:

1. **Step-level** (existing `TaskOrchestrator._rollback_workflow`):
   - Each `WorkflowStep` carries an optional `rollback_handler`
   - On step failure, completed steps run their rollback handlers in reverse order

2. **Stage-level** (`RollbackManager`):
   - Snapshot taken at start of each stage
   - On stage failure (e.g., test fails and debug loop exhausted), entire sandbox reverts to last snapshot
   - Uses git worktree reset for files, container image revert for execution

---

## Key Components

| Component | Responsibility | Location |
|-----------|-----------------|----------|
| `EngineeringWorkflowOrchestrator` | Pipeline driver, stage sequencing, promotion logic | `core_runtime/` |
| `SandboxManager` | Worktree creation/removal, container lifecycle | `core_runtime/` |
| `DebugLoop` | Auto-fix iteration with human fallback | `core_runtime/` |
| `ApprovalGate` | Risk scoring, auto-approval, queue delegation | `core_runtime/` |
| `TaskOrchestrator` (existing) | Per-stage step execution | `core_runtime/task_orchestration.py` |
| `ApprovalQueue` (existing) | Human approval queuing | `safety/approval_queue.py` |
| `RiskScanner` (existing) | Change risk assessment | `safety/risk_scanner.py` |
| `RollbackManager` (existing) | Snapshot/revert | `safety/rollback_manager.py` |
| `EventBus` (existing) | Stage transition events | `core/event_bus.py` |
| `ServiceManager` (existing) | Lifecycle management | `core/service_manager.py` |

---

## Data Flow

```
User Input (natural language)
    ↓
[analyze] → WorkflowSpec { intent, file_changes[], deps[] }
    ↓
[create] → ImplementationPlan { steps[], dependencies[] }
    ↓
[SandboxManager] → create worktree + container (temp environment)
    ↓
[install] → dependencies in sandbox container
    ↓
[code] → TaskOrchestrator executes step handlers in worktree
    ↓
[test] → run test suite in container; verify results
    ↓
[debug] → if tests fail: auto-fix loop (N iterations) → manual if exhausted
    ↓
[approval] → RiskScanner scores changes → auto-approve low-risk OR queue for human
    ↓
[launch] → SandboxManager promotes: temp→test OR test→live
    ↓
RollbackManager snapshots after every stage transition
```

---

## Acceptance Criteria

1. [ ] `analyze` produces a valid `WorkflowSpec` from natural language + codebase scan
2. [ ] `create` produces a step-ordered implementation plan
3. [ ] Sandbox isolation (worktree + container) is enforced for all stages
4. [ ] `install` installs declared dependencies in the sandbox container
5. [ ] `code` writes files only within the sandbox worktree
6. [ ] `test` runs existing test suite; reports pass/fail
7. [ ] `debug` auto-fix retries up to N iterations; falls back to human prompt
8. [ ] **temp→test gate**: low-risk auto-approved; medium/high require human
9. [ ] **test→live gate**: same rules as above
10. [ ] `RollbackManager` reverts sandbox to last snapshot on failure
11. [ ] `launch` promotes approved code to next environment
12. [ ] All stage transitions publish events on `EventBus`

---

## Rollback Scope

Same as the existing safety system: **file modifications only**. External effects (network calls, deployments, environment variables) are logged but not reverted. Recovery from external effects must be handled via idempotent design at action definition time.

---

## Notes

- The EWO does NOT write tests — only runs the existing test suite (test files must already exist)
- Auto-fix in `debug` modifies code in the sandbox worktree; each retry is a new commit
- Debug loop iteration count is configurable (default: 3)
- Approval queue persists across restarts