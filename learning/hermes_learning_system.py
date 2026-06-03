"""
Hermes Adaptive Learning System for MOKA AI

Observe, draft, confidence-score, test, approve, activate — never
auto-executes learned behaviors without user approval.
"""

import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from learning.behavior_database import BehaviorDatabase, BehaviorPattern
from learning.skill_database import SkillDatabase, Skill
from learning.software_profile_database import SoftwareProfileDatabase
from learning.confidence_scoring import ConfidenceScoringSystem
from learning.testing_framework import BehaviorTestingFramework
from learning.dashboard import LearningDashboard


class HermesAdaptiveLearningSystem:
    """Main orchestrator for the Hermes adaptive learning pipeline."""

    def __init__(self, logger: Callable[[str], None] = None):
        self._logger = logger
        self._log = logger.info if logger else lambda m: None
        self.behavior_db = BehaviorDatabase(logger=logger)
        self.skill_db = SkillDatabase(logger=logger)
        self.profile_db = SoftwareProfileDatabase(logger=logger)
        self.confidence_system = ConfidenceScoringSystem()
        self.testing_framework = BehaviorTestingFramework(logger=logger)
        self.dashboard = LearningDashboard()
        self._pending_behaviors: Dict[str, Dict[str, Any]] = {}
        self._inactive_skills: Dict[str, Skill] = {}
        self._approval_handlers: List[Callable[[str], bool]] = []
        self._log("Hermes Adaptive Learning System initialized")

    # ── Pipeline steps ────────────────────────────────────────────────────────

    def observe_behavior(self, behavior_data: Dict[str, Any]) -> bool:
        """Step 1 — Observe and record a behavior pattern."""
        try:
            pattern_id = behavior_data.get("pattern_id", str(uuid.uuid4()))
            confidence_score = self.confidence_system.calculate_confidence_score(behavior_data)

            pattern = BehaviorPattern(
                pattern_id=pattern_id,
                behavior_type=behavior_data.get("type", "unknown"),
                frequency=behavior_data.get("frequency", 1),
                last_observed=datetime.now(),
                context_data=behavior_data.get("context", {}),
                confidence_score=confidence_score,
                is_approved=False,
                is_active=True,
            )

            self.behavior_db.add_behavior_pattern(pattern)
            self._pending_behaviors[pattern_id] = behavior_data
            self._log(f"Observed behavior '{pattern_id}' with confidence {confidence_score:.2f}")
            self._update_dashboard()
            return True
        except Exception as e:
            self._log(f"Error observing behavior: {e}")
            return False

    def draft_behavior(self, behavior_pattern: Dict[str, Any]) -> Optional[str]:
        """Step 2 — Draft a new behavior from observed patterns."""
        try:
            pattern_id = behavior_pattern.get("pattern_id", str(uuid.uuid4()))
            confidence_score = self.confidence_system.calculate_confidence_score(behavior_pattern)

            pattern = BehaviorPattern(
                pattern_id=pattern_id,
                behavior_type=behavior_pattern.get("type", "draft"),
                frequency=behavior_pattern.get("frequency", 0),
                last_observed=datetime.now(),
                context_data=behavior_pattern.get("context", {}),
                confidence_score=confidence_score,
                is_approved=False,
                is_active=True,
            )

            self.behavior_db.add_behavior_pattern(pattern)
            self._pending_behaviors[pattern_id] = behavior_pattern
            self._log(f"Drafted behavior '{pattern_id}' with confidence {confidence_score:.2f}")
            return pattern_id
        except Exception as e:
            self._log(f"Error drafting behavior: {e}")
            return None

    def _get_current_confidence(self, pattern_id: str, pattern: BehaviorPattern) -> float:
        """Recalculate confidence score based on the most recent data."""
        # Try to use full data from pending behaviors if available
        data = self._pending_behaviors.get(pattern_id)
        if not data:
            # Fallback to constructing a dict from the stored BehaviorPattern
            data = {
                "frequency": pattern.frequency,
                "last_observed": pattern.last_observed.isoformat() if hasattr(pattern.last_observed, "isoformat") else pattern.last_observed,
                "context_data": pattern.context_data,
                "behavior_type": pattern.behavior_type
            }
        return self.confidence_system.calculate_confidence_score(data)

    def test_behavior(self, behavior_pattern: Dict[str, Any]) -> bool:
        """Step 4 — Test drafted behavior for safety and effectiveness."""
        try:
            pattern_id = behavior_pattern.get("pattern_id")
            if not pattern_id:
                return False

            behavior_data = self._pending_behaviors.get(pattern_id, behavior_pattern)
            test_cases = behavior_pattern.get("test_cases", [behavior_data])

            results = self.testing_framework.run_comprehensive_behavior_test(pattern_id, test_cases)
            passed = results["tests_passed"] > 0 and results["tests_failed"] == 0
            is_safe = self.testing_framework.validate_behavior_safety(behavior_data)

            if passed and is_safe:
                existing = self.behavior_db.get_behavior_pattern(pattern_id)
                if existing:
                    # Use dynamic confidence as base for the boost
                    current_conf = self._get_current_confidence(pattern_id, existing)
                    existing.confidence_score = min(1.0, current_conf + 0.1)
                    self.behavior_db.update_behavior_pattern(pattern_id, existing)
                    self._log(f"Behavior '{pattern_id}' passed tests — confidence boosted to {existing.confidence_score:.2f}")

            return passed and is_safe
        except Exception as e:
            self._log(f"Error testing behavior: {e}")
            return False

    def learn_and_adapt(self, new_behavior: Dict[str, Any]) -> bool:
        """Step 5 — Promote tested behavior to a skill (requires approval)."""
        try:
            pattern_id = new_behavior.get("pattern_id")
            if not pattern_id:
                return False

            pattern = self.behavior_db.get_behavior_pattern(pattern_id)
            if not pattern:
                return False

            # Dynamic re-evaluation: Recalculate confidence at the moment of promotion
            current_confidence = self._get_current_confidence(pattern_id, pattern)

            if current_confidence < self.confidence_system.learning_threshold:
                self._log(
                    f"Behavior '{pattern_id}' rejected — dynamic confidence "
                    f"{current_confidence:.2f} below threshold"
                )
                return False

            skill = Skill(
                skill_id=pattern_id,
                name=new_behavior.get("name", f"Learned Skill {pattern_id[:8]}"),
                description=new_behavior.get("description", pattern.behavior_type),
                code=new_behavior.get("code", ""),
                dependencies=new_behavior.get("dependencies", []),
                is_approved=False,
                confidence_score=current_confidence,
                usage_count=0,
            )

            self.skill_db.add_skill(skill)
            self._inactive_skills[skill.skill_id] = skill
            self._log(f"Skill '{skill.skill_id}' created with confidence {current_confidence:.2f} — awaiting approval")
            self._notify_approval_handlers(skill.skill_id)
            self._update_dashboard()
            return True
        except Exception as e:
            self._log(f"Error learning behavior: {e}")
            return False

    # ── Approval ──────────────────────────────────────────────────────────────

    def approve_skill(self, skill_id: str) -> bool:
        """Approve a learned skill — activates it only after approval."""
        try:
            skill = self.skill_db.get_skill(skill_id)
            if not skill:
                return False
            skill.is_approved = True
            self.skill_db.update_skill(skill_id, skill)
            if skill_id in self._inactive_skills:
                del self._inactive_skills[skill_id]
            self._log(f"Skill '{skill_id}' approved and activated")
            return True
        except Exception as e:
            self._log(f"Error approving skill: {e}")
            return False

    def get_pending_approvals(self) -> List[str]:
        """Return skill IDs awaiting approval."""
        return list(self._inactive_skills.keys())

    def on_approval_required(self, handler: Callable[[str], bool]) -> None:
        """Register a callback notified when a new skill needs approval."""
        self._approval_handlers.append(handler)

    def _notify_approval_handlers(self, skill_id: str) -> None:
        for handler in self._approval_handlers:
            try:
                handler(skill_id)
            except Exception as e:
                self._log(f"Approval handler error: {e}")

    def _update_dashboard(self) -> None:
        try:
            self.dashboard.update_dashboard(
                behavior_count=len(self.behavior_db.get_all_behavior_patterns()),
                skill_count=len(self.skill_db.get_all_skills()),
                profile_count=len(self.profile_db.profiles),
            )
        except Exception:
            pass