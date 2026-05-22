"""
Memory Injection Module for MOKA AI Core Runtime

This module handles memory management and injection for the AI.
"""

from typing import Dict, Any, List, Optional
import json
from datetime import datetime

class MemoryManager:
    """Manages memory for the AI system"""

    def __init__(self):
        self.memory_store = {}
        self.memory_history = []
        self.short_term_memory = {}
        self.long_term_memory = {}

    def inject_memory(self, memory_data: Dict[str, Any]):
        """Inject memory data into the system"""
        self.memory_store.update(memory_data)

    def get_memory(self, key: str = None) -> Any:
        """Get memory data"""
        if key:
            return self.memory_store.get(key)
        return self.memory_store

    def store_memory(self, key: str, value: Any):
        """Store memory data"""
        self.memory_store[key] = value
        self.memory_history.append({
            'timestamp': datetime.now().isoformat(),
            'key': key,
            'value': value
        })

    def clear_memory(self):
        """Clear all memory"""
        self.memory_store.clear()

    def get_memory_keys(self) -> List[str]:
        """Get all memory keys"""
        return list(self.memory_store.keys())

    def update_memory(self, key: str, value: Any):
        """Update memory with new key-value pair"""
        self.store_memory(key, value)

    def get_memory_value(self, key: str, default=None):
        """Get specific memory value"""
        return self.memory_store.get(key, default)