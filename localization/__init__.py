"""
Localization Module for MOKA AI

Provides Tagalog-first communication with an abstract interface
for future NLP upgrade path.
"""

from localization.base_localizer import BaseLocalizer
from localization.tagalog.localization_service import LocalizationService

__all__ = ["BaseLocalizer", "LocalizationService"]