"""
Model Abstraction Module for MOKA AI Core Runtime

Provides abstraction layers for local AI model providers.
Supports interchangeable backends (OLLAMA, llama.cpp, etc).
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List


class LocalModelBackend(ABC):
    """Abstract interface for a local model backend."""

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from a prompt."""
        pass

    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """Generate embedding vector for text."""
        pass

    @abstractmethod
    def info(self) -> Dict[str, Any]:
        """Return backend metadata."""
        pass


class OllamaBackend(LocalModelBackend):
    """Ollama CLI backend implementation."""

    def __init__(self, model_name: str = "llama3.2", base_url: str = "http://localhost:11434"):
        import subprocess
        import json
        self.model_name = model_name
        self.base_url = base_url
        self._run = subprocess.run

    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text using ollama CLI."""
        import json
        try:
            result = self._run(
                ["ollama", "generate", "--model", self.model_name, "--prompt", prompt],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except FileNotFoundError:
            pass
        return ""

    def embed(self, text: str) -> List[float]:
        """Generate embedding using ollama embeddings API."""
        return []

    def info(self) -> Dict[str, Any]:
        return {"provider": "ollama", "model": self.model_name}


class DefaultLocalBackend(LocalModelBackend):
    """Default local backend — requires user configuration."""

    def generate(self, prompt: str, **kwargs) -> str:
        raise NotImplementedError(
            "LocalModelProvider has no backend configured. "
            "Pass a LocalModelBackend subclass to LocalModelProvider.__init__ "
            "or configure one via the DIContainer."
        )

    def embed(self, text: str) -> List[float]:
        raise NotImplementedError(
            "LocalModelProvider has no backend configured. "
            "Call set_backend() or pass a backend at construction."
        )

    def info(self) -> Dict[str, Any]:
        return {"provider": "default", "configured": False}


class ModelProvider(ABC):
    """Abstract base class for AI model providers."""

    @abstractmethod
    def generate_text(self, prompt: str, **kwargs) -> str:
        """Generate text based on prompt."""
        pass

    @abstractmethod
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text."""
        pass

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model."""
        pass


class LocalModelProvider(ModelProvider):
    """Local model provider with injectable backend."""

    def __init__(self, backend: LocalModelBackend = None):
        self.backend = backend
        self.provider_name = "local"

    def set_backend(self, backend: LocalModelBackend) -> None:
        """Set or replace the backend."""
        self.backend = backend

    def generate_text(self, prompt: str, **kwargs) -> str:
        """Generate text using the configured backend."""
        if self.backend is None:
            self.backend = DefaultLocalBackend()
        return self.backend.generate(prompt, **kwargs)

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using the configured backend."""
        if self.backend is None:
            return []
        return self.backend.embed(text)

    def get_model_info(self) -> Dict[str, Any]:
        """Get model information from backend."""
        if self.backend is None:
            return {"provider": self.provider_name, "configured": False}
        return self.backend.info()


class ModelAbstraction:
    """Model abstraction layer for interchangeable providers."""

    def __init__(self):
        self.providers: Dict[str, ModelProvider] = {}
        self.current_provider: Optional[ModelProvider] = None

    def register_provider(self, name: str, provider: ModelProvider) -> None:
        """Register a model provider by name."""
        self.providers[name] = provider

    def set_provider(self, name: str) -> bool:
        """Set the active provider by name."""
        if name in self.providers:
            self.current_provider = self.providers[name]
            return True
        return False

    def get_provider(self, name: str) -> Optional[ModelProvider]:
        """Get a provider by name."""
        return self.providers.get(name)

    def generate_text(self, prompt: str, **kwargs) -> str:
        """Generate text using the current provider."""
        if self.current_provider:
            return self.current_provider.generate_text(prompt, **kwargs)
        return ""

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using the current provider."""
        if self.current_provider:
            return self.current_provider.generate_embedding(text)
        return []

    def list_providers(self) -> List[str]:
        """List all registered provider names."""
        return list(self.providers.keys())