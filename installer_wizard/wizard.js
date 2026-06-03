// installer_wizard/wizard.js — Moka AI Installer Wizard JS
(function () {
  'use strict';

  // ===== Orb =====================================================
  const ORB = {
    IDLE:      { phase: 0,    color: '#D9CFC4', pulse: 1.0,  speed: 1.0  },
    LISTENING: { phase: 0.15, color: '#C9956A', pulse: 1.8,  speed: 1.4  },
    THINKING:  { phase: 0.3,  color: '#B8845A', pulse: 0.6,  speed: 0.7  },
    SPEAKING:  { phase: 0.5,  color: '#C9956A', pulse: 2.2,  speed: 2.0  },
    ERROR:     { phase: 0,    color: '#7A4A3A', pulse: 1.0,  speed: 0.8  },
  };

  function createOrb(canvas, state) {
    state = state || 'IDLE';
    const ctx = canvas.getContext('2d');
    let t = 0;
    let raf;

    function draw() {
      const cfg = ORB[state] || ORB.IDLE;
      const cx = canvas.width / 2, cy = canvas.height / 2;
      const baseR = cx - 8;

      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Ambient glow
      const glow = ctx.createRadialGradient(cx, cy, baseR * 0.3, cx, cy, baseR * 1.5);
      glow.addColorStop(0, cfg.color + '40');
      glow.addColorStop(1, cfg.color + '00');
      ctx.fillStyle = glow;
      ctx.beginPath();
      ctx.arc(cx, cy, baseR * 1.5, 0, Math.PI * 2);
      ctx.fill();

      // Sphere shading
      const sphere = ctx.createRadialGradient(cx - baseR * 0.3, cy - baseR * 0.3, 0, cx, cy, baseR);
      sphere.addColorStop(0, '#ffffff60');
      sphere.addColorStop(0.45, cfg.color);
      sphere.addColorStop(1, cfg.color + 'bb');
      ctx.fillStyle = sphere;
      ctx.beginPath();
      ctx.arc(cx, cy, baseR * (0.82 + 0.14 * Math.sin(t * cfg.speed * cfg.pulse + cfg.phase)), 0, Math.PI * 2);
      ctx.fill();

      // Ring waves for speaking
      if (state === 'SPEAKING') {
        for (let i = 1; i <= 2; i++) {
          const r = baseR * (1.1 + 0.12 * i + 0.07 * Math.sin(t * 2.5 + i * 1.3));
          ctx.strokeStyle = cfg.color + Math.floor(70 - i * 22).toString(16);
          ctx.lineWidth = 1.5;
          ctx.beginPath();
          ctx.arc(cx, cy, r, 0, Math.PI * 2);
          ctx.stroke();
        }
      }

      t += 0.016;
      raf = requestAnimationFrame(draw);
    }

    draw();

    return {
      setState(s) { state = s; },
      stop() { if (raf) cancelAnimationFrame(raf); }
    };
  }

  // ===== State ==================================================
  const api = window.pywebview ? window.pywebview.api : null;
  let orb = null;
  let currentStep = 1;

  // ===== Navigation =============================================
  function showStep(n) {
    // Update current step and UI

    currentStep = n;
    document.querySelectorAll('.step').forEach(s => s.classList.remove('active'));
    const el = document.getElementById('step-' + n);
    if (el) el.classList.add('active');

    document.querySelectorAll('.step-dot').forEach(d => {
      const s = parseInt(d.dataset.step, 10);
      d.classList.toggle('active', s === n);
      d.classList.toggle('done', s < n);
    });

    updateOrb(n);

    if (n === 4) startInstallPoll();

    // Accessibility: move focus to first focusable element in the new step
    if (el) {
      const focusable = el.querySelector('button, a, input, select, textarea, [tabindex]:not([tabindex="-1"])');
      if (focusable) focusable.focus();
    }
    // Sync hidden generic next button for screen readers
    const nextBtn = document.getElementById('nextBtn');
    if (nextBtn) {
      const primary = el ? el.querySelector('button.btn-primary') : null;
      if (primary) {
        nextBtn.onclick = () => primary.click();
      } else {
        nextBtn.onclick = null;
      }
    }
  }

  function updateOrb(n) {
    if (!orb) return;
    const map = { 1: 'IDLE', 2: 'THINKING', 3: 'IDLE', 4: 'SPEAKING', 5: 'SPEAKING' };
    orb.setState(map[n] || 'IDLE');
  }

  function escHtml(s) {
    return String(s).replace(/&/g, '&').replace(/</g, '<').replace(/>/g, '>');
  }

  // ===== Step 1: Welcome ========================================
  function initWelcome() {
    const pathInput = document.getElementById('install-path');
    const browseBtn  = document.getElementById('btn-browse');
    const getStart   = document.getElementById('btn-get-started');
    const validation = document.getElementById('path-validation');

    browseBtn.addEventListener('click', async () => {
      if (!api) return;
      const path = await api.browse_folder();
      if (path) {
        pathInput.value = path;
        validatePath(path);
      }
    });

    pathInput.addEventListener('input', () => validatePath(pathInput.value));

    getStart.addEventListener('click', async () => {
      const path = pathInput.value.trim();
      if (!path || getStart.disabled) return;
      if (api) {
        await api.set_install_path(path);
        await api.scan_hardware();
      }
      showStep(2);
      // Auto-resume will handle rendering hw cards via polling
    });
  }

  function validatePath(path) {
    const validation = document.getElementById('path-validation');
    const getStart   = document.getElementById('btn-get-started');
    if (!path || path.length < 3) {
      validation.textContent = '';
      validation.className   = 'path-validation';
      getStart.disabled      = true;
      return;
    }
    const valid = !path.includes('\x00') && /^[A-Za-z]:/.test(path) || path.startsWith('/');
    validation.textContent = valid ? 'Path looks good' : 'Enter a valid path';
    validation.className   = 'path-validation ' + (valid ? 'valid' : 'invalid');
    getStart.disabled      = !valid;
  }

  // ===== Step 2: Hardware =======================================
  async function pollState() {
    if (!api) return;
    try {
      const state = await api.get_state();
      if (state.step === 2 && state.step_name === 'hardware') {
        renderHwCards(state.hw_profile || {});
      }
    } catch (e) { /* ignore */ }
  }

  function renderHwCards(hw) {
    const cards = document.getElementById('hw-cards');
    const scanHint = document.getElementById('scan-hint');
    if (scanHint) scanHint.style.display = 'none';

    const items = [
      { icon: '&#128187;', label: 'Processor',    value: hw.cpu_model || 'Detecting…',  cls: ''  },
      { icon: '&#127918;', label: 'Graphics',     value: hw.gpu_model || 'Detecting…', cls: hw.gpu_model && hw.gpu_model.toLowerCase().includes('nvidia') ? 'amber' : '' },
      { icon: '&#129504;', label: 'VRAM',          value: hw.vram_gb ? `${hw.vram_gb} GB available` : 'Detecting…', showBar: true, vramPct: hw.vram_pct || 0 },
      { icon: '&#128203;', label: 'Memory',        value: hw.ram || 'Detecting…',        cls: ''  },
      { icon: '&#128421;', label: 'OS',           value: hw.os || 'Detecting…',         cls: ''  },
    ];

    cards.innerHTML = items.map(item => `
      <div class="hw-card">
        <span class="icon">${item.icon}</span>
        <div class="meta">
          <div class="label">${item.label}</div>
          <div class="value ${item.cls || ''}">${item.value}</div>
          ${item.showBar ? `<div class="vram-bar"><div class="vram-fill" style="width:${item.vramPct}%"></div></div>` : ''}
        </div>
      </div>
    `).join('');

    // Stagger animation
    cards.querySelectorAll('.hw-card').forEach((card, i) => {
      setTimeout(() => card.classList.add('visible'), i * 130);
    });

    // Show rescan
    const rescan = document.getElementById('btn-rescan');
    if (rescan) rescan.classList.add('visible');

    // Enable continue
    document.getElementById('btn-continue-hw').disabled = false;
    document.getElementById('btn-continue-hw').addEventListener('click', () => {
      const vram = hw.vram_gb || 4;
      loadModels(vram);
      showStep(3);
    });

    // Rescan handler
    if (rescan) {
      rescan.addEventListener('click', async () => {
        rescan.textContent = 'Scanning…';
        if (api) await api.scan_hardware();
        rescan.textContent = 'Rescan';
      });
    }
  }

  // ===== Step 3: Models =========================================
  async function loadModels(vram_gb) {
    if (!api) return;
    try {
      const models = await api.get_models(vram_gb || 4);
      const baseSel  = document.getElementById('model-base');
      const imageSel = document.getElementById('model-image');
      const voiceSel = document.getElementById('model-voice');

      fillSelect(baseSel,  models.base  || [], 'base');
      fillSelect(imageSel, models.image || [], 'image');
      fillSelect(voiceSel, models.voice || [], 'voice');

      document.getElementById('vram-badge').textContent = `Recommended for ${vram_gb} GB VRAM`;

      // Size pills on change
      baseSel.addEventListener('change',  () => updateSizePillBySelect(baseSel,  'base'));
      imageSel.addEventListener('change', () => updateSizePillBySelect(imageSel, 'image'));
      voiceSel.addEventListener('change', () => updateSizePillBySelect(voiceSel, 'voice'));

      // Init pills
      updateSizePillBySelect(baseSel,  'base');
      updateSizePillBySelect(imageSel, 'image');
      updateSizePillBySelect(voiceSel, 'voice');
    } catch (e) { console.error('loadModels', e); }
  }

  function fillSelect(select, options, type) {
    select.innerHTML = options.map(m => `<option value="${escHtml(m.name)}">${escHtml(m.name)}</option>`).join('');
    if (!select.value && options.length) select.selectedIndex = 0;
  }

  function updateSizePillBySelect(select, type) {
    const model = select.options[select.selectedIndex];
    const pill  = document.getElementById('size-' + type);
    if (!model || !pill) return;
    const text = model.textContent;
    const tier = model.dataset.tier || 'medium';
    const size  = model.dataset.size || '—';
    pill.textContent = size;
    pill.className   = 'size-pill ' + (tier === 'large' ? 'large' : tier === 'medium' ? 'medium' : 'small');
  }

  function initStep3() {
    document.getElementById('btn-install').addEventListener('click', async () => {
      if (!api) return;
      await api.set_models(
        document.getElementById('model-base').value,
        document.getElementById('model-image').value,
        document.getElementById('model-voice').value
      );
      await api.start_install();
      showStep(4);
    });
    document.getElementById('btn-back-models').addEventListener('click', () => showStep(2));
  }

  // ===== Step 4: Installing ======================================
  function startInstallPoll() {
    (function poll() {
      if (currentStep !== 4) return;
      if (!api) { setTimeout(poll, 500); return; }
      api.get_state().then(s => {
        updateInstallUI(s);
        if (s.step_name === 'complete') {
          showStep(5);
        } else {
          setTimeout(poll, 300);
        }
      }).catch(() => setTimeout(poll, 500));
    })();
  }

  function updateInstallUI(s) {
    const pct = Math.round((s.install_progress || 0) * 100);
    const fill = document.getElementById('progress-fill');
    const pctEl = document.getElementById('install-pct');
    const statusEl = document.getElementById('install-status');

    if (fill)   fill.style.width   = pct + '%';
    if (pctEl)  pctEl.textContent  = pct + '%';
    if (statusEl && s.install_log && s.install_log.length) {
      const last = s.install_log[s.install_log.length - 1];
      if (last.includes('INSTALL COMPLETE'))  statusEl.textContent = 'All done!';
      else if (last.includes('FATAL') || last.includes('ERROR')) statusEl.textContent = 'Error occurred';
      else statusEl.textContent = last;
    }

    // Package list
    if (s.packages) {
      const pkgList = document.getElementById('pkg-list');
      if (pkgList) {
        pkgList.innerHTML = s.packages.map(pkg => {
          const cls = pkg.status === 'done' ? 'badge-done'
                    : pkg.status === 'installing' ? 'badge-installing'
                    : pkg.status === 'failed' ? 'badge-failed' : 'badge-pending';
          return `<div class="pkg-item">
            <span class="pkg-name">${escHtml(pkg.name)}</span>
            <span class="badge ${cls}">${escHtml(pkg.status || 'pending')}</span>
          </div>`;
        }).join('');
      }
    }

    // Log pane
    if (s.install_log) {
      const logPane = document.getElementById('log-pane');
      if (logPane) {
        logPane.innerHTML = s.install_log.map(l =>
          `<div class="log-line ${l.includes('FATAL') || l.includes('ERROR') && !l.includes('ERROR:') === false ? 'error' : ''}">${escHtml(l)}</div>`
        ).join('');
        logPane.scrollTop = logPane.scrollHeight;
      }
    }
  }

  function initStep4() {
    const toggle = document.getElementById('btn-toggle-log');
    const logPane = document.getElementById('log-pane');
    if (toggle && logPane) {
      toggle.addEventListener('click', () => {
        const show = logPane.style.display === 'none';
        logPane.style.display = show ? 'block' : 'none';
        toggle.innerHTML = show ? 'Hide log &#9650;' : 'Show log &#9660;';
      });
    }
  }

  // ===== Step 5: Complete =========================================
  function initStep5() {
    document.getElementById('btn-finish').addEventListener('click', async () => {
      if (!api) { window.close(); return; }
      await api.create_shortcuts_and_launch(
        document.getElementById('chk-desktop').checked,
        document.getElementById('chk-startmenu').checked,
        document.getElementById('chk-launch').checked
      );
      window.close();
    });
  }

  // ===== Boot ====================================================
  document.addEventListener('DOMContentLoaded', async () => {
    // Orb on both canvases
    const mainCanvas = document.getElementById('orb');
    const compCanvas  = document.getElementById('orb-complete');
    if (mainCanvas) orb = createOrb(mainCanvas, 'IDLE');
    else if (compCanvas) orb = createOrb(compCanvas, 'IDLE');

    // Step dot back-navigation
    document.querySelectorAll('.step-dot').forEach(dot => {
      dot.addEventListener('click', () => {
        const target = parseInt(dot.dataset.step, 10);
        if (target < currentStep) showStep(target);
      });
    });

    initWelcome();
    initStep3();
    initStep4();
    initStep5();

    // Restore state
    if (api) {
      try {
        const s = await api.get_state();
        if (s.install_path) {
          const el = document.getElementById('install-path');
          if (el) el.value = s.install_path;
        }
        if (s.step) showStep(s.step);
        if (s.step === 4) startInstallPoll();
      } catch (e) { showStep(1); }
    } else {
      showStep(1);
    }
  });

  // Background state refresh every 5s (for hardware scan completion)
  let pollTimer;
  (function startBgPoll() {
    pollState();
    pollTimer = setTimeout(startBgPoll, 2000);
  })();

})();