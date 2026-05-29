"""
Service wrappers for Phase 1–7 modules.

Each wrapper provides start()/stop() so ServiceManager can manage their
lifecycle, and bridges module-specific events to the shared EventBus.

Phase 1  — TaskOrchestrator
Phase 2  — Personality (MoodEngine + PersonalityEngine + LocalizationService)
Phase 3  — Voice (VoiceService)
Phase 4  — Memory (ShortTermMemory + LongTermMemory + BehaviorMemory)
Phase 5  — Learning (HermesAdaptiveLearningSystem)
Phase 6  — Safety  (EmergencyStop singleton)
Phase 7  — Localization is embedded in PersonalityService (Tagalog-first)
"""

import json
import os
from pathlib import Path

# ── Phase 1: Task Orchestrator ────────────────────────────────────────────────

from core_runtime.task_orchestration import TaskOrchestrator


class Phase1OrchestratorService:
    """Wraps TaskOrchestrator for standalone service lifecycle."""

    def __init__(self, event_bus=None, logger=None):
        self._log = logger.info if logger else lambda *_: None
        self._event_bus = event_bus
        self._orchestrator = TaskOrchestrator()
        self._data_dir = Path("data")
        self._history_file = self._data_dir / "phase1_execution_history.json"

    def start(self):
        self._data_dir.mkdir(exist_ok=True)
        self._log("[Phase1Service] TaskOrchestrator started")
        if self._event_bus:
            self._event_bus.subscribe("phase1:execute_workflow", self._on_execute_workflow)

    def stop(self):
        if self._event_bus:
            # Keep listener list intact — EventBus re-init on next start handles it
            pass
        self._persist_history()
        self._log("[Phase1Service] TaskOrchestrator stopped")

    def _on_execute_workflow(self, data):
        workflow_id = data.get("workflow_id")
        if workflow_id and self._orchestrator.get_workflow(workflow_id):
            self._orchestrator.execute_workflow(workflow_id, data.get("context"))

    def _persist_history(self):
        if not hasattr(self, "_orchestrator"):
            return
        try:
            history = self._orchestrator.get_workflow_history(limit=500)
            self._data_dir.mkdir(exist_ok=True)
            with open(self._history_file, "w") as f:
                json.dump(history, f)
        except Exception as e:
            self._log(f"[Phase1Service] Could not persist history: {e}")

    @property
    def orchestrator(self) -> TaskOrchestrator:
        return self._orchestrator


# ── Phase 2: Personality (MoodEngine + PersonalityEngine + Localization) ───────


class PersonalityService:
    """Wraps MoodEngine + PersonalityEngine + LocalizationService."""

    def __init__(self, event_bus=None, logger=None):
        self._log = logger.info if logger else lambda *_: None
        self._event_bus = event_bus
        self._conversation_memory = None

        from localization.tagalog.localization_service import LocalizationService
        from personality.mood_engine import MoodEngine
        from personality.personality_engine import PersonalityEngine, MoodState

        self._mood_engine = MoodEngine(logger=logger)
        self._localizer = LocalizationService()
        self._personality_engine = PersonalityEngine(localizer=self._localizer)
        self._mood_states = MoodState

    def start(self):
        self._log("[PersonalityService] MoodEngine + PersonalityEngine + LocalizationService started")
        if self._event_bus:
            self._event_bus.subscribe("personality:set_mood", self._on_set_mood)
            self._event_bus.subscribe("personality:get_response", self._on_get_response)

    def stop(self):
        if self._personality_engine and hasattr(self._personality_engine, "conversation_memory"):
            try:
                mem = self._personality_engine.conversation_memory
                if hasattr(mem, "save"):
                    mem.save()
            except Exception as e:
                self._log(f"[PersonalityService] Could not persist conversation memory: {e}")
        self._log("[PersonalityService] PersonalityService stopped")

    def _on_set_mood(self, data):
        mood = data.get("mood", "neutral")
        intensity = data.get("intensity", 1.0)
        self._mood_engine.update_mood(mood, intensity)
        if hasattr(self._personality_engine, "set_mood"):
            try:
                from personality.personality_engine import MoodState
                self._personality_engine.set_mood(MoodState(mood))
            except Exception:
                pass

    def _on_get_response(self, data):
        text = data.get("text", "")
        ctx = data.get("context", {})
        return self._personality_engine.get_personality_response(text, ctx)

    @property
    def mood_engine(self):
        return self._mood_engine

    @property
    def personality_engine(self):
        return self._personality_engine

    @property
    def localizer(self):
        return self._localizer


