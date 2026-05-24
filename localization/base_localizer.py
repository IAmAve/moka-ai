"""
Base Localizer Interface for MOKA AI

Abstract interface for localization services.
Enables future NLP-based implementation without changing callers.
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional


class BaseLocalizer(ABC):
    """Abstract base class for localization providers."""

    @abstractmethod
    def get_phrase(self, intent: str, context: Optional[Dict] = None) -> str:
        """Get a localized phrase for the given intent and context."""
        pass

    @abstractmethod
    def get_greeting(self, style: str = "formal") -> str:
        """Get a greeting phrase in the configured language."""
        pass

    @abstractmethod
    def set_language(self, lang: str) -> None:
        """Set the active language."""
        pass

    @abstractmethod
    def get_language(self) -> str:
        """Get the current active language."""
        pass