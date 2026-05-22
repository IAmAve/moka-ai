"""
Behavior Database for MOKA AI - Hermes Adaptive Learning System
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import json
import os


@dataclass
class BehaviorPattern:
    """Data class for behavior patterns"""
    pattern_id: str
    behavior_type: str
    frequency: int
    last_observed: datetime
    context_data: Dict[str, Any]
    confidence_score: float
    is_approved: bool = False
    is_active: bool = True


class BehaviorDatabase:
    """Database for tracking and managing behavior patterns"""

    def __init__(self, db_path: str = "behavior_memory.json"):
        self.db_path = db_path
        self.behaviors: Dict[str, BehaviorPattern] = {}
        self.load_database()

    def load_database(self):
        """Load behavior database from file"""
        try:
            if os.path.exists(self.db_path):
                with open(self.db_path, 'r') as f:
                    data = json.load(f)
                    # Convert data to BehaviorPattern objects
                    for pattern_id, behavior_data in data.items():
                        self.behaviors[pattern_id] = BehaviorPattern(
                            pattern_id=pattern_id,
                            behavior_type=behavior_data.get('behavior_type', ''),
                            frequency=behavior_data.get('frequency', 0),
                            last_observed=datetime.fromisoformat(behavior_data.get('last_observed', datetime.now().isoformat())),
                            context_data=behavior_data.get('context_data', {}),
                            confidence_score=behavior_data.get('confidence_score', 0.0),
                            is_approved=behavior_data.get('is_approved', False),
                            is_active=behavior_data.get('is_active', True)
                        )
        except Exception as e:
            print(f"Error loading behavior database: {e}")
            self.behaviors = {}

    def save_database(self):
        """Save behavior database to file"""
        try:
            with open(self.db_path, 'w') as f:
                json.dump(self.behaviors, f, default=str)
        except Exception as e:
            print(f"Error saving behavior database: {e}")

    def add_behavior_pattern(self, pattern: BehaviorPattern) -> bool:
        """Add a new behavior pattern to the database"""
        try:
            self.behaviors[pattern.pattern_id] = pattern
            self.save_database()
            return True
        except Exception as e:
            print(f"Error adding behavior pattern: {e}")
            return False

    def get_behavior_pattern(self, pattern_id: str) -> Optional[BehaviorPattern]:
        """Get a behavior pattern by ID"""
        return self.behaviors.get(pattern_id)

    def get_all_behavior_patterns(self) -> Dict[str, BehaviorPattern]:
        """Get all behavior patterns"""
        return self.behaviors

    def update_behavior_pattern(self, pattern_id: str, pattern: BehaviorPattern) -> bool:
        """Update an existing behavior pattern"""
        if pattern_id in self.behaviors:
            self.behaviors[pattern_id] = pattern
            self.save_database()
            return True
        return False

    def remove_behavior_pattern(self, pattern_id: str) -> bool:
        """Remove a behavior pattern"""
        if pattern_id in self.behaviors:
            del self.behaviors[pattern_id]
            self.save_database()
            return True
        return False

    def get_patterns_by_type(self, behavior_type: str) -> List[BehaviorPattern]:
        """Get all behavior patterns of a specific type"""
        return [pattern for pattern in self.behaviors.values()
                if pattern.behavior_type == behavior_type]

    def get_approved_patterns(self) -> List[BehaviorPattern]:
        """Get all approved behavior patterns"""
        return [pattern for pattern in self.behaviors.values()
                if pattern.is_approved]