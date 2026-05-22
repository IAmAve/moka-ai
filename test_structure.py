"""
Test script for MOKA AI project structure
"""

import os
import sys

def test_directories():
    """Test that all required directories exist"""
    required_dirs = [
        "config",
        "data",
        "logs",
        "plugins",
        "models",
        "temp"
    ]

    missing_dirs = []

    for directory in required_dirs:
        if not os.path.exists(directory):
            missing_dirs.append(directory)

    if missing_dirs:
        print(f"Missing directories: {missing_dirs}")
        return False

    print("All required directories exist")
    return True

def test_files():
    """Test that required files exist"""
    required_files = [
        "moka.py",
        "config/config.json"
    ]

    missing_files = []

    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)

    if missing_files:
        print(f"Missing files: {missing_files}")
        return False

    print("All required files exist")
    return True

if __name__ == "__main__":
    print("Testing MOKA AI project structure...")

    if test_directories() and test_files():
        print("All tests passed!")
    else:
        print("Some tests failed!")
        sys.exit(1)