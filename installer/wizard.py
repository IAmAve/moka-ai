"""Moka AI Installer — Dear PyGUI wizard entry point.

Usage: python wizard.py   (when installed via pip / pip install -e .)
   or: python installer/wizard.py  (from repo root during development)
"""

from __future__ import annotations

import os
import sys
import threading
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


# ── Color palette (Moka AI dark theme) ───────────────────────────────────────
BG = (22, 27, 34)           # #161B22 — main background
SURFACE = (33, 38, 45)       # #21262D — cards / panels
BORDER = (48, 54, 61)        # #30363D — dividers
ACCENT = (56, 139, 253)      # #388BFD — Moka blue
ACCENT_DIM = (56, 139, 253, 80)
TEXT = (230, 237, 243)       # #E6EDF3 — primary text
TEXT_MUTED = (139, 148, 158) # #8B949E — secondary text
SUCCESS = (63, 185, 80)       # #3FB950 — green
ERROR = (248, 81, 73)        # #F85149 — red
WARNING = (210, 168, 75)     # #D2A84B — amber
PURPLE = (163, 113, 247)     # #A371F7 — orb accent


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


# ── Logging ────────────────────────────────────────────────────────────────────

_log_tag = None


def _log(msg: str):
    state.log_lines.append(msg)
    if dpg.does_item_exist("log_area"):
        dpg.set_value("log_area", "\n".join(state.log_lines[-200:]))


# ── Directory picker ───────────────────────────────────────────────────────────

def _show_directory_picker(sender, app_data, user_data):
    selection = app_data.get("file_path", "")
    if selection:
        dpg.set_value("install_path_input", selection)
        state.install_path = selection


def _browse_install_path():
    dpg.show_item("directory_dialog")


# ── Page navigation ──────────────────────────────────────────────────────────

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
        # Header with orb accent dot
        with dpg.group(horizontal=True):
            dpg.add_text("●", color=PURPLE, tag="orb_dot", wrap=0)
            dpg.add_same_line()
            dpg.add_text("Moka AI Installer", tag="welcome_title", color=TEXT, wrap=400)
        dpg.add_text(f"Version {INSTALLER_VERSION}", color=TEXT_MUTED)
        dpg.add_separator(color=BORDER)

        dpg.add_text("Set up Moka AI on your machine. "
                     "Download models, configure settings, and create shortcuts.",
                     color=TEXT_MUTED, wrap=420)

        dpg.add_spacing()
        dpg.add_text("Installation directory:", color=TEXT)

        # Path input + Browse button on same line
        with dpg.group(horizontal=True):
            dpg.add_input_text(
                tag="install_path_input",
                default_value=_default_install_path(),
                width=420,
            )
            dpg.add_same_line()
            dpg.add_button(
                label="Browse...",
                callback=_browse_install_path,
                width=90,
            )

        dpg.add_spacing()

        # Directory picker dialog (hidden, triggered by Browse button)
        with dpg.file_dialog(
            tag="directory_dialog",
            show=False,
            directory_selector=True,
            min_size=(400, 300),
            callback=_show_directory_picker,
            default_path=_default_install_path(),
        ):
            dpg.add_file_extension("", color=ACCENT)
            dpg.add_file_extension(".MokaAI", color=TEXT_MUTED)

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
    threading.Thread(target=_do_hardware_scan, daemon=True).start()


# ── Hardware page ─────────────────────────────────────────────────────────────

