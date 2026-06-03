#!/usr/bin/env python3
"""Quick test to verify basic module structure"""

import sys
import os

# Try to import key modules to verify structure
modules_to_test = [
    'moka',
    'core.event_bus',
    'core.di_container',
    'core.service_manager',
    'personality.personality_engine',
    'learning.hermes_learning_system',
    'memory.short_term_memory',
    'safety.intent_detector',
    'localization.localization_service',
    'voice.voice_service'
]

print("Testing module imports...")
failed_imports = []

for module_name in modules_to_test:
    try:
        __import__(module_name)
        print(f"✓ {module_name}")
    except Exception as e:
        print(f"✗ {module_name}: {e}")
        failed_imports.append((module_name, str(e)))

if failed_imports:
    print(f"\n{len(failed_imports)} imports failed:")
    for module, error in failed_imports:
        print(f"  - {module}: {error}")
    sys.exit(1)
else:
    print("\nAll core modules imported successfully!")
    sys.exit(0)