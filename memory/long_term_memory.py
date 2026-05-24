"""
Long-term memory service for MOKA AI
"""

from typing import Any, Dict, Optional
import json
import os
from datetime import datetime


class LongTermMemory:
    """Long-term memory service for MOKA AI"""

    def __init__(self, storage_file: str = "memory_long_term.json", logger=None):
        self._logger = logger
        self._log = logger.info if logger else lambda m: None
        self.storage_file = storage_file
        self.memory_store: Dict[str, Any] = {}
        self._load_memory()

    def store(self, key: str, value: Any, metadata: Dict[str, Any] = None) -> bool:
        """Store information in long-term memory"""
        try:
            self._load_memory()

            self.memory_store[key] = {
                "value": value,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {},
            }

            self._save_memory()
            self._log(f"Stored key '{key}' in long-term memory")
            return True
        except Exception as e:
            if self._logger:
                self._logger.error(f"Failed to store in long-term memory: {e}")
            return False

    def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve information from long-term memory"""
        try:
            self._load_memory()
            if key in self.memory_store:
                self._log(f"Retrieved key '{key}' from long-term memory")
                return self.memory_store[key].get("value")
            return None
        except Exception as e:
            if self._logger:
                self._logger.error(f"Failed to retrieve from long-term memory: {e}")
            return None

    def _save_memory(self):
        """Save memory to persistent storage"""
        try:
            with open(self.storage_file, "w") as f:
                json.dump(self.memory_store, f)
        except Exception as e:
            if self._logger:
                self._logger.error(f"Failed to save long-term memory: {e}")

    def _load_memory(self):
        """Load memory from persistent storage"""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, "r") as f:
                    self.memory_store = json.load(f)
        except Exception as e:
            if self._logger:
                self._logger.warning(f"Could not load long-term memory: {e}")
            self.memory_store = {}

    def clear_all(self):
        """Clear all long-term memory"""
        self.memory_store.clear()
        self._save_memory()
        self._log("Cleared all long-term memory")
        return True