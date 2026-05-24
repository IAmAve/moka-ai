"""Environment Manager for MOKA AI"""
import sys, os
from pathlib import Path
from typing import List

class EnvironmentManager:
    MIN_PYTHON_VERSION = (3, 9)
    def __init__(self): self._errors: List[str] = []
    def validate(self) -> bool:
        self._errors.clear()
        self._check_python_version()
        self._check_required_dirs()
        return len(self._errors) == 0
    def _check_python_version(self) -> None:
        if sys.version_info < self.MIN_PYTHON_VERSION:
            self._errors.append("Python 3.9+ required")
    def _check_required_dirs(self) -> None:
        for d in ["logs", "data"]:
            p = Path(d)
            if not p.exists():
                try: p.mkdir(parents=True, exist_ok=True)
                except OSError as e: self._errors.append(f"Cannot create {d}")
    def get_errors(self) -> List[str]: return list(self._errors)
    def get_env(self, k: str, default: str = "") -> str: return os.environ.get(k, default)