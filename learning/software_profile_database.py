"""
Software Profile Database for MOKA AI - Hermes Adaptive Learning System
"""

import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field

@dataclass
class SoftwareProfile:
    """Data class for software profiles"""
    profile_id: str
    name: str
    description: str
    usage_patterns: List[str] = field(default_factory=list)
    confidence_score: float = 0.0
    last_accessed: Optional[datetime] = None
    is_active: bool = True

class SoftwareProfileDatabase:
    """Database for tracking software profiles and usage patterns"""

    def __init__(self, db_path: str = "software_profiles.json"):
        self.db_path = db_path
        self.profiles: Dict[str, SoftwareProfile] = {}
        self.load_database()

    def load_database(self):
        """Load software profile database from file"""
        try:
            if os.path.exists(self.db_path):
                with open(self.db_path, 'r') as f:
                    data = json.load(f)
                    self.profiles = data
        except Exception as e:
            print(f"Error loading software profile database: {e}")
            self.profiles = {}

    def save_database(self):
        """Save software profile database to file"""
        try:
            with open(self.db_path, 'w') as f:
                json.dump(self.profiles, f, default=str)
        except Exception as e:
            print(f"Error saving software profile database: {e}")

    def add_profile(self, profile: SoftwareProfile) -> bool:
        """Add a new software profile to the database"""
        try:
            self.profiles[profile.profile_id] = profile
            self.save_database()
            return True
        except Exception as e:
            print(f"Error adding profile: {e}")
            return False

    def get_profile(self, profile_id: str) -> Optional[SoftwareProfile]:
        """Get a software profile by ID"""
        return self.profiles.get(profile_id)

    def update_profile(self, profile_id: str, profile: SoftwareProfile) -> bool:
        """Update an existing software profile"""
        try:
            if profile_id in self.profiles:
                self.profiles[profile_id] = profile
                self.save_database()
                return True
            return False
        except Exception as e:
            print(f"Error updating profile: {e}")
            return False

    def remove_profile(self, profile_id: str) -> bool:
        """Remove a software profile"""
        try:
            if profile_id in self.profiles:
                del self.profiles[profile_id]
                self.save_database()
                return True
            return False
        except Exception as e:
            print(f"Error removing profile: {e}")
            return False