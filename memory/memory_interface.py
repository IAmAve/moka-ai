"""
Memory Abstraction Interface for MOKA AI Memory System
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class MemoryItem:
    """Represents a memory item with metadata"""
    id: str
    data: Any
    timestamp: datetime
    metadata: Dict[str, Any] = None

class MemoryAbstraction(ABC):
    """Abstract base class for memory storage implementations"""

    @abstractmethod
    def store(self, key: str, value: Any, metadata: Dict[str, Any] = None) -> bool:
        """Store a memory item"""
        pass

    @abstractmethod
    def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve a memory item by key"""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete a memory item by key"""
        pass

    @abstractmethod
    def list_keys(self) -> List[str]:
        """List all keys in memory"""
        pass

    @abstractmethod
    def clear(self) -> bool:
        """Clear all memory items"""
        pass