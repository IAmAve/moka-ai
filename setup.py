"""
Setup script for MOKA AI
"""

import os
import sys
from setuptools import setup

def setup_moka():
    """Run first-run setup tasks (create directories)."""
    print("Setting up MOKA AI...")

    # Create necessary directories
    directories = [
        "config",
        "data",
        "logs",
        "plugins",
        "models",
        "temp"
    ]

    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"Created directory: {directory}")

    print("MOKA AI setup completed")

# __main__ path: run first-run setup only (no pip install)
if __name__ == "__main__":
    import argparse
    # When called as a script with no pip args, run setup tasks
    if len(sys.argv) == 1 or (len(sys.argv) == 2 and sys.argv[1] == "setup"):
        setup_moka()
    else:
        # Otherwise let setup() handle the call (pip install -e ., etc.)
        setup()

if __name__ != "__main__" or "setuptools" in sys.modules:
    # When imported by pip/setuptools build backend, always run setup()
    setup(packages=["core", "core_runtime", "personality", "learning",
                   "memory", "plugins", "safety", "voice", "localization"])