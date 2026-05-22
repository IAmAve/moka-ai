import unittest
import sys
import os
import tempfile
import shutil
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from safety.rollback_manager import RollbackManager, Snapshot

class TestRollbackManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.manager = RollbackManager(base_path=self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_snapshot(self):
        file_path = os.path.join(self.temp_dir, "test.txt")
        with open(file_path, 'w') as f:
            f.write("original")
        snapshot = self.manager.create_snapshot("action-1", file_path)
        self.assertIsNotNone(snapshot)
        self.assertTrue(os.path.exists(snapshot.backup_path))

    def test_rollback_restores_content(self):
        file_path = os.path.join(self.temp_dir, "test.txt")
        with open(file_path, 'w') as f:
            f.write("original")
        self.manager.create_snapshot("action-1", file_path)
        with open(file_path, 'w') as f:
            f.write("modified")
        self.manager.rollback("action-1")
        with open(file_path, 'r') as f:
            self.assertEqual(f.read(), "original")

    def test_rollback_lifo_order(self):
        file1 = os.path.join(self.temp_dir, "file1.txt")
        file2 = os.path.join(self.temp_dir, "file2.txt")
        with open(file1, 'w') as f: f.write("f1-orig")
        with open(file2, 'w') as f: f.write("f2-orig")
        self.manager.create_snapshot("action-1", file1)
        self.manager.create_snapshot("action-1", file2)
        with open(file1, 'w') as f: f.write("f1-mod")
        with open(file2, 'w') as f: f.write("f2-mod")
        self.manager.rollback("action-1")
        self.assertEqual(open(file1).read(), "f1-orig")
        self.assertEqual(open(file2).read(), "f2-orig")

if __name__ == '__main__':
    unittest.main()