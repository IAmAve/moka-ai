"""
Teaching Modes Module for MOKA AI Personality System
"""

from localization import LocalizationService


class TeachingModes:
    """Teaching modes manager for MOKA AI"""

    def __init__(self, logger=None):
        self._logger = logger
        self._log = logger.info if logger else lambda m: None
        self.localization = LocalizationService()
        self.modes = {
            "beginner": self.beginner_mode,
            "intermediate": self.intermediate_mode,
            "advanced": self.advanced_mode,
        }

    def beginner_mode(self, topic: str) -> str:
        """Beginner teaching mode"""
        phrase = self.localization.get_phrase("explaining")
        return f"{phrase}. {topic}"

    def intermediate_mode(self, topic: str) -> str:
        """Intermediate teaching mode"""
        phrase = self.localization.get_phrase("explaining")
        return f"{phrase}. {topic}"

    def advanced_mode(self, topic: str) -> str:
        """Advanced teaching mode"""
        phrase = self.localization.get_phrase("explaining")
        return f"{phrase}. {topic}"

    def get_teaching_response(self, mode: str, topic: str) -> str:
        """Get response based on teaching mode"""
        teaching_fn = self.modes.get(mode)
        if teaching_fn:
            self._log(f"Applying {mode} teaching mode for '{topic}'")
            return teaching_fn(topic)
        return f"Teaching {topic} in {mode} mode"