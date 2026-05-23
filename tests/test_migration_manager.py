import unittest, sys, os, tempfile, shutil
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.migration_manager import MigrationManager, Migration

class TestMigrationManager(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = os.path.join(self.tmpdir, "migrations.json")
        self.mm = MigrationManager(store_path=self.store)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_register_and_get_pending(self):
        run_order = []
        m1 = Migration("1.0", "first", lambda: (run_order.append("up1"), True), lambda: (run_order.append("down1"), True))
        m2 = Migration("2.0", "second", lambda: (run_order.append("up2"), True), lambda: (run_order.append("down2"), True))
        self.mm.register([m1, m2])
        pending = self.mm.get_pending()
        self.assertEqual(len(pending), 2)

    def test_migrate_applies_all(self):
        run_order = []
        m1 = Migration("1.0", "a", lambda: (run_order.append("up1"), True), lambda: True)
        m2 = Migration("2.0", "b", lambda: (run_order.append("up2"), True), lambda: True)
        self.mm.register([m1, m2])
        result = self.mm.migrate()
        self.assertEqual(len(result["applied"]), 2)
        self.assertEqual(run_order, ["up1", "up2"])

    def test_rollback_reverts(self):
        run_order = []
        m1 = Migration("1.0", "a", lambda: (run_order.append("up1"), True), lambda: (run_order.append("down1"), True))
        m2 = Migration("2.0", "b", lambda: (run_order.append("up2"), True), lambda: (run_order.append("down2"), True))
        self.mm.register([m1, m2])
        self.mm.migrate()
        ok = self.mm.rollback("1.0")
        self.assertTrue(ok)
        self.assertEqual(run_order, ["up1", "up2", "down2"])

if __name__ == "__main__":
    unittest.main()