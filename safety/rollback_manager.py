from dataclasses import dataclass
from typing import List, Dict, Optional
import os
import shutil
from datetime import datetime

@dataclass
class Snapshot:
    action_id: str
    file_path: str
    backup_path: str
    created_at: datetime

class RollbackManager:
    def __init__(self, base_path: str = ".safety_snapshots"):
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)
        self._snapshots: Dict[str, List[Snapshot]] = {}

    def create_snapshot(self, action_id: str, file_path: str) -> Optional[Snapshot]:
        if not os.path.exists(file_path):
            return None
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = os.path.basename(file_path)
        backup_path = os.path.join(self.base_path, f"{action_id}_{safe_name}_{timestamp}.bak")
        shutil.copy2(file_path, backup_path)
        snapshot = Snapshot(
            action_id=action_id,
            file_path=file_path,
            backup_path=backup_path,
            created_at=datetime.now()
        )
        if action_id not in self._snapshots:
            self._snapshots[action_id] = []
        self._snapshots[action_id].append(snapshot)
        return snapshot

    def rollback(self, action_id: str) -> bool:
        if action_id not in self._snapshots:
            return False
        snapshots = self._snapshots[action_id]
        for snapshot in reversed(snapshots):
            if os.path.exists(snapshot.backup_path):
                shutil.copy2(snapshot.backup_path, snapshot.file_path)
        self._cleanup(action_id)
        return True

    def _cleanup(self, action_id: str):
        if action_id in self._snapshots:
            for snapshot in self._snapshots[action_id]:
                if os.path.exists(snapshot.backup_path):
                    os.remove(snapshot.backup_path)
            del self._snapshots[action_id]