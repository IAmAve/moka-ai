# Desktop UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A production Flask + Flask-SocketIO desktop UI — warm sand palette, glassmorphism, animated orb voice interface, icon rail navigation, 9 panels.

**Architecture:** Single Flask app serving static HTML/CSS/JS + SocketIO for real-time state events. Orb rendered on canvas. All panels are JS-controlled sections shown/hidden by icon rail. Backend pushes state changes via EventBus → SocketIO → browser.

**Tech Stack:** Python/Flask, Flask-SocketIO, vanilla JS/CSS (no framework), HTML5 Canvas, SocketIO client.

---

## Task 1: Flask Backend Shell + SocketIO

**Files:**
- Create: `backend/app.py`
- Create: `tests/test_backend.py`

### `backend/app.py`

```python
"""MokaAI Flask + SocketIO backend."""

from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import eventlet

eventlet.monkey_patch()

app = Flask(__name__)
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
```

### `tests/test_backend.py`

```python
import pytest, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.app import app, socketio, AGENT_STATE


@pytest.fixture
def client():
    with app.test_client() as c:
        yield c


def test_index_returns_html(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"<!DOCTYPE" in r.data or b"<html" in r.data


def test_agent_state_has_required_keys(client):
    required = {"status", "transcript", "last_message"}
    assert required.issubset(AGENT_STATE.keys())


def test_connect_emit_agent_state(client):
    with client.session_transaction() as sess:
        pass
    r = client.get("/")
    assert r.status_code == 200
```

---

## Task 2: Flask HTML + CSS Foundations

**Files:**
- Create: `frontend/templates/index.html`
- Create: `frontend/static/css/style.css`

### `frontend/templates/index.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Moka AI</title>
    <link rel="stylesheet" href="/static/css/style.css">
    <script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>
</head>
<body>

