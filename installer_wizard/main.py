# installer_wizard/main.py
"""Moka AI Installer — PyWebView entry point."""

import os
import sys
import webview

# Enable relative imports inside the installer_wizard package
# (required when run as a top-level script by PyInstaller)
__package__ = "installer_wizard"

from .api import WizardAPI


def create_window():
    # Get the directory this file lives in
    base_dir = os.path.dirname(os.path.abspath(__file__))
    index_path = os.path.join(base_dir, "index.html")

    # Expose WizardAPI to JS window.pywebview.api.*
    api = WizardAPI.get_instance()

    return webview.create_window(
        title="Moka AI Setup",
        url=index_path,
        width=780,
        height=820,
        min_size=(720, 640),
        resizable=True,
        js_api=api,
        text_select=False,
        frameless=True,
        easy_drag=True,
    )


def main():
    # Set high DPI awareness on Windows
    if sys.platform == "win32":
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass

    window = create_window()
    api = WizardAPI.get_instance()
    api._window = window
    debug = os.environ.get("MOKA_DEBUG", "0") == "1"
    webview.start(debug=debug)
    # After window closes, Python exits cleanly
    sys.exit(0)


if __name__ == "__main__":
    main()