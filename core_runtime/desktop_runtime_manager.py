"""Desktop Runtime Manager - orchestrates all scanners, wires to MokaAI."""

from core_runtime.desktop_runtime_cache import DesktopRuntimeCache
from core_runtime.software_scanner import SoftwareScanner
from core_runtime.hardware_scanner import HardwareScanner
from core_runtime.runtime_scanner import RuntimeScanner
from core_runtime.tool_scanner import ToolScanner
from core_runtime.software_profile_engine import SoftwareProfileEngine
from learning.software_profile_database import SoftwareProfileDatabase


class DesktopRuntimeManager:
    def __init__(self, logger=None, db_path: str = "software_profiles.json"):
        self._logger = logger
        self._log = logger.info if logger else lambda *a, **k: None
        self._cache = DesktopRuntimeCache()
        self._scanner = SoftwareScanner()
        self._runtime_scanner = RuntimeScanner()
        self._tool_scanner = ToolScanner()
        self._engine = SoftwareProfileEngine(
            db=SoftwareProfileDatabase(db_path, logger=logger),
            logger=logger,
        )

    def run(self) -> dict:
        software = self._scanner.scan()
        runtimes = self._runtime_scanner.scan()
        plugins = self._tool_scanner.bulk_map(list(software.keys()))

        self._hardware_scanner = HardwareScanner()
        hw_profile = self._hardware_scanner.scan()
        self._cache.set_hardware_profile(hw_profile)
        self._log(f"Hardware scan: {hw_profile.gpu_model}, {hw_profile.vram_gb}GB VRAM, compute {hw_profile.compute_capability}")

        for name, data in software.items():
            self._cache.set_software(name, data)
        self._cache.set_runtime(runtimes)

        for plugin in ("vscode", "git", "chrome", "explorer", "terminal", "comfyui"):
            self._cache.set_plugin_availability(
                plugin, any(p == plugin for p in plugins))

        profiles = self._engine.generate(software, runtimes, {})
        n = len(profiles)
        self._log(f"Desktop scan: {len(software)} apps, {len(runtimes)} processes, {n} profiles")
        return {
            "software_detected": len(software),
            "runtime_count": len(runtimes),
            "plugins_available": len(set(plugins)),
            "profiles_generated": n,
        }

    def get_software_profiles(self):
        """Return list of software profiles from the profile engine."""
        db = self._engine.db
        return [p for p in db.profiles.values()] if hasattr(db, 'profiles') else []

    def get_cache(self) -> DesktopRuntimeCache:
        return self._cache