"""
Productivity Coaching Module for MOKA AI Personality System
"""

from localization import LocalizationService


class ProductivityCoaching:
    """Productivity coaching system for MOKA AI"""

    def __init__(self, logger=None):
        self._logger = logger
        self._log = logger.info if logger else lambda m: None
        self.localization = LocalizationService()
        self.coaching_modes = {
            "focus": self.focus_coaching,
            "break": self.break_coaching,
            "motivation": self.motivation_coaching,
        }

    def focus_coaching(self, user_state: str) -> str:
        """Focus coaching mode"""
        phrase = self.localization.get_phrase("task_begin")
        return f"{phrase}. Focus mode."

    def break_coaching(self, user_state: str) -> str:
        """Break coaching mode"""
        phrase = self.localization.get_phrase("task_complete")
        return f"{phrase}. Break mode."

    def motivation_coaching(self, user_state: str) -> str:
        """Motivation coaching mode"""
        phrase = self.localization.get_phrase("affirmation")
        return f"{phrase}. Motivation mode."

    def get_coaching_response(self, coaching_type: str, user_state: str) -> str:
        """Get response based on coaching type"""
        coaching_fn = self.coaching_modes.get(coaching_type)
        if coaching_fn:
            self._log(f"Applying {coaching_type} coaching")
            return coaching_fn(user_state)
        return f"Coaching {user_state} in {coaching_type} mode"