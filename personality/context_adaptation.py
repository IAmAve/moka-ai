"""
Context Adaptation Module for MOKA AI Personality System
"""

from typing import Any, Dict
from datetime import datetime


class ContextAdaptation:
    """Context adaptation system for MOKA AI"""

    def __init__(self, logger=None):
        self._logger = logger
        self._log = logger.info if logger else lambda m: None
        self.context_profiles: Dict[str, Any] = {}
        self.user_context: Dict[str, Any] = {}
        self.current_session: Dict[str, Any] = {}
        self.context_history: list = []

    def adapt_to_context(self, context_data: Dict[str, Any]) -> bool:
        """Adapt responses based on context"""
        try:
            self.context_profiles.update(context_data)
            self._log(f"Adapted to context: {list(context_data.keys())}")
            return True
        except Exception as e:
            if self._logger:
                self._logger.error(f"Context adaptation failed: {e}")
            return False

    def update_context(self, context_key: str, context_value: Any) -> None:
        """Update the current context"""
        self.user_context[context_key] = context_value
        self.context_history.append(
            {
                "timestamp": datetime.now(),
                "context": context_key,
                "value": context_value,
            }
        )

    def get_context_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user context profile"""
        return self.context_profiles.get(user_id, {})

    def update_context_profile(self, user_id: str, profile_data: Dict[str, Any]) -> None:
        """Update user context profile"""
        self.context_profiles[user_id] = profile_data
        self._log(f"Updated context profile for user '{user_id}'")