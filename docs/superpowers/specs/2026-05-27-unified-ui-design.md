# Phase 13 — Installer + Main App UI Redesign

**Date:** 2026-05-27
**Phase:** 13
**Status:** Approved

---

## Concept & Vision

The installer is a calm, focused utility — one task, one screen, no clutter. The main app is a warm, spacious environment where information is easy to scan and the orb gives life to otherwise static panels. Both share a soul (warm sand/espresso, glassmorphism) but speak different languages: the wizard is a focused conversation; the app is a rich dashboard.

---

## Part 1: Installer Wizard — PyWebView Standalone

### Color & Typography
```css
/* Same Phase 11 warm palette */
--bg-base: #F2EBE0;
--bg-panel: rgba(242, 231, 224, 0.55);
--bg-card: rgba(255, 248, 240, 0.7);
--text-primary: #2C1A0E;
--text-secondary: #6B4C3B;
--accent-sand: #D4B896;
--accent-amber: #C9956A;
--orb-idle: #D9CFC4;
--border-subtle: rgba(212, 184, 150, 0.35);
```

Typography for the wizard:
- **Headings:** `Figtree` 600 weight — clean, warm geometric humanist
- **Body/Labels:** `Figtree` 400/500 — readable, non-generic
- **Monospace (values):** `Cascadia Code` — VRAM, model sizes, package names
- No decorative display font — the wizard is utilitarian, not editorial

### Navigation Model
```
┌─────────────────────────────────────────┐
│  ○──────○──────○──────○──────○         │  Step dots: 5 steps
│  Welcome HW Models Install Done        │
├─────────────────────────────────────────┤
│                                         │
│           [ SCREEN CONTENT ]           │
│                                         │
├─────────────────────────────────────────┤
│                           [Back] [Next] │  Buttons always visible
└─────────────────────────────────────────┘
```

Non-linear: any step dot clickable to go back; "Back" button on all steps; state preserved when revisiting.

### Screen Flow

**Step 1 — Welcome**
- Centered single-column, generous vertical padding
- Moka AI wordmark (Figtree 700, 28px) + version tag
- Decorative orb at top (idle animation, muted)
- Installation path: text input + "Browse" button → native OS folder picker via PyWebView
- Path validation inline (exists? writable?)
- CTA: "Get Started" (amber fill, primary)

**Step 2 — Hardware Scan**
- Auto-triggers on page load
- Orb transitions to "thinking" state
- Hardware cards animate in one by one (stagger 120ms):
  - CPU card: chip icon + "Processor" label + detected value
  - GPU card: GPU icon + "Graphics" label + value (amber for NVIDIA, brand color coding)
  - VRAM bar: visual progress bar showing detected VRAM
  - RAM card: icon + "Memory" label + value
  - OS card: icon + OS name + build
- "Rescan" secondary button (top-right corner)
- "Continue" activates when scan done

**Step 3 — Model Selection**
- Shows detected VRAM badge: "Recommended for 8 GB VRAM"
- Three model rows:
  - **Base Model** (coding + reasoning): icon + dropdown of tiered models + size pill
  - **Image Model** (text→image): icon + dropdown + size pill
  - **Voice Model** (TTS + STT): icon + dropdown + size pill
- Each dropdown pre-selected to recommended model
- Size pills color-coded: green=small, amber=medium, red=large
- Total disk estimate shown below: "Total: ~6.2 GB"
- Model info tooltip on hover (? icon next to each type)
- "Back" + "Install →" nav

**Step 4 — Installing**
- Orb enters "speaking" state (animated rings)
- Full-width progress bar (amber fill, sand track)
- Percentage shown large top-right of bar
- Package list with status badges:
  - Sand pill = pending
  - Amber pill + spin icon = installing
  - Green pill = done
  - Red pill = failed (+ error tooltip)
- Collapsible log pane (toggle button, default expanded)
- Status header: "Installing packages..." / "Configuring..." / "Setting up shortcuts..."
- On failure: error card with package name + "Retry" button

