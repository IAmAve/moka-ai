"""MokaAI Flask + SocketIO backend."""

from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import eventlet

eventlet.monkey_patch()

app = Flask(__name__, template_folder="../frontend/templates")
app.config["SECRET_KEY"] = "moka-voice-companion"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

# Agent state
AGENT_STATE = {
    "status": "idle",  # idle | listening | thinking | speaking | error
    "transcript": [],
    "last_message": None,
}


@app.route("/")
def index():
    return render_template("index.html")


@socketio.on("connect")
def handle_connect():
    emit("agent_state", AGENT_STATE)


@socketio.on("panel_change")
def handle_panel_change(data):
    pass  # Acknowledge client panel change


def broadcast_state(state):
    AGENT_STATE.update(state)
    socketio.emit("agent_state", AGENT_STATE)


def broadcast_event(event_type, data):
    socketio.emit("agent_event", {"type": event_type, "data": data})


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5555, debug=False)