"""
Voice Service for MOKA AI
"""

"""
Voice Service for MOKA AI
"""

import threading
import time
import pyaudio
import wave
from utils.logger import normalize_logger


class VoiceService:
    """Voice service for handling speech input/output."""

    def __init__(self, event_bus=None, logger=None):
        # Normalize logger to an object with an `info` method
        from types import SimpleNamespace
        if logger is None:
            self.logger = SimpleNamespace(info=lambda *args, **kwargs: None)
        elif hasattr(logger, "info"):
            self.logger = logger
        else:
            # Assume callable logger; keep as is
            self.logger = logger
        # Use .info if available, otherwise the callable itself
        self._log = getattr(self.logger, "info", self.logger)
        self._event_bus = event_bus
        self._is_initialized = False
        self._audio = None
        self._stream = None
        self._log("VoiceService initialized")