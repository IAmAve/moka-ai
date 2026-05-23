"""
Version Manager for MOKA AI
"""

import re
from pathlib import Path
from typing import Callable, List

class Version:
    def __init__(self, major_or_str, minor=None, patch=None, prerelease=None):
        # Handle Version("1.2.3") calls
        if isinstance(major_or_str, str):
            m = re.match(r"(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9]+))?", major_or_str)
            if not m:
                raise ValueError(f"Invalid: {major_or_str}")
            self.major = int(m[1])
            self.minor = int(m[2])
            self.patch = int(m[3])
            self.prerelease = m[4] or ""
        else:
            self.major = major_or_str
            self.minor = minor
            self.patch = patch
            self.prerelease = prerelease or ""

    def __str__(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"
        return base + (f"-{self.prerelease}" if self.prerelease else "")

    def __lt__(self, other: "Version") -> bool:
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

    def __eq__(self, other) -> bool:
        return isinstance(other, Version) and (self.major, self.minor, self.patch) == (other.major, other.minor, other.patch)

    @classmethod
    def parse(cls, s: str) -> "Version":
        return cls(s)


class VersionManager:
    def __init__(self, version_file: str = "config/version.txt"):
        self.version_file = Path(version_file)
        self._current_version = self._read_version()
        self._upgrade_hooks: List[Callable[[], None]] = []

    def _read_version(self) -> Version:
        if self.version_file.exists():
            return Version.parse(self.version_file.read_text().strip())
        return Version(1, 0, 0)

    def get_current_version(self) -> Version:
        return self._current_version

    def set_version(self, version: Version) -> None:
        self._current_version = version
        self.version_file.parent.mkdir(parents=True, exist_ok=True)
        self.version_file.write_text(str(version))

    def needs_upgrade(self, from_version: Version) -> bool:
        return self._current_version > from_version

    def register_upgrade_hook(self, hook: Callable[[], None]) -> None:
        self._upgrade_hooks.append(hook)

    def run_upgrade(self, from_version: Version) -> None:
        for hook in self._upgrade_hooks:
            hook()
        self.set_version(self._current_version)