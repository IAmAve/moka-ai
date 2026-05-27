"""Create desktop and Start Menu shortcuts."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


class Shortcuts:
    """Create shortcuts on Windows/macOS/Linux."""

    def __init__(self, install_path: str, moka_exe: str = None):
        self.install_path = Path(install_path)
        self.moka_exe = moka_exe or str(Path(sys.executable).parent / "python.exe")
        self.moka_script = str(self.install_path / "moka.py")

    def create_desktop_shortcut(self) -> str:
        """Create desktop shortcut. Returns path or '' if failed."""
        system = sys.platform

        if system == "win32":
            return self._create_windows_shortcut(
                Path.home() / "Desktop" / "Moka AI.lnk",
                self.moka_exe, self.moka_script,
            )
        elif system == "darwin":
            return self._create_macos_app()
        else:
            return self._create_linux_desktop_file(
                Path.home() / ".local" / "share" / "applications" / "moka-ai.desktop",
            )

    def create_start_menu_shortcut(self) -> str:
        """Create Start Menu shortcut. Returns path or '' if failed."""
        system = sys.platform

        if system == "win32":
            start_menu = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
            return self._create_windows_shortcut(
                start_menu / "Moka AI.lnk",
                self.moka_exe, self.moka_script,
            )
        else:
            return self._create_linux_desktop_file(
                Path.home() / ".local" / "share" / "applications" / "moka-ai.desktop",
            )

    def _create_windows_shortcut(self, path: Path, target: str, args: str) -> str:
        """Create a .lnk shortcut using PowerShell."""
        try:
            import pythoncom, win32com.client
            pythoncom.CoInitialize()
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortcut(str(path))
            shortcut.TargetPath = target
            shortcut.Arguments = f'"{args}"'
            shortcut.WorkingDirectory = str(Path(target).parent)
            shortcut.Description = "Moka AI"
            shortcut.Save()
            pythoncom.CoUninitialize()
            return str(path)
        except Exception:
            # Fallback: PowerShell
            script = f'''
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{path}")
$Shortcut.TargetPath = "{target}"
$Shortcut.Arguments = '"{args}"'
$Shortcut.WorkingDirectory = "{Path(target).parent}"
$Shortcut.Description = "Moka AI"
$Shortcut.Save()
'''
            try:
                subprocess.run(
                    ["powershell", "-Command", script],
                    capture_output=True, timeout=10,
                )
                return str(path)
            except Exception:
                return ""

    def _create_macos_app(self) -> str:
        """Create macOS app bundle."""
        app_path = Path.home() / "Applications" / "Moka AI.app"
        app_path.mkdir(parents=True, exist_ok=True)
        plist = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleExecutable</key><string>python</string>
<key>CFBundleIdentifier</key><string>com.mokaaai</string>
<key>CFBundleName</key><string>Moka AI</string>
</dict></plist>'''
        (app_path / "Contents" / "Info.plist").write_text(plist)
        return str(app_path)

    def _create_linux_desktop_file(self, path: Path) -> str:
        """Create a .desktop file on Linux."""
        content = f'''[Desktop Entry]
Name=Moka AI
Exec={self.moka_exe} {self.moka_script}
Type=Application
Terminal=false
Categories=Utility;AI;
'''
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        os.chmod(path, 0o755)
        return str(path)