"""
Mood Engine for MOKA AI Personality System
"""

from typing import Any, Dict
from datetime import datetime


class MoodEngine:
    """Mood engine for managing MOKA AI's emotional states"""

    def __init__(self, logger=None):
        self._logger = logger
        self._log = logger.info if logger else lambda m: None
        self.current_mood = "neutral"
        self.mood_history: list = []
        self.mood_transitions: list = []
        self.mood_intensity = 1.0

    def update_mood(self, mood_state: str, intensity: float = 1.0) -> None:
        """Update the current mood state"""
        self.current_mood = mood_state
        self.mood_intensity = intensity
        self.mood_history.append(
            {
                "timestamp": datetime.now(),
                "mood": mood_state,
                "intensity": intensity,
            }
        )
        self._log(f"Updated mood to '{mood_state}' with intensity {intensity}")

    def get_mood_response(self, input_text: str, localization_service=None) -> str:
        """Generate a mood-appropriate response"""
        if localization_service:
            return localization_service.get_phrase("task_begin")
        return f"Response in {self.current_mood} mood"

    def adapt_mood_to_context(self, context: Dict[str, Any]) -> None:
        """Adapt mood based on conversation context"""
        if "mood" in context:
            self.update_mood(context["mood"], context.get("intensity", 1.0))

    def calculate_mood_from_sentiment(self, text: str) -> str:
        """Calculate mood state from text sentiment using TextBlob polarity."""
        try:
            from textblob import TextBlob
            polarity = TextBlob(text).sentiment.polarity
            if polarity > 0.3:
                return "encouraging"
            elif polarity < -0.3:
                return "strict"
            else:
                return "neutral"
        except Exception:
            return "neutral"