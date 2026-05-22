from dataclasses import dataclass
from typing import Optional
from .permission_levels import PermissionLevel

@dataclass
class Intent:
    action: str
    target: str
    params: dict
    suggested_level: PermissionLevel
    original_text: str

class IntentDetector:
    ACTION_KEYWORDS = {
        "read": ["read", "show", "view", "cat", "get", "display", "list"],
        "write": ["write", "edit", "modify", "create", "add", "append"],
        "delete": ["delete", "remove", "rm", "del", "unlink", "destroy"],
        "execute": ["execute", "run", "bash", "cmd", "exec", "shell", "python", "node"],
        "network": ["curl", "wget", "fetch", "http", "api", "request", "send"],
        "config": ["config", "set", "env", "setting", "configure"],
        "plugin": ["plugin", "load", "unload", "enable", "disable"],
    }

    def detect(self, text: str) -> Intent:
        text_lower = text.lower()
        action = self._extract_action(text_lower)
        target = self._extract_target(text, action)
        suggested_level = self._get_level_for_action(action)
        return Intent(
            action=action,
            target=target,
            params={},
            suggested_level=suggested_level,
            original_text=text
        )

    def _extract_action(self, text: str) -> str:
        for action, keywords in self.ACTION_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    return action
        return "unknown"

    def _extract_target(self, text: str, action: str) -> str:
        words = text.split()
        if len(words) > 1:
            return words[-1]
        return text

    def _get_level_for_action(self, action: str) -> PermissionLevel:
        action_to_level = {
            "read": PermissionLevel.SAFE,
            "write": PermissionLevel.MEDIUM,
            "delete": PermissionLevel.DANGEROUS,
            "execute": PermissionLevel.DANGEROUS,
            "network": PermissionLevel.DANGEROUS,
            "config": PermissionLevel.SYSTEM,
            "plugin": PermissionLevel.SYSTEM,
        }
        return action_to_level.get(action, PermissionLevel.MEDIUM)