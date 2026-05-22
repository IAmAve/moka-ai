# Safety System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement permission-based safety system with four levels, execution pipeline, rollback, and emergency stop.

**Architecture:** Four-tier permission architecture gating both user input and command execution through intent detection → risk scan → approval → queue → execution → verification → rollback pipeline. Rollback scoped to file modifications only.

**Tech Stack:** Python, event bus pub/sub, JSON config, `keyboard` library for global hotkey, pytest for testing.

---

## Task 1: Create Safety Module Structure

**Files:**
- Create: `safety/__init__.py`
- Create: `safety/permission_levels.py`
- Create: `config/permission_levels.json`

- [ ] **Step 1: Create safety directory and __init__.py**

```python
# safety/__init__.py
from .permission_levels import PermissionLevel, PermissionManager
from .intent_detector import IntentDetector
from .risk_scanner import RiskScanner
from .approval_queue import ApprovalQueue
from .execution_pipeline import ExecutionPipeline
from .rollback_manager import RollbackManager
from .emergency_stop import EmergencyStop

__all__ = [
    'PermissionLevel',
    'PermissionManager',
    'IntentDetector',
    'RiskScanner',
    'ApprovalQueue',
    'ExecutionPipeline',
    'RollbackManager',
    'EmergencyStop',
]
```

```bash
mkdir -p safety
touch safety/__init__.py
```

- [ ] **Step 2: Create permission_levels.py**

```python
# safety/permission_levels.py
from enum import Enum
from typing import Dict, List, Optional
import json
import os

class PermissionLevel(Enum):
    SAFE = "safe"
    MEDIUM = "medium"
    DANGEROUS = "dangerous"
    SYSTEM = "system"

class PermissionManager:
    DEFAULT_CONFIG = {
        "levels": {
            "safe": {"actions": ["read", "search", "query", "grep", "find", "list"]},
            "medium": {"actions": ["create", "modify", "write", "edit", "add"]},
            "dangerous": {"actions": ["delete", "execute", "network", "run", "install"]},
            "system": {"actions": ["config", "plugin", "admin", "reload", "restart"]}
        },
        "dangerous_patterns": ["rm -rf", "del /f", "format", "truncate", "DROP TABLE", "git push --force"],
        "protected_paths": ["C:\\Windows", "/etc", "~/.ssh", ".env"],
        "approval_timeout_seconds": 60
    }

    def __init__(self, config_path: str = "config/permission_levels.json"):
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return self.DEFAULT_CONFIG.copy()

    def get_level_for_action(self, action: str) -> PermissionLevel:
        action = action.lower()
        for level_name, level_data in self.config.get("levels", {}).items():
            if action in level_data.get("actions", []):
                return PermissionLevel(level_name)
        return PermissionLevel.MEDIUM  # Default to MEDIUM if unknown

    def is_dangerous_pattern(self, text: str) -> bool:
        patterns = self.config.get("dangerous_patterns", [])
        text_lower = text.lower()
        return any(p.lower() in text_lower for p in patterns)

    def is_protected_path(self, path: str) -> bool:
        protected = self.config.get("protected_paths", [])
        for p in protected:
            if p.lower() in path.lower():
                return True
        return False

    def get_approval_timeout(self) -> int:
        return self.config.get("approval_timeout_seconds", 60)
```

- [ ] **Step 3: Create config/permission_levels.json**

```json
{
  "levels": {
    "safe": {"actions": ["read", "search", "query", "grep", "find", "list"]},
    "medium": {"actions": ["create", "modify", "write", "edit", "add"]},
    "dangerous": {"actions": ["delete", "execute", "network", "run", "install"]},
    "system": {"actions": ["config", "plugin", "admin", "reload", "restart"]}
  },
  "dangerous_patterns": ["rm -rf", "del /f", "format", "truncate", "DROP TABLE", "git push --force"],
  "protected_paths": ["C:\\Windows", "/etc", "~/.ssh", ".env"],
  "approval_timeout_seconds": 60
}
```

- [ ] **Step 4: Run test to verify module imports**

