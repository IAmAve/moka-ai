"""Config writer — generate config.yaml and config.json."""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

from jinja2 import Template


class ConfigWriter:
    """Render config files from a Jinja2 template."""

    def __init__(self, template_path: str = None, install_path: str = None):
        if template_path is None:
            template_path = Path(__file__).parent.parent / "templates" / "config.yaml.j2"
        self.template_path = Path(template_path)
        self.install_path = Path(install_path) if install_path else None

    def _load_template(self) -> Template:
        with open(self.template_path) as f:
            return Template(f.read())

    def _get_limits(self, vram_gb: float) -> dict:
        """Get max_resolution, max_steps, max_concurrent for VRAM tier."""
        if vram_gb >= 24:
            return {"max_resolution": 3072, "max_steps": 500, "max_concurrent": 4}
        elif vram_gb >= 16:
            return {"max_resolution": 2048, "max_steps": 200, "max_concurrent": 3}
        elif vram_gb >= 8:
            return {"max_resolution": 1024, "max_steps": 100, "max_concurrent": 2}
        else:
            return {"max_resolution": 512, "max_steps": 50, "max_concurrent": 1}

    def write(
        self,
        install_path: str,
        base_model: str = None,
        image_model: str = None,
        voice_model: str = None,
        gpu_model: str = "Unknown",
        vram_gb: float = 0.0,
        compute_capability: str = None,
        custom_resolution: int = None,
    ) -> str:
        """Write config.yaml and config.json. Returns the written config.json path."""
        install_path = Path(install_path)
        config_dir = install_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        limits = self._get_limits(vram_gb)
        if custom_resolution:
            limits["max_resolution"] = custom_resolution

        config = {
            "log_level": "INFO",
            "max_workers": limits["max_concurrent"],
            "voice_enabled": bool(voice_model),
            "memory_backend": "sqlite",
            "storage_path": str(install_path / "data"),
            "moka_base_dir": str(install_path),
            "models_dir": str(install_path / "models"),
            "plugins_path": str(install_path / "plugins"),
            "temp_path": str(install_path / "temp"),
            "hardware": {
                "gpu": gpu_model,
                "vram_gb": vram_gb,
                "compute_capability": compute_capability or "",
            },
            "limits": limits,
            "models": {
                "base_model": base_model or "",
                "image_model": image_model or "",
                "voice_model": voice_model or "",
            },
        }

        config_json_path = config_dir / "config.json"
        with open(config_json_path, "w") as f:
            json.dump(config, f, indent=2)

        yaml_path = config_dir / "config.yaml"
        template = self._load_template()
        tpl_data = {
            "install_path": str(install_path),
            "gpu_model": gpu_model,
            "vram_gb": vram_gb,
            "compute_capability": compute_capability or "unknown",
            "max_resolution": limits["max_resolution"],
            "max_steps": limits["max_steps"],
            "max_concurrent": limits["max_concurrent"],
            "base_model": base_model or "",
            "image_model": image_model or "",
            "voice_model": voice_model or "",
        }
        with open(yaml_path, "w") as f:
            f.write(template.render(**tpl_data))

        return str(config_json_path)

    def register_uninstaller(self, install_path: str, version: str) -> bool:
        """Register MokaAI in Windows Add/Remove Programs. No-op on other platforms."""
        if sys.platform != "win32":
            return True
        import winreg
        install_path = Path(install_path)
        uninstaller_exe = str(install_path / "uninstall_moka.exe")

        try:
            key = winreg.CreateKeyEx(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Uninstall\MokaAI",
                0, winreg.KEY_ALL_ACCESS,
            )
            winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, "Moka AI")
            winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, f'"{uninstaller_exe}"')
            winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, str(install_path))
            winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, version)
            winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, "Moka AI")
            winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(key)
            return True
        except Exception:
            return False