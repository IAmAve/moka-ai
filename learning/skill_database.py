"""
Skill Database for MOKA AI - Hermes Adaptive Learning System
"""

import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field

@dataclass
class Skill:
    """Data class for learned skills"""
    skill_id: str
    name: str
    description: str
    code: str
    dependencies: List[str] = field(default_factory=list)
    is_approved: bool = False
    confidence_score: float = 0.0
    usage_count: int = 0
    last_used: Optional[datetime] = None

class SkillDatabase:
    """Database for managing learned skills"""

    def __init__(self, db_path: str = "skill_database.json", logger=None):
        self._logger = logger
        self._log = logger.info if logger else lambda m: None
        self.db_path = db_path
        self.skills: Dict[str, Skill] = {}
        self.load_database()

    def load_database(self):
        """Load skill database from file"""
        try:
            if not os.path.exists(self.db_path):
                self.skills = {}
                return
            with open(self.db_path, 'r') as f:
                data = json.load(f)
                for skill_id, skill_data in data.items():
                    self.skills[skill_id] = Skill(
                        skill_id=skill_id,
                        name=skill_data.get('name', ''),
                        description=skill_data.get('description', ''),
                        code=skill_data.get('code', ''),
                        dependencies=skill_data.get('dependencies', []),
                        is_approved=skill_data.get('is_approved', False),
                        confidence_score=skill_data.get('confidence_score', 0.0),
                        usage_count=skill_data.get('usage_count', 0),
                        last_used=datetime.fromisoformat(skill_data['last_used']) if skill_data.get('last_used') else None
                    )
        except Exception as e:
            self._log(f"Error loading skill database: {e}")
            self.skills = {}

    def save_database(self):
        """Save skill database to file"""
        try:
            with open(self.db_path, 'w') as f:
                json.dump(self.skills, f, default=str)
        except Exception as e:
            self._log(f"Error saving skill database: {e}")

    def add_skill(self, skill: Skill) -> bool:
        """Add a new skill to the database"""
        try:
            self.skills[skill.skill_id] = skill
            self.save_database()
            return True
        except Exception as e:
            self._log(f"Error adding skill: {e}")
            return False

    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """Get a skill by ID"""
        return self.skills.get(skill_id)

    def update_skill(self, skill_id: str, skill: Skill) -> bool:
        """Update an existing skill"""
        try:
            self.skills[skill_id] = skill
            self.save_database()
            return True
        except Exception as e:
            self._log(f"Error updating skill: {e}")
            return False

    def remove_skill(self, skill_id: str) -> bool:
        """Remove a skill"""
        try:
            if skill_id in self.skills:
                del self.skills[skill_id]
                self.save_database()
                return True
            return False
        except Exception as e:
            self._log(f"Error removing skill: {e}")
            return False

    def get_all_skills(self) -> Dict[str, Skill]:
        """Get all skills"""
        return self.skills

    def get_approved_skills(self) -> Dict[str, Skill]:
        """Get all approved skills"""
        return {k: v for k, v in self.skills.items() if v.is_approved}