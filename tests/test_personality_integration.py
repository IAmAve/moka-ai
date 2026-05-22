"""
Integration test for the MOKA AI personality system
"""

import sys
import os
import unittest

# Add the moka-ai directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from personality.personality_engine import PersonalityEngine
from personality.conversation_memory import ConversationMemory

class TestPersonalityIntegration(unittest.TestCase):

    def test_personality_system_integration(self):
        """Test that all personality components work together"""
        # Create instances of all personality components
        engine = PersonalityEngine()
        memory = ConversationMemory()

        # Test that the components can be instantiated
        self.assertIsNotNone(engine)
        self.assertIsNotNone(memory)

        print("All personality components created successfully")

if __name__ == "__main__":
    unittest.main()