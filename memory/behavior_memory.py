"""
Behavior memory service for MOKA AI
"""

from typing import Any, Dict, Optional
import json
import os
from datetime import datetime


class BehaviorMemory:
    """Behavior memory service for MOKA AI"""

    def __init__(self, storage_file: str = "behavior_memory.json", logger=None):
        self._logger = logger
        if logger and hasattr(logger, 'info'):
            self._log = logger.info
        elif callable(logger):
            self._log = logger
        else:
            self._log = lambda m: None
        self.storage_file = storage_file
        self.memory_store: Dict[str, Any] = {}
        self._load_memory()

    def store_behavior_pattern(self, pattern_id: str, behavior_data: Dict[str, Any]) -> bool:
        """Store behavior pattern data"""
        try:
            self.memory_store[pattern_id] = {
                "data": behavior_data,
                "timestamp": datetime.now().isoformat(),
            }
            self._save_memory()
            self._log(f"Stored behavior pattern '{pattern_id}'")
            return True
        except Exception as e:
            if self._logger:
                self._logger.error(f"Failed to store behavior pattern: {e}")
            return False

    def retrieve_behavior_pattern(self, pattern_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve behavior pattern data"""
        try:
            self._load_memory()
            result = self.memory_store.get(pattern_id)
            if result:
                self._log(f"Retrieved behavior pattern '{pattern_id}'")
            return result
        except Exception as e:
            if self._logger:
                self._logger.error(f"Failed to retrieve behavior pattern: {e}")
            return None

    def _save_memory(self):
        """Save memory to persistent storage"""
        try:
            with open(self.storage_file, "w") as f:
                json.dump(self.memory_store, f)
        except Exception as e:
            if self._logger:
                self._logger.error(f"Failed to save behavior memory: {e}")

    def _load_memory(self):
        """Load memory from persistent storage"""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, "r") as f:
                    self.memory_store = json.load(f)
        except Exception as e:
            if self._logger:
                self._logger.warning(f"Could not load behavior memory: {e}")
            self.memory_store = {}

    def clear_all(self):
        """Clear all behavior memory"""
        self.memory_store.clear()
        self._save_memory()
        self._log("Cleared all behavior memory")
        return True