def build_hardware_page():
    with dpg.group(parent="hardware_page"):
        dpg.add_text("Hardware Scan", color=TEXT, tag="hw_title", wrap=400)
        dpg.add_text("Detecting your hardware...", color=TEXT_MUTED, tag="hw_status")
        dpg.add_separator(color=BORDER)
        dpg.add_spacing()

        # GPU row
        with dpg.group(horizontal=True):
            dpg.add_text("GPU", color=TEXT_MUTED, width=100)
            dpg.add_text("Detecting...", tag="hw_gpu", color=TEXT)
        dpg.add_spacing()

        # VRAM row
        with dpg.group(horizontal=True):
            dpg.add_text("VRAM", color=TEXT_MUTED, width=100)
            dpg.add_text("—", tag="hw_vram", color=TEXT)
        dpg.add_spacing()

        # RAM row
        with dpg.group(horizontal=True):
            dpg.add_text("System RAM", color=TEXT_MUTED, width=100)
            dpg.add_text("—", tag="hw_ram", color=TEXT)
        dpg.add_spacing()

        # Platform row
        with dpg.group(horizontal=True):
            dpg.add_text("Platform", color=TEXT_MUTED, width=100)
            dpg.add_text("—", tag="hw_platform", color=TEXT)
        dpg.add_spacing()
        dpg.add_separator(color=BORDER)
        dpg.add_spacing()

        with dpg.group(horizontal=True):
            dpg.add_button(
                label="↻ Rescan",
                tag="btn_rescan_hw",
                callback=lambda: threading.Thread(target=_do_hardware_scan, daemon=True).start(),
            )
            dpg.add_same_line()
            dpg.add_button(
                label="Next →",
                tag="btn_next_from_hw",
                callback=lambda: show_page("models_page"),
                enabled=False,
            )


def _do_hardware_scan():
    # Run scan on background thread so UI never freezes
    dpg.set_value("hw_status", "Scanning hardware...")
    dpg.set_value("hw_gpu", "Detecting...")
    dpg.set_value("hw_vram", "—")
    dpg.set_value("hw_ram", "—")
    dpg.set_value("hw_platform", "—")
    try:
        scanner = HardwareScan()
        hw = scanner.scan()
        state.hw_profile = hw
        cc = hw.compute_capability or "N/A"
        dpg.set_value("hw_gpu", f"{hw.gpu_model}  (compute {cc})")
        dpg.set_value("hw_vram", f"{hw.vram_gb:.1f} GB")
        dpg.set_value("hw_ram", f"{hw.system_ram_gb:.1f} GB")
        dpg.set_value("hw_platform", hw.platform)
        dpg.set_value("hw_status", "Hardware detected successfully.")
        dpg.configure_item("btn_next_from_hw", enabled=True)
        _log(f"Hardware: {hw.gpu_model}, {hw.vram_gb:.0f}GB VRAM, "
             f"{hw.system_ram_gb:.0f}GB RAM, {hw.platform}")
    except Exception as e:
        dpg.set_value("hw_status", f"Scan failed: {e}")
        _log(f"Hardware scan error: {e}")


# ── Model selection page ──────────────────────────────────────────────────────

def build_models_page():
    with dpg.group(parent="models_page"):
        vram = state.hw_profile.vram_gb if state.hw_profile else 0.0
        dpg.add_text("Select AI Models", color=TEXT, tag="models_title", wrap=400)
        dpg.add_text(
            f"Recommended models for your {vram:.0f} GB VRAM:",
            color=TEXT_MUTED, wrap=400,
        )
        dpg.add_separator(color=BORDER)
        dpg.add_spacing()

        dpg.add_text("Base Model (coding / reasoning)", color=TEXT_MUTED)
        dpg.add_combo(
            tag="model_base",
            items=["auto"],
            default_value="auto",
            width=420,
            callback=_on_model_changed,
        )
        dpg.add_spacing()

        dpg.add_text("Image Model", color=TEXT_MUTED)
        dpg.add_combo(
            tag="model_image",
            items=["auto"],
            default_value="auto",
            width=420,
            callback=_on_model_changed,
        )
        dpg.add_spacing()

        dpg.add_text("Voice Model", color=TEXT_MUTED)
        dpg.add_combo(
            tag="model_voice",
            items=["auto"],
            default_value="auto",
            width=420,
            callback=_on_model_changed,
        )
        dpg.add_spacing()

        with dpg.group(horizontal=True):
            dpg.add_text("Total download size:", color=TEXT_MUTED)
            dpg.add_same_line()
            dpg.add_text("—", tag="model_total_size", color=ACCENT)

        dpg.add_spacing()
        dpg.add_separator(color=BORDER)
        dpg.add_spacing()

        with dpg.group(horizontal=True):
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

        # Populate combos after widgets exist
        _load_model_options()


