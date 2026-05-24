"""
Personality Module for MOKA AI

Provides personality engine, communication styles, and mood management
for MOKA's female mentor companion profile.
"""

from personality.personality_engine import (
    PersonalityEngine,
    PersonalityProfile,
    PersonalityTraits,
    MoodState,
    CommunicationStyle,
)
from personality.conversation_memory import ConversationMemory
from personality.context_adaptation import ContextAdaptation
from personality.communication_styles import CommunicationStyles
from personality.mood_engine import MoodEngine
from personality.productivity_coaching import ProductivityCoaching
from personality.teaching_modes import TeachingModes

__all__ = [
    "PersonalityEngine",
    "PersonalityProfile",
    "PersonalityTraits",
    "MoodState",
    "CommunicationStyle",
    "ConversationMemory",
    "ContextAdaptation",
    "CommunicationStyles",
    "MoodEngine",
    "ProductivityCoaching",
    "TeachingModes",
]