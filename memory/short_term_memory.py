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

    def __init__(self, max_items: int = 100):
        self.memory_store = {}
        self.max_items = max_items
        self.access_count = {}

    def store(self, key: str, value: Any, context: Dict[str, Any] = None) -> bool:
        """Store information in short-term memory"""
        if len(self.memory_store) >= self.max_items:
            # Remove least accessed item if memory is full
            self._prune_memory()

        self.memory_store[key] = {
            'value': value,
            'timestamp': datetime.now(),
            'context': context or {}
        }

        # Update access count
        self.access_count[key] = self.access_count.get(key, 0) + 1
        return True

    def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve information from short-term memory"""
        if key in self.memory_store:
            # Update access count
            self.access_count[key] = self.access_count.get(key, 0) + 1
            return self.memory_store[key]['value']
        return None

    def delete(self, key: str) -> bool:
        """Delete information from short-term memory"""
        if key in self.memory_store:
            del self.memory_store[key]
            if key in self.access_count:
                del self.access_count[key]
            return True
        return False

    def _prune_memory(self):
        """Remove least accessed items when memory is full"""
        if self.memory_store:
            # Find the least accessed item
            least_accessed = min(self.access_count.items(), key=lambda x: x[1])
            del self.memory_store[least_accessed[0]]
            del self.access_count[least_accessed[0]]

    def clear_memory(self):
        """Clear all short-term memory"""
        self.memory_store.clear()
        self.access_count.clear()