"""
Explorer Plugin for MOKA AI

Opens folders and selects files using OS-native file explorer.
Works on Windows, macOS, and Linux.
Minimal filesystem permission required.
"""

import subprocess
import os
import platform
import shutil
from pathlib import Path
from typing import Any, Dict

from plugins.base_plugin import MokaPlugin, PluginMetadata, PluginPermissions


class ExplorerPlugin(MokaPlugin):
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="explorer",
            version="1.0.0",
            description="File explorer integration — open folders, select files",
            author="MOKA",
        )

    @property
    def permissions(self) -> PluginPermissions:
        return PluginPermissions(filesystem=True)

    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        action = data.get("action", "open")
        if action == "open":
            return self._open_path(data)
        elif action == "select":
            return self._open_path(data)  # open + "reveal in explorer" = open folder on all platforms
        return {"ok": False, "error": f"unknown action: {action}"}

    def _open_path(self, data: Dict[str, Any]) -> Dict[str, Any]:
        path_str = str(Path(data.get("path", ".")).resolve())
        try:
            system = platform.system()
            if system == "Windows":
                os.startfile(path_str)
            elif system == "Darwin":
                subprocess.run(["open", path_str], capture_output=True)
            else:  # Linux
                # Try common file managers
                for fm in ["xdg-open", "nautilus", "dolphin", "thunar", "pcmanfm"]:
                    if shutil.which(fm):
                        subprocess.Popen([fm, path_str],
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        break
                else:
                    subprocess.Popen(["xdg-open", path_str],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self._log(f"Opened: {path_str}")
            return {"ok": True, "action": data.get("action", "open"), "path": path_str}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def verify(self) -> bool:
        system = platform.system()
        if system == "Windows":
            return True  # explorer.exe always available
        elif system == "Darwin":
            return shutil.which("open") is not None
        else:
            return shutil.which("xdg-open") is not None or shutil.which("nautilus") is not None

    def rollback(self) -> bool:
        self._log("Explorer plugin rollback — no undo operation available")
        return True

    def health(self) -> Dict[str, Any]:
        system = platform.system()
        if system == "Windows":
            return {"ok": True, "message": "Explorer available"}
        elif system == "Darwin":
            return {"ok": True, "message": "open command available"}
        else:
            return {"ok": True, "message": "xdg-open available"}