"""Desktop Runtime Cache - singleton in-memory cache for desktop scan results."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from core_runtime.hardware_scanner import HardwareProfile


class DesktopRuntimeCache:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._software = {}
            cls._instance._runtimes = []
            cls._instance._plugin_available = {}
        return cls._instance

    def clear(self):
        self._software.clear()
        self._runtimes.clear()
        self._plugin_available.clear()

    def set_software(self, name: str, data: dict):
        self._software[name] = data

    def get_software(self, name: str) -> dict | None:
        return self._software.get(name)

    def get_all_software(self) -> dict:
        return dict(self._software)

    def set_runtime(self, process_names: list):
        self._runtimes = list(process_names)

    def get_runtimes(self) -> list:
        return list(self._runtimes)

    def set_plugin_availability(self, plugin: str, available: bool):
        self._plugin_available[plugin] = available

    def is_plugin_available(self, plugin: str) -> bool:
        return self._plugin_available.get(plugin, True)

    def set_hardware_profile(self, profile: "HardwareProfile"):
        self._hardware_profile = profile

    def get_hardware_profile(self) -> Optional["HardwareProfile"]:
        return getattr(self, '_hardware_profile', None)