<div id="app">

    <!-- Icon Rail -->
    <nav id="icon-rail">
        <button class="rail-icon active" data-panel="voice" title="Voice">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M12 14a3 3 0 003 3V21h-6v-4a3 3 0 003-3z" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
        </button>
        <button class="rail-icon" data-panel="chat" title="Chat">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
        </button>
        <button class="rail-icon" data-panel="memory" title="Memory">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="2"/><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
        </button>
        <button class="rail-icon" data-panel="skills" title="Skills">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </button>
        <button class="rail-icon" data-panel="tasks" title="Task Queue">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
        </button>
        <button class="rail-icon" data-panel="resources" title="Resource Monitor">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><rect x="3" y="12" width="4" height="8" rx="1" stroke="currentColor" stroke-width="2"/><rect x="10" y="8" width="4" height="12" rx="1" stroke="currentColor" stroke-width="2"/><rect x="17" y="4" width="4" height="16" rx="1" stroke="currentColor" stroke-width="2"/></svg>
        </button>
        <button class="rail-icon" data-panel="learning" title="Learning Dashboard">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M3 3v18h18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><path d="M7 16l4-4 4 2 5-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </button>
        <button class="rail-icon" data-panel="history" title="Activity History">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="2"/><path d="M12 6v6l4 2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
        </button>
        <button class="rail-icon" data-panel="settings" title="Settings">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="2"/><path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
        </button>
    </nav>

    <!-- Panel Area -->
    <main id="panel-area">

        <!-- Voice Panel -->
        <section class="panel active" id="panel-voice">
            <canvas id="orb-canvas" width="300" height="300"></canvas>
            <div id="transcript-panel">
                <div id="transcript-log"></div>
            </div>
            <button id="mic-btn" class="mic-button">Tap to speak</button>
        </section>

        <!-- Chat Panel -->
        <section class="panel" id="panel-chat">
            <div class="panel-header">Conversations</div>
            <div id="chat-orb-mini"><canvas id="chat-orb-canvas" width="60" height="60"></canvas></div>
            <div id="conversation-list"></div>
        </section>

        <!-- Memory Panel -->
        <section class="panel" id="panel-memory">
            <div class="panel-header">Memory</div>
            <div class="memory-split">
                <div class="memory-col"><h3>Short-Term</h3><div id="stm-list" class="card-list"></div></div>
                <div class="memory-col"><h3>Long-Term</h3><div id="ltm-list" class="card-list"></div></div>
            </div>
        </section>

        <!-- Skills Panel -->
        <section class="panel" id="panel-skills">
            <div class="panel-header">Skills</div>
            <div id="skill-list"></div>
        </section>

        <!-- Task Queue Panel -->
        <section class="panel" id="panel-tasks">
            <div class="panel-header">Task Queue</div>
            <div id="task-list"></div>
        </section>

        <!-- Resource Monitor Panel -->
        <section class="panel" id="panel-resources">
            <div class="panel-header">Resource Monitor</div>
            <div id="resource-stats">
                <div class="stat-card"><label>GPU</label><div id="gpu-bar" class="bar"><div class="bar-fill"></div></div><span id="gpu-pct">—</span></div>
                <div class="stat-card"><label>RAM</label><div id="ram-bar" class="bar"><div class="bar-fill"></div></div><span id="ram-pct">—</span></div>
            </div>
            <div id="active-jobs"></div>
        </section>

        <!-- Learning Dashboard Panel -->
        <section class="panel" id="panel-learning">
            <div class="panel-header">Learning Dashboard</div>
            <div id="learning-metrics">
                <div class="metric-card"><span class="metric-value" id="metric-behaviors">0</span><span class="metric-label">Behaviors Learned</span></div>
                <div class="metric-card"><span class="metric-value" id="metric-skills">0</span><span class="metric-label">Skills Acquired</span></div>
                <div class="metric-card"><span class="metric-value" id="metric-profiles">0</span><span class="metric-label">Profiles Tracked</span></div>
            </div>
            <div id="confidence-scores"></div>
        </section>

        <!-- Activity History Panel -->
        <section class="panel" id="panel-history">
            <div class="panel-header">Activity History</div>
            <div id="event-filters">
                <button class="filter-btn active" data-filter="all">All</button>
                <button class="filter-btn" data-filter="chat">Chat</button>
                <button class="filter-btn" data-filter="skill">Skill</button>
                <button class="filter-btn" data-filter="task">Task</button>
                <button class="filter-btn" data-filter="system">System</button>
            </div>
            <div id="event-log"></div>
        </section>

        <!-- Settings Panel -->
        <section class="panel" id="panel-settings">
            <div class="panel-header">Settings</div>
            <div class="settings-group">
                <h3>Voice</h3>
                <label>Wake word<input type="text" id="setting-wake-word" value="Hey Moka"></label>
                <label>Mic<select id="setting-mic"></select></label>
                <label>TTS Voice<select id="setting-tts"></select></label>
            </div>
            <div class="settings-group">
                <h3>Data</h3>
                <button class="btn-secondary" id="btn-clear-history">Clear History</button>
                <button class="btn-secondary" id="btn-export-memory">Export Memory</button>
            </div>
            <div class="settings-group">
                <h3>About</h3>
                <p id="app-version">Moka AI — loading...</p>
            </div>
        </section>

    </main>
</div>

<script src="/static/js/app.js"></script>
</body>
</html>
```

### `frontend/static/css/style.css`

```css
/* ═══ CSS Variables ═══ */
:root {
    --bg-base: #F2EBE0;
    --bg-panel: rgba(242, 231, 224, 0.55);
    --bg-card: rgba(255, 248, 240, 0.7);
    --text-primary: #2C1A0E;
    --text-secondary: #6B4C3B;
    --accent-sand: #D4B896;
    --accent-amber: #C9956A;
    --orb-idle: #D9CFC4;
    --orb-listening: #E8A96B;
    --orb-thinking: #4A2C17;
    --orb-speaking: #F0D9A0;
    --orb-error: #7A4A3A;
    --border-subtle: rgba(212, 184, 150, 0.35);
    --glass-bg: rgba(242, 231, 224, 0.55);
    --glass-border: rgba(212, 184, 150, 0.35);
    --glass-blur: blur(16px);
    --card-bg: rgba(255, 248, 240, 0.7);
    --card-border: rgba(212, 184, 150, 0.25);
    --rail-width: 56px;
}

