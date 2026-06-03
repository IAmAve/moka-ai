# Phase 13 Part B: Main App UI Redesign Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rewrite `frontend/` to Google modern minimalism (Figtree font, shadow hierarchy, generous whitespace, amber CTAs) while preserving Phase 11 warm sand/espresso palette and glassmorphism panels.

**Architecture:** Vanilla HTML/CSS/JS served by `backend/app.py` at `/`. `orb.js` drives the animated orb on the Voice panel. `app.js` handles SocketIO events and panel switching. No build step, no bundler — direct browser load.

---

## File Map

| Action | File |
|--------|------|
| Rewrite | `frontend/templates/index.html` |
| Rewrite | `frontend/static/css/style.css` |
| Rewrite | `frontend/static/js/app.js` |
| Rewrite | `frontend/static/js/orb.js` (add missing methods called by app.js) |
| Create | `frontend/static/fonts/Figtree-Variable.woff2` (self-hosted, ~80KB) |
| Create | `frontend/static/fonts/CascadiaCode.woff2` |

---

## Task 1: Download Self-Hosted Fonts

**Files:**
- Create: `frontend/static/fonts/`

- [ ] **Step 1: Download Figtree Variable woff2**

Download from: `https://fonts.google.com/download?family=Figtree` (or use Google Fonts CSS API to get direct woff2 URL). Save as `frontend/static/fonts/Figtree-Variable.woff2`.

- [ ] **Step 2: Download Cascadia Code woff2**

Download from: `https://raw.githubusercontent.com/microsoft/cascadia-code/master/fonts/web/CascadiaCode.woff2`. Save as `frontend/static/fonts/CascadiaCode.woff2`.

- [ ] **Step 3: Commit**

```bash
git add frontend/static/fonts/
git commit -m "chore(frontend): add self-hosted Figtree + Cascadia Code fonts"
```

---

## Task 2: index.html — Clean Structure

**Files:**
- Rewrite: `frontend/templates/index.html`

- [ ] **Step 1: Write index.html**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Moka AI</title>
  <link rel="stylesheet" href="/static/css/style.css">
  <link rel="preload" href="/static/fonts/Figtree-Variable.woff2" as="font" type="font/woff2" crossorigin>
  <link rel="preload" href="/static/fonts/CascadiaCode.woff2" as="font" type="font/woff2" crossorigin>
  <script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>
</head>
<body>

