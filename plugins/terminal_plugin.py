"""
Terminal Plugin for MOKA AI

Opens the system terminal (cmd.exe, Windows Terminal, Terminal.app, or Linux terminal).
Requires process_management permission.
"""

import subprocess
import os
import shutil
import platform
from typing import Any, Dict

from plugins.base_plugin import MokaPlugin, PluginMetadata, PluginPermissions


def _find_terminal() -> str:
    """Find available terminal on Windows/macOS/Linux."""
    system = platform.system()

    if system == "Windows":
        # Prefer Windows Terminal, fall back to cmd
        import glob
        wt = os.path.expandvars(r"%ProgramFiles%\WindowsApps\Microsoft.WindowsTerminal_*\wt.exe")
        try:
            matches = glob.glob(wt)
        except Exception:
            matches = []
        if matches:
            return matches[0]
        if shutil.which("wt"):
            return "wt"
        return "cmd"

    elif system == "Darwin":
        # macOS: prefer iTerm2, fall back to Terminal.app
        if shutil.which("iTerm"):
            return "iTerm"
        return "Terminal"  # open -a "Terminal"

    else:  # Linux
        # Check common terminal emulators
        for term in ["gnome-terminal", "konsole", "xfce4-terminal",
                     "tilix", "alacritty", "kitty", "xterm"]:
            if shutil.which(term):
                return term
        return "xterm"  # fallback

    return "xterm"  # generic fallback


class TerminalPlugin(MokaPlugin):
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="terminal",
            version="1.0.0",
            description="System terminal launcher — opens terminal at optional path",
            author="MOKA",
        )

    @property
    def permissions(self) -> PluginPermissions:
        return PluginPermissions(process_management=True)

    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        action = data.get("action", "open")
        if action == "open":
            return self._open_terminal(data)
        elif action == "run":
            return self._run_and_exit(data)
        return {"ok": False, "error": f"unknown action: {action}"}

    def _open_terminal(self, data: Dict[str, Any]) -> Dict[str, Any]:
        path = data.get("path", None)
        terminal = _find_terminal()
        system = platform.system()
        try:
            if system == "Windows":
                if terminal == "cmd":
                    cmd = ["cmd"]
                    if path:
                        cmd.extend(["/K", f"cd /d {path}"])
                else:  # wt or other
                    cmd = [terminal]
                    if path:
                        cmd.extend(["--startingDirectory", path])
            elif system == "Darwin":
                if terminal == "iTerm":
                    cmd = ["iTerm"]
                    if path:
                        cmd.extend(["--cwd", path])
                else:
                    cmd = ["open", "-a", "Terminal"]
                    if path:
                        cmd = ["open", "-a", "Terminal", path]
            else:  # Linux
                cmd = [terminal]
                if path:
                    cmd.extend(["--directory", path])

            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self._log(f"Opened terminal: {terminal}")
            return {"ok": True, "terminal": terminal, "path": path}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _run_and_exit(self, data: Dict[str, Any]) -> Dict[str, Any]:
        cmd = data.get("command", "")
        path = data.get("path", ".")
        if not cmd:
            return {"ok": False, "error": "no command provided"}
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=path,
                capture_output=True,
                text=True,
                timeout=data.get("timeout", 60),
            )
            return {
                "ok": result.returncode == 0,
                "command": cmd,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "command timed out"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def verify(self) -> bool:
        return _find_terminal() != ""

    def rollback(self) -> bool:
        self._log("Terminal plugin rollback — no-op")
        return True

    def health(self) -> Dict[str, Any]:
        terminal = _find_terminal()
        return {"ok": True, "message": f"Terminal ready: {terminal}"}