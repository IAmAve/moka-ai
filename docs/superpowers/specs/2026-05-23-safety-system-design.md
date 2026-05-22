# MOKA AI Safety System Design

**Date:** 2026-05-23
**Phase:** PHASE 6 — Safety System
**Status:** Approved

## Overview

The safety system implements a four-tier permission architecture (SAFE/MEDIUM/DANGEROUS/SYSTEM) that gates both incoming user requests and outgoing command executions through a unified pipeline.

## Architecture

```
User Input → Intent Detection → Risk Scan → Approval (if needed) → Queue → Execution → Verification → Rollback (if needed) → Response
```

## Permission Levels

| Level | Description | Config Key |
|-------|-------------|------------|
| SAFE | Read-only operations (file reads, queries, search) | `level: safe` |
| MEDIUM | Non-destructive writes (create/modify project files) | `level: medium` |
| DANGEROUS | Destructive operations (delete, execute code, network calls) | `level: dangerous` |
| SYSTEM | Infrastructure changes (config mods, plugin loading, admin) | `level: system` |

Defaults stored in `config/permission_levels.json`. User-configurable.

## Pipeline Stages

### 1. Intent Detection
- Extracts action type, target, parameters from input
- Maps to permission level candidate
- Output: `Intent(intent_type, target, params, suggested_level)`

### 2. Risk Scan
- Evaluates against dangerous pattern list (delete, rm, format, exec, etc.)
- Checks file targets against protected paths
- Combines with intent level to determine final required level
- Output: `RiskAssessment(required_level, risk_factors[], blocked: bool)`

### 3. Approval
- If `required_level in [DANGEROUS, SYSTEM]`: queue for user approval
- Presents action description + risk explanation to user
- User approves, denies, or cancels
- Approved actions move to queue; denied actions return error

### 4. Queue
- Holds approved actions awaiting execution
- FIFO processing with timeout (configurable, default 60s)
- Expired approvals return to pending state

### 5. Execution
- Runs action with monitoring
- Tracks execution state and duration
- Emits events for completion/failure

### 6. Verification
- Confirms expected outcome occurred
- Checks file state, return codes, output
- On failure: triggers rollback

### 7. Rollback
- Reverts file modifications to pre-action snapshots
- `RollbackManager` maintains snapshot queue (LIFO)
- External effects (network, deployments) logged but not reverted
- Supports idempotent recovery

## Emergency Stop

**Trigger:** `CTRL+ALT+M` (global hotkey)

**Behavior:**
1. Stops current in-flight action
2. Clears execution queue (pending actions discarded)
3. Preserves state for post-mortem
4. Emits `emergency_stop` event on EventBus

**Implementation:** OS-level hotkey binding via `pygetwindow` or `keyboard` library.

## Components

| File | Responsibility |
|------|----------------|
| `safety/permission_levels.py` | Level definitions, config loading |
| `safety/intent_detector.py` | Parse input, extract intent |
| `safety/risk_scanner.py` | Pattern matching, path protection |
| `safety/approval_queue.py` | User approval workflow |
| `safety/execution_pipeline.py` | Orchestrate all stages |
| `safety/rollback_manager.py` | Snapshot + revert logic |
| `safety/emergency_stop.py` | Global hotkey + stop logic |
| `safety/__init__.py` | Package exports |

## Integration

- Subscribes to `MokaAI` EventBus for: `action_requested`, `action_completed`, `action_failed`
- Publishes: `safety.approval_required`, `safety.action_blocked`, `safety.emergency_stopped`
- Plugs into CLI layer as middleware on all command executions

## Configuration

`config/permission_levels.json`:
```json
{
  "levels": {
    "safe": {"actions": ["read", "search", "query"]},
    "medium": {"actions": ["create", "modify", "write"]},
    "dangerous": {"actions": ["delete", "execute", "network"]},
    "system": {"actions": ["config", "plugin", "admin"]}
  },
  "dangerous_patterns": ["rm -rf", "del /f", "format", "truncate"],
  "protected_paths": ["C:\\Windows", "/etc", "~/.ssh"],
  "approval_timeout_seconds": 60
}
```

## Acceptance Criteria

1. [ ] MEDIUM action blocked without approval → returns `safety.action_blocked` event
2. [ ] DANGEROUS action requires explicit user approval step before execution
3. [ ] Rollback reverts file to pre-action state after verification failure
4. [ ] Emergency stop halts queue and in-flight action within 100ms
5. [ ] All pipeline stages emit appropriate events on EventBus
6. [ ] Configuration reloads without restart

## Rollback Scope

File modifications only (git-like revert). External effects (network calls, deployments) are logged but not reverted — must be handled via idempotent design at action definition time.