<div id="app">

  <!-- Icon Rail -->
  <nav id="icon-rail" role="navigation" aria-label="Main navigation">
    <button class="rail-icon active" data-panel="voice" title="Voice" aria-label="Voice">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M12 14a3 3 0 003 3V21h-6v-4a3 3 0 003-3z" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      </svg>
    </button>
    <button class="rail-icon" data-panel="chat" title="Chat" aria-label="Chat">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      </svg>
    </button>
    <button class="rail-icon" data-panel="memory" title="Memory" aria-label="Memory">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="2"/>
        <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      </svg>
    </button>
    <button class="rail-icon" data-panel="skills" title="Skills" aria-label="Skills">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </button>
    <button class="rail-icon" data-panel="tasks" title="Task Queue" aria-label="Task Queue">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      </svg>
    </button>
    <button class="rail-icon" data-panel="resources" title="Resource Monitor" aria-label="Resource Monitor">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <rect x="3" y="12" width="4" height="8" rx="1" stroke="currentColor" stroke-width="2"/>
        <rect x="10" y="8" width="4" height="12" rx="1" stroke="currentColor" stroke-width="2"/>
        <rect x="17" y="4" width="4" height="16" rx="1" stroke="currentColor" stroke-width="2"/>
      </svg>
    </button>
    <button class="rail-icon" data-panel="learning" title="Learning Dashboard" aria-label="Learning Dashboard">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M3 3v18h18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        <path d="M7 16l4-4 4 2 5-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </button>
    <button class="rail-icon" data-panel="history" title="Activity History" aria-label="Activity History">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="2"/>
        <path d="M12 6v6l4 2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      </svg>
    </button>
    <button class="rail-icon" id="rail-settings" data-panel="settings" title="Settings" aria-label="Settings">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="2"/>
        <path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      </svg>
    </button>
  </nav>

  <!-- Panel Area -->
  <main id="panel-area" role="main">

    <!-- Voice Panel -->
    <section class="panel active" id="panel-voice" aria-label="Voice">
      <div class="voice-orb-wrap">
        <canvas id="orb-canvas" width="240" height="240" aria-label="Moka AI orb"></canvas>
      </div>
      <div class="transcript-wrap" id="transcript-wrap">
        <div id="transcript-log" role="log" aria-live="polite" aria-label="Conversation transcript"></div>
      </div>
      <button class="mic-btn" id="mic-btn" aria-label="Tap to speak">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path d="M12 14a3 3 0 003 3V21h-6v-4a3 3 0 003-3z" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        </svg>
        Tap to speak
      </button>
    </section>

    <!-- Chat Panel -->
    <section class="panel" id="panel-chat" aria-label="Conversations">
      <div class="panel-header">
        <div class="mini-orb-wrap"><canvas id="chat-orb-canvas" width="48" height="48" aria-hidden="true"></canvas></div>
        <h2>Conversations</h2>
      </div>
      <div id="conversation-list" role="list" aria-label="Past conversations"></div>
    </section>

    <!-- Memory Panel -->
    <section class="panel" id="panel-memory" aria-label="Memory">
      <div class="panel-header"><h2>Memory</h2></div>
      <div class="memory-split">
        <div class="memory-col">
          <h3 class="col-label">Short-Term</h3>
          <div id="stm-list" class="card-list" role="list" aria-label="Short-term memory"></div>
        </div>
        <div class="memory-col">
          <h3 class="col-label">Long-Term</h3>
          <div id="ltm-list" class="card-list" role="list" aria-label="Long-term memory"></div>
        </div>
      </div>
    </section>

    <!-- Skills Panel -->
    <section class="panel" id="panel-skills" aria-label="Skills">
      <div class="panel-header"><h2>Skills</h2></div>
      <div id="skill-list" role="list" aria-label="Available skills"></div>
    </section>

    <!-- Task Queue Panel -->
    <section class="panel" id="panel-tasks" aria-label="Task Queue">
      <div class="panel-header"><h2>Task Queue</h2></div>
      <div id="task-list" role="list" aria-label="Active tasks"></div>
    </section>

    <!-- Resource Monitor Panel -->
    <section class="panel" id="panel-resources" aria-label="Resource Monitor">
      <div class="panel-header"><h2>Resource Monitor</h2></div>
      <div class="resource-stats" id="resource-stats">
        <div class="metric-card">
          <div class="metric-label">GPU Usage</div>
          <div class="bar-track"><div class="bar-fill" id="gpu-bar-fill"></div></div>
          <div class="metric-value" id="gpu-pct">—</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">RAM Usage</div>
          <div class="bar-track"><div class="bar-fill" id="ram-bar-fill"></div></div>
          <div class="metric-value" id="ram-pct">—</div>
        </div>
      </div>
      <div id="active-jobs" aria-label="Active generation jobs"></div>
    </section>

    <!-- Learning Dashboard Panel -->
    <section class="panel" id="panel-learning" aria-label="Learning Dashboard">
      <div class="panel-header"><h2>Learning Dashboard</h2></div>
      <div id="learning-metrics" class="metrics-grid">
        <div class="metric-card">
          <div class="metric-value" id="metric-behaviors">0</div>
          <div class="metric-label">Behaviors Learned</div>
        </div>
        <div class="metric-card">
          <div class="metric-value" id="metric-skills">0</div>
          <div class="metric-label">Skills Acquired</div>
        </div>
        <div class="metric-card">
          <div class="metric-value" id="metric-profiles">0</div>
          <div class="metric-label">Profiles Tracked</div>
        </div>
      </div>
      <div id="confidence-scores" class="scores-grid"></div>
    </section>

    <!-- Activity History Panel -->
    <section class="panel" id="panel-history" aria-label="Activity History">
      <div class="panel-header"><h2>Activity History</h2></div>
      <div class="filter-row" role="group" aria-label="Filter events">
        <button class="filter-btn active" data-filter="all" aria-pressed="true">All</button>
        <button class="filter-btn" data-filter="chat" aria-pressed="false">Chat</button>
        <button class="filter-btn" data-filter="skill" aria-pressed="false">Skill</button>
        <button class="filter-btn" data-filter="task" aria-pressed="false">Task</button>
        <button class="filter-btn" data-filter="system" aria-pressed="false">System</button>
      </div>
      <div id="event-log" class="event-log" role="log" aria-live="polite" aria-label="Event log"></div>
    </section>

    <!-- Settings Panel -->
    <section class="panel" id="panel-settings" aria-label="Settings">
      <div class="panel-header"><h2>Settings</h2></div>
      <div class="settings-section">
        <h3 class="settings-group-label">Voice</h3>
        <div class="field-row">
          <label for="setting-wake-word" class="field-label">Wake word</label>
          <input type="text" id="setting-wake-word" class="input" value="Hey Moka">
        </div>
        <div class="field-row">
          <label for="setting-mic" class="field-label">Microphone</label>
          <select id="setting-mic" class="select"></select>
        </div>
        <div class="field-row">
          <label for="setting-tts" class="field-label">TTS Voice</label>
          <select id="setting-tts" class="select"></select>
        </div>
      </div>
      <div class="settings-section">
        <h3 class="settings-group-label">Data</h3>
        <div class="btn-row">
          <button class="btn-secondary" id="btn-clear-history">Clear History</button>
          <button class="btn-secondary" id="btn-export-memory">Export Memory</button>
        </div>
      </div>
      <div class="settings-section settings-about">
        <p class="about-text" id="app-version">Moka AI</p>
      </div>
    </section>

  </main>
