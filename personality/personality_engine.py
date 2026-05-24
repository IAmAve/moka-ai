"""
MOKA AI Personality Engine

Implements MOKA's strict female mentor companion profile with
Tagalog-first communication.
"""

from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

from personality.conversation_memory import ConversationMemory
from localization import LocalizationService


class PersonalityTraits(Enum):
    DISCIPLINED = "disciplined"
    TEACHER = "teacher"
    STRUCTURED = "structured"
    DIRECT = "direct"
    SUPPORTIVE = "supportive"
    PROFESSIONAL = "professional"


class CommunicationStyle(Enum):
    FORMAL = "formal"
    INFORMAL = "informal"
    ENCOURAGING = "encouraging"
    INSTRUCTIVE = "instructive"
    EMPATHETIC = "empathetic"


@dataclass
class PersonalityProfile:
    """Personality profile for MOKA AI."""
    name: str = "MOKA"
    role: str = "Mentor"
    traits: list = field(default_factory=list)
    communication_style: CommunicationStyle = CommunicationStyle.FORMAL
    language_preference: str = "Tagalog"
    teaching_approach: str = "structured"

    def __post_init__(self):
        if self.traits is None:
            self.traits = [
                PersonalityTraits.DISCIPLINED,
                PersonalityTraits.TEACHER,
                PersonalityTraits.STRUCTURED,
                PersonalityTraits.DIRECT,
                PersonalityTraits.SUPPORTIVE,
                PersonalityTraits.PROFESSIONAL,
            ]


class MoodState(Enum):
    """Mood states for MOKA AI."""
    NEUTRAL = "neutral"
    ENCOURAGING = "encouraging"
    STRICT = "strict"
    SUPPORTIVE = "supportive"
    FOCUSED = "focused"
    SATISFIED = "satisfied"
    CONCERNED = "concerned"


class PersonalityEngine:
    """Main personality engine for MOKA AI with Tagalog-first communication."""

    def __init__(self, localizer: LocalizationService = None):
        self.profile = PersonalityProfile()
        self.mood_state = MoodState.NEUTRAL
        self.context_awareness = True
        self.conversation_memory = ConversationMemory()
        self.current_context: Dict[str, Any] = {}
        self.localization = localizer or LocalizationService()
        self.response_log: list = []

    def set_mood(self, mood: MoodState) -> None:
        """Set the current mood state."""
        self.mood_state = mood
        self.localization.set_mood(mood.value)

    def get_mood(self) -> MoodState:
        """Get the current mood state."""
        return self.mood_state

    def get_personality_response(self, input_text: str, context: Dict[str, Any] = None) -> str:
        """Generate a response based on personality traits, mood, and Tagalog localization."""
        self.conversation_memory.add_conversation_turn("user", input_text)

        if context:
            self.current_context.update(context)

        response = self._generate_response(input_text, context)

        self.conversation_memory.add_conversation_turn("assistant", response)
        self.response_log.append({
            "timestamp": datetime.now(),
            "mood": self.mood_state.value,
            "input": input_text,
            "response": response,
        })

        return response

    def _generate_response(self, input_text: str, context: Dict[str, Any] = None) -> str:
        """Generate a response by combining personality, mood, and Tagalog localization."""
        intent = self._classify_intent(input_text)

        base_phrase = self.localization.get_phrase(intent)

        modulated = self._apply_personality_modulation(base_phrase, context)

        return modulated

    def _classify_intent(self, input_text: str) -> str:
        """Classify the user's intent to select the appropriate phrase."""
        text_lower = input_text.lower()

        greetings = ["kamusta", "hello", "hi", "good morning", "good afternoon"]
        if any(g in text_lower for g in greetings):
            return "greeting"
        elif "?" in input_text or "paano" in text_lower or "ano" in text_lower:
            return "explaining"
        elif self.mood_state == MoodState.ENCOURAGING:
            return "affirmation"
        else:
            return "task_begin"

    def _apply_personality_modulation(self, phrase: str, context: Dict[str, Any] = None) -> str:
        """Apply personality trait and mood-based modulation to a phrase."""
        trait_prefix = ""
        trait_suffix = ""

        if PersonalityTraits.DIRECT in self.profile.traits:
            trait_prefix = ""

        if PersonalityTraits.SUPPORTIVE in self.profile.traits:
            trait_suffix = " Andidto lang ako."

        elif self.mood_state == MoodState.ENCOURAGING:
            trait_prefix = "Galing mo! "

        elif self.mood_state == MoodState.STRICT:
            trait_suffix = " gawain mo na."

        final_response = f"{trait_prefix}{phrase}{trait_suffix}"

        return final_response

    def adapt_to_context(self, context: Dict[str, Any]) -> None:
        """Adapt personality based on context."""
        self.current_context.update(context)
        if "mood" in context:
            try:
                self.set_mood(MoodState(context["mood"]))
            except ValueError:
                pass

    def get_teaching_mode(self, subject: str = None) -> str:
        """Get appropriate teaching mode based on subject and personality."""
        return self.profile.teaching_approach

    def get_communication_style(self, mood_state: str = None) -> CommunicationStyle:
        """Get communication style based on mood state."""
        if mood_state:
            try:
                mood = MoodState(mood_state)
                if mood == MoodState.ENCOURAGING:
                    return CommunicationStyle.ENCOURAGING
                elif mood == MoodState.STRICT:
                    return CommunicationStyle.FORMAL
            except ValueError:
                pass
        return self.profile.communication_style

    def get_response_history(self) -> list:
        """Get the history of generated responses."""
        return self.response_log.copy()