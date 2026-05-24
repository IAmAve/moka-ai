# MOKA AI Compliance Fix — Design Spec

**Date:** 2026-05-25
**Author:** MOKA AI Agent
**Status:** Approved for Implementation

---

## Context

MOKA AI has 7 compliance failures against its own architectural requirements:

1. **Tagalog-first is declared but not implemented** — only 4 string references exist, no infrastructure
2. **Placeholder/prototype code** in `model_abstraction.py`, `conversation_pipeline.py`, `personality_engine.py`
3. **Missing `__init__.py`** in `memory/` and `personality/` packages
4. **Logging not integrated per-module** — Logger exists but most modules don't import it
5. **Config not used per-module** — modules use hardcoded defaults instead of `Config`
6. **DI Container not consistently used** — services created directly instead of via container
7. **Unused files/folders** need to be identified and removed

This spec covers the full fix across 3 phases.

---

## Design Decisions

### 1. Tagalog Localization

**Approach:** Dictionary-based localization with future NLP upgrade path

**Structure:**
```
localization/
  __init__.py
  base_localizer.py      # Abstract interface for future NLP
  tagalog/
    __init__.py
    resources.json       # Phrase dictionary by intent/scenario
    localization_service.py
    phrases/
      greetings.json
      responses.json
      task_workflows.json
      emotional_support.json
```

**LocalizationService API:**
- `get_phrase(intent: str, context: dict = None) -> str` — returns localized phrase
- `get_greeting(style: str = "formal") -> str`
- `get_task_response(action: str, status: str) -> str`
- `set_preference(lang: str)` — "Tagalog" or "English"

**Upgrade path to NLP:** `base_localizer.py` defines the interface. Future implementation replaces `LocalizationService` with a proper NLP-based class without changing callers.

---

### 2. Model Abstraction — Injectable Backend

**Interface:**
```python
class LocalModelBackend(ABC):
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str: pass

    @abstractmethod
    def embed(self, text: str) -> list[float]: pass

    @abstractmethod
    def info(self) -> dict: pass
```

**LocalModelProvider** takes a backend at construction:
```python
class LocalModelProvider(ModelProvider):
    def __init__(self, backend: LocalModelBackend = None):
        self.backend = backend or DefaultLocalBackend()
```

**DefaultLocalBackend** provides the same placeholder behavior but cleanly separated from the interface. User swaps it via config injection (not hardcoded).

---

### 3. Conversation Pipeline — Full Implementation

Replaces all `pass` and `None` returns with:
- Context injection from `ContextManager`
- Memory injection via `MemoryInjector`
- Model routing via `ModelAbstraction`
- Tagalog-first via `LocalizationService`
- Tool routing stub (returns empty list, ready for plugin system)
- State management (returns actual state dict)

---

### 4. Personality Engine — Tagalog-Aware

- Holds reference to `LocalizationService`
- `get_personality_response()` calls `LocalizationService.get_phrase()` and applies mood/style modulation
- Mood-aware phrase selection (encouraging mood → encouraging Tagalog phrases)
- Removes all hardcoded string returns

---

### 5. Logging Per-Module

**Pattern:** Constructor injection with optional fallback
```python
from logger import Logger

class SomeModule:
    def __init__(self, logger: Logger = None):
        self.logger = logger if logger else Logger("some_module")
```

All modules in `memory/`, `personality/`, `core_runtime/` follow this pattern.

---

### 6. Config Per-Module

Modules read config at construction:
```python
def __init__(self, config: Config = None):
    self.config = config if config else Config()
    self._log_level = self.config.get("log_level", "INFO")
```

---

### 7. Missing `__init__.py` Files

```python
# memory/__init__.py
from .memory_interface import MemoryInterface
from .short_term_memory import ShortTermMemory
from .long_term_memory import LongTermMemory
from .behavior_memory import BehaviorMemory
from .project_memory import ProjectMemory

__all__ = ["MemoryInterface", "ShortTermMemory", "LongTermMemory", "BehaviorMemory", "ProjectMemory"]

# personality/__init__.py
from .personality_engine import PersonalityEngine, PersonalityProfile, PersonalityTraits, MoodState
from .conversation_memory import ConversationMemory
# ... other exports

__all__ = ["PersonalityEngine", ...]
```

---

### 8. Unused Files Cleanup

Files to **DELETE** (not linked from any working module):
- `test_project.py` — placeholder, superseded by `tests/`
- `docs/superpowers/plans/2026-05-23-safety-system-completion.md`
- `docs/superpowers/plans/2026-05-24-phase0-completion.md`
- Any `.pyc`, `__pycache__`, `*.py.bak` files

Files to **AUDIT** (verify before delete):
- Check if any `moka.py` or entry point references unused modules

---

## Phase Summary

| Phase | Items | Files Touched |
|-------|-------|---------------|
| 1 | Tagalog system, remove placeholders | `localization/*.py`, `localization/tagalog/*.json`, `core_runtime/model_abstraction.py`, `core_runtime/conversation_pipeline.py`, `personality/personality_engine.py` |
| 2 | Missing `__init__.py`, logger integration | `memory/`, `personality/`, all modules in `core_runtime/` |
| 3 | Unused file deletion | `test_project.py`, plan docs |

---

## Verification

After Phase 1:
- `grep -r "Generated response" moka-ai/` returns nothing
- `localization/tagalog/resources.json` has 20+ Tagalog phrases
- `PersonalityEngine.get_personality_response()` calls `LocalizationService`

After Phase 2:
- `ls memory/__init__.py personality/__init__.py` both exist
- All modules in `memory/`, `personality/`, `core_runtime/` import and use Logger

After Phase 3:
- No placeholder files remain
- Git status shows only production code