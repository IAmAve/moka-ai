import unittest
import sys
import os
import tempfile
import shutil
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.skill_memory import SkillMemory


class TestSkillMemory(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.storage_file = os.path.join(self.temp_dir, "skill_test.json")
        self.logs = []
        self.logger = type("L", (), {"info": lambda s, m: self.logs.append(m)})()
        self.memory = SkillMemory(storage_file=self.storage_file, logger=self.logger)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_store_and_retrieve_skill(self):
        result = self.memory.store_skill("python programming", {"level": "expert"}, 0.9)
        self.assertTrue(result)
        retrieved = self.memory.retrieve_skill("python programming")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["proficiency"], 0.9)
        self.assertEqual(retrieved["data"]["level"], "expert")

    def test_update_proficiency(self):
        self.memory.store_skill("test-skill", {}, 0.5)
        result = self.memory.update_proficiency("test-skill", 0.8)
        self.assertTrue(result)
        retrieved = self.memory.retrieve_skill("test-skill")
        self.assertEqual(retrieved["proficiency"], 0.8)

    def test_update_proficiency_nonexistent_returns_false(self):
        result = self.memory.update_proficiency("does-not-exist", 1.0)
        self.assertFalse(result)

    def test_increment_usage(self):
        self.memory.store_skill("test-skill", {}, 0.5)
        self.memory.increment_usage("test-skill")
        self.memory.increment_usage("test-skill")
        retrieved = self.memory.retrieve_skill("test-skill")
        self.assertEqual(retrieved["usage_count"], 2)

    def test_list_skills_default(self):
        self.memory.store_skill("skill-a", {}, 0.3)
        self.memory.store_skill("skill-b", {}, 0.7)
        self.memory.store_skill("skill-c", {}, 0.9)
        skills = self.memory.list_skills()
        self.assertEqual(len(skills), 3)

    def test_list_skills_min_proficiency(self):
        self.memory.store_skill("skill-a", {}, 0.3)
        self.memory.store_skill("skill-b", {}, 0.7)
        self.memory.store_skill("skill-c", {}, 0.9)
        skills = self.memory.list_skills(min_proficiency=0.7)
        self.assertEqual(sorted(skills), ["skill-b", "skill-c"])

    def test_retrieve_nonexistent_returns_none(self):
        result = self.memory.retrieve_skill("does-not-exist")
        self.assertIsNone(result)

    def test_clear_all(self):
        self.memory.store_skill("skill-a", {}, 0.5)
        self.memory.store_skill("skill-b", {}, 0.6)
        self.memory.clear_all()
        self.assertEqual(self.memory.list_skills(), [])


if __name__ == "__main__":
    unittest.main()