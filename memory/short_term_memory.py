"""
Memory Services for MOKA AI
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import json
import os


class ShortTermMemory:
    """Short-term memory service for MOKA AI"""

    def __init__(self, max_items: int = 100, logger=None):
        self._logger = logger
        if logger and hasattr(logger, 'info'):
            self._log = lambda m: logger.info(m)
        else:
            self._log = lambda m: None
        self.memory_store: dict = {}
        self.max_items = max_items
        self.access_count: dict = {}

    def store(self, key: str, value: Any, context: Dict[str, Any] = None) -> bool:
        """Store information in short-term memory"""
        try:
            if len(self.memory_store) >= self.max_items:
                self._prune_memory()

            self.memory_store[key] = {
                "value": value,
                "timestamp": datetime.now(),
                "context": context or {},
            }

            self.access_count[key] = self.access_count.get(key, 0) + 1
            self._log(f"Stored key '{key}' in short-term memory")
            return True
        except Exception as e:
            if self._logger:
                self._logger.error(f"Failed to store in short-term memory: {e}")
            return False

    def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve information from short-term memory"""
        try:
            if key in self.memory_store:
                self.access_count[key] = self.access_count.get(key, 0) + 1
                self._log(f"Retrieved key '{key}' from short-term memory")
                return self.memory_store[key]["value"]
            return None
        except Exception as e:
            if self._logger:
                self._logger.error(f"Failed to retrieve from short-term memory: {e}")
            return None

    def delete(self, key: str) -> bool:
        """Delete information from short-term memory"""
        try:
            if key in self.memory_store:
                del self.memory_store[key]
                if key in self.access_count:
                    del self.access_count[key]
                self._log(f"Deleted key '{key}' from short-term memory")
                return True
            return False
        except Exception as e:
            if self._logger:
                self._logger.error(f"Failed to delete from short-term memory: {e}")
            return False

    def _prune_memory(self):
        """Remove least accessed items when memory is full"""
        if self.memory_store and self.access_count:
            least_accessed = min(self.access_count.items(), key=lambda x: x[1])
            del self.memory_store[least_accessed[0]]
            del self.access_count[least_accessed[0]]

    def clear_memory(self):
        """Clear all short-term memory"""
        self.memory_store.clear()
        self.access_count.clear()
        self._log("Cleared all short-term memory")