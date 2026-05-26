/** MokaAI App — SocketIO client, panel switching, event handlers. */

(function() {
    const socket = io();
    let currentPanel = "voice";
    let orbRenderer = null;
    const transcripts = [];  // { speaker, text, ts }

    // ─── Safe text helper (XSS prevention) ──────────────────────────────
    function safeText(str) {
        const d = document.createElement("div");
        d.textContent = str == null ? "" : String(str);
        return d.innerHTML;
    }

    // ─── Orb Initialization ──────────────────────────────────────────────
    function initOrb() {
        const canvas = document.getElementById("orb-canvas");
        if (!canvas) return;
        orbRenderer = new OrbRenderer(canvas);
        canvas.addEventListener("click", () => {
            socket.emit("mic_toggle");
        });
        // Mini orb on chat panel
        const miniCanvas = document.getElementById("chat-orb-canvas");
        if (miniCanvas && miniCanvas !== canvas) {
            new OrbRenderer(miniCanvas);
        }
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
        if (state.transcript && state.transcript.length) {
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
        } else if (event.type === "event_log" || event.type === "event") {
            addEventLogItem(event.data || event);
        } else if (event.type === "skill_update") {
            updateSkillList(event.data);
        } else if (event.type === "task_update") {
            updateTaskList(event.data);
        } else if (event.type === "memory_update") {
            updateMemoryPanels(event.data);
        } else if (event.type === "conversation_list") {
            updateConversationList(event.data);
        }
    });

    // ─── UI Update Helpers ──────────────────────────────────────────────
    function updateResourceBars(data) {
        if (data.gpu !== undefined) {
            const bar = document.getElementById("gpu-bar");
            if (bar) {
                bar.querySelector(".bar-fill").style.width = Math.min(100, data.gpu) + "%";
                const pct = document.getElementById("gpu-pct");
                if (pct) pct.textContent = data.gpu + "%";
            }
        }
        if (data.ram !== undefined) {
            const bar = document.getElementById("ram-bar");
            if (bar) {
                bar.querySelector(".bar-fill").style.width = Math.min(100, data.ram) + "%";
                const pct = document.getElementById("ram-pct");
                if (pct) pct.textContent = data.ram + "%";
            }
        }
    }

    function updateLearningMetrics(data) {
        const map = { behaviors: "metric-behaviors", skills: "metric-skills", profiles: "metric-profiles" };
        for (const [key, id] of Object.entries(map)) {
            const el = document.getElementById(id);
            if (el && data[key] !== undefined) el.textContent = data[key];
        }
        // Show confidence scores
        const scoresEl = document.getElementById("confidence-scores");
        if (scoresEl && data.confidence) {
            scoresEl.innerHTML = data.confidence.map(c =>
                `<div class="card"><span>${c.category}</span><span>${(c.score * 100).toFixed(0)}%</span></div>`
            ).join("");
        }
    }

    function addEventLogItem(data) {
        const log = document.getElementById("event-log");
        if (!log) return;
        const activeFilter = document.querySelector(".filter-btn.active")?.dataset.filter || "all";
        const eventType = data.type || "system";
        if (activeFilter !== "all" && eventType !== activeFilter) return;
        const item = document.createElement("div");
        item.className = "event-item";
        const ts = data.ts ? new Date(data.ts).toLocaleTimeString() : "";
        item.innerHTML = `<span class="event-time">${ts}</span><span class="event-type">${safeText(eventType)}</span>${safeText(data.description || "")}`;
        log.insertBefore(item, log.firstChild);
        while (log.children.length > 100) log.removeChild(log.lastChild);
    }

    function filterEvents(type) {
        // Filter is applied in addEventLogItem check
    }

    function updateSkillList(skills) {
        const list = document.getElementById("skill-list");
        if (!list || !skills) return;
        list.innerHTML = skills.map(s => `
            <div class="skill-item">
                <span class="skill-name">${safeText(s.name)}</span>
                <span class="skill-badge badge-${safeText(s.status)}">${safeText(s.status)}</span>
            </div>
        `).join("");
    }

    function updateTaskList(tasks) {
        const list = document.getElementById("task-list");
        if (!list || !tasks) return;
        list.innerHTML = tasks.map(t => `
            <div class="task-item">
                <span class="task-chip chip-${safeText(t.status)}">${safeText(t.status)}</span>
                <span>${safeText(t.description || t.name || "Task")}</span>
            </div>
        `).join("");
    }

    function updateMemoryPanels(data) {
        const stm = document.getElementById("stm-list");
        const ltm = document.getElementById("ltm-list");
        if (stm && data.shortTerm) {
            stn.innerHTML = data.shortTerm.map(m =>
                `<div class="card">${safeText(m.content || m.text || JSON.stringify(m))}</div>`
            ).join("");
        }
        if (ltm && data.longTerm) {
            ltm.innerHTML = data.longTerm.map(m =>
                `<div class="card">${safeText(m.content || m.text || JSON.stringify(m))}</div>`
            ).join("");
        }
    }

    function updateConversationList(conversations) {
        const list = document.getElementById("conversation-list");
        if (!list || !conversations) return;
        list.innerHTML = conversations.map(c => `
            <div class="conv-item">
                <div class="conv-meta">${safeText(c.date || "")} — ${safeText(c.duration || "")}</div>
                <div class="conv-preview">${safeText(c.preview || c.firstLine || "")}</div>
            </div>
        `).join("");
    }

    // ─── Boot ───────────────────────────────────────────────────────────
    document.addEventListener("DOMContentLoaded", () => {
        initOrb();
        socket.emit("panel_change", { panel: "voice" });
    });
})();