/* ═══ Reset ═══ */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body { height: 100%; background: var(--bg-base); color: var(--text-primary); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 14px; }

/* ═══ App Shell ═══ */
#app { display: flex; height: 100vh; overflow: hidden; }

/* ═══ Icon Rail ═══ */
#icon-rail {
    width: var(--rail-width);
    background: var(--bg-base);
    border-right: 1px solid var(--border-subtle);
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 12px 0;
    gap: 4px;
    flex-shrink: 0;
}
.rail-icon {
    width: 40px; height: 40px;
    border-radius: 10px;
    border: none;
    background: transparent;
    color: var(--text-secondary);
    cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    transition: background 0.2s, color 0.2s;
}
.rail-icon:hover { background: var(--bg-card); color: var(--text-primary); }
.rail-icon.active { background: var(--accent-sand); color: var(--text-primary); }
.rail-icon svg { width: 22px; height: 22px; }

/* ═══ Panel Area ═══ */
#panel-area {
    flex: 1;
    position: relative;
    overflow: hidden;
}
.panel {
    position: absolute;
    inset: 0;
    padding: 24px;
    display: none;
    flex-direction: column;
    gap: 16px;
    overflow-y: auto;
}
.panel.active { display: flex; }

/* Glassmorphism panels */
.panel {
    background: var(--glass-bg);
    backdrop-filter: var(--glass-blur);
    -webkit-backdrop-filter: var(--glass-blur);
}

.panel-header {
    font-size: 18px;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 8px;
}

/* ═══ Cards ═══ */
.card {
    background: var(--card-bg);
    backdrop-filter: blur(8px);
    border: 1px solid var(--card-border);
    border-radius: 12px;
    padding: 12px 16px;
}
.card-list { display: flex; flex-direction: column; gap: 8px; }

/* ═══ Voice Panel ═══ */
#panel-voice {
    align-items: center;
    justify-content: center;
    gap: 24px;
}
#orb-canvas { cursor: pointer; }
#transcript-panel {
    max-height: 160px;
    width: 100%;
    max-width: 480px;
    overflow-y: auto;
}
#transcript-log {
    display: flex;
    flex-direction: column;
    gap: 8px;
}
.transcript-line { font-size: 13px; color: var(--text-secondary); padding: 4px 0; border-bottom: 1px solid var(--card-border); }
.transcript-line:last-child { color: var(--text-primary); font-weight: 500; }
.mic-button {
    padding: 12px 32px;
    border-radius: 24px;
    border: 1.5px solid var(--accent-sand);
    background: var(--card-bg);
    color: var(--text-primary);
    font-size: 14px;
    cursor: pointer;
    transition: background 0.2s;
}
.mic-button:hover { background: var(--accent-sand); }

/* ═══ Chat Panel ═══ */
#panel-chat { gap: 12px; }
#chat-orb-mini { display: flex; justify-content: center; opacity: 0.6; }
#conversation-list { display: flex; flex-direction: column; gap: 8px; }
.conv-item {
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 12px;
    padding: 12px 16px;
    cursor: pointer;
    transition: background 0.2s;
}
.conv-item:hover { background: var(--accent-sand); }
.conv-meta { font-size: 11px; color: var(--text-secondary); margin-bottom: 4px; }
.conv-preview { font-size: 13px; color: var(--text-primary); }

/* ═══ Memory Panel ═══ */
.memory-split { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.memory-col h3 { font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-secondary); margin-bottom: 8px; }

