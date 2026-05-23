"""Worker Manager for MOKA AI"""
import threading
from typing import Callable, Dict, Any, Optional
from core.task_queue import TaskQueue

class Worker:
    def __init__(self, wid: str, q: TaskQueue, fn: Callable):
        self.worker_id = wid; self.task_queue = q; self.process_fn = fn
        self._thread: Optional[threading.Thread] = None; self._running = False; self._processed = 0
    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
    def stop(self) -> None:
        self._running = False
        if self._thread: self._thread.join(timeout=5)
    def _run(self) -> None:
        while self._running:
            t = self.task_queue.dequeue(timeout=0.5)
            if t:
                try: self.process_fn(t); self.task_queue.complete(t.id)
                except: self.task_queue.fail(t.id)
                finally: self._processed += 1
    def get_stats(self) -> Dict[str, Any]: return {"worker_id": self.worker_id, "processed": self._processed}

class WorkerManager:
    def __init__(self, q: TaskQueue, fn: Callable, max_workers: int = 4):
        self.task_queue = q; self.process_fn = fn; self.max_workers = max_workers
        self._workers: Dict[str, Worker] = {}
    def start(self) -> None:
        for i in range(self.max_workers):
            w = Worker(f"worker-{i}", self.task_queue, self.process_fn); w.start(); self._workers[w.worker_id] = w
    def stop(self) -> None:
        for w in self._workers.values(): w.stop()
        self._workers.clear()
    def get_stats(self) -> Dict[str, Dict[str, Any]]: return {k: w.get_stats() for k, w in self._workers.items()}
    def get_active_count(self) -> int: return sum(1 for w in self._workers.values() if w._thread and w._thread.is_alive())