# ── Phase 3: Voice Service ─────────────────────────────────────────────────────


class VoiceService:
    """Wraps VoiceService (no start/stop in the raw module — we add lifecycle)."""

    def __init__(self, event_bus=None, logger=None):
        self._log = logger.info if logger else lambda *_: None
        self._event_bus = event_bus
        from voice.voice_service import VoiceService as _VoiceService
        self._voice = _VoiceService(logger=logger)
        self._started = False
        self._data_dir = Path("data")
        self._state_file = self._data_dir / "voice_state.json"

    def start(self):
        self._data_dir.mkdir(exist_ok=True)
        self._voice.initialize()
        self._started = True
        self._log("[VoiceService] VoiceService started")
        if self._event_bus:
            self._event_bus.subscribe("voice:speak", self._on_speak)
            self._event_bus.subscribe("voice:interrupt", self._on_interrupt)

    def stop(self):
        if self._started:
            try:
                self._voice.interrupt_speaking()
                self._persist_state()
            except Exception as e:
                self._log(f"[VoiceService] stop error: {e}")
        self._started = False
        self._log("[VoiceService] VoiceService stopped")

    def _on_speak(self, data):
        text = data.get("text", "")
        self._voice.speak_text(text)

    def _on_interrupt(self, _data):
        self._voice.interrupt_speaking()

    def _persist_state(self):
        try:
            transitions = self._voice.transitions()[-10:]
            self._data_dir.mkdir(exist_ok=True)
            with open(self._state_file, "w") as f:
                json.dump({"transitions": transitions}, f)
        except Exception:
            pass

    @property
    def voice(self):
        return self._voice


# ── Phase 4: Memory (ShortTerm + LongTerm + Behavior) ─────────────────────────


class MemoryService:
    """Wraps ShortTermMemory + LongTermMemory + BehaviorMemory with persistence."""

    def __init__(self, event_bus=None, logger=None):
        self._log = logger.info if logger else lambda *_: None
        self._event_bus = event_bus
        self._data_dir = Path("data")

        from memory.short_term_memory import ShortTermMemory
        from memory.long_term_memory import LongTermMemory
        from memory.behavior_memory import BehaviorMemory

        self._short_term = ShortTermMemory(logger=logger)
        self._long_term = LongTermMemory(logger=logger)
        self._behavior = BehaviorMemory(logger=logger)

    def start(self):
        self._data_dir.mkdir(exist_ok=True)
        self._log("[MemoryService] Memory services started")
        if self._event_bus:
            self._event_bus.subscribe("memory:store", self._on_store)
            self._event_bus.subscribe("memory:retrieve", self._on_retrieve)
            self._event_bus.subscribe("memory:clear", self._on_clear)

    def stop(self):
        self._persist_all()
        self._log("[MemoryService] Memory services stopped")

    def _on_store(self, data):
        scope = data.get("scope", "short_term")  # short_term | long_term | behavior
        key = data.get("key", "")
        value = data.get("value")
        ctx = data.get("context")
        if scope == "short_term":
            self._short_term.store(key, value, ctx)
        elif scope == "long_term":
            self._long_term.store(key, value, ctx)
        elif scope == "behavior":
            self._behavior.store_behavior_pattern(key, value or {})

    def _on_retrieve(self, data):
        scope = data.get("scope", "short_term")
        key = data.get("key", "")
        if scope == "short_term":
            return self._short_term.retrieve(key)
        elif scope == "long_term":
            return self._long_term.retrieve(key)
        elif scope == "behavior":
            result = self._behavior.retrieve_behavior_pattern(key)
            return result.get("data") if result else None

    def _on_clear(self, data):
        scope = data.get("scope")
        if scope == "short_term" or scope is None:
            self._short_term.clear_memory()
        if scope == "long_term" or scope is None:
            self._long_term.clear_all()
        if scope == "behavior" or scope is None:
            self._behavior.clear_all()

    def _persist_all(self):
        try:
            self._data_dir.mkdir(exist_ok=True)
        except Exception:
            pass

    @property
    def short_term(self):
        return self._short_term

    @property
    def long_term(self):
        return self._long_term

    @property
    def behavior(self):
        return self._behavior