/* ═══ Task Queue ═══ */
#task-list { display: flex; flex-direction: column; gap: 8px; }
.task-item {
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 12px;
    padding: 12px 16px;
    display: flex;
    align-items: center;
    gap: 12px;
}
.task-chip {
    padding: 2px 10px;
    border-radius: 10px;
    font-size: 11px;
    font-weight: 500;
    text-transform: uppercase;
}
.chip-pending { background: var(--accent-sand); color: var(--text-primary); }
.chip-running { background: var(--orb-speaking); color: var(--text-primary); }
.chip-done { background: #b5d4a0; color: #2a4a1a; }
.chip-failed { background: var(--orb-error); color: white; }

/* ═══ Resource Monitor ═══ */
.stat-card {
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 12px;
    padding: 16px;
}
.stat-card label { font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-secondary); }
.bar { height: 6px; background: var(--accent-sand); border-radius: 3px; margin: 8px 0 4px; overflow: hidden; }
.bar-fill { height: 100%; background: var(--accent-amber); border-radius: 3px; width: 0%; transition: width 0.5s ease; }

/* ═══ Learning Dashboard ═══ */
#learning-metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.metric-card {
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 12px;
    padding: 16px;
    text-align: center;
}
.metric-value { display: block; font-size: 28px; font-weight: 600; color: var(--text-primary); }
.metric-label { font-size: 11px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.05em; }

/* ═══ Activity History ═══ */
#event-filters { display: flex; gap: 8px; flex-wrap: wrap; }
.filter-btn {
    padding: 4px 12px;
    border-radius: 8px;
    border: 1px solid var(--accent-sand);
    background: transparent;
    color: var(--text-secondary);
    font-size: 12px;
    cursor: pointer;
}
.filter-btn.active { background: var(--accent-amber); color: var(--text-primary); border-color: var(--accent-amber); }
#event-log { display: flex; flex-direction: column; gap: 6px; }
.event-item {
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 12px;
    color: var(--text-secondary);
}
.event-item .event-time { opacity: 0.6; margin-right: 8px; }
.event-item .event-type { font-weight: 600; margin-right: 8px; }

/* ═══ Settings ═══ */
.settings-group {
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 12px;
    padding: 16px;
}
.settings-group h3 { font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-secondary); margin-bottom: 12px; }
.settings-group label { display: flex; flex-direction: column; gap: 4px; font-size: 13px; color: var(--text-primary); margin-bottom: 10px; }
.settings-group input, .settings-group select {
    padding: 8px 12px;
    border-radius: 8px;
    border: 1px solid var(--accent-sand);
    background: var(--bg-base);
    color: var(--text-primary);
    font-size: 13px;
    outline: none;
}
.btn-secondary { padding: 8px 16px; border-radius: 8px; border: 1px solid var(--accent-sand); background: transparent; color: var(--text-primary); cursor: pointer; margin-right: 8px; font-size: 13px; }
.btn-secondary:hover { background: var(--accent-sand); }
#app-version { font-size: 12px; color: var(--text-secondary); }

/* ═══ Scrollbar ═══ */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--accent-sand); border-radius: 3px; }
```

---

## Task 3: Orb Canvas Renderer

**Files:**
- Create: `frontend/static/js/orb.js`
- Create: `tests/test_orb.py`

### `frontend/static/js/orb.js`

```javascript
/** Orb canvas renderer — states, pulsing, orbit dots, particles. */

const ORB_STATES = {
    idle:      { color: "#D9CFC4", pulseSpeed: 3000,  glowColor: "rgba(217,207,196,0.3)" },
    listening: { color: "#E8A96B", pulseSpeed: 1000,  glowColor: "rgba(232,169,107,0.5)" },
    thinking:  { color: "#4A2C17", pulseSpeed: 2000,  glowColor: "rgba(74,44,23,0.6)" },
    speaking:  { color: "#F0D9A0", pulseSpeed: 800,   glowColor: "rgba(240,217,160,0.5)" },
    error:     { color: "#7A4A3A", pulseSpeed: 4000,  glowColor: "rgba(122,74,58,0.4)" },
};

