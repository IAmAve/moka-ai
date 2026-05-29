"""
Conversation Memory Module for MOKA AI Personality System
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json


@dataclass
class ConversationTurn:
    """Represents a single turn in a conversation"""
    role: str
    content: str
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


class ConversationMemory:
    """Manages conversation memory for MOKA AI personality system"""

    def __init__(self, logger=None):
        self._logger = logger
        self._log = logger.info if logger else lambda m: None
        self.conversation_history: List[ConversationTurn] = []
        self.context_memory: Dict[str, Any] = {}
        self.session_context: Dict[str, Any] = {}
        self.max_history_length = 100
        self.max_context_size = 1000

    def add_conversation_turn(self, role: str, content: str, metadata: Dict[str, Any] = None):
        """Add a conversation turn to memory"""
        if metadata is None:
            metadata = {}

        turn = ConversationTurn(
            role=role,
            content=content,
            timestamp=datetime.now(),
            metadata=metadata,
        )

        self.conversation_history.append(turn)

        if len(self.conversation_history) > self.max_history_length:
            self.conversation_history = self.conversation_history[-self.max_history_length :]

        self._log(f"Added {role} turn to conversation history")
        return len(self.conversation_history)

    def get_conversation_context(self, limit: int = 10) -> List[ConversationTurn]:
        """Get recent conversation context"""
        return self.conversation_history[-limit:] if self.conversation_history else []

    def get_context_summary(self) -> Dict[str, Any]:
        """Get a summary of conversation context"""
        return {
            "history_length": len(self.conversation_history),
            "session_context": self.session_context,
            "last_interaction": (
                self.conversation_history[-1].timestamp if self.conversation_history else None
            ),
        }

    def update_session_context(self, key: str, value: Any):
        """Update session context with new information"""
        self.session_context[key] = value

    def get_session_context(self, key: str) -> Any:
        """Get session context value"""
        return self.session_context.get(key)

    def clear_conversation_history(self):
        """Clear conversation history"""
        self.conversation_history.clear()
        self._log("Cleared conversation history")

    def save_conversation_state(self, filepath: str):
        """Save conversation state to file"""
        state = {
            "conversation_history": [
                {
                    "role": turn.role,
                    "content": turn.content,
                    "timestamp": turn.timestamp.isoformat(),
                    "metadata": turn.metadata,
                }
                for turn in self.conversation_history
            ],
            "session_context": self.session_context,
        }

        try:
            with open(filepath, "w") as f:
                json.dump(state, f, default=str)
            self._log(f"Saved conversation state to {filepath}")
        except Exception as e:
            if self._logger:
                self._logger.error(f"Failed to save conversation state: {e}")

    def load_conversation_state(self, filepath: str):
        """Load conversation state from file"""
        try:
            with open(filepath, "r") as f:
                state = json.load(f)

            self.conversation_history = [
                ConversationTurn(
                    role=item["role"],
                    content=item["content"],
                    timestamp=datetime.fromisoformat(item["timestamp"]),
                    metadata=item["metadata"],
                )
                for item in state.get("conversation_history", [])
            ]

            self.session_context = state.get("session_context", {})
            self._log(f"Loaded conversation state from {filepath}")
            return True
        except Exception as e:
            if self._logger:
                self._logger.error(f"Failed to load conversation state: {e}")
            return False

    def get_conversation_turns(self, user_id: str = None) -> List[ConversationTurn]:
        """Get conversation turns, optionally filtered by user"""
        if user_id:
            return [turn for turn in self.conversation_history if turn.metadata.get("user_id") == user_id]
        return self.conversation_history

    def get_memory_context(self, context_type: str = "recent", limit: int = 5) -> List[Dict[str, Any]]:
        """Get memory context for personality engine"""
        if context_type == "recent":
            return self.conversation_history[-limit:] if self.conversation_history else []
        elif context_type == "relevant":
            return self.conversation_history[-limit:] if self.conversation_history else []
        else:
            return []