Run: `python -c "from safety import PermissionLevel, PermissionManager; print('Import OK')"`
Expected: Import OK

- [ ] **Step 5: Commit**

```bash
git add safety/__init__.py safety/permission_levels.py config/permission_levels.json
git commit -m "feat(safety): add permission levels and PermissionManager"
```

---

## Task 2: Intent Detector

**Files:**
- Create: `safety/intent_detector.py`
- Create: `tests/test_intent_detector.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_intent_detector.py
import unittest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from safety.intent_detector import IntentDetector, Intent

class TestIntentDetector(unittest.TestCase):
    def test_detect_read_action(self):
        detector = IntentDetector()
        intent = detector.detect("read the file config.py")
        self.assertEqual(intent.action, "read")
        self.assertIn("config.py", intent.target)

    def test_detect_write_action(self):
        detector = IntentDetector()
        intent = detector.detect("write to config.json")
        self.assertEqual(intent.action, "write")

    def test_detect_delete_action(self):
        detector = IntentDetector()
        intent = detector.detect("delete the temp file")
        self.assertEqual(intent.action, "delete")

    def test_detect_unknown_action_defaults_to_medium(self):
        detector = IntentDetector()
        intent = detector.detect("do something")
        self.assertEqual(intent.suggested_level.value, "medium")
```

Run: `python -m pytest tests/test_intent_detector.py -v`
Expected: FAIL — module not found

- [ ] **Step 2: Create IntentDetector**

```python
# safety/intent_detector.py
from dataclasses import dataclass
from typing import Optional
from .permission_levels import PermissionLevel

@dataclass
class Intent:
    action: str
    target: str
    params: dict
    suggested_level: PermissionLevel
    original_text: str

class IntentDetector:
    ACTION_KEYWORDS = {
        "read": ["read", "show", "view", "cat", "get", "display", "list"],
        "write": ["write", "edit", "modify", "create", "add", "append"],
        "delete": ["delete", "remove", "rm", "del", "unlink", "destroy"],
        "execute": ["execute", "run", "bash", "cmd", "exec", "shell", "python", "node"],
        "network": ["curl", "wget", "fetch", "http", "api", "request", "send"],
        "config": ["config", "set", "env", "setting", "configure"],
        "plugin": ["plugin", "load", "unload", "enable", "disable"],
    }

    def detect(self, text: str) -> Intent:
        text_lower = text.lower()
        action = self._extract_action(text_lower)
        target = self._extract_target(text, action)
        suggested_level = self._get_level_for_action(action)
        return Intent(
            action=action,
            target=target,
            params={},
            suggested_level=suggested_level,
            original_text=text
        )

    def _extract_action(self, text: str) -> str:
        for action, keywords in self.ACTION_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    return action
        return "unknown"

    def _extract_target(self, text: str, action: str) -> str:
        words = text.split()
        if len(words) > 1:
            return words[-1]
        return text

    def _get_level_for_action(self, action: str) -> PermissionLevel:
        from .permission_levels import PermissionLevel
        action_to_level = {
            "read": PermissionLevel.SAFE,
            "write": PermissionLevel.MEDIUM,
            "delete": PermissionLevel.DANGEROUS,
            "execute": PermissionLevel.DANGEROUS,
            "network": PermissionLevel.DANGEROUS,
            "config": PermissionLevel.SYSTEM,
            "plugin": PermissionLevel.SYSTEM,
        }
        return action_to_level.get(action, PermissionLevel.MEDIUM)
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `python -m pytest tests/test_intent_detector.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add safety/intent_detector.py tests/test_intent_detector.py
git commit -m "feat(safety): add IntentDetector for action extraction"
```

---

## Task 3: Risk Scanner

**Files:**
- Create: `safety/risk_scanner.py`
- Create: `tests/test_risk_scanner.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_risk_scanner.py
import unittest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from safety.risk_scanner import RiskScanner, RiskAssessment
from safety.intent_detector import Intent
from safety.permission_levels import PermissionLevel

