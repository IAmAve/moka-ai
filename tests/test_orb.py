"""Tests for frontend/static/js/orb.js"""
import unittest
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ORB_STATES_PATTERN = re.compile(r'ORB_STATES\s*=\s*\{[^}]+\}')
CANVAS_METHODS = ["draw", "setState", "_triggerWakeBurst", "_startSpeechRings"]


class TestOrbJs(unittest.TestCase):
    def setUp(self):
        self.js_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "frontend", "static", "js", "orb.js"
        )
        with open(self.js_path, "r") as f:
            self.content = f.read()

    def test_orb_js_exists(self):
        self.assertTrue(os.path.exists(self.js_path))

    def test_orb_states_defined(self):
        match = ORB_STATES_PATTERN.search(self.content)
        self.assertTrue(match, "ORB_STATES not found in orb.js")

    def test_all_five_states_present(self):
        for state in ["idle", "listening", "thinking", "speaking", "error"]:
            self.assertIn(state + ":", self.content, f"{state} missing from ORB_STATES")

    def test_orb_state_colors_valid_hex(self):
        hex_color = re.compile(r'"#(?:[0-9a-fA-F]{6})"')
        colors = hex_color.findall(self.content)
        self.assertGreaterEqual(len(colors), 5)

    def test_orb_renderer_class_defined(self):
        self.assertIn("class OrbRenderer", self.content)

    def test_orb_has_canvas_context_setup(self):
        self.assertIn("getContext", self.content)
        self.assertIn("requestAnimationFrame", self.content)

    def test_orbit_dots_defined(self):
        self.assertIn("orbitDots", self.content)

    def test_burst_and_speech_particle_system(self):
        self.assertIn("burstParticles", self.content)
        self.assertIn("speechRings", self.content)

    def test_lighten_helper(self):
        self.assertIn("_lighten", self.content)

    def test_pulse_factor(self):
        self.assertIn("_pulseFactor", self.content)

    def test_wake_burst_triggered_on_listening_transition(self):
        self.assertIn("prev === 'listening'", self.content)


if __name__ == "__main__":
    unittest.main()