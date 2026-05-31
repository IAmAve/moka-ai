"""Standalone uninstaller — lightweight, no deps beyond stdlib + pywin32."""

import os
import sys
import platform
import time
from pathlib import Path


def _find_install_path() -> str:
    if platform.system() == "Windows":
        try:
            import winreg
            key = winreg.OpenKeyEx(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Uninstall\MokaAI",
                0, winreg.KEY_READ,
            )
            install_path, _ = winreg.QueryValueEx(key, "InstallLocation")
            winreg.CloseKey(key)
            return install_path
        except Exception:
            pass
    if platform.system() == "Windows":
        return str(Path(os.environ.get("LOCALAPPDATA", "")) / "MokaAI")
    elif platform.system() == "Darwin":
        return str(Path.home() / "Library" / "Application Support" / "MokaAI")
    else:
        return str(Path.home() / ".local" / "share" / "moka-ai")


def _confirm_uninstall() -> bool:
    if platform.system() == "Windows":
        import ctypes
        result = ctypes.windll.user32.MessageBoxW(
            0,
            "Are you sure you want to uninstall Moka AI?\n\n"
            "This will remove all files and shortcuts.",
            "Moka AI Uninstaller",
            0x04 | 0x20,  # MB_YESNO | MB_ICONQUESTION
        )
        return result == 6  # IDYES
    else:
        return input("Uninstall Moka AI? [y/N]: ").strip().lower() == "y"


def _do_uninstall(install_path: str) -> None:
    import shutil, subprocess
    install_path = Path(install_path)

    if platform.system() == "Windows":
        subprocess.run(
            ["taskkill", "/F", "/IM", "python.exe", "/FI", "WINDOWTITLE eq Moka*"],
            capture_output=True,
        )
    else:
        subprocess.run(["pkill", "-f", "moka"], capture_output=True)

    time.sleep(1)

    # Remove shortcuts
    if platform.system() == "Windows":
        start_menu = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
        for name in ["Moka AI.lnk"]:
            p = start_menu / name
            if p.exists():
                try:
                    p.unlink()
                except Exception:
                    pass
        desktop = Path.home() / "Desktop" / "Moka AI.lnk"
        if desktop.exists():
            try:
                desktop.unlink()
            except Exception:
                pass
    elif platform.system() == "Darwin":
        app = Path.home() / "Applications" / "Moka AI.app"
        if app.exists():
            shutil.rmtree(app)
    else:
        desktop_file = Path.home() / ".local" / "share" / "applications" / "moka-ai.desktop"
        if desktop_file.exists():
            try:
                desktop_file.unlink()
            except Exception:
                pass

    # Remove install directory
    if install_path.exists():
        try:
            shutil.rmtree(install_path)
        except Exception as e:
            print(f"Warning: could not remove {install_path}: {e}")

    # Remove registry
    if platform.system() == "Windows":
        try:
            import winreg
            winreg.DeleteKeyEx(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Uninstall\MokaAI",
            )
        except Exception:
            pass

    print("Moka AI uninstalled successfully.")


if __name__ == "__main__":
    install_path = _find_install_path()
    if _confirm_uninstall():
        _do_uninstall(install_path)
    else:
        print("Uninstall cancelled.")