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


# ── Moka AI dark color palette ───────────────────────────────────────────────
# Inspired by Moka AI orb: deep slate bg + electric blue accent + purple glow
BACKGROUND  = (13, 17, 23)    # #0D1117 — GitHub-dark style main bg
PANEL       = (22, 27, 34)    # #161B22 — card / panel surfaces
BORDER      = (38, 44, 54)     # #262E3A — subtle borders
ACCENT      = (56, 139, 253)  # #388BFD — Moka blue CTA / links
ACCENT_HOVER= (70, 151, 255)   # lighter blue on hover
TEXT_PRIMARY = (229, 235, 241) # #E5EBF1
TEXT_MUTED  = (99, 110, 123)   # #636E7B
SUCCESS     = (46, 192, 124)   # #3FC07C — green
WARNING     = (213, 168, 75)  # #D5A84B — amber
ORB_PURPLE  = (163, 113, 247)  # #A371F7 — the moka orb accent
INTEL_BLUE  = (0, 117, 200)    # Intel brand blue
AMD_RED     = (237, 42, 39)    # AMD brand red


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


# ── Welcome page ──────────────────────────────────────────────────────────────

def build_welcome_page():
    with dpg.group(parent="welcome_page"):
        # Header: orb icon + title
        with dpg.group(horizontal=True):
            dpg.add_text("◉", color=ORB_PURPLE, tag="orb_icon", wrap=0)
            dpg.add_same_line()
            dpg.add_text("Moka AI Installer", tag="welcome_title",
                          color=TEXT_PRIMARY, bold=True, wrap=400)
        dpg.add_text(f"v{INSTALLER_VERSION}", color=TEXT_MUTED, tag="welcome_ver")
        dpg.add_separator(color=BORDER)
        dpg.add_spacing()

        dpg.add_text("Set up Moka AI on your machine. "
                     "Download AI models, configure settings, and "
                     "create shortcuts.",
                     color=TEXT_MUTED, wrap=440)
        dpg.add_spacing()

        # Installation path row
        dpg.add_text("Installation directory", color=TEXT_MUTED, tag="path_label")
        dpg.add_spacing(count=1)
        with dpg.group(horizontal=True):
            dpg.add_input_text(
                tag="install_path_input",
                default_value=_default_install_path(),
                width=440,
            )
            dpg.add_same_line()
            dpg.add_button(
                label="Browse...",
                callback=_browse_install_path,
                width=90,
            )

        # Directory dialog
        with dpg.file_dialog(
            tag="directory_dialog",
            show=False,
            directory_selector=True,
            min_size=(480, 360),
            callback=_show_directory_picker,
            default_path=_default_install_path(),
        ):
            dpg.add_file_extension("", color=ACCENT)
            dpg.add_file_extension(".MokaAI", color=TEXT_MUTED)

        dpg.add_spacing()

        # Terms note
        dpg.add_text(
            "By clicking Next, you agree to the MIT license and "
            "acknowledge that AI models will be downloaded.",
            color=TEXT_MUTED, wrap=420,
        )
        dpg.add_spacing()

        dpg.add_button(
            label="Next  →",
            tag="btn_next_from_welcome",
            callback=lambda: _on_welcome_next(),
            width=120,
        )


def _on_welcome_next():
    path = dpg.get_value("install_path_input").strip()
    if not path:
        return
    state.install_path = path
    show_page("hardware_page")
    threading.Thread(target=_do_hardware_scan, daemon=True).start()


# ── Hardware page ──────────────────────────────────────────────────────────────

def _gpu_color(name: str):
    """Return brand-appropriate color for GPU."""
    n = name.lower()
    if "intel" in n:
        return INTEL_BLUE
    if "amd" in n or "radeon" in n or "rx " in n:
        return AMD_RED
    if "nvidia" in n or "geforce" in n or "rtx" in n or "gtx" in n:
        return ACCENT
    return TEXT_PRIMARY


def _gpu_tag(prefix: str, idx: int) -> str:
    return f"{prefix}_{idx}"


