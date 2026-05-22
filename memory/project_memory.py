"""
Project memory service for MOKA AI
"""

from typing import Any, Dict, Optional
import json
import os
from datetime import datetime

class ProjectMemory:
    """Project memory service for MOKA AI"""

    def __init__(self, storage_file: str = "memory_project.json"):
        self.storage_file = storage_file
        self.memory_store = {}
        self._load_memory()

    def store_project_context(self, project_id: str, context_data: Dict[str, Any]) -> bool:
        """Store project-specific context data"""
        self.memory_store[project_id] = {
            'data': context_data,
            'timestamp': datetime.now().isoformat()
        }
        self._save_memory()
        return True

    def retrieve_project_context(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve project-specific context data"""
        self._load_memory()
        return self.memory_store.get(project_id, {}).get('data')

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
        """Clear all project memory"""
        self.memory_store.clear()
        self._save_memory()
        return True