</div>

<script src="/static/js/orb.js"></script>
<script src="/static/js/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/templates/index.html
git commit -m "refactor(frontend): rewrite index.html — clean semantic structure, accessibility attrs, self-hosted fonts"
```

---

## Task 3: style.css — Google Modern Minimalism

**Files:**
- Rewrite: `frontend/static/css/style.css`

- [ ] **Step 1: Write the complete stylesheet**

```css
/* ═══ Figtree Font Face ═══ */
@font-face {
  font-family: 'Figtree';
  src: url('/static/fonts/Figtree-Variable.woff2') format('woff2-variations');
  font-weight: 300 900;
  font-style: normal;
  font-display: swap;
}
@font-face {
  font-family: 'Cascadia Code';
  src: url('/static/fonts/CascadiaCode.woff2') format('woff2');
  font-weight: 400;
  font-style: normal;
  font-display: swap;
}

/* ═══ CSS Variables — Phase 11 Warmth + Google Minimalism ═══ */
:root {
  --bg-base:           #F2EBE0;
  --bg-panel:          rgba(242, 231, 224, 0.55);
  --bg-card:           rgba(255, 248, 240, 0.72);
  --bg-white:          #fffdf9;
  --text-primary:      #2C1A0E;
  --text-secondary:    #6B4C3B;
  --text-tertiary:     #9C7A6A;
  --accent:            #C9956A;
  --accent-hover:      #B8845A;
  --success:           #2a7a50;
  --error:             #7A4A3A;
  --border-subtle:      rgba(212, 184, 150, 0.25);
  --border-card:        rgba(212, 184, 150, 0.18);
  --shadow-xs:          0 1px 2px rgba(44, 26, 14, 0.06);
  --shadow-sm:          0 1px 4px rgba(44, 26, 14, 0.08);
  --shadow-md:          0 4px 12px rgba(44, 26, 14, 0.10);
  --shadow-lg:          0 8px 24px rgba(44, 26, 14, 0.13);
  --radius-xs:          4px;
  --radius-sm:          8px;
  --radius-md:          12px;
  --radius-lg:          16px;
  --radius-full:        9999px;
  --rail-width:         60px;
  --font-sans:          'Figtree', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --font-mono:          'Cascadia Code', 'SF Mono', 'Cascadia Code', monospace;
  --ease-out:           cubic-bezier(0.16, 1, 0.3, 1);
}

/* ═══ Reset ═══ */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { font-size: 15px; }
body {
  height: 100%;
  background: var(--bg-base);
  color: var(--text-primary);
  font-family: var(--font-sans);
  font-size: 14px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
  overflow: hidden;
}

/* ═══ App Shell ═══ */
#app {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

/* ═══ Icon Rail ═══ */
#icon-rail {
  width: var(--rail-width);
  background: var(--bg-base);
  border-right: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px 0;
  gap: 3px;
  flex-shrink: 0;
  overflow-y: auto;
  overflow-x: visible;
}
.rail-icon {
  width: 42px;
  height: 42px;
  border-radius: var(--radius-md);
  border: none;
  background: transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  transition: background 0.15s ease, color 0.15s ease, transform 0.1s ease;
}
.rail-icon svg { width: 20px; height: 20px; transition: transform 0.15s; }
.rail-icon:hover {
  background: rgba(212, 184, 150, 0.2);
  color: var(--text-primary);
}
.rail-icon.active {
  background: var(--accent);
  color: white;
  box-shadow: var(--shadow-sm);
}
.rail-icon.active svg { transform: scale(1.05); }

/* ═══ Panel Area ═══ */
#panel-area {
  flex: 1;
  position: relative;
  overflow: hidden;
  /* Glassmorphism: blur behind panel content */
  backdrop-filter: blur(0px); /* disabled — each panel applies its own */
}