**Step 5 — Complete**
- Orb enters "speaking" state (warm golden)
- Large checkmark icon (amber)
- "Moka AI is ready" heading
- Shortcut path shown (subtle)
- "Create Desktop Shortcut" checkbox (default ON)
- "Create Start Menu shortcut" checkbox (default ON)
- "Launch Moka AI now" checkbox (default ON)
- CTA: "Finish Setup" → creates shortcuts + launches + closes wizard

### Tech Stack
- **Runtime:** PyWebView 4.x — OS-native webview (no bundled Chromium), ~2MB overhead
- **Backend:** Python 3 — all `installer.core.*` logic unchanged, single `WizardState` dataclass
- **Frontend:** HTML/CSS/JS in `installer_wizard/` directory (loaded by PyWebView as local file)
- **Fonts:** Google Fonts (Figtree + Cascadia Code) via embedded base64 or bundled .woff2
- **Build:** PyInstaller → single `.exe`

### PyWebView JS↔Python Bridge
```python
class WizardAPI:
    def get_state(self):           # JS polls or receives state
    def set_install_path(self, p): # JS calls on path change
    def scan_hardware(self):       # JS triggers scan
    def get_models(self, vram_gb): # JS loads model options
    def set_models(self, base, image, voice):
    def start_install(self):       # JS triggers install, runs in thread
    def get_install_progress(self): # JS polls for SSE/progress dict
    def create_shortcuts(self, desktop, startmenu):
    def launch_and_close(self):
```

### State Machine (Python)
```
WELCOME → HARDWARE → MODELS → INSTALLING → COMPLETE
   ↑_________|_________|_________|___________|
   (back navigation via step dots or Back button)
```

All state in one `WizardState` dataclass, persisted across back-navigation.

---

## Part 2: Main App — Google Modern Minimalism UX

### Design Philosophy
Google modern minimalism: **generous whitespace, shadow-depth hierarchy, typographic rhythm, restrained animation**. Warm Phase 11 palette as the paint.

Key Google UX principles applied:
1. **White space is the layout** — panels never feel crowded
2. **Elevation = importance** — subtle `box-shadow` layers rather than borders to show hierarchy
3. **Typography first** — clear size/rhythm hierarchy, not decorative elements
4. **Color as signal** — amber only on CTAs and active states, rest is neutral
5. **Smooth but brief** — transitions 150-250ms, no bounce or delay

### Color & Typography
```css
:root {
    --bg-base: #F2EBE0;           /* warm sand background */
    --bg-panel: rgba(242, 231, 224, 0.55);
    --bg-card: rgba(255, 248, 240, 0.7);
    --text-primary: #2C1A0E;      /* deep espresso */
    --text-secondary: #6B4C3B;    /* soft espresso */
    --text-tertiary: #9C7A6A;     /* lighter espresso for meta */
    --accent: #C9956A;            /* amber — CTAs only */
    --accent-hover: #B8845A;       /* darker amber */
    --border-subtle: rgba(212, 184, 150, 0.25);
    --shadow-sm: 0 1px 3px rgba(44, 26, 14, 0.08);
    --shadow-md: 0 4px 12px rgba(44, 26, 14, 0.12);
    --shadow-lg: 0 8px 24px rgba(44, 26, 14, 0.16);
    --radius-sm: 8px;
    --radius-md: 12px;
    --radius-lg: 16px;
}
```

**Font: Figtree** (Google Fonts) — the actual font used by Google's modern UI.
- Display: Figtree 600, 24-32px
- Heading: Figtree 600, 18-20px
- Body: Figtree 400, 14px
- Label/micro: Figtree 500, 11-12px, letter-spacing 0.04em, uppercase
- Mono: Cascadia Code 400, 13px

### Layout: Icon Rail + Panel Area
```
┌──────┬────────────────────────────────────────┐
│      │                                        │
│ Rail │           Panel Content                │
│ 56px │                                        │
│      │   ← panels use --shadow-md cards      │
│      │     generous padding (24px+)           │
│      │     generous gap (16px+)               │
└──────┴────────────────────────────────────────┘
```