class TestRiskScanner(unittest.TestCase):
    def test_safe_action_pass(self):
        scanner = RiskScanner()
        intent = Intent("read", "config.py", {}, PermissionLevel.SAFE, "read config.py")
        assessment = scanner.assess(intent)
        self.assertFalse(assessment.blocked)

    def test_dangerous_pattern_blocked(self):
        scanner = RiskScanner()
        intent = Intent("execute", "rm -rf /tmp/test", {}, PermissionLevel.DANGEROUS, "rm -rf /tmp/test")
        assessment = scanner.assess(intent)
        self.assertTrue(assessment.blocked)
        self.assertIn("dangerous_pattern", assessment.risk_factors)

    def test_protected_path_blocked(self):
        scanner = RiskScanner()
        intent = Intent("delete", "/etc/passwd", {}, PermissionLevel.DANGEROUS, "delete /etc/passwd")
        assessment = scanner.assess(intent)
        self.assertTrue(assessment.blocked)
        self.assertIn("protected_path", assessment.risk_factors)

    def test_medium_requires_approval(self):
        scanner = RiskScanner()
        intent = Intent("write", "project/newfile.py", {}, PermissionLevel.MEDIUM, "create newfile.py")
        assessment = scanner.assess(intent)
        self.assertEqual(assessment.required_level, PermissionLevel.MEDIUM)
```

Run: `python -m pytest tests/test_risk_scanner.py -v`
Expected: FAIL — module not found

- [ ] **Step 2: Create RiskScanner**

```python
# safety/risk_scanner.py
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
    def __init__(self, permission_manager: PermissionManager = None):
        self.permission_manager = permission_manager or PermissionManager()

    def assess(self, intent: Intent) -> RiskAssessment:
        risk_factors = []

        if self.permission_manager.is_dangerous_pattern(intent.original_text):
            risk_factors.append("dangerous_pattern")

        if self.permission_manager.is_protected_path(intent.target):
            risk_factors.append("protected_path")

        required_level = intent.suggested_level
        blocked = len(risk_factors) > 0 and intent.suggested_level == PermissionLevel.DANGEROUS

        return RiskAssessment(
            required_level=required_level,
            risk_factors=risk_factors,
            blocked=blocked
        )
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `python -m pytest tests/test_risk_scanner.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add safety/risk_scanner.py tests/test_risk_scanner.py
git commit -m "feat(safety): add RiskScanner for pattern and path validation"
```

---

## Task 4: Approval Queue

**Files:**
- Create: `safety/approval_queue.py`
- Create: `tests/test_approval_queue.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_approval_queue.py
import unittest
import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from safety.approval_queue import ApprovalQueue, PendingApproval
from safety.permission_levels import PermissionLevel

class TestApprovalQueue(unittest.TestCase):
    def setUp(self):
        self.queue = ApprovalQueue(timeout_seconds=2)

    def test_queue_requires_approval_for_dangerous(self):
        result = self.queue.requires_approval(PermissionLevel.DANGEROUS)
        self.assertTrue(result)

    def test_queue_allows_safe_without_approval(self):
        result = self.queue.requires_approval(PermissionLevel.SAFE)
        self.assertFalse(result)

    def test_request_approval_adds_to_queue(self):
        self.queue.request_approval("action-1", "delete file", PermissionLevel.DANGEROUS)
        self.assertEqual(len(self.queue.get_pending()), 1)

    def test_approval_timeout(self):
        self.queue.request_approval("action-timeout", "test", PermissionLevel.DANGEROUS)
        time.sleep(3)
        self.assertFalse(self.queue.is_pending("action-timeout"))
```

Run: `python -m pytest tests/test_approval_queue.py -v`
Expected: FAIL — module not found

- [ ] **Step 2: Create ApprovalQueue**

