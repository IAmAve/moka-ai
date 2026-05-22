"""
Long-term memory service for MOKA AI
"""

from typing import Any, Dict, Optional
import json
import os
from datetime import datetime

class LongTermMemory:
    def __init__(self, storage_file: str = "memory_long_term.json"):
        self.storage_file = storage_file
        self.memory_store = {}
        self._load_memory()

    def store(self, key: str, value: Any, metadata: Dict[str, Any] = None) -> bool:
        """Store information in long-term memory"""
        # Load existing data first
        self._load_memory()

        # Store the data with metadata
        self.memory_store[key] = {
            'value': value,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        }

        # Save to persistent storage
        self._save_memory()
        return True

    def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve information from long-term memory"""
        self._load_memory()
        if key in self.memory_store:
            return self.memory_store[key].get('value')
        return None

    def _save_memory(self):
        """Save memory to persistent storage"""
        try:
            with open(self.storage_file, 'w') as f:
                json.dump(self.memory_store, f)
        except Exception:
            pass

    def _load_memory(self):
        """Load memory from persistent storage"""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'r') as f:
                    self.memory_store = json.load(f)
        except Exception:
            self.memory_store = {}
            pass

    def clear_all(self):
        """Clear all long-term memory"""
        self.memory_store.clear()
        self._save_memory()
        return True