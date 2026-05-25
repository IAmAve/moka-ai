import os, shutil, subprocess, uuid
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional

class SandboxStatus(Enum):
    PENDING = "pending"; READY = "ready"; RUNNING = "running"; DESTROYED = "destroyed"

class SandboxEnvironment(Enum):
    TEMP = "temp"; TEST = "test"; LIVE = "live"

@dataclass
class Sandbox:
    sandbox_id: str; workflow_id: str; environment: SandboxEnvironment
    worktree_path: str; container_id: Optional[str]; status: SandboxStatus = SandboxStatus.PENDING

class SandboxManager:
    def __init__(self, base_path="d:/tmp/moka_sandboxes", base_branch="main", container_image="python:3.11-slim", logger=None):
        self.base_path = base_path; self.base_branch = base_branch
        self.container_image = container_image
        self._logger = logger
        self._log = logger.info if logger else lambda m: None
        self._sandboxes: Dict[str, Sandbox] = {}
        os.makedirs(base_path, exist_ok=True)

    def create_sandbox(self, workflow_id: str) -> str:
        sandbox_id = str(uuid.uuid4())[:8]
        worktree_path = os.path.join(self.base_path, f"worktree_{sandbox_id}")
        os.makedirs(worktree_path, exist_ok=True)
        try:
            subprocess.run(["git", "clone", "-b", self.base_branch, os.getcwd(), worktree_path], capture_output=True)
        except Exception: pass
        sandbox = Sandbox(sandbox_id=sandbox_id, workflow_id=workflow_id, environment=SandboxEnvironment.TEMP,
                          worktree_path=worktree_path, container_id=None, status=SandboxStatus.READY)
        self._sandboxes[sandbox_id] = sandbox
        self._log(f"Sandbox {sandbox_id} created for workflow {workflow_id}")
        return sandbox_id

    def create_container(self, sandbox_id: str) -> Optional[str]:
        sandbox = self._sandboxes.get(sandbox_id)
        if not sandbox: return None
        try:
            r = subprocess.run(["docker", "run", "-d", "--rm", "-v", f"{sandbox.worktree_path}:/workspace",
                               "-w", "/workspace", self.container_image, "sleep", "infinity"],
                              capture_output=True, text=True)
            sandbox.container_id = r.stdout.strip()
            sandbox.status = SandboxStatus.RUNNING
            return sandbox.container_id
        except: return None

    def _remove_readonly(self, func, path, exc):
        """Handle Windows read-only file removal."""
        import stat
        os.chmod(path, stat.S_IWRITE)
        func(path)

    def destroy_sandbox(self, sandbox_id: str) -> bool:
        sandbox = self._sandboxes.get(sandbox_id)
        if not sandbox: return False
        if sandbox.container_id:
            try: subprocess.run(["docker", "kill", sandbox.container_id], capture_output=True)
            except: pass
        if os.path.isdir(sandbox.worktree_path):
            shutil.rmtree(sandbox.worktree_path, onerror=self._remove_readonly)
        sandbox.status = SandboxStatus.DESTROYED
        del self._sandboxes[sandbox_id]
        return True

    def snapshot_sandbox(self, sandbox_id: str, tag: str = "") -> bool:
        sandbox = self._sandboxes.get(sandbox_id)
        if not sandbox: return False
        try:
            subprocess.run(["git", "-C", sandbox.worktree_path, "add", "-A"], capture_output=True)
            subprocess.run(["git", "-C", sandbox.worktree_path, "commit", "-m", f"Snapshot {tag}" if tag else "Auto snapshot"], capture_output=True)
            return True
        except: return False

    def promote_environment(self, sandbox_id: str) -> SandboxEnvironment:
        sandbox = self._sandboxes.get(sandbox_id)
        if not sandbox: return None
        order = [SandboxEnvironment.TEMP, SandboxEnvironment.TEST, SandboxEnvironment.LIVE]
        idx = order.index(sandbox.environment)
        if idx + 1 < len(order): sandbox.environment = order[idx + 1]
        return sandbox.environment

    def get_sandbox(self, sandbox_id: str) -> Optional[Sandbox]:
        return self._sandboxes.get(sandbox_id)