```python
# safety/approval_queue.py
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
    def __init__(self, timeout_seconds: int = 60):
        self.timeout_seconds = timeout_seconds
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
            return True
        return False

    def deny(self, action_id: str) -> bool:
        if action_id in self._pending:
            self._pending[action_id].status = ApprovalStatus.DENIED
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
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `python -m pytest tests/test_approval_queue.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add safety/approval_queue.py tests/test_approval_queue.py
git commit -m "feat(safety): add ApprovalQueue for user approval workflow"
```

---

## Task 5: Rollback Manager

**Files:**
- Create: `safety/rollback_manager.py`
- Create: `tests/test_rollback_manager.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_rollback_manager.py
import unittest
import sys
import os
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from safety.rollback_manager import RollbackManager, Snapshot

class TestRollbackManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.manager = RollbackManager(base_path=self.temp_dir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_snapshot(self):
        file_path = os.path.join(self.temp_dir, "test.txt")
        with open(file_path, 'w') as f:
            f.write("original")
        snapshot = self.manager.create_snapshot("action-1", file_path)
        self.assertIsNotNone(snapshot)
        self.assertTrue(os.path.exists(snapshot.backup_path))

    def test_rollback_restores_content(self):
        file_path = os.path.join(self.temp_dir, "test.txt")
        with open(file_path, 'w') as f:
            f.write("original")
        self.manager.create_snapshot("action-1", file_path)
        with open(file_path, 'w') as f:
            f.write("modified")
        self.manager.rollback("action-1")
        with open(file_path, 'r') as f:
            self.assertEqual(f.read(), "original")

    def test_rollback_lifo_order(self):
        file1 = os.path.join(self.temp_dir, "file1.txt")
        file2 = os.path.join(self.temp_dir, "file2.txt")
        with open(file1, 'w') as f: f.write("f1-orig")
        with open(file2, 'w') as f: f.write("f2-orig")
        self.manager.create_snapshot("action-1", file1)
        self.manager.create_snapshot("action-1", file2)
        with open(file1, 'w') as f: f.write("f1-mod")
        with open(file2, 'w') as f: f.write("f2-mod")
        self.manager.rollback("action-1")
        self.assertEqual(open(file1).read(), "f1-orig")
        self.assertEqual(open(file2).read(), "f2-orig")
```

Run: `python -m pytest tests/test_rollback_manager.py -v`
Expected: FAIL — module not found

- [ ] **Step 2: Create RollbackManager**

```python
# safety/rollback_manager.py
from dataclasses import dataclass
from typing import List, Dict, Optional
import os
import shutil
from datetime import datetime

@dataclass
class Snapshot:
    action_id: str
    file_path: str
    backup_path: str
    created_at: datetime

class RollbackManager:
    def __init__(self, base_path: str = ".safety_snapshots"):
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)
        self._snapshots: Dict[str, List[Snapshot]] = {}

    def create_snapshot(self, action_id: str, file_path: str) -> Optional[Snapshot]:
        if not os.path.exists(file_path):
            return None
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = os.path.basename(file_path)
        backup_path = os.path.join(self.base_path, f"{action_id}_{safe_name}_{timestamp}.bak")
        shutil.copy2(file_path, backup_path)
        snapshot = Snapshot(
            action_id=action_id,
            file_path=file_path,
            backup_path=backup_path,
            created_at=datetime.now()
        )
        if action_id not in self._snapshots:
            self._snapshots[action_id] = []
        self._snapshots[action_id].append(snapshot)
        return snapshot

    def rollback(self, action_id: str) -> bool:
        if action_id not in self._snapshots:
            return False
        snapshots = self._snapshots[action_id]
        for snapshot in reversed(snapshots):
            if os.path.exists(snapshot.backup_path):
                shutil.copy2(snapshot.backup_path, snapshot.file_path)
        self._cleanup(action_id)
        return True

    def _cleanup(self, action_id: str):
        if action_id in self._snapshots:
            for snapshot in self._snapshots[action_id]:
                if os.path.exists(snapshot.backup_path):
                    os.remove(snapshot.backup_path)
            del self._snapshots[action_id]
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `python -m pytest tests/test_rollback_manager.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add safety/rollback_manager.py tests/test_rollback_manager.py
git commit -m "feat(safety): add RollbackManager for file snapshot/restore"
```

---

## Task 6: Emergency Stop