**Rail** (left, 56px wide):
- Fixed left, not scrollable
- 9 icon buttons, 40×40px, pill radius on hover
- Active: amber accent background, not full-height fill
- Tooltip on hover (label appears to the right of icon)
- Bottom-anchored settings icon

**Panel area:**
- Fills remaining width, scrollable per panel
- Each panel's content: generous 28px padding, 16-20px gaps
- No panel background fill — panel IS the background (glassmorphism backdrop)
- Cards use `background: var(--bg-card)` + `--shadow-sm` + `--radius-md`
- Active panel slides in (translateX, 200ms ease)

### Card System (Google-style elevation)
```css
.card {
    background: var(--bg-card);        /* slightly lighter than panel */
    border: 1px solid transparent;       /* no border — shadow only */
    box-shadow: var(--shadow-sm);        /* Google: shadow over border */
    border-radius: var(--radius-md);     /* 12px */
    padding: 16px;
    transition: box-shadow 0.15s ease;
}
.card:hover {
    box-shadow: var(--shadow-md);        /* Google hover: lift by 1 level */
}
.card-elevated { box-shadow: var(--shadow-md); }
```

### Google-Style Component Updates

**Buttons**
```css
.btn-primary {
    background: var(--accent);
    color: #fff;
    padding: 10px 20px;
    border-radius: var(--radius-sm);  /* 8px — not pill */
    font: Figtree 500 14px;
    box-shadow: var(--shadow-sm);
    transition: background 0.15s, box-shadow 0.15s, transform 0.1s;
}
.btn-primary:hover {
    background: var(--accent-hover);
    box-shadow: var(--shadow-md);
    transform: translateY(-1px);
}
.btn-primary:active { transform: translateY(0); box-shadow: var(--shadow-sm); }

.btn-ghost {
    background: transparent;
    color: var(--text-primary);
    padding: 8px 16px;
    border-radius: var(--radius-sm);
    /* no border, no shadow — pure ghost */
}
.btn-ghost:hover { background: rgba(44, 26, 14, 0.06); }
```

**Inputs / Selects**
```css
.input {
    background: white;
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-sm);
    padding: 10px 12px;
    font: Figtree 400 14px;
    color: var(--text-primary);
    box-shadow: inset 0 1px 2px rgba(44, 26, 14, 0.06); /* subtle inner shadow */
    transition: border-color 0.15s, box-shadow 0.15s;
}
.input:focus {
    outline: none;
    border-color: var(--accent);
    box-shadow: 0 0 0 3px rgba(201, 149, 106, 0.15);
}
```

**Badges / Chips / Status**
```css
.chip {
    display: inline-flex;
    align-items: center;
    padding: 3px 10px;
    border-radius: 20px;
    font: Figtree 500 11px;
    letter-spacing: 0.03em;
    text-transform: uppercase;
}
/* Status chips: minimal, color-only signals */
.chip-success  { background: rgba(46, 192, 124, 0.15); color: #2a7a50; }
.chip-warning  { background: rgba(213, 168, 75, 0.15);  color: #7a5a20; }
.chip-error    { background: rgba(122, 74, 58, 0.15);   color: #7A4A3A; }
.chip-neutral  { background: rgba(212, 184, 150, 0.2);  color: var(--text-secondary); }
```

**Progress Bars / Bars**
```css
.bar-track {
    height: 6px;
    background: rgba(212, 184, 150, 0.3);
    border-radius: 3px;
    overflow: hidden;
}
.bar-fill {
    height: 100%;
    background: var(--accent);
    border-radius: 3px;
    transition: width 0.5s ease;
}
```

**Filter / Tab rows**
```css
.filter-row {
    display: flex;
    gap: 6px;
    padding: 4px;
    background: rgba(212, 184, 150, 0.15);
    border-radius: var(--radius-sm);
}
.filter-btn {
    padding: 5px 12px;
    border-radius: 6px;
    font-size: 12px;
    color: var(--text-secondary);
    transition: background 0.15s, color 0.15s;
}
.filter-btn.active {
    background: white;
    color: var(--text-primary);
    box-shadow: var(--shadow-sm);
}
/* Clean alternative: pill tabs with bottom border indicator */
```

