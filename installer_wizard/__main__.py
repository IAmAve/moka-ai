"""Moka AI Installer — entry point (python -m installer_wizard or PyInstaller)."""
import os, sys

# _internal/ is the parent of installer_wizard/ in the bundled exe,
# and repo root is the parent of installer_wizard/ in the source tree.
# Add both to sys.path so absolute package imports resolve in both contexts.
for _parent in [
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),  # _internal/  or repo/
    os.path.dirname(os.path.abspath(__file__)),                    # installer_wizard/ dir (for sibling .py files)
]:
    if _parent not in sys.path:
        sys.path.insert(0, _parent)

# Set package context so relative imports are resolved by Python
__package__ = "installer_wizard"

from .main import main, create_window

if __name__ == "__main__":
    main()