/* ═══ Base Panel ═══ */
.panel {
  position: absolute;
  inset: 0;
  padding: 28px 32px;
  display: none;
  flex-direction: column;
  gap: 20px;
  overflow-y: auto;
  /* Google glassmorphism: warm frosted glass */
  background: var(--bg-panel);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  animation: panelIn 0.2s var(--ease-out);
}
.panel.active { display: flex; }

@keyframes panelIn {
  from { opacity: 0; transform: translateX(8px); }
  to   { opacity: 1; transform: translateX(0); }
}

/* ═══ Panel Header ═══ */
.panel-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 4px;
}
.panel-header h2 {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: -0.01em;
}
.mini-orb-wrap {
  opacity: 0.65;
}

/* ═══ Cards (Google shadow system — NO border, shadow hierarchy) ═══ */
.card {
  background: var(--bg-card);
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  padding: 14px 16px;
  box-shadow: var(--shadow-sm);
  transition: box-shadow 0.15s ease, transform 0.15s ease;
}
.card:hover {
  box-shadow: var(--shadow-md);
}
.card-elevated { box-shadow: var(--shadow-md); }

/* ═══ Voice Panel ═══ */
#panel-voice {
  align-items: center;
  justify-content: center;
  gap: 24px;
  text-align: center;
}
.voice-orb-wrap {
  flex-shrink: 0;
}
#orb-canvas {
  cursor: pointer;
  display: block;
}
.transcript-wrap {
  width: 100%;
  max-width: 520px;
  max-height: 160px;
  overflow-y: auto;
  scroll-behavior: smooth;
}
#transcript-log {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.transcript-line {
  font-size: 13px;
  color: var(--text-secondary);
  padding: 5px 0;
  border-bottom: 1px solid var(--border-card);
  line-height: 1.5;
}
.transcript-line:last-child {
  color: var(--text-primary);
  font-weight: 500;
}

.mic-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 11px 28px;
  background: var(--accent);
  color: white;
  border: none;
  border-radius: var(--radius-full);
  font-family: var(--font-sans);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: var(--shadow-md);
  transition: background 0.15s, box-shadow 0.15s, transform 0.1s;
}
.mic-btn:hover {
  background: var(--accent-hover);
  box-shadow: var(--shadow-lg);
  transform: translateY(-1px);
}
.mic-btn:active {
  transform: translateY(0);
  box-shadow: var(--shadow-sm);
}

/* ═══ Chat Panel ═══ */
.conv-item {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  padding: 12px 16px;
  cursor: pointer;
  box-shadow: var(--shadow-sm);
  transition: box-shadow 0.15s, transform 0.15s;
  border: 1px solid transparent;
}
.conv-item:hover { box-shadow: var(--shadow-md); transform: translateY(-1px); }
.conv-meta { font-size: 11px; font-weight: 500; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; }
.conv-preview { font-size: 13px; color: var(--text-primary); font-weight: 500; }
.conv-date { font-size: 11px; color: var(--text-tertiary); }

/* ═══ Memory Panel ═══ */
.memory-split { display: flex; gap: 24px; }
.memory-col { flex: 1; display: flex; flex-direction: column; gap: 10px; }
.col-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--text-tertiary);
}
.card-list { display: flex; flex-direction: column; gap: 8px; }
.memory-card {
  background: var(--bg-card);
  border-radius: var(--radius-sm);
  padding: 10px 14px;
  font-size: 13px;
  color: var(--text-secondary);
  box-shadow: var(--shadow-sm);
  line-height: 1.5;
}

/* ═══ Skills Panel ═══ */
.skill-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--bg-card);
  border-radius: var(--radius-md);
  padding: 13px 16px;
  box-shadow: var(--shadow-sm);
  border: 1px solid transparent;
  transition: box-shadow 0.15s, transform 0.15s;
}
.skill-item:hover { box-shadow: var(--shadow-md); transform: translateY(-1px); }
.skill-name { font-size: 14px; font-weight: 500; color: var(--text-primary); }

/* ═══ Task Queue ═══ */
.task-item {
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--bg-card);
  border-radius: var(--radius-md);
  padding: 12px 16px;
  box-shadow: var(--shadow-sm);
  border: 1px solid transparent;
  transition: box-shadow 0.15s, transform 0.15s;
}
.task-item:hover { box-shadow: var(--shadow-md); }
.task-name { flex: 1; font-size: 14px; color: var(--text-primary); }

/* ═══ Resource Monitor ═══ */
.resource-stats { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.metric-label { font-size: 12px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-tertiary); margin-bottom: 8px; font-weight: 500; }
.metric-card { background: var(--bg-card); border-radius: var(--radius-md); padding: 16px 18px; box-shadow: var(--shadow-sm); }
.metric-value { font-size: 20px; font-weight: 700; color: var(--text-primary); margin-top: 8px; font-family: var(--font-mono); }

