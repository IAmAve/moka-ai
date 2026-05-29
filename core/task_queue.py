"""
Task Queue for MOKA AI
"""

import queue
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class Task:
    id: str
    payload: Dict[str, Any]
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 0

    def __lt__(self, other: "Task") -> bool:
        return self.id < other.id

class TaskQueue:
    def __init__(self, max_size: int = 0):
        self._q: queue.PriorityQueue = queue.PriorityQueue(maxsize=max_size)
        self._tasks: Dict[str, Task] = {}

    def enqueue(self, task_id: str, payload: Dict[str, Any], priority: int = 0) -> Task:
        task = Task(id=task_id, payload=payload, priority=priority, status=TaskStatus.PENDING)
        self._tasks[task_id] = task
        self._q.put((~priority, task))
        return task

    def dequeue(self, timeout: Optional[float] = None) -> Optional[Task]:
        try:
            _, task = self._q.get(timeout=timeout)
            task.status = TaskStatus.RUNNING
            return task
        except queue.Empty:
            return None

    def complete(self, task_id: str) -> None:
        if task_id in self._tasks:
            self._tasks[task_id].status = TaskStatus.COMPLETED

    def fail(self, task_id: str) -> None:
        if task_id in self._tasks:
            self._tasks[task_id].status = TaskStatus.FAILED

    def get_status(self, task_id: str) -> TaskStatus:
        return self._tasks.get(task_id, Task("", {})).status

    def size(self) -> int:
        return self._q.qsize()