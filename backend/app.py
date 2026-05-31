"""
Backend Flask/SocketIO application for Moka AI
This provides the webSocket endpoint for frontend communication
"""
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import json
from datetime import datetime

# Initialize Flask app
app = Flask(__name__, template_folder='../frontend/templates')
app.config['SECRET_KEY'] = 'moka-ai-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global agent state that tests expect
AGENT_STATE = {
    "status": "idle",
    "transcript": "",
    "last_message": ""
}

def broadcast_state(state_data):
    """Broadcast state update to all connected clients"""
    global AGENT_STATE
    AGENT_STATE.update(state_data)
    socketio.emit('agent_state', AGENT_STATE)

def broadcast_event(event_type, data):
    """Broadcast a custom event to all connected clients"""
    socketio.emit(event_type, data)

# Socket.IO event handlers
@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('agent_state', AGENT_STATE)

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('mic_start')
def handle_mic_start():
    print('Mic start requested')
    broadcast_state({"status": "listening"})

@socketio.on('mic_stop')
def handle_mic_stop():
    print('Mic stop requested')
    broadcast_state({"status": "thinking"})

@socketio.on('clear_history')
def handle_clear_history():
    print('Clear history requested')
    # In a real app, this would clear chat history
    broadcast_event('history_cleared', {"timestamp": datetime.now().isoformat()})

@socketio.on('export_memory')
def handle_export_memory():
    print('Export memory requested')
    # In a real app, this would export memory data
    broadcast_event('memory_exported', {"timestamp": datetime.now().isoformat()})

@socketio.on('task_toggle')
def handle_task_toggle(data):
    print(f'Task toggle requested: {data}')
    broadcast_event('task_toggled', data)



# Socket.IO event handlers for testing
@socketio.on('mic_toggle')
def handle_mic_toggle():
    print('Mic toggle requested')
    # Toggle between listening and thinking states
    if AGENT_STATE.get("status") == "listening":
        broadcast_state({"status": "thinking"})
    else:
        broadcast_state({"status": "listening"})

@socketio.on('clear_history')
def handle_clear_history():
    print('Clear history requested')
    # In a real app, this would clear chat history
    broadcast_event('history_cleared', {"timestamp": datetime.now().isoformat()})

@socketio.on('export_memory')
def handle_export_memory():
    print('Export memory requested')
    # In a real app, this would export memory data
    broadcast_event('memory_exported', {"timestamp": datetime.now().isoformat()})

# Flask routes
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