def _load_model_options():
    try:
        recon = ModelRecommender()
        vram = state.hw_profile.vram_gb if state.hw_profile else 8.0
        recommended = recon.get_recommended_models(vram)
        all_models = recon.get_all_models()

        sizes = {"base": 0.0, "image": 0.0, "voice": 0.0}
        for model_type, default_m in recommended.items():
            items = []
            for m in all_models:
                if m.type == model_type:
                    items.append(f"{m.name}  ({m.size_gb:.1f} GB)")
            if items:
                tag = f"model_{model_type}"
                if dpg.does_item_exist(tag):
                    default_label = (
                        f"{default_m.name}  ({default_m.size_gb:.1f} GB)"
                        if default_m else items[0]
                    )
                    dpg.configure_item(tag, items=items, default_value=default_label)
                    state.selected_models[model_type] = default_m
                    sizes[model_type] = default_m.size_gb if default_m else 0.0

        total = sizes["base"] + sizes["image"] + sizes["voice"]
        dpg.set_value("model_total_size", f"~{total:.1f} GB")
    except Exception as e:
        _log(f"Could not load models: {e}")


def _on_model_changed(sender, app_data):
    _log(f"Model: {sender} = {app_data}")


def _on_install_click():
    base_val = dpg.get_value("model_base")
    image_val = dpg.get_value("model_image")
    voice_val = dpg.get_value("model_voice")

    state.packages = DepResolver().resolve(
        require_voice=voice_val not in ("", "auto"),
        require_image=image_val not in ("", "auto"),
    )
    show_page("install_page")
    threading.Thread(target=_do_install, daemon=True).start()


# ── Installation page ─────────────────────────────────────────────────────────

def build_install_page():
    with dpg.group(parent="install_page"):
        dpg.add_text("Installing Moka AI...", color=TEXT, tag="install_title", wrap=400)
        dpg.add_separator(color=BORDER)
        dpg.add_spacing()

        with dpg.group(horizontal=True):
            dpg.add_text("Progress:", color=TEXT_MUTED)
            dpg.add_same_line()
            dpg.add_text("0%", tag="progress_pct", color=ACCENT)
        dpg.add_progress_bar(tag="progress_bar", default_value=0.0, width=500, height=16)
        dpg.add_spacing()

        dpg.add_text("Preparing...", tag="install_status", color=TEXT_MUTED)
        dpg.add_spacing()

        with dpg.group(horizontal=True):
            dpg.add_text("Log:", color=TEXT_MUTED)
        dpg.add_input_text(
            tag="log_area",
            multiline=True,
            readonly=True,
            width=700,
            height=180,
        )


def _do_install():
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
        dpg.configure_item("progress_bar", default_value=0.25)
        dpg.set_value("progress_pct", "25%")

        DepResolver().install_packages(
            state.packages,
            progress_callback=lambda pkg, msg: _log(msg),
        )
        dpg.set_value("install_status", "All packages installed.")
        dpg.configure_item("progress_bar", default_value=0.85)
        dpg.set_value("progress_pct", "85%")
        _log("Installation complete!")
        dpg.configure_item("progress_bar", default_value=1.0)
        dpg.set_value("progress_pct", "100%")
        dpg.set_value("finish_install_status", "Installation complete!")
        dpg.set_value("finish_title", "Moka AI Installed!")
        show_page("finish_page")

    except Exception as e:
        _log(f"ERROR: {e}")
        dpg.set_value("install_status", f"Error: {e}")


# ── Finish page ───────────────────────────────────────────────────────────────

def build_finish_page():
    with dpg.group(parent="finish_page"):
        dpg.add_text("Moka AI Installed!", color=SUCCESS,
                     tag="finish_title", wrap=400)
        dpg.add_separator(color=BORDER)
        dpg.add_spacing()
        dpg.add_text(f"Location: {state.install_path}", color=TEXT_MUTED)
        dpg.add_spacing()
        dpg.add_text("Installation completed successfully.",
                     tag="finish_install_status", color=TEXT, wrap=400)
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
        dpg.add_separator(color=BORDER)
        dpg.add_spacing()
        dpg.add_button(label="Finish", tag="btn_finish", callback=_on_finish)


def _on_finish():
    if dpg.get_value("cb_desktop_shortcut"):
        try:
            Shortcuts(state.install_path).create_desktop_shortcut()
            _log("Desktop shortcut created.")
        except Exception as e:
            _log(f"Shortcut: {e}")

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
            _log(f"Launch: {e}")

    dpg.stop_dearpygui()