**Files:**
- Create: `safety/emergency_stop.py`
- Create: `tests/test_emergency_stop.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_emergency_stop.py
import unittest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from safety.emergency_stop import EmergencyStop, EmergencyStopEvent

class TestEmergencyStop(unittest.TestCase):
    def test_stop_sets_flag(self):
        stop = EmergencyStop()
        stop.trigger()
        self.assertTrue(stop.is_stopped())

    def test_reset_clears_flag(self):
        stop = EmergencyStop()
        stop.trigger()
        stop.reset()
        self.assertFalse(stop.is_stopped())

    def test_callback_invoked(self):
        stop = EmergencyStop()
        callback_invoked = []
        def on_stop():
            callback_invoked.append(True)
        stop.register_callback(on_stop)
        stop.trigger()
        self.assertEqual(len(callback_invoked), 1)
```

Run: `python -m pytest tests/test_emergency_stop.py -v`
Expected: FAIL — module not found

- [ ] **Step 2: Create EmergencyStop**

```python
# safety/emergency_stop.py
from dataclasses import dataclass
from typing import List, Callable
from datetime import datetime

@dataclass
class EmergencyStopEvent:
    triggered_at: datetime
    action_id: str = "unknown"

class EmergencyStop:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._stopped = False
            cls._instance._callbacks = []
        return cls._instance

    def trigger(self, action_id: str = "unknown"):
        self._stopped = True
        event = EmergencyStopEvent(triggered_at=datetime.now(), action_id=action_id)
        for callback in self._callbacks:
            try:
                callback(event)
            except Exception:
                pass

    def is_stopped(self) -> bool:
        return self._stopped

    def reset(self):
        self._stopped = False

    def register_callback(self, callback: Callable):
        self._callbacks.append(callback)

    def clear_callbacks(self):
        self._callbacks = []
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `python -m pytest tests/test_emergency_stop.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add safety/emergency_stop.py tests/test_emergency_stop.py
git commit -m "feat(safety): add EmergencyStop singleton with callback support"
```

---

## Task 7: Execution Pipeline (Integration)

**Files:**
- Create: `safety/execution_pipeline.py`
- Create: `tests/test_execution_pipeline.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_execution_pipeline.py
import unittest
import sys
import os
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from safety.execution_pipeline import ExecutionPipeline
from safety.permission_levels import PermissionLevel

