import logging
import pytest
from voice_service import VoiceService

def test_voice_service_accepts_callable_logger():
    def logger(msg):
        pass
    vs = VoiceService(logger=logger)
    assert callable(vs.logger)

def test_voice_service_accepts_logging_logger():
    std_logger = logging.getLogger("vs")
    std_logger.setLevel(logging.INFO)
    vs = VoiceService(logger=std_logger)
    assert hasattr(vs.logger, "info")
    # Ensure calling info does not raise
    vs.logger.info("test")
