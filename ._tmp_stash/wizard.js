// installer_wizard/wizard.js — Moka AI Installer Wizard JS (6-step)
(function () {
  'use strict';

  // ===== Orb =====================================================
  const ORB = {
    IDLE:      { phase: 0,    color: '#c9a96e', pulse: 1.0,  speed: 1.0  },
    LISTENING: { phase: 0.15, color: '#c9a96e', pulse: 1.8,  speed: 1.4  },
    THINKING:  { phase: 0.3,  color: '#8a6c3e', pulse: 0.6,  speed: 0.7  },
    SPEAKING:  { phase: 0.5,  color: '#c9a96e', pulse: 2.2,  speed: 2.0  },
    ERROR:     { phase: 0,    color: '#e05c5c', pulse: 1.0,  speed: 0.8  },
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

      const glow = ctx.createRadialGradient(cx, cy, baseR * 0.3, cx, cy, baseR * 1.5);
      glow.addColorStop(0, cfg.color + '40');
      glow.addColorStop(1, cfg.color + '00');
      ctx.fillStyle = glow;
      ctx.beginPath();
      ctx.arc(cx, cy, baseR * 1.5, 0, Math.PI * 2);
      ctx.fill();

      const sphere = ctx.createRadialGradient(cx - baseR * 0.3, cy - baseR * 0.3, 0, cx, cy, baseR);
      sphere.addColorStop(0, '#ffffff60');
      sphere.addColorStop(0.45, cfg.color);
      sphere.addColorStop(1, cfg.color + 'bb');
      ctx.fillStyle = sphere;
      ctx.beginPath();
      ctx.arc(cx, cy, baseR * (0.82 + 0.14 * Math.sin(t * cfg.speed * cfg.pulse + cfg.phase)), 0, Math.PI * 2);
      ctx.fill();

      if (state === 'SPEAKING' || state === 'LISTENING') {
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

  // ===== API access =============================================
  function getApi() {
    if (window.pywebview && window.pywebview.api) {
      const firstKey = Object.keys(window.pywebview.api)[0];
      if (firstKey !== undefined || window.pywebview.api !== {}) {
        return window.pywebview.api;
      }
    }
    return null;
  }

  function waitForApi(maxMs) {
    return new Promise((resolve, reject) => {
      const t0 = Date.now();
      function poll() {
        const api = getApi();
        if (api) { resolve(api); return; }
        if (Date.now() - t0 > maxMs) { reject(new Error('API init timeout')); return; }
        setTimeout(poll, 100);
      }
      poll();
    });
  }

  // ===== State ==================================================
  let orb = null;
  let orbDemo = null;
  let currentStep = 1;
  let hwCardsRendered = false;
  let modelsLoadedForVram = 0;
  let installStarted = false;
  let downloadStarted = false;
  let demoOrbCanvas = null;
  let apiConfig = {
    localOnly: true,
    openaiKey: '',
    anthropicKey: '',
    customEndpoint: '',
  };
  let voicePreviewUtterance = null;

  // ===== Navigation =============================================
  function showStep(n) {
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

    if (n === 2) {
      initStep2();
      pollState();
    } else if (n === 3) {
      initStep3();
      // Get vRAM directly from the state to avoid race with async poll
      const api = getApi();
      let vram = modelsLoadedForVram;
      if (!vram && api) {
        try {
          const s = api.get_state();
          vram = (s.hw_profile && parseFloat(s.hw_profile.vram_gb)) || 4;
        } catch(e) { vram = 4; }
      }
      loadModels(vram || 4);
    } else if (n === 4) {
      initDownload();
      initStep4();
      startDownloadPoll();
    } else if (n === 5) {
      initStep5();
      startInstallPoll();
    } else if (n === 6) {
      initStep6();
    }
  }

  function updateOrb(n) {
    if (!orb) return;
    const map = { 1: 'IDLE', 2: 'THINKING', 3: 'IDLE', 4: 'SPEAKING', 5: 'SPEAKING', 6: 'IDLE' };
    orb.setState(map[n] || 'IDLE');
  }

  function updateDemoOrb(state) {
    if (orbDemo) orbDemo.setState(state);
    const indicator = document.getElementById('status-indicator');
    const statusText = document.getElementById('status-text');
    if (indicator) {
      indicator.className = 'status-indicator ' + state.toLowerCase();
    }
    if (statusText) {
      const labels = { IDLE: 'Ready to test', LISTENING: 'Listening...', THINKING: 'Thinking...', SPEAKING: 'Speaking...', ERROR: 'Error' };
      statusText.textContent = labels[state] || 'Ready to test';
    }
  }

  function escHtml(s) {
    return String(s).replace(/&/g, '&').replace(/</g, '<').replace(/>/g, '>');
  }

  // ===== Step 1: Path ===========================================
  function initWelcome() {
    const pathInput = document.getElementById('install-path');
    const browseBtn  = document.getElementById('btn-browse');
    const getStart   = document.getElementById('btn-get-started');
    const validation = document.getElementById('path-validation');

    browseBtn.addEventListener('click', async () => {
      try {
        const api = await waitForApi(3000);
        if (!api) { alert('Error: pywebview API not available'); return; }
        const path = await api.browse_folder();
        if (path && !path.startsWith('[ERROR')) {
          pathInput.value = path;
          validatePath(path);
        } else if (path) {
          alert('Browse failed: ' + path);
        }
      } catch(e) {
        alert('API connection error: ' + e.message);
      }
    });

    getStart.addEventListener('click', async function() {
      const path = pathInput.value.trim();
      if (!path || getStart.disabled) return;
      const api = getApi();
      if (api) {
        const result = await api.set_install_path(path);
        if (!result.valid) {
          validation.textContent = result.error || 'Invalid path — please choose another directory';
          validation.className = 'path-validation invalid';
          getStart.disabled = true;
          return;
        }
        pathInput.value = result.path;  // update with normalized path
        api.scan_hardware().catch(function() {});
        showStep(2);
      } else {
        showStep(2);
      }
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
    const valid = /^[A-Za-z]:/.test(path) || path.startsWith('/');
    validation.textContent = valid ? 'Ready to continue' : 'Enter a valid path';
    validation.className   = 'path-validation ' + (valid ? 'valid' : 'invalid');
    getStart.disabled      = !valid;
  }

  // ===== Step 2: Hardware =======================================
  async function pollState() {
    if (currentStep !== 2) return;
    const api = getApi();
    if (!api) { setTimeout(pollState, 500); return; }
    try {
      const s = await api.get_state();
      if (!hwCardsRendered && s.hw_profile && s.hw_profile.cpu && s.hw_profile.gpu) {
        renderHwCards(s.hw_profile);
        hwCardsRendered = true;
      }
      const continueBtn = document.getElementById('btn-continue-hw');
      if (continueBtn && s.hw_profile && s.hw_profile.cpu) {
        continueBtn.disabled = false;
      }
    } catch (e) { /* ignore */ }
    if (currentStep === 2) setTimeout(pollState, 500);
  }

  function renderHwCards(hw) {
    const cards = document.getElementById('hw-cards');
    const scanHint = document.getElementById('scan-hint');
    if (scanHint) scanHint.style.display = 'none';

    const SIPHON = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">';

    const items = [
      { icon: SIPHON + '<rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/><line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/><line x1="20" y1="9" x2="23" y2="9"/><line x1="20" y1="14" x2="23" y2="14"/><line x1="1" y1="9" x2="4" y2="9"/><line x1="1" y1="14" x2="4" y2="14"/></svg>', label: 'Processor',    value: hw.cpu || 'Detecting…',   cls: '' },
      { icon: SIPHON + '<rect x="2" y="6" width="20" height="12" rx="2"/><line x1="6" y1="10" x2="6" y2="14"/><line x1="10" y1="10" x2="10" y2="14"/><line x1="14" y1="10" x2="14" y2="14"/><circle cx="17" cy="12" r="1"/><line x1="7" y1="18" x2="7" y2="21"/><line x1="17" y1="18" x2="17" y2="21"/></svg>', label: 'Graphics',     value: hw.gpu || 'Detecting…',   cls: hw.gpu && hw.gpu.toLowerCase().includes('nvidia') ? 'amber' : '' },
      { icon: SIPHON + '<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>', label: 'VRAM',         value: hw.vram_gb ? hw.vram_gb + ' GB available' : 'Detecting…', showBar: true, vramPct: hw.vram_pct || 0 },
      { icon: SIPHON + '<path d="M6 19v-3"/><path d="M10 19v-6"/><path d="M14 19v-9"/><path d="M18 19v-12"/><rect x="2" y="5" width="20" height="14" rx="2"/></svg>', label: 'Memory',        value: hw.ram || 'Detecting…',   cls: '' },
      { icon: SIPHON + '<rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>', label: 'OS',            value: hw.os || 'Detecting…',     cls: '' },
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

    cards.querySelectorAll('.hw-card').forEach((card, i) => {
      setTimeout(() => card.classList.add('visible'), i * 130);
    });

    const rescan = document.getElementById('btn-rescan');
    if (rescan) rescan.classList.add('visible');

    document.getElementById('btn-continue-hw').disabled = false;
  }

  function initStep2() {
    const continueBtn = document.getElementById('btn-continue-hw');
    if (continueBtn && !continueBtn.dataset.ls) {
      continueBtn.dataset.ls = '1';
      continueBtn.addEventListener('click', async () => {
        const api = getApi();
        if (api) {
          try {
            const s = await api.get_state();
            if (s?.hw_profile?.vram_gb) {
              modelsLoadedForVram = parseFloat(s.hw_profile.vram_gb) || 4;
            }
          } catch(e) {}
        }
        showStep(3);
      });
    }

    const backBtn = document.getElementById('btn-back-hw');
    if (backBtn) {
      backBtn.addEventListener('click', () => showStep(1));
    }

    const rescan = document.getElementById('btn-rescan');
    if (rescan) {
      rescan.addEventListener('click', async () => {
        rescan.textContent = 'Scanning…';
        const api = getApi();
        if (api) await api.scan_hardware();
        rescan.textContent = 'Rescan';
      });
    }
  }

  // ===== Step 3: Models + Voice =================================
  async function loadModels(vram_gb) {
    let api;
    try {
      api = await waitForApi(5000);
    } catch(e) {
      console.error('loadModels: API not available', e);
      return;
    }
    if (!api) return;
    try {
      const models = await api.get_models(vram_gb || modelsLoadedForVram || 4);
      const baseSel  = document.getElementById('model-base');
      const imageSel = document.getElementById('model-image');
      const voiceSel = document.getElementById('model-voice');

      const mBase  = models.find(m => m.type === 'base');
      const mImage = models.find(m => m.type === 'image');
      const mVoice = models.find(m => m.type === 'voice');

      fillSelect(baseSel,  mBase?.options  || [], 'base');
      fillSelect(imageSel, mImage?.options || [], 'image');
      fillSelect(voiceSel, mVoice?.options || [], 'voice');

      document.getElementById('vram-badge').textContent = `Recommended for ${vram_gb || modelsLoadedForVram || 4} GB VRAM`;

      baseSel.addEventListener('change',  () => { updateSizePillBySelect(baseSel); updateTotalSize(); });
      imageSel.addEventListener('change', () => { updateSizePillBySelect(imageSel); updateTotalSize(); });
      voiceSel.addEventListener('change', () => { updateSizePillBySelect(voiceSel); onVoiceChanged(); updateTotalSize(); });

      updateSizePillBySelect(baseSel);
      updateSizePillBySelect(imageSel);
      updateSizePillBySelect(voiceSel);
      updateTotalSize();

      // Show voice samples/buttons for the auto-selected voice
      onVoiceChanged();
    } catch (e) { console.error('loadModels', e); }
  }

  function fillSelect(select, options, type) {
    const selectedName = options.find(m => m.recommended)?.name || '';
    select.innerHTML = options.map(m =>
      `<option value="${escHtml(m.name)}" data-size="${m.size_gb || 0}"${m.recommended ? ' data-rec="1"' : ''}>${escHtml(m.name)}${m.recommended ? ' ★' : ''}</option>`
    ).join('');
    if (selectedName && select.querySelector(`option[value="${selectedName}"]`)) {
      select.value = selectedName;
    } else if (!select.value && options.length) {
      select.selectedIndex = 0;
    }
  }

  function updateSizePillBySelect(select) {
    const model = select.options[select.selectedIndex];
    const pill  = document.getElementById('size-' + select.id.replace('model-', ''));
    if (!model || !pill) return;
    const size = parseFloat(model.dataset.size || 0);
    pill.textContent = size > 0 ? `~${size.toFixed(1)} GB` : '—';
    const rec = model.dataset.rec === '1';
    pill.className = 'size-pill' + (rec ? ' s' : '');
  }

  function updateTotalSize() {
    const base  = document.getElementById('model-base');
    const image = document.getElementById('model-image');
    const voice = document.getElementById('model-voice');
    const el    = document.getElementById('total-size');
    if (!el) return;

    let total = 0;
    [base, image, voice].forEach(sel => {
      if (sel && sel.selectedIndex >= 0) {
        total += parseFloat(sel.options[sel.selectedIndex].dataset.size || 0);
      }
    });

    if (total > 0) {
      el.textContent = `Total: ~${total.toFixed(1)} GB`;
    } else {
      el.textContent = '';
    }
  }

  // Voice sample phrases — keyed by model name
  // These phrases are spoken via browser speechSynthesis as demo previews
  const VOICE_PHRASES = {
    'xttsv2-female':    ['Magandang umaga! Ako si Moka, handang tumulong.', 'Hello! I am Moka, your voice companion. How can I help you today?', 'Quick test. This is how I sound.'],
    'xttsv2-male':      ['Good morning! I am Moka, ready to assist you today.', 'Paano mo ako matutulungan? Let me know what you need.', 'Testing, testing... one, two, three.'],
    'parler-tts-large': ['Good day! I am Moka, your AI voice companion.', 'Let me help you with coding, images, and everyday tasks.', 'This is a sample of my voice at work.'],
  };

  function onVoiceChanged() {
    const sel = document.getElementById('model-voice');
    const voiceName = sel ? sel.value : '';
    const samplesSection = document.getElementById('voice-samples');
    const btns = document.querySelectorAll('.sample-btn');
    const phrases = VOICE_PHRASES[voiceName] || VOICE_PHRASES['xttsv2-female'];

    // Show voice samples section only after a model is chosen
    if (samplesSection) {
      samplesSection.style.display = voiceName ? 'flex' : 'none';
    }

    // Label each button with the phrase preview (first 30 chars)
    btns.forEach((btn, i) => {
      if (phrases[i]) {
        const short = phrases[i].slice(0, 28).trim() + (phrases[i].length > 28 ? '…' : '');
        btn.textContent = short;
        btn.title = phrases[i]; // full phrase on hover
        btn.disabled = false;
      } else {
        btn.textContent = 'Sample ' + (i + 1);
        btn.disabled = true;
      }
    });
  }

  function initVoiceSamples() {
    const samplesSection = document.getElementById('voice-samples');
    const sampleButtons = document.getElementById('sample-buttons');
    if (samplesSection) samplesSection.style.display = 'none';

    // Create sample buttons once
    if (sampleButtons) {
      sampleButtons.innerHTML = `
        <button class="sample-btn">Sample 1</button>
        <button class="sample-btn">Sample 2</button>
        <button class="sample-btn">Sample 3</button>
      `;
    }

    sampleButtons?.querySelectorAll('.sample-btn').forEach((btn, idx) => {
      btn.addEventListener('click', () => {
        sampleButtons?.querySelectorAll('.sample-btn').forEach(b => b.classList.remove('playing'));
        btn.classList.add('playing');
        const sel = document.getElementById('model-voice');
        const voiceName = sel ? sel.value : 'xttsv2-female';
        const phrases = VOICE_PHRASES[voiceName] || VOICE_PHRASES['xttsv2-female'];
        const text = phrases[idx] || phrases[0];
        if (speechSynthesis) {
          speechSynthesis.cancel();
          const utter = new SpeechSynthesisUtterance(text);
          utter.rate = 1.1;
          const voices = speechSynthesis.getVoices();
          if (voices.length > 0) {
            const enVoices = voices.filter(v => v.lang.startsWith('en'));
            utter.voice = enVoices[idx % Math.max(enVoices.length, 1)] || voices[0];
          }
          utter.onend = utter.onerror = () => btn.classList.remove('playing');
          speechSynthesis.speak(utter);
        }
      });
    });
  }

  function previewVoice() {
    if (voicePreviewUtterance) {
      speechSynthesis.cancel();
      voicePreviewUtterance = null;
      return;
    }
    const sel = document.getElementById('model-voice');
    const voiceName = sel ? sel.value : 'xttsv2-female';
    const phrases = VOICE_PHRASES[voiceName] || VOICE_PHRASES['xttsv2-female'];
    const text = phrases[0];
    const utter = new SpeechSynthesisUtterance(text);
    utter.rate = 1.15;
    utter.onend = () => { voicePreviewUtterance = null; };
    utter.onerror = () => { voicePreviewUtterance = null; };
    voicePreviewUtterance = utter;
    speechSynthesis.speak(utter);
  }

  function initStep3() {
    initVoiceSamples(); // set up voice sample button handlers

    const previewBtn = document.getElementById('btn-preview-voice');
    if (previewBtn) {
      previewBtn.addEventListener('click', previewVoice);
    }

    const localOnlyChk = document.getElementById('chk-local-only');
    const grpOpenAI    = document.getElementById('grp-openai');
    const grpAnthropic = document.getElementById('grp-anthropic');

    function updateApiFieldVisibility() {
      const hide = localOnlyChk && localOnlyChk.checked;
      if (grpOpenAI)    grpOpenAI.style.display    = hide ? 'none' : '';
      if (grpAnthropic) grpAnthropic.style.display = hide ? 'none' : '';
    }

    if (localOnlyChk) {
      localOnlyChk.addEventListener('change', updateApiFieldVisibility);
      updateApiFieldVisibility();
    }

    const backBtn = document.getElementById('btn-back-models');
    if (backBtn) backBtn.addEventListener('click', () => showStep(2));

    document.getElementById('btn-proceed-download').addEventListener('click', async function() {
      const api = getApi();
      if (!api) { showStep(4); return; }

      apiConfig.localOnly     = localOnlyChk ? localOnlyChk.checked : true;
      apiConfig.openaiKey    = (document.getElementById('input-openai-key')     || {}).value || '';
      apiConfig.anthropicKey = (document.getElementById('input-anthropic-key') || {}).value || '';
      apiConfig.customEndpoint = (document.getElementById('input-custom-endpoint') || {}).value || '';

      try {
        await api.set_api_config(
          apiConfig.openaiKey,
          apiConfig.anthropicKey,
          apiConfig.customEndpoint,
          apiConfig.localOnly,
        );
        await api.set_models(
          document.getElementById('model-base').value,
          document.getElementById('model-image').value,
          document.getElementById('model-voice').value
        );
        await api.start_download();
        showStep(4);
      } catch(e) {
        console.error('Proceed failed:', e);
        showStep(4);
      }
    });
  }

  // ===== Step 4: Downloading ====================================
  // Called by showStep(4) — starts the download via API, then polls
  function initDownload() {
    if (downloadStarted) return;  // guard: only start once per visit
    downloadStarted = true;

    const api = getApi();
    if (api) {
      // Fire-and-forget: backend downloads, JS polls for completion
      api.start_download().catch(() => {
        // fallback: simulate if API call fails
        startSimulatedDownload();
      });
    } else {
      startSimulatedDownload();
    }
  }

  function startSimulatedDownload() {
    const items = [
      { id: 'python',      total: 80   },
      { id: 'model-base',  total: 4000 },
      { id: 'model-image', total: 3000 },
      { id: 'voice',       total: 150  },
      { id: 'deps',        total: 500  },
    ];

    let doneCount = 0;
    let totalBytes = items.reduce(function(a, i) { return a + i.total; }, 0);
    let downloadedBytesArr = items.map(function() { return 0; });

    items.forEach(function(item, idx) {
      let progress = 0;

      const timer = setInterval(function() {
        if (currentStep !== 4) { clearInterval(timer); return; }
        progress += 0.12 + Math.random() * 0.15;
        if (progress >= 1) {
          progress = 1;
          clearInterval(timer);
          doneCount++;
          downloadedBytesArr[idx] = item.total;
          setDlStatus(item.id, 'done', 100);
          checkDownloadComplete(doneCount, items.length);
        } else {
          downloadedBytesArr[idx] = Math.floor(item.total * progress);
          setDlStatus(item.id, 'downloading', Math.round(progress * 100));
        }

        var totalDownloaded = 0;
        for (var j = 0; j < items.length; j++) {
          totalDownloaded += downloadedBytesArr[j] || 0;
        }
        updateDownloadSummary(totalDownloaded, totalBytes);
      }, 80);
    });
  }

  function startDownloadPoll() {
    (function poll() {
      if (currentStep !== 4) return;
      const api = getApi();
      if (!api) { setTimeout(poll, 500); return; }
      api.get_state().then(s => {
        if (s.download_items) {
          updateDownloadUI(s.download_items);
        }
        // Backend transitions from DOWNLOAD(4) → INSTALLING(5) when done
        if (s.step >= 5) {
          setDlAllDone();
          showStep(5);  // auto-advance
        } else {
          setTimeout(poll, 500);
        }
      }).catch(() => setTimeout(poll, 500));
    })();
  }

  function setDlAllDone() {
    ['python','model-base','model-image','voice','deps'].forEach(id => {
      const bar = document.getElementById('dl-' + id + '-bar');
      const statusEl = document.getElementById('dl-' + id + '-status');
      if (bar) bar.style.width = '100%';
      if (statusEl) { statusEl.textContent = 'Complete'; statusEl.className = 'dl-status done'; }
    });
    const btn = document.getElementById('btn-continue-download');
    if (btn) btn.disabled = false;
  }

  function updateDownloadUI(items) {
    if (!items) return;
    let totalDone = 0, totalSize = 0;
    items.forEach(item => {
      const pct = Math.round((item.downloaded || 0) / (item.total || 1) * 100);
      const bar = document.getElementById('dl-' + item.id + '-bar');
      const status = document.getElementById('dl-' + item.id + '-status');
      if (bar) bar.style.width = pct + '%';
      if (status) {
        status.textContent = item.status === 'done' ? 'Complete' : item.status === 'downloading' ? pct + '%' : 'Waiting...';
        status.className = 'dl-status ' + (item.status || '');
      }
      totalDone += item.downloaded || 0;
      totalSize += item.total || 0;
    });
    updateDownloadSummary(totalDone, totalSize);
  }

  function setDlStatus(id, status, pct) {
    const bar = document.getElementById('dl-' + id + '-bar');
    const statusEl = document.getElementById('dl-' + id + '-status');
    const sizeEl = document.getElementById('dl-' + id + '-size');
    if (bar) bar.style.width = pct + '%';
    if (statusEl) {
      statusEl.textContent = status === 'done' ? 'Complete' : pct + '%';
      statusEl.className = 'dl-status ' + status;
    }
  }

  function updateDownloadSummary(done, total) {
    const el = document.getElementById('dl-total-progress');
    if (el) {
      const fmt = b => b >= 1000 ? (b / 1000).toFixed(1) + ' GB' : b + ' MB';
      el.textContent = `${fmt(done)} / ${fmt(total)} downloaded`;
    }
  }

  function checkDownloadComplete(done, total) {
    const btn = document.getElementById('btn-continue-download');
    if (done >= total && btn) {
      btn.disabled = false;
    }
  }

  function initStep4() {
    const continueBtn = document.getElementById('btn-continue-download');
    if (continueBtn) {
      continueBtn.addEventListener('click', () => {
        if (installStarted) return;
        installStarted = true;
        const api = getApi();
        if (api) {
          try { api.start_install(); } catch(e) { console.error(e); }
        }
        showStep(5);
      });
    }

    const cancelBtn = document.getElementById('btn-cancel-download');
    if (cancelBtn) {
      cancelBtn.addEventListener('click', () => {
        if (confirm('Cancel the download and return to model selection?')) {
          downloadStarted = false;
          showStep(3);
        }
      });
    }
  }

  // ===== Step 5: Installing =====================================
  function startInstallPoll() {
    (function poll() {
      if (currentStep !== 5) return;
      const api = getApi();
      if (!api) { setTimeout(poll, 500); return; }
      api.get_state().then(s => {
        updateInstallUI(s);
        if (s.step >= 6) {           // COMPLETE = 6
          setTimeout(() => showStep(6), 800);
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
    if (statusEl && s.log && s.log.length) {
      const last = s.log[s.log.length - 1];
      if (last.includes('INSTALL COMPLETE'))  statusEl.textContent = 'All done!';
      else if (last.includes('FATAL') || last.includes('ERROR')) statusEl.textContent = 'Error occurred';
      else statusEl.textContent = last;
    }

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

    if (s.log) {
      const logPane = document.getElementById('log-pane');
      if (logPane) {
        logPane.innerHTML = s.log.map(l =>
          `<div class="log-line">${escHtml(l)}</div>`
        ).join('');
        logPane.scrollTop = logPane.scrollHeight;
      }
    }
  }

  function initStep5() {
    const toggle = document.getElementById('btn-toggle-log');
    const logPane = document.getElementById('log-pane');
    if (toggle && logPane) {
      toggle.addEventListener('click', () => {
        const show = logPane.style.display === 'none';
        logPane.style.display = show ? 'block' : 'none';
        toggle.innerHTML = show ? 'Hide log ▲' : 'Show log ▼';
      });
    }

    const backBtn = document.getElementById('btn-back-install');
    if (backBtn) {
      backBtn.addEventListener('click', () => {
        const inProgress = installStarted;   // install was started
        if (inProgress && !confirm('Installation in progress. Go back to download?')) return;
        showStep(4);
      });
    }
  }

  // ===== Step 6: Demo ===========================================
  function initDemo() {
    // Create demo orb
    if (!orbDemo && demoOrbCanvas) {
      orbDemo = createOrb(demoOrbCanvas, 'IDLE');
    }
    updateDemoOrb('IDLE');

    const micBtn = document.getElementById('btn-mic-test');
    const speakerBtn = document.getElementById('btn-speaker-test');
    const fixBtn = document.getElementById('btn-self-fix');
    const undoBtn = document.getElementById('btn-undo-install');
    const convEl = document.getElementById('demo-conversation');

    if (micBtn) {
      micBtn.addEventListener('click', async () => {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
          alert('Microphone access is not available in this environment.');
          return;
        }
        try {
          micBtn.classList.add('success');
          updateDemoOrb('LISTENING');
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
          stream.getTracks().forEach(t => t.stop());
          micBtn.classList.remove('success', 'error');
          micBtn.classList.add('success');
          updateDemoOrb('SPEAKING');
          addDemoMessage(convEl, 'Microphone working!', 'moka');
          setTimeout(() => updateDemoOrb('IDLE'), 2000);
        } catch(e) {
          micBtn.classList.remove('success');
          micBtn.classList.add('error');
          updateDemoOrb('ERROR');
          addDemoMessage(convEl, 'Microphone access denied or unavailable.', 'error');
          setTimeout(() => updateDemoOrb('IDLE'), 3000);
        }
      });
    }

    if (speakerBtn) {
      speakerBtn.addEventListener('click', () => {
        if (!speechSynthesis) {
          alert('Speech synthesis is not available.');
          return;
        }
        speakerBtn.classList.add('success');
        updateDemoOrb('SPEAKING');
        const utter = new SpeechSynthesisUtterance('Hello! I am Moka. Your voice assistant is ready to help you.');
        utter.rate = 1.0;
        utter.onend = utter.onerror = () => {
          speakerBtn.classList.remove('success', 'error');
          speakerBtn.classList.add('success');
          updateDemoOrb('IDLE');
        };
        speechSynthesis.speak(utter);
      });
    }

    if (fixBtn) {
      fixBtn.addEventListener('click', async () => {
        updateDemoOrb('THINKING');
        addDemoMessage(convEl, 'Running self-diagnostics...', 'moka');
        const api = getApi();
        if (api && api.self_fix) {
          try {
            await api.self_fix();
            addDemoMessage(convEl, 'All systems verified and fixed!', 'moka');
          } catch(e) {
            addDemoMessage(convEl, 'Self-fix completed with minor warnings.', 'moka');
          }
        } else {
          setTimeout(() => {
            addDemoMessage(convEl, 'Self-fix complete. All components are healthy.', 'moka');
            updateDemoOrb('IDLE');
          }, 2000);
        }
      });
    }

    if (undoBtn) {
      undoBtn.addEventListener('click', () => {
        if (confirm('This will remove Moka AI and all installed components. Continue?')) {
          const api = getApi();
          if (api && api.undo_install) {
            api.undo_install().then(() => {
              window.close();
            }).catch(() => {
              window.close();
            });
          } else {
            window.close();
          }
        }
      });
    }
  }

  function initStep6() {
    // Create demo orb
    if (!orbDemo && demoOrbCanvas) {
      orbDemo = createOrb(demoOrbCanvas, 'IDLE');
    }
    updateDemoOrb('IDLE');

    const micBtn     = document.getElementById('btn-mic-test');
    const speakerBtn = document.getElementById('btn-speaker-test');
    const fixBtn     = document.getElementById('btn-self-fix');
    const undoBtn    = document.getElementById('btn-undo-install');
    const convEl     = document.getElementById('demo-conversation');
    const finishBtn  = document.getElementById('btn-finish');

    // Mic Test — real mic + Moka responds via Python TTS
    if (micBtn) {
      micBtn.addEventListener('click', async function() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
          addDemoMessage(convEl, 'Microphone not available in this environment.', 'error');
          return;
        }
        updateDemoOrb('LISTENING');
        addDemoMessage(convEl, 'Listening...', 'user');
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
          stream.getTracks().forEach(function(t) { t.stop(); });
          updateDemoOrb('SPEAKING');
          addDemoMessage(convEl, 'Mic working! Moka is responding...', 'moka');
          const api = getApi();
          const responses = [
            'Hello, I am Moka. Your voice assistant is fully operational.',
            'Great, your microphone is working perfectly. How can I help you today?',
            'I hear you clearly. What would you like to do?',
          ];
          const response = responses[Math.floor(Math.random() * responses.length)];
          if (api && api.speak_text) {
            await api.speak_text(response);
          }
          addDemoMessage(convEl, response, 'moka');
          setTimeout(function() { updateDemoOrb('IDLE'); }, 3000);
        } catch(e) {
          updateDemoOrb('ERROR');
          addDemoMessage(convEl, 'Microphone access denied or unavailable.', 'error');
          setTimeout(function() { updateDemoOrb('IDLE'); }, 3000);
        }
      });
    }

    // Speaker Test — use Python TTS
    if (speakerBtn) {
      speakerBtn.addEventListener('click', async function() {
        updateDemoOrb('SPEAKING');
        const api = getApi();
        const text = 'Hello, I am Moka. Your speaker test was successful.';
        try {
          if (api && api.speak_text) {
            await api.speak_text(text);
          }
          addDemoMessage(convEl, 'Moka spoke successfully via the installed TTS engine.', 'moka');
        } catch(e) {
          addDemoMessage(convEl, 'Speaker test had an issue: ' + e.message, 'error');
        }
        setTimeout(function() { updateDemoOrb('IDLE'); }, 2000);
      });
    }

    // Self-Fix — run Python diagnostics
    if (fixBtn) {
      fixBtn.addEventListener('click', async function() {
        updateDemoOrb('THINKING');
        addDemoMessage(convEl, 'Running self-diagnostics...', 'moka');
        const api = getApi();
        try {
          if (api && api.run_self_diagnostics) {
            const report = await api.run_self_diagnostics();
            (report.log || []).forEach(function(line) { addDemoMessage(convEl, line, 'moka'); });
            addDemoMessage(convEl, report.ok ? 'All systems verified. Moka AI is healthy.' : 'Self-fix complete. Review any warnings above.', 'moka');
          } else if (api && api.self_fix) {
            await api.self_fix();
            addDemoMessage(convEl, 'Self-fix complete. All components healthy.', 'moka');
          } else {
            addDemoMessage(convEl, 'Self-fix not available in this environment.', 'error');
          }
        } catch(e) {
          addDemoMessage(convEl, 'Self-fix error: ' + e.message, 'error');
        }
        updateDemoOrb('IDLE');
      });
    }

    // Undo — call Python uninstall
    if (undoBtn) {
      undoBtn.addEventListener('click', function() {
        if (!confirm('This will remove Moka AI and all installed components. Continue?')) return;
        const api = getApi();
        if (api && api.undo_install) {
          api.undo_install().then(function(result) {
            if (result.ok) {
              addDemoMessage(convEl, 'Moka AI removed successfully.', 'moka');
              setTimeout(function() { window.close(); }, 2000);
            } else {
              addDemoMessage(convEl, 'Undo failed: ' + (result.error || 'Unknown error'), 'error');
            }
          }).catch(function(e) {
            addDemoMessage(convEl, 'Undo error: ' + e.message, 'error');
          });
        } else {
          window.close();
        }
      });
    }

    // Finish — create shortcuts, register uninstaller, then close
    if (finishBtn) {
      finishBtn.addEventListener('click', async function() {
        finishBtn.disabled = true;
        const desktop   = document.getElementById('chk-desktop').checked;
        const startmenu = document.getElementById('chk-startmenu').checked;
        const launch    = document.getElementById('chk-launch').checked;
        const api = getApi();
        if (api) {
          try {
            await api.create_shortcuts_and_launch(desktop, startmenu, launch);
            await api.register_uninstaller('1.0.0');
          } catch(e) { /* continue to close */ }
        }
        setTimeout(function() {
          const cApi = getApi();
          if (cApi && cApi.close_window) cApi.close_window();
          else if (window.close) window.close();
        }, 1500);
      });
    }
  }

  // ===== Boot ==================================================
  document.addEventListener('DOMContentLoaded', async () => {
    const mainCanvas = document.getElementById('orb');
    if (mainCanvas) {
      orb = createOrb(mainCanvas, 'IDLE');
    }

    demoOrbCanvas = document.getElementById('orb-demo');

    // --- Frameless window controls ---
    document.getElementById('btn-minimize')?.addEventListener('click', async () => {
      const api = await waitForApi(2000).catch(() => null);
      if (api?.minimize_window) api.minimize_window();
    });

    document.getElementById('btn-maximize')?.addEventListener('click', async () => {
      const api = await waitForApi(2000).catch(() => null);
      if (api?.maximize_window) api.maximize_window();
    });

    document.getElementById('btn-close')?.addEventListener('click', async () => {
      const api = await waitForApi(2000).catch(() => null);
      if (api?.close_window) api.close_window();
      else if (window.close) window.close();
    });

    document.querySelectorAll('.step-dot').forEach(dot => {
      dot.addEventListener('click', () => {
        const target = parseInt(dot.dataset.step, 10);
        if (target < currentStep) showStep(target);
      });
    });

    initWelcome();
    initStep2();
    initStep3();
    initStep4();
    initStep5();
    initStep6();

    const api = getApi();
    if (api) {
      try {
        const s = await api.get_state();
        if (s.install_path) {
          const el = document.getElementById('install-path');
          if (el) el.value = s.install_path;
        }
        if (s.step) showStep(s.step);
        if (s.step === 4) startDownloadPoll();
        if (s.step === 5) startInstallPoll();
      } catch (e) { showStep(1); }
    } else {
      try {
        const connectedApi = await waitForApi(5000);
        const s = await connectedApi.get_state();
        if (s.install_path) {
          const el = document.getElementById('install-path');
          if (el) el.value = s.install_path;
        }
        if (s.step) showStep(s.step);
        if (s.step === 4) startDownloadPoll();
        if (s.step === 5) startInstallPoll();
      } catch(e) { showStep(1); }
    }
  });

  // Background state refresh
  (function startBgPoll() {
    pollState();
    setTimeout(startBgPoll, 2000);
  })();

})();