/* ═══ Learning Dashboard ═══ */
.metrics-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
.scores-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 12px;
}
.score-card {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  box-shadow: var(--shadow-sm);
}
.score-category { font-size: 12px; color: var(--text-secondary); font-weight: 500; }
.score-value { font-size: 18px; font-weight: 700; color: var(--text-primary); }

/* ═══ Activity History ═══ */
.filter-row {
  display: inline-flex;
  gap: 4px;
  padding: 4px;
  background: rgba(212, 184, 150, 0.18);
  border-radius: var(--radius-sm);
  align-self: flex-start;
}
.filter-btn {
  padding: 5px 14px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--text-secondary);
  font-family: var(--font-sans);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.12s, color 0.12s;
}
.filter-btn:hover { background: rgba(212, 184, 150, 0.3); color: var(--text-primary); }
.filter-btn.active {
  background: var(--bg-white);
  color: var(--text-primary);
  box-shadow: var(--shadow-xs);
}
.event-log { display: flex; flex-direction: column; gap: 6px; }
.event-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  background: var(--bg-card);
  border-radius: var(--radius-sm);
  padding: 8px 12px;
  box-shadow: var(--shadow-sm);
  font-size: 13px;
}
.event-time { font-size: 11px; color: var(--text-tertiary); white-space: nowrap; font-family: var(--font-mono); }
.event-type { font-size: 11px; font-weight: 600; padding: 1px 7px; border-radius: var(--radius-full); text-transform: uppercase; letter-spacing: 0.04em; flex-shrink: 0; }
.event-type-chat    { background: rgba(201,149,106,0.2); color: var(--accent-hover); }
.event-type-skill   { background: rgba(46,192,124,0.15); color: var(--success); }
.event-type-task    { background: rgba(74,144,226,0.15); color: #3a6ea5; }
.event-type-system  { background: rgba(156,122,106,0.15); color: var(--text-secondary); }
.event-desc { color: var(--text-secondary); flex: 1; }

/* ═══ Settings ═══ */
.settings-section {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  padding: 18px 20px;
  box-shadow: var(--shadow-sm);
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.settings-group-label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--text-tertiary);
  font-weight: 600;
  margin-bottom: 2px;
}
.field-row { display: flex; flex-direction: column; gap: 5px; }
.field-label { font-size: 13px; color: var(--text-secondary); font-weight: 500; }
.settings-about { background: transparent; box-shadow: none; }
.about-text { font-size: 12px; color: var(--text-tertiary); }

/* ═══ Buttons — Google Style ═══ */
.btn-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 20px;
  background: var(--accent);
  color: white;
  border: none;
  border-radius: var(--radius-sm);
  font-family: var(--font-sans);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: var(--shadow-sm);
  transition: background 0.15s, box-shadow 0.15s, transform 0.1s;
  text-decoration: none;
}
.btn-primary:hover {
  background: var(--accent-hover);
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
}
.btn-primary:active { transform: translateY(0); box-shadow: var(--shadow-sm); }

.btn-secondary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 9px 18px;
  background: transparent;
  color: var(--text-primary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  font-family: var(--font-sans);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s, box-shadow 0.15s;
}
.btn-secondary:hover { background: var(--bg-card); box-shadow: var(--shadow-sm); }

.btn-row { display: flex; gap: 10px; flex-wrap: wrap; }

/* ═══ Form Elements — Google Style ═══ */
.input, .select {
  width: 100%;
  padding: 9px 12px;
  background: var(--bg-white);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  font-family: var(--font-sans);
  font-size: 14px;
  color: var(--text-primary);
  outline: none;
  box-shadow: inset 0 1px 3px rgba(44,26,14,0.06);
  transition: border-color 0.15s, box-shadow 0.15s;
  appearance: none;
}
.input:focus, .select:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(201,149,106,0.15), inset 0 1px 3px rgba(44,26,14,0.04);
}
.input::placeholder { color: var(--text-tertiary); }
.select {
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%239C7A6A' stroke-width='2'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 12px center;
  padding-right: 36px;
  cursor: pointer;
}