# ── Dark theme setup ───────────────────────────────────────────────────────────

def _apply_theme():
    """Apply Moka AI dark theme to the Dear PyGUI context."""
    with dpg.theme(tag="moka_theme"):
        with dpg.theme_widget():
            # Window background
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, BG, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, SURFACE, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_PopupBg, SURFACE, category=dpg.mvThemeCat_Core)
            # Text
            dpg.add_theme_color(dpg.mvThemeCol_Text, TEXT, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_TextDisabled, TEXT_MUTED, category=dpg.mvThemeCat_Core)
            # Buttons
            dpg.add_theme_color(dpg.mvThemeCol_Button, SURFACE, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (40, 47, 56), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (52, 60, 72), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_Border, BORDER, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_BorderShadow, (0, 0, 0, 0), category=dpg.mvThemeCat_Core)
            # Separator
            dpg.add_theme_color(dpg.mvThemeCol_Separator, BORDER, category=dpg.mvThemeCat_Core)
            # Progress bar
            dpg.add_theme_color(dpg.mvThemeCol_PlotHistogram, ACCENT, category=dpg.mvThemeCat_Core)
            # Frame
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, SURFACE, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, (40, 47, 56), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, (48, 55, 65), category=dpg.mvThemeCat_Core)
            # Input text
            dpg.add_theme_color(dpg.mvThemeCol_InputText, SURFACE, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_InputTextBorder, BORDER, category=dpg.mvThemeCat_Core)
            # Combo
            dpg.add_theme_color(dpg.mvThemeCol_Combo, SURFACE, category=dpg.mvThemeCat_Core)
            # Checkbox
            dpg.add_theme_color(dpg.mvThemeCol_CheckMark, ACCENT, category=dpg.mvThemeCat_Core)
            # Header
            dpg.add_theme_color(dpg.mvThemeCol_Header, SURFACE, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, (40, 47, 56), category=dpg.mvThemeCat_Core)
            # Slider
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrab, ACCENT, category=dpg.mvThemeCat_Core)

        # Apply to viewport
        dpg.bind_theme("moka_theme")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    import traceback
    log_path = os.path.join(
        os.environ.get("TEMP", "C:\\Users\\Ave\\AppData\\Local\\Temp"),
        "moka_install.log"
    )
    log_file = open(log_path, "w", buffering=1)

    def log(msg):
        log_file.write(msg + "\n")
        log_file.flush()

    def log_error(label, e, tb):
        log(f"[ERROR] {label}: {e}")
        tb_str = ''.join(traceback.format_exception(type(e), e, tb))
        log_file.write(tb_str)
        log_file.flush()

    log("Moka AI Installer starting")
    try:
        dpg.create_context()
    except Exception as e:
        log_error("create_context", e, e.__traceback__)
        log_file.close()
        return

    _apply_theme()

    try:
        dpg.create_viewport(
            title=f"Moka AI Installer  v{INSTALLER_VERSION}",
            width=840, height=680, min_size=(700, 600),
            resizable=True,
            bg_color=BG,
        )
    except Exception as e:
        log_error("create_viewport", e, e.__traceback__)
        log_file.close()
        return

    try:
        with dpg.window(
            tag="main_window",
            width=840, height=680,
            pos=(0, 0),
            no_move=True,
            no_close=True,
        ):
            dpg.add_text(
                "Moka AI Installer",
                tag="page_title",
                color=ACCENT,
                wrap=400,
            )
            dpg.add_separator(color=BORDER)
            dpg.add_spacing()

            for tag, builder in [
                ("welcome_page", build_welcome_page),
                ("hardware_page", build_hardware_page),
                ("models_page", build_models_page),
                ("install_page", build_install_page),
                ("finish_page", build_finish_page),
            ]:
                try:
                    with dpg.group(tag=tag, show=(tag == "welcome_page")):
                        builder()
                        log(f"{tag}: built OK")
                except Exception as e:
                    log_error(tag, e, e.__traceback__)

    except Exception as e:
        log_error("window build", e, e.__traceback__)
        log_file.close()
        return

    try:
        dpg.setup_dearpygui()
    except Exception as e:
        log_error("setup_dearpygui", e, e.__traceback__)
        log_file.close()
        return

    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()
    log_file.close()


if __name__ == "__main__":
    main()