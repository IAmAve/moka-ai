"""
Setup script for MOKA AI
"""

import os
import sys

def setup_moka():
    """Setup MOKA AI project"""
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

if __name__ == "__main__":
    setup_moka()