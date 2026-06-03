"""Tests for frontend/static/js/app.js — Phase 13 rewrite"""
import unittest
import sys, os
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
        self.assertIn("io({", self.content)
        self.assertIn("socket.on('connect'", self.content)
        self.assertIn("socket.on('disconnect'", self.content)

    def test_socketio_event_types_wired(self):
        """All Socket.IO event handlers from Phase 11 spec are present."""
        events = [
            "message",
            "voice_transcript",
            "orb_state",
            "memory_update",
            "skill_update",
            "task_update",
            "resource_update",
            "learning_update",
            "history_events",
        ]
        for evt_type in events:
            search = "socket.on('" + evt_type + "'"
            self.assertIn(search, self.content, f"{evt_type} handler not wired")

    def test_safe_text_defined(self):
        self.assertIn("function safeText", self.content)

    def test_safe_text_uses_dom_approach(self):
        """XSS prevention via document.createElement + textContent."""
        self.assertIn("document.createElement", self.content)
        self.assertIn("textContent", self.content)

    def test_panel_switching(self):
        self.assertIn("function switchPanel", self.content)
        self.assertIn("classList.remove('active')", self.content)
        self.assertIn("classList.add('active')", self.content)

    def test_orb_renderer_factory(self):
        """app.js uses createOrbRenderer factory from orb.js."""
        self.assertIn("createOrbRenderer", self.content)

    def test_setOrbVoiceState(self):
        """State normalization for uppercase→lowercase orb states."""
        self.assertIn("setOrbVoiceState", self.content)

    def test_chat_functions(self):
        self.assertIn("function renderMessages", self.content)
        self.assertIn("function sendChat", self.content)
        # socket.emit('message', ...) — single quotes in JS
        self.assertIn("socket.emit('message'", self.content)

    def test_voice_functions(self):
        self.assertIn("function appendTranscript", self.content)
        self.assertIn("socket.emit('mic_start')", self.content)
        self.assertIn("socket.emit('mic_stop')", self.content)

    def test_history_functions(self):
        self.assertIn("function renderHistory", self.content)
        self.assertIn("historyFilter", self.content)
        self.assertIn("socket.emit('clear_history')", self.content)

    def test_memory_functions(self):
        self.assertIn("function renderMemory", self.content)

    def test_skills_functions(self):
        self.assertIn("function renderSkills", self.content)

    def test_tasks_functions(self):
        self.assertIn("function renderTasks", self.content)
        self.assertIn("socket.emit('task_toggle'", self.content)

    def test_resource_functions(self):
        self.assertIn("function renderResources", self.content)
        self.assertIn("gpu-pct", self.content)
        self.assertIn("ram-pct", self.content)

    def test_learning_functions(self):
        self.assertIn("function renderLearning", self.content)
        self.assertIn("metric-behaviors", self.content)
        self.assertIn("metric-skills", self.content)
        self.assertIn("metric-profiles", self.content)

    def test_boot_dom_ready(self):
        self.assertIn("DOMContentLoaded", self.content)
        self.assertIn("switchPanel('chat')", self.content)

    def test_typing_in_input_enter_key(self):
        self.assertIn("e.key === 'Enter'", self.content)
        self.assertIn("chat-input", self.content)

    def test_export_memory_button(self):
        self.assertIn("socket.emit('export_memory')", self.content)


if __name__ == "__main__":
    unittest.main()