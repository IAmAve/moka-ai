"""Moka AI Installer — Dear PyGUI wizard entry point.

Usage: python wizard.py   (when installed via pip / pip install -e .)
   or: python installer/wizard.py  (from repo root during development)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure bundled Python can find bundled packages (PyInstaller _MEIPASS support)
import site
if hasattr(sys, "_MEIPASS"):
    site.addsitedir(sys._MEIPASS)

import dearpygui.dearpygui as dpg

from installer.core.hardware import HardwareScan
from installer.core.models import ModelRecommender
from installer.core.deps import DepResolver
from installer.core.writer import ConfigWriter
from installer.core.shortcuts import Shortcuts


class InstallerState:
    __slots__ = ("install_path", "hw_profile", "selected_models",
                 "packages", "log_lines")

    def __init__(self):
        self.install_path = ""
        self.hw_profile = None
        self.selected_models: dict = {"base": None, "image": None, "voice": None}
        self.packages = []
        self.log_lines: list = []


state = InstallerState()
INSTALLER_VERSION = "0.1.0"


def _default_install_path() -> str:
    if sys.platform == "win32":
        return str(Path(os.environ["LOCALAPPDATA"]) / "MokaAI")
    elif sys.platform == "darwin":
        return str(Path.home() / "Library" / "Application Support" / "MokaAI")
    else:
        return str(Path.home() / ".local" / "share" / "moka-ai")


_log_tag = None


def _log(msg: str):
    state.log_lines.append(msg)
    if dpg.does_item_exist("log_area"):
        dpg.set_value("log_area", "\n".join(state.log_lines[-200:]))


# ── Page navigation ─────────────────────────────────────────────────────────

def show_page(page_tag: str):
    for tag in ["welcome_page", "hardware_page", "models_page",
                "install_page", "finish_page"]:
        dpg.hide_item(tag)
    dpg.show_item(page_tag)
    if page_tag == "install_page":
        dpg.set_value("page_title", "Installing Moka AI...")
    elif page_tag == "finish_page":
        dpg.set_value("page_title", "Installation Complete!")


# ── Welcome page ────────────────────────────────────────────────────────────

def build_welcome_page():
    with dpg.group(parent="welcome_page"):
        dpg.add_text("Moka AI Installer", tag="welcome_title", wrap=400)
        dpg.add_text(f"Version {INSTALLER_VERSION}", color=(130, 130, 130))
        dpg.add_separator()
        dpg.add_spacing()
        dpg.add_text("This installer will set up Moka AI on your machine.")
        dpg.add_text(
            "Installing will download the selected AI models, "
            "set up configuration, and optionally create shortcuts.",
            wrap=400,
        )
        dpg.add_spacing()
        dpg.add_text("Installation directory:", color=(200, 200, 200))
        dpg.add_input_text(
            tag="install_path_input",
            default_value=_default_install_path(),
            width=450,
        )
        dpg.add_spacing()
        dpg.add_button(
            label="Next →",
            tag="btn_next_from_welcome",
            callback=lambda: _on_welcome_next(),
        )


def _on_welcome_next():
    path = dpg.get_value("install_path_input").strip()
    if not path:
        return
    state.install_path = path
    show_page("hardware_page")
    _do_hardware_scan()


# ── Hardware page ─────────────────────────────────────────────────────────────

def build_hardware_page():
    with dpg.group(parent="hardware_page"):
        dpg.add_text("Hardware Scan", tag="hw_title", wrap=400)
        dpg.add_text("We detected the following hardware:", color=(180, 180, 180))
        dpg.add_spacing()

        dpg.add_text("GPU:", color=(200, 200, 200))
        dpg.add_text("Detecting...", tag="hw_gpu")
        dpg.add_spacing()
        dpg.add_text("VRAM:", color=(200, 200, 200))
        dpg.add_text("Detecting...", tag="hw_vram")
        dpg.add_spacing()
        dpg.add_text("System RAM:", color=(200, 200, 200))
        dpg.add_text("Detecting...", tag="hw_ram")
        dpg.add_spacing()
        dpg.add_text("Platform:", color=(200, 200, 200))
        dpg.add_text("Detecting...", tag="hw_platform")
        dpg.add_spacing()

        dpg.add_button(label="Re-scan", tag="btn_rescan_hw", callback=_do_hardware_scan)
        dpg.add_same_line()
        dpg.add_button(
            label="Next →",
            tag="btn_next_from_hw",
            callback=lambda: show_page("models_page"),
            enabled=False,
        )


def _do_hardware_scan():
    try:
        scanner = HardwareScan()
        state.hw_profile = scanner.scan()
        cc = state.hw_profile.compute_capability or "N/A"
        dpg.set_value("hw_gpu", f"{state.hw_profile.gpu_model} (compute {cc})")
        dpg.set_value("hw_vram", f"{state.hw_profile.vram_gb} GB")
        dpg.set_value("hw_ram", f"{state.hw_profile.system_ram_gb} GB")
        dpg.set_value("hw_platform", state.hw_profile.platform)
        _log(f"Hardware scan: {state.hw_profile.gpu_model}, "
             f"{state.hw_profile.vram_gb}GB VRAM, "
             f"{state.hw_profile.system_ram_gb}GB RAM")
        dpg.enable_item("btn_next_from_hw")
    except Exception as e:
        _log(f"Hardware scan failed: {e}")


# ── Model selection page ──────────────────────────────────────────────────────

def build_models_page():
    with dpg.group(parent="models_page"):
        vram = state.hw_profile.vram_gb if state.hw_profile else 0.0
        dpg.add_text("Select AI Models", tag="models_title", wrap=400)
        dpg.add_text(
            f"Recommended models for your {vram:.0f} GB VRAM:",
            color=(180, 180, 180),
            wrap=400,
        )
        dpg.add_spacing()

        dpg.add_text("Base Model (coding/reasoning):", color=(200, 200, 200))
        dpg.add_combo(
            tag="model_base",
            items=["auto"],
            default_value="auto",
            width=400,
            callback=_on_model_changed,
        )
        dpg.add_spacing()
        dpg.add_text("Image Model:", color=(200, 200, 200))
        dpg.add_combo(
            tag="model_image",
            items=["auto"],
            default_value="auto",
            width=400,
            callback=_on_model_changed,
        )
        dpg.add_spacing()
        dpg.add_text("Voice Model:", color=(200, 200, 200))
        dpg.add_combo(
            tag="model_voice",
            items=["auto"],
            default_value="auto",
            width=400,
            callback=_on_model_changed,
        )
        dpg.add_spacing()
        dpg.add_text("Estimated download size:", color=(200, 200, 200))
        dpg.add_text("—", tag="model_total_size")
        dpg.add_spacing()

        # Load model options after widgets are created
        import dearpygui.dearpygui as dpg
        dpg.insert_value(dpg.add_value_registry(), "model_base", "auto")

        dpg.add_button(
            label="← Back",
            callback=lambda: show_page("hardware_page"),
        )
        dpg.add_same_line()
        dpg.add_button(
            label="Install →",
            tag="btn_next_from_models",
            callback=_on_install_click,
        )

        # Populate model combos
        _load_model_options()


def _load_model_options():
    """Populate model combos with tier-appropriate options."""
    try:
        recon = ModelRecommender()
        vram = state.hw_profile.vram_gb if state.hw_profile else 8.0
        recommended = recon.get_recommended_models(vram)
        all_models = recon.get_all_models()

        for model_type, default_m in recommended.items():
            items = []
            for m in all_models:
                if m.type == model_type:
                    label = f"{m.name} ({m.size_gb:.1f} GB)"
                    items.append(label)
            if items:
                tag = f"model_{model_type}"
                if dpg.does_item_exist(tag):
                    default_label = (
                        f"{default_m.name} ({default_m.size_gb:.1f} GB)"
                        if default_m else items[0]
                    )
                    dpg.configure_item(tag, items=items, default_value=default_label)
                    state.selected_models[model_type] = default_m
    except Exception as e:
        _log(f"Could not load model options: {e}")


def _on_model_changed(sender, app_data):
    _log(f"Model selected: {sender} = {app_data}")


def _on_install_click():
    base_val = dpg.get_value("model_base")
    image_val = dpg.get_value("model_image")
    voice_val = dpg.get_value("model_voice")

    state.packages = DepResolver().resolve(
        require_voice=voice_val not in ("", "auto"),
        require_image=image_val not in ("", "auto"),
    )
    show_page("install_page")
    _do_install()


# ── Installation page ─────────────────────────────────────────────────────────

def build_install_page():
    with dpg.group(parent="install_page"):
        dpg.add_text("Installing Moka AI...", tag="install_title", wrap=400)
        dpg.add_separator()
        dpg.add_spacing()
        dpg.add_text("Progress:", color=(200, 200, 200))
        dpg.add_progress_bar(tag="progress_bar", default_value=0.0, width=500, height=20)
        dpg.add_spacing()
        dpg.add_text("Status:", color=(200, 200, 200))
        dpg.add_text("Preparing installation...", tag="install_status")
        dpg.add_spacing()
        dpg.add_text("Log:", color=(200, 200, 200))
        dpg.add_input_text(
            tag="log_area",
            multiline=True,
            readonly=True,
            width=700,
            height=200,
        )


def _do_install():
    """Run install steps in background thread."""
    import threading

    def install_thread():
        try:
            install_path = Path(state.install_path)
            for subdir in ["temp", "models", "data", "logs", "plugins"]:
                (install_path / subdir).mkdir(parents=True, exist_ok=True)
            _log(f"Directories created in {install_path}")

            writer = ConfigWriter()
            writer.write(
                install_path=str(install_path),
                base_model=state.selected_models.get("base", {}).get("hf_id", "")
                if hasattr(state.selected_models.get("base", {}), "hf_id")
                else "",
                image_model="",
                voice_model="",
                gpu_model=state.hw_profile.gpu_model if state.hw_profile else "Unknown",
                vram_gb=state.hw_profile.vram_gb if state.hw_profile else 0.0,
                compute_capability=state.hw_profile.compute_capability
                if state.hw_profile else None,
            )
            writer.register_uninstaller(str(install_path), INSTALLER_VERSION)
            _log("Config written and uninstaller registered.")
            dpg.set_value("install_status", "Installing packages...")
            dpg.configure_item("progress_bar", default_value=0.2)

            DepResolver().install_packages(
                state.packages,
                progress_callback=lambda pkg, msg: _log(msg),
            )
            dpg.set_value("install_status", "All packages installed.")
            dpg.configure_item("progress_bar", default_value=0.9)
            _log("Installation complete!")
            dpg.configure_item("progress_bar", default_value=1.0)

            def _switch():
                show_page("finish_page")
            dpg.set_value("finish_install_status", "Installation complete!")
            _switch()

        except Exception as e:
            _log(f"ERROR: {e}")
            dpg.set_value("install_status", f"Error: {e}")

    t = threading.Thread(target=install_thread, daemon=True)
    t.start()


# ── Finish page ───────────────────────────────────────────────────────────────

def build_finish_page():
    with dpg.group(parent="finish_page"):
        dpg.add_text("Moka AI Installed!", tag="finish_title",
                     color=(100, 255, 150), wrap=400)
        dpg.add_spacing()
        dpg.add_text(f"Location: {state.install_path}", color=(180, 180, 180))
        dpg.add_spacing()
        dpg.add_text("Installation completed successfully.", tag="finish_install_status",
                     color=(180, 180, 180), wrap=400)
        dpg.add_spacing()

        dpg.add_checkbox(
            label="Create Desktop Shortcut",
            default_value=True,
            tag="cb_desktop_shortcut",
        )
        dpg.add_checkbox(
            label="Launch Moka AI now",
            default_value=True,
            tag="cb_launch",
        )
        dpg.add_spacing()

        dpg.add_button(label="Finish", tag="btn_finish", callback=_on_finish)


def _on_finish():
    if dpg.get_value("cb_desktop_shortcut"):
        try:
            Shortcuts(state.install_path).create_desktop_shortcut()
            _log("Desktop shortcut created.")
        except Exception as e:
            _log(f"Shortcut failed: {e}")

    if dpg.get_value("cb_launch"):
        try:
            import subprocess
            subprocess.Popen(
                [sys.executable, str(Path(state.install_path) / "moka.py")],
                cwd=state.install_path,
                detach=True,
            )
            _log("Launched Moka AI.")
        except Exception as e:
            _log(f"Launch failed: {e}")

    dpg.stop_dearpygui()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    dpg.create_context()
    dpg.create_viewport(
        title=f"Moka AI Installer v{INSTALLER_VERSION}",
        width=800,
        height=650,
        resizable=True,
    )

    # Use default DPG styling (dark theme handled via viewport background if needed)
    with dpg.window(tag="main_window", no_title_bar=False,
                    width=800, height=650, pos=(0, 0)):
        dpg.add_text("Moka AI Installer", tag="page_title", wrap=400)
        dpg.add_separator()
        dpg.add_spacing()

        with dpg.group(tag="welcome_page", show=True):
            build_welcome_page()
        with dpg.group(tag="hardware_page", show=False):
            build_hardware_page()
        with dpg.group(tag="models_page", show=False):
            build_models_page()
        with dpg.group(tag="install_page", show=False):
            build_install_page()
        with dpg.group(tag="finish_page", show=False):
            build_finish_page()

    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()


if __name__ == "__main__":
    main()