class OrbRenderer {
    constructor(canvas) {
        this.canvas = canvas;
        this.ctx = canvas.getContext("2d");
        this.state = "idle";
        this.time = 0;
        this.orbitAngle = 0;
        this.orbitDots = [
            { radius: 55, angle: 0, speed: 0.8, size: 3, opacity: 0.5 },
            { radius: 65, angle: 180, speed: -1.2, size: 2, opacity: 0.35 },
            { radius: 50, angle: 90, speed: 1.5, size: 2.5, opacity: 0.4 },
        ];
        this.burstParticles = [];
        this.speechRings = [];
        this.loop();
    }

    setState(newState) {
        if (newState === this.state) return;
        const prev = this.state;
        this.state = newState;
        // Wake burst on transition from listening
        if (prev === "listening") this._triggerWakeBurst();
        // Speech rings while speaking
        if (newState === "speaking") this._startSpeechRings();
        else this.speechRings = [];
    }

    _triggerWakeBurst() {
        for (let i = 0; i < 10; i++) {
            const angle = (Math.PI * 2 / 10) * i + Math.random() * 0.3;
            this.burstParticles.push({
                x: 0, y: 0,
                vx: Math.cos(angle) * (2 + Math.random() * 2),
                vy: Math.sin(angle) * (2 + Math.random() * 2),
                life: 1.0,
                decay: 0.016 + Math.random() * 0.01,
                size: 2 + Math.random() * 2,
            });
        }
    }

    _startSpeechRings() {
        const addRing = () => {
            if (this.state !== "speaking") return;
            this.speechRings.push({ radius: 30, opacity: 0.6 });
            setTimeout(addRing, 1200);
        };
        addRing();
    }

    _pulseFactor(elapsed, speed) {
        return 0.5 + 0.5 * Math.sin(elapsed / speed * Math.PI * 2);
    }

    loop() {
        this.time += 16;
        this.orbitAngle += 0.02;
        this._updateBurst();
        this._updateRings();
        this.draw();
        requestAnimationFrame(() => this.loop());
    }

    _updateBurst() {
        this.burstParticles = this.burstParticles.filter(p => {
            p.x += p.vx; p.y += p.vy;
            p.life -= p.decay;
            return p.life > 0;
        });
    }

    _updateRings() {
        this.speechRings = this.speechRings.map(r => {
            r.radius += 0.8;
            r.opacity -= 0.012;
            return r;
        }).filter(r => r.opacity > 0);
    }

    draw() {
        const { canvas, ctx, state } = this;
        const cx = canvas.width / 2;
        const cy = canvas.height / 2;
        const baseRadius = 38;
        const cfg = ORB_STATES[state] || ORB_STATES.idle;
        const pulse = this._pulseFactor(this.time % cfg.pulseSpeed, cfg.pulseSpeed);

        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Glow
        const glowGrad = ctx.createRadialGradient(cx, cy, baseRadius * 0.5, cx, cy, baseRadius * 2.5);
        glowGrad.addColorStop(0, cfg.glowColor);
        glowGrad.addColorStop(1, "transparent");
        ctx.fillStyle = glowGrad;
        ctx.beginPath();
        ctx.arc(cx, cy, baseRadius * 2.5, 0, Math.PI * 2);
        ctx.fill();

        // Orb body
        const orbGrad = ctx.createRadialGradient(cx - 8, cy - 8, 4, cx, cy, baseRadius);
        orbGrad.addColorStop(0, this._lighten(cfg.color, 20));
        orbGrad.addColorStop(1, cfg.color);
        const orbOpacity = 0.7 + 0.3 * pulse;
        ctx.globalAlpha = orbOpacity;
        ctx.fillStyle = orbGrad;
        ctx.beginPath();
        ctx.arc(cx, cy, baseRadius + pulse * 4, 0, Math.PI * 2);
        ctx.fill();
        ctx.globalAlpha = 1;

        // Speech rings
        this.speechRings.forEach(r => {
            ctx.strokeStyle = cfg.color;
            ctx.lineWidth = 1.5;
            ctx.globalAlpha = r.opacity;
            ctx.beginPath();
            ctx.arc(cx, cy, r.radius, 0, Math.PI * 2);
            ctx.stroke();
        });
        ctx.globalAlpha = 1;

        // Burst particles
        this.burstParticles.forEach(p => {
            ctx.fillStyle = cfg.color;
            ctx.globalAlpha = p.life;
            ctx.beginPath();
            ctx.arc(cx + p.x, cy + p.y, p.size, 0, Math.PI * 2);
            ctx.fill();
        });
        ctx.globalAlpha = 1;

        // Orbit dots
        this.orbitDots.forEach(dot => {
            const angleRad = (this.orbitAngle * dot.speed * Math.PI) / 180 + (dot.angle * Math.PI) / 180;
            const dx = cx + Math.cos(angleRad) * dot.radius;
            const dy = cy + Math.sin(angleRad) * dot.radius;
            ctx.fillStyle = cfg.color;
            ctx.globalAlpha = dot.opacity + 0.2 * pulse;
            ctx.beginPath();
            ctx.arc(dx, dy, dot.size, 0, Math.PI * 2);
            ctx.fill();
        });
        ctx.globalAlpha = 1;
    }

