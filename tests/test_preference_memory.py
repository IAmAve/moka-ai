import unittest
import sys
import os
import tempfile
import shutil
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.preference_memory import PreferenceMemory


class TestPreferenceMemory(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.storage_file = os.path.join(self.temp_dir, "pref_test.json")
        self.logs = []
        self.logger = type("L", (), {"info": lambda s, m: self.logs.append(m)})()
        self.memory = PreferenceMemory(storage_file=self.storage_file, logger=self.logger)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_store_and_retrievePreference(self):
        result = self.memory.store_preference("language", "Tagalog")
        self.assertTrue(result)
        value = self.memory.retrieve_preference("language")
        self.assertEqual(value, "Tagalog")

    def test_retrieve_nonexistent_returns_default(self):
        value = self.memory.retrieve_preference("missing", default="en")
        self.assertEqual(value, "en")

    def test_retrieve_nonexistent_no_default_returns_none(self):
        value = self.memory.retrieve_preference("missing")
        self.assertIsNone(value)

    def test_delete_preference(self):
        self.memory.store_preference("key", "val")
        result = self.memory.delete_preference("key")
        self.assertTrue(result)
        self.assertIsNone(self.memory.retrieve_preference("key"))

    def test_delete_nonexistent_returns_false(self):
        result = self.memory.delete_preference("does-not-exist")
        self.assertFalse(result)

    def test_get_all_preferences(self):
        self.memory.store_preference("lang", "Tagalog")
        self.memory.store_preference("theme", "dark")
        prefs = self.memory.get_all_preferences()
        self.assertEqual(prefs["lang"], "Tagalog")
        self.assertEqual(prefs["theme"], "dark")

    def test_set_defaults_only_sets_missing(self):
        self.memory.store_preference("existing", "keep")
        defaults = {"existing": "override", "new": "defaulted"}
        self.memory.set_defaults(defaults)
        self.assertEqual(self.memory.retrieve_preference("existing"), "keep")
        self.assertEqual(self.memory.retrieve_preference("new"), "defaulted")

    def test_set_defaults_empty(self):
        result = self.memory.set_defaults({})
        self.assertTrue(result)
        self.assertEqual(self.memory.get_all_preferences(), {})

    def test_clear_all(self):
        self.memory.store_preference("key1", "val1")
        self.memory.store_preference("key2", "val2")
        self.memory.clear_all()
        self.assertEqual(self.memory.get_all_preferences(), {})


if __name__ == "__main__":
    unittest.main()