def build_hardware_page():
    with dpg.group(parent="hardware_page"):
        dpg.add_text("Hardware Scan", color=TEXT_PRIMARY, tag="hw_title",
                      bold=True, wrap=400)
        dpg.add_text("Detecting your hardware automatically...",
                      color=TEXT_MUTED, tag="hw_status", wrap=400)
        dpg.add_separator(color=BORDER)
        dpg.add_spacing()

        # ── CPU card ──────────────────────────────────────────────────────────
        with dpg.group(horizontal=True):
            dpg.add_text("[CPU]", color=ACCENT, width=70)
            dpg.add_text("Detecting...", tag="hw_cpu", color=TEXT_PRIMARY)
        dpg.add_spacing(count=1)

        # ── GPU card(s) ───────────────────────────────────────────────────────
        dpg.add_text("[GPU]", color=ACCENT, width=70, tag="gpu_label_anchor")
        # We create tags for 2 possible GPUs
        for i in range(2):
            tag = _gpu_tag("hw_gpu", i)
            with dpg.group(horizontal=True, show=(i == 0)):
                dpg.add_text(f"  ▶", color=TEXT_MUTED, tag=_gpu_tag("gpu_arrow", i))
                dpg.add_text(f"GPU {i+1}:", color=TEXT_MUTED, width=50,
                             tag=_gpu_tag("gpu_label", i))
                dpg.add_text("Detecting...", tag=tag, color=TEXT_PRIMARY)
            dpg.add_spacing(count=1)

        # Primary GPU highlight (shown after scan)
        dpg.add_text("Primary GPU:", color=TEXT_MUTED, tag="hw_primary_gpu_label",
                     show=False)
        dpg.add_text("", tag="hw_primary_gpu", color=ACCENT, show=False)
        dpg.add_spacing(count=1)

        # ── Memory ───────────────────────────────────────────────────────────
        with dpg.group(horizontal=True):
            dpg.add_text("[RAM]", color=ACCENT, width=70)
            dpg.add_text("Detecting...", tag="hw_ram", color=TEXT_PRIMARY)
        dpg.add_spacing(count=1)

        # ── OS ───────────────────────────────────────────────────────────────
        with dpg.group(horizontal=True):
            dpg.add_text("[OS]", color=ACCENT, width=70)
            dpg.add_text("Detecting...", tag="hw_os", color=TEXT_PRIMARY)
        dpg.add_spacing()

        dpg.add_separator(color=BORDER)
        dpg.add_spacing()

        with dpg.group(horizontal=True):
            dpg.add_button(
                label="↻  Rescan",
                tag="btn_rescan_hw",
                callback=lambda: threading.Thread(
                    target=_do_hardware_scan, daemon=True
                ).start(),
                width=100,
            )
            dpg.add_same_line()
            dpg.add_button(
                label="Next  →",
                tag="btn_next_from_hw",
                callback=lambda: show_page("models_page"),
                enabled=False,
                width=100,
            )


def _do_hardware_scan():
    """Run hardware scan on background thread, update UI safely."""
    dpg.set_value("hw_status", "Scanning...")
    try:
        scanner = HardwareScan()
        hw = scanner.scan()
        state.hw_profile = hw

        # CPU
        cpu_label = hw.cpu_model or "Unknown CPU"
        if hw.cpu_cores and hw.cpu_threads:
            cpu_label += f"  ({hw.cpu_cores}C / {hw.cpu_threads}T)"
        dpg.set_value("hw_cpu", cpu_label)

        # OS
        os_label = f"{hw.platform} {platform.release()}"
        try:
            import subprocess
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-WmiObject Win32_OperatingSystem).Caption"],
                capture_output=True, text=True, timeout=5,
            )
            win_caption = r.stdout.strip()
            if win_caption:
                os_label = win_caption
        except Exception:
            pass
        dpg.set_value("hw_os", os_label)

        # RAM
        dpg.set_value("hw_ram", f"{hw.system_ram_gb:.1f} GB available "
                            f"({hw.available_vram_gb:.1f} GB free)")

        # GPUs — show all detected
        all_gpus = hw.all_gpus if hw.all_gpus else [(hw.gpu_model, hw.vram_gb)]
        for i, (gpu_name, gpu_vram) in enumerate(all_gpus[:2]):
            tag = _gpu_tag("hw_gpu", i)
            if dpg.does_item_exist(tag):
                dpg.configure_item(tag, show=True)
                arrow_tag = _gpu_tag("gpu_arrow", i)
                label_tag = _gpu_tag("gpu_label", i)
                if i == 0:
                    dpg.configure_item(arrow_tag, show=True)
                    dpg.configure_item(label_tag, show=True)
                # Tag primary
                gpu_label = f"{gpu_name}  ({gpu_vram:.1f} GB)" if gpu_vram > 0 else gpu_name
                dpg.set_value(tag,
                    f"{gpu_name}  —  {gpu_vram:.1f} GB VRAM" if gpu_vram > 0 else gpu_name)
                dpg.configure_item(tag, color=_gpu_color(gpu_name))

        # Primary GPU
        primary_name = hw.gpu_model
        primary_vram = hw.vram_gb
        if primary_vram > 0:
            dpg.set_value("hw_primary_gpu",
                          f"{primary_name}  ({primary_vram:.1f} GB VRAM)")
            dpg.configure_item("hw_primary_gpu", color=_gpu_color(primary_name))
        else:
            dpg.set_value("hw_primary_gpu", primary_name)
        dpg.configure_item("hw_primary_gpu", show=True)
        dpg.configure_item("hw_primary_gpu_label", show=True)

        # Status
        dpg.set_value("hw_status",
                      f"Found {len(all_gpus)} GPU(s). Hardware scan complete.")
        dpg.configure_item("btn_next_from_hw", enabled=True)
        _log(f"Hardware: {cpu_label} | "
             f"{' | '.join([g[0] for g in all_gpus])} | "
             f"{hw.system_ram_gb:.0f}GB RAM")

    except Exception as e:
        dpg.set_value("hw_status", f"Scan failed: {e}")
        _log(f"Hardware scan error: {e}")


