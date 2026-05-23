import unittest, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.task_queue import TaskQueue, TaskStatus

class TestTaskQueue(unittest.TestCase):
    def test_enqueue_dequeue(self):
        q = TaskQueue(max_size=10)
        q.enqueue("job1", {"data": 42})
        task = q.dequeue(timeout=1)
        self.assertEqual(task.id, "job1")
        self.assertEqual(task.payload["data"], 42)

    def test_priority_ordering(self):
        q = TaskQueue(max_size=10)
        q.enqueue("low", {}, priority=1)
        q.enqueue("high", {}, priority=10)
        q.enqueue("medium", {}, priority=5)
        first = q.dequeue(timeout=1)
        self.assertEqual(first.id, "high")

    def test_max_size_blocks(self):
        q = TaskQueue(max_size=2)
        q.enqueue("t1", {})
        q.enqueue("t2", {})
        q.dequeue(timeout=1)
        q.enqueue("t3", {})

    def test_task_statuses(self):
        q = TaskQueue(max_size=10)
        q.enqueue("t1", {})
        task = q.dequeue(timeout=1)
        self.assertEqual(task.status, TaskStatus.RUNNING)
        q.complete("t1")
        self.assertEqual(q.get_status("t1"), TaskStatus.COMPLETED)

if __name__ == "__main__":
    unittest.main()