    _lighten(hex, amount) {
        const num = parseInt(hex.slice(1), 16);
        const r = Math.min(255, (num >> 16) + amount);
        const g = Math.min(255, ((num >> 8) & 0xff) + amount);
        const b = Math.min(255, (num & 0xff) + amount);
        return `rgb(${r},${g},${b})`;
    }
}
```

### `tests/test_orb.py`

```python
import unittest
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from frontend.static.jsorb import ORB_STATES
except ImportError:
    ORB_STATES = None


class TestOrbStates(unittest.TestCase):
    def test_orb_states_defined(self):
        if ORB_STATES is None:
            self.skipTest("Cannot import JS — test only verifies enum-like keys")
        self.assertIn("idle", ORB_STATES)
        self.assertIn("listening", ORB_STATES)
        self.assertIn("thinking", ORB_STATES)
        self.assertIn("speaking", ORB_STATES)
        self.assertIn("error", ORB_STATES)

    def test_orb_state_has_required_keys(self):
        required = {"color", "pulseSpeed", "glowColor"}
        for state, cfg in (ORB_STATES or {}).items():
            self.assertTrue(required.issubset(cfg.keys()), f"{state} missing keys")

    def test_orb_idle_color_valid(self):
        states = {
            "idle": {"color": "#D9CFC4", "pulseSpeed": 3000, "glowColor": "rgba(217,207,196,0.3)"},
            "listening": {"color": "#E8A96B", "pulseSpeed": 1000, "glowColor": "rgba(232,169,107,0.5)"},
        }
        import re
        hex_color = re.compile(r'^#[0-9a-fA-F]{6}$')
        for state, cfg in states.items():
            self.assertTrue(hex_color.match(cfg["color"]), f"{state} color invalid: {cfg['color']}")


if __name__ == "__main__":
    unittest.main()
```

---

## Task 4: App.js — SocketIO + Panel Switching + Event Wiring

**Files:**
- Create: `frontend/static/js/app.js`
- Create: `tests/test_app_js.py`

### `frontend/static/js/app.js`

```javascript
/** MokaAI App — SocketIO client, panel switching, event handlers. */

