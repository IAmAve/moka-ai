"""
Conversation Pipeline Module for MOKA AI Core Runtime

Handles the full conversation processing pipeline with:
- Context injection
- Memory injection
- Model routing
- Tagalog-first communication
- Tool routing
- State management
"""

import threading
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

from core_runtime.model_abstraction import ModelAbstraction
from localization import LocalizationService


@dataclass
class ConversationTurn:
    """Represents a single turn in a conversation."""
    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationState:
    """Current state of a conversation."""
    context: Dict[str, Any] = field(default_factory=dict)
    memory_level: str = "short_term"
    mood: str = "neutral"
    language: str = "Tagalog"


class ContextManager:
    """Manages conversation context."""

    def __init__(self):
        self.global_context: Dict[str, Any] = {}
        self.session_context: Dict[str, Any] = {}

    def inject(self, context_data: Dict[str, Any]) -> None:
        """Inject context data into the session."""
        self.session_context.update(context_data)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a context value."""
        if key in self.session_context:
            return self.session_context[key]
        return self.global_context.get(key, default)

    def set_global(self, key: str, value: Any) -> None:
        """Set a global context value."""
        self.global_context[key] = value

    def clear_session(self) -> None:
        """Clear session-specific context."""
        self.session_context.clear()


class MemoryInjector:
    """Injects relevant memory into the conversation context."""

    def __init__(self):
        self.recent_turns: List[ConversationTurn] = []
        self.max_history = 50

    def add_turn(self, turn: ConversationTurn) -> None:
        """Add a conversation turn to history."""
        self.recent_turns.append(turn)
        if len(self.recent_turns) > self.max_history:
            self.recent_turns.pop(0)

    def get_context_for_prompt(self, relevant_turns: int = 10) -> str:
        """Build a context string from recent conversation history."""
        if not self.recent_turns:
            return ""
        turns = self.recent_turns[-relevant_turns:]
        return "\n".join(f"{t.role}: {t.content}" for t in turns)

    def clear(self) -> None:
        """Clear memory history."""
        self.recent_turns.clear()


class StateManager:
    """Manages conversation state transitions."""

    def __init__(self):
        self.state = ConversationState()
        self.state_history: List[ConversationState] = []

    def update(self, **kwargs) -> None:
        """Update the current state."""
        self.state_history.append(self._copy_state(self.state))
        for key, value in kwargs.items():
            if hasattr(self.state, key):
                setattr(self.state, key, value)

    def get_state(self) -> ConversationState:
        """Get a copy of the current state."""
        return self._copy_state(self.state)

    def rollback(self) -> bool:
        """Rollback to previous state."""
        if self.state_history:
            self.state = self.state_history.pop()
            return True
        return False

    def _copy_state(self, state: ConversationState) -> ConversationState:
        return ConversationState(
            context=state.context.copy(),
            memory_level=state.memory_level,
            mood=state.mood,
            language=state.language
        )


class ConversationPipeline(ABC):
    """Abstract conversation processing pipeline."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model_router: Optional[ModelAbstraction] = None
        self.context_manager = ContextManager()
        self.memory_injector = MemoryInjector()
        self.tool_router: List[Any] = []
        self.state_manager = StateManager()
        self.localization = LocalizationService()
        self.conversation_history: List[ConversationTurn] = []

    def process_conversation(self, input_text: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Process a conversation turn end-to-end."""
        if context:
            self.context_manager.inject(context)

        turn = ConversationTurn(role="user", content=input_text)
        self.conversation_history.append(turn)
        self.memory_injector.add_turn(turn)

        memory_context = self.memory_injector.get_context_for_prompt()

        prompt = self._build_prompt(input_text, memory_context)
        response = self._generate_response(prompt)

        response_turn = ConversationTurn(role="assistant", content=response)
        self.conversation_history.append(response_turn)
        self.memory_injector.add_turn(response_turn)

        return response

    def _build_prompt(self, input_text: str, memory_context: str) -> str:
        """Build the full prompt with context and memory."""
        greeting = self.localization.get_phrase("task_begin")
        return f"{greeting}\n\nKontexto:\n{memory_context}\n\nUser: {input_text}"

    def _generate_response(self, prompt: str) -> str:
        """Generate a response using the model."""
        if self.model_router and self.model_router.current_provider:
            return self.model_router.generate_text(prompt)
        return self.localization.get_phrase("waiting_for_input")

    def inject_context(self, context_data: Dict[str, Any]) -> None:
        """Inject context into the conversation."""
        self.context_manager.inject(context_data)
        self.state_manager.update(context=context_data)

    def get_conversation_state(self) -> Dict[str, Any]:
        """Get the current conversation state."""
        state = self.state_manager.get_state()
        return {
            "context": state.context,
            "memory_level": state.memory_level,
            "mood": state.mood,
            "language": state.language,
            "turn_count": len(self.conversation_history),
        }

    def get_conversation_history(self) -> List[ConversationTurn]:
        """Get the full conversation history."""
        return self.conversation_history.copy()

    def set_mood(self, mood: str) -> None:
        """Set the conversation mood."""
        self.state_manager.update(mood=mood)
        self.localization.set_mood(mood)

    def set_language(self, lang: str) -> None:
        """Set the active language."""
        self.state_manager.update(language=lang)
        self.localization.set_language(lang)

    @abstractmethod
    def get_model_routing(self) -> ModelAbstraction:
        """Get model routing capabilities."""
        pass

    @abstractmethod
    def get_tool_routing(self) -> List[Any]:
        """Get tool routing capabilities."""
        pass

    @abstractmethod
    def get_state_management(self) -> StateManager:
        """Get state management capabilities."""
        pass

    @abstractmethod
    def get_tagalog_first(self) -> LocalizationService:
        """Get Tagalog-first interaction capabilities."""
        return self.localization

    @abstractmethod
    def reset(self) -> None:
        """Reset the conversation pipeline."""
        self.conversation_history.clear()
        self.memory_injector.clear()
        self.state_manager = StateManager()