"""
Behavior memory service for MOKA AI
"""

from typing import Any, Dict, Optional
import json
import os
from datetime import datetime

class BehaviorMemory:
    """Behavior memory service for MOKA AI"""

    def __init__(self, storage_file: str = "behavior_memory.json"):
        self.storage_file = storage_file
        self.memory_store = {}
        self._load_memory()

    def store_behavior_pattern(self, pattern_id: str, behavior_data: Dict[str, Any]) -> bool:
        """Store behavior pattern data"""
        self.memory_store[pattern_id] = {
            'data': behavior_data,
            'timestamp': datetime.now().isoformat()
        }
        self._save_memory()
        return True

    def retrieve_behavior_pattern(self, pattern_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve behavior pattern data"""
        self._load_memory()
        return self.memory_store.get(pattern_id)

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
        """Clear all behavior memory"""
        self.memory_store.clear()
        self._save_memory()
        return True