# ── Model selection page ───────────────────────────────────────────────────────

def build_models_page():
    with dpg.group(parent="models_page"):
        vram = state.hw_profile.vram_gb if state.hw_profile else 0.0
        dpg.add_text("Select AI Models", color=TEXT_PRIMARY, tag="models_title",
                     bold=True, wrap=400)
        dpg.add_text(
            f"Recommended models for your hardware "
            f"({vram:.0f} GB available VRAM):",
            color=TEXT_MUTED, wrap=400,
        )
        dpg.add_separator(color=BORDER)
        dpg.add_spacing()

        for model_type, label in [
            ("base", "Base Model  (coding & reasoning)"),
            ("image", "Image Model  (text → image)"),
            ("voice", "Voice Model  (TTS & STT)"),
        ]:
            dpg.add_text(label, color=TEXT_MUTED)
            dpg.add_combo(
                tag=f"model_{model_type}",
                items=["auto"],
                default_value="auto",
                width=440,
                callback=_on_model_changed,
            )
            dpg.add_spacing(count=1)

        dpg.add_separator(color=BORDER)
        dpg.add_spacing()

        with dpg.group(horizontal=True):
            dpg.add_text("Estimated total size:", color=TEXT_MUTED)
            dpg.add_same_line()
            dpg.add_text("—", tag="model_total_size", color=ACCENT, bold=True)

        dpg.add_spacing()
        dpg.add_button(
            label="←  Back",
            callback=lambda: show_page("hardware_page"),
            width=100,
        )
        dpg.add_same_line()
        dpg.add_button(
            label="Install  →",
            tag="btn_next_from_models",
            callback=_on_install_click,
            width=140,
        )

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
        dpg.add_text("Installing Moka AI...", color=TEXT_PRIMARY, tag="install_title",
                     bold=True, wrap=400)
        dpg.add_separator(color=BORDER)
        dpg.add_spacing()

        with dpg.group(horizontal=True):
            dpg.add_text("Progress:", color=TEXT_MUTED)
            dpg.add_same_line()
            dpg.add_text("0%", tag="progress_pct", color=ACCENT, bold=True)
        dpg.add_progress_bar(tag="progress_bar", default_value=0.0,
                              width=540, height=18)
        dpg.add_spacing(count=1)
        dpg.add_text("", tag="install_status", color=SUCCESS)
        dpg.add_spacing()

        with dpg.group(horizontal=True):
            dpg.add_text("Log:", color=TEXT_MUTED)
        dpg.add_input_text(
            tag="log_area",
            multiline=True,
            readonly=True,
            width=680,
            height=200,
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
        dpg.set_value("finish_install_status",
                      "Moka AI is installed and ready to run!")
        show_page("finish_page")

    except Exception as e:
        _log(f"ERROR: {e}")
        dpg.set_value("install_status", f"Error: {e}")


# ── Finish page ───────────────────────────────────────────────────────────────

def build_finish_page():
    with dpg.group(parent="finish_page"):
        dpg.add_text("✓", color=SUCCESS, tag="finish_icon", wrap=0)
        dpg.add_same_line()
        dpg.add_text("Moka AI Installed!", color=SUCCESS, tag="finish_title",
                     bold=True, wrap=400)
        dpg.add_text(f"Location: {state.install_path}", color=TEXT_MUTED)
        dpg.add_separator(color=BORDER)
        dpg.add_spacing()
        dpg.add_text("Installation completed successfully.",
                     tag="finish_install_status", color=TEXT_PRIMARY, wrap=400)
        dpg.add_spacing()

        dpg.add_checkbox(
            label="Create Desktop Shortcut",
            default_value=True,
            tag="cb_desktop_shortcut",
        )
        dpg.add_spacing(count=1)
        dpg.add_checkbox(
            label="Launch Moka AI now",
            default_value=True,
            tag="cb_launch",
        )
        dpg.add_spacing()
        dpg.add_separator(color=BORDER)
        dpg.add_spacing()

        dpg.add_button(
            label="Finish",
            tag="btn_finish",
            callback=_on_finish,
            width=100,
        )


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


# ── Theme ─────────────────────────────────────────────────────────────────────

def _apply_theme():
    with dpg.theme(tag="moka_dark"):
        # Core colors
        with dpg.theme_widget():
            # Window / panels
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, BACKGROUND, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, PANEL, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_PopupBg, PANEL, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_Border, BORDER, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_BorderShadow, (0, 0, 0), category=dpg.mvThemeCat_Core)
            # Text
            dpg.add_theme_color(dpg.mvThemeCol_Text, TEXT_PRIMARY, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_TextDisabled, TEXT_MUTED, category=dpg.mvThemeCat_Core)
            # Separator
            dpg.add_theme_color(dpg.mvThemeCol_Separator, BORDER, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_SeparatorHovered, BORDER, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_SeparatorActive, BORDER, category=dpg.mvThemeCat_Core)
            # Buttons
            dpg.add_theme_color(dpg.mvThemeCol_Button, PANEL, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (30, 40, 52), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (36, 48, 62), category=dpg.mvThemeCat_Core)
            # Frame / input
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, PANEL, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, (30, 40, 52), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, (36, 48, 62), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_InputText, PANEL, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_InputTextBorder, BORDER, category=dpg.mvThemeCat_Core)
            # Combo
            dpg.add_theme_color(dpg.mvThemeCol_Combo, PANEL, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ComboHovered, (30, 40, 52), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ComboBorder, BORDER, category=dpg.mvThemeCat_Core)
            # Checkbox
            dpg.add_theme_color(dpg.mvThemeCol_CheckMark, ACCENT, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_CheckBox, PANEL, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_CheckBoxHovered, (30, 40, 52), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_CheckBoxBorder, BORDER, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_CheckBoxBorderHovered, ACCENT, category=dpg.mvThemeCat_Core)
            # Progress bar
            dpg.add_theme_color(dpg.mvThemeCol_PlotHistogram, ACCENT, category=dpg.mvThemeCat_Core)
            # Header
            dpg.add_theme_color(dpg.mvThemeCol_Header, PANEL, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, (30, 40, 52), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, (36, 48, 62), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderBorder, BORDER, category=dpg.mvThemeCat_Core)
            # Slider
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrab, ACCENT, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrabHovered, ACCENT_HOVER, category=dpg.mvThemeCat_Core)
            # Tooltip
            dpg.add_theme_color(dpg.mvThemeCol_TooltipBg, PANEL, category=dpg.mvThemeCat_Core)

    dpg.bind_theme("moka_dark")


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
            width=860, height=720, min_size=(700, 600),
            resizable=True,
            bg_color=BACKGROUND,
        )
    except Exception as e:
        log_error("create_viewport", e, e.__traceback__)
        log_file.close()
        return

    try:
        with dpg.window(
            tag="main_window",
            width=860, height=720,
            pos=(0, 0),
            no_move=True,
        ):
            dpg.add_text(
                "Moka AI Installer",
                tag="page_title",
                color=ACCENT,
                bold=True,
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

# Needed for platform.system() in hardware scan
import platform