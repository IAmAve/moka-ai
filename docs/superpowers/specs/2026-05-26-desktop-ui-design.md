# Phase 11 — Desktop UI

> **For agentic workers:** Create implementation plan after spec approval using superpowers:writing-plans.

## Concept & Vision

A warm, minimal AI voice companion that feels like having a mentor present. The interface recedes — centered on an animated orb that breathes, pulses, and communicates state. Voice is primary; everything else is one tap away on a slim icon rail. The overall feeling: sand, glass, espresso, and ambient intelligence.

---

## Color Palette

All colors derive from a warm sand/espresso foundation:

| Token | Hex | Usage |
|-------|-----|-------|
| `--bg-base` | `#F2EBE0` | Page background |
| `--bg-panel` | `rgba(242, 231, 224, 0.55)` | Panel backgrounds (glassmorphism) |
| `--bg-card` | `rgba(255, 248, 240, 0.7)` | Card / input backgrounds |
| `--text-primary` | `#2C1A0E` | Deep espresso — headings, values |
| `--text-secondary` | `#6B4C3B` | Soft espresso — labels, meta |
| `--accent-sand` | `#D4B896` | Warm sand — borders, dividers |
| `--accent-amber` | `#C9956A` | Warm amber — interactive highlights |
| `--orb-idle` | `#D9CFC4` | Soft beige — idle orb |
| `--orb-listening` | `#E8A96B` | Warm sand amber — listening |
| `--orb-thinking` | `#4A2C17` | Deep espresso — thinking (dark orb) |
| `--orb-speaking` | `#F0D9A0` | Golden sand — speaking |
| `--orb-error` | `#7A4A3A` | Desaturated deep espresso — error |

---

## Orb — State Machine

The orb is a canvas-rendered circle with particle overlay. It communicates all agent states.

### States

| State | Orb Color | Orb Pulse | Particles |
|-------|-----------|-----------|-----------|
| Idle | `--orb-idle` | Slow breathing (3s cycle) | 2 orbit dots |
| Listening | `--orb-listening` | Faster pulse (1s cycle) | 2 orbit dots + wake burst on entry |
| Thinking | `--orb-thinking` | Slow deep pulse (2s cycle) | 2 orbit dots |
| Speaking | `--orb-speaking` | Bright pulse (0.8s cycle) | 2 orbit dots + speech rings |
| Error | `--orb-error` | Slow irregular pulse | Orbit dots freeze |

### Orb Colors (CSS)

```css
--orb-idle: #D9CFC4;
--orb-listening: #E8A96B;
--orb-thinking: #4A2C17;
--orb-speaking: #F0D9A0;
--orb-error: #7A4A3A;
```

### Transitions

State changes crossfade over **400ms**:
1. Previous pulse fades out (opacity 1→0), particle effect deactivates
2. Orb color transitions (CSS transition)
3. New state's pulse/animation fades in

No hard snaps.

### Particle System

| Particle | Trigger | Behavior |
|----------|---------|----------|
| Orbit dots | Always on | 2–3 small dots circling orb at different radii/speeds |
| Wake burst | On state entry (Listening→next state) | Brief outward spray, 8–12 particles, dissipates in 600ms |
| Speech rings | While Speaking | Concentric rings ripple outward every 1.2s, fade as they expand |

---

## Panels

### Voice Panel (Primary)

- Full-screen canvas with centered orb
- Live transcript scrolls below the orb (semi-transparent, auto-scroll)
- Transcript fades older messages (last 3 visible at full opacity)
- Tap orb to activate microphone (Listening state)
- Shows full conversation in progress; completed conversations are saved to Chat

### Chat Panel

- Orb at top (small, decorative — shows last known state as static)
- Scrollable list of past conversations beneath
- Each conversation item shows: date, duration, first line of transcript
- Tap to expand full conversation

### Memory Panel

- Agent memory view — short-term / long-term split
- Cards showing loaded context items
- "Inject" action to add memory to active conversation

### Skills Panel

- List of drafts and approved skills
- Status badges (draft / approved / running)
- Tap skill to view definition

### Task Queue Panel

- Ordered task list from TaskOrchestrator
- Drag to reorder
- Status chips: pending / running / done / failed
- Progress bar for running tasks

### Resource Monitor Panel

- GPU/RAM usage (from HardwareScanner data)
- Active generation jobs with progress
- Minimal — just numbers and simple bars

### Learning Dashboard Panel

- Metrics: behaviors learned, skills acquired, profiles tracked
- Confidence scores by category
- Trend sparklines if data is available

### Activity History Panel

- Timestamped event log from EventBus
- Filterable by type (chat, skill, task, system)
- Scrollable, newest first

### Settings Panel

- Voice settings (wake word, TTS voice, mic selection)
- Appearance (already minimal — no theme switching needed)
- Data management (clear history, export memory)
- About / version

---

## Navigation — Icon Rail

9 panel icons in a left-side vertical rail, 48px wide, full height.

```
┌────┐
│ 🎙  │ Voice (primary — always active at open)
│ 💬  │ Chat
│ 🧠  │ Memory
│ ⚡  │ Skills
│ 📋  │ Task Queue
│ 📊  │ Resource Monitor
│ 📈  │ Learning Dashboard
│ 🕐  │ Activity History
│ ⚙️  │ Settings
└────┘
```

- Soft beige background, accent-amber for active panel icon
- Tooltips on hover showing full name
- Active panel fills the content area to the right of the rail

---

## Glassmorphism

All panel backgrounds use:

```css
background: rgba(242, 231, 224, 0.55);
backdrop-filter: blur(16px);
border: 1px solid rgba(212, 184, 150, 0.35);
border-radius: 16px;
```

Cards within panels:

```css
background: rgba(255, 248, 240, 0.7);
backdrop-filter: blur(8px);
border: 1px solid rgba(212, 184, 150, 0.25);
border-radius: 12px;
```

---

## Typography

- **Font:** System stack — `-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif`
- **Headings:** `text-primary`, medium weight
- **Body:** `text-secondary`, regular weight
- **Monospace:** `'SF Mono', 'Cascadia Code', monospace` for technical values

---

## Acceptance Criteria

- [ ] Voice panel orb displays with correct idle color + orbit dots + breathing pulse
- [ ] State transitions animate smoothly (400ms crossfade) with particle effects per state
- [ ] All 9 panels accessible via icon rail
- [ ] Chat panel shows past conversations
- [ ] Memory, Skills, Task Queue, Resource Monitor, Learning Dashboard render their data
- [ ] Activity History shows events from EventBus
- [ ] Settings panel has working voice and data controls
- [ ] Glassmorphism applied to all panels
- [ ] Flask receives events via SocketIO and updates UI in real-time
- [ ] Flask serves static files for the UI