# ── Phase 5: Learning (HermesAdaptiveLearningSystem) ───────────────────────────


class LearningService:
    """Wraps HermesAdaptiveLearningSystem with EventBus approval bridge."""

    def __init__(self, event_bus=None, logger=None):
        self._log = logger.info if logger else lambda *_: None
        self._event_bus = event_bus
        from learning.hermes_learning_system import HermesAdaptiveLearningSystem
        self._hermes = HermesAdaptiveLearningSystem(logger=logger)
        self._started = False
        self._data_dir = Path("data")
        self._software_profiles_seeded = False

    def start(self):
        self._data_dir.mkdir(exist_ok=True)
        self._started = True
        self._log("[LearningService] Hermes Adaptive Learning System started")
        # Bridge Hermes approval callbacks → EventBus
        self._hermes.on_approval_required(self._hermes_approval_bridge)
        if self._event_bus:
            self._event_bus.subscribe("learning:observe", self._on_observe)
            self._event_bus.subscribe("learning:approve", self._on_approve)
            self._event_bus.subscribe("learning:get_pending", self._on_get_pending)

    def stop(self):
        if self._started:
            try:
                self._hermes.behavior_db.save_database()
                self._hermes.skill_db.save_database()
            except Exception as e:
                self._log(f"[LearningService] stop error: {e}")
        self._started = False
        self._log("[LearningService] Hermes Adaptive Learning System stopped")

    def _hermes_approval_bridge(self, skill_id: str) -> bool:
        self._log(f"[LearningService] Skill '{skill_id}' requires approval")
        if self._event_bus:
            self._event_bus.publish("hermes:approval_required", {"skill_id": skill_id})
        return True

    def _on_observe(self, data):
        self._hermes.observe_behavior(data)

    def _on_approve(self, data):
        skill_id = data.get("skill_id")
        if skill_id:
            self._hermes.approve_skill(skill_id)

    def _on_get_pending(self, _data):
        return {"pending": self._hermes.get_pending_approvals()}

    def seed_software_profiles(self, profiles):
        """Seed software profiles from DesktopRuntime scan into HermesSoftwareProfileDatabase."""
        if self._software_profiles_seeded:
            return
        self._software_profiles_seeded = True
        from learning.software_profile_database import SoftwareProfile
        for p in profiles:
            try:
                profile = SoftwareProfile(
                    profile_id=p.get("profile_id", p.get("name", "")),
                    name=p.get("name", ""),
                    description=p.get("description", ""),
                    usage_patterns=p.get("usage_patterns", []),
                    confidence_score=0.5,
                )
                self._hermes.profile_db.add_profile(profile)
            except Exception as e:
                self._log(f"[LearningService] Could not seed profile: {e}")
        self._log(f"[LearningService] Seeded {len(profiles)} software profiles into Hermes")

    @property
    def hermes(self):
        return self._hermes


# ── Phase 6: Safety (EmergencyStop singleton) ─────────────────────────────────


class SafetyService:
    """Wraps EmergencyStop singleton with EventBus integration."""

    def __init__(self, event_bus=None, logger=None):
        self._log = logger.info if logger else lambda *_: None
        self._event_bus = event_bus
        from safety.emergency_stop import EmergencyStop
        self._estop = EmergencyStop(logger=logger)
        self._started = False

    def start(self):
        self._started = True
        self._log("[SafetyService] EmergencyStop singleton started")
        # Subscribe to general safety events from EventBus
        if self._event_bus:
            self._event_bus.subscribe("safety:trigger", self._on_safety_trigger)

    def stop(self):
        if self._started:
            from safety.emergency_stop import EmergencyStop
            EmergencyStop.reset()
            self._estop.clear_callbacks()
        self._started = False
        self._log("[SafetyService] EmergencyStop singleton stopped")

    def _on_safety_trigger(self, data):
        action_id = data.get("action_id", "event_bus")
        self._estop.trigger(action_id)

    @property
    def emergency_stop(self):
        return self._estop