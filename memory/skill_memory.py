"""
Skill Memory Module for MOKA AI

Stores learned skills, their proficiency levels, and usage history.
Provides skill tracking for the companion's teaching and coaching capabilities.
"""

from typing import Any, Dict, List, Optional
import json
import os
from datetime import datetime


class SkillMemory:
    """Skill memory service — tracks learned skills and proficiency."""

    def __init__(self, storage_file: str = "skill_memory.json", logger=None):
        self._logger = logger
        self._log = logger.info if logger else lambda m: None
        self.storage_file = storage_file
        self.memory_store: Dict[str, Any] = {}
        self._load_memory()

    def store_skill(
        self,
        skill_id: str,
        skill_data: Dict[str, Any],
        proficiency: float = 0.0,
    ) -> bool:
        """Store a skill with proficiency level (0.0–1.0)."""
        try:
            self.memory_store[skill_id] = {
                "data": skill_data,
                "proficiency": proficiency,
                "timestamp": datetime.now().isoformat(),
                "usage_count": self.memory_store.get(skill_id, {}).get("usage_count", 0),
            }
            self._save_memory()
            self._log(f"Stored skill '{skill_id}' with proficiency {proficiency}")
            return True
        except Exception as e:
            if self._logger:
                self._logger.error(f"Failed to store skill: {e}")
            return False

    def retrieve_skill(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve skill data and proficiency."""
        try:
            self._load_memory()
            result = self.memory_store.get(skill_id)
            if result:
                self._log(f"Retrieved skill '{skill_id}'")
            return result
        except Exception as e:
            if self._logger:
                self._logger.error(f"Failed to retrieve skill: {e}")
            return None

    def update_proficiency(self, skill_id: str, proficiency: float) -> bool:
        """Update the proficiency level of a stored skill."""
        try:
            self._load_memory()
            if skill_id in self.memory_store:
                self.memory_store[skill_id]["proficiency"] = proficiency
                self.memory_store[skill_id]["timestamp"] = datetime.now().isoformat()
                self._save_memory()
                self._log(f"Updated proficiency of '{skill_id}' to {proficiency}")
                return True
            return False
        except Exception as e:
            if self._logger:
                self._logger.error(f"Failed to update skill proficiency: {e}")
            return False

    def increment_usage(self, skill_id: str) -> bool:
        """Increment usage counter for a skill."""
        try:
            self._load_memory()
            if skill_id in self.memory_store:
                self.memory_store[skill_id]["usage_count"] = (
                    self.memory_store[skill_id].get("usage_count", 0) + 1
                )
                self._save_memory()
                return True
            return False
        except Exception as e:
            if self._logger:
                self._logger.error(f"Failed to increment skill usage: {e}")
            return False

    def list_skills(self, min_proficiency: float = 0.0) -> List[str]:
        """List all skill IDs optionally filtered by minimum proficiency."""
        try:
            self._load_memory()
            return [
                sid
                for sid, data in self.memory_store.items()
                if data.get("proficiency", 0.0) >= min_proficiency
            ]
        except Exception as e:
            if self._logger:
                self._logger.error(f"Failed to list skills: {e}")
            return []

    def _save_memory(self):
        """Save memory to persistent storage."""
        try:
            with open(self.storage_file, "w") as f:
                json.dump(self.memory_store, f)
        except Exception as e:
            if self._logger:
                self._logger.error(f"Failed to save skill memory: {e}")

    def _load_memory(self):
        """Load memory from persistent storage."""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, "r") as f:
                    self.memory_store = json.load(f)
        except Exception as e:
            if self._logger:
                self._logger.warning(f"Could not load skill memory: {e}")
            self.memory_store = {}

    def clear_all(self):
        """Clear all skill memory."""
        self.memory_store.clear()
        self._save_memory()
        self._log("Cleared all skill memory")
        return True