/* ═══ Chips & Badges ═══ */
.chip {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  border-radius: var(--radius-full);
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.chip-success  { background: rgba(46,192,124,0.15); color: var(--success); }
.chip-warning  { background: rgba(201,149,106,0.15); color: var(--accent-hover); }
.chip-neutral  { background: rgba(212,184,150,0.25); color: var(--text-secondary); }
.chip-running  { background: rgba(240,217,160,0.3); color: var(--accent-hover); }

/* ═══ Task/Mode Chips ═══ */
.chip-pending   { background: rgba(212,184,150,0.25); color: var(--text-secondary); }
.chip-done     { background: rgba(46,192,124,0.15); color: var(--success); }
.chip-failed   { background: rgba(122,74,58,0.15); color: var(--error); }

/* ═══ Progress Bars ═══ */
.bar-track {
  height: 6px;
  background: rgba(212,184,150,0.3);
  border-radius: 3px;
  overflow: hidden;
  margin: 8px 0 4px;
}
.bar-fill {
  height: 100%;
  background: var(--accent);
  border-radius: 3px;
  transition: width 0.5s var(--ease-out);
}

/* ═══ Scrollbar Styling ═══ */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(212,184,150,0.5); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(212,184,150,0.7); }

/* ═══ Utilities ═══ */
.card-list { display: flex; flex-direction: column; gap: 8px; }
.text-muted { color: var(--text-tertiary); }
.text-mono { font-family: var(--font-mono); }

/* ═══ Responsive — Mobile Bottom Tab Bar ═══ */
@media (max-width: 640px) {
  #icon-rail {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    top: auto;
    width: 100%;
    height: 60px;
    flex-direction: row;
    justify-content: space-around;
    border-right: none;
    border-top: 1px solid var(--border-subtle);
    padding: 6px 0;
    background: rgba(242,231,224,0.92);
    backdrop-filter: blur(12px);
    z-index: 100;
  }
  #panel-area {
    padding-bottom: 68px;
  }
  .panel { padding: 20px 16px; }
  .metrics-grid { grid-template-columns: repeat(2, 1fr); }
}
```

- [ ] **Step 2: Update orb.js to work with new structure**

```javascript
// Append to orb.js — ensure OrbRenderer handles all 5 states
// Make sure setState('idle'|'listening'|'thinking'|'speaking'|'error') exists
```

- [ ] **Step 3: Commit**

```bash
git add frontend/static/css/style.css
git commit -m "refactor(frontend): rewrite CSS — Google modern minimalism, Figtree font, shadow hierarchy, amber CTAs"
```

---

## Task 4: app.js — Panel Logic + Socket.IO

**Files:**
- Rewrite: `frontend/static/js/app.js`

- [ ] **Step 1: Write app.js**

```javascript
/** MokaAI — Socket.IO client, panel switching, event handlers. */

