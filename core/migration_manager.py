"""
Migration Manager for MOKA AI
"""

import json
from pathlib import Path
from typing import Callable, Dict, List, Any, Optional

MigrationFn = Callable[[], bool]
RollbackFn = Callable[[], bool]

class Migration:
    def __init__(self, version: str, description: str, up: MigrationFn, down: RollbackFn):
        self.version = version
        self.description = description
        self.up = up
        self.down = down

class MigrationManager:
    def __init__(self, store_path: str = "data/migrations.json"):
        self.store_path = Path(store_path)
        self._migrations: Dict[str, Migration] = {}
        self._applied: List[str] = self._load_applied()

    def _load_applied(self) -> List[str]:
        if self.store_path.exists():
            try:
                return json.loads(self.store_path.read_text()).get("applied", [])
            except (json.JSONDecodeError, OSError):
                return []
        return []

    def _save_applied(self) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.store_path.write_text(json.dumps({"applied": self._applied}, indent=2))

    def register(self, migrations: List[Migration]) -> None:
        for m in migrations:
            self._migrations[m.version] = m

    def get_pending(self) -> List[Migration]:
        pending = []
        for v, m in sorted(self._migrations.items()):
            if v not in self._applied:
                pending.append(m)
        return pending

    def migrate(self) -> Dict[str, Any]:
        pending = self.get_pending()
        results = {"applied": [], "failed": []}
        for m in pending:
            try:
                ok = m.up()
                if ok:
                    self._applied.append(m.version)
                    results["applied"].append(m.version)
                else:
                    results["failed"].append({"version": m.version, "error": "up() returned False"})
            except Exception as e:
                results["failed"].append({"version": m.version, "error": str(e)})
        self._save_applied()
        return results

    def rollback(self, to_version: str) -> bool:
        if to_version not in self._applied:
            return False
        migrations_to_rollback = [v for v in sorted(self._applied, reverse=True) if v > to_version]
        for v in migrations_to_rollback:
            m = self._migrations.get(v)
            if m is None:
                return False
            try:
                ok = m.down()
                if not ok:
                    return False
                self._applied.remove(v)
            except Exception:
                return False
        self._save_applied()
        return True