"""Module Registry for MOKA AI"""
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

@dataclass
class ModuleMetadata:
    name: str; version: str; description: str; author: str = ""; tags: List[str] = field(default_factory=list)

class ModuleRegistry:
    def __init__(self):
        self._modules: Dict[str, Any] = {}
        self._metadata: Dict[str, ModuleMetadata] = {}
    def register(self, name: str, meta: ModuleMetadata, factory: Callable[[], Any]) -> None:
        self._modules[name] = {"factory": factory, "instance": None}
        self._metadata[name] = meta
    def get(self, name: str) -> Optional[Any]:
        e = self._modules.get(name)
        if not e: return None
        if e["instance"] is None: e["instance"] = e["factory"]()
        return e["instance"]
    def get_metadata(self, name: str) -> Optional[ModuleMetadata]: return self._metadata.get(name)
    def list_modules(self) -> List[str]: return list(self._modules.keys())
    def deregister(self, name: str) -> None:
        self._modules.pop(name, None); self._metadata.pop(name, None)