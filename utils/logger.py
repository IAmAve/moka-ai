"""
Utility for normalizing logger inputs.
Provides a function to ensure a logger object has an `info` method, accepting either a standard logging.Logger, a simple callable, or None.
"""

from types import SimpleNamespace
from typing import Callable, Any


def _callable_logger_wrapper(func: Callable[[Any], Any]):
    """Wrap a simple callable so it mimics a logger with an `info` method.
    The wrapper forwards messages to the original callable.
    """
    class _Wrapper:
        def info(self, message):
            return func(message)

    return _Wrapper()


def normalize_logger(logger):
    """Return an object with an ``info`` method.

    - If ``logger`` is ``None`` a no‑op logger is returned.
    - If it already has an ``info`` attribute (e.g. ``logging.Logger``), it is returned unchanged.
    - If it is a callable (e.g. ``def logger(msg): ...``) it is wrapped so callers can use ``logger.info(msg)``.
    """
    if logger is None:
        # Simple no‑op logger
        return SimpleNamespace(info=lambda *args, **kwargs: None)
    if hasattr(logger, "info") and callable(getattr(logger, "info")):
        return logger
    if callable(logger):
        return _callable_logger_wrapper(logger)
    # Fallback: return as‑is; may raise later if used incorrectly
    return logger
