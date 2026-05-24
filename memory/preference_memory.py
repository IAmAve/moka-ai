"""
Preference Memory Module for MOKA AI

Stores user preferences including language settings, communication style,
// and companion behavior defaults. Persists across sessions.
"""

from typing import Any, Dict, Optional
import json
import os
from datetime import datetime


class PreferenceMemory:
    """Preference memory service — stores user settings and defaults."""

    def __init__(self, storage_file: str = "preference_memory.json", logger=None):
        self._logger = logger
        self._log = logger.info if logger else lambda m: None
        self.storage_file = storage_file
        self.memory_store: Dict[str, Any] = {}
        self._load_memory()

    def store_preference(self, key: str, value: Any, metadata: Dict[str, Any] = None) -> bool:
        """Store a user preference."""
        try:
            self.memory_store[key] = {
                "value": value,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {},
            }
            self._save_memory()
            self._log(f"Stored preference '{key}' = {value}")
            return True
        except Exception as e:
            if self._logger:
                self._logger.error(f"Failed to store preference: {e}")
            return False

    def retrieve_preference(self, key: str, default: Any = None) -> Any:
        """Retrieve a user preference, returning default if not set."""
        try:
            self._load_memory()
            result = self.memory_store.get(key, {}).get("value")
            if result is not None:
                self._log(f"Retrieved preference '{key}'")
            return result if result is not None else default
        except Exception as e:
            if self._logger:
                self._logger.error(f"Failed to retrieve preference: {e}")
            return default

    def delete_preference(self, key: str) -> bool:
        """Remove a user preference."""
        try:
            if key in self.memory_store:
                del self.memory_store[key]
                self._save_memory()
                self._log(f"Deleted preference '{key}'")
                return True
            return False
        except Exception as e:
            if self._logger:
                self._logger.error(f"Failed to delete preference: {e}")
            return False

    def get_all_preferences(self) -> Dict[str, Any]:
        """Return all stored preferences as a flat dict."""
        try:
            self._load_memory()
            return {k: v.get("value") for k, v in self.memory_store.items()}
        except Exception as e:
            if self._logger:
                self._logger.error(f"Failed to get all preferences: {e}")
            return {}

    def set_defaults(self, defaults: Dict[str, Any]) -> bool:
        """Set multiple defaults — only writes if key not already present."""
        try:
            self._load_memory()
            for key, value in defaults.items():
                if key not in self.memory_store:
                    self.memory_store[key] = {
                        "value": value,
                        "timestamp": datetime.now().isoformat(),
                        "metadata": {"source": "default"},
                    }
            self._save_memory()
            self._log(f"Set {len(defaults)} default preferences")
            return True
        except Exception as e:
            if self._logger:
                self._logger.error(f"Failed to set defaults: {e}")
            return False

    def _save_memory(self):
        """Save memory to persistent storage."""
        try:
            with open(self.storage_file, "w") as f:
                json.dump(self.memory_store, f)
        except Exception as e:
            if self._logger:
                self._logger.error(f"Failed to save preference memory: {e}")

    def _load_memory(self):
        """Load memory from persistent storage."""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, "r") as f:
                    self.memory_store = json.load(f)
        except Exception as e:
            if self._logger:
                self._logger.warning(f"Could not load preference memory: {e}")
            self.memory_store = {}

    def clear_all(self):
        """Clear all preferences (use with caution)."""
        self.memory_store.clear()
        self._save_memory()
        self._log("Cleared all preference memory")
        return True