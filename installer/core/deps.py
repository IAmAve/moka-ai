"""Dependency resolver — compute pip packages to install per selected models."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import List

from packaging.version import Version


@dataclass
class Package:
    name: str
    install_action: str  # "install" | "skip" | "upgrade"
    current_version: str = ""
    target_version: str = ""
    status: str = "pending"  # pending | installing | done | failed
    error: str = ""


class DepResolver:
    """Compute which pip packages need to be installed/upgraded."""

    BASE_PACKAGES = [
        "flask>=3.0",
        "flask-socketio>=5.0",
        "eventlet>=0.35",
        "psutil>=5.9",
        "pyyaml>=6.0",
        "platformdirs>=4.0",
        "deepeval>=0.21",
        "sentencepiece>=0.1",
        "huggingface-hub>=0.19",
        "rich>=13.0",
        "click>=8.0",
        "requests>=2.31",
    ]

    VERSIONED_PACKAGES = [
        "torch>=2.0",
        "transformers>=4.30",
        "diffusers>=0.27",
        "accelerate>=0.25",
        "safetensors>=0.4",
    ]

    VOICE_PACKAGES = [
        "numpy>=1.24",
        "torchaudio>=2.0",
        "speechrecognition>=3.10",
        "pyttsx3>=0.8",
    ]

    IMAGE_PACKAGES = [
        "torch>=2.0",
        "transformers>=4.30",
        "diffusers>=0.27",
    ]

    INSTALLER_PACKAGES = [
        "dearpygui>=1.90",
        "pyinstaller>=6.0",
    ]

    def __init__(self):
        self._installed: dict = {}

    def _get_installed(self) -> dict:
        """Return {package_name: version_string} for installed packages."""
        if self._installed:
            return self._installed
        import importlib.metadata
        try:
            for dist in importlib.metadata.distributions():
                self._installed[dist.name.lower()] = dist.version
        except Exception:
            pass
        return self._installed

    def resolve(
        self,
        require_voice: bool = False,
        require_image: bool = False,
    ) -> List[Package]:
        """Return list of packages that need install/upgrade."""
        installed = self._get_installed()
        result: List[Package] = []
        seen = set()

        def _add(pkg_spec: str, category: str = "install"):
            name = pkg_spec.split(">=")[0].split("==")[0].split("<")[0].strip()
            if name.lower() in seen:
                return
            seen.add(name.lower())

            current = installed.get(name.lower(), "")
            action = "skip"
            if not current:
                action = "install"
            elif category == "upgrade":
                action = "upgrade"

            result.append(Package(
                name=name,
                install_action=action,
                current_version=current,
                target_version=pkg_spec,
                status="pending",
            ))

        for p in self.BASE_PACKAGES:
            _add(p, "install")
        for p in self.VERSIONED_PACKAGES:
            _add(p, "upgrade")
        if require_voice:
            for p in self.VOICE_PACKAGES:
                _add(p, "install")
        if require_image:
            for p in self.IMAGE_PACKAGES:
                _add(p, "install")

        return result

    def install_packages(self, packages: List[Package], progress_callback=None) -> List[Package]:
        """Install packages via subprocess pip. Calls callback(pkg, stdout_line) for each line."""
        import subprocess
        to_install = [p for p in packages if p.install_action in ("install", "upgrade")]
        for pkg in to_install:
            pkg.status = "installing"
            if progress_callback:
                progress_callback(pkg, f"Installing {pkg.name}...")
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", pkg.target_version,
                     "--quiet", "--no-warn-script-location"],
                    capture_output=True, text=True, timeout=600,
                )
                if result.returncode == 0:
                    pkg.status = "done"
                    if progress_callback:
                        progress_callback(pkg, f"  OK {pkg.name}")
                else:
                    pkg.status = "failed"
                    pkg.error = result.stderr[:200]
                    if progress_callback:
                        progress_callback(pkg, f"  FAIL {pkg.name}: {pkg.error}")
            except subprocess.TimeoutExpired:
                pkg.status = "failed"
                pkg.error = "timeout"
            except Exception as e:
                pkg.status = "failed"
                pkg.error = str(e)
        return packages