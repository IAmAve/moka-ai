/**
 * Moka AI — App JS
 * Socket.IO client, panel switching, orb coordination, event handlers.
 *
 * Socket.IO events received from backend:
 *   message        → new chat message {role, content, ts}
 *   voice_transcript → {speaker, text, ts}
 *   orb_state      → {state}  idle|listening|thinking|speaking|error
 *   memory_update  → {short_term: [], long_term: []}
 *   skill_update   → {skills: [{name, description, status}]}
 *   task_update    → {tasks: [{id, title, priority, completed, ts}]}
 *   resource_update → {gpu_pct, ram_pct, active_jobs}
 *   learning_update → {behaviors, skills, profiles}
 *   history_events  → [{type, text, ts}]
 */
(function() {
  'use strict';

  // ── State ─────────────────────────────────────────────────
  let currentPanel = 'chat';
  const messages = [];       // chat messages for current session
  const conversations = []; // conversation history entries
  let orbVoiceState = 'IDLE';
  let orbVoice = null;

  // ── Safe text helper ───────────────────────────────────────
  function safeText(str) {
    const d = document.createElement('div');
    d.textContent = str == null ? '' : String(str);
    return d.innerHTML;
  }

  // ── Socket.IO ─────────────────────────────────────────────
  const socket = io({ path: '/socket.io/', transports: ['websocket', 'polling'] });

  socket.on('connect', () => {
    console.log('Socket connected', socket.id);
  });
  socket.on('disconnect', () => {
    console.log('Socket disconnected');
  });

  // Incoming events
  socket.on('message', data => {
    messages.push(data);
    renderMessages();
  });
  socket.on('voice_transcript', data => {
    appendTranscript(data.speaker, data.text, data.ts);
  });
  socket.on('orb_state', data => {
    setOrbVoiceState(data.state);
  });
  socket.on('memory_update', data => {
    renderMemory(data);
  });
  socket.on('skill_update', data => {
    renderSkills(data);
  });
  socket.on('task_update', data => {
    renderTasks(data);
  });
  socket.on('resource_update', data => {
    renderResources(data);
  });
  socket.on('learning_update', data => {
    renderLearning(data);
  });
  socket.on('history_events', data => {
    renderHistory(data);
  });

  // ── Panel Switching ────────────────────────────────────────
  function switchPanel(name) {
    if (currentPanel === name) return;
    currentPanel = name;

    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    const panel = document.getElementById('panel-' + name);
    if (panel) panel.classList.add('active');

    document.querySelectorAll('.rail-icon').forEach(b => {
      b.classList.toggle('active', b.dataset.panel === name);
    });

    // Update orb for voice panel
    if (name === 'voice' && orbVoice) startOrbVoice();
  }

  document.querySelectorAll('.rail-icon').forEach(btn => {
    btn.addEventListener('click', () => switchPanel(btn.dataset.panel));
  });

  // ── Orb Voice ─────────────────────────────────────────────
  function initOrbVoice() {
    const canvas = document.getElementById('orb-voice');
    if (!canvas) return;
    orbVoice = createOrbRenderer(canvas, 'IDLE');
  }

  function startOrbVoice() {
    if (orbVoice) orbVoice.start();
  }

  function setOrbVoiceState(state) {
    orbVoiceState = state.toUpperCase();
    if (orbVoice) orbVoice.setState(orbVoiceState);

    // Update state label
    const label = document.getElementById('voice-state-label');
    if (label) {
      const map = { IDLE: 'Ready', LISTENING: 'Listening…', THINKING: 'Thinking…', SPEAKING: 'Speaking…', ERROR: 'Error' };
      label.textContent = map[orbVoiceState] || 'Ready';
    }
  }

  // Chat mini orb
  function initOrbChat() {
    const canvas = document.getElementById('orb-chat');
    if (!canvas) return;
    createOrbRenderer(canvas, 'IDLE');
  }

  // ── Chat ───────────────────────────────────────────────────
  function renderMessages() {
    const container = document.getElementById('chat-messages');
    if (!container) return;
    container.innerHTML = messages.map(m => `
      <div class="msg msg-${m.role === 'user' ? 'user' : m.role === 'error' ? 'error' : 'assistant'}">
        <span>${safeText(m.content)}</span>
        ${m.ts ? `<div class="msg-time">${fmtTime(m.ts)}</div>` : ''}
      </div>
    `).join('');
    container.scrollTop = container.scrollHeight;
  }

  document.getElementById('chat-send')?.addEventListener('click', sendChat);
  document.getElementById('chat-input')?.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChat(); }
  });

  function sendChat() {
    const input = document.getElementById('chat-input');
    const text = input?.value.trim();
    if (!text) return;
    input.value = '';
    socket.emit('message', { content: text });
  }

  // ── Voice ──────────────────────────────────────────────────
  const voiceBtn = document.getElementById('voice-push');
  if (voiceBtn) {
    voiceBtn.addEventListener('mousedown', () => { socket.emit('mic_start'); setOrbVoiceState('LISTENING'); });
    voiceBtn.addEventListener('mouseup',   () => { socket.emit('mic_stop');  setOrbVoiceState('THINKING'); });
    voiceBtn.addEventListener('mouseleave',()=> { socket.emit('mic_stop'); });
    voiceBtn.addEventListener('touchstart',e=> { e.preventDefault(); socket.emit('mic_start'); setOrbVoiceState('LISTENING'); }, { passive: false });
    voiceBtn.addEventListener('touchend',  e=> { e.preventDefault(); socket.emit('mic_stop'); setOrbVoiceState('THINKING'); }, { passive: false });
  }

  function appendTranscript(speaker, text, ts) {
    const container = document.getElementById('voice-transcript');
    if (!container) return;
    const isUser = speaker && speaker.toLowerCase().includes('user');
    const line = document.createElement('div');
    line.className = 'transcript-line';
    line.innerHTML = `
      <span class="transcript-speaker">${safeText(speaker || 'Moka')}</span>
      <div class="transcript-text${isUser ? ' user' : ''}">${safeText(text)}</div>
    `;
    container.appendChild(line);
    container.scrollTop = container.scrollHeight;
  }

  // ── Memory ─────────────────────────────────────────────────
  function renderMemory(data) {
    const el = document.getElementById('memory-content');
    if (!el) return;
    const all = [...(data.short_term || []), ...(data.long_term || [])];
    if (!all.length) {
      el.innerHTML = '<div class="empty-state">Your memories will appear here.</div>';
      return;
    }
    el.innerHTML = all.map(m => `
      <div class="memory-item">
        <div class="mem-type">${safeText(m.type || 'memory')}</div>
        <div>${safeText(m.content || m.text || '')}</div>
      </div>
    `).join('');
  }

  // ── Skills ──────────────────────────────────────────────────
  function renderSkills(data) {
    const el = document.getElementById('skills-grid');
    if (!el || !data?.skills) return;
    el.innerHTML = data.skills.map(s => `
      <div class="skill-card">
        <div class="skill-name">${safeText(s.name)}</div>
        <div class="skill-desc">${safeText(s.description || '')}</div>
        ${s.status ? `<span class="skill-badge">${safeText(s.status)}</span>` : ''}
      </div>
    `).join('');
  }

  // ── Tasks ──────────────────────────────────────────────────
  function renderTasks(data) {
    const el = document.getElementById('tasks-list');
    if (!el || !data?.tasks) return;
    el.innerHTML = data.tasks.map(t => `
      <div class="task-item">
        <div class="task-check${t.completed ? ' done' : ''}" data-id="${safeText(t.id)}"></div>
        <div class="task-body">
          <div class="task-title">${safeText(t.title)}</div>
          ${t.ts ? `<div class="task-meta">${fmtTime(t.ts)}</div>` : ''}
        </div>
        ${t.priority ? `<span class="task-priority ${t.priority}">${safeText(t.priority)}</span>` : ''}
      </div>
    `).join('');

    // Toggle completion
    el.querySelectorAll('.task-check').forEach(chk => {
      chk.addEventListener('click', () => {
        chk.classList.toggle('done');
        socket.emit('task_toggle', { id: chk.dataset.id });
      });
    });
  }

  // ── Resources ──────────────────────────────────────────────
  function renderResources(data) {
    const gpuPct = document.getElementById('gpu-pct');
    const ramPct = document.getElementById('ram-pct');
    const gpuFill = document.querySelector('#gpu-bar .bar-fill');
    const ramFill = document.querySelector('#ram-bar .bar-fill');

    if (data.gpu_pct != null) {
      const pct = Math.round(data.gpu_pct);
      if (gpuPct) gpuPct.textContent = pct + '%';
      if (gpuFill) { gpuFill.style.width = pct + '%'; gpuFill.className = 'bar-fill ' + (pct > 80 ? 'high' : pct > 50 ? 'medium' : 'low'); }
    }
    if (data.ram_pct != null) {
      const pct = Math.round(data.ram_pct);
      if (ramPct) ramPct.textContent = pct + '%';
      if (ramFill) { ramFill.style.width = pct + '%'; ramFill.className = 'bar-fill ' + (pct > 80 ? 'high' : pct > 50 ? 'medium' : 'low'); }
    }
  }

  // ── Learning ───────────────────────────────────────────────
  function renderLearning(data) {
    if (data.behaviors != null) {
      const el = document.getElementById('metric-behaviors');
      if (el) el.textContent = data.behaviors;
    }
    if (data.skills != null) {
      const el = document.getElementById('metric-skills');
      if (el) el.textContent = data.skills;
    }
    if (data.profiles != null) {
      const el = document.getElementById('metric-profiles');
      if (el) el.textContent = data.profiles;
    }
  }

  // ── History ───────────────────────────────────────────────
  let historyFilter = 'all';
  let allEvents = [];

  document.getElementById('history-filters')?.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#history-filters .filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      historyFilter = btn.dataset.filter;
      renderHistory({ events: allEvents });
    });
  });

  function renderHistory(data) {
    allEvents = data.events || [];
    const el = document.getElementById('activity-list');
    if (!el) return;
    const filtered = historyFilter === 'all' ? allEvents : allEvents.filter(e => e.type === historyFilter);
    if (!filtered.length) {
      el.innerHTML = '<div class="empty-state">No activity yet.</div>';
      return;
    }
    el.innerHTML = filtered.map(e => `
      <div class="event-item">
        <span class="event-time">${fmtTime(e.ts)}</span>
        <span class="event-badge badge-${e.type || 'system'}">${safeText(e.type || 'system')}</span>
        <span class="event-text">${safeText(e.text || '')}</span>
      </div>
    `).join('');
  }

  // ── Settings ───────────────────────────────────────────────
  document.getElementById('btn-clear-history')?.addEventListener('click', () => {
    if (confirm('Clear all chat history?')) socket.emit('clear_history');
  });
  document.getElementById('btn-export-memory')?.addEventListener('click', () => {
    socket.emit('export_memory');
  });

  // ── Helpers ────────────────────────────────────────────────
  function fmtTime(ts) {
    if (!ts) return '';
    const d = new Date(ts);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  // ── Boot ──────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', () => {
    initOrbVoice();
    initOrbChat();
    switchPanel('chat');  // Chat is first active panel
  });

})();