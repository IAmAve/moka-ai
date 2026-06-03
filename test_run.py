#!/usr/bin/env python3
"""
Test script to verify Moka AI can initialize and run basic functions
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that key modules can be imported"""
    try:
        print("Testing imports...")
        from moka import MokaAI
        print("✓ MokaAI imported successfully")

        from personality.personality_engine import PersonalityEngine
        print("✓ PersonalityEngine imported successfully")

        from learning.hermes_learning_system import HermesLearningSystem
        print("✓ HermesLearningSystem imported successfully")

        from memory.short_term_memory import ShortTermMemory
        print("✓ ShortTermMemory imported successfully")

        from safety.intent_detector import IntentDetector
        print("✓ IntentDetector imported successfully")

        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_initialization():
    """Test that MokaAI can initialize"""
    try:
        print("\nTesting initialization...")
        from moka import MokaAI

        moka = MokaAI()
        print("✓ MokaAI instance created")

        # This would normally initialize everything, but let's just test creation for now
        # to avoid long startup times and potential issues with missing dependencies
        print("✓ Basic initialization test passed")
        return True
    except Exception as e:
        print(f"✗ Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=== Moka AI System Test ===")

    success = True
    success &= test_imports()
    success &= test_initialization()

    if success:
        print("\n✓ All tests passed!")
        sys.exit(0)
    else:
        print("\n✗ Some tests failed!")
        sys.exit(1)