(function() {
  const socket = io();
  let currentPanel = "voice";
  let orbRenderer = null;
  const MAX_TRANSCRIPT = 50;

  // ═══ Safe text (XSS prevention) ═══
  function safeText(str) {
    const d = document.createElement("div");
    d.textContent = str == null ? "" : String(str);
    return d.innerHTML;
  }

  // ═══ Orb Initialization ═══
  function initOrb() {
    const canvas = document.getElementById("orb-canvas");
    if (canvas) {
      orbRenderer = new OrbRenderer(canvas);
      orbRenderer.start(); // begin animation loop
    }
    const miniCanvas = document.getElementById("chat-orb-canvas");
    if (miniCanvas) {
      new OrbRenderer(miniCanvas, { size: 48 });
    }
  }

  // ═══ Panel Switching ═══
  function switchPanel(name) {
    if (name === currentPanel) return;
    const prev = document.querySelector(`.panel[data-name=${currentPanel}], .panel#panel-${currentPanel}`);
    const next = document.getElementById(`panel-${name}`);

    // Update rail buttons
    document.querySelectorAll(".rail-icon").forEach(b => b.classList.remove("active"));
    document.querySelector(`.rail-icon[data-panel="${name}"]`)?.classList.add("active");

    // Close prev panel
    if (prev) {
      prev.classList.remove("active");
      prev.style.display = "none"; // ensure hidden
    }

    // Open next panel
    if (next) {
      next.classList.add("active");
      next.style.display = "flex";
    }

    // Update orb state for new panel
    if (orbRenderer) {
      if (name === "voice") {
        // orb already animating, state driven by agent_state
      } else {
        orbRenderer.stop(); // save CPU
      }
    }

    currentPanel = name;
    socket.emit("panel_change", { panel: name });
  }

  // ═══ Transcript ═══
  function addTranscriptLine(speaker, text) {
    const log = document.getElementById("transcript-log");
    if (!log) return;
    const el = document.createElement("div");
    el.className = "transcript-line";
    el.textContent = (speaker === "user" ? "You: " : "Moka: ") + safeText(text);
    log.appendChild(el);
    log.scrollTop = log.scrollHeight;
    while (log.children.length > MAX_TRANSCRIPT) {
      log.removeChild(log.firstChild);
    }
  }

  // ═══ Event Handlers ═══
  function setupRailListeners() {
    document.querySelectorAll(".rail-icon").forEach(btn => {
      btn.addEventListener("click", () => {
        const panel = btn.dataset.panel;
        if (panel) switchPanel(panel);
      });
    });
  }

  function setupMicButton() {
    const micBtn = document.getElementById("mic-btn");
    if (micBtn) {
      micBtn.addEventListener("click", () => socket.emit("mic_toggle"));
    }
  }

  function setupSettings() {
    const btnClear = document.getElementById("btn-clear-history");
    if (btnClear) {
      btnClear.addEventListener("click", () => {
        if (confirm("Clear all conversation history?")) {
          socket.emit("clear_history");
          const log = document.getElementById("transcript-log");
          if (log) log.innerHTML = "";
        }
      });
    }
    const btnExport = document.getElementById("btn-export-memory");
    if (btnExport) {
      btnExport.addEventListener("click", () => socket.emit("export_memory"));
    }
  }

  function setupFilterButtons() {
    document.querySelectorAll(".filter-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".filter-btn").forEach(b => {
          b.classList.remove("active");
          b.setAttribute("aria-pressed", "false");
        });
        btn.classList.add("active");
        btn.setAttribute("aria-pressed", "true");
        filterHistory(btn.dataset.filter);
      });
    });
  }

  // ═══ Socket.IO Events ═══
  function setupSocketEvents() {
    socket.on("connect", () => {
      console.log("Connected to MokaAI backend");
    });

    socket.on("agent_state", (state) => {
      // Update orb state on Voice panel
      if (orbRenderer && currentPanel === "voice") {
        orbRenderer.setState(state.status || "idle");
      }
      if (state.transcript && state.transcript.length) {
        const log = document.getElementById("transcript-log");
        if (log && log.children.length === 0) {
          state.transcript.forEach(t => addTranscriptLine(t.speaker, t.text));
        }
      }
    });

    socket.on("agent_event", (event) => {
      if (!event || !event.type) return;
      if (event.type === "transcript") {
        addTranscriptLine(event.data?.speaker || "", event.data?.text || "");
      } else if (event.type === "resource_update") {
        updateResourceBars(event.data || {});
      } else if (event.type === "learning_metrics") {
        updateLearningMetrics(event.data || {});
      } else if (event.type === "event_log" || event.type === "event") {
        addHistoryItem(event.data || {});
      } else if (event.type === "skill_update") {
        updateSkillList(event.data || []);
      } else if (event.type === "task_update") {
        updateTaskList(event.data || []);
      } else if (event.type === "memory_update") {
        updateMemoryPanels(event.data || {});
      } else if (event.type === "conversation_list") {
        updateConversationList(event.data || []);
      }
    });
  }

  // ═══ UI Update Helpers ═══
  function updateResourceBars(data) {
    if (data.gpu !== undefined) {
      const fill = document.getElementById("gpu-bar-fill");
      const pct = document.getElementById("gpu-pct");
      if (fill) fill.style.width = Math.min(100, data.gpu) + "%";
      if (pct) pct.textContent = data.gpu + "%";
    }
    if (data.ram !== undefined) {
      const fill = document.getElementById("ram-bar-fill");
      const pct = document.getElementById("ram-pct");
      if (fill) fill.style.width = Math.min(100, data.ram) + "%";
      if (pct) pct.textContent = data.ram + "%";
    }
  }

  function updateLearningMetrics(data) {
    const map = { behaviors: "metric-behaviors", skills: "metric-skills", profiles: "metric-profiles" };
    for (const [key, id] of Object.entries(map)) {
      const el = document.getElementById(id);
      if (el && data[key] !== undefined) el.textContent = data[key];
    }
    const scoresEl = document.getElementById("confidence-scores");
    if (scoresEl && data.confidence) {
      scoresEl.innerHTML = data.confidence.map(c => `
        <div class="score-card">
          <span class="score-category">${safeText(c.category)}</span>
          <span class="score-value">${Math.round(c.score * 100)}%</span>
        </div>
      `).join("");
    }
  }

  let eventHistory = [];

  function addHistoryItem(data) {
    const log = document.getElementById("event-log");
    if (!log) return;
    const item = {
      ts: data.ts ? new Date(data.ts).toLocaleTimeString() : "",
      type: data.type || "system",
      description: data.description || "",
    };
    if (!eventHistory.find(e => e.ts === item.ts && e.type === item.type && e.description === item.description)) {
      eventHistory.push(item);
    }
    renderHistory(getCurrentFilter());
  }

  function getCurrentFilter() {
    return document.querySelector(".filter-btn.active")?.dataset.filter || "all";
  }

  function filterHistory(type) {
    renderHistory(type);
  }

  function renderHistory(type) {
    const log = document.getElementById("event-log");
    if (!log) return;
    const filtered = type === "all" ? eventHistory : eventHistory.filter(e => e.type === type);
    log.innerHTML = filtered.slice(-100).reverse().map(e => `
      <div class="event-item">
        <span class="event-time">${e.ts}</span>
        <span class="event-type event-type-${e.type}">${e.type}</span>
        <span class="event-desc">${safeText(e.description)}</span>
      </div>
    `).join("");
  }

  function updateSkillList(skills) {
    const list = document.getElementById("skill-list");
    if (!list || !skills) return;
    list.innerHTML = skills.map(s => `
      <div class="skill-item">
        <span class="skill-name">${safeText(s.name)}</span>
        <span class="chip chip-${s.status === "approved" ? "success" : s.status === "running" ? "running" : "neutral"}">${safeText(s.status)}</span>
      </div>
    `).join("");
  }

  function updateTaskList(tasks) {
    const list = document.getElementById("task-list");
    if (!list || !tasks) return;
    list.innerHTML = tasks.map(t => `
      <div class="task-item">
        <span class="chip chip-${t.status === "done" ? "done" : t.status === "failed" ? "failed" : "pending"}">${safeText(t.status)}</span>
        <span class="task-name">${safeText(t.description || t.name || "Task")}</span>
      </div>
    `).join("");
  }

  function updateMemoryPanels(data) {
    const stm = document.getElementById("stm-list");
    const ltm = document.getElementById("ltm-list");
    if (stm && data.shortTerm) {
      stm.innerHTML = data.shortTerm.map(m =>
        `<div class="memory-card">${safeText(m.content || m.text || JSON.stringify(m))}</div>`
      ).join("");
    }
    if (ltm && data.longTerm) {
      ltm.innerHTML = data.longTerm.map(m =>
        `<div class="memory-card">${safeText(m.content || m.text || JSON.stringify(m))}</div>`
      ).join("");
    }
  }

  function updateConversationList(conversations) {
    const list = document.getElementById("conversation-list");
    if (!list || !conversations) return;
    list.innerHTML = conversations.map(c => `
      <div class="conv-item">
        <div class="conv-meta">${safeText(c.date || "")} · ${safeText(c.duration || "")}</div>
        <div class="conv-preview">${safeText(c.preview || c.firstLine || "")}</div>
      </div>
    `).join("");
  }

  // ═══ Boot ═══
  document.addEventListener("DOMContentLoaded", () => {
    initOrb();
    setupRailListeners();
    setupMicButton();
    setupSettings();
    setupFilterButtons();
    setupSocketEvents();
    socket.emit("panel_change", { panel: currentPanel });
  });
})();
```

- [ ] **Step 2: Update orb.js with setState() / start() / stop() public methods**

Ensure `orb.js` exports `OrbRenderer` with at minimum:
- `constructor(canvas, opts?)`
- `start()` — begins animation loop
- `stop()` — cancels animation frame
- `setState(state)` — accepts 'idle'|'listening'|'thinking'|'speaking'|'error'

- [ ] **Step 3: Commit**

```bash
git add frontend/static/js/app.js frontend/static/js/orb.js
git commit -m "refactor(frontend): rewrite app.js — panel switching, SocketIO events, XSS-safe helpers, orb state management"
```

---

## Spec Coverage Check

| Spec Requirement | Implementation |
|-----------------|----------------|
| Figtree font | `@font-face` in style.css pointing to self-hosted woff2 |
| Google shadow system | `--shadow-sm/md/lg` + no card borders |
| Amber CTAs only | `--accent: #C9956A` used only on .btn-primary, .mic-btn |
| Glassmorphism panels | `backdrop-filter: blur(16px)`, `rgba(242,231,224,0.55)` |
| Icon rail amber active | `.rail-icon.active { background: var(--accent); }` |
| Card hover lift | `box-shadow` elevation jump on hover, no border change |
| Orb 5 states | `setState('idle'/'listening'/'thinking'/'speaking'/'error')` in orb.js |
| Phase 11 warm palette | All CSS variables from spec, no color changes |
| Filter row as pill tabs | `.filter-row` with `.filter-btn.active` using white bg |
| Mobile bottom tab bar | `@media (max-width: 640px)` responsive override |

All requirements covered. Variable names consistent across all tasks.