"""Uninstaller business logic — removes Moka AI files, shortcuts, registry entry."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


class UninstallerCore:
    """Pure business logic for uninstallation. No UI (that's in uninstall_moka.py)."""

    def __init__(self, install_path: str = None):
        if install_path is None:
            install_path = self._default_install_path()
        self.install_path = Path(install_path)
        self._shortcuts_dir = self._shortcuts_dir()

    def _default_install_path(self) -> str:
        if sys.platform == "win32":
            return str(Path(os.environ["LOCALAPPDATA"]) / "MokaAI")
        elif sys.platform == "darwin":
            return str(Path.home() / "Library" / "Application Support" / "MokaAI")
        else:
            return str(Path.home() / ".local" / "share" / "moka-ai")

    def _shortcuts_dir(self) -> Path:
        if sys.platform == "win32":
            return Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
        elif sys.platform == "darwin":
            return Path.home() / "Library" / "Applications"
        else:
            return Path.home() / ".local" / "share" / "applications"

    def kill_processes(self) -> None:
        """Kill any running MokaAI processes."""
        try:
            if sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/F", "/IM", "python.exe", "/FI", "WINDOWTITLE eq Moka*"],
                    capture_output=True,
                )
            else:
                subprocess.run(["pkill", "-f", "moka"], capture_output=True)
        except Exception:
            pass

    def remove_install_dir(self) -> bool:
        """Remove the entire moka install directory."""
        if not self.install_path.exists():
            return True
        try:
            shutil.rmtree(self.install_path, ignore_errors=False)
            return True
        except PermissionError:
            return False

    def remove_shortcuts(self) -> list:
        """Remove desktop and Start Menu shortcuts. Returns removed paths."""
        removed = []
        for name in ["Moka AI.lnk"]:
            path = self._shortcuts_dir() / name
            if path.exists():
                try:
                    path.unlink()
                    removed.append(str(path))
                except Exception:
                    pass
        # Desktop shortcut on Windows
        desktop = Path.home() / "Desktop" / "Moka AI.lnk"
        if desktop.exists():
            try:
                desktop.unlink()
                removed.append(str(desktop))
            except Exception:
                pass
        # Linux desktop file
        linux_desktop = Path.home() / ".local" / "share" / "applications" / "moka-ai.desktop"
        if linux_desktop.exists():
            try:
                linux_desktop.unlink()
                removed.append(str(linux_desktop))
            except Exception:
                pass
        return removed

    def remove_registry(self) -> bool:
        """Remove Add/Remove Programs registry entry (Windows only)."""
        if sys.platform != "win32":
            return True
        try:
            import winreg
            winreg.DeleteKeyEx(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Uninstall\MokaAI",
            )
            return True
        except FileNotFoundError:
            return True
        except Exception:
            return False

    def run(self) -> dict:
        """Run full uninstall. Returns result dict."""
        self.kill_processes()
        time.sleep(1)
        shortcuts = self.remove_shortcuts()
        dir_removed = self.remove_install_dir()
        reg_removed = self.remove_registry()
        return {
            "shortcuts_removed": shortcuts,
            "install_dir_removed": dir_removed,
            "registry_removed": reg_removed,
        }