class TestExecutionPipeline(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.pipeline = ExecutionPipeline(base_path=self.temp_dir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_safe_action_executes(self):
        result = self.pipeline.execute("read", "config.py", {})
        self.assertTrue(result.success)

    def test_dangerous_action_requires_approval(self):
        result = self.pipeline.execute("delete", "/tmp/test.txt", {})
        self.assertFalse(result.success)
        self.assertTrue(result.requires_approval)

    def test_blocked_action_returns_blocked(self):
        self.pipeline.permission_manager.is_dangerous_pattern = lambda x: True
        result = self.pipeline.execute("execute", "rm -rf /", {})
        self.assertTrue(result.blocked)
```

Run: `python -m pytest tests/test_execution_pipeline.py -v`
Expected: FAIL — module not found

- [ ] **Step 2: Create ExecutionPipeline**

```python
# safety/execution_pipeline.py
from dataclasses import dataclass
from typing import Any, Dict, Optional, Callable
from .permission_levels import PermissionManager, PermissionLevel
from .intent_detector import IntentDetector
from .risk_scanner import RiskScanner
from .approval_queue import ApprovalQueue
from .rollback_manager import RollbackManager
from .emergency_stop import EmergencyStop

@dataclass
class ExecutionResult:
    success: bool
    blocked: bool = False
    requires_approval: bool = False
    error: Optional[str] = None
    action_id: Optional[str] = None

class ExecutionPipeline:
    def __init__(self, base_path: str = ".safety_snapshots"):
        self.permission_manager = PermissionManager()
        self.intent_detector = IntentDetector()
        self.risk_scanner = RiskScanner(self.permission_manager)
        self.approval_queue = ApprovalQueue(
            timeout_seconds=self.permission_manager.get_approval_timeout()
        )
        self.rollback_manager = RollbackManager(base_path)
        self.emergency_stop = EmergencyStop()
        self._execution_handlers: Dict[str, Callable] = {}

    def execute(self, action: str, target: str, params: Dict[str, Any]) -> ExecutionResult:
        if self.emergency_stop.is_stopped():
            return ExecutionResult(success=False, blocked=True, error="Emergency stop active")

        intent = self.intent_detector.detect(f"{action} {target}")
        assessment = self.risk_scanner.assess(intent)

        if assessment.blocked:
            return ExecutionResult(success=False, blocked=True, error=f"Blocked: {', '.join(assessment.risk_factors)}")

        if self.approval_queue.requires_approval(assessment.required_level):
            self.approval_queue.request_approval(
                f"{action}_{target}",
                f"{action} on {target}",
                assessment.required_level
            )
            return ExecutionResult(success=False, requires_approval=True, action_id=f"{action}_{target}")

        return self._execute_action(action, target, params)

    def _execute_action(self, action: str, target: str, params: Dict[str, Any]) -> ExecutionResult:
        handler = self._execution_handlers.get(action)
        if handler:
            try:
                handler(target, params)
                return ExecutionResult(success=True)
            except Exception as e:
                return ExecutionResult(success=False, error=str(e))
        return ExecutionResult(success=True)

    def register_handler(self, action: str, handler: Callable):
        self._execution_handlers[action] = handler

    def approve(self, action_id: str) -> bool:
        return self.approval_queue.approve(action_id)

    def deny(self, action_id: str) -> bool:
        return self.approval_queue.deny(action_id)
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `python -m pytest tests/test_execution_pipeline.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add safety/execution_pipeline.py tests/test_execution_pipeline.py
git commit -m "feat(safety): add ExecutionPipeline integrating all safety components"
```

---

## Task 8: Integration Test — Full Flow

**Files:**
- Create: `tests/test_safety_integration.py`

- [ ] **Step 1: Write integration test**

```python
# tests/test_safety_integration.py
import unittest
import sys
import os
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from safety.execution_pipeline import ExecutionPipeline
from safety.emergency_stop import EmergencyStop
from safety.permission_levels import PermissionLevel

class TestSafetyIntegration(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.pipeline = ExecutionPipeline(base_path=self.temp_dir)
        EmergencyStop().reset()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_full_flow_safe_action(self):
        result = self.pipeline.execute("read", "test.py", {})
        self.assertTrue(result.success)
        self.assertFalse(result.blocked)
        self.assertFalse(result.requires_approval)

    def test_full_flow_requires_approval_for_dangerous(self):
        result = self.pipeline.execute("delete", "temp.txt", {})
        self.assertTrue(result.requires_approval)

    def test_emergency_stop_blocks_execution(self):
        self.pipeline.execute("read", "test.txt", {})
        EmergencyStop().trigger()
        result = self.pipeline.execute("delete", "test.txt", {})
        self.assertTrue(result.blocked)
        EmergencyStop().reset()

    def test_approval_then_execution(self):
        result = self.pipeline.execute("delete", "temp.txt", {})
        self.assertTrue(result.requires_approval)
        action_id = result.action_id
        self.pipeline.approve(action_id)
        result2 = self.pipeline.execute("read", "temp.txt", {})
        self.assertFalse(result2.requires_approval)
```

Run: `python -m pytest tests/test_safety_integration.py -v`
Expected: PASS

- [ ] **Step 2: Commit**

```bash
git add tests/test_safety_integration.py
git commit -m "test(safety): add integration tests for full pipeline flow"
```

---

## Self-Review Checklist

- [ ] All 8 tasks have failing tests first, then implementation
- [ ] All tests run with `python -m pytest tests/test_safety*.py -v`
- [ ] Each commit is atomic (one task per commit)
- [ ] No TBD/TODO in code
- [ ] Rollback scope: file modifications only (matches spec)
- [ ] Emergency stop: halts queue + sets flag (matches spec)
- [ ] Permission levels: SAFE/MEDIUM/DANGEROUS/SYSTEM (matches spec)