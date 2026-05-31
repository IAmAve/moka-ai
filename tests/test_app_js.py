"""Tests for frontend/static/js/app.js"""
import unittest
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestAppJs(unittest.TestCase):
    def setUp(self):
        self.js_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "frontend", "static", "js", "app.js"
        )
        with open(self.js_path, "r") as f:
            self.content = f.read()

    def test_app_js_exists(self):
        self.assertTrue(os.path.exists(self.js_path))

    def test_socket_io_connection(self):
        self.assertIn("io(", self.content)
        self.assertIn('socket.on("connect"', self.content)

    def test_agent_state_handler(self):
        self.assertIn('socket.on("agent_state"', self.content)

    def test_agent_event_handler(self):
        self.assertIn('socket.on("agent_event"', self.content)

    def test_panel_switching_function(self):
        self.assertIn("function switchPanel", self.content)
        self.assertIn("panel.classList.add", self.content)

    def test_orb_renderer_integration(self):
        self.assertIn("createOrbRenderer", self.content)
        self.assertIn("orbVoice.setState", self.content)

    def test_transcript_line_handler(self):
        self.assertIn("function appendTranscript", self.content)
        self.assertIn('transcript-line', self.content)

    def test_mic_toggle_event(self):
        self.assertIn('socket.emit("mic_start")', self.content)
        self.assertIn('socket.emit("mic_stop")', self.content)

    def test_clear_history_handler(self):
        self.assertIn('socket.emit("clear_history")', self.content)

    def test_export_memory_handler(self):
        self.assertIn('socket.emit("export_memory")', self.content)

    def test_resource_bars_update(self):
        self.assertIn("renderResources", self.content)
        self.assertIn("gpu-bar", self.content)

    def test_learning_metrics_update(self):
        self.assertIn("renderLearning", self.content)

    def test_event_log_update(self):
        self.assertIn("renderHistory", self.content)

    def test_initorb_on_dom_ready(self):
        self.assertIn("DOMContentLoaded", self.content)
        self.assertIn("initOrbVoice", self.content)

    def test_skill_list_update(self):
        self.assertIn("renderSkills", self.content)

    def test_task_list_update(self):
        self.assertIn("renderTasks", self.content)

    def test_memory_panels_update(self):
        self.assertIn("renderMemory", self.content)

    def test_conversation_list_update(self):
        self.assertIn("updateConversationList", self.content)

    def test_socketio_event_types_wired(self):
        for evt_type in ["resource_update", "learning_update", "history_events", "skill_update", "task_update", "memory_update", "conversation_list"]:
            self.assertIn(f'"{evt_type}"', self.content, f"{evt_type} event type not wired")

    def test_safe_text_defined(self):
        self.assertIn("function safeText", self.content)

    def test_safe_text_uses_dom_approach(self):
        self.assertIn("document.createElement", self.content)
        self.assertIn("textContent", self.content)


if __name__ == "__main__":
    unittest.main()