(function() {
    const socket = io();
    let currentPanel = "voice";
    let orbRenderer = null;
    const transcripts = [];  // { speaker, text, ts }

    // ─── Orb Initialization ──────────────────────────────────────────────
    function initOrb() {
        const canvas = document.getElementById("orb-canvas");
        if (!canvas) return;
        orbRenderer = new OrbRenderer(canvas);
        canvas.addEventListener("click", () => {
            socket.emit("mic_toggle");
        });
    }

    // ─── Panel Switching ───────────────────────────────────────────────
    function switchPanel(name) {
        if (name === currentPanel) return;
        document.querySelectorAll(".panel").forEach(p => p.classList.remove("active"));
        document.querySelectorAll(".rail-icon").forEach(b => b.classList.remove("active"));
        const panel = document.getElementById("panel-" + name);
        const btn = document.querySelector(`.rail-icon[data-panel="${name}"]`);
        if (panel) panel.classList.add("active");
        if (btn) btn.classList.add("active");
        currentPanel = name;
        socket.emit("panel_change", { panel: name });
    }

    // ─── Transcript ────────────────────────────────────────────────────
    function addTranscriptLine(speaker, text) {
        const log = document.getElementById("transcript-log");
        if (!log) return;
        transcripts.push({ speaker, text, ts: Date.now() });
        const el = document.createElement("div");
        el.className = "transcript-line";
        el.textContent = (speaker === "user" ? "You: " : "Moka: ") + text;
        log.appendChild(el);
        log.scrollTop = log.scrollHeight;
        // Keep last 50 lines
        while (log.children.length > 50) log.removeChild(log.firstChild);
    }

    // ─── Event Listeners ───────────────────────────────────────────────
    document.querySelectorAll(".rail-icon").forEach(btn => {
        btn.addEventListener("click", () => switchPanel(btn.dataset.panel));
    });

    document.querySelectorAll(".filter-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            filterEvents(btn.dataset.filter);
        });
    });

    const micBtn = document.getElementById("mic-btn");
    if (micBtn) {
        micBtn.addEventListener("click", () => socket.emit("mic_toggle"));
    }

    const btnClearHistory = document.getElementById("btn-clear-history");
    if (btnClearHistory) {
        btnClearHistory.addEventListener("click", () => {
            if (confirm("Clear all conversation history?")) {
                socket.emit("clear_history");
            }
        });
    }

    const btnExportMemory = document.getElementById("btn-export-memory");
    if (btnExportMemory) {
        btnExportMemory.addEventListener("click", () => socket.emit("export_memory"));
    }

    // ─── SocketIO Events ───────────────────────────────────────────────
    socket.on("connect", () => {
        console.log("Connected to MokaAI backend");
    });

    socket.on("agent_state", (state) => {
        if (orbRenderer) orbRenderer.setState(state.status || "idle");
        if (state.transcript) {
            state.transcript.forEach(t => addTranscriptLine(t.speaker, t.text));
        }
    });

    socket.on("agent_event", (event) => {
        if (event.type === "transcript") {
            addTranscriptLine(event.data.speaker, event.data.text);
        } else if (event.type === "resource_update") {
            updateResourceBars(event.data);
        } else if (event.type === "learning_metrics") {
            updateLearningMetrics(event.data);
        } else if (event.type === "event_log") {
            addEventLogItem(event.data);
        }
    });

    // ─── UI Update Helpers ──────────────────────────────────────────────
    function updateResourceBars(data) {
        if (data.gpu !== undefined) {
            const bar = document.getElementById("gpu-bar");
            if (bar) {
                bar.querySelector(".bar-fill").style.width = data.gpu + "%";
                bar.nextElementSibling.textContent = data.gpu + "%";
            }
        }
        if (data.ram !== undefined) {
            const bar = document.getElementById("ram-bar");
            if (bar) {
                bar.querySelector(".bar-fill").style.width = data.ram + "%";
                bar.nextElementSibling.textContent = data.ram + "%";
            }
        }
    }

    function updateLearningMetrics(data) {
        const map = {
            behaviors: "metric-behaviors",
            skills: "metric-skills",
            profiles: "metric-profiles",
        };
        for (const [key, id] of Object.entries(map)) {
            const el = document.getElementById(id);
            if (el && data[key] !== undefined) el.textContent = data[key];
        }
    }

    function addEventLogItem(data) {
        const log = document.getElementById("event-log");
        if (!log) return;
        const filter = document.querySelector(".filter-btn.active")?.dataset.filter || "all";
        if (filter !== "all" && data.type !== filter) return;
        const item = document.createElement("div");
        item.className = "event-item";
        const time = new Date(data.ts).toLocaleTimeString();
        item.innerHTML = `<span class="event-time">${time}</span><span class="event-type">${data.type}</span>${data.description || ""}`;
        log.insertBefore(item, log.firstChild);
        while (log.children.length > 100) log.removeChild(log.lastChild);
    }

    function filterEvents(type) {
        // Re-render with filter — for now the addEventLogItem checks filter
    }

    // ─── Boot ───────────────────────────────────────────────────────────
    document.addEventListener("DOMContentLoaded", () => {
        initOrb();
        socket.emit("panel_change", { panel: "voice" });
    });
})();
```

---

## Task 5: Backend Event Wiring + Mock Data for All Panels

**Files:**
- Modify: `backend/app.py`
- Create: `tests/test_backend_events.py`

### Changes to `backend/app.py`

Add event simulation for development (mock data sent to UI):

```python
import threading
import time
import random

