"""
Test file for MOKA AI Personality System
"""

import unittest
from personality.conversation_memory import ConversationMemory
from personality.personality_engine import PersonalityEngine

class TestPersonalitySystem(unittest.TestCase):

    def test_conversation_memory_creation(self):
        """Test that conversation memory can be created"""
        memory = ConversationMemory()
        self.assertIsNotNone(memory)

    def test_personality_engine_creation(self):
        """Test that personality engine can be created"""
        engine = PersonalityEngine()
        self.assertIsNotNone(engine)

if __name__ == "__main__":
    unittest.main()