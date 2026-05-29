"""
Communication Styles Module for MOKA AI Personality System
"""

from localization import LocalizationService


class CommunicationStyles:
    """Communication styles manager for MOKA AI"""

    def __init__(self, logger=None):
        self._logger = logger
        self._log = logger.info if logger else lambda m: None
        self.localization = LocalizationService()
        self.styles = {
            "formal": self.formal_style,
            "informal": self.informal_style,
            "teaching": self.teaching_style,
            "encouraging": self.encouraging_style,
            "instructive": self.instructive_style,
        }

    def formal_style(self, content: str) -> str:
        """Formal communication style"""
        greeting = self.localization.get_phrase("greeting")
        return f"{greeting}. {content}"

    def informal_style(self, content: str) -> str:
        """Informal communication style"""
        greeting = self.localization.get_phrase("greeting_informal")
        return f"{greeting} {content}"

    def teaching_style(self, content: str) -> str:
        """Teaching communication style"""
        intro = self.localization.get_phrase("explaining")
        return f"{intro}. {content}"

    def encouraging_style(self, content: str) -> str:
        """Encouraging communication style"""
        affirmation = self.localization.get_phrase("affirmation")
        return f"{affirmation} {content}"

    def instructive_style(self, content: str) -> str:
        """Instructive communication style"""
        return f"{content}"

    def get_style_response(self, style_type: str, content: str) -> str:
        """Get response based on communication style"""
        style_fn = self.styles.get(style_type)
        if style_fn:
            self._log(f"Applying style '{style_type}'")
            return style_fn(content)
        return content