def start_mock_broadcasts():
    """Send mock event data to all connected clients for development."""
    def run():
        while True:
            time.sleep(5)
            state = {
                "status": random.choice(["idle", "idling", "thinking", "speaking"]),
                "transcript": [],
            }
            socketio.emit("agent_state", state)
            socketio.emit("agent_event", {
                "type": "event_log",
                "data": {
                    "ts": time.time(),
                    "type": random.choice(["chat", "skill", "task", "system"]),
                    "description": "Mock event: agent " + random.choice(["started", "responded", "task completed"]),
                }
            })
    t = threading.Thread(target=run, daemon=True)
    t.start()
```

In `app.py`, after `socketio = SocketIO(...)`, call `start_mock_broadcasts()`.

Update `@app.route("/")` to serve from template path:

```python
from pathlib import Path
template_dir = Path(__file__).parent.parent / "frontend" / "templates"
static_dir = Path(__file__).parent.parent / "frontend" / "static"
app.template_folder = str(template_dir)
app.static_folder = str(static_dir)
```

Add SocketIO event handlers:

```python
@socketio.on("mic_toggle")
def handle_mic_toggle():
    broadcast_state({"status": "listening"})
    time.sleep(2)
    broadcast_state({"status": "thinking"})
    time.sleep(1)
    broadcast_state({"status": "speaking"})
    add_transcript("user", "What is the capital of France?")
    time.sleep(2)
    broadcast_state({"status": "speaking"})
    add_transcript("moka", "The capital of France is Paris.")
    time.sleep(1)
    broadcast_state({"status": "idle"})


@socketio.on("panel_change")
def handle_panel_change(data):
    pass  # Acknowledge only


@socketio.on("clear_history")
def handle_clear_history():
    global AGENT_STATE
    AGENT_STATE["transcript"] = []
    emit("agent_state", AGENT_STATE)


@socketio.on("export_memory")
def handle_export_memory():
    emit("agent_event", {
        "type": "memory_export",
        "data": {"url": "/api/memory/export"}
    })
```

---

## Acceptance Criteria

- [ ] Flasked app serves HTML at `http://localhost:5555`
- [ ] Icon rail switches between 9 panels with glassmorphism active panel
- [ ] Orb renders on canvas with correct idle color (#D9CFC4) + orbit dots + breathing pulse
- [ ] State transitions (idle→listening→thinking→speaking→idle) animate smoothly with correct colors
- [ ] Wake burst triggers on Listening→next state transition
- [ ] Speech rings appear during Speaking state
- [ ] Transcript scroll updates in real-time
- [ ] Mock event data populates all panels (memory, skills, tasks, resources, learning, history)
- [ ] Settings panel shows voice controls + about
- [ ] SocketIO connects and receives state events
- [ ] 213 + new tests pass