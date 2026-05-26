import unittest
import sys, os, tempfile, shutil, json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core_runtime.workflow_generator import WorkflowGenerator


class TestWorkflowGenerator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp()
        cls.wg = WorkflowGenerator(templates_path=cls.tmpdir, logger=None)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def test_templates_created(self):
        """Default templates are created on first load."""
        for cat in ["portrait", "landscape", "anime", "default"]:
            self.assertIn(cat, self.wg._templates)

    def test_match_template_portrait(self):
        self.assertEqual(self.wg.match_template("Generate a portrait of a samurai"), "portrait")
        self.assertEqual(self.wg.match_template("create a face close-up"), "portrait")

    def test_match_template_landscape(self):
        self.assertEqual(self.wg.match_template("A landscape with mountains"), "landscape")
        self.assertEqual(self.wg.match_template("forest scenery"), "landscape")

    def test_match_template_anime(self):
        self.assertEqual(self.wg.match_template("anime character"), "anime")
        self.assertEqual(self.wg.match_template("manga style art"), "anime")

    def test_match_template_default(self):
        self.assertEqual(self.wg.match_template("random image"), "default")
        self.assertEqual(self.wg.match_template("something completely different"), "default")

    def test_generate_produces_valid_workflow(self):
        wf = self.wg.generate("A cyberpunk city at night", template_category="default")
        self.assertIn("nodes", wf)
        self.assertTrue(self.wg.validate(wf))

    def test_generate_replaces_prompt_placeholder(self):
        wf = self.wg.generate("A beautiful sunset", template_category="default")
        wf_str = json.dumps(wf) if hasattr(json, 'dumps') else str(wf)
        self.assertIn("A beautiful sunset", wf_str)

    def test_validate_rejects_duplicate_ids(self):
        wf = {"nodes": [{"id": 1, "type": "A"}, {"id": 1, "type": "B"}]}
        self.assertFalse(self.wg.validate(wf))

    def test_validate_rejects_missing_nodes(self):
        wf = {"links": []}
        self.assertFalse(self.wg.validate(wf))


if __name__ == "__main__":
    unittest.main()