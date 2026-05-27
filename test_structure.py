"""
Test script for MOKA AI project structure
"""

import os
import sys

def test_directories():
    """Test that all required directories exist"""
    required_dirs = ["config", "data", "logs", "plugins", "models", "temp"]
    missing = [d for d in required_dirs if not os.path.exists(d)]
    assert not missing, f"Missing directories: {missing}"


def test_files():
    """Test that required files exist"""
    required_files = ["moka.py", "config/config.json"]
    missing = [f for f in required_files if not os.path.exists(f)]
    assert not missing, f"Missing files: {missing}"

if __name__ == "__main__":
    print("Testing MOKA AI project structure...")

    if test_directories() and test_files():
        print("All tests passed!")
    else:
        print("Some tests failed!")
        sys.exit(1)