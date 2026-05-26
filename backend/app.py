"""MokaAI Flask + SocketIO backend."""

from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from pathlib import Path
import eventlet
import threading
import time
import random

eventlet.monkey_patch()

app = Flask(__name__)
app.config["SECRET_KEY"] = "moka-voice-companion"

# Serve frontend files from frontend/ directory
BASE = Path(__file__).parent.parent
app.template_folder = str(BASE / "frontend" / "templates")
app.static_folder = str(BASE / "frontend" / "static")
app.static_url_path = "/static"

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

# Agent state
AGENT_STATE = {
    "status": "idle",  # idle | listening | thinking | speaking | error
    "transcript": [],
    "last_message": None,
}

# Per-socket transcript log (for clear_history)
_transcript_log = []  # [{speaker, text, ts}]


@app.route("/")
def index():
    return render_template("index.html")


@socketio.on("connect")
def handle_connect():
    emit("agent_state", AGENT_STATE)


def broadcast_state(state):
    AGENT_STATE.update(state)
    socketio.emit("agent_state", AGENT_STATE)


def broadcast_event(event_type, data):
    socketio.emit("agent_event", {"type": event_type, "data": data})


# ─── Mock broadcast loop for development ────────────────────────────────

def _mock_loop():
    """Send mock event data to all connected clients for development."""
    while True:
        eventlet.sleep(8)
        statuses = ["idle", "thinking", "speaking", "idle"]
        broadcast_state({"status": random.choice(statuses)})
        broadcast_event("event_log", {
            "ts": time.time(),
            "type": random.choice(["chat", "skill", "task", "system"]),
            "description": random.choice([
                "Session active", "Skills reloaded", "Task completed", "Memory synced"
            ]),
        })
        # Mock resource data
        broadcast_event("resource_update", {
            "gpu": random.randint(10, 85),
            "ram": random.randint(30, 70),
        })
        # Mock learning metrics
        broadcast_event("learning_metrics", {
            "behaviors": random.randint(0, 20),
            "skills": random.randint(0, 8),
            "profiles": random.randint(0, 3),
            "confidence": [
                {"category": "code", "score": random.uniform(0.6, 0.95)},
                {"category": "creative", "score": random.uniform(0.5, 0.9)},
                {"category": "analysis", "score": random.uniform(0.7, 0.98)},
            ],
        })
        # Mock skill list
        broadcast_event("skill_update", [
            {"name": "Write Code", "status": "approved"},
            {"name": "Debug Issue", "status": "running"},
            {"name": "Refactor Module", "status": "draft"},
        ])
        # Mock task list
        broadcast_event("task_update", [
            {"name": "Scan workspace", "status": "done", "description": "Scan workspace for changes"},
            {"name": "Build index", "status": "running", "description": "Building search index"},
            {"name": "Sync memory", "status": "pending", "description": "Sync short-term to long-term memory"},
        ])
        # Mock memory panels
        broadcast_event("memory_update", {
            "shortTerm": [
                {"content": "User asked about Python async patterns"},
                {"content": "Last conversation: debugging workflow generation"},
            ],
            "longTerm": [
                {"content": "User prefers detailed explanations"},
                {"content": "Large projects go in ~/dev/"},
            ],
        })
        # Mock conversation list
        broadcast_event("conversation_list", [
            {"date": "Today", "duration": "4m", "preview": "How do I structure an async pipeline in Python?"},
            {"date": "Yesterday", "duration": "12m", "preview": "Help me refactor the approval gate module"},
        ])


# ─── SocketIO event handlers ──────────────────────────────────────────────

@socketio.on("mic_toggle")
def handle_mic_toggle():
    """Simulate a voice interaction cycle."""
    broadcast_state({"status": "listening"})
    eventlet.sleep(1.5)
    broadcast_state({"status": "thinking"})
    user_text = "How do I structure an async pipeline?"
    moka_text = "Use asyncio.Queue with a worker coroutine pattern, connecting producers to consumers via await queue.put() and await queue.get()."
    _transcript_log.append({"speaker": "user", "text": user_text, "ts": time.time()})
    _transcript_log.append({"speaker": "moka", "text": moka_text, "ts": time.time()})
    broadcast_state({"transcript": _transcript_log[-4:]})
    broadcast_event("transcript", {"speaker": "user", "text": user_text})
    eventlet.sleep(0.5)
    broadcast_state({"status": "speaking"})
    broadcast_event("transcript", {"speaker": "moka", "text": moka_text})
    eventlet.sleep(2)
    broadcast_state({"status": "idle"})


@socketio.on("panel_change")
def handle_panel_change(data):
    pass  # Acknowledge client panel change


@socketio.on("clear_history")
def handle_clear_history():
    global _transcript_log
    _transcript_log = []
    AGENT_STATE["transcript"] = []
    emit("agent_state", AGENT_STATE)


@socketio.on("export_memory")
def handle_export_memory():
    emit("agent_event", {
        "type": "memory_export",
        "data": {"url": "/api/memory/export"},
    })


# Start mock broadcast in background thread
_mock_t = threading.Thread(target=_mock_loop, daemon=True)
_mock_t.start()


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5555, debug=False)