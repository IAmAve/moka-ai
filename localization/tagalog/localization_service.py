"""
Tagalog Localization Service for MOKA AI

Dictionary-based localization with mood-aware phrase selection.
Upgrade path: Replace this with NLP-based implementation via BaseLocalizer interface.
"""

import json
import random
from pathlib import Path
from typing import Dict, Optional

from localization.base_localizer import BaseLocalizer


class LocalizationService(BaseLocalizer):
    """Tagalog-first localization service."""

    def __init__(self, language: str = "Tagalog"):
        self.language = language
        self.resources = self._load_resources()
        self.current_mood = "neutral"

    def _load_resources(self) -> Dict:
        """Load localization resources from JSON files."""
        resources_path = Path(__file__).parent / "resources.json"
        if resources_path.exists():
            with open(resources_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"intents": {}, "mood_modulation": {}}

    def get_phrase(self, intent: str, context: Optional[Dict] = None) -> str:
        """Get a localized phrase for the given intent."""
        context = context or {}
        intents = self.resources.get("intents", {})

        if intent in intents:
            phrase = intents[intent]

            if isinstance(phrase, list):
                phrase = random.choice(phrase)

            return self._apply_mood(phrase)
        return intent

    def get_greeting(self, style: str = "formal") -> str:
        """Get a greeting phrase."""
        return self.get_phrase(f"greeting_{style}", {"style": style})

    def set_language(self, lang: str) -> None:
        """Set the active language."""
        self.language = lang

    def get_language(self) -> str:
        """Get the current active language."""
        return self.language

    def set_mood(self, mood: str) -> None:
        """Set the mood for mood-aware phrase modulation."""
        self.current_mood = mood

    def get_mood(self) -> str:
        """Get the current mood."""
        return self.current_mood

    def _apply_mood(self, phrase: str) -> str:
        """Apply mood-based modulation to a phrase."""
        mood_mods = self.resources.get("mood_modulation", {})
        mood_settings = mood_mods.get(self.current_mood, {})

        prefix = mood_settings.get("prefix", "")
        suffix = mood_settings.get("suffix", "")

        return f"{prefix}{phrase}{suffix}"

    def is_tagalog(self) -> bool:
        """Check if current language is Tagalog."""
        return self.language.lower() == "tagalog"