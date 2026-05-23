import unittest, sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.task_queue import TaskQueue
from core.worker_manager import WorkerManager

class TestWM(unittest.TestCase):
    def test_processes_task(self):
        r = []
        def p(t): r.append(t.payload["v"])
        q = TaskQueue(10); wm = WorkerManager(q, p, 1); wm.start(); q.enqueue("a", {"v": 1}); time.sleep(0.5)
        self.assertEqual(r, [1]); wm.stop()
    def test_multiple_workers(self):
        r = []
        def p(t): r.append(t.payload["v"])
        q = TaskQueue(10); wm = WorkerManager(q, p, 2); wm.start()
        for i in range(4): q.enqueue(f"t{i}", {"v": i})
        time.sleep(1); self.assertEqual(len(r), 4); wm.stop()

if __name__ == "__main__": unittest.main()