# safety/permission_levels.py
from enum import Enum
from typing import Dict, List, Optional
import json
import os

class PermissionLevel(Enum):
    SAFE = "safe"
    MEDIUM = "medium"
    DANGEROUS = "dangerous"
    SYSTEM = "system"

class PermissionManager:
    DEFAULT_CONFIG = {
        "levels": {
            "safe": {"actions": ["read", "search", "query", "grep", "find", "list"]},
            "medium": {"actions": ["create", "modify", "write", "edit", "add"]},
            "dangerous": {"actions": ["delete", "execute", "network", "run", "install"]},
            "system": {"actions": ["config", "plugin", "admin", "reload", "restart"]}
        },
        "dangerous_patterns": ["rm -rf", "del /f", "format", "truncate", "DROP TABLE", "git push --force"],
        "protected_paths": ["C:\\Windows", "/etc", "~/.ssh", ".env"],
        "approval_timeout_seconds": 60
    }

    def __init__(self, config_path: str = "config/permission_levels.json"):
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return self.DEFAULT_CONFIG.copy()

    def reload(self):
        """Hot-reload configuration from disk without restarting."""
        self.config = self._load_config()

    def get_level_for_action(self, action: str) -> PermissionLevel:
        action = action.lower()
        for level_name, level_data in self.config.get("levels", {}).items():
            if action in level_data.get("actions", []):
                return PermissionLevel(level_name)
        return PermissionLevel.MEDIUM

    def is_dangerous_pattern(self, text: str) -> bool:
        patterns = self.config.get("dangerous_patterns", [])
        text_lower = text.lower()
        return any(p.lower() in text_lower for p in patterns)

    def is_protected_path(self, path: str) -> bool:
        protected = self.config.get("protected_paths", [])
        for p in protected:
            if p.lower() in path.lower():
                return True
        return False

    def get_approval_timeout(self) -> int:
        return self.config.get("approval_timeout_seconds", 60)