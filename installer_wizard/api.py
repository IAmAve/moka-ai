"""Moka AI Installer Wizard — Python API (PyWebView bridge)."""
from __future__ import annotations

import os
import threading
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional, Callable

class WizardStep(IntEnum):
    WELCOME = 1
    HARDWARE = 2
    MODELS = 3
    INSTALLING = 4
    COMPLETE = 5

@dataclass
class WizardState:
    step: WizardStep = WizardStep.WELCOME
    install_path: str = ""
    hw_profile: dict = field(default_factory=dict)
    base_model: str = ""
    image_model: str = ""
    voice_model: str = ""
    packages: list = field(default_factory=list)
    install_progress: float = 0.0
    install_log: list = field(default_factory=list)
    shortcuts_created: bool = False
    launch_on_finish: bool = True
    error: Optional[str] = None
    _progress_callbacks: list = field(default_factory=list)

class WizardAPI:
    """Python-side API exposed to JS via PyWebView bridge."""
    _instance = None

    def __init__(self):
        self.state = WizardState()

    @staticmethod
    def get_instance() -> "WizardAPI":
        if WizardAPI._instance is None:
            WizardAPI._instance = WizardAPI()
        return WizardAPI._instance

    # ── State ──────────────────────────────────────────────────────────

    def get_state(self) -> dict:
        """Return current wizard state for JS polling."""
        return {
            "step": self.state.step,
            "step_name": self.state.step.name.lower(),
            "install_path": self.state.install_path,
            "hw_profile": self.state.hw_profile,
            "base_model": self.state.base_model,
            "image_model": self.state.image_model,
            "voice_model": self.state.voice_model,
            "progress": self.state.install_progress,
            "log": self.state.install_log,
            "error": self.state.error,
            "shortcuts_created": self.state.shortcuts_created,
        }

    def get_progress(self) -> dict:
        """Return real-time install progress for polling."""
        return {
            "step": self.state.step,
            "step_name": self.state.step.name.lower(),
            "packages": self.state.packages,
            "progress": self.state.install_progress,
            "log": self.state.install_log,
            "error": self.state.error,
        }

    # ── Welcome step ────────────────────────────────────────────────────

    def set_install_path(self, path: str) -> dict:
        """Validate the installation path. Returns {valid, path, error}."""
        path = path.strip()
        if not path:
            return {"valid": False, "path": "", "error": "Path cannot be empty."}
        self.state.install_path = path
        # Try to create it
        try:
            os.makedirs(path, exist_ok=True)
            test_file = os.path.join(path, ".moka_write_test")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            return {"valid": True, "path": path, "error": ""}
        except Exception as e:
            return {"valid": False, "path": path, "error": str(e)}

    def browse_folder(self) -> str:
        """Open native folder picker. Returns selected path or empty string.
        Override in PyWebView to show real dialog."""
        return ""

    # ── Hardware step ──────────────────────────────────────────────────

    def scan_hardware(self) -> dict:
        """Run hardware scan on background thread. Returns updated state."""
        from installer.core.hardware import HardwareScan
        scan = HardwareScan()
        profile = scan.scan()

        # CPU label
        cpu = profile.cpu_model or "Unknown CPU"
        if profile.cpu_cores and profile.cpu_threads:
            cpu += f"  ({profile.cpu_cores}C / {profile.cpu_threads}T)"

        # OS detection
        os_label = profile.platform
        try:
            import subprocess
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-WmiObject Win32_OperatingSystem).Caption"],
                capture_output=True, text=True, timeout=8,
            )
            caption = r.stdout.strip()
            if caption:
                os_label = caption
        except Exception:
            pass

        self.state.hw_profile = {
            "cpu": cpu,
            "gpu": profile.gpu_model or "No dedicated GPU",
            "vram_gb": float(profile.vram_gb) if profile.vram_gb else 0.0,
            "vram_pct": min(100.0, float(profile.vram_gb or 0) / 24.0 * 100.0),
            "ram": f"{profile.system_ram_gb:.1f} GB total · {profile.available_vram_gb:.1f} GB free",
            "os": os_label,
            "compute_capability": profile.compute_capability or "",
        }
        self.state.step = WizardStep.HARDWARE
        return self.get_state()

    # ── Models step ─────────────────────────────────────────────────────

    def get_models(self, vram_gb: float) -> list:
        """Return tiered model options for given VRAM."""
        from installer.core.models import ModelRecommender
        recon = ModelRecommender()
        recommended = recon.get_recommended_models(vram_gb)
        all_models = recon.get_all_models()

        result = []
        for mtype in ["base", "image", "voice"]:
            rec = recommended.get(mtype)
            rec_name = rec.name if rec else ""
            options = []
            for model in sorted(all_models, key=lambda m: m.size_gb):
                if model.type == mtype:
                    options.append({
                        "name": model.name,
                        "hf_id": model.hf_id,
                        "size_gb": model.size_gb,
                        "min_vram_gb": model.min_vram_gb,
                        "recommended": model.name == rec_name,
                    })
            result.append({
                "type": mtype,
                "label": {"base": "Base Model", "image": "Image Model", "voice": "Voice Model"}[mtype],
                "options": options,
                "selected": rec_name,
            })
        return result

    def set_models(self, base: str, image: str, voice: str):
        """Store selected model names."""
        self.state.base_model = base
        self.state.image_model = image
        self.state.voice_model = voice

    # ── Install step ─────────────────────────────────────────────────────

    def start_install(self):
        """Start installation on a background thread."""
        t = threading.Thread(target=self._do_install, daemon=True)
        t.start()

    def _do_install(self):
        from installer.core.deps import DepResolver
        from installer.core.writer import ConfigWriter

        self.state.step = WizardStep.INSTALLING
        self.state.install_log = []
        self.state.packages = []

        try:
            # Resolve + install packages
            resolver = DepResolver()
            packages = resolver.resolve(
                require_voice=bool(self.state.voice_model),
                require_image=bool(self.state.image_model),
            )
            self.state.packages = [
                {"name": p.name, "status": p.status, "error": p.error}
                for p in packages
            ]

            to_install = [p for p in packages if p.install_action in ("install", "upgrade")]
            total = len(to_install) or 1

            for i, pkg in enumerate(to_install):
                pkg.status = "installing"
                self.state.packages[i]["status"] = "installing"
                self.state.install_log.append(f"Installing {pkg.name}...")
                try:
                    result = resolver.install_packages(
                        [pkg],
                        progress_callback=lambda p, m: self.state.install_log.append(m),
                    )
                    if result[0].status == "done":
                        pkg.status = "done"
                        self.state.packages[i]["status"] = "done"
                        self.state.install_log.append(f"  OK  {pkg.name}")
                    else:
                        pkg.status = "failed"
                        self.state.packages[i]["status"] = "failed"
                        self.state.packages[i]["error"] = pkg.error
                        self.state.install_log.append(f"  FAIL  {pkg.name}")
                except Exception as e:
                    pkg.status = "failed"
                    self.state.packages[i]["status"] = "failed"
                    self.state.packages[i]["error"] = str(e)
                    self.state.install_log.append(f"  FAIL  {pkg.name}: {e}")

                self.state.install_progress = ((i + 1) / total) * 0.8

            # Write config
            self._log_config("Writing config files...")
            hw = self.state.hw_profile
            try:
                ConfigWriter().write(
                    install_path=self.state.install_path,
                    base_model=self.state.base_model,
                    image_model=self.state.image_model,
                    voice_model=self.state.voice_model,
                    gpu_model=hw.get("gpu", "Unknown"),
                    vram_gb=hw.get("vram_gb", 0.0),
                    compute_capability=hw.get("compute_capability"),
                )
                self.state.install_log.append("  OK  Config files written")
                self.state.install_progress = 0.95
            except Exception as e:
                self.state.install_log.append(f"  WARN  Config write failed: {e}")

            self.state.install_progress = 1.0
            self.state.step = WizardStep.COMPLETE
            self.state.install_log.append("INSTALL COMPLETE")

        except Exception as e:
            import traceback
            self.state.error = str(e)
            self.state.install_log.append(f"FATAL ERROR: {e}")
            self.state.install_log.append(traceback.format_exc())

    def _log_config(self, msg: str):
        self.state.install_log.append(msg)

    def register_uninstaller(self, version: str) -> bool:
        """Register uninstaller in Windows Add/Remove Programs."""
        try:
            from installer.core.writer import ConfigWriter
            ConfigWriter().register_uninstaller(self.state.install_path, version)
            return True
        except Exception:
            return False

    # ── Finish step ──────────────────────────────────────────────────────

    def create_shortcuts_and_launch(self, desktop: bool, startmenu: bool, launch: bool):
        """Create shortcuts and optionally launch Moka AI, then close."""
        from installer.core.shortcuts import Shortcuts

        path = self.state.install_path
        if not path:
            return

        sc = Shortcuts(path)
        if desktop:
            try:
                sc.create_desktop_shortcut()
                self.state.install_log.append("Desktop shortcut created.")
            except Exception as e:
                self.state.install_log.append(f"Shortcut (desktop): {e}")
        if startmenu:
            try:
                sc.create_start_menu_shortcut()
                self.state.install_log.append("Start Menu shortcut created.")
            except Exception as e:
                self.state.install_log.append(f"Shortcut (start menu): {e}")

        self.state.shortcuts_created = True

        if launch:
            try:
                import subprocess, sys
                moka_py = os.path.join(path, "moka.py")
                subprocess.Popen(
                    [sys.executable, moka_py],
                    cwd=path,
                    creationflags=getattr(subprocess, "DETACHED_PROCESS", 0) if sys.platform == "win32" else 0,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                self.state.install_log.append("Moka AI launched.")
            except Exception as e:
                self.state.install_log.append(f"Launch: {e}")