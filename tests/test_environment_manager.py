import unittest, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.environment_manager import EnvironmentManager

class TestEM(unittest.TestCase):
    def test_validate_passes(self):
        self.assertTrue(EnvironmentManager().validate())
    def test_validate_fails_old_python(self):
        em = EnvironmentManager()
        em.MIN_PYTHON_VERSION = (99, 0)
        self.assertFalse(em.validate())
        self.assertGreater(len(em.get_errors()), 0)
    def test_get_env_default(self): self.assertEqual(EnvironmentManager().get_env("X_Y_Z", "d"), "d")
    def test_get_env_value(self):
        os.environ["MOKA_TST"] = "val"
        self.assertEqual(EnvironmentManager().get_env("MOKA_TST", "d"), "val")
        del os.environ["MOKA_TST"]

if __name__ == "__main__": unittest.main()