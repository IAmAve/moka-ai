"""
Base plugin classes for MOKA AI plugin system.

Provides the MokaPlugin abstract base class and supporting dataclasses
that all MOKA plugins must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional


@dataclass
class PluginMetadata:
    """Metadata for a MokaPlugin."""
    name: str
    version: str
    description: str
    author: str


@dataclass
class PluginPermissions:
    """Permissions granted to a MokaPlugin."""
    filesystem: bool = False


class MokaPlugin(ABC):
    """Abstract base class for all MOKA AI plugins.

    All plugins must implement the metadata, permissions, execute, verify,
    rollback, and health interface. The on_crash and reset_health methods
    provide crash-recovery helpers used by PluginManager.
    """

    def __init__(self, logger: Callable = None):
        self._logger = logger
        self._log = logger.info if logger and hasattr(logger, 'info') else (logger or (lambda m: None))
        self._rollback_handler: Optional[Callable[[], None]] = None
        self._health_state: Dict[str, Any] = {"ok": True, "message": "initializing"}

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Return the plugin's metadata."""
        raise NotImplementedError

    @property
    @abstractmethod
    def permissions(self) -> PluginPermissions:
        """Return the plugin's permissions."""
        raise NotImplementedError

    @abstractmethod
    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the plugin's main logic. Must return a dict."""
        raise NotImplementedError

    @abstractmethod
    def verify(self) -> bool:
        """Verify the plugin is correctly configured and ready to run."""
        raise NotImplementedError

    @abstractmethod
    def rollback(self) -> bool:
        """Attempt to rollback any side-effects from execute()."""
        raise NotImplementedError

    def health(self) -> Dict[str, Any]:
        """Return the current health status of the plugin."""
        return self._health_state

    def on_crash(self, error: Exception) -> None:
        """Called when the plugin crashes during isolated execution."""
        self._health_state = {"ok": False, "message": str(error)}
        self._log(f"Plugin '{self.metadata.name}' crashed: {error}")

    def reset_health(self) -> None:
        """Reset the plugin's health state to healthy."""
        self._health_state = {"ok": True, "message": "healthy"}