### Orb State Mapping (Main App)
| Panel | Orb State | Visual |
|-------|-----------|--------|
| Voice (idle) | `--orb-idle` | Slow breathing pulse |
| Voice (listening) | `--orb-listening` | Faster pulse + wave effect |
| Voice (thinking) | `--orb-thinking` | Deep slow pulse |
| Voice (speaking) | `--orb-speaking` | Golden pulse + rings |
| Chat | static `--orb-idle` | Small orb, top of panel |
| Memory, Skills, Tasks | static muted | No orb or small static |
| Resource, Learning | static | No orb |
| History | static | No orb |
| Settings | static | No orb |

### Motion Guidelines
- Page transitions: 200ms ease, opacity + translateX(8px)
- Card hover: 150ms ease (shadow lift only, no scale)
- Button press: 100ms ease (translateY 1px)
- Progress bars: 500ms ease for fill changes
- Staggered list items: 50ms delay between items, 150ms fade+translateY
- No spring/bounce physics — Google is restrained, not playful

### File Changes (Main App)

| Action | File |
|--------|------|
| Rewrite | `frontend/static/css/style.css` |
| Rewrite | `frontend/static/js/app.js` |
| Rewrite | `frontend/templates/index.html` |
| Add | `frontend/static/css/fonts/` (Figtree woff2) |

### Component Coverage

| Component | Description |
|-----------|-------------|
| Orb canvas | `orb.js` — all 5 state colors, pulse timing from spec, particle effects |
| Icon rail | 9 icon buttons, amber active state, tooltips |
| Glass panel | `background: var(--bg-panel)`, `backdrop-filter: blur(16px)` — Phase 11 spec |
| Card | elevation-based shadow (no border), 12px radius |
| Primary button | amber fill, white text, shadow lift on hover |
| Ghost button | transparent, hover reveals subtle fill |
| Input/select | white bg, inner shadow, amber focus ring |
| Status chip | color-only pill, no icon (unless error requires it) |
| Progress bar | thin (6px), amber fill, sand track |
| Metric card | large number + small label below, centered |
| Transcript line | speaker label + text, newest at bottom, fade older |
| Event item | timestamp chip + type badge + description text |

---

## Acceptance Criteria

### Installer Wizard
- [ ] PyWebView app launches from `.exe` on Windows without browser dependencies
- [ ] All 5 steps accessible via step dots and Back/Next buttons
- [ ] Hardware scan auto-triggers and populates 5 hardware cards with staggered animation
- [ ] Model dropdowns show only models matching detected VRAM tier, pre-selected
- [ ] Path picker uses OS native folder dialog
- [ ] Install progress streams package status in real-time
- [ ] Finish screen creates Desktop + Start Menu shortcuts (Windows) and launches Moka AI
- [ ] Warm sand/espresso palette throughout
- [ ] All 3 new fonts load (Figtree, Cascadia Code)
- [ ] No bundled Chromium — uses OS WebView2

### Main App
- [ ] `frontend/` served by `backend/app.py` at `/` with full Phase 11 warmth
- [ ] Figtree font throughout (headings + body), Cascadia Code for mono
- [ ] Icon rail with 9 panels, amber active indicator
- [ ] Glassmorphism panels: `backdrop-filter: blur(16px)`, `rgba(242, 231, 224, 0.55)`
- [ ] All cards use shadow elevation instead of borders
- [ ] Primary buttons amber fill, hover lifts shadow, press depresses
- [ ] Orb on Voice panel with all 5 state colors and animations
- [ ] Chat panel with static orb + conversation list
- [ ] Memory/Skills/Tasks/Resources/Learning/History/Settings panels render data from SocketIO
- [ ] Activity History filter row as pill tabs
- [ ] All transitions ≤ 250ms
- [ ] Mobile responsive (single column, rail collapses to bottom tab bar)